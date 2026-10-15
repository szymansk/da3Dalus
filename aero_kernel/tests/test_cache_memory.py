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


class _CountingScope(str):
    """A scope name that counts how often it is compared, to show eviction does not scan."""

    comparisons = 0

    def __eq__(self, other: object) -> bool:
        type(self).comparisons += 1
        return str.__eq__(self, other)

    def __hash__(self) -> int:
        return str.__hash__(self)


@pytest.mark.asyncio
async def test_per_scope_eviction_does_not_scan_other_scopes() -> None:
    cache = MemoryCache(max_entries=10_000, max_entries_per_scope=2)
    for index in range(500):
        await cache.put(f"scope-{index}", "k", entry())
    scope = _CountingScope("busy")
    for name in "abc":
        _CountingScope.comparisons = 0
        await cache.put(scope, name, entry())
    assert _CountingScope.comparisons < 20


@pytest.mark.asyncio
async def test_lru_order_holds_across_scopes_and_limits() -> None:
    cache = MemoryCache(max_entries=3, max_entries_per_scope=2)
    await cache.put("a", "1", entry(1.0))
    await cache.put("b", "1", entry(2.0))
    await cache.put("a", "2", entry(3.0))
    await cache.get("a", "1")
    await cache.put("b", "2", entry(4.0))
    assert await cache.get("b", "1") is None
    await cache.put("a", "3", entry(5.0))
    assert await cache.get("a", "2") is None
    assert await cache.get("a", "1") == entry(1.0)
    assert await cache.get("b", "2") == entry(4.0)


@pytest.mark.asyncio
async def test_a_scope_emptied_by_global_eviction_can_be_filled_again() -> None:
    cache = MemoryCache(max_entries=1)
    await cache.put("a", "k", entry(1.0))
    await cache.put("b", "k", entry(2.0))
    assert await cache.get("a", "k") is None
    await cache.put("a", "k", entry(3.0))
    assert await cache.get("a", "k") == entry(3.0)


def test_the_size_limit_has_no_default() -> None:
    with pytest.raises(TypeError):
        MemoryCache()  # type: ignore[call-arg]  # the point of the test: no default size


@pytest.mark.asyncio
async def test_every_log_record_carries_the_scope(caplog: pytest.LogCaptureFixture) -> None:
    cache = MemoryCache(max_entries=1)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        await cache.get("s", "k")
        await cache.put("s", "k", entry())
        await cache.get("s", "k")
        await cache.put("s", "j", entry())
        await cache.drop_scope("s")
    assert len(caplog.records) == 4
    assert all(getattr(record, "scope", None) == "s" for record in caplog.records)
