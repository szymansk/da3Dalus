"""The geometry conversion against the real AeroSandbox (the fast tier uses a fake)."""

import importlib
import math
from typing import Any

import numpy as np
import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_solvers_asb_airplane import CONTOUR, geometry

pytestmark = pytest.mark.aero


def test_the_real_airplane_has_the_wings_sections_and_airfoils_of_the_document() -> None:
    airplane = to_asb_airplane(geometry())
    assert airplane.name == "t"
    assert [w.name for w in airplane.wings] == ["Main", "Fin"]
    assert [w.symmetric for w in airplane.wings] == [True, False]
    main = airplane.wings[0]
    assert [list(s.xyz_le) for s in main.xsecs] == [
        [0.0, 0.0, 0.0],
        [0.02, 0.4, 0.01],
        [0.04, 0.8, 0.02],
    ]
    assert [s.chord for s in main.xsecs] == [0.2, 0.1, 0.05]
    assert [s.twist for s in main.xsecs] == [0.0, -1.5, 0.0]
    assert main.xsecs[0].airfoil.name == "naca2412"
    assert main.xsecs[1].airfoil.coordinates.tolist() == CONTOUR


def test_the_real_airplane_carries_the_kernels_reference_values() -> None:
    airplane = to_asb_airplane(geometry())
    properties = main_wing_properties(geometry())
    assert (airplane.s_ref, airplane.b_ref, airplane.c_ref) == (
        properties.s_ref,
        properties.b_ref,
        properties.c_mac,
    )


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_fleet_converts_and_aerobuildup_accepts_zero_size_fuselage_ends(
    member: FleetMember,
) -> None:
    """BRYAN's fuselage closes to a point at both ends; AeroBuildup must stay finite."""
    asb: Any = importlib.import_module("aerosandbox")
    document = AirplaneGeometry.model_validate(reference_document(member))
    airplane = to_asb_airplane(document)
    assert all(math.isfinite(f.volume()) and f.volume() > 0.0 for f in airplane.fuselages)
    result: dict[str, Any] = asb.AeroBuildup(
        airplane, asb.OperatingPoint(velocity=10.0, alpha=5.0)
    ).run()
    coefficients = {key: float(np.ravel(result[key])[0]) for key in ("CL", "CD", "Cm")}
    assert all(math.isfinite(value) for value in coefficients.values())
    assert coefficients["CL"] > 0.0
