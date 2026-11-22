"""Spar section modulus and the bending capacity of the wing at a station (gh-1427).

Hand values: the section moduli are worked out from ``W = I / (h / 2)`` with the second moment of
area of each shape; the strength is a TEST VALUE (spar_builders.TEST_STRENGTH_PA), no real material.
"""

import json
import math
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.errors import FormulaError
from aero_kernel.geometry import AirplaneGeometry, CappedSection, SpareDetail, Wing, WingXSec
from aero_kernel.spar_capacity import (
    BendingCapacity,
    CapacityUnknown,
    NoSparAtStation,
    SparCapacity,
    bending_capacity,
    section_modulus,
)
from aero_kernel.tests.spar_builders import (
    CAPPED,
    RECTANGULAR,
    ROD,
    TEST_STRENGTH_PA,
    TUBE,
    material_with,
    spar,
    wing,
)

MATERIALS = {"test": material_with()}
# W of RECTANGULAR: b h^2 / 6 = 0.02 * 0.003^2 / 6 = 3.0e-8 m^3
RECTANGULAR_W = 3.0e-8
RECTANGULAR_M = RECTANGULAR_W * TEST_STRENGTH_PA  # 3.0 N m
# W of TUBE: pi (Do^4 - Di^4) / (32 Do), Do = 16 mm, Di = 14 mm
TUBE_W = 1.6640623586983438e-07
TUBE_M = TUBE_W * TEST_STRENGTH_PA


def close(actual: float | None, expected: float) -> bool:
    """Whether ``actual`` equals ``expected`` up to rounding (no ``None``)."""
    return actual is not None and math.isclose(actual, expected, rel_tol=1e-9)


def moment(wing: Wing, y: float, materials: Any) -> float | None:
    """The capacity in N m, or ``None`` for any outcome that is not a value (tested separately)."""
    outcome = bending_capacity(wing, y, materials)
    return outcome.moment_nm if isinstance(outcome, BendingCapacity) else None


def outcome_at(wing: Wing, y: float) -> SparCapacity:
    """The typed outcome at a station, with the test materials."""
    return bending_capacity(wing, y, MATERIALS)


def section_of(section: dict[str, Any]) -> Any:
    """The parsed section of a spar entry."""
    section_object = SpareDetail.model_validate(spar(section=section)).section
    assert section_object is not None
    return section_object


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        # rod: W = pi d^3 / 32, d = 10 mm
        (ROD, math.pi * 0.01**3 / 32.0),
        (TUBE, TUBE_W),
        # rectangular: W = b h^2 / 6
        (RECTANGULAR, RECTANGULAR_W),
        # capped, flanges only: W = b (H^3 - h^3) / (6 H), b = 4 mm, H = 14.7 mm, h = H - 2 t = 12.7 mm
        (CAPPED, 5.116281179138321e-08),
    ],
)
def test_section_modulus_matches_the_hand_value(section: dict[str, Any], expected: float) -> None:
    assert close(section_modulus(section_of(section)), expected)


def test_the_rod_modulus_is_the_exact_value_not_the_one_tenth_rule() -> None:
    modulus = section_modulus(section_of(ROD))
    assert abs(modulus - 9.8175e-8) < 1e-11  # pi d^3 / 32 for d = 10 mm
    assert modulus < 1.0e-7  # d^3 / 10 would be 1.0e-7


def test_the_capped_web_does_not_count() -> None:
    """The modulus of the capped shape equals that of two flanges alone (no web member)."""
    b, big_h, t = 0.004, 0.0147, 0.001
    inertia_flanges = 2 * (b * t**3 / 12 + b * t * ((big_h - t) / 2) ** 2)
    assert close(section_modulus(section_of(CAPPED)), inertia_flanges / (big_h / 2))


def test_capacity_is_modulus_times_strength() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert close(moment(main, 0.25, MATERIALS), RECTANGULAR_M)


