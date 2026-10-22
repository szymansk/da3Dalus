"""Tests for the input model of the geometry format (ARCHITECTURE ch. 8.11).

The format is docs/geometry-format/AIRPLANE-GEOMETRY.md; the model mirrors
docs/geometry-format/airplane-geometry.schema.json as types, with no physical constraint.
"""

import json
import math
import re
from typing import Any

import pytest
from aero_kernel import geometry
from aero_kernel.geometry import (
    AirplaneGeometry,
    ControlSurface,
    InlineAirfoil,
    Servo,
    SpareDetail,
    TrailingEdgeDevice,
    Turbulator,
    WingXSec,
)
from aero_kernel.tests.test_geometry_schema import SCHEMA_PATH
from jsonschema import Draft202012Validator
from pydantic import ValidationError

# A raw JSON document as read from a file: the one place where Any is the honest type.
Doc = dict[str, Any]


def assert_close(actual: float | None, expected: float) -> None:
    """Assert equality up to the rounding of a mm -> m multiplication."""
    assert actual is not None
    assert math.isclose(actual, expected, rel_tol=1e-12), (actual, expected)


def minimal_wing() -> Doc:
    """A two-section wing document with only the required fields."""
    section = {"xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca0012"}
    tip = section | {"xyz_le": [0.0, 1.0, 0.0]}
    return {"name": "Wing", "x_secs": [section, tip]}


class TestAirplaneGeometryRoot:
    def test_name_alone_parses_with_the_schema_defaults(self) -> None:
        airplane = AirplaneGeometry.model_validate({"name": "Vanilla"})
        assert airplane.name == "Vanilla"
        assert airplane.total_mass_kg is None
        assert airplane.xyz_ref == (0.0, 0.0, 0.0)
        assert airplane.wings is None
        assert airplane.fuselages is None

    def test_name_is_required(self) -> None:
        with pytest.raises(ValidationError, match="name"):
            AirplaneGeometry.model_validate({})

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            AirplaneGeometry.model_validate({"name": "A", "herkunft": "x"})

    @pytest.mark.parametrize("mass", [True, "3.0"])
    def test_mass_must_be_a_number(self, mass: object) -> None:
        with pytest.raises(ValidationError, match="total_mass_kg"):
            AirplaneGeometry.model_validate({"name": "A", "total_mass_kg": mass})

    def test_integers_are_accepted_for_floats(self) -> None:
        airplane = AirplaneGeometry.model_validate(
            {"name": "A", "xyz_ref": [1, 0, 0], "total_mass_kg": 3}
        )
        assert airplane.xyz_ref == (1.0, 0.0, 0.0)
        assert airplane.total_mass_kg == 3.0

    @pytest.mark.parametrize("ref", [[0.0, 0.0], [0, 0, 0, 0], [True, 0, 0], ["0", 0, 0]])
    def test_reference_point_must_be_three_numbers(self, ref: object) -> None:
        with pytest.raises(ValidationError, match="xyz_ref"):
            AirplaneGeometry.model_validate({"name": "A", "xyz_ref": ref})

    def test_non_finite_numbers_parse(self) -> None:
        airplane = AirplaneGeometry.model_validate(
            {"name": "A", "total_mass_kg": float("nan"), "xyz_ref": [float("inf"), 0, 0]}
        )
        assert airplane.xyz_ref[0] == float("inf")
        mass = airplane.total_mass_kg
        assert mass is not None
        assert math.isnan(mass)

    def test_model_is_frozen(self) -> None:
        airplane = AirplaneGeometry.model_validate({"name": "A"})
        with pytest.raises(ValidationError, match="frozen"):
            airplane.name = "B"  # type: ignore[misc]  # frozen on purpose: the test expects the error


