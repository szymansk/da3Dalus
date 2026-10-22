"""The GEO adapter: the AeroSandbox airplane of a geometry document (ARCHITECTURE ch. 8.8).

The conversion itself is :func:`aero_kernel.solvers.asb_airplane.to_asb_airplane`, the only one
(ADR 0022); this adapter owns the capability check and the off-loop import of AeroSandbox.
"""

import asyncio
import importlib
import logging
from collections.abc import Mapping
from typing import Any, ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.base import SolverAdapter
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["GeometryAdapter", "MainWingProperties"]


class MainWingProperties(BaseModel):
    """The reference values of the main wing, projected onto the x-y plane.

    Attributes:
        s_ref: Reference area in m^2 (canon quantity ``wing-reference-area``).
        b_ref: Reference span in m (``wing-span``).
        c_mac: Mean aerodynamic chord in m (``mean-aerodynamic-chord``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    s_ref: float
    b_ref: float
    c_mac: float


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

    async def main_wing_properties(self, airplane: AirplaneGeometry) -> MainWingProperties:
        """Return ``S_ref``, ``b_ref`` and ``c_MAC`` of the one wing with ``surface_type`` ``main_wing``.

        This is the single place that fixes the definition (maintainer, 2026-10-22): the reference
        planform is the sections' chords and leading edges as given, **projected onto the x-y
        plane**, panel by panel (so a polyhedral wing works). Twist does not change it.

        AeroSandbox's ``Wing.area("projected")`` and ``Wing.span("y")`` are not used: they measure
        along the quarter-chord line, whose y depends on twist (BRYAN: S_ref -0.05 %), and
        ``Wing.mean_aerodynamic_chord()`` weights panels by their slant area. The kernel integrates
        the sections itself. For the stored side, per panel with ``dy = |y2 - y1|``:

        - area ``dy (c1 + c2) / 2``, span ``dy``, ``integral c^2 dy = dy (c1^2 + c1 c2 + c2^2) / 3``;
        - ``S_ref`` and ``b_ref`` are the sums, doubled if the wing is mirrored;
        - ``c_MAC = (2/S_ref) * integral(c^2 dy)`` over the half wing, which is the integral over
          the stored side divided by the stored side's area (mirrored or not).

        No external tool is called, so this needs no AeroSandbox.

        Args:
            airplane: The parsed geometry document.

        Returns:
            The three reference values in m^2, m and m.

        Raises:
            FormulaError: ``invalid_input`` (``main_wing_count``) unless exactly one wing is a
                ``main_wing``; ``unsupported_configuration`` if the main wing has no projected
                area (all its sections at one y).
        """
        wings = airplane.wings or {}
        main = [wing for wing in wings.values() if wing.surface_type == "main_wing"]
        if len(main) != 1:
            raise FormulaError(
                ErrorCategory.INVALID_INPUT,
                "main_wing_count",
                f"the airplane has {len(main)} wings with surface_type main_wing; it needs exactly one",
                "mark exactly one wing as main_wing",
                detail={"count": len(main)},
                parameter="airplane",
            )
        wing = main[0]
        area = span = squares = 0.0
        for inner, outer in zip(wing.x_secs[:-1], wing.x_secs[1:], strict=True):
            dy = abs(outer.xyz_le[1] - inner.xyz_le[1])
            c1, c2 = inner.chord, outer.chord
            area += dy * (c1 + c2) / 2.0
            span += dy
            squares += dy * (c1 * c1 + c1 * c2 + c2 * c2) / 3.0
        if not area > 0.0:
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "unsupported_configuration",
                f"the main wing {wing.name!r} has no area projected onto the x-y plane",
                "a main wing needs sections at different y; a vertical surface is no main wing",
                detail={"wing": wing.name},
                parameter="airplane",
            )
        mirrored = 2.0 if wing.symmetric else 1.0
        return MainWingProperties(
            s_ref=mirrored * area, b_ref=mirrored * span, c_mac=squares / area
        )