def test_capacity_holds_at_the_root_and_at_the_tip_of_the_wing() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert close(moment(main, 0.0, MATERIALS), RECTANGULAR_M)
    assert close(moment(main, 0.5, MATERIALS), RECTANGULAR_M)  # last rib closes


def test_no_safety_factor_is_in_the_capacity() -> None:
    """Doubling the strength doubles the capacity: nothing else enters."""
    doubled = {"test": material_with(2 * TEST_STRENGTH_PA)}
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert close(moment(main, 0.1, doubled), 2 * RECTANGULAR_M)


def test_a_spar_without_section_has_no_capacity() -> None:
    assert moment(wing([spar()]), 0.25, MATERIALS) is None


def test_a_station_without_any_spar_has_no_capacity() -> None:
    assert moment(wing(None), 0.25, MATERIALS) is None


def test_start_and_length_give_the_spanwise_extent_inside_the_segment() -> None:
    main = wing([spar(section=RECTANGULAR, material="test", spare_start=0.1, spare_length=0.2)])
    assert moment(main, 0.05, MATERIALS) is None
    assert close(moment(main, 0.1, MATERIALS), RECTANGULAR_M)
    assert close(moment(main, 0.3, MATERIALS), RECTANGULAR_M)
    assert moment(main, 0.35, MATERIALS) is None


def test_the_extent_is_measured_along_the_leading_edge_line_of_the_segment() -> None:
    """Rib 1 is 0.3 m out in y and 0.4 m up in z: the segment is 0.5 m long, 0.6 of it in y."""
    sloped_spar = spar(section=RECTANGULAR, material="test", spare_start=0.25, spare_length=0.1)
    sloped = Wing.model_validate(
        {
            "name": "Main",
            "surface_type": "main_wing",
            "x_secs": [
                {
                    "xyz_le": [0.0, 0.0, 0.0],
                    "chord": 0.2,
                    "twist": 0.0,
                    "airfoil": "NACA 2412",
                    "spare_list": [sloped_spar],
                },
                {"xyz_le": [0.0, 0.3, 0.4], "chord": 0.2, "twist": 0.0, "airfoil": "NACA 2412"},
            ],
        }
    )
    # 0.25 m along the line is 0.15 m in y; 0.35 m along is 0.21 m in y
    assert moment(sloped, 0.14, MATERIALS) is None
    assert close(moment(sloped, 0.15, MATERIALS), RECTANGULAR_M)
    assert close(moment(sloped, 0.21, MATERIALS), RECTANGULAR_M)
    assert moment(sloped, 0.22, MATERIALS) is None


def test_each_segment_is_read_from_its_own_entry_so_a_continued_spar_is_not_counted_twice() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_mode="standard_backward")
    second = spar(section=TUBE, material="test", spare_mode="standard_backward")
    main = wing([first], [second])
    assert close(moment(main, 0.25, MATERIALS), RECTANGULAR_M)
    assert close(moment(main, 0.75, MATERIALS), TUBE_M)
    assert close(moment(main, 0.5, MATERIALS), TUBE_M)  # a rib belongs outboard


def test_the_front_spar_carries_the_bending_alone() -> None:
    """BR-W16: the rear spar carries the torsion; its capacity is not added."""
    front = spar(section=RECTANGULAR, material="test", spare_position_factor=0.25)
    rear = spar(section=CAPPED, material="test", spare_position_factor=0.7)
    for ordered in ([front, rear], [rear, front]):
        assert close(moment(wing(ordered), 0.25, MATERIALS), RECTANGULAR_M)


def test_a_front_spar_without_section_gives_no_capacity_not_the_rear_spars() -> None:
    front = spar(spare_position_factor=0.25)
    rear = spar(section=CAPPED, material="test", spare_position_factor=0.7)
    assert moment(wing([front, rear]), 0.25, MATERIALS) is None


def test_a_spar_that_has_ended_leaves_the_other_as_the_front_spar() -> None:
    short_front = spar(
        section=RECTANGULAR, material="test", spare_position_factor=0.25, spare_length=0.1
    )
    rear = spar(section=TUBE, material="test", spare_position_factor=0.7)
    assert close(moment(wing([short_front, rear]), 0.3, MATERIALS), TUBE_M)


