"""Spar section modulus and the bending capacity of the wing at a station (gh-1427).

Hand values: the section moduli are worked out from ``W = I / (h / 2)`` with the second moment of
area of each shape; the strength is a TEST VALUE (spar_builders.TEST_STRENGTH_PA), no real material.
"""

import math
from typing import Any

import pytest
from aero_kernel.errors import FormulaError
from aero_kernel.geometry import SpareDetail, Wing
from aero_kernel.spar_capacity import bending_capacity, section_modulus
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
    assert close(bending_capacity(main, 0.25, MATERIALS), RECTANGULAR_M)


def test_capacity_holds_at_the_root_and_at_the_tip_of_the_wing() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert close(bending_capacity(main, 0.0, MATERIALS), RECTANGULAR_M)
    assert close(bending_capacity(main, 0.5, MATERIALS), RECTANGULAR_M)  # last rib closes


def test_no_safety_factor_is_in_the_capacity() -> None:
    """Doubling the strength doubles the capacity: nothing else enters."""
    doubled = {"test": material_with(2 * TEST_STRENGTH_PA)}
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert close(bending_capacity(main, 0.1, doubled), 2 * RECTANGULAR_M)


def test_a_spar_without_section_has_no_capacity() -> None:
    assert bending_capacity(wing([spar()]), 0.25, MATERIALS) is None


def test_a_station_without_any_spar_has_no_capacity() -> None:
    assert bending_capacity(wing(None), 0.25, MATERIALS) is None


def test_a_station_outside_the_wing_has_no_capacity() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    assert bending_capacity(main, 0.75, MATERIALS) is None
    assert bending_capacity(main, -0.1, MATERIALS) is None


def test_start_and_length_give_the_spanwise_extent_inside_the_segment() -> None:
    main = wing([spar(section=RECTANGULAR, material="test", spare_start=0.1, spare_length=0.2)])
    assert bending_capacity(main, 0.05, MATERIALS) is None
    assert close(bending_capacity(main, 0.1, MATERIALS), RECTANGULAR_M)
    assert close(bending_capacity(main, 0.3, MATERIALS), RECTANGULAR_M)
    assert bending_capacity(main, 0.35, MATERIALS) is None


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
    assert bending_capacity(sloped, 0.14, MATERIALS) is None
    assert close(bending_capacity(sloped, 0.15, MATERIALS), RECTANGULAR_M)
    assert close(bending_capacity(sloped, 0.21, MATERIALS), RECTANGULAR_M)
    assert bending_capacity(sloped, 0.22, MATERIALS) is None


def test_each_segment_is_read_from_its_own_entry_so_a_continued_spar_is_not_counted_twice() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_mode="standard_backward")
    second = spar(section=TUBE, material="test", spare_mode="standard_backward")
    main = wing([first], [second])
    assert close(bending_capacity(main, 0.25, MATERIALS), RECTANGULAR_M)
    assert close(bending_capacity(main, 0.75, MATERIALS), TUBE_M)
    assert close(bending_capacity(main, 0.5, MATERIALS), TUBE_M)  # a rib belongs outboard


def test_the_front_spar_carries_the_bending_alone() -> None:
    """BR-W16: the rear spar carries the torsion; its capacity is not added."""
    front = spar(section=RECTANGULAR, material="test", spare_position_factor=0.25)
    rear = spar(section=CAPPED, material="test", spare_position_factor=0.7)
    for ordered in ([front, rear], [rear, front]):
        assert close(bending_capacity(wing(ordered), 0.25, MATERIALS), RECTANGULAR_M)


def test_a_front_spar_without_section_gives_no_capacity_not_the_rear_spars() -> None:
    front = spar(spare_position_factor=0.25)
    rear = spar(section=CAPPED, material="test", spare_position_factor=0.7)
    assert bending_capacity(wing([front, rear]), 0.25, MATERIALS) is None


def test_a_spar_that_has_ended_leaves_the_other_as_the_front_spar() -> None:
    short_front = spar(
        section=RECTANGULAR, material="test", spare_position_factor=0.25, spare_length=0.1
    )
    rear = spar(section=TUBE, material="test", spare_position_factor=0.7)
    assert close(bending_capacity(wing([short_front, rear]), 0.3, MATERIALS), TUBE_M)


def test_two_spars_without_a_position_to_tell_the_front_one_fail() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=None)
    second = spar(section=TUBE, material="test", spare_position_factor=0.7)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing([first, second]), 0.25, MATERIALS)
    assert caught.value.code == "front_spar_not_determinable"


def test_two_spars_at_one_position_fail() -> None:
    first = spar(section=RECTANGULAR, material="test", spare_position_factor=0.25)
    second = spar(section=TUBE, material="test", spare_position_factor=0.25)
    with pytest.raises(FormulaError) as caught:
        bending_capacity(wing([first, second]), 0.25, MATERIALS)
    assert caught.value.code == "front_spar_not_determinable"


def test_a_single_spar_needs_no_position() -> None:
    only = spar(section=RECTANGULAR, material="test", spare_position_factor=None)
    assert close(bending_capacity(wing([only]), 0.25, MATERIALS), RECTANGULAR_M)


def test_a_section_without_material_fails_and_nothing_is_substituted() -> None:
    main = wing([spar(section=RECTANGULAR)])
    with pytest.raises(FormulaError) as caught:
        bending_capacity(main, 0.25, MATERIALS)
    assert caught.value.code == "spar_material_missing"
    assert "x_secs[0].spare_list[0]" in caught.value.message


def test_a_material_key_that_the_components_do_not_hold_fails() -> None:
    main = wing([spar(section=RECTANGULAR, material="birch")])
    with pytest.raises(FormulaError) as caught:
        bending_capacity(main, 0.25, MATERIALS)
    assert caught.value.code == "spar_material_unknown"
    assert "birch" in caught.value.message


def test_pushed_components_without_a_materials_table_fail_like_an_unknown_key() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    with pytest.raises(FormulaError) as caught:
        bending_capacity(main, 0.25, None)
    assert caught.value.code == "spar_material_unknown"


def test_a_material_without_strength_fails() -> None:
    main = wing([spar(section=RECTANGULAR, material="test")])
    with pytest.raises(FormulaError) as caught:
        bending_capacity(main, 0.25, {"test": material_with(None)})
    assert caught.value.code == "spar_material_without_strength"


def test_a_spar_without_section_needs_no_material_and_no_table() -> None:
    assert bending_capacity(wing([spar(material="birch")]), 0.25, None) is None


def test_another_segments_failure_does_not_matter_at_a_station_it_does_not_cover() -> None:
    good = spar(section=RECTANGULAR, material="test")
    bad = spar(section=RECTANGULAR, material="missing")
    assert close(bending_capacity(wing([good], [bad]), 0.25, MATERIALS), RECTANGULAR_M)
