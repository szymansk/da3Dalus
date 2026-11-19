"""Embeddable relations: the registry's ``relation`` and the context's ``embedded`` (ch. 8.12)."""

from collections.abc import Mapping

import pytest
from aero_kernel.context import Context
from aero_kernel.registry import Registry, RegistryError
from aero_kernel.tests.formula_builders import solvers_with


async def _impl(x: Mapping[str, float], ctx: object) -> dict[str, float]:
    return {"v_s": 1.0}


def _sum(a: float, b: float) -> float:
    return a + b


def _double(x: float) -> float:
    return 2.0 * x


def test_a_relation_is_registered_per_formula_and_returned_unchanged() -> None:
    registry = Registry()
    assert registry.relation("static-thrust")(_sum) is _sum
    assert registry.relation_of("calc:static-thrust") is _sum
    assert registry.relation_of("static-thrust") is _sum
    assert registry.relation_of("stall-speed") is None


def test_a_second_relation_of_one_formula_is_an_error() -> None:
    registry = Registry()
    registry.relation("static-thrust")(_sum)
    with pytest.raises(RegistryError, match="already has a relation"):
        registry.relation("static-thrust")(_sum)


def test_a_relation_is_a_plain_function_not_a_coroutine() -> None:
    with pytest.raises(RegistryError, match="not a coroutine"):
        Registry().relation("static-thrust")(_impl)


def test_a_frozen_registry_takes_no_relation() -> None:
    registry = Registry()
    registry.freeze()
    with pytest.raises(RegistryError, match="frozen"):
        registry.relation("static-thrust")


def test_embedded_hands_out_the_relation_and_records_each_request_once() -> None:
    context = Context(origin="x", solvers=solvers_with(), relations={"calc:a.default": _double})
    assert context.embedded_requests == ()
    assert context.embedded("calc:a.default") is _double
    assert context.embedded("calc:a.default") is _double
    assert context.embedded_requests == ("calc:a.default",)


def test_embedded_refuses_an_item_the_formula_does_not_embed() -> None:
    context = Context(origin="x", solvers=solvers_with(), relations={"calc:a.default": _double})
    with pytest.raises(KeyError, match="does not embed"):
        context.embedded("calc:b.default")
