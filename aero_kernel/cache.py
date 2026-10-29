"""Node cache: key, build digest, ``Entry``, the LRU cache and its in-flight deduplication (ch. 8.4).

The cache maps keys to a node's outputs and warnings and never changes a value. It knows only JSON
values; converting typed results to and from JSON is the engine's job. Entries are kept serialised and
every hit builds a fresh object, so no caller can corrupt another caller's result.

The engine reads and writes through :class:`NodeCache`: it claims a key (``claim``) before running a node
and releases it (``release``) with the entry to store, or ``None``, once the run is over. The stateful facade
``CachedKernel`` passes in a :class:`DedupedCache`, which serves a stored entry, lets a second
claim of a key that is still running wait for that run, and stores only what a run released.
"""

import asyncio
import hashlib
import logging
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self

from aero_kernel.canonical import sha256_of
from aero_kernel.errors import check_finite_json
from aero_kernel.schema import KernelWarning, RuleUsed, Seconds
from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

__all__ = [
    "DedupedCache",
    "Entry",
    "Lease",
    "MemoryCache",
    "NodeCache",
    "build_digest",
    "cache_key",
]

logger = logging.getLogger(__name__)

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
    formula: str,
    application: str,
    world: str | None,
    inputs: Mapping[str, JsonValue],
    build_digest: str,
    tool_versions: Mapping[str, str],
    solver_settings: Mapping[str, JsonValue],
    rule_overrides: Mapping[str, float],
) -> str:
    """Compute the cache key of one node (ch. 8.4): SHA-256 over the canonical JSON of everything.

    Floats are hashed exactly (``repr``), never rounded; ``-0.0`` counts as ``0.0``.

    Args:
        formula: Qualified formula slug of the node.
        application: Application id within the formula.
        world: Canonical world assignment, or ``None`` for a certain node.
        inputs: Direct input values by parameter name.
        build_digest: Hash over the code and canon model (see :func:`build_digest`).
        tool_versions: Versions of the tools the node uses; for a node with worlds, those of the
            tool of its world (``CanonModel.tool_of``), not of its formula.
        solver_settings: Settings of those tools, as ``Solvers.settings_of`` returns them.
        rule_overrides: The call's whole ``AircraftInput.rule_overrides``. A formula or adapter
            reads rule thresholds that are not bound parameters; the canon values are in the
            build digest, the caller's overrides are here (maintainer 2026-10-29, #1332, option A).

    Returns:
        ``"sha256:"`` plus the hex digest.

    Raises:
        ValueError: If ``inputs`` holds NaN or infinity (validation rejects those earlier).
    """
    return sha256_of(
        {
            "application": {"formula": formula, "application": application},
            "world": world,
            "inputs": dict(inputs),
            "build_digest": build_digest,
            "tool_versions": dict(tool_versions),
            "solver_settings": dict(solver_settings),
            "rule_overrides": dict[str, JsonValue](rule_overrides),
        }
    )


class Entry(BaseModel):
    """What the cache stores for one node: outputs, own warnings, thresholds read, run time (ch. 8.4).

    There is no status or error field: errors, ``skipped`` and ``not_applicable`` are never stored.
    The JSON form keeps every float exactly (``-0.0`` included), so a hit is bit-identical to the
    computed value; only cache *keys* normalise ``-0.0``.

    Attributes:
        outputs: Output parameter name to JSON value, for every output of the application.
        warnings: The node's warnings, pre- and postcondition warnings included, as received.
        rules_used: The rule thresholds the node read while it ran; a hit declares them again in
            ``provenance.rules_used`` (maintainer 2026-10-29, #1332, option A).
        own_s: The seconds the run took when it was computed. A hit reports this measured time
            (with ``from_cache``), never the near-zero time of the lookup (ch. 8.3). ``None`` means
            the writer measured no time; the entry is still valid.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    outputs: dict[str, JsonValue]
    warnings: tuple[KernelWarning, ...]
    rules_used: tuple[RuleUsed, ...] = ()
    own_s: Seconds | None = None

    @model_validator(mode="after")
    def _check_finite(self) -> Self:
        """Reject NaN and infinity, which would serialise as ``null``."""
        check_finite_json(self.outputs, "outputs")
        return self

    def to_json(self) -> str:
        """Serialise to the JSON text the cache keeps."""
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


def _short(key: str) -> str:
    """The key prefix that is logged instead of the whole key."""
    return key[:_KEY_PREFIX]


class MemoryCache:
    """An in-process LRU cache with one global limit (ch. 8.4).

    The methods are plain synchronous calls that run to completion, so on one event loop no lock
    is needed.
    """

    def __init__(self, *, max_entries: int) -> None:
        """Create an empty cache.

        Args:
            max_entries: Entries kept; the least recently used one is evicted.

        Raises:
            ValueError: If the limit is below 1.
        """
        if max_entries < 1:
            msg = "max_entries must be at least 1"
            raise ValueError(msg)
        self._max_entries = max_entries
        self._texts: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> Entry | None:
        """Return a fresh copy of the entry, marking it most recently used."""
        text = self._texts.get(key)
        if text is None:
            logger.debug("cache miss %s", _short(key))
            return None
        self._texts.move_to_end(key)
        logger.debug("cache hit %s", _short(key))
        return Entry.from_json(text)

    def put(self, key: str, entry: Entry) -> None:
        """Store the serialised entry and evict the least recently used ones over the limit."""
        self._texts[key] = entry.to_json()
        self._texts.move_to_end(key)
        while len(self._texts) > self._max_entries:
            oldest = next(iter(self._texts))
            del self._texts[oldest]
            logger.debug("cache evict %s", _short(oldest))


class Lease(Protocol):
    """One claim of a cache key: the stored entry, or the duty to release the run's outcome."""

    @property
    def entry(self) -> Entry | None:
        """The stored entry (a fresh object), or ``None``: the claimant runs the node."""
        ...

    def release(self, entry: Entry | None) -> None:
        """Hand back the claim with the entry to store, or ``None`` for a run that is not stored.

        Called exactly once, also when the run failed or was cancelled.
        """
        ...


