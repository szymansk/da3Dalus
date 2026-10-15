"""Tests of the physical-admissibility validation (ARCHITECTURE ch. 8.11)."""

import copy
import math
from typing import Any

import pytest
from aero_kernel import geometry
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.schema import AircraftInput
from aero_kernel.validate import UNREAD_FIELDS, Validation, validate_aircraft
from pydantic import BaseModel

NACA = "naca2412"


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


def _result(document: dict[str, Any]) -> Validation:
    return validate_aircraft(AircraftInput.model_validate(copy.deepcopy(document)))


def _validate(document: dict[str, Any]) -> tuple[KernelError, ...]:
    return _result(document).errors


def _codes(errors: tuple[KernelError, ...]) -> list[str]:
    return [error.code for error in errors]


def _paths(errors: tuple[KernelError, ...]) -> list[str | None]:
    return [error.input_path for error in errors]


def test_an_admissible_aircraft_has_no_findings() -> None:
    result = _result(_document())
    assert result.errors == ()
    assert result.warnings == ()


class TestNonFinite:
    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_chord_is_reported_at_its_path(self, bad: float) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"][1]["chord"] = bad
        errors = _validate(document)
        assert _paths(errors) == ['airplane.wings["Main wing"].x_secs[1].chord']
        assert _codes(errors) == ["non_finite_number"]
        assert errors[0].category is ErrorCategory.INVALID_INPUT
        assert errors[0].quantity is None

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


class TestPositiveQuantities:
    @pytest.mark.parametrize("chord", [0.0, -0.1])
    def test_non_positive_chord_is_rejected(self, chord: float) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"][1]["chord"] = chord
        errors = _validate(document)
        assert _paths(errors) == ['airplane.wings["Main wing"].x_secs[1].chord']
        assert _codes(errors) == ["non_positive_length"]
        assert errors[0].category is ErrorCategory.INVALID_INPUT
        assert f"{chord}" in errors[0].message
        assert "must be > 0" in errors[0].message

    def test_positive_chord_is_accepted(self) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"][1]["chord"] = 1e-6
        assert _validate(document) == ()

    @pytest.mark.parametrize("mass", [0.0, -2.0])
    def test_non_positive_mass_is_rejected(self, mass: float) -> None:
        document = _document()
        document["values"]["aircraft-mass"] = mass
        errors = _validate(document)
        assert _paths(errors) == ["values.aircraft-mass"]
        assert _codes(errors) == ["non_positive_mass"]

    @pytest.mark.parametrize("density", [0.0, -1.225])
    def test_non_positive_density_is_rejected(self, density: float) -> None:
        document = _document()
        document["values"]["sea-level-air-density"] = density
        errors = _validate(document)
        assert _paths(errors) == ["values.sea-level-air-density"]
        assert _codes(errors) == ["non_positive_density"]

    def test_absent_mass_and_density_are_not_a_finding(self) -> None:
        # a missing value is `missing_input` in the engine (Q24), not a validation finding
        document = _document()
        document["values"] = {}
        assert _validate(document) == ()


class TestWingSections:
    def test_one_section_is_rejected(self) -> None:
        document = _document()
        del document["airplane"]["wings"]["Main wing"]["x_secs"][1]
        errors = _validate(document)
        assert _paths(errors) == ['airplane.wings["Main wing"].x_secs']
        assert _codes(errors) == ["too_few_sections"]

    def test_no_section_is_rejected(self) -> None:
        document = _document()
        document["airplane"]["wings"]["Main wing"]["x_secs"] = []
        assert _paths(_validate(document)) == ['airplane.wings["Main wing"].x_secs']

    def test_two_sections_are_accepted(self) -> None:
        assert _validate(_document()) == ()


class TestPaths:
    def test_wing_key_is_json_escaped(self) -> None:
        document = _document()
        wing = document["airplane"]["wings"].pop("Main wing")
        key = 'Wing "A"\\ ä'
        wing["name"] = key
        wing["x_secs"][0]["chord"] = math.nan
        document["airplane"]["wings"][key] = wing
        assert _paths(_validate(document)) == [
            'airplane.wings["Wing \\"A\\"\\\\ ä"].x_secs[0].chord'
        ]

    def test_slug_values_key_is_dotted_and_any_other_is_bracketed(self) -> None:
        document = _document()
        document["values"]["Odd key"] = math.nan
        document["values"]['q"x'] = math.nan
        document["values"]["Aircraft-Mass"] = math.nan
        assert sorted(path for path in _paths(_validate(document)) if path) == [
            'values["Aircraft-Mass"]',
            'values["Odd key"]',
            'values["q\\"x"]',
        ]


class TestKernelReadFieldsOnly:
    """A check exists only for a field the kernel reads (ch. 8.11)."""

    def test_cad_only_fields_are_not_checked(self) -> None:
        document = _document()
        x_sec = document["airplane"]["wings"]["Main wing"]["x_secs"][0]
        nan = math.nan
        servo = dict.fromkeys(
            [
                "length",
                "width",
                "height",
                "leading_length",
                "latch_z",
                "latch_x",
                "latch_thickness",
                "latch_length",
                "cable_z",
                "screw_hole_lx",
                "screw_hole_d",
            ],
            nan,
        )
        x_sec["trailing_edge_device"] = {
            "servo": servo,
            "hinge_spacing": nan,
            "side_spacing_root": nan,
            "side_spacing_tip": nan,
            "positive_deflection_deg": nan,
            "negative_deflection_deg": nan,
            "trailing_edge_offset_factor": nan,
        }
        x_sec["spare_list"] = [
            {"spare_support_dimension_width": nan, "spare_support_dimension_height": nan}
        ]
        x_sec["turbulator"] = {"position_root": nan, "height_mm": nan}
        document["airplane"]["wings"]["Main wing"]["x_secs"].append(_xsec(1.0))
        assert _validate(document) == ()

    def test_trailing_edge_device_deflection_must_be_finite(self) -> None:
        document = _document()
        x_sec = document["airplane"]["wings"]["Main wing"]["x_secs"][0]
        x_sec["trailing_edge_device"] = {"deflection_deg": math.inf}
        assert _paths(_validate(document)) == [
            'airplane.wings["Main wing"].x_secs[0].trailing_edge_device.deflection_deg'
        ]

    def test_only_cad_only_fields_have_a_format_alias(self) -> None:
        """Walked fields keep the format's name, so a path matches the caller's document."""
        for model in vars(geometry).values():
            if not (isinstance(model, type) and issubclass(model, BaseModel)):
                continue
            for name, field in model.model_fields.items():
                if field.validation_alias is not None:
                    assert name in UNREAD_FIELDS.get(model, frozenset()), (model, name)
