"""Field length schemas — takeoff and landing field length response (gh-489)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TakeoffMode = Literal["runway", "hand_launch", "bungee", "catapult"]
LandingMode = Literal["runway", "belly_land"]


class FieldLengthRead(BaseModel):
    """Takeoff and landing field length results.

    Computed via Roskam Vol I §3.4 simplified ground-roll (energy method).
    """

    s_to_ground_m: float = Field(
        ..., description="Takeoff ground roll [m] (standstill to liftoff)"
    )
    s_to_50ft_m: float = Field(
        ..., description="Takeoff distance to clear 50-ft obstacle [m]"
    )
    s_ldg_ground_m: float = Field(
        ..., description="Landing ground roll [m] (touchdown to stop)"
    )
    s_ldg_50ft_m: float = Field(
        ..., description="Landing distance from 50-ft obstacle to stop [m]"
    )
    vto_obstacle_mps: float = Field(
        ..., description="V_LOF = 1.2·V_S — liftoff speed over obstacle [m/s]"
    )
    vapp_mps: float = Field(
        ..., description="V_app = 1.3·V_S — approach speed [m/s]"
    )
    mode_takeoff: TakeoffMode = Field(
        ..., description="Takeoff mode used for computation"
    )
    mode_landing: LandingMode = Field(
        ..., description="Landing mode used for computation"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (e.g. insufficient climb-out margin)",
    )
