"""The published powertrain data (reference/powertrain): every number has its source, nothing is made up."""

from typing import Any

import pytest
from aero_kernel.tests.components_builders import components_of, reference
from aero_kernel.tests.formula_builders import close

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
    assert part["page"].startswith(("http", "Dantsker")), name
    assert set(part["fields"]) == set(part["published_wording"]), (kind, name)
    assert all(part["published_wording"][field] for field in part["fields"])


@pytest.mark.parametrize(("name", "motor"), DATA["motors"].items())
def test_a_motor_resistance_is_in_the_range_of_this_motor_class(
    name: str, motor: dict[str, Any]
) -> None:
    # roughly 10-300 mOhm; a value outside is a finding to report, not a value to take
    assert 0.010 <= motor["fields"]["rm_ohm"] <= 0.300, name
    assert "rm_ohm" in motor["conventions"], name
    assert "io_no_load_a" in motor["conventions"], name


@pytest.mark.parametrize(("name", "motor"), DATA["motors"].items())
def test_a_field_is_either_published_or_declared_not_published(
    name: str, motor: dict[str, Any]
) -> None:
    catalogue = {"kv_rpm_per_volt", "rm_ohm", "io_no_load_a", "max_power_w", "efficiency_pct"}
    assert catalogue == set(motor["fields"]) | set(motor.get("not_published", [])), name
    assert not set(motor["fields"]) & set(motor.get("not_published", [])), name


@pytest.mark.parametrize("name", DATA["sets"])
def test_a_set_maps_onto_the_components_contract(name: str) -> None:
    chosen = DATA["sets"][name]
    components = components_of(chosen["motor"], chosen["battery"], chosen["propeller"])
    assert components.motor is not None
    assert components.motor.kv_rpm_per_volt > 0
    assert components.battery is not None
    assert components.propeller is not None


def test_the_avistar_pack_cell_voltage_is_the_nameplate_divided_by_the_cells() -> None:
    battery = DATA["batteries"]["thunder_power_prolitex_4s_6000"]["fields"]
    assert close(battery["cell_voltage_v"], 14.8 / battery["cells"], 1e-12)
    assert battery["capacity_mah"] == 6000.0
