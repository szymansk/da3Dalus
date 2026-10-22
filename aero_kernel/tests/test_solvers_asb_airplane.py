"""The one conversion of the geometry format to an AeroSandbox airplane (ADR 0022)."""

from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.tests.asb_fakes import (
    FakeAirfoil,
    FakeAirplane,
    FakeFuselage,
    install_fake_aerosandbox,
)

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


def test_the_reference_values_are_the_kernels_projected_ones() -> None:
    """ASB normalises C_L by these, not by its own planform area (ADR 0022)."""
    kwargs = converted().kwargs
    properties = main_wing_properties(geometry())
    assert kwargs["s_ref"] == properties.s_ref
    assert kwargs["b_ref"] == properties.b_ref
    assert kwargs["c_ref"] == properties.c_mac


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


def test_different_upper_and_lower_exponents_are_unsupported() -> None:
    """ASB has one shape exponent per section."""
    document = geometry_document()
    document["fuselages"]["Body"]["x_secs"][1]["n_lower"] = 3.0
    two_exponents = AirplaneGeometry.model_validate(document)
    with pytest.raises(FormulaError) as raised:
        to_asb_airplane(two_exponents)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_an_equal_lower_exponent_is_the_same_section() -> None:
    document = geometry_document()
    document["fuselages"]["Body"]["x_secs"][1]["n_lower"] = 2.5
    (body,) = to_asb_airplane(AirplaneGeometry.model_validate(document)).kwargs["fuselages"]
    assert body.kwargs["xsecs"][1].kwargs["shape"] == 2.5
