"""``MemoryCache``: LRU with a global and a per-scope limit (Q21)."""

import logging

import pytest
from aero_kernel.cache import MemoryCache

from .cache_builders import entry


@pytest.mark.parametrize(
    "kwargs", [{"max_entries": 0}, {"max_entries": 1, "max_entries_per_scope": 0}]
)
def test_limits_below_one_are_rejected(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        MemoryCache(**kwargs)


@pytest.mark.asyncio
async def test_global_limit_evicts_the_least_recently_used() -> None:
    cache = MemoryCache(max_entries=2)
    await cache.put("s", "a", entry(1.0))
    await cache.put("s", "b", entry(2.0))
    await cache.put("s", "c", entry(3.0))
    assert await cache.get("s", "a") is None
    assert await cache.get("s", "b") is not None
    assert await cache.get("s", "c") is not None


@pytest.mark.asyncio
async def test_get_refreshes_recency() -> None:
    cache = MemoryCache(max_entries=2)
    await cache.put("s", "a", entry(1.0))
    await cache.put("s", "b", entry(2.0))
    assert await cache.get("s", "a") is not None
    await cache.put("s", "c", entry(3.0))
    assert await cache.get("s", "b") is None
    assert await cache.get("s", "a") is not None


@pytest.mark.asyncio
async def test_put_of_an_existing_key_refreshes_and_does_not_grow() -> None:
    cache = MemoryCache(max_entries=2)
    await cache.put("s", "a", entry(1.0))
    await cache.put("s", "b", entry(2.0))
    await cache.put("s", "a", entry(3.0))
    await cache.put("s", "c", entry(4.0))
    assert await cache.get("s", "b") is None
    assert await cache.get("s", "a") == entry(3.0)


@pytest.mark.asyncio
async def test_per_scope_limit_evicts_only_within_that_scope() -> None:
    cache = MemoryCache(max_entries=10, max_entries_per_scope=2)
    await cache.put("other", "x", entry(9.0))
    await cache.put("busy", "a", entry(1.0))
    await cache.put("busy", "b", entry(2.0))
    await cache.get("busy", "a")
    await cache.put("busy", "c", entry(3.0))
    assert await cache.get("busy", "b") is None
    assert await cache.get("busy", "a") is not None
    assert await cache.get("busy", "c") is not None
    assert await cache.get("other", "x") == entry(9.0)


@pytest.mark.asyncio
async def test_drop_scope_frees_room_for_the_global_limit() -> None:
    cache = MemoryCache(max_entries=2)
    await cache.put("a", "k", entry(1.0))
    await cache.put("b", "k", entry(2.0))
    await cache.drop_scope("a")
    await cache.put("c", "k", entry(3.0))
    assert await cache.get("b", "k") == entry(2.0)


@pytest.mark.asyncio
async def test_hit_miss_and_eviction_are_logged_at_debug(caplog: pytest.LogCaptureFixture) -> None:
    cache = MemoryCache(max_entries=1)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        await cache.get("s", "sha256:0123456789abcdef")
        await cache.put("s", "sha256:0123456789abcdef", entry())
        await cache.get("s", "sha256:0123456789abcdef")
        await cache.put("s", "other", entry())
    assert "cache miss" in caplog.text
    assert "cache hit" in caplog.text
    assert "cache evict" in caplog.text
    assert "0123456789abcdef" not in caplog.text