def fuselage_doc() -> Doc:
    """A fuselage with two super-ellipse stations."""
    return {
        "name": "Fuselage",
        "x_secs": [
            {"xyz": [0.0, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
            {"xyz": [1.0, 0.0, 0.0], "a": 0.05, "b": 0.04, "n": 2, "n_lower": 6.0},
        ],
    }


class TestFuselage:
    def test_fuselage_parses_with_defaults_and_n_lower(self) -> None:
        airplane = AirplaneGeometry.model_validate(
            {"name": "A", "fuselages": {"F": fuselage_doc()}}
        )
        assert airplane.fuselages is not None
        fuselage = airplane.fuselages["F"]
        assert fuselage.symmetric is False
        assert fuselage.step_path is None
        assert fuselage.solid_step_path is None
        first, second = fuselage.x_secs
        assert first.n_lower is None
        assert (second.a, second.b, second.n, second.n_lower) == (0.05, 0.04, 2.0, 6.0)

    def test_station_fields_are_not_scaled(self) -> None:
        airplane = AirplaneGeometry.model_validate(
            {"name": "A", "fuselages": {"F": fuselage_doc()}}
        )
        assert airplane.fuselages is not None
        assert airplane.fuselages["F"].x_secs[1].xyz == (1.0, 0.0, 0.0)

    @pytest.mark.parametrize(
        ("path", "value"),
        [("a", "0.1"), ("n", True), ("xyz", [0, 0]), ("n_lower", "6"), ("extra", 1)],
    )
    def test_station_types_are_strict(self, path: str, value: object) -> None:
        doc = fuselage_doc()
        station = {"xyz": [1.0, 0.0, 0.0], "a": 0.05, "b": 0.04, "n": 2.0} | {path: value}
        doc["x_secs"] = [station, station]
        with pytest.raises(ValidationError, match=path):
            AirplaneGeometry.model_validate({"name": "A", "fuselages": {"F": doc}})

    @pytest.mark.parametrize("missing", ["xyz", "a", "b", "n"])
    def test_station_requires_xyz_a_b_n(self, missing: str) -> None:
        station = {"xyz": [1.0, 0.0, 0.0], "a": 0.05, "b": 0.04, "n": 2.0}
        del station[missing]
        doc = fuselage_doc() | {"x_secs": [station, station]}
        with pytest.raises(ValidationError, match=missing):
            AirplaneGeometry.model_validate({"name": "A", "fuselages": {"F": doc}})

    def test_fuselage_requires_name_and_sections(self) -> None:
        with pytest.raises(ValidationError, match="x_secs"):
            AirplaneGeometry.model_validate({"name": "A", "fuselages": {"F": {"name": "F"}}})

    def test_step_paths_are_kept(self) -> None:
        doc = fuselage_doc() | {"symmetric": True, "step_path": "a.step", "solid_step_path": None}
        airplane = AirplaneGeometry.model_validate({"name": "A", "fuselages": {"F": doc}})
        assert airplane.fuselages is not None
        assert airplane.fuselages["F"].symmetric is True
        assert airplane.fuselages["F"].step_path == "a.step"

    @pytest.mark.parametrize("flag", ["true", 1])
    def test_symmetric_must_be_a_bool(self, flag: object) -> None:
        doc = fuselage_doc() | {"symmetric": flag}
        with pytest.raises(ValidationError, match="symmetric"):
            AirplaneGeometry.model_validate({"name": "A", "fuselages": {"F": doc}})


def airplane_with_wing(wing: Doc) -> Doc:
    """Wrap a wing document into an aeroplane document."""
    return {"name": "A", "wings": {"W": wing}}


class TestWing:
    def test_minimal_wing_gets_the_schema_defaults(self) -> None:
        airplane = AirplaneGeometry.model_validate(airplane_with_wing(minimal_wing()))
        assert airplane.wings is not None
        wing = airplane.wings["W"]
        assert wing.symmetric is True
        assert wing.design_model is None
        assert wing.units.geometry_length == "m"
        assert wing.units.detail_length == "m"
        assert wing.units.angle == "deg"
        root = wing.x_secs[0]
        assert root.xyz_le == (0.0, 0.0, 0.0)
        assert root.chord == 0.2
        assert root.dihedral is None
        assert root.control_surface is None
        assert root.x_sec_type is None
        assert root.tip_type is None
        assert root.number_interpolation_points is None
        assert root.spare_list is None
        assert root.trailing_edge_device is None
        assert root.turbulator is None

    def test_wing_requires_name_and_sections(self) -> None:
        with pytest.raises(ValidationError, match="name"):
            AirplaneGeometry.model_validate(airplane_with_wing({"x_secs": []}))
        with pytest.raises(ValidationError, match="x_secs"):
            AirplaneGeometry.model_validate(airplane_with_wing({"name": "W"}))

    def test_section_count_is_not_a_type_matter(self) -> None:
        wing: Doc = {"name": "W", "x_secs": []}
        airplane = AirplaneGeometry.model_validate(airplane_with_wing(wing))
        assert airplane.wings is not None
        assert airplane.wings["W"].x_secs == ()

    @pytest.mark.parametrize("missing", ["xyz_le", "chord", "twist", "airfoil"])
    def test_section_requires_its_four_fields(self, missing: str) -> None:
        wing = minimal_wing()
        sections = wing["x_secs"]
        del sections[0][missing]
        with pytest.raises(ValidationError, match=missing):
            AirplaneGeometry.model_validate(airplane_with_wing(wing))

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("chord", "0.2"),
            ("twist", True),
            ("dihedral", "3"),
            ("xyz_le", [0, 0]),
            ("x_sec_type", "middle"),
            ("tip_type", "pointy"),
            ("number_interpolation_points", 2.5),
            ("number_interpolation_points", True),
            ("airfoil", 12),
            ("control_surfaces", []),
        ],
    )
    def test_section_types_and_enums_are_strict(self, field: str, value: object) -> None:
        wing = minimal_wing()
        sections = wing["x_secs"]
        sections[0][field] = value
        with pytest.raises(ValidationError, match=field):
            AirplaneGeometry.model_validate(airplane_with_wing(wing))

    def test_section_details_parse(self) -> None:
        wing = minimal_wing()
        sections = wing["x_secs"]
        sections[0] |= {
            "dihedral": 3,
            "x_sec_type": "root",
            "tip_type": "round",
            "number_interpolation_points": 5,
        }
        sections[0]["twist"] = -2
        airplane = AirplaneGeometry.model_validate(airplane_with_wing(wing))
        assert airplane.wings is not None
        root = airplane.wings["W"].x_secs[0]
        assert (root.dihedral, root.twist) == (3.0, -2.0)
        assert (root.x_sec_type, root.tip_type, root.number_interpolation_points) == (
            "root",
            "round",
            5,
        )

    @pytest.mark.parametrize("design_model", ["wc", "asb", None])
    def test_design_model_enum(self, design_model: str | None) -> None:
        wing = minimal_wing() | {"design_model": design_model, "symmetric": False}
        airplane = AirplaneGeometry.model_validate(airplane_with_wing(wing))
        assert airplane.wings is not None
        assert airplane.wings["W"].design_model == design_model
        assert airplane.wings["W"].symmetric is False

    def test_unknown_design_model_is_rejected(self) -> None:
        wing = minimal_wing() | {"design_model": "xyz"}
        with pytest.raises(ValidationError, match="design_model"):
            AirplaneGeometry.model_validate(airplane_with_wing(wing))

    @pytest.mark.parametrize("units", [None, {"angle": None}, {"detail_length": None}])
    def test_units_are_never_null(self, units: object) -> None:
        wing = minimal_wing() | {"units": units}
        with pytest.raises(ValidationError, match="units"):
            AirplaneGeometry.model_validate(airplane_with_wing(wing))

    def test_units_block_accepts_only_the_declared_constants(self) -> None:
        wing = minimal_wing() | {
            "units": {"geometry_length": "m", "detail_length": "m", "angle": "deg"}
        }
        airplane = AirplaneGeometry.model_validate(airplane_with_wing(wing))
        assert airplane.wings is not None
        for key, value in (("geometry_length", "mm"), ("angle", "rad"), ("extra", "m")):
            bad = minimal_wing() | {"units": {key: value}}
            with pytest.raises(ValidationError, match=key):
                AirplaneGeometry.model_validate(airplane_with_wing(bad))