class NodeCache(Protocol):
    """What the engine reads and writes the cache through (ch. 8.4)."""

    async def claim(self, key: str) -> Lease:
        """Claim a key before running its node."""
        ...


@dataclass
class _Lease:
    """A claim of :class:`DedupedCache`; ``on_release`` is ``None`` for a hit."""

    entry: Entry | None
    on_release: Callable[[Entry | None], None] | None = None

    def release(self, entry: Entry | None) -> None:
        """Pass the outcome on, once; a later call does nothing."""
        on_release, self.on_release = self.on_release, None
        if on_release is not None:
            on_release(entry)


class DedupedCache:
    """A :class:`MemoryCache` with in-flight deduplication (ch. 8.4).

    The first claim of a key that is neither stored nor running runs the node; a claim of a key
    that is running waits for that run (``asyncio.shield``, so a waiter that is cancelled never
    cancels the run it waits for). When the run is stored, every waiter gets the stored entry, a
    fresh object each. When it is not (an error, a non-``ok`` status, a timeout or a cancellation),
    the outcome is **not shared**: each waiter runs the node itself, concurrently, and stores what
    it computes. A failure is never cached, and sharing it would hand one call's error wording to
    another call.

    All waiting happens on one event loop: a future belongs to the loop that created it. A claim
    from another loop while a run of the same key is in flight is a defect of the caller and
    raises ``RuntimeError``.
    """

    def __init__(self, store: MemoryCache) -> None:
        """Create the cache over a store.

        Args:
            store: The LRU cache the entries are kept in.
        """
        self._store = store
        self._in_flight: dict[str, asyncio.Future[str | None]] = {}

    async def claim(self, key: str) -> Lease:
        """Return the stored entry, wait for a run of the key in flight, or claim its run.

        Raises:
            RuntimeError: If a run of the key is in flight on another event loop.
        """
        stored = self._store.get(key)
        if stored is not None:
            return _Lease(stored)
        running = self._in_flight.get(key)
        if running is not None:
            if running.get_loop() is not asyncio.get_running_loop():
                msg = "a CachedKernel serves one event loop; it was called from a second one"
                raise RuntimeError(msg)
            text = await asyncio.shield(running)
            if text is not None:
                logger.debug("cache hit after waiting %s", _short(key))
                return _Lease(Entry.from_json(text))
            logger.debug("in-flight run of %s was not stored; running it again", _short(key))
            return _Lease(None, lambda entry: self._store_only(key, entry))
        future: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
        self._in_flight[key] = future
        return _Lease(None, lambda entry: self._finish(key, future, entry))

    def _store_only(self, key: str, entry: Entry | None) -> None:
        """Store the outcome of a run that no other claim waits for."""
        if entry is not None:
            self._store.put(key, entry)

    def _finish(self, key: str, future: "asyncio.Future[str | None]", entry: Entry | None) -> None:
        """Store the outcome of a claimed run and wake its waiters."""
        self._store_only(key, entry)
        if self._in_flight.get(key) is future:
            del self._in_flight[key]
        if not future.done():
            future.set_result(None if entry is None else entry.to_json())
