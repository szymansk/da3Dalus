"""The flaps of a configuration in AVL: mesh, file, commands, output and the steady roll (ch. 8.8, #1212).

The mesh, writer and parser tests need no tool; the adapter tests run the real ``run_process``
against a fake executable that echoes every control it was commanded.
"""

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
from aero_kernel.solvers.avl import AvlAdapter, AvlRoll, Contour
from aero_kernel.solvers.avl_mesh import FLAP_CONTROL, ROLL_CONTROL, MeshSurface, split_at_hinge
from aero_kernel.solvers.avl_writer import (
    avl_geometry,
    avl_roll_commands,
    control_order,
    parse_flap_echo,
    parse_roll_output,
)
from aero_kernel.tests.mesh_helpers import mesh_surfaces
from aero_kernel.tests.test_solvers_roll_devices import section

DELTA, FLAP = 20.0, 30.0


def device(role: str, root: float, tip: float, deflection: float | None = None) -> dict[str, Any]:
    return {
        "name": role,
        "role": role,
        "rel_chord_root": root,
        "rel_chord_tip": tip,
        "deflection_deg": deflection,
    }


def wing(
    devices: dict[int, dict[str, Any]], ys: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6)
) -> AirplaneGeometry:
    sections = [section(y, devices.get(index)) for index, y in enumerate(ys)]
    main = {"name": "Main", "surface_type": "main_wing", "symmetric": True, "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": main}})


def flapped_with_aileron(flap_hinge: float = 0.8, aileron_hinge: float = 0.8) -> AirplaneGeometry:
    """A flap on the first panel and an aileron on the second, meeting at y = 0.2 m."""
    return wing(
        {
            0: device("flap", flap_hinge, flap_hinge, FLAP),
            1: device("aileron", aileron_hinge, aileron_hinge),
        }
    )


def flaperon() -> AirplaneGeometry:
    return wing({1: device("flaperon", 0.78, 0.78, FLAP)})


def mesh(airplane: AirplaneGeometry, **drive: bool) -> tuple[MeshSurface, ...]:
    return mesh_surfaces(airplane, 12, lambda _a: 0, **drive)


def controlled_ys(surface: MeshSurface, name: str) -> list[float]:
    return [s.y for s in surface.sections if name in [c.name for c in s.controls()]]


def test_flap_stations_carry_the_flap_control_and_roll_stations_the_roll_control() -> None:
    (main, *_) = mesh(flapped_with_aileron(), drive_roll=True, drive_flaps=True)
    flap_ys = controlled_ys(main, FLAP_CONTROL)
    roll_ys = controlled_ys(main, ROLL_CONTROL)
    assert flap_ys[0] == 0.0
    assert math.isclose(flap_ys[-1], 0.2, abs_tol=1e-9)
    assert math.isclose(roll_ys[0], 0.2, abs_tol=1e-9)
    assert math.isclose(roll_ys[-1], 0.4, abs_tol=1e-9)
    junction = next(s for s in main.sections if math.isclose(s.y, 0.2, abs_tol=1e-9))
    assert [c.name for c in junction.controls()] == [ROLL_CONTROL, FLAP_CONTROL]


def test_the_ends_of_a_flap_are_stations() -> None:
    ys = [
        s.y for s in mesh(wing({1: device("flap", 0.8, 0.8, FLAP)}), drive_flaps=True)[0].sections
    ]
    assert any(math.isclose(y, 0.2, abs_tol=1e-9) for y in ys)
    assert any(math.isclose(y, 0.4, abs_tol=1e-9) for y in ys)


def test_a_flap_at_rest_is_no_flap_station_and_no_control() -> None:
    airplane = wing({1: device("flap", 0.8, 0.8, 0.0)})
    surfaces = mesh(airplane, drive_roll=True, drive_flaps=True)
    assert all(not s.controls() for s in surfaces[0].sections)


def test_the_flap_is_symmetric_and_the_roll_control_antisymmetric() -> None:
    (main, *_) = mesh(flapped_with_aileron(), drive_roll=True, drive_flaps=True)
    flap = next(c for s in main.sections for c in s.controls() if c.name == FLAP_CONTROL)
    roll = next(c for s in main.sections for c in s.controls() if c.name == ROLL_CONTROL)
    assert (flap.gain, flap.sgn_dup) == (1.0, 1)
    assert (roll.gain, roll.sgn_dup) == (-1.0, -1)


def test_a_flaperon_carries_both_controls_on_the_same_stations() -> None:
    (main, *_) = mesh(flaperon(), drive_roll=True, drive_flaps=True)
    assert controlled_ys(main, FLAP_CONTROL) == controlled_ys(main, ROLL_CONTROL)
    assert controlled_ys(main, FLAP_CONTROL)


