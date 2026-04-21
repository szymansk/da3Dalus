from typing import Literal, Optional, OrderedDict

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.schemas.Servo import Servo

SparMode = Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"]
HingeType = Literal["middle", "top", "top_simple", "round_inside", "round_outside"]
WingXSecType = Literal["root", "segment", "tip"]
TipType = Literal["flat", "round"]


class AeroplaneSchema(BaseModel):
    name: str = Field(..., description="Aeroplane name", examples=["Vanilla"])
    total_mass_kg: Optional[float] = Field(None, description="Total mass of the aeroplane in kg", examples=[3.0])
    wings: Optional[OrderedDict[str, "AsbWingSchema"]] = Field(None, description="Aeroplane wings dictionary")
    fuselages: Optional[OrderedDict[str, "FuselageSchema"]] = Field(
        None,
        description="Aeroplane fuselages dictionary",
    )
    xyz_ref: Optional[list[float]] = Field(
        [0, 0, 0],
        description="Reference point (e.g. CG) of the aeroplane in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )

    model_config = ConfigDict(from_attributes=True)


class ControlSurfaceSchema(BaseModel):
    name: str = Field(
        ...,
        description="Control surface name",
        examples=["Aileron", "Elevator", "Rudder", "Flap", "Elevon"],
    )
    hinge_point: float = Field(
        0.8,
        description="Hinge point location of the control surface as a factor of the chord length",
        examples=[0.8, 0.7, 0.5],
    )
    symmetric: bool = Field(
        True,
        description=(
            "Whether the control surface moves symmetric (e.g flaps, elevator) or anti-symmetric "
            "(e.g. aileron, elevon, v-tail) to the left and right wing"
        ),
    )
    deflection: float = Field(
        0.0,
        description="Deflection angle of the control surface in degrees",
        examples=[5, 2, 0],
    )

    model_config = ConfigDict(from_attributes=True)


class ControlSurfacePatchSchema(BaseModel):
    name: Optional[str] = Field(None, description="Control surface name")
    hinge_point: Optional[float] = Field(
        None,
        description="Hinge point location as relative chord factor",
    )
    symmetric: Optional[bool] = Field(
        None,
        description="Whether the control surface is symmetric between left/right wings",
    )
    deflection: Optional[float] = Field(
        None,
        description="Current control-surface deflection in degrees",
    )

    @model_validator(mode="after")
    def validate_non_empty_patch(self):
        if all(
            value is None
            for value in [self.name, self.hinge_point, self.symmetric, self.deflection]
        ):
            raise ValueError("ControlSurfacePatchSchema requires at least one field.")
        return self

    model_config = ConfigDict(extra="forbid")


class ControlSurfaceCadDetailsSchema(BaseModel):
    rel_chord_tip: Optional[float] = Field(None, description="Tip hinge position as relative chord (0.0-1.0)")
    hinge_spacing: Optional[float] = Field(None, description="Hinge spacing in millimeters")
    side_spacing_root: Optional[float] = Field(None, description="Root side spacing in millimeters")
    side_spacing_tip: Optional[float] = Field(None, description="Tip side spacing in millimeters")
    servo_placement: Optional[Literal["top", "bottom"]] = Field(
        None,
        description="Servo placement relative to the wing shell",
    )
    rel_chord_servo_position: Optional[float] = Field(
        None,
        description="Relative chord position of servo placement",
    )
    rel_length_servo_position: Optional[float] = Field(
        None,
        description="Relative segment-length position of servo placement",
    )
    positive_deflection_deg: Optional[float] = Field(None, description="Maximum positive deflection in degrees")
    negative_deflection_deg: Optional[float] = Field(None, description="Maximum negative deflection in degrees")
    trailing_edge_offset_factor: Optional[float] = Field(
        None,
        description="Trailing-edge offset factor for printable geometry",
    )
    hinge_type: Optional[HingeType] = Field(None, description="Hinge type")

    model_config = ConfigDict(from_attributes=True)


class ControlSurfaceCadDetailsPatchSchema(BaseModel):
    rel_chord_tip: Optional[float] = Field(None, description="Tip hinge position as relative chord (0.0-1.0)")
    hinge_spacing: Optional[float] = Field(None, description="Hinge spacing in millimeters")
    side_spacing_root: Optional[float] = Field(None, description="Root side spacing in millimeters")
    side_spacing_tip: Optional[float] = Field(None, description="Tip side spacing in millimeters")
    servo_placement: Optional[Literal["top", "bottom"]] = Field(
        None,
        description="Servo placement relative to the wing shell",
    )
    rel_chord_servo_position: Optional[float] = Field(
        None,
        description="Relative chord position of servo placement",
    )
    rel_length_servo_position: Optional[float] = Field(
        None,
        description="Relative segment-length position of servo placement",
    )
    positive_deflection_deg: Optional[float] = Field(None, description="Maximum positive deflection in degrees")
    negative_deflection_deg: Optional[float] = Field(None, description="Maximum negative deflection in degrees")
    trailing_edge_offset_factor: Optional[float] = Field(
        None,
        description="Trailing-edge offset factor for printable geometry",
    )
    hinge_type: Optional[HingeType] = Field(None, description="Hinge type")

    @model_validator(mode="after")
    def validate_non_empty_patch(self):
        if all(
            value is None
            for value in [
                self.rel_chord_tip,
                self.hinge_spacing,
                self.side_spacing_root,
                self.side_spacing_tip,
                self.servo_placement,
                self.rel_chord_servo_position,
                self.rel_length_servo_position,
                self.positive_deflection_deg,
                self.negative_deflection_deg,
                self.trailing_edge_offset_factor,
                self.hinge_type,
            ]
        ):
            raise ValueError("ControlSurfaceCadDetailsPatchSchema requires at least one field.")
        return self

    model_config = ConfigDict(extra="forbid")


class SpareDetailSchema(BaseModel):
    spare_support_dimension_width: float = Field(..., description="Spar support width in millimeters")
    spare_support_dimension_height: float = Field(..., description="Spar support height in millimeters")
    spare_position_factor: Optional[float] = Field(
        None,
        description="Relative chord-wise position of the spar as a factor (0.0-1.0)",
    )
    spare_length: Optional[float] = Field(None, description="Spar length in millimeters")
    spare_start: float = Field(0.0, description="Spar start offset in millimeters")
    spare_mode: Optional[SparMode] = Field(
        "standard",
        description="Spar placement mode",
    )
    spare_vector: Optional[list[float]] = Field(None, description="Spar direction vector [x, y, z]")
    spare_origin: Optional[list[float]] = Field(None, description="Spar origin [x, y, z]")

    model_config = ConfigDict(from_attributes=True)


class TrailingEdgeDeviceDetailSchema(BaseModel):
    name: Optional[str] = Field(None, description="Trailing-edge device name")
    rel_chord_root: Optional[float] = Field(None, description="Root hinge position as relative chord (0.0-1.0)")
    rel_chord_tip: Optional[float] = Field(None, description="Tip hinge position as relative chord (0.0-1.0)")
    hinge_spacing: Optional[float] = Field(None, description="Hinge spacing in millimeters")
    side_spacing_root: Optional[float] = Field(None, description="Root side spacing in millimeters")
    side_spacing_tip: Optional[float] = Field(None, description="Tip side spacing in millimeters")
    servo: Optional[Servo | int] = Field(None, description="Servo object or servo index")
    servo_placement: Literal["top", "bottom"] = Field(
        "top",
        description="Servo placement relative to the wing shell",
    )

    @field_validator("servo_placement", mode="before")
    @classmethod
    def _default_servo_placement(cls, v):
        """DB column is nullable — coerce None to the default."""
        return v if v is not None else "top"

    rel_chord_servo_position: Optional[float] = Field(
        None,
        description="Relative chord position of servo placement",
    )
    rel_length_servo_position: Optional[float] = Field(
        None,
        description="Relative segment-length position of servo placement",
    )
    positive_deflection_deg: Optional[float] = Field(None, description="Maximum positive deflection in degrees")
    negative_deflection_deg: Optional[float] = Field(None, description="Maximum negative deflection in degrees")
    deflection_deg: Optional[float] = Field(
        0.0,
        description="Current trailing-edge device deflection in degrees",
    )
    trailing_edge_offset_factor: Optional[float] = Field(
        None,
        description="Trailing-edge offset factor for printable geometry",
    )
    hinge_type: Optional[HingeType] = Field(
        None,
        description="Hinge type",
    )
    symmetric: Optional[bool] = Field(
        None,
        description="Whether deflection is symmetric between left/right wing",
    )

    model_config = ConfigDict(from_attributes=True)


class TrailingEdgeDevicePatchSchema(BaseModel):
    name: Optional[str] = Field(None, description="Trailing-edge device name")
    rel_chord_root: Optional[float] = Field(None, description="Root hinge position as relative chord (0.0-1.0)")
    rel_chord_tip: Optional[float] = Field(None, description="Tip hinge position as relative chord (0.0-1.0)")
    hinge_spacing: Optional[float] = Field(None, description="Hinge spacing in millimeters")
    side_spacing_root: Optional[float] = Field(None, description="Root side spacing in millimeters")
    side_spacing_tip: Optional[float] = Field(None, description="Tip side spacing in millimeters")
    servo_placement: Optional[Literal["top", "bottom"]] = Field(
        None,
        description="Servo placement relative to the wing shell",
    )
    rel_chord_servo_position: Optional[float] = Field(
        None,
        description="Relative chord position of servo placement",
    )
    rel_length_servo_position: Optional[float] = Field(
        None,
        description="Relative segment-length position of servo placement",
    )
    positive_deflection_deg: Optional[float] = Field(None, description="Maximum positive deflection in degrees")
    negative_deflection_deg: Optional[float] = Field(None, description="Maximum negative deflection in degrees")
    deflection_deg: Optional[float] = Field(
        None,
        description="Current trailing-edge device deflection in degrees",
    )
    trailing_edge_offset_factor: Optional[float] = Field(
        None,
        description="Trailing-edge offset factor for printable geometry",
    )
    hinge_type: Optional[HingeType] = Field(
        None,
        description="Hinge type",
    )
    symmetric: Optional[bool] = Field(
        None,
        description="Whether deflection is symmetric between left/right wing",
    )

    @model_validator(mode="after")
    def validate_non_empty_patch(self):
        if all(
            value is None
            for value in [
                self.name,
                self.rel_chord_root,
                self.rel_chord_tip,
                self.hinge_spacing,
                self.side_spacing_root,
                self.side_spacing_tip,
                self.servo_placement,
                self.rel_chord_servo_position,
                self.rel_length_servo_position,
                self.positive_deflection_deg,
                self.negative_deflection_deg,
                self.deflection_deg,
                self.trailing_edge_offset_factor,
                self.hinge_type,
                self.symmetric,
            ]
        ):
            raise ValueError("TrailingEdgeDevicePatchSchema requires at least one field.")
        return self

    model_config = ConfigDict(extra="forbid")


class TrailingEdgeServoSchema(BaseModel):
    servo: Servo | int = Field(..., description="Servo object data or servo index")

    model_config = ConfigDict(from_attributes=True)


class TrailingEdgeServoPatchSchema(BaseModel):
    servo: Servo | int = Field(..., description="Servo object data or servo index")

    model_config = ConfigDict(extra="forbid")


class ControlSurfaceServoDetailsSchema(TrailingEdgeServoSchema):
    model_config = ConfigDict(from_attributes=True)


class ControlSurfaceServoDetailsPatchSchema(TrailingEdgeServoPatchSchema):
    model_config = ConfigDict(extra="forbid")


class WingUnitsSchema(BaseModel):
    geometry_length: Literal["m"] = Field("m", description="Unit of `xyz_le`, `chord` in x-sections")
    detail_length: Literal["mm"] = Field("mm", description="Unit of detailed wing configuration fields")
    angle: Literal["deg"] = Field("deg", description="Unit of angular fields")

    model_config = ConfigDict(from_attributes=True)


class WingXSecSchema(BaseModel):
    xyz_le: list[float] = Field(
        ...,
        description="Coordinates of the leading edge of the cross-section in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )
    chord: float = Field(
        ...,
        description="Chord length of the cross-section in meters",
        examples=[0.2, 0.18, 0.16],
    )
    twist: float = Field(
        ...,
        description="Twist angle of the cross-section in degrees",
        examples=[5, 2, 0],
    )
    airfoil: str | HttpUrl = Field(
        ...,
        description="Airfoil dat file location of the cross-section (file or URL)",
        examples=["./components/airfoils/naca0015.dat", "https://m-selig.ae.illinois.edu/ads/coord/naca0015.dat"],
    )
    control_surface: Optional[ControlSurfaceSchema] = Field(
        None,
        description="Control surface on the cross-section (ASB-compatible subset)",
    )
    x_sec_type: Optional[WingXSecType] = Field(
        None,
        description="Wing section type associated with the outgoing segment anchored at this x-section",
    )
    tip_type: Optional[TipType] = Field(
        None,
        description="Tip style for tip segments",
    )
    number_interpolation_points: Optional[int] = Field(
        None,
        description="Interpolation points used for lofting this segment",
    )
    spare_list: Optional[list[SpareDetailSchema]] = Field(
        None,
        description="Spar definitions associated with the outgoing segment at this x-section",
    )
    trailing_edge_device: Optional[TrailingEdgeDeviceDetailSchema] = Field(
        None,
        description="Detailed trailing-edge device definition for the outgoing segment at this x-section",
    )

    model_config = ConfigDict(from_attributes=True)


class WingXSecReadSchema(WingXSecSchema):
    model_config = ConfigDict(from_attributes=True)


class WingXSecGeometryWriteSchema(BaseModel):
    xyz_le: list[float] = Field(
        ...,
        description="Coordinates of the leading edge of the cross-section in the local coordinate system",
    )
    chord: float = Field(
        ...,
        description="Chord length of the cross-section in meters",
    )
    twist: float = Field(
        ...,
        description="Twist angle of the cross-section in degrees",
    )
    airfoil: str | HttpUrl = Field(
        ...,
        description="Airfoil dat file location of the cross-section (file or URL)",
    )
    x_sec_type: Optional[WingXSecType] = Field(
        default=None,
        description=(
            "Optional Wing-level segment classification. ``root`` is the "
            "first segment, ``segment`` is a regular middle segment, and "
            "``tip`` marks a wing tip that must also provide ``tip_type``. "
            "Leaving this ``None`` is fine for bare-aero wings; the CAD "
            "pipeline only looks at it for the VaseMode creator. The "
            "name matches ``x_sec_type`` on the read-side ``WingXSecSchema`` "
            "and the DB column; the legacy CAD code refers to the same "
            "concept as ``wing_segment_type`` in the Wing-side model."
        ),
    )
    tip_type: Optional[TipType] = Field(
        default=None,
        description=(
            "Optional wing-tip geometry. Only meaningful when "
            "``wing_segment_type='tip'``. ``flat`` closes the tip with a "
            "flat wall; ``round`` attempts a rounded fillet. Ignored on "
            "regular segments."
        ),
    )
    number_interpolation_points: Optional[int] = Field(
        default=None,
        description=(
            "Optional override for the number of points the airfoil spline "
            "is sampled at when the loft is built by the CAD pipeline. "
            "Higher values produce smoother lofts at the cost of CAD "
            "runtime; 201 is typical for production prints. Ignored by "
            "aerodynamic analysis."
        ),
    )

    model_config = ConfigDict(extra="forbid")


class AsbWingSchema(BaseModel):
    name: str = Field(..., description="Wing name", examples=["Main Wing", "Horizontal Stabilizer"])
    symmetric: bool = Field(
        True,
        description="Is the wing symmetric?",
        examples=[True, False],
    )
    design_model: Optional[Literal["wc", "asb"]] = Field(
        None,
        description="Design model discriminator: 'wc' (WingConfig) or 'asb' (Aerosandbox). NULL for legacy wings.",
    )
    x_secs: list[WingXSecSchema] = Field(
        ...,
        description="List of cross-sections of the wing",
        min_length=2,
    )
    units: WingUnitsSchema = Field(
        default_factory=WingUnitsSchema,
        description="Units for wing geometry and optional detailed fields",
    )

    @model_validator(mode="after")
    def validate_last_xsec_has_no_segment_details(self):
        last_xsec = self.x_secs[-1]
        if (
            last_xsec.x_sec_type is not None
            or last_xsec.tip_type is not None
            or last_xsec.number_interpolation_points is not None
            or last_xsec.spare_list is not None
            or last_xsec.trailing_edge_device is not None
        ):
            raise ValueError(
                "Segment-specific fields are not allowed on the last x-section; "
                "the last x-section is the terminal section only."
            )
        return self

    model_config = ConfigDict(from_attributes=True)


class AsbWingReadSchema(AsbWingSchema):
    x_secs: list[WingXSecReadSchema] = Field(
        ...,
        description="List of cross-sections of the wing",
        min_length=2,
    )

    model_config = ConfigDict(from_attributes=True)


class AsbWingGeometryWriteSchema(BaseModel):
    name: str = Field(..., description="Wing name", examples=["Main Wing", "Horizontal Stabilizer"])
    symmetric: bool = Field(
        True,
        description="Is the wing symmetric?",
        examples=[True, False],
    )
    x_secs: list[WingXSecGeometryWriteSchema] = Field(
        ...,
        description="List of wing cross-sections containing only ASB-minimum geometry",
        min_length=2,
    )

    model_config = ConfigDict(extra="forbid")


class FuselageXSecSuperEllipseSchema(BaseModel):
    xyz: list[float] = Field(
        ...,
        description="Coordinates of the center of the cross-section in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )
    a: float = Field(
        ...,
        description="Semi-major axis of the superellipse in meters",
        examples=[0.5, 0.6],
    )
    b: float = Field(
        ...,
        description="Semi-minor axis of the superellipse in meters",
        examples=[0.5, 0.4],
    )
    n: float = Field(
        ...,
        description="Superellipse exponent",
        examples=[2, 1.5],
    )

    model_config = ConfigDict(from_attributes=True)


class FuselageSchema(BaseModel):
    name: str = Field(..., description="Fuselage name", examples=["Fuselage"])
    x_secs: list[FuselageXSecSuperEllipseSchema] = Field(
        ...,
        description="List of cross-sections of the fuselage",
        min_length=2,
    )

    model_config = ConfigDict(from_attributes=True)
