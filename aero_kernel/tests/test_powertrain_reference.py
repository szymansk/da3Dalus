"""The published powertrain data (reference/powertrain): every number has its source, nothing is made up."""

from typing import Any

import pytest
from aero_kernel.tests.components_builders import components_of, reference

DATA = reference()
PARTS = [
    (kind, name, part)
    for kind in ("motors", "batteries", "propellers")
    for name, part in DATA[kind].items()
]


@pytest.mark.parametrize(("kind", "name", "part"), PARTS)
def test_every_field_has_its_published_wording_and_nothing_else_does(
    kind: str, name: str, part: dict[str, Any]
) -> None:
    assert part["page"].startswith("https://"), name
    assert set(part["fields"]) == set(part["published_wording"]), (kind, name)
    assert all(part["published_wording"][field] for field in part["fields"])


@pytest.mark.parametrize(("name", "motor"), DATA["motors"].items())
def test_a_motor_resistance_is_positive_and_its_convention_is_recorded(
    name: str, motor: dict[str, Any]
) -> None:
    assert motor["fields"]["rm_ohm"] > 0, name
    assert "rm_ohm" in motor["conventions"], name
    assert "io_no_load_a" in motor["conventions"], name


@pytest.mark.parametrize(("name", "motor"), DATA["motors"].items())
def test_a_field_is_either_published_or_declared_not_published(
    name: str, motor: dict[str, Any]
) -> None:
    catalogue = {"kv_rpm_per_volt", "rm_ohm", "io_no_load_a", "max_power_w", "efficiency_pct"}
    fields = set(motor["fields"])
    declared = set(motor.get("not_published", [])) | set(motor.get("not_adopted", []))
    assert catalogue == fields | declared, name
    assert not fields & declared, name


@pytest.mark.parametrize("name", DATA["sets"])
def test_a_set_maps_onto_the_components_contract(name: str) -> None:
    chosen = DATA["sets"][name]
    components = components_of(chosen["motor"], chosen["battery"], chosen["propeller"])
    assert components.motor is not None
    assert components.motor.kv_rpm_per_volt > 0
    assert components.battery is not None
    assert components.propeller is not None


@pytest.mark.parametrize(("kind", "name", "part"), PARTS)
def test_a_value_that_is_not_adopted_carries_its_wording_and_its_reason(
    kind: str, name: str, part: dict[str, Any]
) -> None:
    for field, entry in part.get("not_adopted", {}).items():
        assert field not in part["fields"], (kind, name, field)
        assert entry["published_as"], (name, field)
        assert entry["why"], (name, field)


def test_the_derived_cell_voltage_and_the_unlabelled_c_rate_are_not_adopted() -> None:
    battery = DATA["batteries"]["thunder_power_prolitex_4s_6000"]
    assert set(battery["fields"]) == {"capacity_mah", "cells"}
    assert set(battery["not_adopted"]) == {"cell_voltage_v", "c_rate"}
