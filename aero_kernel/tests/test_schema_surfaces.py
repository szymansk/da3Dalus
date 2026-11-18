"""The per-surface value of a ``per_control_surface`` quantity in ``QuantityResult`` (ch. 8.3)."""

import pytest
from aero_kernel.schema import QuantityResult, QuantityStatus
from pydantic import ValidationError

SURFACES = {
    "Main wing.aileron_right": {"aileron": 0.012},
    "Main wing.aileron_left": {"aileron": -0.012},
}


def ok(**fields: object) -> QuantityResult:
    """An ``ok`` hinge-moment result with the given value fields."""
    return QuantityResult.model_validate(
        {
            "slug": "hinge-moment",
            "unit": "N*m",
            "status": QuantityStatus.OK,
            "tool": "AVL",
            "application": "aileron",
            **fields,
        }
    )


def test_a_per_surface_value_is_a_result() -> None:
    result = ok(surfaces=SURFACES)
    assert result.surfaces == SURFACES
    assert result.value is None
    assert result.interval is None


def test_an_ok_result_with_a_value_and_surfaces_is_refused() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ok(value=1.0, surfaces=SURFACES)


def test_an_ok_result_without_any_value_is_refused() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ok()


def test_an_empty_per_surface_value_is_refused() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        ok(surfaces={})


def test_a_surface_without_an_application_is_refused() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        ok(surfaces={"Main wing.aileron_right": {}})


def test_a_non_finite_value_is_refused() -> None:
    with pytest.raises(ValidationError, match="finite"):
        ok(surfaces={"Main wing.aileron_right": {"aileron": float("nan")}})


def test_only_an_ok_result_carries_surfaces() -> None:
    with pytest.raises(ValidationError, match="must not carry a value"):
        QuantityResult.model_validate(
            {
                "slug": "hinge-moment",
                "unit": "N*m",
                "status": QuantityStatus.NOT_APPLICABLE,
                "surfaces": SURFACES,
                "reason": {"code": "condition_not_met", "message": "no device"},
            }
        )
