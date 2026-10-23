"""What the engine hands a formula (ARCHITECTURE ch. 8.12).

``Inputs`` is the ``x`` of a formula, ``Context`` its ``ctx``. Nothing else reaches a formula: no
cache, no request, no global.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.opti import OptiAdapter
from pydantic import JsonValue

__all__ = ["Context", "Inputs", "Solvers", "Value"]

# The values that flow between nodes: a scalar in the canon unit of its quantity, or the geometry.
# A new quantity type adds its class here when the first formula needs it (ch. 8.12).
Value = float | AirplaneGeometry

# ``x`` of a formula: value per canon parameter name; ``None`` only for an absent ``optional`` input.
Inputs = Mapping[str, Value | None]


# Canon tool codes of formulas that call no adapter: pure relations and plain input reads (ch. 8.8).
_PURE_TOOLS = frozenset({"APP", "GEO", "KAT", "APC"})


@dataclass(frozen=True)
class Solvers:
    """The solver adapters a formula may use (ch. 8.8); one attribute per adapter.

    A frozen dataclass rather than a Pydantic model: it holds adapters, which are code. An
    adapter is added with the first formula that needs it (ADR 0021).

    Attributes:
        atmosphere: The ATM adapter (exact ISA density).
        opti: The OPT adapter (the stall problem, IPOPT over AeroBuildup).
    """

    atmosphere: AtmosphereAdapter
    opti: OptiAdapter

    def settings_of(self, tool: str) -> dict[str, JsonValue]:
        """Return the solver settings of the adapter of a canon tool code (``solver_settings``).

        Args:
            tool: The canon tool code of a formula, e.g. ``OPT``.

        Returns:
            Name -> value; empty for a tool whose adapter fixes no setting, and for a pure tool.
        """
        for adapter in (self.atmosphere, self.opti):
            if tool == adapter.tool:
                return adapter.settings()
        return {}

    def tool_versions_of(self, tool: str) -> dict[str, str]:
        """Return the installed versions of the distributions a canon tool code relies on.

        Feeds ``Provenance.tool_versions`` and the cache key (ch. 8.4). A plain read or a pure
        formula (``APP``, ``GEO``, ``KAT``, ``APC``) uses no tool and has none.

        Args:
            tool: The canon tool code of a formula, e.g. ``ATM``.

        Returns:
            Distribution name -> version; empty for a pure tool.

        Raises:
            ValueError: If the tool needs an adapter that does not exist yet; an empty answer
                there would claim a version-free result (ADR 0020).
        """
        if tool in _PURE_TOOLS:
            return {}
        for adapter in (self.atmosphere, self.opti):
            if tool == adapter.tool:
                return dict(adapter.tool_versions())
        msg = f"no solver adapter for the tool {tool}"
        raise ValueError(msg)


class Context:
    """The context of one formula call."""

    def __init__(self, *, origin: str, solvers: Solvers, world: str | None = None) -> None:
        """Create the context of one node.

        Args:
            origin: Slug of the quantity that warnings of this call are reported against.
            solvers: The solver adapters of the call.
            world: The method world this formula runs in, for a formula with worlds (ch. 8.13).
        """
        self._origin = origin
        self.solvers = solvers
        self.world = world
        self._warnings: list[KernelWarning] = []

    def warn(self, code: str, message: str, detail: dict[str, JsonValue] | None = None) -> None:
        """Report a value with a caveat; the severity follows from the closed warning table.

        Args:
            code: Code from the warning catalogue.
            message: The caveat, in natural language.
            detail: Structured values the warning carries.

        Raises:
            ValueError: If the code is not in the catalogue (the engine reports it as ``internal``).
        """
        self._warnings.append(KernelWarning.of(code, message, origin=self._origin, detail=detail))

    @property
    def warnings(self) -> tuple[KernelWarning, ...]:
        """The warnings reported so far, in order."""
        return tuple(self._warnings)