def parse_first_section(detail: Doc) -> WingXSec:
    """Parse a wing whose root rib carries ``detail`` and return that parsed rib."""
    wing = minimal_wing()
    sections = wing["x_secs"]
    sections[0] |= detail
    airplane = AirplaneGeometry.model_validate(airplane_with_wing(wing))
    assert airplane.wings is not None
    return airplane.wings["W"].x_secs[0]


def first_surface(detail: Doc) -> ControlSurface:
    """Parse a root rib with ``detail`` and return its control surface."""
    surface = parse_first_section(detail).control_surface
    assert surface is not None
    return surface


def first_spar(detail: Doc) -> SpareDetail:
    """Parse a root rib with ``detail`` and return its first spar."""
    spars = parse_first_section(detail).spare_list
    assert spars
    return spars[0]


def first_device(detail: Doc) -> TrailingEdgeDevice:
    """Parse a root rib with ``detail`` and return its trailing-edge device."""
    device = parse_first_section(detail).trailing_edge_device
    assert device is not None
    return device


def first_turbulator(detail: Doc) -> Turbulator:
    """Parse a root rib with ``detail`` and return its turbulator."""
    turbulator = parse_first_section(detail).turbulator
    assert turbulator is not None
    return turbulator


def reject_first_section(detail: Doc, match: str) -> None:
    """Assert that a root rib carrying ``detail`` fails to parse with ``match``."""
    wing = minimal_wing()
    sections = wing["x_secs"]
    sections[0] |= detail
    with pytest.raises(ValidationError, match=match):
        AirplaneGeometry.model_validate(airplane_with_wing(wing))


SERVO_MM = {
    "length": 23.0,
    "width": 12.0,
    "height": 24.0,
    "leading_length": 6.0,
    "latch_z": 15.0,
    "latch_x": 4.0,
    "latch_thickness": 2.5,
    "latch_length": 32.0,
    "cable_z": 7.0,
    "screw_hole_lx": 3.0,
    "screw_hole_d": 2.0,
}


