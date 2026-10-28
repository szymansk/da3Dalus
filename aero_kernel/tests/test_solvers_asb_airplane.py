"""The one conversion of the geometry format to an AeroSandbox airplane (ADR 0022)."""

from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers import asb_airplane
from aero_kernel.solvers.asb_airplane import (
    fin_area,
    horizontal_tail_area,
    main_wing_properties,
    surface_properties,
    to_asb_airplane,
)
from aero_kernel.superellipse import equivalent_exponent
from aero_kernel.tests.asb_fakes import (
    FAKE_AC_X,
    FAKE_CENTRELINE_AREA,
    FAKE_CENTRELINE_GAP,
    FAKE_REFERENCE,
    FakeAirfoil,
    FakeAirplane,
    FakeFuselage,
    FakeWing,
    install_fake_aerosandbox,
)
from aero_kernel.tests.formula_builders import near

NACA = "naca2412"
CONTOUR = [[1.0, 0.0], [0.5, 0.05], [0.0, 0.0], [0.5, -0.04], [1.0, 0.0]]


def geometry_document() -> dict[str, Any]:
    """Two wings: a symmetric one with a NACA root and an inline tip, and a fin on one side."""
    section = {"twist": 0.0, "dihedral": 3.0}
    return {
        "name": "t",
        "xyz_ref": [0.1, 0.0, 0.02],
        "wings": {
            "Main": {
                "name": "Main",
                "surface_type": "main_wing",
                "symmetric": True,
                "x_secs": [
                    {**section, "xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "airfoil": NACA},
                    {
                        **section,
                        "twist": -1.5,
                        "xyz_le": [0.02, 0.4, 0.01],
                        "chord": 0.1,
                        "airfoil": {"coordinates": CONTOUR},
                        "trailing_edge_device": {
                            "name": "ail",
                            "rel_chord_root": 0.8,
                            "rel_chord_tip": 0.8,
                            "positive_deflection_deg": 25.0,
                            "negative_deflection_deg": 25.0,
                            "deflection_deg": 12.0,
                        },
                    },
                    {**section, "xyz_le": [0.04, 0.8, 0.02], "chord": 0.05, "airfoil": NACA},
                ],
            },
            "Fin": {
                "name": "Fin",
                "surface_type": "vertical_tail",
                "symmetric": False,
                "x_secs": [
                    {**section, "xyz_le": [0.5, 0.0, 0.0], "chord": 0.1, "airfoil": NACA},
                    {**section, "xyz_le": [0.52, 0.0, 0.1], "chord": 0.05, "airfoil": NACA},
                ],
            },
        },
        "fuselages": {
            "Body": {
                "name": "Body",
                "x_secs": [
                    {"xyz": [0.0, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
                    {"xyz": [0.2, 0.0, 0.01], "a": 0.05, "b": 0.04, "n": 2.5},
                    {"xyz": [0.5, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
                ],
            }
        },
    }


def geometry() -> AirplaneGeometry:
    """The document, parsed."""
    return AirplaneGeometry.model_validate(geometry_document())


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)


def converted() -> FakeAirplane:
    airplane = to_asb_airplane(geometry())
    assert isinstance(airplane, FakeAirplane)
    return airplane


def test_the_airplane_carries_name_and_reference_point() -> None:
    kwargs = converted().kwargs
    assert kwargs["name"] == "t"
    assert list(kwargs["xyz_ref"]) == [0.1, 0.0, 0.02]


def test_wings_keep_their_order_name_and_symmetry() -> None:
    wings = converted().kwargs["wings"]
    assert [(w.kwargs["name"], w.kwargs["symmetric"]) for w in wings] == [
        ("Main", True),
        ("Fin", False),
    ]


def test_each_section_keeps_leading_edge_chord_and_twist() -> None:
    (main, _) = converted().kwargs["wings"]
    sections = main.kwargs["xsecs"]
    assert [list(s.kwargs["xyz_le"]) for s in sections] == [
        [0.0, 0.0, 0.0],
        [0.02, 0.4, 0.01],
        [0.04, 0.8, 0.02],
    ]
    assert [s.kwargs["chord"] for s in sections] == [0.2, 0.1, 0.05]
    assert [s.kwargs["twist"] for s in sections] == [0.0, -1.5, 0.0]


def test_a_naca_designation_and_inline_coordinates_become_airfoils() -> None:
    (main, _) = converted().kwargs["wings"]
    root, tip, _ = (s.kwargs["airfoil"] for s in main.kwargs["xsecs"])
    assert isinstance(root, FakeAirfoil)
    assert (root.name, root.coordinates) == (NACA, None)
    assert isinstance(tip, FakeAirfoil)
    assert tip.coordinates.tolist() == CONTOUR


def test_only_the_geometry_is_passed_never_a_control_device_or_the_dihedral_field() -> None:
    """Devices stay at 0 deg (ch. 8.11); xyz_le already carries the dihedral."""
    (main, _) = converted().kwargs["wings"]
    for section in main.kwargs["xsecs"]:
        assert set(section.kwargs) == {"xyz_le", "chord", "twist", "airfoil"}


def test_an_airplane_without_a_main_wing_is_a_defect_of_the_caller() -> None:
    """Validation guarantees one main wing; the reference values need it."""
    empty = AirplaneGeometry.model_validate({"name": "empty"})
    with pytest.raises(ValueError, match="exactly one main wing"):
        to_asb_airplane(empty)


def test_the_reference_values_are_asbs_own_values_of_the_main_wing() -> None:
    """ASB normalises C_L by these (ADR 0022): area and span with the centreline gap, and the MAC."""
    kwargs = converted().kwargs
    area, span, chord = FAKE_REFERENCE["Main"]
    assert kwargs["s_ref"] == area + FAKE_CENTRELINE_AREA
    assert kwargs["b_ref"] == span + FAKE_CENTRELINE_GAP
    assert kwargs["c_ref"] == chord


def test_the_main_wing_is_chosen_by_surface_type_not_by_list_position() -> None:
    """ASB's own default takes the first wing, here the fin (VSPAERO finding F1)."""
    document = geometry_document()
    document["wings"] = {"Fin": document["wings"]["Fin"], "Main": document["wings"]["Main"]}
    kwargs = to_asb_airplane(AirplaneGeometry.model_validate(document)).kwargs
    assert [w.kwargs["name"] for w in kwargs["wings"]] == ["Fin", "Main"]
    assert kwargs["s_ref"] == FAKE_REFERENCE["Main"][0] + FAKE_CENTRELINE_AREA


def test_every_area_and_span_call_sets_the_type_and_the_centreline_flag_explicitly() -> None:
    """No reliance on ASB's defaults (gh-1262): the fake wing refuses a call without both."""
    wings = converted().kwargs["wings"]
    asked = [call for wing in wings for call in wing.calls]
    assert ("area", {"type": "planform", "include_centerline_distance": True}) in asked
    assert ("span", {"type": "yz", "include_centerline_distance": True}) in asked
    assert all(
        options.get("include_centerline_distance") is True
        for name, options in asked
        if name in ("area", "span")
    )


def test_the_main_wing_properties_include_the_centreline_gap_in_area_and_span() -> None:
    properties = main_wing_properties(geometry())
    assert (properties.s_ref, properties.c_mac) == (
        FAKE_REFERENCE["Main"][0] + FAKE_CENTRELINE_AREA,
        FAKE_REFERENCE["Main"][2],
    )
    assert properties.b_ref == FAKE_REFERENCE["Main"][1] + FAKE_CENTRELINE_GAP


def test_the_surface_properties_are_asbs_with_the_ac_less_a_quarter_mac() -> None:
    """AR = b^2 / S of ASB's own two values; x_le_MAC = x_AC - 0.25 c_MAC (gh-1253)."""
    area, span, chord = FAKE_REFERENCE["Fin"]
    found = surface_properties(geometry(), "Fin")
    area += FAKE_CENTRELINE_AREA
    span += FAKE_CENTRELINE_GAP
    assert (found.area, found.span, found.c_mac) == (area, span, chord)
    assert found.aspect_ratio == span**2 / area
    assert found.x_le_mac == FAKE_AC_X["Fin"] - 0.25 * chord


def test_a_main_wing_without_a_planform_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(FAKE_REFERENCE, "Main", (-FAKE_CENTRELINE_AREA, 1.7, 0.21))
    document = geometry()
    with pytest.raises(FormulaError) as raised:
        main_wing_properties(document)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_a_fuselage_becomes_super_ellipse_sections_with_full_widths() -> None:
    """Semi-axes a, b are half widths; ASB takes the full width and height."""
    (body,) = converted().kwargs["fuselages"]
    assert isinstance(body, FakeFuselage)
    assert body.kwargs["name"] == "Body"
    sections = body.kwargs["xsecs"]
    assert [list(s.kwargs["xyz_c"]) for s in sections] == [
        [0.0, 0.0, 0.0],
        [0.2, 0.0, 0.01],
        [0.5, 0.0, 0.0],
    ]
    assert [(s.kwargs["width"], s.kwargs["height"], s.kwargs["shape"]) for s in sections] == [
        (0.0, 0.0, 2.0),
        (0.1, 0.08, 2.5),
        (0.0, 0.0, 2.0),
    ]
    assert all(set(s.kwargs) == {"xyz_c", "width", "height", "shape"} for s in sections)


def with_fuselage_change(**change: object) -> AirplaneGeometry:
    document = geometry_document()
    document["fuselages"]["Body"].update(change)
    return AirplaneGeometry.model_validate(document)


def test_a_fuselage_without_wings_list_converts_to_no_fuselages() -> None:
    document = geometry_document()
    document["fuselages"] = None
    assert to_asb_airplane(AirplaneGeometry.model_validate(document)).kwargs["fuselages"] == []


def test_a_mirrored_fuselage_is_unsupported() -> None:
    """ASB has no mirrored body; substituting one would be silent (ADR 0020)."""
    mirrored = with_fuselage_change(symmetric=True)
    with pytest.raises(FormulaError) as raised:
        to_asb_airplane(mirrored)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_different_upper_and_lower_exponents_become_one_equivalent_exponent() -> None:
    """ASB has one shape exponent per section: width 2a, height 2b, the centre kept, and the
    exponent that keeps the cross-section area (gh-1307)."""
    document = geometry_document()
    section = document["fuselages"]["Body"]["x_secs"][1]
    section["n_lower"] = 3.0
    (body,) = to_asb_airplane(AirplaneGeometry.model_validate(document)).kwargs["fuselages"]
    converted = body.kwargs["xsecs"][1].kwargs
    assert converted["shape"] == equivalent_exponent(section["n"], 3.0)
    assert converted["width"] == 2.0 * section["a"]
    assert converted["height"] == 2.0 * section["b"]
    assert converted["xyz_c"] == section["xyz"]


def test_an_equal_lower_exponent_is_the_same_section() -> None:
    document = geometry_document()
    document["fuselages"]["Body"]["x_secs"][1]["n_lower"] = 2.5
    (body,) = to_asb_airplane(AirplaneGeometry.model_validate(document)).kwargs["fuselages"]
    assert body.kwargs["xsecs"][1].kwargs["shape"] == 2.5


def v_tail_document(rows: list[tuple[float, float]]) -> AirplaneGeometry:
    """The geometry with a mirrored ``v_tail`` through (y, z) leading-edge points."""
    document = geometry_document()
    section = {"twist": 0.0, "airfoil": NACA}
    document["wings"]["VTail"] = {
        "name": "VTail",
        "surface_type": "v_tail",
        "symmetric": True,
        "x_secs": [
            {**section, "xyz_le": [0.5, y, z], "chord": 0.1 - 0.01 * index}
            for index, (y, z) in enumerate(rows)
        ],
    }
    return AirplaneGeometry.model_validate(document)


def test_the_fin_area_is_asbs_planform_area_without_the_centreline_distance() -> None:
    area = fin_area(geometry(), "Fin")
    assert area == FAKE_REFERENCE["Fin"][0]  # the fake adds its centreline area only when asked to


def test_the_fin_area_flags_are_passed_explicitly() -> None:
    """No reliance on ASB's defaults (maintainer 2026-10-26): the fake refuses a call without both."""
    wing = FakeWing(name="Fin")
    asb_airplane._fin_planform(wing)  # pyright: ignore[reportPrivateUsage]
    assert wing.calls == [("area", {"type": "planform", "include_centerline_distance": False})]


def test_a_v_tail_counts_the_fin_share_sin_squared_of_the_panel_angle() -> None:
    """One panel at 45 degrees to the horizontal: sin^2 = 1/2 of the (fake) planform area 1.0."""
    found = fin_area(v_tail_document([(0.05, 0.0), (0.25, 0.2)]), "VTail")
    assert near(found, 0.5)


def test_a_two_panel_v_tail_weights_each_panel_by_its_own_angle() -> None:
    """Panel 1 at 45 degrees (sin^2 = 1/2), panel 2 vertical (sin^2 = 1): 0.5 + 1.0 of the fake area 1.0."""
    found = fin_area(v_tail_document([(0.05, 0.0), (0.25, 0.2), (0.25, 0.4)]), "VTail")
    assert near(found, 1.5)


def test_a_flat_v_tail_panel_has_no_fin_share_and_a_flat_v_tail_no_area() -> None:
    flat = v_tail_document([(0.05, 0.0), (0.25, 0.0)])
    with pytest.raises(FormulaError, match="no fin area") as raised:
        fin_area(flat, "VTail")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_a_panel_without_extent_is_skipped_and_the_others_count() -> None:
    found = fin_area(v_tail_document([(0.05, 0.0), (0.25, 0.2), (0.25, 0.2)]), "VTail")
    assert near(found, 0.5)


def test_a_fin_without_a_planform_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(FAKE_REFERENCE, "Fin", (0.0, 0.4, 0.08))
    plane = geometry()
    with pytest.raises(FormulaError) as raised:
        fin_area(plane, "Fin")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_the_horizontal_tail_area_is_asbs_planform_area_with_the_centreline_distance() -> None:
    """The gross planform through the fuselage, the convention of the reference wing (#1262)."""
    area = horizontal_tail_area(geometry(), "Main")
    assert near(area, FAKE_REFERENCE["Main"][0] + FAKE_CENTRELINE_AREA)


def test_the_horizontal_tail_area_flags_are_passed_explicitly() -> None:
    wing = FakeWing(name="Main")
    asb_airplane._tail_planform(wing)  # pyright: ignore[reportPrivateUsage]
    assert wing.calls == [("area", {"type": "planform", "include_centerline_distance": True})]


def test_a_horizontal_tail_without_a_planform_is_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(FAKE_REFERENCE, "Fin", (-FAKE_CENTRELINE_AREA, 0.4, 0.08))
    plane = geometry()
    with pytest.raises(FormulaError, match="no horizontal tail area") as raised:
        horizontal_tail_area(plane, "Fin")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


# A V-tail counts as the horizontal tail with S_h,eff = sum S_i cos^2(nu_i) and the true panel
# aspect ratio (maintainer 2026-10-27, #1208). The fake wing gives every panel the area 1.0 and the span 2.0.
def test_a_v_tail_counts_the_horizontal_share_cos_squared_of_the_panel_angle() -> None:
    """One panel at 45 degrees to the horizontal: cos^2 = 1/2 of the (fake) planform area 1.0."""
    found = horizontal_tail_area(v_tail_document([(0.05, 0.0), (0.25, 0.2)]), "VTail")
    assert near(found, 0.5)


def test_a_two_panel_v_tail_weights_the_horizontal_share_per_panel() -> None:
    """Panel 1 at 45 degrees (cos^2 = 1/2), panel 2 vertical (cos^2 = 0)."""
    found = horizontal_tail_area(v_tail_document([(0.05, 0.0), (0.25, 0.2), (0.25, 0.4)]), "VTail")
    assert near(found, 0.5)


def test_the_two_shares_of_a_v_tail_add_up_to_its_planform_area() -> None:
    document = v_tail_document([(0.05, 0.0), (0.25, 0.2), (0.35, 0.3)])
    total = horizontal_tail_area(document, "VTail") + fin_area(document, "VTail")
    assert near(total, 2.0)  # two panels of the fake area 1.0


def test_a_vertical_v_tail_has_no_horizontal_area() -> None:
    vertical = v_tail_document([(0.05, 0.0), (0.05, 0.2)])
    with pytest.raises(FormulaError, match="no horizontal tail area") as raised:
        horizontal_tail_area(vertical, "VTail")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_the_v_tail_surface_has_the_effective_area_and_the_true_panel_aspect_ratio() -> None:
    """S_h,eff = 0.5; AR = (true yz span)^2 / (true planform area) = 2.0^2 / 1.0, not projected."""
    found = surface_properties(v_tail_document([(0.05, 0.0), (0.25, 0.2)]), "VTail")
    assert near(found.area, 0.5)
    assert near(found.span, 2.0)
    assert near(found.aspect_ratio, 4.0)
    assert near(found.c_mac, 0.5)
    assert near(found.x_le_mac, 0.1 - 0.25 * 0.5)


def test_the_aspect_ratio_of_a_two_panel_v_tail_uses_the_summed_true_span_and_area() -> None:
    found = surface_properties(v_tail_document([(0.05, 0.0), (0.25, 0.2), (0.25, 0.4)]), "VTail")
    assert near(found.area, 0.5)
    assert near(found.aspect_ratio, 4.0**2 / 2.0)


def test_a_v_tail_panel_measure_passes_every_flag_explicitly() -> None:
    wing = FakeWing(name="VTail")
    asb_airplane._panel_measures(wing)  # pyright: ignore[reportPrivateUsage]
    assert wing.calls == [
        ("area", {"type": "planform", "include_centerline_distance": False}),
        ("span", {"type": "yz", "include_centerline_distance": False}),
    ]


def test_a_flat_v_tail_surface_counts_all_its_area_as_horizontal() -> None:
    found = surface_properties(v_tail_document([(0.05, 0.0), (0.25, 0.0)]), "VTail")
    assert near(found.area, 1.0)


def test_a_vertical_v_tail_has_no_horizontal_surface_properties() -> None:
    vertical = v_tail_document([(0.05, 0.0), (0.05, 0.2)])
    with pytest.raises(FormulaError, match="no horizontal planform") as raised:
        surface_properties(vertical, "VTail")
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
