"""The AVL hinge moments against a fake executable through the real ``run_process`` (fast tier)."""

import json
import math
import stat
import sys
from pathlib import Path

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import avl as avl_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.avl import AvlAdapter, AvlHinge, Contour
from aero_kernel.solvers.regime import SurfaceSections
from aero_kernel.tests.hinge_builders import conventional, device

# A fake AVL: it echoes every driven control and prints a hinge moment of 0.01 per degree of the
# control, in AVL's table format; the file it was given is kept for the tests to read.
SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
geometry = pathlib.Path(sys.argv[1]).read_text()
commands = sys.stdin.read()
(here / "seen.json").write_text(json.dumps({{"commands": commands, "geometry": geometry}}))
cl = float(re.search(r"a c (\\S+)", commands).group(1)) + config.get("cl_offset", 0.0)
driven = re.findall(r"^d(\\d+) d\\d+ (\\S+)$", commands, re.MULTILINE)
names = []
for line in geometry.splitlines():
    if re.fullmatch(r"c\\d\\d .*", line) and line.split()[0] not in names:
        names.append(line.split()[0])
if config.get("silent"):
    print(" nothing useful")
    sys.exit(0)
print("  CLtot = %10.5f" % cl)
for index, value in driven:
    print("   %s         = %12.5f" % (names[int(index) - 1], float(value) + config.get("echo_offset", 0.0)))
print(" Control Hinge Moments")
print(" (referred to    Sref =  0.1600     Cref =    0.2000)")
print(" Control          Chinge")
print(" ---------------- -----------")
for index, value in driven:
    print(" %-16s%12.4E" % (names[int(index) - 1], 0.01 * float(value)))
"""

AIR = AirState(density=1.225, dynamic_viscosity=1.8e-5, speed_of_sound=340.0)
REFERENCE = MainWingProperties(s_ref=0.16, c_mac=0.2, b_ref=0.8)


class FakeAvl(AvlAdapter):
    """The adapter with AeroSandbox's contour work replaced and availability assumed."""

    def available(self) -> bool:
        return True

    async def _contours(self, airfoils: tuple[object, ...]) -> tuple[Contour, ...]:
        return tuple(
            Contour(coordinates=((1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), claf=1.0924) for _ in airfoils
        )


def reference_of(_airplane: AirplaneGeometry) -> MainWingProperties:
    """The fixed reference values, standing in for AeroSandbox's."""
    return REFERENCE


def sections_of(airplane: AirplaneGeometry) -> dict[str, SurfaceSections]:
    """The sections of every wing with a fixed mean chord, standing in for AeroSandbox's."""
    return {key: SurfaceSections.of(wing, 0.1) for key, wing in (airplane.wings or {}).items()}


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    monkeypatch.setattr(avl_module, "main_wing_properties", reference_of)
    monkeypatch.setattr(avl_module, "surface_sections", sections_of)
    (tmp_path / "fake.json").write_text(json.dumps({}))
    return tmp_path


async def hinge(
    airplane: AirplaneGeometry | None = None,
    role: str = "aileron",
    delta: float = 10.0,
    speed: float = 20.0,
) -> AvlHinge:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).hinge_moments(
            airplane or conventional(),
            cl=0.5,
            role=role,
            delta_deg=delta,
            speed_ms=speed,
            air=AIR,
        )


def seen(directory: Path) -> dict[str, str]:
    return json.loads((directory / "seen.json").read_text())


@pytest.mark.asyncio
async def test_the_moment_is_q_sref_cref_times_the_coefficient_with_the_sign_of_the_side(
    fake: Path,
) -> None:
    """A positive aileron command deflects the right half by -10 deg and the left by +10 deg; the
    fake answers 0.01 per degree, and H = q S_ref c_ref C_hinge with q = 0.5 * 1.225 * 20^2."""
    found = await hinge()
    scale = 0.5 * 1.225 * 20.0**2 * 0.16 * 0.2
    assert set(found.moments) == {"Main wing.aileron_right", "Main wing.aileron_left"}
    assert math.isclose(found.moments["Main wing.aileron_right"], scale * -0.1, rel_tol=1e-4)
    assert math.isclose(found.moments["Main wing.aileron_left"], scale * 0.1, rel_tol=1e-4)


@pytest.mark.asyncio
async def test_the_dialogue_constrains_cl_only_and_drives_every_control_of_the_role(
    fake: Path,
) -> None:
    await hinge()
    commands = seen(fake)["commands"]
    assert "a c 0.5\n" in commands
    assert "d1 d1 -10.0\nd2 d2 10.0\n" in commands
    assert "x\nhm\n" in commands
    assert "r rm" not in commands


