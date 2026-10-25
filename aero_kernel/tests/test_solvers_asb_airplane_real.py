"""The geometry conversion against the real AeroSandbox (the fast tier uses a fake)."""

import importlib
import math
from typing import Any

import numpy as np
import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import main_wing_properties, to_asb_airplane
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


def stored_variant(member: FleetMember, *, negative_y: bool, tip_first: bool) -> AirplaneGeometry:
    """The fleet member with its mirrored main wing stored on -y and/or tip first."""
    document = reference_document(member)
    (main,) = [w for w in document["wings"].values() if w["surface_type"] == "main_wing"]
    secs = main["x_secs"]
    if negative_y:
        for sec in secs:
            sec["xyz_le"][1] = -sec["xyz_le"][1]
    if tip_first:
        secs.reverse()
    return AirplaneGeometry.model_validate(document)


def aero_coefficients(airplane: AirplaneGeometry) -> dict[str, float]:
    asb: Any = importlib.import_module("aerosandbox")
    result: dict[str, Any] = asb.AeroBuildup(
        to_asb_airplane(airplane), asb.OperatingPoint(velocity=10.0, alpha=5.0)
    ).run()
    return {key: float(np.ravel(result[key])[0]) for key in ("CL", "CD", "Cm")}


@pytest.mark.parametrize("member", list(FleetMember))
@pytest.mark.parametrize(("negative_y", "tip_first"), [(True, False), (False, True), (True, True)])
def test_the_storage_of_a_mirrored_wing_does_not_change_the_aerodynamics(
    member: FleetMember, negative_y: bool, tip_first: bool
) -> None:
    """A mirrored wing stored on -y or tip first is the same wing (one orientation rule with the AVL
    writer, surface_chain.oriented_chain): CL, CD and Cm of the clean airplane agree."""
    reference = aero_coefficients(stored_variant(member, negative_y=False, tip_first=False))
    variant = aero_coefficients(stored_variant(member, negative_y=negative_y, tip_first=tip_first))
    for key, value in reference.items():
        assert math.isclose(variant[key], value, rel_tol=1e-9, abs_tol=1e-12), key