class TestControlSurface:
    def test_defaults_and_values(self) -> None:
        surface = first_surface({"control_surface": {"name": "Aileron"}})
        assert (surface.name, surface.hinge_point, surface.symmetric, surface.deflection) == (
            "Aileron",
            0.8,
            True,
            0.0,
        )

    def test_name_is_required_and_types_are_strict(self) -> None:
        reject_first_section({"control_surface": {}}, "name")
        reject_first_section({"control_surface": {"name": "A", "deflection": "3"}}, "deflection")
        reject_first_section({"control_surface": {"name": "A", "symmetric": 0}}, "symmetric")
        reject_first_section({"control_surface": {"name": "A", "mix": 1}}, "extra_forbidden")

    def test_factor_range_is_not_a_type_matter(self) -> None:
        assert (
            first_surface({"control_surface": {"name": "A", "hinge_point": 1.5}}).hinge_point == 1.5
        )


class TestSpar:
    def test_spar_lengths_are_metres_and_stay_unscaled(self) -> None:
        spar = {
            "spare_support_dimension_width": 0.006,
            "spare_support_dimension_height": 0.004,
            "spare_length": 0.5,
            "spare_start": 0.1,
            "spare_origin": [0.1, 0.0, 0.0],
            "spare_vector": [0.0, 1.0, 0.0],
            "spare_position_factor": 0.25,
            "spare_mode": "normal",
        }
        parsed = first_spar({"spare_list": [spar]})
        assert parsed.spare_support_dimension_width == 0.006
        assert parsed.spare_support_dimension_height == 0.004
        assert parsed.spare_length == 0.5
        assert parsed.spare_start == 0.1
        assert parsed.spare_origin == (0.1, 0.0, 0.0)
        assert parsed.spare_vector == (0.0, 1.0, 0.0)
        assert parsed.spare_position_factor == 0.25
        assert parsed.spare_mode == "normal"

    def test_defaults(self) -> None:
        spar = {"spare_support_dimension_width": 0.006, "spare_support_dimension_height": 0.004}
        parsed = first_spar({"spare_list": [spar]})
        assert parsed.spare_start == 0.0
        assert parsed.spare_mode == "standard"
        assert parsed.spare_length is None
        assert parsed.spare_origin is None
        assert parsed.spare_vector is None
        assert parsed.spare_position_factor is None

    def test_required_enum_and_strictness(self) -> None:
        reject_first_section({"spare_list": [{"spare_support_dimension_width": 0.1}]}, "height")
        base = {"spare_support_dimension_width": 0.1, "spare_support_dimension_height": 0.1}
        reject_first_section({"spare_list": [base | {"spare_mode": "diagonal"}]}, "spare_mode")
        reject_first_section({"spare_list": [base | {"spare_vector": [0, 1]}]}, "spare_vector")
        reject_first_section({"spare_list": [base | {"spare_start": "0"}]}, "spare_start")
        reject_first_section({"spare_list": [base | {"colour": 1}]}, "extra_forbidden")


def servo_attributes() -> dict[str, float]:
    """The hand-computed metre values of ``SERVO_MM`` (mm * 0.001)."""
    return {
        "length_m": 0.023,
        "width_m": 0.012,
        "height_m": 0.024,
        "leading_length_m": 0.006,
        "latch_z_m": 0.015,
        "latch_x_m": 0.004,
        "latch_thickness_m": 0.0025,
        "latch_length_m": 0.032,
        "cable_z_m": 0.007,
        "screw_hole_lx_m": 0.003,
        "screw_hole_d_m": 0.002,
    }


