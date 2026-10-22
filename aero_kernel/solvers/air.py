"""The air a solver evaluates in (ARCHITECTURE ch. 8.8)."""

import math
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

__all__ = ["AirState"]


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
