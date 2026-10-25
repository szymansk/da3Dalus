"""The precondition ``main_wing_has_spanwise_extent`` of ``airplane-geometry`` (gh-1253).

A wing typed ``main_wing`` whose stored sections extend no further in y than in z is a vertical
surface; AeroSandbox would measure it without complaint (slant planform), so the canon refuses it
before the measurement. Criterion: y-extent > z-extent of the stored sections (the proposed
threshold, needs maintainer approval).
"""

from typing import Any

import pytest
from aero_kernel import compute
from aero_kernel.build import shipped_build
from aero_kernel.formulas.airplane_geometry import main_wing_has_spanwise_extent
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, QuantityStatus
from aero_kernel.tests.engine_builders import request

PRECONDITION = "main_wing_has_spanwise_extent"


def airplane(*points: tuple[float, float]) -> AirplaneGeometry:
    """An airplane whose main wing has sections at the given (y, z) positions."""
    sections = [
        {"xyz_le": [0.0, y, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y, z in points
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


def state(*points: tuple[float, float]) -> str:
    return main_wing_has_spanwise_extent({"airplane": airplane(*points)}).state


def test_the_canon_declares_the_precondition_as_an_error_on_the_airplane() -> None:
    formula = shipped_build().model.formula("airplane-geometry")
    assert formula is not None
    (check,) = formula.preconditions
    assert (check.id, check.parameter, check.on_violation) == (PRECONDITION, "airplane", "error")


def test_a_flat_wing_holds() -> None:
    assert state((0.0, 0.0), (0.5, 0.0)) == "held"


def test_a_steep_dihedral_below_45_degrees_holds() -> None:
    assert state((0.0, 0.0), (0.5, 0.4)) == "held"


def test_a_wing_with_a_winglet_that_is_longer_in_y_overall_holds() -> None:
    assert state((0.0, 0.0), (0.6, 0.0), (0.62, 0.1)) == "held"


def test_a_vertical_surface_is_violated() -> None:
    assert state((0.0, 0.0), (0.0, 0.5)) == "violated"


def test_exactly_45_degrees_is_violated() -> None:
    assert state((0.0, 0.0), (0.5, 0.5)) == "violated"


def test_a_wing_stored_on_the_negative_side_is_judged_by_its_extent() -> None:
    assert state((0.0, 0.0), (-0.5, 0.0)) == "held"


def test_the_message_names_the_wing_and_the_remedy() -> None:
    message = main_wing_has_spanwise_extent({"airplane": airplane((0.0, 0.0), (0.0, 0.5))}).message
    assert "'Main'" in message
    assert "surface type" in message


@pytest.mark.asyncio
async def test_a_vertical_main_wing_is_an_unsupported_configuration_before_asb_computes() -> None:
    document: dict[str, Any] = {"name": "t", "wings": {}}
    document["wings"]["Main"] = {
        "name": "Main",
        "surface_type": "main_wing",
        "x_secs": [
            {"xyz_le": [0.0, 0.0, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
            for z in (0.0, 0.5)
        ],
    }
    aircraft = AircraftInput.model_validate({"airplane": document, "values": {}})
    result = await compute(aircraft, request("wing-reference-area"))
    (quantity,) = result.quantities
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "precondition_violated"
    assert quantity.error.category.value == "unsupported_configuration"
    assert quantity.error.detail == {"precondition": PRECONDITION}
