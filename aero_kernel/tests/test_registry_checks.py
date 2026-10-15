"""Registry: checks, freezing and the default registry (ARCHITECTURE ch. 8.12)."""

import logging
from collections.abc import Callable, Mapping
from typing import Any, cast

import pytest
from aero_kernel import registry as registry_module
from aero_kernel.registry import CheckResult, Registry, RegistryError

FINGERPRINT = "sha256:" + "0" * 64
HELD = CheckResult(state="held", message="ok")


def pre(x: Mapping[str, float]) -> CheckResult:
    return HELD


def post(x: Mapping[str, float], y: Mapping[str, float]) -> CheckResult:
    return HELD


def test_check_result_holds_state_and_message() -> None:
    result = CheckResult(state="violated", message="rho is off")
    assert (result.state, result.message) == ("violated", "rho is off")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"state": "ok", "message": "m"},
        {"state": "held", "message": ""},
        {"state": "held", "message": "m", "extra": 1},
    ],
)
def test_check_result_rejects_bad_state_empty_message_and_unknown_fields(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="validation error"):
        CheckResult(**kwargs)  # pyright: ignore[reportArgumentType]  # deliberately malformed


def test_check_result_is_frozen() -> None:
    with pytest.raises(ValueError, match="frozen"):
        HELD.message = "other"


def test_precondition_and_postcondition_are_registered_per_kind() -> None:
    registry = Registry()
    assert registry.precondition("stall-speed", "rho-ok")(pre) is pre
    assert registry.postcondition("stall-speed", "rho-ok")(post) is post
    assert registry.checks("stall-speed", "pre") == {"rho-ok": pre}
    assert registry.checks("calc:stall-speed", "post") == {"rho-ok": post}


def test_unregistered_checks_are_an_empty_mapping() -> None:
    assert dict(Registry().checks("stall-speed", "pre")) == {}


def test_stacked_decorators_share_one_function_across_formulas() -> None:
    registry = Registry()
    registry.postcondition("stall-speed", "first-peak")(
        registry.postcondition("butterfly-approach", "first-peak")(post)
    )
    assert registry.checks("stall-speed", "post")["first-peak"] is post
    assert registry.checks("butterfly-approach", "post")["first-peak"] is post


def test_duplicate_check_is_an_error_even_for_the_same_function() -> None:
    registry = Registry()
    registry.precondition("stall-speed", "rho-ok")(pre)
    with pytest.raises(RegistryError, match=r"rho-ok.*calc:stall-speed.*already"):
        registry.precondition("stall-speed", "rho-ok")(pre)


@pytest.mark.parametrize("check_id", ["", "Rho", "rho ok", "-rho", "rho_", "rho--ok"])
def test_malformed_check_id_is_rejected(check_id: str) -> None:
    with pytest.raises(RegistryError, match="check id"):
        Registry().precondition("stall-speed", check_id)(pre)


def test_precondition_must_take_exactly_x() -> None:
    with pytest.raises(RegistryError, match="exactly 1"):
        Registry().precondition("stall-speed", "rho-ok")(post)


def test_postcondition_must_take_exactly_x_and_y() -> None:
    with pytest.raises(RegistryError, match="exactly 2"):
        Registry().postcondition("stall-speed", "rho-ok")(pre)


def test_check_must_be_a_plain_function() -> None:
    async def coroutine_check(x: Mapping[str, float]) -> CheckResult:
        return HELD

    with pytest.raises(RegistryError, match="plain function"):
        Registry().precondition("stall-speed", "rho-ok")(
            coroutine_check  # pyright: ignore[reportArgumentType]  # deliberately async
        )


def test_freeze_blocks_every_registration() -> None:
    registry = Registry()
    assert not registry.frozen
    registry.freeze()
    assert registry.frozen
    for register in (
        lambda: registry.formula("a", interface=FINGERPRINT),
        lambda: registry.precondition("a", "b"),
        lambda: registry.postcondition("a", "b"),
    ):
        with pytest.raises(RegistryError, match="frozen"):
            register()


