"""The Ultra Stick's wing section file is what its fit script writes (real AeroSandbox)."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from aero_kernel.reference_fleet import REFERENCE_DIR, read_selig_coordinates

pytestmark = pytest.mark.aero

SCRIPT = (
    REFERENCE_DIR.parents[1]
    / "scripts/canon_checks/reference_fleet/ultra_stick_120/fit_wing_section.py"
)
SECTION = REFERENCE_DIR / "ultra_stick_120/ultra_stick_120_main_wing_kulfan.dat"
READING_ACCURACY = 0.03 / 15.97  # the fit lies within 0.03 in of the readings on a 15.97 in chord


def fit_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fit_wing_section", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_section_file_is_what_the_fit_script_writes(tmp_path: Path) -> None:
    fresh = tmp_path / "section.dat"
    fresh.write_text(fit_script().dat_text())
    written, shipped = read_selig_coordinates(fresh), read_selig_coordinates(SECTION)
    assert len(written) == len(shipped)
    for (x, y), (x_shipped, y_shipped) in zip(written, shipped, strict=True):
        assert abs(x - x_shipped) < 1e-5
        assert abs(y - y_shipped) < 1e-5


def test_the_fit_lies_within_the_reading_accuracy_of_the_drawn_section() -> None:
    script = fit_script()
    # ``Any``: the script is loaded by path, so its arrays carry no static type
    measured: list[list[float]] = script.measured_coordinates().tolist()
    upper = [(x, y) for x, y in measured if y > 0.0]
    curve: Any = script.fitted().to_airfoil(n_coordinates_per_side=400).upper_coordinates()
    fitted: list[list[float]] = curve.tolist()
    for x, y in upper:
        nearest = min(fitted, key=lambda point: abs(point[0] - x))
        assert abs(nearest[1] - y) < READING_ACCURACY + 1e-3, (x, y, nearest)
