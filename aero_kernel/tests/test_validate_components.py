"""Admissibility of ``AircraftInput.components`` (ARCHITECTURE ch. 8.11): ``input_errors``, not raises."""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.canon.model import CanonModel
from aero_kernel.components import Components
from aero_kernel.errors import KernelError
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.components_builders import complete_components
from aero_kernel.tests.wing_builders import airplane_document
from aero_kernel.validate import validate_aircraft, validate_values


def findings(
    components: Components | None, overrides: dict[str, float] | None = None
) -> tuple[KernelError, ...]:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "components": None if components is None else components.model_dump(),
            "values": {"aircraft-mass": 0.151},
            "rule_overrides": overrides or {},
        }
    )
    return validate_aircraft(aircraft).errors


def with_field(part: str, name: str, value: float) -> Components:
    document: dict[str, Any] = complete_components().model_dump()
    document[part][name] = value
    return Components.model_validate(document)


def test_the_complete_document_is_admissible() -> None:
    assert findings(complete_components()) == ()


def test_no_components_is_admissible_at_input() -> None:
    assert findings(None) == ()


@pytest.mark.parametrize(
    ("part", "name"),
    [
        ("motor", "kv_rpm_per_volt"),
        ("motor", "rm_ohm"),
        ("motor", "efficiency_pct"),
        ("motor", "max_power_w"),
        ("battery", "capacity_mah"),
        ("battery", "cells"),
        ("battery", "mass_g"),
        ("battery", "c_rate"),
        ("battery", "cell_voltage_v"),
        ("propeller", "diameter_in"),
    ],
)
@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_a_non_positive_number_is_reported_at_its_path(part: str, name: str, bad: float) -> None:
    (error,) = findings(with_field(part, name, bad))
    assert error.code == "non_positive_value"
    assert error.input_path == f"components.{part}.{name}"


def test_a_no_load_current_of_zero_is_admissible_and_a_negative_one_is_not() -> None:
    assert findings(with_field("motor", "io_no_load_a", 0.0)) == ()
    (error,) = findings(with_field("motor", "io_no_load_a", -0.1))
    assert error.input_path == "components.motor.io_no_load_a"


def test_an_efficiency_above_100_percent_is_reported() -> None:
    (error,) = findings(with_field("motor", "efficiency_pct", 100.5))
    assert error.code == "value_above_maximum"
    assert error.input_path == "components.motor.efficiency_pct"


@pytest.mark.parametrize("bad", [math.nan, math.inf])
def test_a_non_finite_number_is_reported_once(bad: float) -> None:
    (error,) = findings(with_field("motor", "rm_ohm", bad))
    assert error.code == "non_finite_number"
    assert error.input_path == "components.motor.rm_ohm"


def test_components_cannot_be_given_in_values() -> None:
    model: CanonModel = shipped_build().model
    (error,) = validate_values({"components": 1.0}, model)
    assert error.code == "not_an_input"
    assert error.input_path == "values.components"
    assert "AircraftInput.components" in error.message


RULES = shipped_build().model.namespaces["calc"].rules


@pytest.mark.parametrize(
    ("rule", "code"),
    [
        ("components-finite-numbers", "non_finite_number"),
        ("components-positive-numbers", "non_positive_value"),
        ("components-efficiency-at-most", "value_above_maximum"),
    ],
)
def test_each_component_check_has_its_rule_in_the_canon(rule: str, code: str) -> None:
    found = RULES[rule]
    assert found.applies_to.quantity == "components"
    assert found.kind == "input"
    assert found.codes == [code]


def test_the_efficiency_bound_is_the_canon_parameter_of_the_rule() -> None:
    parameter = RULES["components-efficiency-at-most"].parameters["max_efficiency"]
    assert (parameter.value, parameter.unit, parameter.basis) == (1.0, "1", "definition")


def test_the_efficiency_bound_is_read_through_the_rules_and_can_be_overridden() -> None:
    components = with_field("motor", "efficiency_pct", 95.0)
    assert findings(components) == ()
    key = "components-efficiency-at-most.max_efficiency"
    (error,) = findings(components, {key: 0.9})
    assert error.code == "value_above_maximum"
    assert error.input_path == "components.motor.efficiency_pct"
