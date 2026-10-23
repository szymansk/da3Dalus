"""The AVL adapter: the neutral point of an airplane from the vortex lattice (ARCHITECTURE ch. 8.8).

The interface the ``neutral-point`` formula is written against. Tool validity warnings belong to the
adapter (mesh convergence), and it adds no regime warning of its own: those come with the minimum-drag
speed and are inherited (#1203, M2).
"""

import logging
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.base import SolverAdapter
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["AvlAdapter", "AvlNeutralPoint"]


class AvlNeutralPoint(BaseModel):
    """The neutral point AVL found, and the caveats of the run.

    Attributes:
        x_np: x of the neutral point in m, in the geometry frame (aft positive).
        warnings: Tool validity warnings (mesh convergence), without origin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x_np: float
    warnings: tuple[KernelWarning, ...] = ()


class AvlAdapter(SolverAdapter):
    """AVL as a subprocess in the runtime.

    Attributes:
        tool: ``AVL``.
        requirements: The AVL binary and AeroSandbox (the thickness of the sections).
    """

    tool: ClassVar[str] = "AVL"
    requirements: ClassVar[Mapping[str, str]] = {
        "avl-binary": "avl_binary",
        "aerosandbox": "aerosandbox",
    }

    async def neutral_point(self, airplane: AirplaneGeometry, cl: float) -> AvlNeutralPoint:
        """Find the neutral point of the airplane at a lift coefficient.

        Args:
            airplane: The validated geometry, devices at rest.
            cl: The lift coefficient of the operating point.

        Returns:
            The neutral point and the adapter's warnings.

        Raises:
            FormulaError: ``tool_unavailable`` if AVL is missing.
            NotImplementedError: Until the AVL run is built (the next step of #1203).
        """
        self.require_available()
        raise NotImplementedError(airplane, cl)
