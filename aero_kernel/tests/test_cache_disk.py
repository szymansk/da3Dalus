"""``DiskCache``: one SQLite file, JSON values, byte limits, degraded operation (ch. 8.4, 8.14)."""

import asyncio
import logging
import math
import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.cache import DiskCache, Entry, StoreError

from .cache_builders import entry

DB_NAME = "nodes.sqlite"


def _disk(tmp_path: Path, busy_timeout_s: float = 5.0, **kwargs: int | None) -> DiskCache:
    """A cache in ``tmp_path`` with generous limits unless overridden."""
    limits: dict[str, int | None] = {"max_bytes": 10_000_000, "max_bytes_per_scope": None}
    limits.update(kwargs)
    max_bytes = limits["max_bytes"]
    assert max_bytes is not None
    return DiskCache(
        path=tmp_path / DB_NAME,
        max_bytes=max_bytes,
        max_bytes_per_scope=limits["max_bytes_per_scope"],
        busy_timeout_s=busy_timeout_s,
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
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = _disk(tmp_path, busy_timeout_s=0.05)
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
    assert caplog.text.count("disk cache unavailable (SQLITE_BUSY)") == 2
    assert await cache.get("s", "new") is None


@pytest.mark.asyncio
async def test_drop_scope_on_a_locked_database_raises_store_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = _disk(tmp_path, busy_timeout_s=0.05)
    await cache.put("s", "k", entry())
    blocker = sqlite3.connect(tmp_path / DB_NAME, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with (
            caplog.at_level(logging.WARNING, logger="aero_kernel.cache"),
            pytest.raises(StoreError) as caught,
        ):
            await cache.drop_scope("s")
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()
    message = str(caught.value)
    assert message == ("the cache could not delete scope s; the store is busy, retry later")
    assert "sqlite" not in message.lower()
    assert str(tmp_path) not in message
    assert isinstance(caught.value.__cause__, sqlite3.OperationalError)
    assert "database is locked" in caplog.text
    assert await cache.get("s", "k") == entry()


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_busy_timeout_must_be_positive(tmp_path: Path, bad: float) -> None:
    with pytest.raises(ValueError, match="busy_timeout_s"):
        DiskCache(path=tmp_path / DB_NAME, max_bytes=10, busy_timeout_s=bad)


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
    blocker = sqlite3.connect(tmp_path / DB_NAME, isolation_level=None)
    blocker.execute("PRAGMA journal_mode = WAL")
    blocker.execute("BEGIN IMMEDIATE")
    try:
        assert await _disk(tmp_path, busy_timeout_s=0.05).get("s", "k") is None
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
async def test_concurrent_first_opens_drop_no_put(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        for trial in range(30):
            cache = DiskCache(path=tmp_path / f"t{trial}.sqlite", max_bytes=10_000_000)
            await asyncio.gather(*(cache.put("s", f"k{i}", entry(float(i))) for i in range(30)))
            hits = await asyncio.gather(*(cache.get("s", f"k{i}") for i in range(30)))
            assert None not in hits
    assert caplog.text == ""


BIG = Entry(outputs={"v": [float(i) for i in range(400)]}, warnings=())


async def _corrupt_body(tmp_path: Path) -> DiskCache:
    """A cache with 200 entries whose b-tree pages are trashed after the third page."""
    cache = _disk(tmp_path)
    for index in range(200):
        await cache.put("s", str(index), BIG)
    path = tmp_path / DB_NAME
    data = bytearray(path.read_bytes())
    for offset in range(4096 * 3, len(data) - 4096, 4096):
        data[offset : offset + 16] = b"\xff" * 16
    path.write_bytes(bytes(data))
    return cache


@pytest.mark.asyncio
async def test_a_corrupt_page_makes_get_a_miss_and_moves_the_file_aside(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = await _corrupt_body(tmp_path)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await cache.get("s", "150") is None
    assert (tmp_path / f"{DB_NAME}.corrupt").is_file()
    assert "moved aside" in caplog.text
    await cache.put("s", "150", entry(2.0))
    assert await cache.get("s", "150") == entry(2.0)


@pytest.mark.asyncio
async def test_a_corrupt_page_makes_put_a_skipped_write(tmp_path: Path) -> None:
    cache = await _corrupt_body(tmp_path)
    await cache.put("s", "new", entry(3.0))
    assert (tmp_path / f"{DB_NAME}.corrupt").is_file()
    await cache.put("s", "new", entry(3.0))
    assert await cache.get("s", "new") == entry(3.0)


@pytest.mark.asyncio
async def test_a_corrupt_page_is_deleted_with_the_file_by_drop_scope(tmp_path: Path) -> None:
    cache = await _corrupt_body(tmp_path)
    await cache.drop_scope("s")
    assert (tmp_path / f"{DB_NAME}.corrupt").is_file()
    assert await cache.get("s", "150") is None


@pytest.mark.asyncio
async def test_concurrent_calls_on_a_corrupt_file_move_it_aside_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = await _corrupt_body(tmp_path)
    barrier = threading.Barrier(2, timeout=10)
    real_connect = sqlite3.connect

    def meeting_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        barrier.wait()
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", meeting_connect)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        results = await asyncio.gather(cache.get("s", "150"), cache.get("s", "150"))
    assert results == [None, None]
    assert caplog.text.count("moved aside") == 1


@pytest.fixture
def unwritable_parent(tmp_path: Path) -> Path:
    """A database path whose parent directory cannot be created (it is a file)."""
    (tmp_path / "file").write_text("x")
    return tmp_path / "file" / DB_NAME


@pytest.mark.asyncio
async def test_a_failing_mkdir_makes_get_a_miss_with_a_warning(
    unwritable_parent: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = DiskCache(path=unwritable_parent, max_bytes=1000)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await cache.get("s", "k") is None
    assert "disk cache unavailable (FileExistsError)" in caplog.text


@pytest.mark.asyncio
async def test_a_failing_mkdir_makes_put_a_skipped_write_with_a_warning(
    unwritable_parent: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cache = DiskCache(path=unwritable_parent, max_bytes=1000)
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        await cache.put("s", "k", entry())
    assert "disk cache unavailable" in caplog.text


@pytest.mark.asyncio
async def test_a_failing_mkdir_makes_drop_scope_a_store_error_without_the_path(
    unwritable_parent: Path,
) -> None:
    cache = DiskCache(path=unwritable_parent, max_bytes=1000)
    with pytest.raises(StoreError) as caught:
        await cache.drop_scope("s")
    assert str(caught.value) == ("the cache could not delete scope s; the store is unavailable")
    assert isinstance(caught.value.__cause__, OSError)


@pytest.fixture
def directory_as_database(tmp_path: Path) -> DiskCache:
    """A cache whose database path is a directory (SQLite cannot open it)."""
    (tmp_path / DB_NAME).mkdir()
    return _disk(tmp_path)


@pytest.mark.asyncio
async def test_the_warning_names_the_sqlite_error(
    directory_as_database: DiskCache, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="aero_kernel.cache"):
        assert await directory_as_database.get("s", "k") is None
        await directory_as_database.put("s", "k", entry())
    assert caplog.text.count("disk cache unavailable (SQLITE_CANTOPEN)") == 2


@pytest.mark.asyncio
async def test_an_error_that_is_not_a_lock_is_not_called_busy(
    directory_as_database: DiskCache,
) -> None:
    with pytest.raises(StoreError) as caught:
        await directory_as_database.drop_scope("s")
    assert str(caught.value) == "the cache could not delete scope s; the store is unavailable"
