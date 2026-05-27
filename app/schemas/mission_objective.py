"""Mission-Objective + Mission-Preset Pydantic schemas (gh-546)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.mission_kpi import AxisName

RunwayType = Literal["grass", "asphalt", "belly"]
TakeoffMode = Literal["runway", "hand_launch", "bungee", "catapult"]

# gh-477: surface taxonomy for landing-field-length computation. μ_eff
# lookup lives in assumption_compute_service.LANDING_SURFACE_MU. The
# six surfaces span the realistic RC / UAV operations envelope; brake-
# equipped paved is out of scope until a per-aircraft brake flag exists
# (see "Out of Scope" on gh-477).
LandingSurface = Literal[
    "grass_short",
    "grass_long",
    "hard_paved",
    "soft_soil",
    "belly_grass",
    "net_recovery",
]


class MissionObjective(BaseModel):
    """User-set mission targets + field-performance inputs for one aeroplane."""

    mission_type: str = Field(..., description="FK to MissionPreset.id")

    # Performance targets (one per spider axis except W/S which is computed)
    target_cruise_mps: float = Field(..., ge=0)
    target_stall_safety: float = Field(..., ge=1.0, description="V_cruise / V_s1")
    target_maneuver_n: float = Field(..., ge=1.0, description="Load factor [g]")
    target_glide_ld: float = Field(..., ge=0, description="L/D target")
    target_climb_energy: float = Field(..., ge=0, description="C_L^1.5/CD")
    target_wing_loading_n_m2: float = Field(..., ge=0)
    target_field_length_m: float = Field(..., ge=0)

    # Field Performance inputs (migrated from Assumptions)
    available_runway_m: float = Field(..., ge=0)
    runway_type: RunwayType
    t_static_N: float = Field(..., ge=0, description="Static thrust at V=0")
    takeoff_mode: TakeoffMode

    # gh-477: landing-field-length inputs. All optional — the service
    # falls back to grass-short / safety=1.5 / no length check when
    # absent.
    landing_surface: Optional[LandingSurface] = Field(
        None,
        description="Expected landing surface — drives μ_eff for s_ground",
    )
    landing_safety_factor: Optional[float] = Field(
        None,
        ge=1.0,
        le=3.0,
        description="Multiplier applied to (s_flare + s_ground). Typical 1.5–2.0.",
    )
    available_field_length_m: Optional[float] = Field(
        None,
        ge=0,
        description="Length of the planned landing field (meters) — sizing check input.",
    )


class MissionPresetEstimates(BaseModel):
    """Default DesignAssumption estimate_values applied when this mission is selected."""

    g_limit: float
    target_static_margin: float
    cl_max: float
    power_to_weight: float
    prop_efficiency: float


class MissionPreset(BaseModel):
    """One mission preset row (Trainer, Sport, Sailplane, …)."""

    id: str = Field(..., description="Stable preset id, e.g. 'trainer'")
    label: str
    description: str
    target_polygon: dict[AxisName, float] = Field(
        ..., description="Soll polygon scores 0..1 for the 7 axes"
    )
    axis_ranges: dict[AxisName, tuple[float, float]] = Field(
        ..., description="Mission-relative (min, max) for axis normalisation"
    )
    suggested_estimates: MissionPresetEstimates
