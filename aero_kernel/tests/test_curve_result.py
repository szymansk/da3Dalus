"""A curve as a result of the kernel (ARCHITECTURE ch. 8.3, gh-1424).

The result carries exactly one of value, interval, surfaces and curve; every other non-scalar
type is still refused at request time; a curve under several method worlds is a declared
``not_implemented``; the cache stores a curve and returns it bit for bit.
"""

import struct
from collections.abc import Mapping
from typing import Any

import pytest
from aero_kernel.cache import DedupedCache, MemoryCache
from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import CanonGraph
from aero_kernel.schema import (
    ComputeRequest,
    ComputeResult,
    Curve,
    CurveResult,
    Interval,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.tests.engine_builders import (
    NO_SOLVERS,
    STANDARD,
    Impl,
    aircraft,
    make_build,
    num,
    registry_with,
    request,
)
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from pydantic import ValidationError

CURVE = CurveResult(x=(0.0, 0.5, 1.0), y=(3.0, 2.0, -0.0), x_quantity="sweep-x", x_unit="1")
EMPTY = CurveResult(x=(), y=(), x_quantity="sweep-x", x_unit="1")


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
    assert ok(curve=EMPTY).curve == EMPTY


def test_a_curve_result_names_its_abscissa() -> None:
    with pytest.raises(ValidationError, match="x_quantity"):
        CurveResult.model_validate({"x": [0.0], "y": [1.0], "x_unit": "1"})


def test_an_error_result_must_not_carry_a_curve() -> None:
    error = KernelError(
        code="not_converged", category=ErrorCategory.NOT_CONVERGED, message="m", hint="h"
    )
    with pytest.raises(ValidationError, match="must not carry a value or interval"):
        QuantityResult(slug="q", unit="1", status=QuantityStatus.ERROR, error=error, curve=CURVE)


def test_a_curve_result_round_trips_through_json() -> None:
    result = ok(curve=CURVE)
    assert QuantityResult.model_validate_json(result.model_dump_json()) == result


def test_the_json_of_a_curve_result_is_pinned() -> None:
    assert ok(curve=CURVE).model_dump_json() == (
        '{"slug":"q","unit":"1","status":"ok","reason":null,"value":null,"surfaces":null,'
        '"interval":null,"curve":{"x":[0.0,0.5,1.0],"y":[3.0,2.0,-0.0],"x_quantity":"sweep-x",'
        '"x_unit":"1"},"tool":"closed form","application":"clean","validated":false,'
        '"warnings":[],"error":null,"from_cache":false,"timing":null}'
    )


def test_the_json_of_a_scalar_result_is_pinned() -> None:
    assert ok(value=2.5).model_dump_json() == (
        '{"slug":"q","unit":"1","status":"ok","reason":null,"value":2.5,"surfaces":null,'
        '"interval":null,"curve":null,"tool":"closed form","application":"clean",'
        '"validated":false,"warnings":[],"error":null,"from_cache":false,"timing":null}'
    )


def test_the_json_of_an_interval_result_is_pinned() -> None:
    result = ok(interval=Interval(min=1.0, max=2.0, worlds={"f=a": 1.0, "f=b": 2.0}))
    assert result.model_dump_json() == (
        '{"slug":"q","unit":"1","status":"ok","reason":null,"value":null,"surfaces":null,'
        '"interval":{"min":1.0,"max":2.0,"worlds":{"f=a":1.0,"f=b":2.0}},"curve":null,'
        '"tool":"closed form","application":"clean","validated":false,"warnings":[],'
        '"error":null,"from_cache":false,"timing":null}'
    )


RESULT_FIELDS = {
    "slug",
    "unit",
    "status",
    "reason",
    "value",
    "surfaces",
    "interval",
    "curve",
    "tool",
    "application",
    "validated",
    "warnings",
    "error",
    "from_cache",
    "timing",
}


def result_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """The properties of ``QuantityResult`` in a serialization schema, wherever it sits."""
    if "QuantityResult" in schema.get("$defs", {}):
        return schema["$defs"]["QuantityResult"]["properties"]
    return schema["properties"]


@pytest.mark.parametrize("model", [QuantityResult, ComputeResult])
def test_the_serialization_schema_lists_every_field_with_its_type(
    model: type[QuantityResult | ComputeResult],
) -> None:
    schema = model.model_json_schema(mode="serialization")
    properties = result_properties(schema)
    assert set(properties) == RESULT_FIELDS
    assert properties["slug"]["type"] == "string"
    assert properties["value"]["anyOf"][0]["type"] == "number"
    assert {"$ref": "#/$defs/CurveResult"} in properties["curve"]["anyOf"]
    assert set(schema["$defs"]["CurveResult"]["properties"]) == {"x", "y", "x_quantity", "x_unit"}


# --- the graph ----------------------------------------------------------------------------------


def test_a_curve_quantity_is_requestable(flight_canon: CanonModel) -> None:
    found = CanonGraph(flight_canon).resolve("butterfly-stall-speed-curve")
    assert not isinstance(found, KernelError)
    assert found.quantity.type == "curve"
    assert found.quantity.abscissa == "crow-mix"


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
async def test_a_requested_curve_is_returned_with_unit_abscissa_and_provenance() -> None:
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
async def test_the_engine_only_updates_the_facts_of_a_run_on_a_finished_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``model_copy`` does not validate: the engine may update only these fields that way.

    A copy with a ``value`` next to a ``curve`` would be a result no validation ever saw.
    """
    updated: set[str] = set()
    original = QuantityResult.model_copy

    def spy(self: QuantityResult, *, update: Mapping[str, Any] | None = None, **kw: Any) -> Any:
        updated.update(update or {})
        return original(self, update=update, **kw)

    monkeypatch.setattr(QuantityResult, "model_copy", spy)
    store = MemoryCache(max_entries=8)
    build = make_build(registry_with())
    for _ in range(2):  # the second call is served from the cache
        await evaluate(
            build,
            aircraft(),
            request("curve-q", "weight", "double-weight"),
            solvers=NO_SOLVERS,
            cache=DedupedCache(store),
        )
    assert updated <= {"timing", "from_cache", "error"}
    assert "timing" in updated
    assert "from_cache" in updated


# --- a curve under several method worlds, on a real build with two worlds -----------------------

TAXONOMY: dict[str, Any] = {
    "tools": [{"id": "OPT", "name": "O"}, {"id": "AVL", "name": "AVL"}],
    "worlds": [{"id": "aerobuildup", "tool": "OPT"}, {"id": "avl", "tool": "AVL"}],
}


def worlds_build(*, uncertain: bool) -> Any:
    """A canon in which a curve reads a scalar that has two method worlds (or one method)."""
    extra: dict[str, Any] = (
        {"uncertainty": "interval", "worlds": ["aerobuildup", "avl"]} if uncertain else {}
    )
    quantities = {
        "aircraft-mass": quantity("input", unit="kg"),
        "gravity": quantity("input", unit="m/s^2"),
        "sweep-x": quantity("input"),
        "np-q": quantity("derived", **({"uncertainty": "interval"} if uncertain else {})),
        "curve-q": quantity("output", type="curve", abscissa="sweep-x"),
    }
    formulas = {
        "np": formula({"m": "aircraft-mass"}, {"n": "np-q"}, tool="OPT", **extra),
        "profile": formula({"n": "np-q"}, {"c": "curve-q"}),
    }
    model = model_of(quantities, formulas, taxonomy=TAXONOMY)
    registry = registry_with({"np": _np, "profile": _profile}, drop=tuple(STANDARD))
    return make_build(registry, model)


async def _np(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"n": num(x, "m") * 0.1}


async def _profile(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"c": Curve(x=(0.0, 1.0), y=(num(x, "n"), 2 * num(x, "n")))}


@pytest.mark.asyncio
async def test_a_curve_after_a_formula_with_two_worlds_is_not_implemented() -> None:
    result = await evaluate(
        worlds_build(uncertain=True), aircraft(), request("curve-q"), solvers=NO_SOLVERS
    )
    quantity_result = result.quantities[0]
    assert quantity_result.status is QuantityStatus.ERROR
    assert quantity_result.curve is None
    assert quantity_result.error is not None
    assert (quantity_result.error.category, quantity_result.error.code) == (
        ErrorCategory.NOT_IMPLEMENTED,
        "uncertain_curve",
    )
    assert "method worlds" in quantity_result.error.message
    assert "scalar" in quantity_result.error.hint


@pytest.mark.asyncio
async def test_the_same_curve_after_a_formula_with_one_method_is_a_result() -> None:
    result = await evaluate(
        worlds_build(uncertain=False), aircraft(), request("curve-q"), solvers=NO_SOLVERS
    )
    curve = result.quantities[0].curve
    assert curve is not None
    assert curve.y == (0.2, 0.4)


# --- the cache ----------------------------------------------------------------------------------


def bits(values: tuple[float, ...]) -> list[bytes]:
    return [struct.pack("<d", v) for v in values]


@pytest.mark.asyncio
async def test_a_curve_is_stored_and_comes_back_bit_for_bit() -> None:
    calls: list[str] = []

    async def counted(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("run")
        return {"c": Curve(x=CURVE.x, y=CURVE.y)}

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
    assert second.curve == CURVE
    assert second.curve is not None
    assert bits(second.curve.y) == bits(CURVE.y)
