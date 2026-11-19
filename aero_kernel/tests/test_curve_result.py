"""A curve as a result of the kernel (ARCHITECTURE ch. 8.3, gh-1424).

The result carries exactly one of value, interval, surfaces and curve; every other non-scalar
type is still refused at request time; a curve under several method worlds is a declared
``not_implemented``; the cache stores a curve and returns it bit for bit.
"""

import json
import struct
from collections.abc import Mapping

import pytest
from aero_kernel.cache import DedupedCache, MemoryCache
from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import CanonGraph, Subtree
from aero_kernel.schema import (
    ComputeRequest,
    ComputeResult,
    Curve,
    Interval,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.tests.engine_builders import (
    NO_SOLVERS,
    Impl,
    aircraft,
    make_build,
    registry_with,
    request,
)
from pydantic import ValidationError

CURVE = Curve(x=(0.0, 0.5, 1.0), y=(3.0, 2.0, -0.0))


def ok(**fields: object) -> QuantityResult:
    """An ``ok`` result of a quantity in ``1`` with the given value fields."""
    return QuantityResult.model_validate(
        {
            "slug": "q",
            "unit": "1",
            "status": QuantityStatus.OK,
            "tool": "closed form",
            "application": "clean",
            **fields,
        }
    )


# --- the result model ---------------------------------------------------------------------------


def test_a_curve_is_a_result() -> None:
    result = ok(curve=CURVE)
    assert result.curve == CURVE
    assert (result.value, result.interval, result.surfaces) == (None, None, None)


@pytest.mark.parametrize(
    "other",
    [
        {"value": 1.0},
        {"interval": Interval(min=1.0, max=2.0, worlds={"f=a": 1.0, "f=b": 2.0})},
        {"surfaces": {"s": {"a": 1.0}}},
    ],
)
def test_an_ok_result_with_a_curve_and_another_value_is_refused(other: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ok(curve=CURVE, **other)


def test_an_ok_result_without_any_value_is_refused() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        ok()


def test_a_curve_without_points_is_a_result() -> None:
    assert ok(curve=Curve(x=(), y=())).curve == Curve(x=(), y=())


def test_an_error_result_must_not_carry_a_curve() -> None:
    error = KernelError(
        code="not_converged",
        category=ErrorCategory.NOT_CONVERGED,
        message="m",
        hint="h",
    )
    with pytest.raises(ValidationError, match="must not carry a value or interval"):
        QuantityResult(slug="q", unit="1", status=QuantityStatus.ERROR, error=error, curve=CURVE)


def test_a_curve_result_round_trips_through_json() -> None:
    result = ok(curve=CURVE)
    again = QuantityResult.model_validate_json(result.model_dump_json())
    assert again == result
    assert json.loads(result.model_dump_json())["curve"] == {
        "x": [0.0, 0.5, 1.0],
        "y": [3.0, 2.0, -0.0],
    }


def test_the_json_of_a_scalar_result_is_unchanged() -> None:
    result = ok(value=2.5)
    assert result.model_dump_json() == (
        '{"slug":"q","unit":"1","status":"ok","reason":null,"value":2.5,"surfaces":null,'
        '"interval":null,"tool":"closed form","application":"clean","validated":false,'
        '"warnings":[],"error":null,"from_cache":false,"timing":null}'
    )


def test_the_json_of_an_interval_result_is_unchanged() -> None:
    result = ok(interval=Interval(min=1.0, max=2.0, worlds={"f=a": 1.0, "f=b": 2.0}))
    assert result.model_dump_json() == (
        '{"slug":"q","unit":"1","status":"ok","reason":null,"value":null,"surfaces":null,'
        '"interval":{"min":1.0,"max":2.0,"worlds":{"f=a":1.0,"f=b":2.0}},"tool":"closed form",'
        '"application":"clean","validated":false,"warnings":[],"error":null,'
        '"from_cache":false,"timing":null}'
    )


# --- the graph ----------------------------------------------------------------------------------


def test_a_curve_quantity_is_requestable(flight_canon: CanonModel) -> None:
    found = CanonGraph(flight_canon).resolve("butterfly-stall-speed-curve")
    assert not isinstance(found, KernelError)
    assert found.quantity.type == "curve"


@pytest.mark.parametrize("slug", ["polar-stall", "airplane-landing", "butterfly-speed-range"])
def test_every_other_non_scalar_quantity_is_still_refused(
    flight_canon: CanonModel, slug: str
) -> None:
    error = CanonGraph(flight_canon).resolve(slug)
    assert isinstance(error, KernelError)
    assert (error.code, error.category) == ("non_scalar_result", ErrorCategory.NOT_IMPLEMENTED)


# --- the engine ---------------------------------------------------------------------------------

pytestmark = pytest.mark.usefixtures("pending_horizontal_tail")


async def run(*slugs: str, overrides: Mapping[str, Impl] | None = None) -> ComputeResult:
    return await evaluate(
        make_build(registry_with(overrides)), aircraft(), request(*slugs), solvers=NO_SOLVERS
    )


@pytest.mark.asyncio
async def test_a_requested_curve_is_returned_with_unit_and_provenance() -> None:
    result = await run("curve-q", "weight")
    curve, weight = result.quantities
    assert curve.status is QuantityStatus.OK
    assert curve.curve == CURVE
    assert (curve.value, curve.interval) == (None, None)
    assert curve.unit == "1"
    assert curve.application == "default"
    assert curve.tool is not None
    assert weight.value == 2.0 * 9.81


@pytest.mark.asyncio
async def test_a_formula_that_returns_no_curve_for_a_curve_output_is_internal() -> None:
    async def wrong(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"c": 1.0}

    result = await run("curve-q", overrides={"curve-producer": wrong})
    error = result.quantities[0].error
    assert error is not None
    assert error.category is ErrorCategory.INTERNAL


@pytest.mark.asyncio
async def test_a_curve_under_several_method_worlds_is_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def with_worlds(_self: Subtree, _slug: str) -> tuple[dict[str, str], ...]:
        return ({"neutral-point": "avl"}, {"neutral-point": "textbook"})

    monkeypatch.setattr(Subtree, "world_assignments", with_worlds)
    quantity = (await run("curve-q")).quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.curve is None
    assert quantity.error is not None
    assert (quantity.error.category, quantity.error.code) == (
        ErrorCategory.NOT_IMPLEMENTED,
        "uncertain_curve",
    )
    assert "method worlds" in quantity.error.message


# --- the cache ----------------------------------------------------------------------------------


def bits(values: tuple[float, ...]) -> list[bytes]:
    return [struct.pack("<d", v) for v in values]


@pytest.mark.asyncio
async def test_a_curve_is_stored_and_comes_back_bit_for_bit() -> None:
    calls: list[str] = []

    async def counted(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("run")
        return {"c": CURVE}

    build = make_build(registry_with({"curve-producer": counted}))
    store = MemoryCache(max_entries=8)

    async def call() -> QuantityResult:
        result = await evaluate(
            build,
            aircraft(),
            ComputeRequest(quantities=("curve-q",)),
            solvers=NO_SOLVERS,
            cache=DedupedCache(store),
        )
        return result.quantities[0]

    first, second = await call(), await call()
    assert calls == ["run"]
    assert (first.from_cache, second.from_cache) == (False, True)
    assert second.curve is not None
    assert second.curve == CURVE
    assert bits(second.curve.y) == bits(CURVE.y)