def test_two_spars_without_a_position_to_tell_the_front_one_fail() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=None)
    second = spar(section=TUBE, material="test", spare_position_factor=0.7)
    with pytest.raises(FormulaError) as caught:
        moment(wing([first, second]), 0.25, MATERIALS)
    assert caught.value.code == "front_spar_not_determinable"


def test_two_spars_at_one_position_fail() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=0.25)
    second = spar(section=TUBE, material="test", spare_position_factor=0.25)
    with pytest.raises(FormulaError) as caught:
        moment(wing([first, second]), 0.25, MATERIALS)
    assert caught.value.code == "front_spar_not_determinable"


def test_a_single_spar_needs_no_position() -> None:
    only = spar(section=RECTANGULAR, material="test", spare_position_factor=None)
    assert close(moment(wing([only]), 0.25, MATERIALS), RECTANGULAR_M)


def test_a_section_without_material_fails_and_nothing_is_substituted() -> None:
    main = wing([spar(section=RECTANGULAR)])
    with pytest.raises(FormulaError) as caught:
        moment(main, 0.25, MATERIALS)
    assert caught.value.code == "spar_material_missing"
    assert "x_secs[0].spare_list[0]" in caught.value.message


def test_a_material_key_that_the_components_do_not_hold_fails() -> None:
    main = wing([spar(section=RECTANGULAR, material="birch")])
    with pytest.raises(FormulaError) as caught:
        moment(main, 0.25, MATERIALS)
    assert caught.value.code == "spar_material_unknown"
    assert "birch" in caught.value.message


def test_pushed_components_without_a_materials_table_fail_like_an_unknown_key() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    with pytest.raises(FormulaError) as caught:
        moment(main, 0.25, None)
    assert caught.value.code == "spar_material_unknown"


def test_a_material_without_strength_fails() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    with pytest.raises(FormulaError) as caught:
        moment(main, 0.25, {"test": material_with(None)})
    assert caught.value.code == "spar_material_without_strength"


def test_a_spar_without_section_needs_no_material_and_no_table() -> None:
    assert moment(wing([spar(material="birch")]), 0.25, None) is None


def test_another_segments_failure_does_not_matter_at_a_station_it_does_not_cover() -> None:
    good = spar(section=RECTANGULAR, material="test")
    bad = spar(section=RECTANGULAR, material="missing")
    assert close(moment(wing([good], [bad]), 0.25, MATERIALS), RECTANGULAR_M)


# --- typed outcomes: "no spar" and "unknown" are not values and are not each other ---------------


def test_a_capacity_is_a_typed_value() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    outcome = outcome_at(main, 0.25)
    assert isinstance(outcome, BendingCapacity)
    assert close(outcome.moment_nm, RECTANGULAR_M)


def test_a_station_with_no_spar_is_the_no_spar_outcome() -> None:
    assert isinstance(outcome_at(wing(None), 0.25), NoSparAtStation)
    assert isinstance(outcome_at(wing([]), 0.25), NoSparAtStation)


def test_a_station_where_every_spar_has_ended_is_the_no_spar_outcome() -> None:
    ended = spar(section=RECTANGULAR, material="test", spare_start=0.1, spare_length=0.1)
    assert isinstance(outcome_at(wing([ended]), 0.4), NoSparAtStation)
    assert isinstance(outcome_at(wing([ended]), 0.05), NoSparAtStation)


def test_a_present_front_spar_without_section_is_the_unknown_outcome_naming_it() -> None:
    outcome = outcome_at(wing([spar()]), 0.25)
    assert isinstance(outcome, CapacityUnknown)
    assert (outcome.wing, outcome.x_sec, outcome.spar) == ("Main", 0, 0)
    assert outcome.reason == "front_spar_without_section"


def test_the_rear_spar_never_stands_in_for_a_present_front_spar() -> None:
    front = spar(spare_position_factor=0.25)
    rear = spar(section=CAPPED, material="test", spare_position_factor=0.7)
    outcome = outcome_at(wing([front, rear]), 0.25)
    assert isinstance(outcome, CapacityUnknown)
    assert outcome.spar == 0


