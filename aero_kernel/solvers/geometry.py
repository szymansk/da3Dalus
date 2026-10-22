"""The GEO adapter: the AeroSandbox airplane of a geometry document (ARCHITECTURE ch. 8.8).

The conversion itself is :func:`aero_kernel.solvers.asb_airplane.to_asb_airplane`, the only one
(ADR 0022); this adapter owns the capability check and the off-loop import of AeroSandbox.
"""

import asyncio
import importlib
import logging
from collections.abc import Mapping
from typing import Any, ClassVar

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.base import SolverAdapter

logger = logging.getLogger(__name__)

__all__ = ["GeometryAdapter"]


class GeometryAdapter(SolverAdapter):
    """Evaluates the geometry of an airplane with AeroSandbox.

    Attributes:
        tool: ``GEO``.
        requirements: AeroSandbox, imported lazily so a missing install is ``tool_unavailable``.
    """

    tool: ClassVar[str] = "GEO"
    requirements: ClassVar[Mapping[str, str]] = {"aerosandbox": "aerosandbox"}

    async def asb_airplane(self, airplane: AirplaneGeometry) -> Any:  # noqa: ANN401  # untyped aerosandbox boundary
        """Return the ``asb.Airplane`` of a geometry document.

        The conversion is closed-form and runs inline on the event loop; only the first import of
        aerosandbox, which is slow, runs in a worker thread (ch. 8.10).

        Args:
            airplane: The parsed geometry document.

        Returns:
            The ``asb.Airplane``.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing.
        """
        self.require_available()
        await asyncio.to_thread(importlib.import_module, "aerosandbox")
        return to_asb_airplane(airplane)
