"""The AVL adapter's spanwise loads against a fake executable through the real ``run_process`` (fast tier)."""

import json
import math
import stat
import sys
from pathlib import Path

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.avl import AvlLoads
from aero_kernel.tests.formula_builders import all_near
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with
from aero_kernel.tests.solver_builders import airplane
from aero_kernel.tests.test_avl_writer_loads import SHEAR_MOMENT, STRIPS
from aero_kernel.tests.test_solvers_avl import FakeAvl

pytestmark = pytest.mark.asyncio

# The fake writes the two files the dialogue asks for (``fs <name>``, ``vm <name>``) from fake.json.
SCRIPT = """#!{python}
import json, pathlib, re, sys
here = pathlib.Path(__file__).resolve().parent
config = json.loads((here / "fake.json").read_text())
commands = sys.stdin.read()
(here / "seen.json").write_text(json.dumps({{"commands": commands}}))
for key in ("fs", "vm"):
    name = re.search(rf"^{{key}} (\\S+)$", commands, re.MULTILINE).group(1)
    if key in config:
        pathlib.Path(name).write_text(config[key])
print(" CLtot = 0.60000")
sys.exit(0)
"""
TRIMMED_CL = 0.6


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_avl"
    script.write_text(SCRIPT.format(python=sys.executable))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("avl_binary.avl_path", lambda: script, raising=False)
    configure(tmp_path, STRIPS, SHEAR_MOMENT)
    return tmp_path


def configure(directory: Path, strips: str | None, shear_moment: str | None) -> None:
    config = {key: text for key, text in (("fs", strips), ("vm", shear_moment)) if text is not None}
    (directory / "fake.json").write_text(json.dumps(config))


async def loads(cl: float = TRIMMED_CL, types: tuple[str, ...] = CONVENTIONAL) -> AvlLoads:
    async with SolverRuntime() as runtime:
        return await FakeAvl(runtime).spanwise_loads(airplane_with(*types), cl)


async def test_the_rows_of_the_first_surface_come_back_in_metres_per_dynamic_pressure(
    fake: Path,
) -> None:
    found = await loads()
    assert found.y_strip == (0.0146, 0.0437, 0.0729)
    assert found.c_cl == (0.1392, 0.1391, 0.1389)
    assert found.y_station[0] == 0.0
    assert found.warnings == ()
    # the airplane's references (S 0.28 m^2, b 1.4 m: half span 0.7 m, chord 0.2 m) undo the
    # normalisations; the hand values are those of test_avl_writer_loads.py: y = (2Y/Bref) Bref/2,
    # V/q = Vz/(q Sref) Sref, M/q = Mx/(q Bref Sref) Bref Sref (a swap of Sref and Bref fails all)
    assert all_near(found.y_station, (0.0, 0.0208 * 0.7, 0.7), 1e-12)
    assert math.isclose(found.shear[0], 0.298353 * 0.28, rel_tol=1e-9)
    assert math.isclose(found.moment[0], 0.0669065 * 0.28 * 1.4, rel_tol=1e-9)


async def test_the_run_is_one_solution_at_the_lift_coefficient_asked_for(fake: Path) -> None:
    await loads()
    commands = json.loads((fake / "seen.json").read_text())["commands"]
    assert "a c 0.6\n" in commands
    assert "fs strips.txt\nvm shearmoment.txt\n" in commands


async def test_a_run_that_trimmed_to_another_lift_coefficient_is_a_defect(fake: Path) -> None:
    with pytest.raises(RuntimeError, match=r"trimmed to C_L 0\.6, not the requested 0\.8"):
        await loads(cl=0.8)


async def test_a_missing_file_is_a_run_that_did_not_complete(fake: Path) -> None:
    configure(fake, STRIPS, None)
    with pytest.raises(RuntimeError, match="did not complete"):
        await loads()


async def test_a_table_that_does_not_start_at_the_centreline_is_a_defect(fake: Path) -> None:
    configure(fake, STRIPS, SHEAR_MOMENT.replace("    0.0000  0.298353", "    0.0500  0.298353"))
    with pytest.raises(RuntimeError, match="not the centreline"):
        await loads()


async def test_a_main_wing_that_is_not_mirrored_is_refused(fake: Path) -> None:
    one = airplane_with("main_wing")
    ((key, wing),) = (one.wings or {}).items()
    asymmetric = one.model_copy(
        update={"wings": {key: wing.model_copy(update={"symmetric": False})}}
    )
    async with SolverRuntime() as runtime:
        with pytest.raises(FormulaError) as caught:
            await FakeAvl(runtime).spanwise_loads(asymmetric, TRIMMED_CL)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "not mirrored" in caught.value.message
    assert not (fake / "seen.json").exists()  # AVL was never started


@pytest.mark.parametrize(("role", "deflection"), [("flap", 30.0), ("aileron", -5.0)])
async def test_a_deflected_control_surface_is_refused_the_controls_are_undeflected(
    fake: Path, role: str, deflection: float
) -> None:
    deflected = airplane(device=(role, deflection))
    async with SolverRuntime() as runtime:
        with pytest.raises(FormulaError) as caught:
            await FakeAvl(runtime).spanwise_loads(deflected, TRIMMED_CL)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert not (fake / "seen.json").exists()
