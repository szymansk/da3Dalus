import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TrimTarget(str, Enum):
    """Aerodynamic parameters that AVL can target during trim."""

    CL = "C"
    CY = "S"
    PITCHING_MOMENT = "PM"
    ROLLING_MOMENT = "RM"
    YAWING_MOMENT = "YM"


KNOWN_STATE_VARIABLES = {"alpha", "beta", "roll_rate", "pitch_rate", "yaw_rate"}


class TrimConstraint(BaseModel):
    """A single trim constraint: adjust a variable to achieve a target."""

    variable: str = Field(
        ...,
        description="Run variable to adjust: 'alpha', 'beta', 'roll_rate', "
        "'pitch_rate', 'yaw_rate', or a control surface name like 'elevator'",
    )
    target: TrimTarget = Field(..., description="Aerodynamic parameter to target")
    value: float = Field(0.0, description="Target value (default: 0 = zero the parameter)")

    @field_validator("variable")
    @classmethod
    def validate_variable_format(cls, v: str) -> str:
        if v in KNOWN_STATE_VARIABLES:
            return v
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                f"Invalid variable name '{v}'. Must be a letter followed by "
                f"letters/digits/underscores, or one of: {sorted(KNOWN_STATE_VARIABLES)}"
            )
        return v


class AVLTrimRequest(BaseModel):
    """Request to run AVL trim analysis."""

    operating_point: "OperatingPointSchema" = Field(
        ..., description="Operating point for the trim analysis"
    )
    trim_constraints: list[TrimConstraint] = Field(
        ..., min_length=1, description="At least one trim constraint"
    )

    @model_validator(mode="after")
    def validate_constraints(self) -> "AVLTrimRequest":
        variables = [c.variable for c in self.trim_constraints]
        if len(variables) != len(set(variables)):
            dupes = [v for v in variables if variables.count(v) > 1]
            raise ValueError(f"Duplicate trim variables: {set(dupes)}")
        targets = [c.target for c in self.trim_constraints]
        if len(targets) != len(set(targets)):
            dupes = [t.name for t in targets if targets.count(t) > 1]
            raise ValueError(f"Duplicate trim targets: {set(dupes)}")
        op = self.operating_point
        if isinstance(getattr(op, "alpha", None), list):
            raise ValueError("Alpha must be a scalar float for trim analysis, not a list")
        return self


class AVLTrimResult(BaseModel):
    """Result of AVL trim analysis."""

    converged: bool = Field(..., description="Whether AVL successfully converged")
    trimmed_deflections: dict[str, float] = Field(
        default_factory=dict, description="Achieved control surface deflections (name -> degrees)"
    )
    trimmed_state: dict[str, float] = Field(
        default_factory=dict, description="Achieved state variables (alpha, beta, etc.)"
    )
    aero_coefficients: dict[str, float] = Field(
        default_factory=dict, description="Aerodynamic coefficients at trim (CL, CD, Cm, etc.)"
    )
    forces_and_moments: dict[str, float] = Field(
        default_factory=dict, description="Dimensional forces and moments"
    )
    stability_derivatives: dict[str, float] = Field(
        default_factory=dict, description="Stability derivatives at trim point"
    )
    raw_results: dict[str, float] = Field(
        default_factory=dict, description="Full parsed AVL output"
    )
    trim_enrichment: Optional["TrimEnrichment"] = Field(
        None, description="Enrichment data computed after trim"
    )


