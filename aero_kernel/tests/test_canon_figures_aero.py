"""The geometry figures' hand example, measured by AeroSandbox 4.2.9 with the canon's flags."""

import importlib
import importlib.util
import math
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.aero

EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "_reversa_sdd"
    / "calculations"
    / "canon"
    / "figures"
    / "_example.py"
)


def example_wing() -> tuple[Any, Any]:
    """The example module (hand values) and the same wing built in AeroSandbox."""
    asb: Any = importlib.import_module("aerosandbox")
    spec = importlib.util.spec_from_file_location("canon_figure_example_aero", EXAMPLE)
    assert spec is not None
    assert spec.loader is not None
    ex: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    airfoil = asb.Airfoil("naca0012")
    wing = asb.Wing(
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[0.0, ex.Y_ROOT, 0.0], chord=ex.C_ROOT, airfoil=airfoil),
            asb.WingXSec(xyz_le=[ex.X_LE_TIP, ex.Y_TIP, 0.0], chord=ex.C_TIP, airfoil=airfoil),
        ],
    )
    return ex, wing


def test_the_figure_example_matches_aerosandbox() -> None:
    ex, wing = example_wing()
    s_ref = float(wing.area(type="planform", include_centerline_distance=True))
    b_ref = float(wing.span(type="yz", include_centerline_distance=True))
    c_mac = float(wing.mean_aerodynamic_chord())
    assert math.isclose(s_ref, ex.s_ref(), rel_tol=1e-9)
    assert math.isclose(b_ref, ex.b_ref(), rel_tol=1e-9)
    assert math.isclose(b_ref**2 / s_ref, ex.aspect_ratio(), rel_tol=1e-9)
    assert math.isclose(c_mac, ex.c_mac(), rel_tol=1e-9)
    x_ac = float(wing.aerodynamic_center()[0])
    assert math.isclose(x_ac - 0.25 * c_mac, ex.x_le_mac(), abs_tol=1e-6)


def test_the_gap_free_values_are_what_the_misreading_panel_quotes() -> None:
    ex, wing = example_wing()
    area = float(wing.area(type="planform", include_centerline_distance=False))
    span = float(wing.span(type="yz", include_centerline_distance=False))
    assert math.isclose(area, ex.s_panels(), rel_tol=1e-9)
    assert math.isclose(span, ex.b_panels(), rel_tol=1e-9)
