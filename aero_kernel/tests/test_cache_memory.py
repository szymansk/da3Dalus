"""``MemoryCache``: one global LRU, entries kept serialised (Q7, Q21)."""

import logging
import struct

import pytest
from aero_kernel.cache import Entry, MemoryCache
from pydantic import JsonValue

from .cache_builders import entry


def test_a_limit_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        MemoryCache(max_entries=0)


def test_the_size_limit_has_no_default() -> None:
    with pytest.raises(TypeError):
        MemoryCache()  # type: ignore[call-arg]  # the point of the test: no default size


def test_miss_is_none() -> None:
    assert MemoryCache(max_entries=2).get("k") is None


def test_put_then_get_returns_an_equal_entry() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("k", entry(2.5))
    assert cache.get("k") == entry(2.5)


def test_every_hit_is_a_fresh_object() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("k", Entry(outputs={"v": [1.0, 2.0]}, warnings=()))
    first = cache.get("k")
    assert first is not None
    first_list = first.outputs["v"]
    assert isinstance(first_list, list)
    first_list.append(99.0)
    second = cache.get("k")
    assert second == Entry(outputs={"v": [1.0, 2.0]}, warnings=())
    assert second is not first


def test_mutating_the_put_object_does_not_change_the_cache() -> None:
    cache = MemoryCache(max_entries=2)
    values: list[JsonValue] = [1.0]
    cache.put("k", Entry(outputs={"v": values}, warnings=()))
    values.append(2.0)
    assert cache.get("k") == Entry(outputs={"v": [1.0]}, warnings=())


def test_negative_zero_survives_bit_exactly() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("k", entry(-0.0))
    hit = cache.get("k")
    assert hit is not None
    value = hit.outputs["v"]
    assert isinstance(value, float)
    assert struct.pack("<d", value) == struct.pack("<d", -0.0)


def test_put_replaces_an_existing_key() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("k", entry(1.0))
    cache.put("k", entry(2.0))
    assert cache.get("k") == entry(2.0)


def test_limit_evicts_the_least_recently_used() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("a", entry(1.0))
    cache.put("b", entry(2.0))
    cache.put("c", entry(3.0))
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None


def test_get_refreshes_recency() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("a", entry(1.0))
    cache.put("b", entry(2.0))
    assert cache.get("a") is not None
    cache.put("c", entry(3.0))
    assert cache.get("b") is None
    assert cache.get("a") is not None


def test_put_of_an_existing_key_refreshes_and_does_not_grow() -> None:
    cache = MemoryCache(max_entries=2)
    cache.put("a", entry(1.0))
    cache.put("b", entry(2.0))
    cache.put("a", entry(3.0))
    cache.put("c", entry(4.0))
    assert cache.get("b") is None
    assert cache.get("a") == entry(3.0)


def test_hit_miss_and_eviction_are_logged_at_debug(caplog: pytest.LogCaptureFixture) -> None:
    cache = MemoryCache(max_entries=1)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        cache.get("sha256:0123456789abcdef")
        cache.put("sha256:0123456789abcdef", entry())
        cache.get("sha256:0123456789abcdef")
        cache.put("other", entry())
    assert "cache miss" in caplog.text
    assert "cache hit" in caplog.text
    assert "cache evict" in caplog.text
    assert "0123456789abcdef" not in caplog.text