def test_freeze_logs_the_counts_once(caplog: pytest.LogCaptureFixture) -> None:
    registry = Registry()

    async def impl(x: Mapping[str, float], ctx: object) -> dict[str, float]:
        return {}

    registry.formula("stall-speed", interface=FINGERPRINT)(impl)
    registry.precondition("stall-speed", "rho-ok")(pre)
    registry.postcondition("stall-speed", "rho-ok")(post)
    registry.postcondition("stall-speed", "other-ok")(post)
    with caplog.at_level(logging.INFO, logger="aero_kernel.registry"):
        registry.freeze()
        registry.freeze()
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.INFO, "registry frozen: 1 formulas, 3 checks")
    ]


def test_registrations_are_logged_at_debug(caplog: pytest.LogCaptureFixture) -> None:
    registry = Registry()
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.registry"):
        registry.formula("stall-speed", interface=FINGERPRINT)(_impl)
        registry.precondition("stall-speed", "rho-ok")(pre)
        registry.postcondition("stall-speed", "rho-ok")(post)
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.DEBUG, "registered formula calc:stall-speed"),
        (logging.DEBUG, "registered precondition calc:stall-speed/rho-ok"),
        (logging.DEBUG, "registered postcondition calc:stall-speed/rho-ok"),
    ]


def test_module_level_decorators_belong_to_the_default_registry() -> None:
    default = registry_module.DEFAULT_REGISTRY
    assert isinstance(default, Registry)
    assert registry_module.formula.__self__ is default  # pyright: ignore[reportFunctionMemberAccess]  # bound method
    assert registry_module.precondition.__self__ is default  # pyright: ignore[reportFunctionMemberAccess]
    assert registry_module.postcondition.__self__ is default  # pyright: ignore[reportFunctionMemberAccess]


async def _impl(x: Mapping[str, float], ctx: object) -> dict[str, float]:
    return {}


def test_a_decorator_made_before_the_freeze_cannot_register_after_it() -> None:
    registry = Registry()
    decorators: list[Callable[[Any], object]] = [
        registry.formula("stall-speed", interface=FINGERPRINT),
        registry.precondition("stall-speed", "rho-ok"),
        registry.postcondition("stall-speed", "rho-ok"),
    ]
    targets: list[object] = [_impl, pre, post]
    registry.freeze()
    for decorator, target in zip(decorators, targets, strict=True):
        with pytest.raises(RegistryError, match="frozen"):
            decorator(target)
    assert registry.implementation("stall-speed") is None
    assert dict(registry.checks("stall-speed", "pre")) == {}
    assert dict(registry.checks("stall-speed", "post")) == {}


def test_checks_returns_a_copy() -> None:
    registry = Registry()
    registry.precondition("stall-speed", "rho-ok")(pre)
    # ``checks`` is typed as a Mapping; the copy it hands out is a dict, which is what is tested.
    copy = cast("dict[str, Callable[..., CheckResult]]", registry.checks("stall-speed", "pre"))
    copy.clear()
    assert registry.checks("stall-speed", "pre") == {"rho-ok": pre}


def test_check_result_may_be_unchecked() -> None:
    assert CheckResult(state="unchecked", message="no data").state == "unchecked"


def _keyword_only_pre(*, x: Mapping[str, float]) -> CheckResult:
    return HELD


def test_check_that_cannot_be_called_positionally_is_rejected() -> None:
    with pytest.raises(RegistryError, match="exactly 1"):
        Registry().precondition("stall-speed", "rho-ok")(_keyword_only_pre)


def _var_positional_pre(*args: object) -> CheckResult:
    return HELD


def _pre_with_default(x: Mapping[str, float], extra: int = 1) -> CheckResult:
    return HELD


def _post_with_default(x: Mapping[str, float], y: Mapping[str, float], z: int = 1) -> CheckResult:
    return HELD


@pytest.mark.parametrize("func", [_var_positional_pre, _pre_with_default])
def test_precondition_must_declare_exactly_x(func: Callable[..., CheckResult]) -> None:
    with pytest.raises(RegistryError, match="exactly 1"):
        Registry().precondition("stall-speed", "rho-ok")(func)


@pytest.mark.parametrize("func", [_var_positional_pre, _post_with_default])
def test_postcondition_must_declare_exactly_x_and_y(func: Callable[..., CheckResult]) -> None:
    with pytest.raises(RegistryError, match="exactly 2"):
        Registry().postcondition("stall-speed", "rho-ok")(func)
