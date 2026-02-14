import math
import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\- ]+$")
MAX_BANK_DEG = 85
MAX_ALPHA_DEG = 25
MAX_BETA_DEG = 30
MIN_ROLL_RATE_DPS = 10
MAX_ROLL_RATE_DPS = 600
DEFAULT_AGILE_ROLL_RATE_DPS = 240


class FlightProfileType(str, Enum):
    """Type of aircraft mission this profile targets."""

    trainer = "trainer"
    warbird = "warbird"
    fpv_cruiser = "fpv_cruiser"
    three_d = "3d"
    glider = "glider"
    motor_glider = "motor_glider"
    custom = "custom"


class StabilityPreference(str, Enum):
    """How naturally stable the aircraft should feel in flight."""

    stable = "stable"
    neutral = "neutral"
    agile = "agile"


class PitchResponse(str, Enum):
    """How quickly pitch control inputs should take effect."""

    smooth = "smooth"
    balanced = "balanced"
    snappy = "snappy"


class YawCouplingTolerance(str, Enum):
    """How much yaw-roll coupling is acceptable during maneuvers."""

    low = "low"
    medium = "medium"
    high = "high"


class Environment(BaseModel):
    """Outside conditions used to derive operating points."""

    model_config = ConfigDict(extra="forbid")

    altitude_m: float = Field(
        default=0,
        ge=-100,
        le=6000,
        description=(
            "Airfield altitude in meters above sea level. Typical values are 0 for sea-level fields "
            "or around 500 for inland clubs. This shifts density and therefore required lift settings."
        ),
    )
    wind_mps: float = Field(
        default=0,
        ge=0,
        le=25,
        description=(
            "Expected wind speed in meters per second. Typical values are 0 to 8 m/s. "
            "This helps pick conservative takeoff and approach operating points."
        ),
    )


class Goals(BaseModel):
    """Target performance goals used to build design and analysis targets."""

    model_config = ConfigDict(extra="forbid")

    cruise_speed_mps: float = Field(
        ...,
        gt=0,
        description=(
            "Desired cruise speed in meters per second. Typical trainer values are 15 to 22 m/s. "
            "This becomes the primary cruise operating-point target."
        ),
    )
    max_level_speed_mps: Optional[float] = Field(
        default=None,
        description=(
            "Maximum desired level-flight speed in meters per second. Typical values are 25 to 40 m/s. "
            "If set, it must be higher than cruise speed and guides top-speed checks."
        ),
    )
    min_speed_margin_vs_clean: float = Field(
        default=1.20,
        ge=1.05,
        le=1.60,
        description=(
            "Safety multiplier above clean-stall speed. Typical values are 1.15 to 1.30. "
            "Higher values produce safer low-speed targets."
        ),
    )
    takeoff_speed_margin_vs_to: float = Field(
        default=1.25,
        ge=1.05,
        le=1.80,
        description=(
            "Takeoff target as multiplier over estimated stall-in-takeoff-config speed. Typical values are 1.20 to 1.35. "
            "This sets safer launch operating points."
        ),
    )
    approach_speed_margin_vs_ldg: float = Field(
        default=1.30,
        ge=1.10,
        le=2.00,
        description=(
            "Approach speed as multiplier over landing-config stall speed. Typical values are 1.25 to 1.40. "
            "This directly shapes landing approach operating points."
        ),
    )
    target_turn_n: float = Field(
        default=2.0,
        ge=1.0,
        le=4.0,
        description=(
            "Target sustained turn load factor n (g-equivalent). Typical values are 1.5 to 2.5 for trainers. "
            "This drives turn-performance operating points."
        ),
    )
    loiter_s: Optional[int] = Field(
        default=None,
        ge=0,
        le=10800,
        description=(
            "Desired loiter duration in seconds. Typical values are 300 to 1200 s. "
            "Used for endurance-oriented operating-point goals."
        ),
    )

    @model_validator(mode="after")
    def validate_speed_relationship(self):
        if self.max_level_speed_mps is not None and self.max_level_speed_mps <= self.cruise_speed_mps:
            raise ValueError("max_level_speed_mps must be greater than cruise_speed_mps.")
        return self


