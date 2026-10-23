"""The AVL adapter against a fake executable through the real ``run_process`` (fast tier)."""

import asyncio
import json
import stat
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError, ToolRunTimeoutError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers import avl as avl_module
from aero_kernel.solvers.avl import AvlAdapter, AvlNeutralPoint, Contour
from aero_kernel.solvers.avl_writer import AvlOutput
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with
from aero_kernel.tests.solver_builders import airplane

SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
geometry = pathlib.Path(sys.argv[1]).read_text()
commands = sys.stdin.read()
(here / "pid.txt").write_text(str(__import__("os").getpid()))
if config.get("sleep"):
    __import__("time").sleep(config["sleep"])
n_chord = int(re.search(r"#Nchordwise  Cspace\\n(\\d+)", geometry).group(1))
cl = float(re.search(r"a c (\\S+)", commands).group(1))
(here / "seen.json").write_text(json.dumps({{"n_chord": n_chord, "commands": commands, "geometry": geometry, "files": sorted(p.name for p in pathlib.Path('.').iterdir())}}))
if str(n_chord) in config.get("overflow", []):
    print(" SDUPL: Vortex array overflow. Increase NVMAX currently")
    sys.exit(0)
if str(n_chord) in config.get("illegal", []):
    print(" ** On entry to DGETRF parameter number  4 had an illegal value")
    sys.exit(0)
print(" Sref = 0.28000")
print(" CLtot = %.5f" % (cl + config.get("cl_offset", 0.0)))
print(" Xnp = %r" % config["xnp"][str(n_chord)])
sys.exit(config.get("exit", 0))
"""


class FakeAvl(AvlAdapter):
    """The adapter with AeroSandbox's contour work replaced and availability assumed."""

    def available(self) -> bool:
        return True

    async def _contours(self, airfoils: tuple[object, ...]) -> tuple[Contour, ...]:
        return tuple(
            Contour(coordinates=((1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), claf=1.0924) for _ in airfoils
        )


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import sys

    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    configure(tmp_path, {"10": 0.14, "20": 0.14})
    return tmp_path


def configure(directory: Path, xnp: dict[str, float], **extra: object) -> None:
    (directory / "fake.json").write_text(json.dumps({"xnp": xnp, **extra}))


async def neutral(directory: Path, cl: float = 0.5) -> AvlNeutralPoint:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).neutral_point(airplane_with(*CONVENTIONAL), cl)


@pytest.mark.asyncio
async def test_the_declared_meshs_value_is_returned_without_warning_when_the_refinement_agrees(
    fake: Path,
) -> None:
    found = await neutral(fake)
    assert found.x_np == 0.14
    assert found.warnings == ()


@pytest.mark.asyncio
async def test_avl_gets_the_declared_and_the_refined_mesh_and_the_requested_cl(fake: Path) -> None:
    await neutral(fake, cl=0.62)
    seen = json.loads((fake / "seen.json").read_text())  # the last run: the refined one
    assert seen["n_chord"] == 20
    assert "a c 0.62" in seen["commands"]
    assert "af0.dat" in seen["files"]
    assert "airplane.avl" in seen["files"]


@pytest.mark.asyncio
async def test_a_disagreement_above_the_tolerance_is_a_defect_warning_with_both_values(
    fake: Path,
) -> None:
    configure(fake, {"10": 0.14, "20": 0.14 + 0.2 * 0.006})  # 0.6 % MAC of c_MAC = 0.2 m
    found = await neutral(fake)
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == ("avl_mesh_not_converged", WarningSeverity.DEFECT)
    assert warning.detail["x_np_declared"] == 0.14
    assert warning.detail["delta_mac"] == pytest.approx(0.006, rel=1e-9)  # pyright: ignore[reportUnknownMemberType]
    assert found.x_np == 0.14


@pytest.mark.asyncio
async def test_a_disagreement_within_the_tolerance_is_silent(fake: Path) -> None:
    configure(fake, {"10": 0.14, "20": 0.14 + 0.2 * 0.004})
    assert (await neutral(fake)).warnings == ()


@pytest.mark.asyncio
async def test_a_refined_mesh_that_overflows_is_an_unchecked_refinement(fake: Path) -> None:
    configure(fake, {"10": 0.14}, overflow=["20"])
    found = await neutral(fake)
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == ("avl_refinement_unchecked", WarningSeverity.DEFECT)
    assert found.x_np == 0.14


@pytest.mark.asyncio
async def test_a_declared_mesh_that_overflows_is_an_array_limit_error(fake: Path) -> None:
    configure(fake, {}, overflow=["10"])
    with pytest.raises(FormulaError) as raised:
        await neutral(fake)
    assert (raised.value.category, raised.value.code) == (
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "avl_array_limit",
    )


@pytest.mark.asyncio
async def test_a_nonzero_exit_is_a_defect(fake: Path) -> None:
    configure(fake, {"10": 0.14, "20": 0.14}, exit=3)
    with pytest.raises(RuntimeError, match="did not complete"):
        await neutral(fake)


@pytest.mark.asyncio
async def test_a_missed_lift_coefficient_is_a_defect(fake: Path) -> None:
    configure(fake, {"10": 0.14, "20": 0.14}, cl_offset=0.01)
    with pytest.raises(RuntimeError, match="not the requested"):
        await neutral(fake)


