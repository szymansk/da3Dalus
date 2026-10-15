"""Node cache: the cache key, the build digest, ``Entry``, the ``NodeStore`` protocol and its stores (ch. 8.4).

The cache maps keys to a node's outputs and warnings and never changes a value. It knows only JSON
values; converting typed results to and from JSON is the engine's job. Entries are kept serialised and
every hit builds a fresh object, so no caller can corrupt another caller's result.
"""

import asyncio
import hashlib
import logging
import sqlite3
import threading
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Protocol, Self, runtime_checkable

from aero_kernel.canonical import sha256_of
from aero_kernel.errors import check_finite_json
from aero_kernel.schema import Accuracy, KernelWarning
from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

__all__ = [
    "DiskCache",
    "Entry",
    "MemoryCache",
    "NodeStore",
    "StoreError",
    "build_digest",
    "cache_key",
]

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1
_PACKAGE_ROOT = Path(__file__).resolve().parent
_EXCLUDED_DIRECTORIES = frozenset({"tests", "tools", "importer"})
_CANON_MODEL = "canon/canon_model.json"


def _file_hash(path: Path) -> str:
    """Return the hex SHA-256 of the bytes of ``path``."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_digest(root: Path | None = None) -> str:
    """Hash the code and the canon model, so any change invalidates every cache entry (ch. 8.4).

    Covers every ``.py`` file of the package except those under ``tests/``, ``tools/`` and
    ``importer/`` at the package top level, plus ``canon/canon_model.json``. A missing canon model is
    a defined state (hash ``null``), not an error. The function is pure; the owner memoises it.

    Args:
        root: The package directory; ``None`` means the installed ``aero_kernel`` package.

    Returns:
        ``"sha256:"`` plus the hex digest.
    """
    base = _PACKAGE_ROOT if root is None else root
    files: list[JsonValue] = []
    for path in sorted(base.rglob("*.py")):
        relative = path.relative_to(base)
        if relative.parts[0] in _EXCLUDED_DIRECTORIES and len(relative.parts) > 1:
            continue
        files.append({"path": relative.as_posix(), "sha256": _file_hash(path)})
    canon = base / _CANON_MODEL
    if canon.is_file():
        files.append({"path": _CANON_MODEL, "sha256": _file_hash(canon)})
    else:
        logger.debug("canon model absent from the build digest: %s", _CANON_MODEL)
        files.append({"path": _CANON_MODEL, "sha256": None})
    return sha256_of(files)


def cache_key(
    *,
    scope: str,
    formula: str,
    application: str,
    world: str | None,
    inputs: Mapping[str, JsonValue],
    build_digest: str,
    tool_versions: Mapping[str, str],
    accuracy: Accuracy,
    provider_hashes: Mapping[str, str],
) -> str:
    """Compute the cache key of one node (ch. 8.4): SHA-256 over the canonical JSON of everything.

    Floats are hashed exactly (``repr``), never rounded; ``-0.0`` counts as ``0.0``.

    Args:
        scope: Cache scope of the call.
        formula: Qualified formula slug of the node.
        application: Application id within the formula.
        world: Canonical world assignment, or ``None`` for a certain node.
        inputs: Direct input values by parameter name.
        build_digest: Hash over the code and canon model (see :func:`build_digest`).
        tool_versions: Versions of the tools the node uses.
        accuracy: Accuracy tier of the call.
        provider_hashes: ``content_hash()`` of every provider the node reads, by provider name.

    Returns:
        ``"sha256:"`` plus the hex digest.

    Raises:
        ValueError: If ``inputs`` holds NaN or infinity (validation rejects those earlier).
    """
    return sha256_of(
        {
            "scope": scope,
            "application": {"formula": formula, "application": application},
            "world": world,
            "inputs": dict(inputs),
            "build_digest": build_digest,
            "tool_versions": dict(tool_versions),
            "accuracy": accuracy,
            "provider_hashes": dict(provider_hashes),
        }
    )


class Entry(BaseModel):
    """What the cache stores for one node: its outputs and its own warnings (ch. 8.4).

    There is no status or error field: errors, ``skipped`` and ``not_applicable`` are never stored.
    The JSON form keeps every float exactly (``-0.0`` included), so a hit is bit-identical to the
    computed value; only cache *keys* normalise ``-0.0``.

    Attributes:
        outputs: Output parameter name to JSON value, for every output of the application.
        warnings: The node's warnings, pre- and postcondition warnings included, as received.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    outputs: dict[str, JsonValue]
    warnings: tuple[KernelWarning, ...]

    @model_validator(mode="after")
    def _check_finite(self) -> Self:
        """Reject NaN and infinity, which would serialise as ``null``."""
        check_finite_json(self.outputs, "outputs")
        return self

    def to_json(self) -> str:
        """Serialise to the JSON text a store keeps."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Build a fresh entry from stored JSON text.

        Args:
            text: Text produced by :meth:`to_json`.

        Returns:
            A new object that shares nothing with any other.

        Raises:
            ValueError: If the text is not a valid entry.
        """
        return cls.model_validate_json(text)


