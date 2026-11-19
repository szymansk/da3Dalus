"""The sampling of the crow mix is a whole number of steps, at least one (config.yaml)."""

import pytest
from aero_kernel.canon.model import ConfigValue
from aero_kernel.config import config
from pydantic import ValidationError


def value(steps: float) -> dict[str, object]:
    return {
        "value": steps,
        "unit": "1",
        "guards": "g",
        "basis": "numerical",
        "source": "s",
    }


def with_steps(steps: float) -> object:
    shipped = config()
    fields = shipped.model_dump()
    fields["butterfly_mix_steps"] = value(steps)
    return type(shipped).model_validate(fields)


def test_the_shipped_mix_steps_are_a_whole_number_of_at_least_one() -> None:
    steps = config().butterfly_mix_steps.value
    assert steps >= 1.0
    assert steps == round(steps)


@pytest.mark.parametrize("steps", [0.5, 2.5, 10.4])
def test_a_fractional_number_of_steps_is_refused(steps: float) -> None:
    with pytest.raises(ValidationError, match="whole number"):
        with_steps(steps)


def test_zero_steps_are_refused() -> None:
    with pytest.raises(ValidationError):
        ConfigValue.model_validate(value(0.0))
    with pytest.raises(ValidationError):
        with_steps(0.0)


def test_one_step_is_the_least_that_is_accepted() -> None:
    assert with_steps(1.0) is not None


def with_mass_steps(steps: float) -> object:
    shipped = config()
    fields = shipped.model_dump()
    fields["mass_envelope_max_steps"] = value(steps)
    return type(shipped).model_validate(fields)


def test_the_shipped_mass_scan_is_a_whole_number_of_steps_of_a_positive_share() -> None:
    assert config().mass_envelope_step.value > 0.0
    assert config().mass_envelope_max_steps.value == round(config().mass_envelope_max_steps.value)


@pytest.mark.parametrize("steps", [0.5, 3.5])
def test_a_fractional_number_of_mass_scan_steps_is_refused(steps: float) -> None:
    with pytest.raises(ValidationError, match="whole number"):
        with_mass_steps(steps)


def test_one_mass_scan_step_is_the_least_that_is_accepted() -> None:
    assert with_mass_steps(1.0) is not None
