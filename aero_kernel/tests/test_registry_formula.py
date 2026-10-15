"""Registry: registering formula implementations (ARCHITECTURE ch. 8.12)."""

from collections.abc import Callable, Coroutine, Mapping

import pytest
from aero_kernel.registry import Implementation, Registry, RegistryError

FINGERPRINT = "sha256:" + "0" * 64


async def _impl(x: Mapping[str, float], ctx: object) -> dict[str, float]:
    return {"v_s": 1.0}


def test_formula_is_registered_under_its_qualified_slug_and_returned_unchanged() -> None:
    registry = Registry()
    decorated = registry.formula("stall-speed", interface=FINGERPRINT)(_impl)
    assert decorated is _impl
    found = registry.implementation("calc:stall-speed")
    assert found == Implementation(slug="calc:stall-speed", func=_impl, interface=FINGERPRINT)


def test_bare_and_qualified_slug_find_the_same_implementation() -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=FINGERPRINT)(_impl)
    assert registry.implementation("stall-speed") is registry.implementation("calc:stall-speed")


def test_other_namespace_is_kept() -> None:
    registry = Registry()
    registry.formula("other:stall-speed", interface=FINGERPRINT)(_impl)
    assert registry.implementation("other:stall-speed") is not None
    assert registry.implementation("stall-speed") is None


def test_unregistered_formula_has_no_implementation() -> None:
    assert Registry().implementation("stall-speed") is None


def test_duplicate_formula_is_an_error_even_for_the_same_function() -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=FINGERPRINT)(_impl)
    with pytest.raises(RegistryError, match="calc:stall-speed"):
        registry.formula("stall-speed", interface=FINGERPRINT)(_impl)


def test_bare_and_qualified_spelling_collide() -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=FINGERPRINT)(_impl)
    with pytest.raises(RegistryError, match="already"):
        registry.formula("calc:stall-speed", interface=FINGERPRINT)(_impl)


def test_non_coroutine_formula_is_rejected() -> None:
    def sync(x: Mapping[str, float], ctx: object) -> dict[str, float]:
        return {}

    with pytest.raises(RegistryError, match="coroutine"):
        Registry().formula("stall-speed", interface=FINGERPRINT)(
            sync  # pyright: ignore[reportArgumentType]  # deliberately not a coroutine function
        )


@pytest.mark.parametrize(
    "slug", ["", "Stall_Speed", "calc:", ":stall-speed", "a:b:c", "stall speed"]
)
def test_malformed_slug_is_rejected(slug: str) -> None:
    with pytest.raises(RegistryError, match="slug"):
        Registry().formula(slug, interface=FINGERPRINT)(_impl)


@pytest.mark.parametrize(
    "interface",
    [
        "",
        "abc",
        "sha256:xyz",
        "sha256:" + "0" * 63,
        "sha256:" + "0" * 65,
        "sha256:" + "0" * 64 + "x",
    ],
)
def test_malformed_interface_fingerprint_is_rejected(interface: str) -> None:
    with pytest.raises(RegistryError, match="interface"):
        Registry().formula("stall-speed", interface=interface)(_impl)


def test_formula_must_take_exactly_x_and_ctx() -> None:
    async def one(x: Mapping[str, float]) -> dict[str, float]:
        return {}

    async def three(x: Mapping[str, float], ctx: object, extra: object) -> dict[str, float]:
        return {}

    for func in (one, three):
        with pytest.raises(RegistryError, match="exactly 2"):
            Registry().formula("stall-speed", interface=FINGERPRINT)(func)


async def _keyword_only_ctx(x: Mapping[str, float], *, ctx: object) -> dict[str, float]:
    return {}


async def _var_keyword(x: Mapping[str, float], **kwargs: object) -> dict[str, float]:
    return {}


async def _var_positional(*args: object) -> dict[str, float]:
    return {}


@pytest.mark.parametrize("func", [_keyword_only_ctx, _var_keyword])
def test_formula_that_cannot_be_called_with_x_and_ctx_positionally_is_rejected(
    func: Callable[..., Coroutine[object, object, dict[str, float]]],
) -> None:
    with pytest.raises(RegistryError, match="exactly 2"):
        Registry().formula("stall-speed", interface=FINGERPRINT)(func)


def test_formula_taking_var_positional_is_accepted() -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=FINGERPRINT)(_var_positional)
    assert registry.implementation("stall-speed") is not None