@pytest.mark.asyncio
async def test_a_missing_binary_is_tool_unavailable(
    fake: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("avl_binary.avl_path", lambda: fake / "absent", raising=False)
    with pytest.raises(FormulaError) as raised:
        await neutral(fake)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


def test_the_settings_are_public_keys_with_their_values() -> None:
    assert AvlAdapter(SolverRuntime()).settings() == {
        "avl_nchord": 10,
        "avl_nspan": 24,
        "avl_airfoil_points_per_side": 80,
        "avl_core_ratio": 0.25,
        "avl_refine_factor": 2,
        "avl_refinement_tolerance_mac": 0.005,
    }


def test_the_module_states_its_sources() -> None:
    assert avl_module.CLAF_PER_THICKNESS == 0.77


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "deflection"), [("flap", 30.0), ("aileron", -5.0), ("flaperon", 0.5)]
)
async def test_a_deflected_control_surface_is_refused_not_computed_as_clean(
    fake: Path, role: str, deflection: float
) -> None:
    """The writer emits no CONTROL, so a deflected device would silently be ignored."""
    async with SolverRuntime() as runtime:
        with pytest.raises(FormulaError) as raised:
            await FakeAvl(runtime).neutral_point(airplane(device=(role, deflection)), 0.5)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "not yet passed to AVL" in raised.value.message
    assert role in raised.value.message
    assert not (fake / "seen.json").exists()  # AVL was never started


@pytest.mark.asyncio
async def test_a_matrix_too_large_for_avl_is_the_same_limit_as_an_overflow(fake: Path) -> None:
    """AVL 3.40 on a very fine mesh exits 0 with a LAPACK 'illegal value' instead of the overflow text."""
    configure(fake, {"10": 0.14}, illegal=["20"])
    found = await neutral(fake)
    assert [w.code for w in found.warnings] == ["avl_refinement_unchecked"]
    configure(fake, {}, illegal=["10"])
    with pytest.raises(FormulaError) as raised:
        await neutral(fake)
    assert raised.value.code == "avl_array_limit"


def alive(directory: Path) -> bool:
    """Whether the fake AVL of the last run still exists."""
    import os

    try:
        os.kill(int((directory / "pid.txt").read_text()), 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.asyncio
async def test_a_run_longer_than_the_adapters_own_limit_is_a_timeout_and_is_killed(
    fake: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AVL can spin forever on a geometry it cannot solve; the adapter never waits for it."""
    monkeypatch.setattr(avl_module, "AVL_MAX_RUN_S", 0.5)
    configure(fake, {"10": 0.14, "20": 0.14}, sleep=30)
    with pytest.raises(ToolRunTimeoutError) as raised:
        await neutral(fake)
    assert raised.value.limit_s == 0.5
    await asyncio.sleep(0.2)
    assert not alive(fake)


@pytest.mark.asyncio
async def test_a_time_budget_kills_a_running_avl(fake: Path) -> None:
    configure(fake, {"10": 0.14, "20": 0.14}, sleep=30)
    with pytest.raises(TimeoutError) as raised:
        async with asyncio.timeout(0.5):
            await neutral(fake)
    assert not isinstance(raised.value, ToolRunTimeoutError)  # the budget's, not the adapter's own
    await asyncio.sleep(0.2)
    assert not alive(fake)


def test_the_run_limit_is_far_above_the_measured_refined_run() -> None:
    """15 s measured for the refined 20/48 run of BRYAN and JAGUAR; BRYAN 20/96 fails fast."""
    assert avl_module.AVL_MAX_RUN_S >= 4 * 15


@pytest.mark.asyncio
async def test_a_refined_value_forward_of_the_declared_one_is_also_a_disagreement(
    fake: Path,
) -> None:
    """The delta is absolute: the refined neutral point 0.6 % MAC forward of the declared one warns."""
    configure(fake, {"10": 0.14, "20": 0.14 - 0.2 * 0.006})
    found = await neutral(fake)
    (warning,) = found.warnings
    assert warning.code == "avl_mesh_not_converged"
    assert warning.detail["delta_mac"] == pytest.approx(0.006, rel=1e-9)  # pyright: ignore[reportUnknownMemberType]


class SecondCallFails(FakeAvl):
    """The adapter whose refined (second) run raises ``failure``."""

    failure: Exception

    async def _run(self, *args: Any) -> AvlOutput:  # type: ignore[override]
        self.calls = getattr(self, "calls", 0) + 1
        if self.calls == 2:
            raise self.failure
        return await super()._run(*args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION, "unsupported_configuration", "m", "h"
        ),
        FormulaError(ErrorCategory.TOOL_UNAVAILABLE, "tool_unavailable", "m", "h"),
        ToolRunTimeoutError("the vortex lattice run", 120.0),
    ],
)
async def test_a_refined_run_that_fails_for_another_reason_propagates(
    fake: Path, failure: Exception
) -> None:
    """Only the array limit makes the refinement 'unchecked'; any other failure is the run's."""
    async with SolverRuntime() as runtime:
        adapter = SecondCallFails(runtime)
        adapter.failure = failure
        with pytest.raises(type(failure)) as raised:
            await adapter.neutral_point(airplane_with(*CONVENTIONAL), 0.5)
    assert raised.value is failure
