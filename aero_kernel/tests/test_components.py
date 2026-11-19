"""The ``Components`` input contract (ARCHITECTURE ch. 8.11): types and structure only."""

import pytest
from aero_kernel.components import Battery, Components, Material, Motor, Propeller
from aero_kernel.tests.components_builders import complete_components
from pydantic import ValidationError

MOTOR = {"kv_rpm_per_volt": 900.0}
BATTERY = {"capacity_mah": 6000.0, "cells": 4.0}
PROPELLER = {"diameter_in": 13.0}


def test_a_document_with_only_the_required_fields_parses_and_the_rest_is_absent() -> None:
    parsed = Components.model_validate(
        {"schema_version": 3, "motor": MOTOR, "battery": BATTERY, "propeller": PROPELLER}
    )
    assert parsed.motor == Motor(kv_rpm_per_volt=900.0)
    assert parsed.motor is not None
    assert parsed.motor.rm_ohm is None
    assert parsed.motor.io_no_load_a is None
    assert parsed.motor.efficiency_pct is None
    assert parsed.motor.max_power_w is None
    assert parsed.battery == Battery(capacity_mah=6000.0, cells=4.0)
    assert parsed.battery is not None
    assert parsed.battery.mass_g is None
    assert parsed.battery.c_rate is None
    assert parsed.battery.cell_voltage_v is None
    assert parsed.battery.chemistry is None
    assert parsed.propeller == Propeller(diameter_in=13.0)


def test_a_part_may_be_missing_altogether() -> None:
    parsed = Components.model_validate({"schema_version": 3})
    assert (parsed.motor, parsed.battery, parsed.propeller) == (None, None, None)


def test_the_schema_version_is_required_and_only_one_is_accepted() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        Components.model_validate({})
    with pytest.raises(ValidationError, match="schema_version"):
        Components.model_validate({"schema_version": 2})  # older documents are refused outright
    with pytest.raises(ValidationError, match="schema_version"):
        Components.model_validate({"schema_version": 4})


def test_the_refusal_of_an_older_version_names_the_materials_table() -> None:
    with pytest.raises(ValidationError, match="materials"):
        Components.model_validate({"schema_version": 2})


def test_an_unknown_field_is_refused() -> None:
    with pytest.raises(ValidationError, match="surprise"):
        Components.model_validate({"schema_version": 3, "motor": MOTOR | {"surprise": 1.0}})


def test_the_chemistry_is_one_of_the_closed_list() -> None:
    battery = Battery.model_validate(BATTERY | {"chemistry": "lihv"})
    assert battery.chemistry == "lihv"
    with pytest.raises(ValidationError, match="chemistry"):
        Battery.model_validate(BATTERY | {"chemistry": "lead"})


def test_a_number_must_be_a_number_not_a_string() -> None:
    with pytest.raises(ValidationError, match="kv_rpm_per_volt"):
        Motor.model_validate({"kv_rpm_per_volt": "900"})


def test_a_document_is_frozen() -> None:
    components = complete_components()
    with pytest.raises(ValidationError, match="frozen"):
        components.motor = None  # pyright: ignore[reportAttributeAccessIssue]


def test_the_json_round_trip_keeps_absence_absent() -> None:
    components = Components.model_validate({"schema_version": 3, "motor": MOTOR})
    again = Components.model_validate_json(components.model_dump_json())
    assert again == components
    assert again.motor is not None
    assert again.motor.rm_ohm is None


def test_materials_are_absent_unless_pushed() -> None:
    assert Components.model_validate({"schema_version": 3}).materials is None


def test_a_material_needs_only_its_name_and_the_rest_stays_absent() -> None:
    parsed = Components.model_validate(
        {"schema_version": 3, "materials": {"birch_ply": {"name": "Birch plywood"}}}
    )
    assert parsed.materials is not None
    birch = parsed.materials["birch_ply"]
    assert birch.name == "Birch plywood"
    assert birch.bending_strength_pa is None
    assert birch.source is None


def test_a_material_carries_strength_and_source() -> None:
    material = Material.model_validate(
        {
            "name": "Test material",
            "bending_strength_pa": 1.0e8,
            "source": "a test value",
        }
    )
    assert material.bending_strength_pa == 1.0e8
    assert material.source == "a test value"


def test_a_material_has_no_safety_factor_field() -> None:
    with pytest.raises(ValidationError, match="safety_factor"):
        Material.model_validate({"name": "x", "safety_factor": 1.5})


def test_a_material_strength_must_be_a_number_not_a_string() -> None:
    with pytest.raises(ValidationError, match="bending_strength_pa"):
        Material.model_validate({"name": "x", "bending_strength_pa": "100"})


def test_a_material_has_no_density_field() -> None:
    """Nothing reads a density (ADR 0021): the contract does not carry one."""
    with pytest.raises(ValidationError, match="density_kg_m3"):
        Material.model_validate({"name": "x", "density_kg_m3": 500.0})
