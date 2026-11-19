"""The canon type ``curve``: a sampled function with a rising variable (ch. 8.12)."""

import pytest
from aero_kernel.schema import Curve, Polar, StallCurve
from pydantic import ValidationError

POLAR = Polar(alpha_deg=(0.0, 1.0), cl=(0.1, 0.2), cd=(0.01, 0.01))


def test_a_curve_holds_equally_long_series_over_a_rising_variable() -> None:
    curve = Curve(x=(0.0, 0.5, 1.0), y=(1.0, 2.0, 3.0))
    assert curve.y == (1.0, 2.0, 3.0)


@pytest.mark.parametrize(
    "change",
    [{"y": (1.0, 2.0)}, {"x": (0.0, 0.0, 1.0)}, {"x": (0.0, 1.0, 0.5)}],
)
def test_a_curve_refuses_unequal_or_unordered_series(change: dict[str, object]) -> None:
    fields: dict[str, object] = {"x": (0.0, 0.5, 1.0), "y": (1.0, 2.0, 3.0)}
    with pytest.raises(ValidationError):
        Curve.model_validate({**fields, **change})


def test_a_stall_curve_carries_one_stall_per_point() -> None:
    curve = StallCurve(
        x=(0.0, 1.0),
        y=(8.0, 9.0),
        alpha_s=(12.0, 11.0),
        cl_max=(1.2, 1.0),
        polars=(POLAR, POLAR),
    )
    assert curve.cl_max == (1.2, 1.0)


def test_a_stall_curve_refuses_a_missing_sweep() -> None:
    with pytest.raises(ValidationError):
        StallCurve(
            x=(0.0, 1.0), y=(8.0, 9.0), alpha_s=(12.0, 11.0), cl_max=(1.2, 1.0), polars=(POLAR,)
        )


def test_an_empty_curve_is_a_curve_without_points() -> None:
    assert Curve(x=(), y=()).x == ()
