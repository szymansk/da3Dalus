"""Per-node attribution of rule thresholds (ARCHITECTURE ch. 8.4, maintainer 2026-10-29, #1332)."""

import asyncio

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.rules import Rules, node_rule_reads, unrecorded_rule_reads

RULE, PARAMETER = "flap-model-validity", "max_flap_deflection"


def rules() -> Rules:
    return Rules(shipped_build().model)


def test_a_read_inside_a_node_is_credited_to_it_and_to_the_call() -> None:
    resolver = rules()
    with node_rule_reads() as reads:
        resolver.value(RULE, PARAMETER)
    assert list(reads) == [(RULE, PARAMETER)]
    assert [(r.rule, r.parameter) for r in resolver.used()] == [(RULE, PARAMETER)]


def test_a_read_outside_any_node_is_the_calls_only() -> None:
    resolver = rules()
    with node_rule_reads() as reads:
        pass
    resolver.value(RULE, PARAMETER)
    assert reads == {}
    assert len(resolver.used()) == 1


@pytest.mark.asyncio
async def test_a_read_in_a_worker_thread_is_credited_to_the_node() -> None:
    resolver = rules()
    with node_rule_reads() as reads:
        await asyncio.to_thread(resolver.value, RULE, PARAMETER)
    assert list(reads) == [(RULE, PARAMETER)]


@pytest.mark.asyncio
async def test_concurrent_nodes_keep_their_own_reads() -> None:
    resolver = rules()

    async def node(parameter: str) -> list[tuple[str, str]]:
        with node_rule_reads() as reads:
            await asyncio.sleep(0)
            resolver.value(RULE, parameter)
            await asyncio.sleep(0)
            return list(reads)

    first, second = await asyncio.gather(node(PARAMETER), node("min_confidence"))
    assert first == [(RULE, PARAMETER)]
    assert second == [(RULE, "min_confidence")]


def test_an_unrecorded_read_declares_nothing() -> None:
    resolver = rules()
    with node_rule_reads() as reads, unrecorded_rule_reads():
        value = resolver.value(RULE, PARAMETER)
    assert value > 0
    assert reads == {}
    assert resolver.used() == ()


def test_replayed_thresholds_are_declared_by_the_call_and_the_node() -> None:
    source = rules()
    source.value(RULE, PARAMETER)
    target = rules()
    with node_rule_reads() as reads:
        target.replay(source.used())
    assert target.used() == source.used()
    assert list(reads) == [(RULE, PARAMETER)]