class AeroBuildupTrimRequest(BaseModel):
    """Request to run AeroBuildup trim analysis."""

    operating_point: "OperatingPointSchema" = Field(
        ..., description="Operating point for the trim analysis"
    )
    trim_variable: str = Field(
        "elevator",
        description="Control surface name to vary for trim (e.g. 'elevator')",
    )
    target_coefficient: str = Field(
        "Cm",
        description="Aerodynamic coefficient to target (one of: CL, CD, CY, Cm, Cl, Cn).",
    )
    target_value: float = Field(
        0.0,
        description="Target value for the coefficient (default: 0)",
    )
    deflection_bounds: list[float] = Field(
        default=[-25.0, 25.0],
        min_length=2,
        max_length=2,
        description="Search bounds for deflection in degrees [lower, upper]",
    )

    @field_validator("trim_variable")
    @classmethod
    def validate_trim_variable_format(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                f"Invalid trim variable name '{v}'. Must be a letter followed by "
                f"letters/digits/underscores."
            )
        return v

    @field_validator("target_coefficient")
    @classmethod
    def validate_target_coefficient(cls, v: str) -> str:
        allowed = {"CL", "CD", "CY", "Cm", "Cl", "Cn"}
        if v not in allowed:
            raise ValueError(f"Invalid target coefficient '{v}'. Must be one of: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_bounds_order(self) -> "AeroBuildupTrimRequest":
        if self.deflection_bounds[0] >= self.deflection_bounds[1]:
            raise ValueError("deflection_bounds[0] must be less than deflection_bounds[1]")
        op = self.operating_point
        if isinstance(getattr(op, "alpha", None), list):
            raise ValueError("Alpha must be a scalar float for trim analysis, not a list")
        return self


class AeroBuildupTrimResult(BaseModel):
    """Result of AeroBuildup trim analysis."""

    converged: bool = Field(..., description="Whether the root-finding converged")
    trim_variable: str = Field(..., description="Control surface that was varied")
    trimmed_deflection: float = Field(
        ..., description="Deflection angle that achieves trim (degrees)"
    )
    target_coefficient: str = Field(..., description="Coefficient that was targeted")
    achieved_value: Optional[float] = Field(
        ..., description="Achieved value of target coefficient at trim, or null if not converged"
    )
    aero_coefficients: dict[str, float] = Field(
        default_factory=dict,
        description="All aero coefficients at trim (CL, CD, Cm, etc.)",
    )
    stability_derivatives: dict[str, float] = Field(
        default_factory=dict, description="Stability derivatives at trim point"
    )
    trim_enrichment: Optional["TrimEnrichment"] = Field(
        None, description="Enrichment data computed after trim"
    )


class CdclConfig(BaseModel):
    """Configuration for NeuralFoil CDCL profile-drag computation."""

    alpha_start_deg: float = Field(
        -10.0, ge=-180.0, le=180.0, description="Start of alpha sweep in degrees"
    )
    alpha_end_deg: float = Field(
        16.0, ge=-180.0, le=180.0, description="End of alpha sweep in degrees"
    )
    alpha_step_deg: float = Field(1.0, gt=0.0, le=10.0, description="Alpha step size in degrees")
    model_size: str = Field("large", description="NeuralFoil model size")
    n_crit: float = Field(
        9.0, ge=0.0, le=20.0, description="Critical amplification ratio for transition"
    )
    xtr_upper: float = Field(
        1.0, ge=0.0, le=1.0, description="Upper surface forced transition location (0-1)"
    )
    xtr_lower: float = Field(
        1.0, ge=0.0, le=1.0, description="Lower surface forced transition location (0-1)"
    )
    include_360_deg_effects: bool = Field(
        False, description="Include 360-degree post-stall effects"
    )


class SpacingConfig(BaseModel):
    """Configuration for AVL panel spacing optimisation."""

    n_chord: int = Field(12, ge=4, le=100, description="Base chordwise panel count")
    c_space: float = Field(1.0, description="Chordwise spacing distribution (1=cosine)")
    n_span: int = Field(20, ge=4, le=200, description="Base spanwise panel count")
    s_space: float = Field(1.0, description="Spanwise spacing distribution (1=cosine)")
    auto_optimise: bool = Field(True, description="Apply intelligent spacing rules automatically")


# Schema für OperatingPointSet
class OperatingPointSetSchema(BaseModel):
    name: str
    description: str
    operating_points: list[int]

    model_config = ConfigDict(from_attributes=True)


class OperatingPointSchema(BaseModel):
    name: Optional[str] = Field(None, description="Name of the operating point")
    description: Optional[str] = Field(None, description="Description of the operating point")

    # Operating point parameters
    velocity: float = Field(10.0, description="Velocity in m/s")
    alpha: float | list[float] = Field(0.0, description="Angle of attack in degrees")
    beta: float = Field(0.0, description="Sideslip angle in degrees")
    p: float = Field(0.0, description="Roll rate in rad/s")
    q: float = Field(0.0, description="Pitch rate in rad/s")
    r: float = Field(0.0, description="Yaw rate in rad/s")

    xyz_ref: List[float] = Field(
        [0.0, 0.0, 0.0],
        description="default location in meters about which moments and rotation rates are defined (if doing trim calculations, xyz_ref must be the CG location)",
    )

    # Atmosphere parameters
    altitude: float = Field(0.0, description="Altitude in meters")

    # Optional NeuralFoil and spacing configurations
    cdcl_config: Optional[CdclConfig] = Field(None, description="NeuralFoil CDCL configuration")
    spacing_config: Optional[SpacingConfig] = Field(
        None, description="AVL panel spacing configuration"
    )

    control_deflections: dict[str, float] | None = Field(
        default=None,
        description="Runtime control surface deflections (name → degrees). "
        "Overrides geometry defaults for this operating point.",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "level_flight",
                "description": "Level flight at sea level",
                "velocity": 15.0,
                "alpha": [0.0],
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "altitude": 0.0,
                "xyz_ref": [0.0, 0.0, 0.0],
                "control_deflections": {"elevator": -2.0},
            }
        },
    )


