"""The ``Components`` input contract (ARCHITECTURE ch. 8.11): types and structure only."""

import pytest
from aero_kernel.components import Battery, Components, Motor, Propeller
from aero_kernel.tests.components_builders import complete_components
from pydantic import ValidationError

MOTOR = {"kv_rpm_per_volt": 900.0}
BATTERY = {"capacity_mah": 6000.0, "cells": 4.0}
PROPELLER = {"diameter_in": 13.0}


def test_a_document_with_only_the_required_fields_parses_and_the_rest_is_absent() -> None:
    parsed = Components.model_validate(
        {"schema_version": 1, "motor": MOTOR, "battery": BATTERY, "propeller": PROPELLER}
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
    parsed = Components.model_validate({"schema_version": 1})
    assert (parsed.motor, parsed.battery, parsed.propeller) == (None, None, None)


def test_the_schema_version_is_required_and_only_one_is_accepted() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        Components.model_validate({})
    with pytest.raises(ValidationError, match="schema_version"):
        Components.model_validate({"schema_version": 2})


def test_an_unknown_field_is_refused() -> None:
    with pytest.raises(ValidationError, match="surprise"):
        Components.model_validate({"schema_version": 1, "motor": MOTOR | {"surprise": 1.0}})


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
    components = Components.model_validate({"schema_version": 1, "motor": MOTOR})
    again = Components.model_validate_json(components.model_dump_json())
    assert again == components
    assert again.motor is not None
    assert again.motor.rm_ohm is None