class Handling(BaseModel):
    """Pilot feel and handling-quality preferences."""

    model_config = ConfigDict(extra="forbid")

    stability_preference: StabilityPreference = Field(
        default=StabilityPreference.stable,
        description=(
            "Preferred stability feel. stable is easiest for beginners, neutral is balanced, agile is very responsive. "
            "This biases control and stability targets."
        ),
    )
    roll_rate_target_dps: Optional[float] = Field(
        default=None,
        ge=MIN_ROLL_RATE_DPS,
        le=MAX_ROLL_RATE_DPS,
        description=(
            "Desired roll rate in degrees per second. Typical values are 90 to 180 deg/s for trainers. "
            "This informs roll control authority targets."
        ),
    )
    pitch_response: PitchResponse = Field(
        default=PitchResponse.smooth,
        description=(
            "Pitch response character. smooth is beginner-friendly, balanced is neutral, snappy is quick. "
            "This influences pitch damping and control goals."
        ),
    )
    yaw_coupling_tolerance: YawCouplingTolerance = Field(
        default=YawCouplingTolerance.low,
        description=(
            "Allowed yaw coupling during roll and turns. low means coordinated feel is important. "
            "This impacts acceptable lateral-directional behavior in derived points."
        ),
    )

    @model_validator(mode="after")
    def apply_agile_default_roll_rate(self):
        if self.stability_preference == StabilityPreference.agile and self.roll_rate_target_dps is None:
            self.roll_rate_target_dps = DEFAULT_AGILE_ROLL_RATE_DPS
        return self


class Constraints(BaseModel):
    """Hard limits that generated operating points must respect."""

    model_config = ConfigDict(extra="forbid")

    max_bank_deg: float = Field(
        default=60,
        ge=0,
        le=MAX_BANK_DEG,
        description=(
            "Maximum allowed bank angle in degrees. Typical values are 45 to 60 deg. "
            "This limits achievable turn load factor in generated scenarios."
        ),
    )
    max_alpha_deg: Optional[float] = Field(
        default=None,
        ge=0,
        le=MAX_ALPHA_DEG,
        description=(
            "Maximum allowed angle of attack in degrees. Typical values are 10 to 16 deg. "
            "This caps stall-proximity operating points."
        ),
    )
    max_beta_deg: Optional[float] = Field(
        default=None,
        ge=0,
        le=MAX_BETA_DEG,
        description=(
            "Maximum allowed sideslip angle in degrees. Typical values are 3 to 10 deg. "
            "This limits crosswind and yawed-condition operating points."
        ),
    )