def test_a_deflected_flap_off_the_main_wing_is_unsupported() -> None:
    main = {
        "name": "Main",
        "surface_type": "main_wing",
        "symmetric": True,
        "x_secs": [section(0.0), section(0.4)],
    }
    tail = {
        "name": "Tail",
        "surface_type": "horizontal_tail",
        "symmetric": True,
        "x_secs": [section(0.0, device("flap", 0.7, 0.7, FLAP)), section(0.2)],
    }
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": main, "Tail": tail}})
    with pytest.raises(FormulaError) as raised:
        mesh(airplane, drive_flaps=True)
    assert raised.value.code == "unsupported_layout"
    assert raised.value.detail["wing"] == "Tail"


def test_split_moves_a_hinge_that_differs_from_the_cut_measured_from_the_cut() -> None:
    airplane = flapped_with_aileron(flap_hinge=0.75, aileron_hinge=0.8)
    (main, *_) = mesh(airplane, drive_roll=True, drive_flaps=True)
    _, aft = split_at_hinge(main, (12, 8))
    junction = next(s for s in aft.sections if math.isclose(s.y, 0.2, abs_tol=1e-9))
    assert junction.flap is not None
    assert junction.control is not None
    assert junction.flap.x_hinge == 0.0  # the flap hinge is the cut (the more forward one)
    assert math.isclose(junction.control.x_hinge, (0.8 - 0.75) / (1.0 - 0.75), rel_tol=1e-9)


def test_split_with_equal_hinges_puts_every_control_at_the_aft_leading_edge() -> None:
    (main, *_) = mesh(flapped_with_aileron(), drive_roll=True, drive_flaps=True)
    front, aft = split_at_hinge(main, (12, 8))
    assert all(s.control is None and s.flap is None for s in front.sections)
    assert all(c.x_hinge == 0.0 for s in aft.sections for c in s.controls())


def test_the_control_order_is_the_order_of_first_appearance_in_the_file() -> None:
    (main, *_) = mesh(flapped_with_aileron(), drive_roll=True, drive_flaps=True)
    assert control_order([main]) == (FLAP_CONTROL, ROLL_CONTROL)
    (alone, *_) = mesh(flaperon(), drive_roll=True, drive_flaps=True)
    assert control_order([alone]) == (ROLL_CONTROL, FLAP_CONTROL)  # roll is written first
    assert control_order(mesh(flapped_with_aileron())) == ()


def test_the_file_writes_the_flap_symmetric_after_the_roll_control() -> None:
    (main, *_) = mesh(flaperon(), drive_roll=True, drive_flaps=True)
    text = avl_geometry([main], [1.0], n_chord=10, s_ref=0.2, c_ref=0.2, b_ref=1.2)
    lines = text.splitlines()
    first = lines.index("CONTROL")
    assert lines[first + 1].startswith("aileron -1.0")
    assert lines[first + 1].endswith(" -1")
    assert lines[first + 2] == "CONTROL"
    assert lines[first + 3].startswith("flap 1.0")
    assert lines[first + 3].endswith(" 1")


def test_commands_hold_the_flap_in_both_runs_and_zero_only_the_roll_control() -> None:
    text = avl_roll_commands(0.5, 0.25, DELTA, order=(FLAP_CONTROL, ROLL_CONTROL), flap_deg=FLAP)
    assert text == (
        "oper\no\nc\n0.25\n\na c 0.5\nr rm 0\nd1 d1 30.0\nd2 d2 20.0\nx\n"
        "r r 0\nd1 d1 30.0\nd2 d2 0\nx\nst\n\n\nquit\n"
    )


OUTPUT = """
  Alpha =   7.08055     pb/2V =   0.24217     p'b/2V =   0.24403
  CLtot =   0.80000
  Cl'tot =   0.00000
   flap            =  30.00000
   aileron         =  20.00000
 x' mom.  Cl'|    Clp =  -0.352014
 x' mom.  Cl'|   Cld01 =   0.001111
 x' mom.  Cl'|   Cld02 =   0.004929
"""


def test_the_roll_derivative_is_read_by_the_roll_controls_number() -> None:
    parsed = parse_roll_output(OUTPUT, roll_index=2)
    assert parsed is not None
    assert parsed.cl_delta == 0.004929
    assert parse_roll_output(OUTPUT, roll_index=1) is not None
    assert parse_roll_output(OUTPUT.replace("Cld02", "xxxxx"), roll_index=2) is None


def test_the_flap_echo_is_read_by_name() -> None:
    assert parse_flap_echo(OUTPUT) == 30.0
    assert parse_flap_echo(OUTPUT.replace("flap ", "xxxx ")) is None


SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
geometry = pathlib.Path(sys.argv[1]).read_text()
commands = sys.stdin.read()
n_chord = int(re.search(r"#Nchordwise  Cspace\\n(\\d+)", geometry).group(1))
cl = float(re.search(r"a c (\\S+)", commands).group(1))
order = []
for name in re.findall(r"^CONTROL\\n(\\S+) ", geometry, re.MULTILINE):
    if name not in order:
        order.append(name)
