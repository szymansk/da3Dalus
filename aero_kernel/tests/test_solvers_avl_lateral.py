"""The AVL lateral derivatives against a fake executable through the real ``run_process`` (fast tier)."""

import json
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers.avl import AvlAdapter, AvlLateral, Contour
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with
from aero_kernel.tests.test_solvers_avl_flap import FLAP, device, wing

SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
geometry = pathlib.Path(sys.argv[1]).read_text()
commands = sys.stdin.read()
cl = float(re.search(r"a c (\\S+)", commands).group(1))
order = []
for name in re.findall(r"^CONTROL\\n(\\S+) ", geometry, re.MULTILINE):
    if name not in order:
        order.append(name)
first = commands.split("\\nx\\n")[0]
values = {{order[int(i) - 1]: float(v) for i, v in re.findall(r"^d(\\d+) d\\1 (\\S+)$", first, re.MULTILINE)}}
(here / "seen.json").write_text(json.dumps({{"commands": commands, "geometry": geometry}}))
if config.get("silent"):
    print(" nothing useful")
    sys.exit(0)
print("  CLtot = %10.5f" % (cl + config.get("cl_offset", 0.0)))
for name in ([] if config.get("no_echo") else order):
    print("   %-15s = %12.5f" % (name, values[name] + config.get("echo_offset", 0.0)))
print(" x' mom.  Cl'|    Cla =  -0.000000    Clb = %10.6f" % -0.05)
print(" z' mom.  Cn'|    Cna =  -0.000000    Cnb = %10.6f" % 0.07)
print(" x' mom.  Cl'|    Clp = %10.6f    Clq =  -0.000000    Clr = %10.6f" % (-0.55, 0.11))
print(" z' mom.  Cn'|    Cnp = %10.6f    Cnq =   0.000000    Cnr = %10.6f" % (-0.04, -0.06))
"""


class FakeAvl(AvlAdapter):
    """The adapter with AeroSandbox's contour work replaced and availability assumed."""

    def available(self) -> bool:
        return True

    async def _contours(self, airfoils: tuple[object, ...]) -> tuple[Contour, ...]:
        return tuple(
            Contour(coordinates=((1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), claf=1.0924) for _ in airfoils
        )


def with_fuselage() -> AirplaneGeometry:
    dumped: dict[str, Any] = airplane_with(*CONVENTIONAL).model_dump(mode="json")
    dumped["xyz_ref"] = [0.05, 0.0, 0.01]
    dumped["fuselages"] = {
        "Rumpf": {
            "name": "Rumpf",
            "x_secs": [
                {"xyz": [0.0, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
                {"xyz": [0.3, 0.0, 0.0], "a": 0.02, "b": 0.02, "n": 2.0},
                {"xyz": [0.7, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
            ],
        }
    }
    return AirplaneGeometry.model_validate(dumped)


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    (tmp_path / "fake.json").write_text(json.dumps({}))
    return tmp_path


async def lateral(
    airplane: AirplaneGeometry | None = None, cl: float = 0.6, x_cg: float = 0.12
) -> AvlLateral:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).lateral_derivatives(
            airplane or airplane_with(*CONVENTIONAL), cl, x_cg
        )


@pytest.mark.asyncio
async def test_the_six_derivatives_are_read_and_no_body_means_no_warning(fake: Path) -> None:
    found = await lateral()
    assert (found.c_l_beta, found.c_n_beta) == (-0.05, 0.07)
    assert (found.c_l_p, found.c_n_p, found.c_l_r, found.c_n_r) == (-0.55, -0.04, 0.11, -0.06)
    assert found.warnings == ()


@pytest.mark.asyncio
async def test_one_run_at_the_lift_coefficient_with_the_moment_reference_at_the_cg(
    fake: Path,
) -> None:
    await lateral(with_fuselage(), cl=0.62, x_cg=0.12)
    seen = json.loads((fake / "seen.json").read_text())
    assert "a c 0.62\nx\nst\n" in seen["commands"]
    lines = seen["geometry"].splitlines()
    # x_cg replaces the x of the airplane's reference point; its y and z stay
    assert lines[lines.index("#Xref    Yref    Zref") + 1] == "0.12 0.0 0.01"
    assert "BODY" in lines
    assert "BFIL" in lines


@pytest.mark.asyncio
async def test_a_fuselage_is_declared_as_a_round_body_of_equal_area(fake: Path) -> None:
    (warning,) = (await lateral(with_fuselage())).warnings
    assert warning.code == "avl_body_equivalent_round"
    assert warning.severity is WarningSeverity.PRACTICE
    assert warning.detail["bodies"] == [{"fuselage": "Rumpf", "axis_offset_m": 0.0, "sections": 3}]


@pytest.mark.asyncio
async def test_an_output_without_derivatives_is_a_defect_of_ours(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"silent": True}))
    with pytest.raises(RuntimeError, match="no lateral derivatives"):
        await lateral()


@pytest.mark.asyncio
async def test_a_missed_lift_coefficient_is_a_defect_of_ours(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"cl_offset": 0.01}))
    with pytest.raises(RuntimeError, match="trimmed to C_L"):
        await lateral()


@pytest.mark.asyncio
async def test_a_deflected_device_is_refused() -> None:
    from aero_kernel.tests.test_solvers_roll_devices import aileron, wing_geometry

    deflected = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.78, 0.80, deflection_deg=4.0))
    async with SolverRuntime() as runtime:
        adapter = FakeAvl(runtime)
        with pytest.raises(FormulaError) as raised:
            await adapter.lateral_derivatives(deflected, 0.5, 0.1)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def flapped() -> AirplaneGeometry:
    """A flap on the second panel, deflected to the landing angle of the fleet."""
    return wing({1: device("flap", 0.8, 0.8, FLAP)})


@pytest.mark.asyncio
async def test_a_deflected_flap_is_held_by_the_flap_control_and_declared(fake: Path) -> None:
    found = await lateral(flapped())
    seen = json.loads((fake / "seen.json").read_text())
    assert f"a c 0.6\nd1 d1 {FLAP}\nx\nst\n" in seen["commands"]
    assert "CONTROL" in seen["geometry"].splitlines()
    assert [w.code for w in found.warnings] == ["avl_flap_linearised"]
    assert (found.c_l_beta, found.c_n_beta) == (-0.05, 0.07)


@pytest.mark.asyncio
async def test_a_flap_echoed_at_another_angle_is_a_defect_of_ours(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"echo_offset": 0.5}))
    with pytest.raises(RuntimeError, match="echoed the flap"):
        await lateral(flapped())


@pytest.mark.asyncio
async def test_a_flap_without_an_echo_is_a_defect_of_ours(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"no_echo": True}))
    with pytest.raises(RuntimeError, match="echoed the flap at None"):
        await lateral(flapped())
