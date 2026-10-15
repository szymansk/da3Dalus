"""The solver adapter base: capability detection, tool versions, error form (Q10)."""

import importlib.metadata
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
    """Fake adapter whose tool (pydantic) is installed."""

    tool: ClassVar[str] = "fake-present"
    requirements: ClassVar[Mapping[str, str]] = {"pydantic": "pydantic"}


class MissingAdapter(SolverAdapter):
    """Fake adapter whose tool is not installed."""

    tool: ClassVar[str] = "fake-missing"
    requirements: ClassVar[Mapping[str, str]] = {
        "pydantic": "pydantic",
        "no-such-distribution": "no_such_module_xyz",
    }

    def simulate(self) -> str:
        """A public adapter method: the first thing it does is require the tool."""
        self.require_available()
        return "ran"


class NestedAdapter(SolverAdapter):
    """Fake adapter whose module is a submodule of a missing package."""

    tool: ClassVar[str] = "fake-nested"
    requirements: ClassVar[Mapping[str, str]] = {"no-such-distribution": "no_such_pkg_xyz.sub"}


def test_adapter_holds_the_runtime_it_was_given() -> None:
    runtime = SolverRuntime()
    assert PresentAdapter(runtime).runtime is runtime


def test_an_installed_tool_is_available_and_reports_its_version() -> None:
    adapter = PresentAdapter(SolverRuntime())
    assert adapter.available() is True
    assert adapter.tool_versions() == {"pydantic": importlib.metadata.version("pydantic")}


def test_a_missing_tool_is_not_available_and_not_in_the_versions() -> None:
    adapter = MissingAdapter(SolverRuntime())
    assert adapter.available() is False
    assert adapter.tool_versions() == {"pydantic": importlib.metadata.version("pydantic")}


def test_a_submodule_of_a_missing_package_is_not_available() -> None:
    assert NestedAdapter(SolverRuntime()).available() is False


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
