"""Tests of the physical-admissibility validation (ARCHITECTURE ch. 8.11)."""

import copy
import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.schema import AircraftInput
from aero_kernel.validate import validate_input

NACA = "NACA 2412"


def _xsec(y: float, chord: float = 0.2, airfoil: Any = NACA) -> dict[str, Any]:
    return {"xyz_le": [0.0, y, 0.0], "chord": chord, "twist": 0.0, "airfoil": airfoil}


def _document() -> dict[str, Any]:
    """A minimal admissible aircraft document: one wing, one fuselage, a mass."""
    return {
        "airplane": {
            "name": "Test",
            "wings": {"Main wing": {"name": "Main wing", "x_secs": [_xsec(0.0), _xsec(0.5)]}},
            "fuselages": {
                "Body": {
                    "name": "Body",
                    "x_secs": [
                        {"xyz": [0.0, 0.0, 0.0], "a": 0.05, "b": 0.05, "n": 2.0},
                        {"xyz": [0.5, 0.0, 0.0], "a": 0.05, "b": 0.05, "n": 2.0},
                    ],
                }
            },
        },
        "values": {"aircraft-mass": 1.5, "sea-level-air-density": 1.225},
    }


def _validate(document: dict[str, Any]) -> tuple[KernelError, ...]:
    return validate_input(AircraftInput.model_validate(copy.deepcopy(document)))


def _paths(errors: tuple[KernelError, ...]) -> list[str | None]:
    return [error.input_path for error in errors]


def test_an_admissible_aircraft_has_no_findings() -> None:
    assert _validate(_document()) == ()


class TestNonFinite:
    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_chord_is_reported_at_its_path(self, bad: float) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"][1]["chord"] = bad
        errors = _validate(document)
        assert _paths(errors) == ['airplane.wings["Main wing"].x_secs[1].chord']
        assert errors[0].category is ErrorCategory.INVALID_INPUT

    def test_non_finite_tuple_element_gets_an_index(self) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"][0]["xyz_le"][1] = math.nan
        assert _paths(_validate(document)) == ['airplane.wings["Main wing"].x_secs[0].xyz_le[1]']

    def test_non_finite_value_is_reported_at_its_slug(self) -> None:
        document = _document()
        document["values"]["flight-speed"] = math.inf
        assert _paths(_validate(document)) == ["values.flight-speed"]

    def test_non_finite_fuselage_dimension_and_inline_airfoil_point(self) -> None:
        document = _document()
        document["airplane"]["fuselages"]["Body"]["x_secs"][1]["a"] = math.nan
        document["airplane"]["wings"]["Main wing"]["x_secs"][0]["airfoil"] = {
            "coordinates": [[1.0, 0.0], [0.0, math.inf], [1.0, 0.0]]
        }
        assert _paths(_validate(document)) == [
            'airplane.wings["Main wing"].x_secs[0].airfoil.coordinates[1][1]',
            'airplane.fuselages["Body"].x_secs[1].a',
        ]

    def test_all_findings_are_collected(self) -> None:
        document = _document()
        document["values"]["aircraft-mass"] = math.nan
        document["values"]["altitude"] = math.nan
        assert _paths(_validate(document)) == ["values.aircraft-mass", "values.altitude"]
