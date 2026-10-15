"""``validate_values``: the supplied ``values`` against the canon model (ARCHITECTURE ch. 8.11)."""

import math

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory
from aero_kernel.tests.canon_builders import base_namespaces, with_hash
from aero_kernel.validate import validate_values


def model() -> CanonModel:
    """A model with a positive input, an unrestricted input, a target, a derived and an airplane."""
    namespaces = base_namespaces()
    quantities = namespaces["calc"]["quantities"]
    quantities["altitude"] = {"symbol": "h", "unit": "m", "role": "input", "type": "scalar"}
    quantities["cruise-speed-target"] = {
        "symbol": "V_c",
        "unit": "m/s",
        "role": "target",
        "type": "scalar",
        "positive": True,
    }
    quantities["airplane"] = {
        "symbol": "airplane",
        "unit": "1",
        "role": "input",
        "type": "airplane",
    }
    return CanonModel.model_validate(with_hash(namespaces))


def test_admissible_values_have_no_findings() -> None:
    values = {"aircraft-mass": 1.5, "gravity": 9.81, "altitude": -10.0, "cruise-speed-target": 20.0}
    assert validate_values(values, model()) == ()


def test_unknown_slug_is_reported_with_its_path() -> None:
    (error,) = validate_values({"warp-speed": 1.0}, model())
    assert error.code == "unknown_quantity"
    assert error.category is ErrorCategory.INVALID_INPUT
    assert error.input_path == "values.warp-speed"
    assert error.message
    assert error.hint


@pytest.mark.parametrize("slug", ["weight", "airplane"])
def test_derived_output_and_non_scalar_slugs_are_not_inputs(slug: str) -> None:
    (error,) = validate_values({slug: 1.0}, model())
    assert error.code == "not_an_input"
    assert error.input_path == f"values.{slug}"


@pytest.mark.parametrize("value", [0.0, -1.5])
def test_non_positive_value_of_a_positive_quantity(value: float) -> None:
    (error,) = validate_values({"aircraft-mass": value}, model())
    assert error.code == "non_positive_value"
    assert error.input_path == "values.aircraft-mass"
    assert error.detail == {"value": value}


def test_non_finite_numbers_are_left_to_validate_aircraft() -> None:
    assert validate_values({"aircraft-mass": math.nan, "gravity": math.inf}, model()) == ()


def test_zero_and_negative_are_fine_where_the_canon_does_not_say_positive() -> None:
    assert validate_values({"altitude": 0.0}, model()) == ()
    assert validate_values({"altitude": -5.0}, model()) == ()


def test_findings_come_by_slug_and_qualified_slugs_resolve() -> None:
    errors = validate_values(
        {"weight": 1.0, "calc:aircraft-mass": 0.0, "ghost": 1.0, "aircraft-mass": 0.0}, model()
    )
    assert [(e.code, e.input_path) for e in errors] == [
        ("non_positive_value", "values.aircraft-mass"),
        ("non_positive_value", 'values["calc:aircraft-mass"]'),
        ("unknown_quantity", "values.ghost"),
        ("not_an_input", "values.weight"),
    ]


def test_not_an_input_messages_say_where_the_quantity_comes_from() -> None:
    errors = {e.input_path: e for e in validate_values({"airplane": 1.0, "weight": 1.0}, model())}
    assert "`airplane` is given as AircraftInput.airplane, not in values" in (
        errors["values.airplane"].message
    )
    assert "computed by the kernel; values cannot override it" in errors["values.weight"].message


def test_other_non_scalar_input_is_not_a_number() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["grid"] = {
        "symbol": "grid",
        "unit": "1",
        "role": "input",
        "type": "curve",
    }
    (error,) = validate_values({"grid": 1.0}, CanonModel.model_validate(with_hash(namespaces)))
    assert "`grid` is a curve, not a number; values hold numbers only" in error.message
