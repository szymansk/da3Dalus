"""The solver adapter base: capability detection, tool versions, error form (Q10)."""

import importlib.metadata
import importlib.util
import logging
import subprocess
import sys
from collections.abc import Mapping
from typing import ClassVar

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.base import SolverAdapter


class PresentAdapter(SolverAdapter):
    """Fake adapter whose tool (pytest) is installed."""

    tool: ClassVar[str] = "fake-present"
    # the distribution name (pytest) differs from the module name (_pytest) on purpose
    requirements: ClassVar[Mapping[str, str]] = {"pytest": "_pytest"}


class MissingAdapter(SolverAdapter):
    """Fake adapter whose tool is not installed."""

    tool: ClassVar[str] = "fake-missing"
    requirements: ClassVar[Mapping[str, str]] = {
        "pytest": "_pytest",
        "no-such-distribution": "no_such_module_xyz",
    }

    def simulate(self) -> str:
        """A public adapter method: the first thing it does is require the tool."""
        self.require_available()
        return "ran"


def test_adapter_holds_the_runtime_it_was_given() -> None:
    runtime = SolverRuntime()
    assert PresentAdapter(runtime).runtime is runtime


def test_an_installed_tool_is_available_and_reports_its_version() -> None:
    adapter = PresentAdapter(SolverRuntime())
    assert adapter.available() is True
    assert adapter.tool_versions() == {"pytest": importlib.metadata.version("pytest")}


def test_a_missing_tool_is_not_available_and_has_no_versions() -> None:
    adapter = MissingAdapter(SolverRuntime())
    assert adapter.available() is False
    # a tool that cannot run has no version, although one of its distributions is installed
    assert adapter.tool_versions() == {}


def test_a_dotted_module_name_is_rejected_when_the_class_is_defined() -> None:
    with pytest.raises(ValueError, match="top-level"):

        class _Dotted(SolverAdapter):  # pyright: ignore[reportUnusedClass]  # defining it is the test
            tool: ClassVar[str] = "fake-dotted"
            requirements: ClassVar[Mapping[str, str]] = {"dist": "pkg.sub"}


@pytest.mark.parametrize("error", [ImportError("broken"), ValueError("no __spec__")])
def test_a_find_spec_failure_means_unavailable_with_a_warning(
    error: Exception, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def failing_find_spec(name: str) -> None:
        raise error

    monkeypatch.setattr(importlib.util, "find_spec", failing_find_spec)
    adapter = PresentAdapter(SolverRuntime())
    with caplog.at_level(logging.WARNING, logger="aero_kernel.solvers.base"):
        assert adapter.available() is False
        with pytest.raises(FormulaError) as caught:
            adapter.require_available()
    assert caught.value.code == "tool_unavailable"
    assert any("_pytest" in r.getMessage() and "find" in r.getMessage() for r in caplog.records)


def test_versions_are_read_once() -> None:
    adapter = PresentAdapter(SolverRuntime())
    assert adapter.tool_versions() is adapter.tool_versions()


def test_require_available_passes_for_an_installed_tool() -> None:
    PresentAdapter(SolverRuntime()).require_available()


def test_a_missing_tool_raises_tool_unavailable_not_import_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Q10."""
    adapter = MissingAdapter(SolverRuntime())
    with (
        caplog.at_level(logging.WARNING, logger="aero_kernel.solvers.base"),
        pytest.raises(FormulaError) as caught,
    ):
        adapter.simulate()
    error = caught.value
    assert error.category is ErrorCategory.TOOL_UNAVAILABLE
    assert error.code == "tool_unavailable"
    assert "fake-missing" in error.message
    assert "no-such-distribution" in error.hint
    assert error.detail == {"tool": "fake-missing", "missing": ["no-such-distribution"]}
    (record,) = [r for r in caplog.records if r.name == "aero_kernel.solvers.base"]
    assert record.levelno == logging.WARNING


def test_importing_the_package_does_not_import_a_solver_library() -> None:
    """Q10: capability is detected without importing the tool at module level."""
    code = (
        "import sys\n"
        "import aero_kernel.solvers.base, aero_kernel.runtime\n"
        "assert 'aerosandbox' not in sys.modules\n"
        "assert 'casadi' not in sys.modules\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr


def test_checking_availability_imports_nothing() -> None:
    """Run in a fresh interpreter: the process of a test run has imported anything before."""
    code = (
        "import sys\n"
        "from collections.abc import Mapping\n"
        "from typing import ClassVar\n"
        "from aero_kernel.runtime import SolverRuntime\n"
        "from aero_kernel.solvers.base import SolverAdapter\n"
        "assert 'pydoc_data' not in sys.modules\n"
        "modules_before = set(sys.modules)\n"
        "class Harmless(SolverAdapter):\n"
        "    tool: ClassVar[str] = 'fake-harmless'\n"
        "    requirements: ClassVar[Mapping[str, str]] = {'pydoc-data': 'pydoc_data'}\n"
        "adapter = Harmless(SolverRuntime())\n"
        "assert adapter.available() is True\n"
        "adapter.require_available()\n"
        "assert set(sys.modules) == modules_before\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
