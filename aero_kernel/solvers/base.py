"""Base of the solver adapters (ARCHITECTURE ch. 8.8).

Adapters know no canon names. They return warnings without ``origin``; the engine sets it.
"""

import importlib.metadata
import importlib.util
import logging
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime
from pydantic import JsonValue

logger = logging.getLogger(__name__)

__all__ = ["SolverAdapter"]


class SolverAdapter:
    """Base of every solver adapter (ch. 8.8): capability check, tool versions, the runtime.

    A subclass names its tool and the distributions it needs, each with the module that proves
    it is importable. Nothing is imported here: capability is found with ``find_spec`` and the
    versions with ``importlib.metadata``, so a missing tool is ``tool_unavailable`` and never an
    ``ImportError`` (Q10). Adapters know no canon names. Every public method of a subclass calls
    :meth:`require_available` first, and returns warnings without ``origin`` (the engine sets it).

    Attributes:
        tool: Name of the tool, e.g. ``aerobuildup``.
        requirements: Distribution name -> importable module name, for every distribution the
            adapter relies on (e.g. ``{"aerosandbox": "aerosandbox"}``).
        runtime: The runtime that runs the adapter's CPU work and subprocesses.
    """

    tool: ClassVar[str]
    requirements: ClassVar[Mapping[str, str]]

    def __init__(self, runtime: SolverRuntime) -> None:
        """Create the adapter.

        Args:
            runtime: The runtime of the owning ``compute()`` call or ``CachedKernel``.
        """
        self.runtime = runtime
        self._versions: dict[str, str] | None = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Reject a ``requirements`` entry that is not a top-level module name.

        ``find_spec`` of a dotted name imports its parent package, which would import the tool.

        Raises:
            ValueError: If a module name of ``requirements`` contains a dot.
        """
        super().__init_subclass__(**kwargs)
        for distribution, module in cls.__dict__.get("requirements", {}).items():
            if "." in module:
                msg = (
                    f"{cls.__name__}.requirements[{distribution!r}] must name a top-level "
                    f"module, got {module!r}"
                )
                raise ValueError(msg)

    def _importable(self, module: str) -> bool:
        """Tell whether ``module`` can be found without importing it; a failure is logged."""
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ValueError) as error:
            logger.warning(
                "cannot find module %s of tool %s, treating it as unavailable: %s",
                module,
                self.tool,
                error,
            )
            return False

    def _missing(self) -> list[str]:
        """Return the required distributions whose module cannot be found."""
        return [
            distribution
            for distribution, module in self.requirements.items()
            if not self._importable(module)
        ]

    def available(self) -> bool:
        """Tell whether every required module can be found (nothing is imported)."""
        return not self._missing()

    def require_available(self) -> None:
        """Raise ``tool_unavailable`` unless :meth:`available`; logs a ``WARNING`` (ch. 8.14).

        Raises:
            FormulaError: Category ``tool_unavailable`` naming the missing distributions.
        """
        missing = self._missing()
        if not missing:
            return
        logger.warning("tool %s is unavailable, missing: %s", self.tool, ", ".join(missing))
        raise FormulaError(
            ErrorCategory.TOOL_UNAVAILABLE,
            "tool_unavailable",
            f"the tool {self.tool} is not available in this installation",
            f"install: {', '.join(missing)}",
            detail={"tool": self.tool, "missing": list(missing)},
        )

    def settings(self) -> dict[str, JsonValue]:
        """Return the solver settings this adapter fixes (``Provenance.solver_settings``, ch. 8.4).

        Returns:
            Name -> value; empty if the adapter has no setting that changes a value.
        """
        return {}

    def tool_versions(self) -> dict[str, str]:
        """Return the installed version per required distribution (provenance, cache key).

        A tool that cannot run has no version (ch. 8.4): while :meth:`available` is false the
        result is empty, even if one of its distributions is installed. A distribution that is
        not installed is omitted. The versions are read once and then kept; treat the result as
        read-only.

        Returns:
            Distribution name -> version, e.g. ``{"aerosandbox": "4.2.8"}``.
        """
        if not self.available():
            return {}
        if self._versions is None:
            versions: dict[str, str] = {}
            for distribution in self.requirements:
                try:
                    versions[distribution] = importlib.metadata.version(distribution)
                except importlib.metadata.PackageNotFoundError:
                    continue
            self._versions = versions
        return self._versions
