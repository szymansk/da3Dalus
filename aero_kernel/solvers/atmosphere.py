"""The ATM adapter: the exact ISA air state (ARCHITECTURE ch. 8.8, K30 / O5).

The kernel has one ISA, ``asb.Atmosphere(altitude=h, method="isa")``; there is no hand-written
second one. Implements the tool behind the canon formula ``air-density-isa``.
"""

import asyncio
import importlib
import logging
from collections.abc import Mapping
from typing import ClassVar

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.base import SolverAdapter

logger = logging.getLogger(__name__)

__all__ = ["AtmosphereAdapter"]


class AtmosphereAdapter(SolverAdapter):
    """Air density of the exact International Standard Atmosphere.

    Attributes:
        tool: ``ATM``.
        requirements: AeroSandbox, imported lazily so a missing install is ``tool_unavailable``.
    """

    tool: ClassVar[str] = "ATM"
    requirements: ClassVar[Mapping[str, str]] = {"aerosandbox": "aerosandbox"}

    async def state(self, altitude_m: float) -> AirState:
        """Return the ISA air state at a geopotential altitude.

        The lookup is closed-form and runs inline on the event loop, not in the pool; only the
        first import of aerosandbox, which is slow, runs in a worker thread (ch. 8.10).
        Finiteness of the altitude is the input validation's.

        Args:
            altitude_m: Altitude above mean sea level in metres.

        Returns:
            Density in kg/m^3, dynamic viscosity in Pa s and speed of sound in m/s.

        Raises:
            FormulaError: ``tool_unavailable`` if AeroSandbox is missing; ``invalid_input``
                (parameter ``h``) if the altitude is outside the range of AeroSandbox's ISA.
        """
        self.require_available()
        # Lazy and off the loop: the first import of aerosandbox takes about 0.8 s (ch. 8.10).
        asb = await asyncio.to_thread(importlib.import_module, "aerosandbox")
        atmosphere = asb.Atmosphere(altitude=altitude_m, method="isa")
        # AeroSandbox keeps its validity range in a private attribute; it is the tool's own
        # statement of where the ISA model holds, so it is read rather than copied here.
        low, high = atmosphere._valid_altitude_range  # pyright: ignore[reportPrivateUsage]
        if not low <= altitude_m <= high:
            raise FormulaError(
                ErrorCategory.INVALID_INPUT,
                "invalid_input",
                f"altitude {altitude_m} m is outside the ISA range {low}..{high} m",
                f"give an altitude between {low} m and {high} m",
                detail={"altitude_m": altitude_m, "valid_range_m": [low, high]},
                parameter="h",
            )
        air = AirState(
            density=float(atmosphere.density()),  # pyright: ignore[reportUnknownArgumentType]  # untyped ASB
            dynamic_viscosity=float(atmosphere.dynamic_viscosity()),  # pyright: ignore[reportUnknownArgumentType]
            speed_of_sound=float(atmosphere.speed_of_sound()),  # pyright: ignore[reportUnknownArgumentType]
        )
        logger.debug("isa state at %s m: %s", altitude_m, air)
        return air