_KEY_PREFIX = 12


def _check_scope(scope: str) -> None:
    """Raise ``ValueError`` for an empty scope (a programming error, ch. 8.4)."""
    if not scope:
        msg = "scope must be a non-empty string"
        raise ValueError(msg)


def _short(key: str) -> str:
    """The key prefix that is logged instead of the whole key."""
    return key[:_KEY_PREFIX]


class StoreError(Exception):
    """A store could not do what the caller relies on (ADR 0019: no SQL, path or backend text).

    Raised by ``drop_scope`` only, because a deletion cannot degrade to a no-op; reads and writes
    degrade to a miss or a skipped write instead.
    """


@runtime_checkable
class NodeStore(Protocol):
    """Where the node cache keeps its entries (ch. 8.4); a caller may supply its own.

    Implementations are safe for concurrent use, keep entries serialised and return a fresh
    :class:`Entry` on every hit. A hit never crosses scopes. The one error ``drop_scope`` may raise,
    in a custom store too, is :class:`StoreError`; ``get`` and ``put`` degrade instead of raising.
    """

    async def get(self, scope: str, key: str) -> Entry | None:
        """Return a fresh copy of the entry of ``key`` in ``scope``, or ``None`` on a miss."""
        ...

    async def put(self, scope: str, key: str, entry: Entry) -> None:
        """Store ``entry`` under ``key`` in ``scope``, replacing an earlier one."""
        ...

    async def drop_scope(self, scope: str) -> None:
        """Remove every entry of ``scope``; other scopes are untouched."""
        ...


class MemoryCache:
    """An in-process LRU store: one global limit and an optional limit per scope (ch. 8.4).

    The methods are coroutines for protocol compatibility only; none awaits inside its critical
    section, so on one event loop no lock is needed.
    """

    def __init__(self, *, max_entries: int, max_entries_per_scope: int | None = None) -> None:
        """Create an empty cache.

        Args:
            max_entries: Entries kept over all scopes; the least recently used one is evicted.
            max_entries_per_scope: Optional limit per scope; evicts that scope's least recently
                used entry, so one scope cannot push out the others.

        Raises:
            ValueError: If a limit is below 1.
        """
        if max_entries < 1 or (max_entries_per_scope is not None and max_entries_per_scope < 1):
            msg = "cache limits must be at least 1"
            raise ValueError(msg)
        self._max_entries = max_entries
        self._max_per_scope = max_entries_per_scope
        self._entries: OrderedDict[tuple[str, str], str] = OrderedDict()

    async def get(self, scope: str, key: str) -> Entry | None:
        """Return a fresh copy of the entry, marking it most recently used."""
        _check_scope(scope)
        text = self._entries.get((scope, key))
        if text is None:
            logger.debug("cache miss %s", _short(key), extra={"scope": scope})
            return None
        self._entries.move_to_end((scope, key))
        logger.debug("cache hit %s", _short(key), extra={"scope": scope})
        return Entry.from_json(text)

    async def put(self, scope: str, key: str, entry: Entry) -> None:
        """Store the serialised entry and evict by the limits."""
        _check_scope(scope)
        self._entries[(scope, key)] = entry.to_json()
        self._entries.move_to_end((scope, key))
        if self._max_per_scope is not None:
            self._evict_scope(scope, self._max_per_scope)
        while len(self._entries) > self._max_entries:
            self._evict(next(iter(self._entries)))

    async def drop_scope(self, scope: str) -> None:
        """Remove every entry of ``scope``."""
        _check_scope(scope)
        for stored in [item for item in self._entries if item[0] == scope]:
            del self._entries[stored]
        logger.debug("cache scope dropped", extra={"scope": scope})

    def _evict_scope(self, scope: str, limit: int) -> None:
        """Evict the least recently used entries of ``scope`` until it holds ``limit``."""
        members = [item for item in self._entries if item[0] == scope]
        for stored in members[: max(0, len(members) - limit)]:
            self._evict(stored)

    def _evict(self, stored: tuple[str, str]) -> None:
        """Remove one entry and log it."""
        del self._entries[stored]
        logger.debug("cache evict %s", _short(stored[1]), extra={"scope": stored[0]})


