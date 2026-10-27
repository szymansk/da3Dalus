"""The GEO adapter: the planform values of the wings, as AeroSandbox measures them.

Implements the tool behind the canon formula ``airplane-geometry`` (ARCHITECTURE ch. 8.8). The
measurement itself is :func:`aero_kernel.solvers.asb_airplane.main_wing_properties`, shared with the
other adapters that convert the geometry (one authority, ADR 0022).
"""

import asyncio
import importlib
import logging
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties, SurfaceProperties
from aero_kernel.solvers.asb_airplane import (
    fin_area,
    main_wing_properties,
    quarter_chord_mac_x,
    surface_properties,
)
from aero_kernel.solvers.base import SolverAdapter

logger = logging.getLogger(__name__)

__all__ = ["GeometryAdapter"]


class GeometryAdapter(SolverAdapter):
    """``S_ref``, ``b_ref`` and ``c_MAC`` of the main wing.

    Attributes:
        tool: ``GEO``.
        requirements: AeroSandbox, imported lazily so a missing install is ``tool_unavailable``.
    """

    tool: ClassVar[str] = "GEO"
    requirements: ClassVar[Mapping[str, str]] = {"aerosandbox": "aerosandbox"}

    async def main_wing_reference(self, airplane: AirplaneGeometry) -> MainWingProperties:
        """Return AeroSandbox's reference values of the wing with ``surface_type`` ``main_wing``.

        Building the wing is cheap and runs inline on the event loop; only the first import of
        aerosandbox, which is slow, runs in a worker thread (ch. 8.10).

        Args:
            airplane: The validated geometry document, which has exactly one main wing.

        Returns:
            The reference area, span and mean aerodynamic chord in m^2, m and m.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing;
                ``unsupported_configuration`` for a main wing without a planform or one whose
                sections fold back along y.
            ValueError: If the document does not have exactly one main wing.
        """
        self.require_available()
        await asyncio.to_thread(importlib.import_module, "aerosandbox")
        reference = main_wing_properties(airplane)
        logger.debug("main wing reference of %s: %s", airplane.name, reference)
        return reference

    async def surface_reference(self, airplane: AirplaneGeometry, key: str) -> SurfaceProperties:
        """Return AeroSandbox's planform values of one wing, for the neutral point's surface terms.

        Args:
            airplane: The validated geometry document.
            key: The key of the wing in ``airplane.wings``.

        Returns:
            Area, span, aspect ratio, MAC and the MAC's leading edge in m^2, m, 1, m, m.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing;
                ``unsupported_configuration`` for a wing without a planform or one whose
                sections fold back along y.
        """
        self.require_available()
        await asyncio.to_thread(importlib.import_module, "aerosandbox")
        return surface_properties(airplane, key)

    async def quarter_chord_mac_x(self, airplane: AirplaneGeometry, key: str) -> float:
        """Return x of the quarter-chord MAC of one wing, for the tail arms from the design CG.

        Args:
            airplane: The validated geometry document.
            key: The key of the wing in ``airplane.wings``.

        Returns:
            ``Wing.aerodynamic_center(chord_fraction=0.25)[0]`` in m, geometry frame, aft positive.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing;
                ``unsupported_configuration`` for a wing without an aerodynamic centre.
        """
        self.require_available()
        await asyncio.to_thread(importlib.import_module, "aerosandbox")
        return quarter_chord_mac_x(airplane, key)

    async def fin_area(self, airplane: AirplaneGeometry, key: str) -> float:
        """Return the fin area of one wing, for the vertical tail volume.

        Args:
            airplane: The validated geometry document.
            key: The key of the one ``vertical_tail`` or ``v_tail`` wing in ``airplane.wings``.

        Returns:
            ``Wing.area(type="planform", include_centerline_distance=False)`` in m^2; a V-tail's
            fin share, the panel areas times ``sin^2`` of the panel angle.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing;
                ``unsupported_configuration`` for a surface with no planform.
        """
        self.require_available()
        await asyncio.to_thread(importlib.import_module, "aerosandbox")
        return fin_area(airplane, key)