class OperatingPointStatus(str, Enum):
    TRIMMED = "TRIMMED"
    NOT_TRIMMED = "NOT_TRIMMED"
    LIMIT_REACHED = "LIMIT_REACHED"
    DIRTY = "DIRTY"
    COMPUTING = "COMPUTING"


class StoredOperatingPointCreate(BaseModel):
    name: str
    description: str
    aircraft_id: Optional[int] = None
    config: str = Field(
        "clean", description="Aircraft configuration name, e.g. clean/takeoff/landing."
    )
    status: OperatingPointStatus = Field(OperatingPointStatus.NOT_TRIMMED)
    warnings: list[str] = Field(default_factory=list)
    controls: dict[str, float] = Field(
        default_factory=dict, description="Trim outputs such as throttle/elevator."
    )
    velocity: float = Field(..., description="Velocity in m/s")
    alpha: float = Field(..., description="Angle of attack in radians")
    beta: float = Field(..., description="Sideslip angle in radians")
    p: float = Field(..., description="Roll rate in rad/s")
    q: float = Field(..., description="Pitch rate in rad/s")
    r: float = Field(..., description="Yaw rate in rad/s")
    xyz_ref: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    altitude: float = Field(..., description="Altitude in meters")

    control_deflections: dict[str, float] | None = Field(
        default=None,
        description="Runtime control surface deflections (name → degrees). "
        "Overrides geometry defaults for this operating point.",
    )

    trim_enrichment: Optional["TrimEnrichment"] = Field(
        default=None,
        description="Enrichment data: analysis goal, deflection reserves, design warnings. "
        "Computed after trim solve.",
    )

    model_config = ConfigDict(from_attributes=True)


class StoredOperatingPointRead(StoredOperatingPointCreate):
    id: int


class OperatingPointDeflectionPatch(BaseModel):
    """Partial update: only control surface deflection overrides."""

    control_deflections: dict[str, float] | None = Field(
        ...,
        description="Runtime control surface deflections (name → degrees). "
        "Overrides geometry defaults for this operating point. "
        "Set to null to clear all overrides.",
    )

    @field_validator("control_deflections")
    @classmethod
    def validate_deflection_keys(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is None:
            return v
        for key in v:
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9_ -]*$", key):
                raise ValueError(
                    f"Invalid control surface name '{key}'. "
                    "Must start with a letter, followed by letters/digits/underscores/spaces/hyphens."
                )
        return v


class GenerateOperatingPointSetRequest(BaseModel):
    replace_existing: bool = Field(
        False,
        description="If true, delete existing operating points and sets for the aircraft before generating new ones.",
    )
    profile_id_override: Optional[int] = Field(
        default=None,
        description="Optional profile ID to use instead of the aircraft-assigned flight profile.",
    )


class TrimOperatingPointRequest(BaseModel):
    name: str = Field(
        "custom_trim_point",
        description="Name of the operating point to trim.",
    )
    config: str = Field(
        "clean",
        description="Aircraft configuration label, for example clean/takeoff/landing.",
    )
    velocity: float = Field(..., gt=0.0, description="Target velocity in m/s.")
    altitude: float = Field(0.0, description="Target altitude in meters.")
    beta_target_deg: float = Field(0.0, description="Target sideslip in degrees.")
    n_target: float = Field(1.0, gt=0.0, description="Target load factor n.")
    profile_id_override: Optional[int] = Field(
        default=None,
        description="Optional profile ID to use instead of the aircraft-assigned flight profile.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Optional custom warning tags to carry into the trim output.",
    )


class TrimmedOperatingPointRead(BaseModel):
    source_flight_profile_id: Optional[int] = None
    point: StoredOperatingPointCreate

    model_config = ConfigDict(from_attributes=True)


class GeneratedOperatingPointSetRead(BaseModel):
    id: int
    name: str
    description: str
    aircraft_id: Optional[int] = None
    source_flight_profile_id: Optional[int] = None
    operating_points: list[StoredOperatingPointRead]

    model_config = ConfigDict(from_attributes=True)


