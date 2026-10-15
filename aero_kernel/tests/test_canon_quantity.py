"""The quantity entries of the canon model (README "Machine-readable fields", quantity entries)."""

import pytest
from aero_kernel.canon.model import Quantity
from pydantic import ValidationError


def make_quantity(**overrides: object) -> Quantity:
    """Build a valid scalar input quantity, with ``overrides`` applied."""
    fields: dict[str, object] = {
        "symbol": "m",
        "unit": "kg",
        "role": "input",
        "type": "scalar",
        **overrides,
    }
    return Quantity.model_validate(fields)


def test_minimal_quantity_defaults() -> None:
    quantity = make_quantity()
    assert quantity.default is None
    assert quantity.positive is None
    assert quantity.uncertainty is None


def test_positive_quantity_with_default() -> None:
    quantity = make_quantity(
        positive=True, default={"value": 1.225, "source": "U.S. Standard Atmosphere 1976"}
    )
    assert quantity.positive is True
    assert quantity.default is not None
    assert quantity.default.value == 1.225


@pytest.mark.parametrize("role", ["derived", "output"])
def test_positive_only_on_input_or_target(role: str) -> None:
    with pytest.raises(ValidationError, match="positive"):
        make_quantity(role=role, positive=True)


def test_default_of_positive_quantity_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="default"):
        make_quantity(positive=True, default={"value": 0.0, "source": "s"})


def test_default_needs_a_source() -> None:
    with pytest.raises(ValidationError):
        make_quantity(default={"value": 1.0, "source": ""})


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_quantity(type="vector")


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_quantity(tags=["x"])


@pytest.mark.parametrize("unit", ["1", "m/s", "kg/m^3", "rpm/V", "1/rad^2", "deg/s", "Wh/kg"])
def test_canon_units_are_accepted(unit: str) -> None:
    assert make_quantity(unit=unit).unit == unit


@pytest.mark.parametrize("unit", ["—", "furlong", "", "M"])
def test_unit_outside_the_closed_set_is_rejected(unit: str) -> None:
    with pytest.raises(ValidationError):
        make_quantity(unit=unit)


@pytest.mark.parametrize("role", ["input", "target", "derived", "output"])
def test_positive_false_is_an_error_on_every_role(role: str) -> None:
    """README: ``positive`` is ``true`` or omitted; ``false`` is one spelling too many."""
    with pytest.raises(ValidationError):
        make_quantity(role=role, positive=False)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_default_must_be_finite(bad: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        make_quantity(default={"value": bad, "source": "s"})


def test_quantity_is_frozen() -> None:
    quantity = make_quantity()
    with pytest.raises(ValidationError, match="frozen"):
        quantity.symbol = "x"  # type: ignore[misc]  # the assignment is the thing under test