first = commands.split("\\nx\\n")[0]
values = {{order[int(i) - 1]: float(v) for i, v in re.findall(r"^d(\\d+) d\\1 (\\S+)$", first, re.MULTILINE)}}
(here / "seen.json").write_text(json.dumps({{"commands": commands, "geometry": geometry, "order": order}}))
delta = values.get("aileron", 0.0)
print("  Alpha =   7.08055     pb/2V =   0.99999     p'b/2V = %10.5f" % config["p_hat"][str(n_chord)])
print("  Cl'tot = %10.5f" % 0.0)
print("  CLtot = %10.5f" % cl)
for name in order:
    print("   %-15s = %12.5f" % (name, values[name] + config.get("echo_offset", {{}}).get(name, 0.0)))
print(" x' mom.  Cl'|    Clp = %10.6f    Clq =  -0.000000" % -0.35)
index = order.index("aileron") + 1
print(" x' mom.  Cl'|   Cld%02d = %10.6f" % (index, 0.0 if delta == 0.0 else config["p_hat"][str(n_chord)] * 0.35 / delta))
"""


class FakeAvl(AvlAdapter):
    def available(self) -> bool:
        return True

    async def _contours(self, airfoils: tuple[object, ...]) -> tuple[Contour, ...]:
        return tuple(
            Contour(coordinates=((1.0, 0.0), (0.0, 0.0), (1.0, 0.0)), claf=1.0924) for _ in airfoils
        )


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    configure(tmp_path)
    return tmp_path


def configure(directory: Path, **extra: object) -> None:
    (directory / "fake.json").write_text(json.dumps({"p_hat": {"12": 0.05, "24": 0.05}, **extra}))


async def roll(airplane: AirplaneGeometry, delta: float = DELTA) -> AvlRoll:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).steady_roll(airplane, 0.5, delta)


@pytest.mark.asyncio
async def test_a_flapped_steady_roll_commands_the_flap_and_the_aileron_by_their_numbers(
    fake: Path,
) -> None:
    found = await roll(flapped_with_aileron())
    assert math.isclose(found.p_hat, 0.05, rel_tol=1e-12)
    seen = json.loads((fake / "seen.json").read_text())
    assert seen["order"] == [FLAP_CONTROL, ROLL_CONTROL]
    assert "d1 d1 30.0\nd2 d2 20.0\nx\nr r 0\nd1 d1 30.0\nd2 d2 0\nx\n" in seen["commands"]


@pytest.mark.asyncio
async def test_a_flaperon_is_commanded_with_its_bias_and_the_aileron_on_top(fake: Path) -> None:
    await roll(flaperon())
    seen = json.loads((fake / "seen.json").read_text())
    assert seen["order"] == [ROLL_CONTROL, FLAP_CONTROL]
    assert "d1 d1 20.0\nd2 d2 30.0\nx\n" in seen["commands"]


@pytest.mark.asyncio
async def test_the_flap_is_declared_as_linearised_with_its_deflection(fake: Path) -> None:
    found = await roll(flapped_with_aileron())
    (warning,) = found.warnings
    assert (warning.code, warning.severity) == ("avl_flap_linearised", "practice")
    assert warning.detail == {"flaps": [{"wing": "Main", "device": "flap", "deflection_deg": FLAP}]}


@pytest.mark.asyncio
async def test_without_a_deflected_flap_there_is_no_flap_control_and_no_caveat(fake: Path) -> None:
    found = await roll(wing({1: device("aileron", 0.8, 0.8)}))
    assert found.warnings == ()
    seen = json.loads((fake / "seen.json").read_text())
    assert seen["order"] == [ROLL_CONTROL]
    assert "d2" not in seen["commands"]


@pytest.mark.asyncio
async def test_a_flap_echoed_at_another_angle_is_internal(fake: Path) -> None:
    configure(fake, echo_offset={FLAP_CONTROL: 0.5})
    airplane = flapped_with_aileron()
    with pytest.raises(RuntimeError, match="echoed the flap"):
        await roll(airplane)


@pytest.mark.asyncio
async def test_flaps_at_different_angles_are_unsupported(fake: Path) -> None:
    airplane = wing(
        {
            0: device("flap", 0.8, 0.8, 10.0),
            1: device("flap", 0.8, 0.8, 20.0),
            2: device("aileron", 0.8, 0.8),
        }
    )
    with pytest.raises(FormulaError) as raised:
        await roll(airplane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "flap_deflections_differ"
    assert not (fake / "seen.json").exists()


@pytest.mark.asyncio
async def test_a_deflected_non_flap_device_is_still_refused(fake: Path) -> None:
    deflected = wing({1: device("aileron", 0.8, 0.8, 3.0)})
    with pytest.raises(FormulaError) as raised:
        await roll(deflected)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert not (fake / "seen.json").exists()
