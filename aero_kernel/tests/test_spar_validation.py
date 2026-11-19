"""Validation of the spar section, the materials table and the unread pocket fields (gh-1427)."""

import math
from typing import Any

import pytest
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.spar_builders import CAPPED, RECTANGULAR, ROD, TUBE, spar
from aero_kernel.validate import validate_aircraft


def aircraft(
    spars: list[dict[str, Any]] | None = None, components: dict[str, Any] | None = None
) -> AircraftInput:
    """A two-rib main wing whose first segment carries ``spars``."""
    root: dict[str, Any] = {
        "xyz_le": [0.0, 0.0, 0.0],
        "chord": 0.2,
        "twist": 0.0,
        "airfoil": "naca2412",
    }
    if spars is not None:
        root["spare_list"] = spars
    tip = {"xyz_le": [0.0, 0.5, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": [root, tip]}
    document: dict[str, Any] = {
        "airplane": {"name": "t", "wings": {"Main": wing}},
        "values": {},
    }
    if components is not None:
        document["components"] = components
    return AircraftInput.model_validate(document)


def findings(found: AircraftInput) -> list[tuple[str, str | None]]:
    """The (code, input path) of every error."""
    return [(e.code, e.input_path) for e in validate_aircraft(found).errors]


SECTION_PATH = 'airplane.wings["Main"].x_secs[0].spare_list[0].section'


@pytest.mark.parametrize("section", [ROD, TUBE, RECTANGULAR, CAPPED])
def test_an_admissible_section_is_accepted(section: dict[str, Any]) -> None:
    assert findings(aircraft([spar(section=section, material="m")])) == []


def test_a_spar_without_section_is_valid() -> None:
    assert findings(aircraft([spar()])) == []


def test_a_pocket_with_nonsense_values_is_still_not_read() -> None:
    """The pocket fields stay CAD-only and unchecked."""
    assert findings(aircraft([spar(spare_support_dimension_width=-1.0)])) == []


@pytest.mark.parametrize(
    "section",
    [
        {"shape": "rod", "diameter": 0.0},
        {"shape": "rod", "diameter": -0.01},
        {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.0},
        {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.008},  # wall = radius
        {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.009},  # wall > radius
        {"shape": "tube", "outer_diameter": -0.016, "wall_thickness": 0.001},
        {"shape": "rectangular", "width": 0.0, "height": 0.003},
        {"shape": "rectangular", "width": 0.02, "height": -0.003},
        {"shape": "capped", "width": 0.004, "height": 0.0147, "flange_thickness": 0.00735},
        {"shape": "capped", "width": 0.004, "height": 0.0147, "flange_thickness": 0.0},
        {"shape": "capped", "width": 0.0, "height": 0.0147, "flange_thickness": 0.001},
    ],
)
def test_a_non_physical_section_is_refused_with_its_path(section: dict[str, Any]) -> None:
    assert findings(aircraft([spar(section=section)])) == [("invalid_spar_section", SECTION_PATH)]


def test_a_non_finite_dimension_is_a_non_finite_finding_only() -> None:
    section = {"shape": "rod", "diameter": math.nan}
    assert findings(aircraft([spar(section=section)])) == [
        ("non_finite_number", SECTION_PATH + ".diameter")
    ]


def test_every_spar_is_checked_by_its_own_index() -> None:
    bad = {"shape": "rod", "diameter": -1.0}
    found = findings(aircraft([spar(section=ROD), spar(section=bad)]))
    assert found == [("invalid_spar_section", SECTION_PATH.replace("[0].section", "[1].section"))]


def test_a_section_on_the_last_rib_is_the_known_last_rib_finding() -> None:
    last_rib = aircraft([spar()])
    document = last_rib.model_dump(mode="json", by_alias=True)
    wing = document["airplane"]["wings"]["Main"]
    wing["x_secs"][1]["spare_list"] = [spar(section=ROD, material="m")]
    found = findings(AircraftInput.model_validate(document))
    assert [code for code, _ in found] == ["segment_on_last_section"]


def components(materials: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 3, "materials": materials}


def test_a_material_with_positive_numbers_or_none_is_accepted() -> None:
    table = {
        "a": {"name": "A", "bending_strength_pa": 1.0e8, "density_kg_m3": 500.0},
        "b": {"name": "B"},
    }
    assert findings(aircraft(components=components(table))) == []


@pytest.mark.parametrize("field", ["bending_strength_pa", "density_kg_m3"])
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_a_material_number_that_is_not_positive_is_refused(field: str, value: float) -> None:
    table = {"birch": {"name": "Birch", field: value}}
    assert findings(aircraft(components=components(table))) == [
        ("non_positive_value", f'components.materials["birch"].{field}')
    ]


def test_a_non_finite_material_number_is_refused() -> None:
    table = {"birch": {"name": "Birch", "bending_strength_pa": math.inf}}
    assert findings(aircraft(components=components(table))) == [
        ("non_finite_number", 'components.materials["birch"].bending_strength_pa')
    ]


def test_a_spar_material_key_missing_from_the_components_is_not_an_input_error() -> None:
    """Whether the key resolves is decided where the capacity is read, never for other quantities."""
    found = aircraft([spar(section=ROD, material="nowhere")], components({}))
    assert findings(found) == []
