"""``DiskCache``: one SQLite file, JSON values, byte limits, degraded operation (ch. 8.4, 8.14)."""

import asyncio
import logging
import sqlite3
from pathlib import Path

import pytest
from aero_kernel import cache as cache_module
from aero_kernel.cache import DiskCache

from .cache_builders import entry

DB_NAME = "nodes.sqlite"


def _disk(tmp_path: Path, **kwargs: int | None) -> DiskCache:
    """A cache in ``tmp_path`` with generous limits unless overridden."""
    limits: dict[str, int | None] = {"max_bytes": 10_000_000, "max_bytes_per_scope": None}
    limits.update(kwargs)
    max_bytes = limits["max_bytes"]
    assert max_bytes is not None
    return DiskCache(
        path=tmp_path / DB_NAME,
        max_bytes=max_bytes,
        max_bytes_per_scope=limits["max_bytes_per_scope"],
    )


def _size(value: float = 1.0) -> int:
    """Payload bytes of ``entry(value)``."""
    return len(entry(value).to_json().encode())


@pytest.mark.parametrize("kwargs", [{"max_bytes": 0}, {"max_bytes": 5, "max_bytes_per_scope": 0}])
def test_limits_below_one_are_rejected(tmp_path: Path, kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        DiskCache(path=tmp_path / DB_NAME, **kwargs)


def test_construction_does_no_io(tmp_path: Path) -> None:
    _disk(tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


@pytest.mark.asyncio
async def test_first_use_creates_the_parent_directory_and_the_file(tmp_path: Path) -> None:
    cache = DiskCache(path=tmp_path / "a" / "b" / DB_NAME, max_bytes=1000)
    await cache.put("s", "k", entry())
    assert (tmp_path / "a" / "b" / DB_NAME).is_file()


@pytest.mark.asyncio
async def test_entries_survive_a_new_instance(tmp_path: Path) -> None:
    await _disk(tmp_path).put("s", "k", entry(4.0))
    assert await _disk(tmp_path).get("s", "k") == entry(4.0)


@pytest.mark.asyncio
async def test_values_are_stored_as_json_text(tmp_path: Path) -> None:
    await _disk(tmp_path).put("s", "k", entry(4.0))
    with sqlite3.connect(tmp_path / DB_NAME) as db:
        (value,) = db.execute("SELECT value FROM entries").fetchone()
    assert value == entry(4.0).to_json()


@pytest.mark.asyncio
async def test_unreadable_entry_is_a_miss_deleted_and_warned(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = _disk(tmp_path)
    await cache.put("s", "k", entry())
    with sqlite3.connect(tmp_path / DB_NAME) as db:
        db.execute("UPDATE entries SET value = 'not json'")
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await cache.get("s", "k") is None
    assert "unreadable" in caplog.text
    with sqlite3.connect(tmp_path / DB_NAME) as db:
        assert db.execute("SELECT COUNT(*) FROM entries").fetchone() == (0,)


@pytest.mark.asyncio
async def test_a_file_that_is_no_database_is_moved_aside(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / DB_NAME
    path.write_bytes(b"this is not a sqlite file" * 100)
    aside = tmp_path / f"{DB_NAME}.corrupt"
    aside.write_bytes(b"older")
    cache = _disk(tmp_path)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await cache.get("s", "k") is None
    assert aside.read_bytes().startswith(b"this is not")
    assert "moved aside" in caplog.text
    await cache.put("s", "k", entry(2.0))
    assert await cache.get("s", "k") == entry(2.0)


@pytest.mark.asyncio
async def test_unknown_schema_version_resets_the_cache(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = _disk(tmp_path)
    await cache.put("s", "k", entry())
    with sqlite3.connect(tmp_path / DB_NAME) as db:
        db.execute("PRAGMA user_version = 99")
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await cache.get("s", "k") is None
    assert "schema version" in caplog.text
    await cache.put("s", "k", entry(3.0))
    assert await cache.get("s", "k") == entry(3.0)


@pytest.mark.asyncio
async def test_global_byte_limit_evicts_by_access_order(tmp_path: Path) -> None:
    cache = _disk(tmp_path, max_bytes=2 * _size() + 1)
    await cache.put("s", "a", entry())
    await cache.put("s", "b", entry())
    assert await cache.get("s", "a") is not None
    await cache.put("s", "c", entry())
    assert await cache.get("s", "b") is None
    assert await cache.get("s", "a") is not None
    assert await cache.get("s", "c") is not None


@pytest.mark.asyncio
async def test_per_scope_byte_limit_evicts_only_within_the_scope(tmp_path: Path) -> None:
    cache = _disk(tmp_path, max_bytes_per_scope=2 * _size() + 1)
    await cache.put("other", "x", entry())
    await cache.put("busy", "a", entry())
    await cache.put("busy", "b", entry())
    await cache.put("busy", "c", entry())
    assert await cache.get("busy", "a") is None
    assert await cache.get("busy", "b") is not None
    assert await cache.get("busy", "c") is not None
    assert await cache.get("other", "x") is not None


@pytest.mark.asyncio
async def test_an_oversized_entry_is_not_stored(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = _disk(tmp_path, max_bytes=_size() - 1)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        await cache.put("s", "k", entry())
    assert await cache.get("s", "k") is None
    assert "too large" in caplog.text


@pytest.mark.asyncio
async def test_an_entry_over_the_scope_limit_is_not_stored(tmp_path: Path) -> None:
    cache = _disk(tmp_path, max_bytes_per_scope=_size() - 1)
    await cache.put("s", "k", entry())
    assert await cache.get("s", "k") is None


@pytest.mark.asyncio
async def test_a_locked_database_degrades_get_and_put_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_module, "_BUSY_TIMEOUT_S", 0.05)
    cache = _disk(tmp_path)
    await cache.put("s", "k", entry())
    blocker = sqlite3.connect(tmp_path / DB_NAME, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
            assert await cache.get("s", "k") is None
            await cache.put("s", "new", entry())
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    assert caplog.text.count("database locked") == 2
    assert await cache.get("s", "new") is None


@pytest.mark.asyncio
async def test_drop_scope_on_a_locked_database_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_module, "_BUSY_TIMEOUT_S", 0.05)
    cache = _disk(tmp_path)
    await cache.put("s", "k", entry())
    blocker = sqlite3.connect(tmp_path / DB_NAME, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(sqlite3.OperationalError):
            await cache.drop_scope("s")
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    assert await cache.get("s", "k") == entry()


@pytest.mark.asyncio
async def test_two_instances_share_one_file(tmp_path: Path) -> None:
    first, second = _disk(tmp_path), _disk(tmp_path)
    await first.put("s", "k", entry(1.0))
    await second.put("s", "j", entry(2.0))
    assert await first.get("s", "j") == entry(2.0)
    assert await second.get("s", "k") == entry(1.0)


@pytest.mark.asyncio
async def test_a_database_locked_while_opening_is_a_miss_not_a_move_aside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cache_module, "_BUSY_TIMEOUT_S", 0.05)
    blocker = sqlite3.connect(tmp_path / DB_NAME, isolation_level=None)
    blocker.execute("PRAGMA journal_mode = WAL")
    blocker.execute("BEGIN IMMEDIATE")
    try:
        assert await _disk(tmp_path).get("s", "k") is None
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    assert not (tmp_path / f"{DB_NAME}.corrupt").exists()


@pytest.mark.asyncio
async def test_concurrent_calls_on_one_cache_agree(tmp_path: Path) -> None:
    cache = _disk(tmp_path)
    await asyncio.gather(*(cache.put("s", f"k{i}", entry(float(i))) for i in range(20)))
    hits = await asyncio.gather(*(cache.get("s", f"k{i}") for i in range(20)))
    assert hits == [entry(float(i)) for i in range(20)]


@pytest.mark.asyncio
async def test_repair_by_another_thread_is_used_without_moving_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _disk(tmp_path)
    # The repair race cannot be provoked from outside, so the private method is patched by name.
    real_open = getattr(cache, "_open")  # noqa: B009 - a string keeps the type checker out of it
    calls: list[int] = []

    def flaky_open() -> sqlite3.Connection:
        calls.append(1)
        if len(calls) == 1:
            raise sqlite3.DatabaseError("file is not a database")
        return real_open()

    monkeypatch.setattr(cache, "_open", flaky_open)
    await cache.put("s", "k", entry())
    assert len(calls) == 2
    assert not (tmp_path / f"{DB_NAME}.corrupt").exists()


@pytest.mark.asyncio
async def test_a_lock_during_the_repair_retry_raises_and_keeps_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _disk(tmp_path)
    (tmp_path / DB_NAME).write_bytes(b"precious")
    outcomes: list[Exception] = [
        sqlite3.DatabaseError("file is not a database"),
        sqlite3.OperationalError("database is locked"),
    ]

    def failing_open() -> sqlite3.Connection:
        raise outcomes.pop(0)

    monkeypatch.setattr(cache, "_open", failing_open)
    assert await cache.get("s", "k") is None
    assert (tmp_path / DB_NAME).read_bytes() == b"precious"