class TestTrailingEdgeDevice:
    def test_defaults(self) -> None:
        device = first_device({"trailing_edge_device": {}})
        assert device.role == "other"
        assert device.servo_placement == "top"
        assert device.deflection_deg == 0.0
        assert device.trailing_edge_offset_factor == 1.0
        assert (device.mix_gain_primary, device.mix_gain_secondary, device.differential_ratio) == (
            1.0,
            1.0,
            1.0,
        )
        for name in (
            "name",
            "label",
            "rel_chord_root",
            "rel_chord_tip",
            "hinge_spacing_m",
            "side_spacing_root_m",
            "side_spacing_tip_m",
            "servo",
            "rel_chord_servo_position",
            "rel_length_servo_position",
            "positive_deflection_deg",
            "negative_deflection_deg",
            "hinge_type",
            "symmetric",
        ):
            assert getattr(device, name) is None, name

    def test_millimetre_spacings_become_metres(self) -> None:
        detail = {"hinge_spacing": 0.5, "side_spacing_root": 2.0, "side_spacing_tip": 1.5}
        device = first_device({"trailing_edge_device": detail})
        assert_close(device.hinge_spacing_m, 0.0005)
        assert_close(device.side_spacing_root_m, 0.002)
        assert_close(device.side_spacing_tip_m, 0.0015)

    def test_dimensionless_and_angle_fields_are_not_scaled(self) -> None:
        detail = {
            "role": "elevon",
            "rel_chord_root": 0.7,
            "rel_chord_tip": 0.75,
            "rel_chord_servo_position": 0.5,
            "rel_length_servo_position": 0.4,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": -20,
            "deflection_deg": 5,
            "trailing_edge_offset_factor": 1.2,
            "mix_gain_primary": 1.5,
            "mix_gain_secondary": 0.5,
            "differential_ratio": 2.0,
            "hinge_type": "top_simple",
            "symmetric": False,
            "servo_placement": "bottom",
            "name": "L",
            "label": "left",
        }
        device = first_device({"trailing_edge_device": detail})
        assert device.role == "elevon"
        assert (device.rel_chord_root, device.rel_chord_tip) == (0.7, 0.75)
        assert (device.rel_chord_servo_position, device.rel_length_servo_position) == (0.5, 0.4)
        assert (device.positive_deflection_deg, device.negative_deflection_deg) == (25.0, -20.0)
        assert device.deflection_deg == 5.0
        assert device.trailing_edge_offset_factor == 1.2
        assert (device.mix_gain_primary, device.mix_gain_secondary, device.differential_ratio) == (
            1.5,
            0.5,
            2.0,
        )
        assert (device.hinge_type, device.symmetric, device.servo_placement) == (
            "top_simple",
            False,
            "bottom",
        )
        assert (device.name, device.label) == ("L", "left")

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("role", "spoiler"),
            ("hinge_type", "pivot"),
            ("servo_placement", "left"),
            ("hinge_spacing", "0.5"),
            ("rel_chord_root", True),
            ("symmetric", "yes"),
            ("hinge_hight", 1),
        ],
    )
    def test_enums_types_and_unknown_fields_are_rejected(self, field: str, value: object) -> None:
        reject_first_section({"trailing_edge_device": {field: value}}, field)

    def test_format_key_not_attribute_name_is_the_input(self) -> None:
        reject_first_section(
            {"trailing_edge_device": {"hinge_spacing_m": 0.0005}}, "extra_forbidden"
        )

    def test_servo_index_and_null(self) -> None:
        assert first_device({"trailing_edge_device": {"servo": 3}}).servo == 3
        reject_first_section({"trailing_edge_device": {"servo": 2.5}}, "servo")
        reject_first_section({"trailing_edge_device": {"servo": True}}, "servo")

    def test_servo_millimetres_become_metres(self) -> None:
        device = first_device({"trailing_edge_device": {"servo": SERVO_MM}})
        servo = device.servo
        assert isinstance(servo, Servo)
        for name, expected in servo_attributes().items():
            assert_close(getattr(servo, name), expected)
        assert servo.component_id is None

    def test_servo_component_id_is_kept_and_all_dimensions_are_required(self) -> None:
        device = first_device({"trailing_edge_device": {"servo": SERVO_MM | {"component_id": 7}}})
        assert isinstance(device.servo, Servo)
        assert device.servo.component_id == 7
        for missing in SERVO_MM:
            partial = {k: v for k, v in SERVO_MM.items() if k != missing}
            reject_first_section({"trailing_edge_device": {"servo": partial}}, missing)

    def test_dumped_model_does_not_parse_again(self) -> None:
        """A converted field renamed to SI cannot be scaled twice by a re-parse."""
        rib = parse_first_section(
            {"trailing_edge_device": {"hinge_spacing": 0.5, "servo": SERVO_MM}}
        )
        dumped = rib.model_dump()
        with pytest.raises(ValidationError, match="extra_forbidden"):
            WingXSec.model_validate(dumped)


class TestTurbulator:
    def test_height_is_converted_and_defaults_apply(self) -> None:
        turbulator = first_turbulator({"turbulator": {"position_root": 0.3, "height_mm": 0.4}})
        assert_close(turbulator.height_m, 0.0004)
        assert (turbulator.position_root, turbulator.position_tip) == (0.3, None)
        assert (turbulator.form, turbulator.enabled) == ("zigzag", True)

    def test_default_height_is_the_format_default_in_metres(self) -> None:
        turbulator = first_turbulator({"turbulator": {"position_root": 0.3}})
        assert_close(turbulator.height_m, 0.0003)

    def test_other_fields_and_rejections(self) -> None:
        detail = {"position_root": 0.3, "position_tip": 0.35, "form": "dots", "enabled": False}
        turbulator = first_turbulator({"turbulator": detail})
        assert (turbulator.position_tip, turbulator.form, turbulator.enabled) == (
            0.35,
            "dots",
            False,
        )
        reject_first_section({"turbulator": {}}, "position_root")
        reject_first_section({"turbulator": {"position_root": 0.3, "form": "wave"}}, "form")
        reject_first_section({"turbulator": {"position_root": 0.3, "height_mm": "1"}}, "height_mm")
        reject_first_section(
            {"turbulator": {"position_root": 0.3, "height_m": 0.001}}, "extra_forbidden"
        )