class RCFlightProfileCreate(BaseModel):
    """Create payload for an RC Flight Profile intent."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description=(
            "Human-readable profile name. Example: 'rc_trainer_balanced'. "
            "This is unique and helps users choose profile intent quickly."
        ),
    )
    type: FlightProfileType = Field(
        ...,
        description=(
            "Profile category such as trainer or glider. Example: trainer. "
            "Used to filter profiles and seed design assumptions."
        ),
    )
    environment: Environment = Field(
        default_factory=Environment,
        description="Environment assumptions in SI units used for deriving operating points.",
    )
    goals: Goals = Field(
        ...,
        description="Performance goals that the generated operating points should satisfy.",
    )
    handling: Handling = Field(
        default_factory=Handling,
        description="Handling preference targets describing pilot feel and response characteristics.",
    )
    constraints: Constraints = Field(
        default_factory=Constraints,
        description="Hard operational limits that generated points must not exceed.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        if value is None:
            return value
        trimmed = value.strip()
        if trimmed != value:
            raise ValueError("name must not have leading or trailing spaces.")
        if not _NAME_PATTERN.fullmatch(trimmed):
            raise ValueError("name may only contain letters, numbers, spaces, '_' and '-'.")
        return trimmed

    @model_validator(mode="after")
    def validate_turn_load_vs_bank(self):
        phi_rad = math.radians(self.constraints.max_bank_deg)
        max_n = (1 / math.cos(phi_rad)) if self.constraints.max_bank_deg < 90 else float("inf")
        if self.goals.target_turn_n > max_n + 0.05:
            raise ValueError(
                "target_turn_n is greater than what is achievable with max_bank_deg. "
                "Increase max_bank_deg or decrease target_turn_n."
            )
        return self


class EnvironmentUpdate(BaseModel):
    """Patch payload for environment settings."""

    model_config = ConfigDict(extra="forbid")

    altitude_m: Optional[float] = Field(default=None, ge=-100, le=6000)
    wind_mps: Optional[float] = Field(default=None, ge=0, le=25)


class GoalsUpdate(BaseModel):
    """Patch payload for goal settings."""

    model_config = ConfigDict(extra="forbid")

    cruise_speed_mps: Optional[float] = Field(default=None, gt=0)
    max_level_speed_mps: Optional[float] = Field(default=None)
    min_speed_margin_vs_clean: Optional[float] = Field(default=None, ge=1.05, le=1.60)
    takeoff_speed_margin_vs_to: Optional[float] = Field(default=None, ge=1.05, le=1.80)
    approach_speed_margin_vs_ldg: Optional[float] = Field(default=None, ge=1.10, le=2.00)
    target_turn_n: Optional[float] = Field(default=None, ge=1.0, le=4.0)
    loiter_s: Optional[int] = Field(default=None, ge=0, le=10800)


class HandlingUpdate(BaseModel):
    """Patch payload for handling settings."""

    model_config = ConfigDict(extra="forbid")

    stability_preference: Optional[StabilityPreference] = None
    roll_rate_target_dps: Optional[float] = Field(
        default=None,
        ge=MIN_ROLL_RATE_DPS,
        le=MAX_ROLL_RATE_DPS,
    )
    pitch_response: Optional[PitchResponse] = None
    yaw_coupling_tolerance: Optional[YawCouplingTolerance] = None


class ConstraintsUpdate(BaseModel):
    """Patch payload for constraint settings."""

    model_config = ConfigDict(extra="forbid")

    max_bank_deg: Optional[float] = Field(default=None, ge=0, le=MAX_BANK_DEG)
    max_alpha_deg: Optional[float] = Field(default=None, ge=0, le=MAX_ALPHA_DEG)
    max_beta_deg: Optional[float] = Field(default=None, ge=0, le=MAX_BETA_DEG)


class RCFlightProfileUpdate(BaseModel):
    """Partial update payload. Only provided fields are changed."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=3, max_length=64)
    type: Optional[FlightProfileType] = None
    environment: Optional[EnvironmentUpdate] = None
    goals: Optional[GoalsUpdate] = None
    handling: Optional[HandlingUpdate] = None
    constraints: Optional[ConstraintsUpdate] = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_optional_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        trimmed = value.strip()
        if trimmed != value:
            raise ValueError("name must not have leading or trailing spaces.")
        if not _NAME_PATTERN.fullmatch(trimmed):
            raise ValueError("name may only contain letters, numbers, spaces, '_' and '-'.")
        return trimmed


class RCFlightProfileRead(BaseModel):
    """Response model for RC flight profiles."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    name: str
    type: FlightProfileType
    environment: Environment
    goals: Goals
    handling: Handling
    constraints: Constraints
    created_at: datetime
    updated_at: datetime


class AircraftFlightProfileAssignmentRead(BaseModel):
    """Minimal assignment response after linking profile to aircraft."""

    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    flight_profile_id: Optional[int]
