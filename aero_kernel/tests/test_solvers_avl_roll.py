"""The AVL steady roll against a fake executable through the real ``run_process`` (fast tier)."""

import json
import math
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers.avl import AvlAdapter, AvlRoll, Contour
from aero_kernel.tests.test_solvers_roll_devices import aileron, wing_geometry

SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
geometry = pathlib.Path(sys.argv[1]).read_text()
commands = sys.stdin.read()
n_chord = int(re.search(r"#Nchordwise  Cspace\\n(\\d+)", geometry).group(1))
cl = float(re.search(r"a c (\\S+)", commands).group(1))
delta = float(re.search(r"d1 d1 (\\S+)", commands).group(1))
(here / "seen.json").write_text(json.dumps({{"n_chord": n_chord, "commands": commands, "geometry": geometry}}))
if str(n_chord) in config.get("overflow", []):
    print(config.get("overflow_message", " SDUPL: Vortex array overflow. Increase NVMAX currently"))
    sys.exit(0)
if "p_hat" not in config:
    print(" nothing useful")
    sys.exit(0)
print("  Alpha =   7.08055     pb/2V =   0.99999     p'b/2V = %10.5f" % config["p_hat"][str(n_chord)])
print("  CXtot =   0.07226     Cltot =   0.00385     Cl'tot = %10.5f" % config.get("cl_stab", 0.0))
print("  CLtot = %10.5f" % (cl + config.get("cl_offset", 0.0)))
print("   aileron         = %12.5f" % (delta + config.get("echo_offset", 0.0)))
linear = config["p_hat"][str(n_chord)] * config.get("linear_ratio", 1.0)
print(" x' mom.  Cl'|    Clp = %10.6f    Clq =  -0.000000" % -0.35)
print(" x' mom.  Cl'|   Cld01 = %10.6f" % (0.0 if delta == 0.0 else linear * 0.35 / delta))
"""

DELTA = 20.0


class FakeAvl(AvlAdapter):
    """The adapter with AeroSandbox's contour work replaced and availability assumed."""

    def available(self) -> bool:
        return True

    async def _contours(self, airfoils: tuple[object, ...]) -> tuple[Contour, ...]:
        return tuple(
            Contour(coordinates=((1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), claf=1.0924) for _ in airfoils
        )


def rolling_airplane() -> AirplaneGeometry:
    document = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.78, 0.80)).model_dump(
        mode="json", exclude_none=True
    )
    document["xyz_ref"] = [0.05, 0.0, 0.01]
    return AirplaneGeometry.model_validate(document)


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    configure(tmp_path, {"12": 0.05, "24": 0.05})
    return tmp_path


def configure(directory: Path, p_hat: dict[str, float], **extra: object) -> None:
    (directory / "fake.json").write_text(json.dumps({"p_hat": p_hat, **extra}))


async def roll(
    airplane: AirplaneGeometry | None = None, cl: float = 0.5, delta: float = DELTA
) -> AvlRoll:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).steady_roll(airplane or rolling_airplane(), cl, delta)


@pytest.mark.asyncio
async def test_the_declared_meshs_value_is_returned_without_warning_when_the_meshes_agree(
    fake: Path,
) -> None:
    found = await roll()
    assert found.p_hat == 0.05
    assert found.warnings == ()


@pytest.mark.asyncio
async def test_roll_file_and_commands_reach_avl(fake: Path) -> None:
    """The last run is the refined one: its file has the controls and the airplane's reference point,
    its commands constrain C_L and the rolling moment and set d1."""
    await roll(cl=0.62, delta=-12.5)
    seen = json.loads((fake / "seen.json").read_text())
    assert seen["n_chord"] == 24
    assert "a c 0.62\nr rm 0\nd1 d1 -12.5\nx\n" in seen["commands"]
    lines = seen["geometry"].splitlines()
    assert lines[lines.index("#Xref    Yref    Zref") + 1] == "0.05 0.0 0.01"
    assert "CONTROL" in lines


@pytest.mark.asyncio
async def test_a_disagreement_above_one_percent_is_a_defect_warning_with_both_values(
    fake: Path,
) -> None:
    configure(fake, {"12": 0.05, "24": 0.05 * 1.012})
    found = await roll()
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == ("avl_mesh_not_converged", WarningSeverity.DEFECT)
    assert warning.detail["p_hat_declared"] == 0.05
    assert warning.detail["p_hat_refined"] == pytest.approx(0.0506, abs=1e-9)  # pyright: ignore[reportUnknownMemberType]
    assert found.p_hat == 0.05


