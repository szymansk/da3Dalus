"""Canonical JSON and its SHA-256 (ARCHITECTURE ch. 8.4, 8.9)."""

import hashlib

from aero_kernel.canonical import canonical_json, sha256_of


def test_keys_are_sorted_and_separators_compact() -> None:
    assert canonical_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


def test_unicode_is_not_escaped() -> None:
    assert canonical_json({"k": "α—ü"}) == '{"k":"α—ü"}'


def test_floats_use_repr() -> None:
    assert canonical_json([1.0, 0.1, 1e-07, 1.5e300]) == "[1.0,0.1,1e-07,1.5e+300]"


def test_nested_order_is_independent_of_insertion() -> None:
    assert canonical_json({"x": {"b": 1, "a": 2}}) == canonical_json({"x": {"a": 2, "b": 1}})


def test_sha256_of_is_prefixed_hash_of_utf8_canonical_json() -> None:
    digest = hashlib.sha256('{"a":1}'.encode()).hexdigest()
    assert sha256_of({"a": 1}) == f"sha256:{digest}"