@pytest.mark.asyncio
async def test_a_deflected_surface_changes_the_hinge_moment(fake: Path) -> None:
    """The deflection reaches AVL: the moment scales with it and vanishes at zero."""
    half, full, none = await hinge(delta=5.0), await hinge(delta=10.0), await hinge(delta=0.0)
    key = "Main wing.aileron_left"
    assert math.isclose(full.moments[key], 2.0 * half.moments[key], rel_tol=1e-4)
    assert none.moments[key] == 0.0


@pytest.mark.asyncio
async def test_the_moment_scales_with_the_dynamic_pressure(fake: Path) -> None:
    slow, fast = await hinge(speed=10.0), await hinge(speed=20.0)
    key = "Main wing.aileron_left"
    assert math.isclose(fast.moments[key], 4.0 * slow.moments[key], rel_tol=1e-4)


@pytest.mark.asyncio
async def test_every_wing_is_in_the_file_and_the_halves_are_explicit(fake: Path) -> None:
    await hinge(role="elevator")
    geometry = seen(fake)["geometry"]
    assert "YDUPLICATE" not in geometry
    for name in ("Main wing right", "Main wing left", "Tail right front", "Tail left aft", "Fin"):
        assert f"SURFACE\n{name}\n" in geometry
    # the keys never reach AVL: only the internal control names do
    assert "elevator" not in geometry


@pytest.mark.asyncio
async def test_the_regime_warnings_of_the_flow_are_returned(fake: Path) -> None:
    """At 1 m/s the Reynolds number of every surface is below the band: the check ran."""
    found = await hinge(speed=1.0)
    assert {w.code for w in found.warnings} >= {"reynolds_outside_band"}
    assert {w.code for w in (await hinge(speed=20.0)).warnings}.isdisjoint(
        {"reynolds_outside_band"}
    )


@pytest.mark.asyncio
async def test_a_role_without_a_control_surface_is_a_declared_refusal(fake: Path) -> None:
    """The conditions of the canon look at every rib; only a device on a segment is a surface."""
    async with SolverRuntime() as runtime:
        with pytest.raises(FormulaError) as raised:
            await FakeAvl(runtime).hinge_moments(
                conventional(), cl=0.5, role="flap", delta_deg=1.0, speed_ms=20.0, air=AIR
            )
    assert raised.value.code == "no_control_in_role"
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


@pytest.mark.asyncio
async def test_a_non_finite_deflection_is_refused(fake: Path) -> None:
    with pytest.raises(FormulaError) as raised:
        await hinge(delta=math.inf)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


@pytest.mark.asyncio
async def test_a_deflected_geometry_state_is_refused(fake: Path) -> None:
    plane = conventional(main={1: device("aileron", "aileron", 0.75, deflection_deg=5.0)})
    with pytest.raises(FormulaError) as raised:
        await hinge(plane)
    assert raised.value.code == "unsupported_configuration"


@pytest.mark.asyncio
async def test_an_output_that_is_not_understood_is_a_defect(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"silent": True}))
    with pytest.raises(RuntimeError, match="no hinge moments"):
        await hinge()


@pytest.mark.asyncio
async def test_a_missed_lift_coefficient_is_a_defect(fake: Path) -> None:
    (fake / "fake.json").write_text(json.dumps({"cl_offset": 0.01}))
    with pytest.raises(RuntimeError, match="trimmed to C_L"):
        await hinge()


@pytest.mark.asyncio
async def test_an_echoed_control_that_differs_from_the_commanded_one_is_a_defect(
    fake: Path,
) -> None:
    (fake / "fake.json").write_text(json.dumps({"echo_offset": 0.5}))
    with pytest.raises(RuntimeError, match="echoed a control"):
        await hinge()


def with_fuselage() -> AirplaneGeometry:
    """The conventional airplane with a fuselage of three sections."""
    dumped = conventional().model_dump(mode="json", exclude_none=True)
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


@pytest.mark.asyncio
async def test_the_fuselage_is_in_the_run_as_in_the_lateral_run_and_declared(fake: Path) -> None:
    found = await hinge(with_fuselage(), role="elevator")
    assert "BODY\nRumpf\n" in seen(fake)["geometry"]
    assert "avl_body_equivalent_round" in [w.code for w in found.warnings]


@pytest.mark.asyncio
async def test_an_airplane_without_a_fuselage_has_no_body_in_the_file(fake: Path) -> None:
    await hinge(role="elevator")
    assert "BODY" not in seen(fake)["geometry"]


@pytest.mark.asyncio
async def test_the_file_carries_the_reference_area_chord_and_span_in_that_order(fake: Path) -> None:
    """The hinge moment is q S_ref c_ref C_hinge with the references the AVL file carries. The
    three values are distinct (S 0.16 m^2, c 0.2 m, b 0.8 m), so any swap of two fails."""
    await hinge()
    lines = seen(fake)["geometry"].splitlines()
    assert lines[lines.index("#Sref    Cref    Bref") + 1] == "0.16 0.2 0.8"