class TestAirfoil:
    @pytest.mark.parametrize(
        "designation", ["naca2412", "NACA0012", "./airfoils/mh45.dat", "https://x/y.dat"]
    )
    def test_a_string_is_kept_verbatim(self, designation: str) -> None:
        assert parse_first_section({"airfoil": designation}).airfoil == designation

    def test_inline_coordinates_parse_as_tuples(self) -> None:
        coordinates = [[1, 0], [0.5, 0.06], [0.0, 0.0], [0.5, -0.06], [1.0, 0.0]]
        airfoil = parse_first_section({"airfoil": {"coordinates": coordinates}}).airfoil
        assert isinstance(airfoil, InlineAirfoil)
        assert airfoil.coordinates[0] == (1.0, 0.0)
        assert len(airfoil.coordinates) == 5

    @pytest.mark.parametrize(
        "airfoil",
        [
            {"coordinates": [[1.0]]},
            {"coordinates": [[1.0, "0"]]},
            {"coordinates": [[1.0, 0.0]], "n": 1},
            {},
            None,
        ],
    )
    def test_malformed_airfoil_is_rejected(self, airfoil: object) -> None:
        reject_first_section({"airfoil": airfoil}, "airfoil")

    def test_an_empty_or_open_contour_still_parses(self) -> None:
        assert parse_first_section({"airfoil": {"coordinates": []}}).airfoil == InlineAirfoil(
            coordinates=()
        )


def test_all_pins_the_public_names() -> None:
    assert sorted(geometry.__all__) == sorted(
        [
            "Airfoil",
            "AirplaneGeometry",
            "ControlSurface",
            "Fuselage",
            "FuselageXSecSuperEllipse",
            "InlineAirfoil",
            "Servo",
            "SurfaceType",
            "SpareDetail",
            "TrailingEdgeDevice",
            "Turbulator",
            "Wing",
            "WingUnits",
            "WingXSec",
        ]
    )
    for name in geometry.__all__:
        assert hasattr(geometry, name)


@pytest.mark.parametrize(
    "name", [n for n in geometry.__all__ if n not in {"Airfoil", "SurfaceType"}]
)
def test_docstring_documents_every_attribute(name: str) -> None:
    model = getattr(geometry, name)
    doc = model.__doc__ or ""
    undocumented = [
        f for f in model.model_fields if not re.search(rf"^\s+{re.escape(f)}:", doc, re.MULTILINE)
    ]
    assert undocumented == []


class TestNoPhysicalConstraint:
    def test_inadmissible_but_well_typed_values_parse(self) -> None:
        """Each of these becomes an input_error in validate.py, never a ValidationError."""
        wing = minimal_wing()
        sections = wing["x_secs"]
        sections[0] |= {
            "chord": -0.1,
            "number_interpolation_points": 0,
            "trailing_edge_device": {
                "positive_deflection_deg": 400,
                "mix_gain_primary": 10,
                "servo": SERVO_MM | {"length": -1},
            },
        }
        fuselage = fuselage_doc()
        fuselage["x_secs"] = [{"xyz": [0, 0, 0], "a": -1, "b": 0.1, "n": -2}]
        airplane = AirplaneGeometry.model_validate(
            {
                "name": "A",
                "total_mass_kg": -1,
                "wings": {"W": wing},
                "fuselages": {"F": fuselage},
            }
        )
        assert airplane.total_mass_kg == -1
        assert airplane.wings is not None
        rib = airplane.wings["W"].x_secs[0]
        assert rib.chord == -0.1
        assert rib.number_interpolation_points == 0
        assert rib.trailing_edge_device is not None
        assert rib.trailing_edge_device.positive_deflection_deg == 400
        assert rib.trailing_edge_device.mix_gain_primary == 10
        assert isinstance(rib.trailing_edge_device.servo, Servo)
        assert rib.trailing_edge_device.servo.length_m == -0.001
        assert airplane.fuselages is not None
        assert len(airplane.fuselages["F"].x_secs) == 1
        assert airplane.fuselages["F"].x_secs[0].a == -1


class TestSiNamesAreNotInput:
    """A converted field is only readable under the format key, so a re-parse cannot rescale it."""

    @pytest.mark.parametrize("key", sorted(SERVO_MM))
    def test_servo_rejects_its_si_key(self, key: str) -> None:
        servo = {k: v for k, v in SERVO_MM.items() if k != key} | {f"{key}_m": 0.02}
        reject_first_section({"trailing_edge_device": {"servo": servo}}, "servo")

    @pytest.mark.parametrize("key", ["hinge_spacing", "side_spacing_root", "side_spacing_tip"])
    def test_device_rejects_a_spacing_under_its_si_key(self, key: str) -> None:
        reject_first_section({"trailing_edge_device": {f"{key}_m": 0.001}}, f"{key}_m")

    def test_turbulator_rejects_its_height_under_the_si_key(self) -> None:
        reject_first_section({"turbulator": {"position_root": 0.3, "height_m": 0.001}}, "height_m")