@pytest.mark.asyncio
async def test_roll_refinement_warning_and_unchecked(fake: Path) -> None:
    configure(fake, {"12": 0.05, "24": 0.05 * 1.009})
    assert (await roll()).warnings == ()
    configure(fake, {"12": 0.05}, overflow=["24"])
    found = await roll()
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == ("avl_refinement_unchecked", WarningSeverity.DEFECT)
    assert found.p_hat == 0.05


@pytest.mark.asyncio
async def test_roll_beyond_primer_range_is_defect_warning(fake: Path) -> None:
    configure(fake, {"12": 0.276, "24": 0.276})
    found = await roll()
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == (
        "avl_roll_rate_beyond_range",
        WarningSeverity.DEFECT,
    )
    assert warning.detail == {"p_hat": 0.276, "limit": 0.10}
    assert found.p_hat == 0.276  # a value with a caveat, never clipped


@pytest.mark.asyncio
async def test_a_negative_roll_beyond_the_range_warns_too(fake: Path) -> None:
    configure(fake, {"12": -0.15, "24": -0.15})
    assert [w.code for w in (await roll(delta=-DELTA)).warnings] == ["avl_roll_rate_beyond_range"]


@pytest.mark.asyncio
async def test_roll_moment_not_zero_is_internal(fake: Path) -> None:
    configure(fake, {"12": 0.05, "24": 0.05}, cl_stab=0.001)
    with pytest.raises(RuntimeError, match="rolling moment"):
        await roll()


@pytest.mark.asyncio
async def test_cl_mismatch_is_internal(fake: Path) -> None:
    configure(fake, {"12": 0.05, "24": 0.05}, cl_offset=0.01)
    with pytest.raises(RuntimeError, match="not the requested"):
        await roll()


@pytest.mark.asyncio
async def test_control_echo_mismatch_is_internal(fake: Path) -> None:
    configure(fake, {"12": 0.05, "24": 0.05}, echo_offset=0.5)
    with pytest.raises(RuntimeError, match="echoed the control"):
        await roll()


@pytest.mark.asyncio
async def test_an_output_without_the_roll_is_internal(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({}))
    with pytest.raises(RuntimeError, match="did not complete"):
        await roll()


@pytest.mark.asyncio
async def test_a_declared_mesh_that_overflows_is_an_array_limit_error(fake: Path) -> None:
    configure(fake, {}, overflow=["12"])
    with pytest.raises(FormulaError) as raised:
        await roll()
    assert raised.value.code == "avl_array_limit"


@pytest.mark.asyncio
async def test_roll_device_on_unmirrored_surface_is_unsupported(fake: Path) -> None:
    plane = wing_geometry((0.0, 0.2, 0.4), 1, symmetric=False)
    with pytest.raises(FormulaError) as raised:
        await roll(plane)
    assert raised.value.code == "roll_device_on_unmirrored_surface"
    assert not (fake / "seen.json").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("on_device", [True, False])