class DeflectionReserve(BaseModel):
    """Per-surface deflection usage at a trim point."""

    deflection_deg: float = Field(..., description="Actual deflection at trim (degrees)")
    max_pos_deg: float = Field(..., description="Mechanical limit in positive direction (degrees)")
    max_neg_deg: float = Field(..., description="Mechanical limit in negative direction (degrees)")
    usage_fraction: float = Field(
        ..., description="Fraction of available authority used (|defl| / limit), 0.0-1.0+"
    )


class DesignWarning(BaseModel):
    """A threshold-based design warning generated from trim results."""

    level: str = Field(
        ...,
        description="Severity: 'info', 'warning', or 'critical'",
        pattern="^(info|warning|critical)$",
    )
    category: str = Field(..., description="Warning category: 'authority', 'trim_quality', etc.")
    surface: Optional[str] = Field(None, description="Control surface name, if applicable")
    message: str = Field(..., description="Human-readable warning message")


class ControlEffectiveness(BaseModel):
    """Per-surface control effectiveness derivative at trim point."""

    derivative: float = Field(..., description="Control derivative (e.g. dCm/d-delta-e in 1/deg)")
    coefficient: str = Field(
        ..., description="Coefficient affected (Cm, Cl, Cn, CL)", pattern="^(Cm|Cl|Cn|CL)$"
    )
    surface: str = Field(..., description="Control surface name")


class StabilityClassification(BaseModel):
    """Static stability classification at a trim point."""

    is_statically_stable: bool = Field(..., description="Cm_alpha < 0")
    is_directionally_stable: bool = Field(..., description="Cn_beta > 0")
    is_laterally_stable: bool = Field(..., description="Cl_beta < 0")
    static_margin: Optional[float] = Field(
        None, description="Static margin = -Cm_a/CL_a (fraction of MAC)"
    )
    overall_class: str = Field(
        ...,
        description="'stable', 'neutral', or 'unstable'",
        pattern="^(stable|neutral|unstable)$",
    )


class MixerValues(BaseModel):
    """Symmetric/differential decomposition for dual-role surfaces."""

    symmetric_offset: float = Field(
        ..., description="Average deflection of paired surfaces (degrees)"
    )
    differential_throw: float = Field(
        ..., ge=0.0, description="Half-difference of paired surfaces (degrees)"
    )
    role: str = Field(
        ...,
        description="Dual-role type: elevon, flaperon, ruddervator",
        pattern="^(elevon|flaperon|ruddervator)$",
    )


class TrimEnrichment(BaseModel):
    """Enrichment data computed after a trim solve - stored as JSON on OperatingPointModel."""

    analysis_goal: str = Field(..., description="Human-readable design question this OP answers")
    trim_method: str = Field(
        ..., description="Solver used: 'opti', 'grid_search', 'avl', 'aerobuildup'"
    )
    trim_score: Optional[float] = Field(None, description="Trim quality score (lower = better)")
    trim_residuals: dict[str, float] = Field(
        default_factory=dict, description="Residual coefficients at trim (cm, cy, cl)"
    )
    deflection_reserves: dict[str, DeflectionReserve] = Field(
        default_factory=dict, description="Per-surface deflection reserve"
    )
    design_warnings: list[DesignWarning] = Field(
        default_factory=list, description="Threshold-based design warnings"
    )
    effectiveness: dict[str, ControlEffectiveness] = Field(
        default_factory=dict, description="Per-surface control effectiveness"
    )
    stability_classification: Optional[StabilityClassification] = Field(
        None, description="Stability classification at trim point"
    )
    mixer_values: dict[str, MixerValues] = Field(
        default_factory=dict, description="Dual-role surface decomposition"
    )
    result_summary: str = Field("", description="Human-readable trim result summary")


class AnalysisStatusResponse(BaseModel):
    op_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of operating points per status (TRIMMED, NOT_TRIMMED, DIRTY, COMPUTING, LIMIT_REACHED)",
    )
    total_ops: int = Field(0, description="Total number of operating points")
    retrim_active: bool = Field(False, description="Whether a background retrim job is running")
    retrim_debouncing: bool = Field(False, description="Whether a debounce timer is active")
    last_computation: Optional[datetime] = Field(
        None, description="Timestamp of last completed retrim"
    )


# Resolve forward references for TrimEnrichment used in earlier classes
AVLTrimResult.model_rebuild()
AeroBuildupTrimResult.model_rebuild()
StoredOperatingPointCreate.model_rebuild()
