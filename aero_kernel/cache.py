"""Node cache: the cache key, the build digest, ``Entry`` and the in-memory LRU cache (ch. 8.4).

The cache maps keys to a node's outputs and warnings and never changes a value. It knows only JSON
values; converting typed results to and from JSON is the engine's job. Entries are kept serialised and
every hit builds a fresh object, so no caller can corrupt another caller's result.
"""

import hashlib
import logging
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from aero_kernel.canonical import sha256_of
from aero_kernel.errors import check_finite_json
from aero_kernel.schema import KernelWarning
from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

__all__ = [
    "Entry",
    "MemoryCache",
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
) -> str:
    """Compute the cache key of one node (ch. 8.4): SHA-256 over the canonical JSON of everything.

    Floats are hashed exactly (``repr``), never rounded; ``-0.0`` counts as ``0.0``.

    Args:
        formula: Qualified formula slug of the node.
        application: Application id within the formula.
        world: Canonical world assignment, or ``None`` for a certain node.
        inputs: Direct input values by parameter name.
        build_digest: Hash over the code and canon model (see :func:`build_digest`).
        tool_versions: Versions of the tools the node uses.

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


def _short(key: str) -> str:
    """The key prefix that is logged instead of the whole key."""
    return key[:_KEY_PREFIX]


class MemoryCache:
    """An in-process LRU cache with one global limit (ch. 8.4).

    The methods are plain synchronous methods; none awaits or yields inside its critical section, so
    on one event loop no lock is needed.
    """

    def __init__(self, *, max_entries: int) -> None:
        """Create an empty cache.

        Args:
            max_entries: Entries kept; the least recently used one is evicted.

        Raises:
            ValueError: If the limit is below 1.
        """
        if max_entries < 1:
            msg = "cache limits must be at least 1"
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