def test_the_three_outcomes_are_distinct_types() -> None:
    seen = {
        type(outcome_at(wing([spar(section=RECTANGULAR, material="test")]), 0.25)),
        type(outcome_at(wing(None), 0.25)),
        type(outcome_at(wing([spar()]), 0.25)),
    }
    assert seen == {BendingCapacity, NoSparAtStation, CapacityUnknown}


@pytest.mark.parametrize("station", [-0.1, 0.6, math.nan, math.inf, -math.inf])
def test_a_station_outside_the_half_span_is_an_error_not_an_outcome(station: float) -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    with pytest.raises(FormulaError) as caught:
        bending_capacity(main, station, MATERIALS)
    assert caught.value.code == "station_outside_wing"


def test_the_stations_of_the_wing_ends_are_admissible() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert isinstance(outcome_at(main, 0.0), BendingCapacity)
    assert isinstance(outcome_at(main, 0.5), BendingCapacity)


# --- the front-spar errors name the spars; nothing odd flows through min -------------------------


def test_the_front_spar_error_names_the_spars_and_their_positions() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=None)
    second = spar(section=TUBE, material="test", spare_position_factor=0.7)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing([first, second]), 0.25, MATERIALS)
    error = caught.value
    assert error.code == "front_spar_not_determinable"
    assert "spar 0" in error.message
    assert "spar 1" in error.message
    assert error.detail["spars"] == [0, 1]


def test_a_nan_position_factor_does_not_flow_through_the_minimum() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=math.nan)
    second = spar(section=TUBE, material="test", spare_position_factor=0.7)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing([first, second]), 0.25, MATERIALS)
    assert caught.value.code == "front_spar_not_determinable"


# --- the spanwise extent follows the construction, mode by mode -----------------------------------


def two_rib_wing(
    spar_fields: dict[str, Any], tip: tuple[float, float, float], tip_chord: float
) -> Wing:
    """One segment from the origin (chord 0.2) to ``tip`` (leading edge) with ``tip_chord``."""
    return Wing.model_validate(
        {
            "name": "Main",
            "surface_type": "main_wing",
            "x_secs": [
                {
                    "xyz_le": [0.0, 0.0, 0.0],
                    "chord": 0.2,
                    "twist": 0.0,
                    "airfoil": "NACA 2412",
                    "spare_list": [spar(**spar_fields)],
                },
                {"xyz_le": list(tip), "chord": tip_chord, "twist": 0.0, "airfoil": "NACA 2412"},
            ],
        }
    )


def test_standard_mode_runs_along_the_line_between_the_chord_position_points() -> None:
    """Quarter chord: x 0.05 at the root, 0.1 + 0.025 at the tip; axis 0.5056 m, 0.9889 of it in y."""
    fields = {"section": RECTANGULAR, "material": "test", "spare_start": 0.2}
    tapered = two_rib_wing(fields, tip=(0.1, 0.5, 0.0), tip_chord=0.1)
    # start at 0.2 m along the axis is y = 0.19778 (along the leading edge line it would be 0.19612)
    assert isinstance(outcome_at(tapered, 0.1970), NoSparAtStation)
    assert isinstance(outcome_at(tapered, 0.1980), BendingCapacity)


def test_normal_mode_with_a_vector_runs_along_that_vector() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_vector": [0.0, 0.8, 0.6],
        "spare_start": 0.1,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    # 0.1 m along a unit direction with y component 0.8 is y = 0.08
    assert isinstance(outcome_at(wing_, 0.079), NoSparAtStation)
    assert isinstance(outcome_at(wing_, 0.081), BendingCapacity)


def test_normal_mode_origin_is_an_offset_from_the_segment_root() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_vector": [0.0, 1.0, 0.0],
        "spare_origin": [0.0, 0.2, 0.0],
        "spare_start": 0.05,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    assert isinstance(outcome_at(wing_, 0.24), NoSparAtStation)
    assert isinstance(outcome_at(wing_, 0.26), BendingCapacity)


