"""Node cache: the cache key, the build digest, ``Entry``, the ``NodeStore`` protocol and its stores (ch. 8.4).

The cache maps keys to a node's outputs and warnings and never changes a value. It knows only JSON
values; converting typed results to and from JSON is the engine's job. Entries are kept serialised and
every hit builds a fresh object, so no caller can corrupt another caller's result.
"""

from collections.abc import Mapping

from aero_kernel.canonical import sha256_of
from aero_kernel.schema import Accuracy
from pydantic import JsonValue

__all__ = ["cache_key"]


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
