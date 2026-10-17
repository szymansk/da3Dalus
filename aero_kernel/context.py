"""What the engine hands a formula (ARCHITECTURE ch. 8.12).

``Inputs`` is the ``x`` of a formula, ``Context`` its ``ctx``. Nothing else reaches a formula: no
cache, no request, no global.
"""

from collections.abc import Mapping

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning
from pydantic import JsonValue

__all__ = ["Context", "Inputs", "Value"]

# The values that flow between nodes: a scalar in the canon unit of its quantity, or the geometry.
# A new quantity type adds its class here when the first formula needs it (ch. 8.12).
Value = float | AirplaneGeometry

# ``x`` of a formula: value per canon parameter name; ``None`` only for an absent ``optional`` input.
Inputs = Mapping[str, Value | None]


class Context:
    """The context of one formula call.

    Attributes:
        world: The method world of this call; ``None`` while no formula has worlds.
    """

    def __init__(self, *, origin: str, world: str | None = None) -> None:
        """Create the context of one node.

        Args:
            origin: Slug of the quantity that warnings of this call are reported against.
            world: The method world of this call, if any.
        """
        self.world = world
        self._origin = origin
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
        self._warnings.append(
            KernelWarning.of(code, message, origin=self._origin, world=None, detail=detail)
        )

    @property
    def warnings(self) -> tuple[KernelWarning, ...]:
        """The warnings reported so far, in order."""
        return tuple(self._warnings)
