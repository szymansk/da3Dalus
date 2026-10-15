"""Cache key (ARCHITECTURE ch. 8.4, Q27)."""

import math
from typing import Any

import pytest
from aero_kernel.cache import cache_key
from pydantic import JsonValue


def _key(**overrides: Any) -> str:
    """Key of a base node with ``overrides`` applied."""
    args: dict[str, Any] = {
        "scope": "shared",
        "formula": "flight:stall-speed",
        "application": "default",
        "world": None,
        "inputs": {"mass": 2.5, "area": 0.4},
        "build_digest": "sha256:aa",
        "tool_versions": {"aerosandbox": "4.2.8"},
        "accuracy": "medium",
        "provider_hashes": {},
    }
    args.update(overrides)
    return cache_key(**args)


def test_key_is_prefixed_sha256() -> None:
    key = _key()
    assert key.startswith("sha256:")
    assert len(key) == len("sha256:") + 64


def test_key_is_deterministic_and_order_independent() -> None:
    assert _key(inputs={"mass": 2.5, "area": 0.4}) == _key(inputs={"area": 0.4, "mass": 2.5})


def test_last_bit_of_a_float_changes_the_key() -> None:
    assert _key(inputs={"mass": math.nextafter(2.5, 3.0), "area": 0.4}) != _key()


def test_negative_zero_equals_zero_in_the_key() -> None:
    assert _key(inputs={"x": -0.0}) == _key(inputs={"x": 0.0})


@pytest.mark.parametrize(
    "override",
    [
        {"scope": "aircraft/1"},
        {"formula": "flight:other"},
        {"application": "alt"},
        {"world": "neutral-point=avl"},
        {"build_digest": "sha256:bb"},
        {"tool_versions": {"aerosandbox": "4.2.9"}},
        {"accuracy": "large"},
        {"provider_hashes": {"kat": "sha256:cc"}},
    ],
)
def test_every_component_changes_the_key(override: dict[str, JsonValue]) -> None:
    assert _key(**override) != _key()


def test_formula_and_application_are_not_concatenated() -> None:
    assert _key(formula="a:b", application="c") != _key(formula="a", application="b:c")


def test_non_finite_input_raises() -> None:
    with pytest.raises(ValueError, match="Out of range"):
        _key(inputs={"x": math.nan})


def test_provider_content_changes_the_key() -> None:
    assert _key(provider_hashes={"kat": "sha256:aa"}) != _key(provider_hashes={"kat": "sha256:bb"})


def test_tool_version_text_changes_the_key() -> None:
    assert _key(tool_versions={"avl": "3.36"}) != _key(tool_versions={"avl": "3.40"})


def test_the_sign_of_a_float_changes_the_key() -> None:
    assert _key(inputs={"mass": -2.5, "area": 0.4}) != _key()
