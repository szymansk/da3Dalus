"""Contract every ``NodeStore`` meets: round trip, fresh objects, scope isolation (Q7, Q21)."""

import struct
from collections.abc import Callable
from pathlib import Path

import pytest
from aero_kernel.cache import DiskCache, Entry, MemoryCache, NodeStore
from pydantic import JsonValue

from .cache_builders import entry

StoreFactory = Callable[[Path], NodeStore]

FACTORIES: dict[str, StoreFactory] = {
    "memory": lambda _path: MemoryCache(max_entries=100),
    "disk": lambda path: DiskCache(path=path / "cache" / "nodes.sqlite", max_bytes=10_000_000),
}


@pytest.fixture(params=sorted(FACTORIES))
def store(request: pytest.FixtureRequest, tmp_path: Path) -> NodeStore:
    """A fresh store of each implementation."""
    return FACTORIES[request.param](tmp_path)


def test_stores_implement_the_protocol(store: NodeStore) -> None:
    assert isinstance(store, NodeStore)


@pytest.mark.asyncio
async def test_miss_is_none(store: NodeStore) -> None:
    assert await store.get("shared", "k") is None


@pytest.mark.asyncio
async def test_put_then_get_returns_an_equal_entry(store: NodeStore) -> None:
    await store.put("shared", "k", entry(2.5))
    assert await store.get("shared", "k") == entry(2.5)


@pytest.mark.asyncio
async def test_every_hit_is_a_fresh_object(store: NodeStore) -> None:
    stored = Entry(outputs={"v": [1.0, 2.0]}, warnings=())
    await store.put("shared", "k", stored)
    first = await store.get("shared", "k")
    assert first is not None
    first_list = first.outputs["v"]
    assert isinstance(first_list, list)
    first_list.append(99.0)
    second = await store.get("shared", "k")
    assert second == Entry(outputs={"v": [1.0, 2.0]}, warnings=())
    assert second is not first


@pytest.mark.asyncio
async def test_mutating_the_put_object_does_not_change_the_store(store: NodeStore) -> None:
    values: list[JsonValue] = [1.0]
    await store.put("shared", "k", Entry(outputs={"v": values}, warnings=()))
    values.append(2.0)
    assert await store.get("shared", "k") == Entry(outputs={"v": [1.0]}, warnings=())


@pytest.mark.asyncio
async def test_negative_zero_survives_bit_exactly(store: NodeStore) -> None:
    await store.put("shared", "k", entry(-0.0))
    hit = await store.get("shared", "k")
    assert hit is not None
    value = hit.outputs["v"]
    assert isinstance(value, float)
    assert struct.pack("<d", value) == struct.pack("<d", -0.0)


@pytest.mark.asyncio
async def test_put_replaces_an_existing_key(store: NodeStore) -> None:
    await store.put("shared", "k", entry(1.0))
    await store.put("shared", "k", entry(2.0))
    assert await store.get("shared", "k") == entry(2.0)


@pytest.mark.asyncio
async def test_entry_in_one_scope_is_no_hit_in_another(store: NodeStore) -> None:
    await store.put("a", "k", entry(1.0))
    assert await store.get("b", "k") is None
    assert await store.get("a", "k") == entry(1.0)


@pytest.mark.asyncio
async def test_scope_and_key_are_not_concatenated(store: NodeStore) -> None:
    await store.put("a|b", "c", entry(1.0))
    assert await store.get("a", "b|c") is None


@pytest.mark.asyncio
async def test_drop_scope_leaves_other_scopes_untouched(store: NodeStore) -> None:
    await store.put("a", "k", entry(1.0))
    await store.put("a", "k2", entry(1.0))
    await store.put("b", "k", entry(2.0))
    await store.drop_scope("a")
    assert await store.get("a", "k") is None
    assert await store.get("a", "k2") is None
    assert await store.get("b", "k") == entry(2.0)


@pytest.mark.asyncio
async def test_drop_of_an_unknown_scope_is_a_no_op(store: NodeStore) -> None:
    await store.drop_scope("never-used")


@pytest.mark.asyncio
async def test_empty_scope_is_rejected_by_get(store: NodeStore) -> None:
    with pytest.raises(ValueError, match="scope"):
        await store.get("", "k")


@pytest.mark.asyncio
async def test_empty_scope_is_rejected_by_put(store: NodeStore) -> None:
    with pytest.raises(ValueError, match="scope"):
        await store.put("", "k", entry())


@pytest.mark.asyncio
async def test_empty_scope_is_rejected_by_drop_scope(store: NodeStore) -> None:
    with pytest.raises(ValueError, match="scope"):
        await store.drop_scope("")
