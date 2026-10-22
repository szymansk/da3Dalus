"""Surface types: the required `surface_type` of each wing and the one main wing (ch. 8.5, 8.11)."""

from typing import Any, get_args

import pytest
from aero_kernel import geometry
from aero_kernel.errors import CODE_CATALOGUE, ErrorCategory, KernelError
from aero_kernel.schema import AircraftInput
from aero_kernel.validate import validate_aircraft
from pydantic import ValidationError

SURFACE_TYPES = (
    "main_wing",
    "horizontal_tail",
    "vertical_tail",
    "v_tail",
    "canard",
    "tandem_wing",
    "winglet",
)


def wing(name: str, surface_type: str | None) -> dict[str, Any]:
    """A two-section wing; ``surface_type`` is left out when ``None``."""
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y in (0.0, 0.5)
    ]
    document: dict[str, Any] = {"name": name, "x_secs": sections}
    if surface_type is not None:
        document["surface_type"] = surface_type
    return document


def errors_of(wings: dict[str, dict[str, Any]] | None) -> tuple[KernelError, ...]:
    """Validate an aircraft with the given wings."""
    airplane: dict[str, Any] = {"name": "t"}
    if wings is not None:
        airplane["wings"] = wings
    aircraft = AircraftInput.model_validate({"airplane": airplane, "values": {}})
    return validate_aircraft(aircraft).errors


def test_the_seven_surface_types_of_the_architecture_are_the_model_values() -> None:
    annotation = geometry.Wing.model_fields["surface_type"].annotation
    values = {value for arg in get_args(annotation) for value in get_args(arg)}
    assert values == set(SURFACE_TYPES)


@pytest.mark.parametrize("surface_type", SURFACE_TYPES)
def test_each_surface_type_parses(surface_type: str) -> None:
    parsed = geometry.Wing.model_validate(wing("w", surface_type))
    assert parsed.surface_type == surface_type


def test_a_wing_may_lack_the_type_in_the_model_because_validation_reports_it() -> None:
    assert geometry.Wing.model_validate(wing("w", None)).surface_type is None


def test_an_unknown_surface_type_does_not_parse() -> None:
    with pytest.raises(ValidationError):
        geometry.Wing.model_validate(wing("w", "biplane_lower"))


@pytest.mark.parametrize("code", ["missing_surface_type", "main_wing_count"])
def test_the_codes_are_invalid_input(code: str) -> None:
    assert CODE_CATALOGUE[code] is ErrorCategory.INVALID_INPUT


def test_one_main_wing_and_typed_tails_is_admissible() -> None:
    wings = {
        "Main": wing("Main", "main_wing"),
        "HT": wing("HT", "horizontal_tail"),
        "VT": wing("VT", "vertical_tail"),
    }
    assert errors_of(wings) == ()


def test_a_wing_without_a_surface_type_is_reported_at_its_path() -> None:
    errors = errors_of({"Main": wing("Main", "main_wing"), "Tail": wing("Tail", None)})
    (error,) = errors
    assert (error.code, error.category) == ("missing_surface_type", ErrorCategory.INVALID_INPUT)
    assert error.input_path == 'airplane.wings["Tail"]'


def test_every_wing_without_a_type_is_reported_and_counts_for_no_main_wing() -> None:
    errors = errors_of({"A": wing("A", None), "B": wing("B", None)})
    assert [(e.code, e.input_path) for e in errors] == [
        ("missing_surface_type", 'airplane.wings["A"]'),
        ("missing_surface_type", 'airplane.wings["B"]'),
        ("main_wing_count", "airplane.wings"),
    ]


@pytest.mark.parametrize("wings", [None, {}])
def test_an_airplane_without_wings_has_no_main_wing(wings: dict[str, Any] | None) -> None:
    (error,) = errors_of(wings)
    assert (error.code, error.input_path) == ("main_wing_count", "airplane.wings")
    assert error.detail == {"count": 0}


def test_wings_but_no_main_wing_is_reported_with_the_count() -> None:
    (error,) = errors_of({"HT": wing("HT", "horizontal_tail")})
    assert (error.code, error.detail) == ("main_wing_count", {"count": 0})


def test_two_main_wings_are_reported_with_the_count() -> None:
    (error,) = errors_of({"A": wing("A", "main_wing"), "B": wing("B", "main_wing")})
    assert (error.code, error.input_path, error.detail) == (
        "main_wing_count",
        "airplane.wings",
        {"count": 2},
    )
    assert error.category is ErrorCategory.INVALID_INPUT