def distinct_document() -> Doc:
    """A document in which every number is different and non-zero, to expose a wrong scale."""
    servo = {name: 10.0 + index for index, name in enumerate(SERVO_MM)}
    device = {
        "rel_chord_root": 0.71, "rel_chord_tip": 0.72, "hinge_spacing": 0.53,
        "side_spacing_root": 2.54, "side_spacing_tip": 3.55, "servo": servo,
        "rel_chord_servo_position": 0.56, "rel_length_servo_position": 0.57,
        "positive_deflection_deg": 23.5, "negative_deflection_deg": -19.5, "deflection_deg": 4.5,
        "trailing_edge_offset_factor": 1.15, "mix_gain_primary": 1.7, "mix_gain_secondary": 0.9,
        "differential_ratio": 1.4,
    }  # fmt: skip
    spar = {
        "spare_support_dimension_width": 0.0061, "spare_support_dimension_height": 0.0042,
        "spare_position_factor": 0.31, "spare_length": 0.43, "spare_start": 0.05,
        "spare_vector": [0.1, 0.9, 0.2], "spare_origin": [0.11, 0.12, 0.13],
    }  # fmt: skip
    rib = {
        "xyz_le": [0.011, 0.022, 0.033], "chord": 0.2345, "twist": 1.5, "dihedral": 2.5,
        "airfoil": "naca2412",
        "control_surface": {"name": "A", "hinge_point": 0.77, "deflection": 6.5},
        "spare_list": [spar], "trailing_edge_device": device,
        "turbulator": {"position_root": 0.33, "position_tip": 0.36, "height_mm": 0.45},
    }  # fmt: skip
    tip = {"xyz_le": [0.1, 1.2, 0.3], "chord": 0.12, "twist": -1.5, "airfoil": "naca2412"}
    station = {"xyz": [0.4, 0.015, 0.025], "a": 0.081, "b": 0.062, "n": 2.3, "n_lower": 4.7}
    return {
        "name": "D", "total_mass_kg": 2.75, "xyz_ref": [0.101, 0.002, 0.003],
        "wings": {"W": {"name": "W", "x_secs": [rib, tip]}},
        "fuselages": {"F": {"name": "F", "x_secs": [station, station]}},
    }  # fmt: skip


class TestUnitsAreConvertedExactlyWhereDocumented:
    def test_non_millimetre_numbers_are_unscaled_and_millimetre_numbers_are_scaled(self) -> None:
        airplane = AirplaneGeometry.model_validate(distinct_document())
        assert airplane.total_mass_kg == 2.75
        assert airplane.xyz_ref == (0.101, 0.002, 0.003)
        assert airplane.wings is not None
        rib, tip = airplane.wings["W"].x_secs
        assert rib.xyz_le == (0.011, 0.022, 0.033)
        assert (rib.chord, rib.twist, rib.dihedral) == (0.2345, 1.5, 2.5)
        assert tip.xyz_le == (0.1, 1.2, 0.3)
        assert (tip.chord, tip.twist) == (0.12, -1.5)
        surface = rib.control_surface
        assert surface is not None
        assert (surface.hinge_point, surface.deflection) == (0.77, 6.5)
        assert rib.spare_list is not None
        spar = rib.spare_list[0]
        assert (spar.spare_support_dimension_width, spar.spare_support_dimension_height) == (
            0.0061,
            0.0042,
        )
        assert (spar.spare_position_factor, spar.spare_length, spar.spare_start) == (
            0.31,
            0.43,
            0.05,
        )
        assert spar.spare_vector == (0.1, 0.9, 0.2)
        assert spar.spare_origin == (0.11, 0.12, 0.13)
        device = rib.trailing_edge_device
        assert device is not None
        assert (device.rel_chord_root, device.rel_chord_tip) == (0.71, 0.72)
        assert (device.rel_chord_servo_position, device.rel_length_servo_position) == (0.56, 0.57)
        assert (device.positive_deflection_deg, device.negative_deflection_deg) == (23.5, -19.5)
        assert device.deflection_deg == 4.5
        assert device.trailing_edge_offset_factor == 1.15
        assert (device.mix_gain_primary, device.mix_gain_secondary) == (1.7, 0.9)
        assert device.differential_ratio == 1.4
        turbulator = rib.turbulator
        assert turbulator is not None
        assert (turbulator.position_root, turbulator.position_tip) == (0.33, 0.36)
        assert airplane.fuselages is not None
        station = airplane.fuselages["F"].x_secs[0]
        assert station.xyz == (0.4, 0.015, 0.025)
        assert (station.a, station.b, station.n, station.n_lower) == (0.081, 0.062, 2.3, 4.7)
        # millimetre fields: x 1e-3
        assert_close(device.hinge_spacing_m, 0.00053)
        assert_close(device.side_spacing_root_m, 0.00254)
        assert_close(device.side_spacing_tip_m, 0.00355)
        assert_close(turbulator.height_m, 0.00045)
        assert isinstance(device.servo, Servo)
        for index, name in enumerate(SERVO_MM):
            assert_close(getattr(device.servo, f"{name}_m"), (10.0 + index) * 1e-3)


