"""Canonical JSON and its hash: the one serialisation behind every content hash (ch. 8.4, 8.9).

Sorted keys, separators ``,`` and ``:``, UTF-8 without ASCII escaping, floats as ``repr``. The
canon model's ``content_hash`` and, later, the cache keys are built on it, so equal content always
serialises, and hashes, alike.
"""

import hashlib
import json
import math

from pydantic import JsonValue

__all__ = ["canonical_json", "sha256_of", "spell_non_finite"]


def _without_negative_zero(value: JsonValue) -> JsonValue:
    """Return ``value`` with every ``-0.0`` replaced by ``0.0``, recursively (ch. 8.4)."""
    if isinstance(value, float):
        return value + 0.0  # -0.0 + 0.0 is 0.0; every other float is unchanged
    if isinstance(value, dict):
        return {key: _without_negative_zero(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_without_negative_zero(item) for item in value]
    return value


def canonical_json(value: JsonValue) -> bytes:
    """Serialise a JSON value canonically.

    Args:
        value: A JSON value; floats must be finite.

    Returns:
        The canonical UTF-8 text: sorted keys, no whitespace, non-ASCII kept, floats via ``repr``, ``-0.0`` as ``0.0``.
    """
    text = json.dumps(
        _without_negative_zero(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
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


def spell_non_finite(value: JsonValue) -> JsonValue:
    """A JSON value with every NaN or infinity spelled out, for a key only (ch. 8.4).

    Validation rejects non-finite numbers in what the kernel reads, but not in the geometry's
    unread fields (``validate.UNREAD_FIELDS``); a key must not fail on them, nor equate them with
    ``null``.

    Args:
        value: A JSON value, possibly with non-finite floats.

    Returns:
        The value with each non-finite float replaced by ``{"non_finite": repr(value)}``.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return {"non_finite": repr(value)}
    if isinstance(value, dict):
        return {name: spell_non_finite(item) for name, item in value.items()}
    if isinstance(value, list):
        return [spell_non_finite(item) for item in value]
    return value
