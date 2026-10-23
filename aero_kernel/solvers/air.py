"""The air a solver evaluates in (ARCHITECTURE ch. 8.8)."""

import math
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

__all__ = ["AirState", "FixedAtmosphere"]


def _positive_finite(value: float) -> float:
    """Require a finite number greater than 0."""
    if not math.isfinite(value) or value <= 0.0:
        msg = f"must be a finite number > 0, got {value}"
        raise ValueError(msg)
    return value


PositiveFloat = Annotated[float, AfterValidator(_positive_finite)]


class AirState(BaseModel):
    """Density, viscosity and speed of sound of the air an aircraft is evaluated in.

    Attributes:
        density: Air density in kg/m^3.
        dynamic_viscosity: Dynamic viscosity in Pa s.
        speed_of_sound: Speed of sound in m/s.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    density: PositiveFloat
    dynamic_viscosity: PositiveFloat
    speed_of_sound: PositiveFloat

    @property
    def kinematic_viscosity(self) -> float:
        """Kinematic viscosity in m^2/s."""
        return self.dynamic_viscosity / self.density


# Ideal-gas constants of air, as AeroSandbox uses them (aerosandbox.atmosphere): the temperature and
# pressure a fixed state implies; AeroBuildup asks only for density, viscosity and speed of sound.
_GAS_CONSTANT = 287.0500676  # J/(kg K)
_GAMMA = 1.4


class FixedAtmosphere:
    """A duck-typed ``asb.Atmosphere`` for one :class:`AirState`.

    AeroSandbox evaluates its models in whatever atmosphere object it is given; this one answers
    the methods it calls from a fixed state, so a solver can run in the air the kernel computed
    (an ISA state at the altitude, ch. 8.8) without a second atmosphere model.
    """

    def __init__(self, air: AirState) -> None:
        """Create the atmosphere.

        Args:
            air: The fixed state.
        """
        self._air = air

    def density(self) -> float:
        """Density in kg/m^3."""
        return self._air.density

    def dynamic_viscosity(self) -> float:
        """Dynamic viscosity in Pa s."""
        return self._air.dynamic_viscosity

    def speed_of_sound(self) -> float:
        """Speed of sound in m/s."""
        return self._air.speed_of_sound

    def ratio_of_specific_heats(self) -> float:
        """Ratio of specific heats of air."""
        return _GAMMA

    def temperature(self) -> float:
        """Temperature in K implied by the speed of sound."""
        return self._air.speed_of_sound**2 / (_GAMMA * _GAS_CONSTANT)

    def pressure(self) -> float:
        """Pressure in Pa implied by density and temperature."""
        return self._air.density * _GAS_CONSTANT * self.temperature()