def test_a_spar_starting_at_zero_with_a_length_extends_both_ways_from_its_origin() -> None:
    """The creator extrudes in both directions when spare_start is 0 (VaseModeWingCreator.py:813-817)."""
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_vector": [0.0, 1.0, 0.0],
        "spare_origin": [0.0, 0.2, 0.0],
        "spare_length": 0.1,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    assert isinstance(outcome_at(wing_, 0.09), NoSparAtStation)
    assert isinstance(outcome_at(wing_, 0.11), BendingCapacity)
    assert isinstance(outcome_at(wing_, 0.29), BendingCapacity)
    assert isinstance(outcome_at(wing_, 0.31), NoSparAtStation)


def test_a_spar_with_a_start_but_no_length_runs_to_the_end_of_the_segment() -> None:
    fields = {"section": RECTANGULAR, "material": "test", "spare_start": 0.3}
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    assert isinstance(outcome_at(wing_, 0.29), NoSparAtStation)
    assert isinstance(outcome_at(wing_, 0.5), BendingCapacity)


@pytest.mark.parametrize("mode", ["follow", "standard_backward", "orthogonal_backward"])
def test_a_continued_spar_with_start_or_length_is_a_declared_failure_naming_the_mode(
    mode: str,
) -> None:
    fields = {"section": RECTANGULAR, "material": "test", "spare_mode": mode, "spare_length": 0.2}
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing_, 0.1, MATERIALS)
    assert caught.value.code == "spar_extent_not_determinable"
    assert mode in caught.value.message


def test_standard_mode_without_a_position_factor_cannot_place_a_partial_spar() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_position_factor": None,
        "spare_start": 0.1,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing_, 0.2, MATERIALS)
    assert caught.value.code == "spar_extent_not_determinable"


def test_a_full_segment_spar_needs_no_axis_in_any_mode() -> None:
    for mode in ("standard", "normal", "follow", "standard_backward", "orthogonal_backward"):
        fields = {"section": RECTANGULAR, "material": "test", "spare_mode": mode}
        wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
        assert isinstance(outcome_at(wing_, 0.25), BendingCapacity)


def test_an_axis_without_a_spanwise_component_is_a_declared_failure() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_vector": [1.0, 0.0, 0.0],
        "spare_start": 0.1,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing_, 0.2, MATERIALS)
    assert caught.value.code == "spar_extent_not_determinable"


# --- BRYAN: the recorded I-spar, mapped by the smallest-section convention -----------------------

BRYAN = (
    Path(__file__).resolve().parents[2]
    / "scripts/canon_checks/reference_fleet/bryan/bryan.airplane.json"
)


def bryan_wing() -> Wing:
    wings = AirplaneGeometry.model_validate(json.loads(BRYAN.read_text())).wings
    assert wings is not None
    return wings["Tragflaeche"]


def bryan_ribs() -> list[WingXSec]:
    return list(bryan_wing().x_secs)


def main_spar(rib: WingXSec, index: int = 0) -> SpareDetail:
    assert rib.spare_list is not None
    return rib.spare_list[index]


def test_bryan_segments_carry_the_section_of_their_outboard_rib() -> None:
    ribs = bryan_ribs()
    for segment in range(12):
        spar_here = main_spar(ribs[segment])
        outboard = main_spar(ribs[segment + 1])
        section = spar_here.section
        assert isinstance(section, CappedSection)
        assert section.width == outboard.spare_support_dimension_width
        assert section.height == outboard.spare_support_dimension_height
        assert section.flange_thickness == 0.001
        assert spar_here.material == "birch_ply"


def test_bryan_segment_12_and_the_rear_spar_carry_no_section() -> None:
    ribs = bryan_ribs()
    assert main_spar(ribs[12]).section is None
    assert all(main_spar(rib, 1).section is None for rib in ribs[:6])