async def test_deflected_geometry_state_still_refused(fake: Path, on_device: bool) -> None:
    plane = wing_geometry(
        (0.0, 0.2, 0.4),
        1,
        aileron(deflection_deg=3.0) if on_device else aileron(),
        surface_deflection=None if on_device else 2.0,
    )
    with pytest.raises(FormulaError) as raised:
        await roll(plane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "not yet passed to AVL" in raised.value.message
    assert not (fake / "seen.json").exists()


@pytest.mark.asyncio
async def test_a_discontinuous_hinge_of_a_driven_device_is_unsupported(fake: Path) -> None:
    document = wing_geometry((0.0, 0.2, 0.4, 0.6), 1, aileron(0.75, 0.78)).model_dump(
        mode="json", exclude_none=True
    )
    document["wings"]["Main"]["x_secs"][2]["trailing_edge_device"] = {
        "name": "Querruder",
        "role": "aileron",
        "rel_chord_root": 0.70,
        "rel_chord_tip": 0.80,
    }
    with pytest.raises(FormulaError) as raised:
        await roll(AirplaneGeometry.model_validate(document))
    assert raised.value.code == "hinge_line_discontinuous"


@pytest.mark.asyncio
async def test_an_airplane_without_a_roll_device_is_a_defect_of_the_caller(fake: Path) -> None:
    plane = wing_geometry((0.0, 0.2, 0.4), None)
    with pytest.raises(ValueError, match="device acting as aileron"):
        await roll(plane)


@pytest.mark.asyncio
@pytest.mark.parametrize("delta", [float("nan"), float("inf")])
async def test_a_non_finite_command_is_invalid_input(fake: Path, delta: float) -> None:
    with pytest.raises(FormulaError) as raised:
        await roll(delta=delta)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


def test_roll_settings_public_keys() -> None:
    settings: dict[str, Any] = AvlAdapter(SolverRuntime()).settings()
    assert settings["avl_roll_refinement_tolerance"] == 0.01
    assert (settings["avl_roll_nchord_front"], settings["avl_roll_nchord_aft"]) == (12, 8)
    assert settings["avl_roll_branch_tolerance"] == 0.10


@pytest.mark.asyncio
async def test_the_wing_reaches_avl_as_a_front_and_an_aft_surface(fake: Path) -> None:
    """Declared mesh: front 12, aft 8 chordwise vortices; the last (refined) run doubles both."""
    await roll()
    geometry = json.loads((fake / "seen.json").read_text())["geometry"]
    lines = geometry.splitlines()
    names = [lines[i + 1] for i, line in enumerate(lines) if line == "SURFACE"]
    counts = [lines[i + 1] for i, line in enumerate(lines) if line == "#Nchordwise  Cspace"]
    assert names == ["Main front", "Main aft"]
    assert counts == ["24   1", "16   1"]


@pytest.mark.asyncio
async def test_more_than_fifty_chordwise_vortices_on_one_surface_are_refused(
    fake: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AVL's KCMAX: above 50 it prints an array overflow and returns a zero roll without an error."""
    monkeypatch.setattr("aero_kernel.solvers.avl.SPLIT_N_CHORD", (51, 8))
    with pytest.raises(FormulaError) as raised:
        await roll()
    assert raised.value.code == "avl_array_limit"
    assert raised.value.detail["n_chord"] == 51


@pytest.mark.asyncio
async def test_a_refined_mesh_beyond_fifty_is_unchecked_not_wrong(
    fake: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("aero_kernel.solvers.avl.SPLIT_N_CHORD", (26, 8))
    configure(fake, {"26": 0.05})
    found = await roll()
    assert found.p_hat == 0.05
    assert [w.code for w in found.warnings] == ["avl_refinement_unchecked"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        " SDUPL: Strip array overflow. Increase NSMAX currently          500",
        " SDUPL: Surface array overflow. Increase NFMAX currently          100",
    ],
)
async def test_a_strip_or_surface_overflow_is_an_array_limit_too(fake: Path, message: str) -> None:
    """AVL stops at 500 strips (NSMAX) and 100 surfaces (NFMAX) with only this message: without the
    marker the refined run would be an internal error instead of an unchecked refinement."""
    configure(fake, {"12": 0.05}, overflow=["24"], overflow_message=message)
    found = await roll()
    assert [w.code for w in found.warnings] == ["avl_refinement_unchecked"]


@pytest.mark.asyncio
async def test_a_trimmed_roll_far_from_the_linear_response_is_a_branch_inconsistency(
    fake: Path,
) -> None:
    """BRYAN at 96 spanwise strips: AVL's Newton step lands on a spurious branch (p'b/2V 0.82491,
    alpha 10.8 deg) while its derivatives at the state without roll (Clp -0.190612, Cld01 0.003311,
    a linear response of 0.3474) are not wrong by that factor. Every other check of the run passes."""
    configure(fake, {"12": 0.82491, "24": 0.82491}, linear_ratio=0.3474 / 0.82491)
    with pytest.raises(FormulaError) as raised:
        await roll()
    assert raised.value.code == "avl_roll_branch_inconsistent"
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["p_hat"] == 0.82491
    assert math.isclose(float(raised.value.detail["p_hat_linear"]), 0.3474, abs_tol=2e-4)  # pyright: ignore[reportArgumentType]


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", [0.93, 1.07])
async def test_a_nonlinearity_within_ten_percent_is_accepted(fake: Path, ratio: float) -> None:
    configure(fake, {"12": 0.276, "24": 0.276}, linear_ratio=ratio)
    found = await roll()
    assert found.p_hat == 0.276


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "value"),
    [("AVL_MAX_STRIPS", 10), ("AVL_MAX_VORTICES", 100), ("AVL_MAX_SURFACES", 3)],
)
async def test_a_lattice_beyond_a_fixed_array_is_counted_before_it_is_written(
    fake: Path, monkeypatch: pytest.MonkeyPatch, limit: str, value: int
) -> None:
    """AVL stops at 500 strips, 6000 vortices and 100 surfaces (mirror images included) and some
    overflows do not even print a message, so the adapter counts first: here the declared mesh."""
    monkeypatch.setattr(f"aero_kernel.solvers.avl.{limit}", value)
    with pytest.raises(FormulaError) as raised:
        await roll()
    assert raised.value.code == "avl_array_limit"
    # 24 strips on each of the two pieces, mirrored; 12 and 8 chordwise vortices
    assert raised.value.detail["strips"] == 96
    assert raised.value.detail["vortices"] == 24 * 2 * 12 + 24 * 2 * 8
