"""Tests for cad_designer.decorators.general_decorators."""
import os
import logging

import pytest

from cad_designer.decorators.general_decorators import conditional_execute, fluent_init


# ---- @conditional_execute -----------------------------------------------

class _ConditionalHost:
    """Dummy class used to test the conditional_execute decorator."""

    def __init__(self, value: int = 0):
        self.value = value

    @conditional_execute("TEST_COND_EXEC_FLAG")
    def double_value(self):
        self.value *= 2
        return self


class TestConditionalExecute:
    """Verify @conditional_execute honours / ignores the env-var gate."""

    ENV_VAR = "TEST_COND_EXEC_FLAG"

    @pytest.fixture(autouse=True)
    def _clean_env(self):
        """Remove the test env-var before and after each test."""
        os.environ.pop(self.ENV_VAR, None)
        yield
        os.environ.pop(self.ENV_VAR, None)

    @pytest.mark.parametrize("flag", ["1", "ON", "TRUE", "ENABLED"])
    def test_executes_when_env_var_enabled(self, flag):
        os.environ[self.ENV_VAR] = flag
        host = _ConditionalHost(value=5)
        result = host.double_value()
        assert host.value == 10
        assert result is host  # decorated function returns self

    @pytest.mark.parametrize("flag", ["on", "true", "enabled"])
    def test_executes_case_insensitive(self, flag):
        """The decorator uppercases the env-var value before comparing."""
        os.environ[self.ENV_VAR] = flag
        host = _ConditionalHost(value=3)
        host.double_value()
        assert host.value == 6

    def test_skips_when_env_var_not_set(self):
        host = _ConditionalHost(value=7)
        result = host.double_value()
        assert host.value == 7  # unchanged
        assert result is host  # returns self even when skipped

    @pytest.mark.parametrize("flag", ["0", "OFF", "FALSE", "DISABLED", "random"])
    def test_skips_when_env_var_not_in_allowed_set(self, flag):
        os.environ[self.ENV_VAR] = flag
        host = _ConditionalHost(value=4)
        host.double_value()
        assert host.value == 4

    def test_logs_warning_when_skipped(self, caplog):
        host = _ConditionalHost(value=1)
        with caplog.at_level(logging.WARNING):
            host.double_value()
        assert "has not been executed" in caplog.text
        assert self.ENV_VAR in caplog.text

    def test_preserves_function_name(self):
        """@wraps should preserve the original function name."""
        assert _ConditionalHost.double_value.__name__ == "double_value"


# ---- @fluent_init -------------------------------------------------------

@fluent_init
class _FluentPoint:
    """Dummy class decorated with @fluent_init."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y


class TestFluentInit:
    """Verify @fluent_init adds a static .init() factory method."""

    def test_init_class_method_exists(self):
        assert hasattr(_FluentPoint, "init")

    def test_init_returns_instance(self):
        p = _FluentPoint.init(x=1.0, y=2.0)
        assert isinstance(p, _FluentPoint)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_init_uses_defaults(self):
        p = _FluentPoint.init()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_init_with_positional_args(self):
        p = _FluentPoint.init(3.0, 4.0)
        assert p.x == 3.0
        assert p.y == 4.0

    def test_normal_constructor_still_works(self):
        p = _FluentPoint(x=5.0, y=6.0)
        assert isinstance(p, _FluentPoint)
        assert p.x == 5.0

    @pytest.mark.xfail(
        reason="fluent_init uses @wraps(cls.__init__) which copies the "
               "original signature including 'self'; production code quirk",
        strict=True,
    )
    def test_init_signature_omits_self(self):
        """Ideally .init() signature should not include 'self', but the
        current implementation copies the full __init__ signature."""
        import inspect
        sig = inspect.signature(_FluentPoint.init)
        assert "self" not in sig.parameters

    def test_init_signature_contains_params(self):
        """The .init() signature should contain the real parameters."""
        import inspect
        sig = inspect.signature(_FluentPoint.init)
        assert "x" in sig.parameters
        assert "y" in sig.parameters
