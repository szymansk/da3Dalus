"""Canonical JSON and its hash: the one serialisation behind every content hash (ch. 8.4, 8.9).

Sorted keys, separators ``,`` and ``:``, UTF-8 without ASCII escaping, floats as ``repr``. The
canon model's ``content_hash`` and, later, the cache keys are built on it, so equal content always
serialises, and hashes, alike.
"""

import hashlib
import json

from pydantic import JsonValue

__all__ = ["canonical_json", "sha256_of"]


def canonical_json(value: JsonValue) -> bytes:
    """Serialise a JSON value canonically.

    Args:
        value: A JSON value; floats must be finite.

    Returns:
        The canonical UTF-8 text: sorted keys, no whitespace, non-ASCII kept, floats via ``repr``.
    """
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return text.encode("utf-8")


def sha256_of(value: JsonValue) -> str:
    """Hash a JSON value: ``"sha256:"`` plus the hex SHA-256 of its UTF-8 canonical JSON.

    Args:
        value: A JSON value; floats must be finite.

    Returns:
        The prefixed hex digest.
    """
    digest = hashlib.sha256(canonical_json(value)).hexdigest()
    return f"sha256:{digest}"