class TestStringsAreKeptVerbatim:
    def test_names_labels_paths_and_designations_are_not_normalised(self) -> None:
        document = distinct_document()
        document["name"] = "  Mixed Case  "
        wing = document["wings"]["W"]
        wing["name"] = " W "
        rib = wing["x_secs"][0]
        rib["airfoil"] = " NACA2412 "
        rib["control_surface"]["name"] = " Aileron "
        rib["trailing_edge_device"] |= {"name": " L ", "label": " left "}
        fuselage = document["fuselages"]["F"]
        fuselage |= {"name": " F ", "step_path": " a/b.step ", "solid_step_path": " c.step "}
        airplane = AirplaneGeometry.model_validate(document)
        assert airplane.name == "  Mixed Case  "
        assert airplane.wings is not None
        parsed_wing = airplane.wings["W"]
        assert parsed_wing.name == " W "
        parsed_rib = parsed_wing.x_secs[0]
        assert parsed_rib.airfoil == " NACA2412 "
        assert parsed_rib.control_surface is not None
        assert parsed_rib.control_surface.name == " Aileron "
        assert parsed_rib.trailing_edge_device is not None
        assert parsed_rib.trailing_edge_device.name == " L "
        assert parsed_rib.trailing_edge_device.label == " left "
        assert airplane.fuselages is not None
        parsed_fuselage = airplane.fuselages["F"]
        assert (parsed_fuselage.name, parsed_fuselage.step_path) == (" F ", " a/b.step ")
        assert parsed_fuselage.solid_step_path == " c.step "


def count_documents(value: object) -> dict[str, Doc]:
    """Schema-valid documents that put ``value`` into each of the three integer fields."""
    servo = SERVO_MM

    def doc(detail: Doc) -> Doc:
        wing = minimal_wing()
        wing["x_secs"][0] |= detail
        return airplane_with_wing(wing)

    return {
        "number_interpolation_points": doc({"number_interpolation_points": value}),
        "servo": doc({"trailing_edge_device": {"servo": value}}),
        "component_id": doc({"trailing_edge_device": {"servo": servo | {"component_id": value}}}),
    }


class TestCountAcceptsIntegerValuedFloats:
    """JSON Schema 'integer' admits 3.0; the model normalises it to int 3 (architect ruling)."""

    @pytest.mark.parametrize("field", ["number_interpolation_points", "servo", "component_id"])
    def test_integer_valued_float_becomes_an_int(self, field: str) -> None:
        airplane = AirplaneGeometry.model_validate(count_documents(3.0)[field])
        assert airplane.wings is not None
        rib = airplane.wings["W"].x_secs[0]
        if field == "number_interpolation_points":
            parsed = rib.number_interpolation_points
        else:
            assert rib.trailing_edge_device is not None
            servo = rib.trailing_edge_device.servo
            parsed = servo.component_id if isinstance(servo, Servo) else servo
        assert parsed == 3
        assert type(parsed) is int

    @pytest.mark.parametrize("field", ["number_interpolation_points", "servo", "component_id"])
    @pytest.mark.parametrize("value", [3.5, True, "3", float("nan"), float("inf")])
    def test_other_values_are_rejected(self, field: str, value: object) -> None:
        with pytest.raises(ValidationError, match=field):
            AirplaneGeometry.model_validate(count_documents(value)[field])

    @pytest.mark.parametrize("field", ["number_interpolation_points", "servo", "component_id"])
    @pytest.mark.parametrize("value", [3, 3.0, 3.5, True, False, "3", None, 1e300])
    def test_model_agrees_with_the_json_schema(self, field: str, value: object) -> None:
        # jsonschema ships no type information: Any is the honest type at this boundary
        validator: Any = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
        document = count_documents(value)[field]
        by_schema = bool(validator.is_valid(document))
        try:
            AirplaneGeometry.model_validate(document)
            by_model = True
        except ValidationError:
            by_model = False
        # Not compared: the schema's exclusiveMinimum on number_interpolation_points. The model
        # carries no physical bound (ch. 8.11), so 0 and -2 are validate.py's business.
        assert by_model == by_schema, (field, value)