class DiskCache:
    """A persistent store: one SQLite file, values as JSON text, never pickle (ch. 8.4).

    Limits count payload bytes (the JSON text), not SQLite overhead, and evict by access order
    (least recently read or written first). Every call opens its own connection in a worker thread,
    so the cache is thread-safe and several processes may share the file through SQLite's locking;
    writers of one key write the same content, so the last writer winning is harmless.

    Degraded operation is declared with a ``WARNING`` log (ADR 0020, ch. 8.14): an unreadable entry
    is a miss and is deleted, a non-database file is moved aside as ``<name>.corrupt``, an unknown
    schema version resets the cache, and a locked database makes ``get`` a miss and ``put`` a no-op.
    ``drop_scope`` is a deletion the caller relies on, so a locked database raises there. The file
    does not shrink after evictions or ``drop_scope`` (no ``VACUUM``).
    """

    def __init__(
        self,
        *,
        path: Path,
        max_bytes: int,
        max_bytes_per_scope: int | None = None,
        busy_timeout_s: float = 5.0,
    ) -> None:
        """Remember the settings; nothing is created until the first call.

        Args:
            path: The SQLite file; its parent directory is created on first use.
            max_bytes: Payload bytes kept over all scopes.
            max_bytes_per_scope: Optional payload bytes kept per scope.
            busy_timeout_s: Seconds to wait for a lock held by another connection. Unlike the
                limits this is infrastructure, not an engineering decision, so it has a default.

        Raises:
            ValueError: If a limit is below 1 or ``busy_timeout_s`` is not positive.
        """
        if max_bytes < 1 or (max_bytes_per_scope is not None and max_bytes_per_scope < 1):
            msg = "cache limits must be at least 1"
            raise ValueError(msg)
        if busy_timeout_s <= 0:
            msg = "busy_timeout_s must be positive"
            raise ValueError(msg)
        self._busy_timeout_s = busy_timeout_s
        self._path = path
        self._max_bytes = max_bytes
        self._max_per_scope = max_bytes_per_scope
        self._lock = threading.Lock()

    async def get(self, scope: str, key: str) -> Entry | None:
        """Return a fresh entry and mark it most recently used; a miss on any read problem."""
        _check_scope(scope)
        try:
            found = await asyncio.to_thread(self._read, scope, key)
        except sqlite3.OperationalError:
            logger.warning(
                "disk cache database locked, %s treated as a miss",
                _short(key),
                extra={"scope": scope},
            )
            return None
        logger.debug("cache %s %s", "hit" if found else "miss", _short(key), extra={"scope": scope})
        return found

    async def put(self, scope: str, key: str, entry: Entry) -> None:
        """Store the entry and evict by the limits; skipped if it alone exceeds a limit."""
        _check_scope(scope)
        text = entry.to_json()
        size = len(text.encode())
        if size > self._max_bytes or (
            self._max_per_scope is not None and size > self._max_per_scope
        ):
            logger.debug(
                "entry too large for the disk cache, not stored: %s",
                _short(key),
                extra={"scope": scope},
            )
            return
        try:
            await asyncio.to_thread(self._write, scope, key, text, size)
        except sqlite3.OperationalError:
            logger.warning(
                "disk cache database locked, %s not stored", _short(key), extra={"scope": scope}
            )

    async def drop_scope(self, scope: str) -> None:
        """Delete every entry of ``scope``.

        Raises:
            StoreError: If the database stays locked past the busy timeout; no retry follows.
        """
        _check_scope(scope)
        try:
            await asyncio.to_thread(self._drop, scope)
        except sqlite3.OperationalError as exc:
            logger.warning(
                "disk cache database locked, scope not dropped",
                exc_info=exc,
                extra={"scope": scope},
            )
            msg = f"the cache could not delete scope {scope}; the store is busy, retry later"
            raise StoreError(msg) from exc
        logger.debug("cache scope dropped", extra={"scope": scope})

    def _read(self, scope: str, key: str) -> Entry | None:
        """Look the entry up (worker thread); delete and warn about an unreadable row."""
        with closing(self._connect()) as db, db:
            row = db.execute(
                "SELECT value FROM entries WHERE scope = ? AND key = ?", (scope, key)
            ).fetchone()
            if row is None:
                return None
            try:
                found = Entry.from_json(row[0])
            except ValueError:
                db.execute("DELETE FROM entries WHERE scope = ? AND key = ?", (scope, key))
                logger.warning(
                    "disk cache entry unreadable and recomputed: %s",
                    _short(key),
                    extra={"scope": scope},
                )
                return None
            db.execute(
                "UPDATE entries SET tick = (SELECT MAX(tick) + 1 FROM entries)"
                " WHERE scope = ? AND key = ?",
                (scope, key),
            )
            return found

    def _write(self, scope: str, key: str, text: str, size: int) -> None:
        """Insert the row and evict in one transaction (worker thread)."""
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT OR REPLACE INTO entries (scope, key, value, size, tick)"
                " VALUES (?, ?, ?, ?, (SELECT COALESCE(MAX(tick), 0) + 1 FROM entries))",
                (scope, key, text, size),
            )
            if self._max_per_scope is not None:
                self._trim(db, "WHERE scope = ?", (scope,), self._max_per_scope)
            self._trim(db, "", (), self._max_bytes)

    def _drop(self, scope: str) -> None:
        """Delete the rows of ``scope`` (worker thread)."""
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM entries WHERE scope = ?", (scope,))

    @staticmethod
    def _trim(db: sqlite3.Connection, where: str, params: tuple[str, ...], limit: int) -> None:
        """Delete the least recently used rows matching ``where`` until their payload fits ``limit``.

        ``where`` is one of the constant clauses of :meth:`_write`, never caller data.
        """
        (total,) = db.execute(
            f"SELECT COALESCE(SUM(size), 0) FROM entries {where}", params
        ).fetchone()
        rows = iter(
            db.execute(
                f"SELECT scope, key, size FROM entries {where} ORDER BY tick", params
            ).fetchall()
        )
        while total > limit:
            scope, key, size = next(rows)
            db.execute("DELETE FROM entries WHERE scope = ? AND key = ?", (scope, key))
            total -= size
            logger.debug("cache evict %s", _short(key), extra={"scope": scope})

    def _connect(self) -> sqlite3.Connection:
        """Open the database, creating it, or moving a file that is no database aside."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self._open()
        except sqlite3.OperationalError:
            raise
        except sqlite3.DatabaseError:
            pass
        with self._lock:  # one thread repairs; another may already have
            try:
                return self._open()
            except sqlite3.OperationalError:
                raise
            except sqlite3.DatabaseError:
                self._move_aside()
        return self._open()

    def _open(self) -> sqlite3.Connection:
        """Open a connection and make sure the schema is current."""
        db = sqlite3.connect(self._path, timeout=self._busy_timeout_s)
        try:
            db.execute("PRAGMA journal_mode = WAL")
            (version,) = db.execute("PRAGMA user_version").fetchone()
            if version not in (0, _SCHEMA_VERSION):
                logger.warning(
                    "disk cache schema version %s is unknown, resetting the cache", version
                )
                db.execute("DROP TABLE IF EXISTS entries")
            if version != _SCHEMA_VERSION:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS entries (scope TEXT NOT NULL, key TEXT NOT NULL,"
                    " value TEXT NOT NULL, size INTEGER NOT NULL, tick INTEGER NOT NULL,"
                    " PRIMARY KEY (scope, key))"
                )
                db.execute("CREATE INDEX IF NOT EXISTS entries_tick ON entries (tick)")
                db.execute("CREATE INDEX IF NOT EXISTS entries_scope_tick ON entries (scope, tick)")
                db.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        except BaseException:
            db.close()
            raise
        return db

    def _move_aside(self) -> None:
        """Rename the unusable file to ``<name>.corrupt``, replacing an older one."""
        aside = self._path.with_name(f"{self._path.name}.corrupt")
        logger.warning("disk cache file is no database, moved aside to %s", aside.name)
        self._path.replace(aside)
        for suffix in ("-wal", "-shm"):
            self._path.with_name(f"{self._path.name}{suffix}").unlink(missing_ok=True)
