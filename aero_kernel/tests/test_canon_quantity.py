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
    assert quantity.positive is None
    assert quantity.uncertainty is None


def test_a_quantity_carries_no_default() -> None:
    """The defaults live in the namespace table (S5)."""
    with pytest.raises(ValidationError, match="default"):
        make_quantity(default={"value": 1.0, "unit": "kg", "source": "s", "regime": "r"})


def test_positive_quantity() -> None:
    assert make_quantity(positive=True).positive is True


@pytest.mark.parametrize("role", ["derived", "output"])
def test_positive_only_on_input_or_target(role: str) -> None:
    with pytest.raises(ValidationError, match="positive"):
        make_quantity(role=role, positive=True)


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


def test_quantity_is_frozen() -> None:
    quantity = make_quantity()
    with pytest.raises(ValidationError, match="frozen"):
        quantity.symbol = "x"  # type: ignore[misc]  # the assignment is the thing under test


@pytest.mark.parametrize("type_", ["airplane", "curve", "polar", "curve_pair"])
@pytest.mark.parametrize("role", ["input", "target"])
def test_positive_only_on_scalars(role: str, type_: str) -> None:
    """Positivity is a property of one number; a curve or the airplane has no ``> 0``."""
    with pytest.raises(ValidationError, match="scalar"):
        make_quantity(role=role, type=type_, positive=True)