def test_bryan_capacity_at_the_root_is_the_hand_value_of_the_flanges() -> None:
    """W = b (H^3 - h^3) / (6 H), b = 3.98 mm, H = 14.34 mm, h = H - 2 mm: 4.9483e-8 m^3."""
    outcome = bending_capacity(bryan_wing(), 0.0, {"birch_ply": material_with()})
    assert isinstance(outcome, BendingCapacity)
    assert close(outcome.moment_nm, 4.948326043700604e-08 * TEST_STRENGTH_PA)


def test_a_zero_vector_cannot_place_a_partial_spar() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_vector": [0.0, 0.0, 0.0],
        "spare_start": 0.1,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing_, 0.2, MATERIALS)
    assert caught.value.code == "spar_extent_not_determinable"


def test_normal_mode_without_a_vector_follows_the_segment_plane_not_the_sweep() -> None:
    """The plane's y axis has no x component: a swept tip changes nothing, dihedral does."""
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "normal",
        "spare_start": 0.25,
    }
    swept = two_rib_wing(fields, tip=(0.3, 0.3, 0.4), tip_chord=0.2)
    # 0.25 m along a direction with y component 0.3 / 0.5 = 0.6 is y = 0.15
    assert isinstance(outcome_at(swept, 0.149), NoSparAtStation)
    assert isinstance(outcome_at(swept, 0.151), BendingCapacity)


def test_standard_mode_origin_is_an_absolute_point() -> None:
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_mode": "standard",
        "spare_vector": [0.0, 1.0, 0.0],
        "spare_origin": [0.0, 0.2, 0.0],
        "spare_start": 0.05,
    }
    wing_ = two_rib_wing(fields, tip=(0.0, 0.5, 0.0), tip_chord=0.2)
    assert isinstance(outcome_at(wing_, 0.24), NoSparAtStation)
    assert isinstance(outcome_at(wing_, 0.26), BendingCapacity)


def test_a_partial_spar_of_an_outboard_segment_is_measured_from_the_root_rib_of_its_segment() -> (
    None
):
    """Ribs at y = 0, 0.5, 1.0; the second segment's spar starts 0.1 m and is 0.2 m long.

    Its axis begins at the root rib of the segment (y = 0.5), so it covers y = 0.6 to 0.8 and not
    0.1 to 0.3 (the origin of the wing).
    """
    first = spar(section=RECTANGULAR, material="test")
    second = spar(section=RECTANGULAR, material="test", spare_start=0.1, spare_length=0.2)
    wing_ = wing([first], [second])
    assert isinstance(outcome_at(wing_, 0.55), NoSparAtStation)
    for y in (0.6, 0.65, 0.8):
        assert isinstance(outcome_at(wing_, y), BendingCapacity), y
    assert isinstance(outcome_at(wing_, 0.85), NoSparAtStation)


def test_normal_mode_offset_and_standard_mode_point_differ_in_an_outboard_segment() -> None:
    """The second segment starts at y = 0.5; the spar axis is the y direction with origin y 0.2, start 0.05.

    Normal mode: the origin is an offset from the segment root, so the spar starts at
    0.5 + 0.2 + 0.05 = 0.75. Standard mode: the origin is an absolute point, so it starts at
    0.2 + 0.05 = 0.25, before the segment, and the spar is present over the whole segment.
    """
    first = spar(section=RECTANGULAR, material="test")
    fields = {
        "section": RECTANGULAR,
        "material": "test",
        "spare_vector": [0.0, 1.0, 0.0],
        "spare_origin": [0.0, 0.2, 0.0],
        "spare_start": 0.05,
    }
    normal = wing([first], [spar(**fields, spare_mode="normal")])
    standard = wing([first], [spar(**fields, spare_mode="standard")])
    assert isinstance(outcome_at(normal, 0.74), NoSparAtStation)
    assert isinstance(outcome_at(normal, 0.76), BendingCapacity)
    assert isinstance(outcome_at(standard, 0.51), BendingCapacity)
    assert isinstance(outcome_at(standard, 0.74), BendingCapacity)
