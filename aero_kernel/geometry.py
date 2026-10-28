"""Input model of the geometry format (ARCHITECTURE ch. 8.11).

Mirrors ``docs/geometry-format/airplane-geometry.schema.json`` as types: required and optional
fields, enums, strict numbers and ``extra="forbid"``. It carries no physical constraint (no
``gt=0``, NaN and infinity parse): physically inadmissible but well-typed input is reported by
``validate.py`` as ``input_errors``.

Lengths are metres and angles degrees, except the format's millimetre fields (servo,
``hinge_spacing``, ``side_spacing_*``, ``turbulator.height_mm``). Those are converted to metres
while parsing, in :func:`_mm_to_m`, the only unit conversion in the kernel. Their attributes carry
the SI name (``height_m``) and the format's key is the ``validation_alias`` only, so a dumped
model does not parse again and cannot be scaled twice.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

__all__ = [
    "Airfoil",
    "AirplaneGeometry",
    "ControlSurface",
    "Fuselage",
    "FuselageXSecSuperEllipse",
    "InlineAirfoil",
    "Servo",
    "SpareDetail",
    "SurfaceType",
    "TrailingEdgeDevice",
    "Turbulator",
    "Wing",
    "WingUnits",
    "WingXSec",
]

# A number in the format is an int or a float, never a bool or a string; NaN and infinity parse.
Num = Annotated[float, Field(strict=True)]
Point3 = tuple[Num, Num, Num]
Flag = Annotated[bool, Field(strict=True)]


def _integer_valued(value: object) -> object:
    """Turn an integer-valued float (``3.0``) into an int; leave everything else to strict int.

    JSON Schema's ``integer`` admits ``3.0``. A bool, a string, ``3.5`` and NaN/infinity are
    passed on unchanged, so the strict int validation that follows rejects them.
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# A count or index of the format: an int, or an integer-valued float, normalised to int.
Count = Annotated[int, BeforeValidator(_integer_valued), Field(strict=True)]

_MM_TO_M = 0.001


def _mm_to_m(value: float) -> float:
    """Convert a millimetre field of the format to metres.

    The only unit conversion in the kernel (ch. 8.11): it runs while a document is parsed, so
    everything after parsing is SI.

    Args:
        value: The value as written in the format, in millimetres.

    Returns:
        The value in metres.
    """
    return value * _MM_TO_M


# A millimetre field of the format; it holds metres once parsed.
Millimetres = Annotated[float, Field(strict=True), AfterValidator(_mm_to_m)]


class _Frozen(BaseModel):
    """Base of all input models: frozen, unknown fields rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class FuselageXSecSuperEllipse(_Frozen):
    """One fuselage station: the outline ``|y/a|^n + |z/b|^n = 1`` normal to the x axis.

    Attributes:
        xyz: Centre of the section in aeroplane coordinates, metres.
        a: Semi-axis in y (half-width), metres.
        b: Semi-axis in z (half-height), metres.
        n: Exponent of the section, or of the upper half (``z >= 0``) when ``n_lower`` is set.
        n_lower: Exponent of the lower half (``z < 0``); ``None`` means the same as ``n``.
    """

    xyz: Point3
    a: Num
    b: Num
    n: Num
    n_lower: Num | None = None


class Fuselage(_Frozen):
    """One fuselage body: a chain of super-ellipse sections lofted along x.

    Attributes:
        name: Body name.
        x_secs: Sections in loft order.
        symmetric: Whether the body is mirrored about y = 0 (paired sub-bodies only).
        step_path: Path of the exported STEP surface geometry; kept verbatim, never read.
        solid_step_path: Path of the sewed solid STEP geometry; kept verbatim, never read.
    """

    name: str
    x_secs: tuple[FuselageXSecSuperEllipse, ...]
    symmetric: Flag = False
    step_path: str | None = None
    solid_step_path: str | None = None


class InlineAirfoil(_Frozen):
    """An airfoil given as coordinates instead of a designation.

    Attributes:
        coordinates: Contour points (x, y) in Selig order, normalised to chord 1.
    """

    coordinates: tuple[tuple[Num, Num], ...]


# A string is kept verbatim: whether it is a NACA designation or an unresolved path is decided
# by validate.py (code ``unresolved_airfoil``), in one place.
Airfoil = str | InlineAirfoil


class WingUnits(_Frozen):
    """Declared units of a wing; constant today (AIRPLANE-GEOMETRY.md ch. 2).

    Attributes:
        geometry_length: Unit of ``xyz_le`` and ``chord``.
        detail_length: Unit of the spar fields.
        angle: Unit of every angular field.
    """

    geometry_length: Literal["m"] = "m"
    detail_length: Literal["m"] = "m"
    angle: Literal["deg"] = "deg"


class ControlSurface(_Frozen):
    """The aerodynamic view of a movable surface; a projection of the trailing-edge device.

    Attributes:
        name: Surface name.
        hinge_point: Hinge line as a fraction of chord from the leading edge.
        symmetric: True when left and right deflect together.
        deflection: Current deflection in degrees (a state, not a limit).
    """

    name: str
    hinge_point: Num = 0.8
    symmetric: Flag = True
    deflection: Num = 0.0


class SpareDetail(_Frozen):
    """One spar of a segment. Every length is metres in the document (ch. 5); never scaled.

    Attributes:
        spare_support_dimension_width: Width of the spar pocket across the chord, metres.
        spare_support_dimension_height: Height of the spar pocket through the profile, metres.
        spare_position_factor: Chordwise position as a fraction of chord.
        spare_length: Spar length, metres; ``None`` means the full segment.
        spare_start: Offset from the segment root where the spar begins, metres.
        spare_mode: How origin and direction are derived.
        spare_vector: Dimensionless unit direction of the spar axis.
        spare_origin: Start point of the spar axis, metres.
    """

    spare_support_dimension_width: Num
    spare_support_dimension_height: Num
    spare_position_factor: Num | None = None
    spare_length: Num | None = None
    spare_start: Num = 0.0
    spare_mode: (
        Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"] | None
    ) = "standard"
    spare_vector: Point3 | None = None
    spare_origin: Point3 | None = None


class Servo(_Frozen):
    """Physical envelope of a servo actuator. The format gives millimetres; attributes hold metres.

    Attributes:
        component_id: Foreign key into the component library; kept, never read.
        length_m: X-dimension of the body (format key ``length``).
        width_m: Y-dimension of the body (``width``).
        height_m: Z-dimension of the body (``height``).
        leading_length_m: X-distance from the front face to the output shaft axis (``leading_length``).
        latch_z_m: Z-position of the lower edge of the mounting lug (``latch_z``).
        latch_x_m: X-dimension of the mounting lug (``latch_x``).
        latch_thickness_m: Thickness of the mounting lug (``latch_thickness``).
        latch_length_m: Length of the mounting lug (``latch_length``).
        cable_z_m: Z-position of the cable exit (``cable_z``).
        screw_hole_lx_m: X-distance of the screw hole from the leading edge (``screw_hole_lx``).
        screw_hole_d_m: Screw hole diameter (``screw_hole_d``).
    """

    component_id: Count | None = None
    length_m: Millimetres = Field(validation_alias="length")
    width_m: Millimetres = Field(validation_alias="width")
    height_m: Millimetres = Field(validation_alias="height")
    leading_length_m: Millimetres = Field(validation_alias="leading_length")
    latch_z_m: Millimetres = Field(validation_alias="latch_z")
    latch_x_m: Millimetres = Field(validation_alias="latch_x")
    latch_thickness_m: Millimetres = Field(validation_alias="latch_thickness")
    latch_length_m: Millimetres = Field(validation_alias="latch_length")
    cable_z_m: Millimetres = Field(validation_alias="cable_z")
    screw_hole_lx_m: Millimetres = Field(validation_alias="screw_hole_lx")
    screw_hole_d_m: Millimetres = Field(validation_alias="screw_hole_d")


class TrailingEdgeDevice(_Frozen):
    """Construction definition of a movable trailing-edge surface (ch. 6).

    Spacings are millimetres in the format and metres here (``hinge_spacing_m`` is the format key
    ``hinge_spacing``). Relative chords are fractions, deflections degrees.

    Attributes:
        name: Device name.
        role: Standardised role.
        label: Display name.
        rel_chord_root: Hinge position at the segment root as a fraction of chord.
        rel_chord_tip: Hinge position at the segment tip as a fraction of chord.
        hinge_spacing_m: Gap at the hinge line, metres.
        side_spacing_root_m: Side gap at the root end, metres.
        side_spacing_tip_m: Side gap at the tip end, metres.
        servo: A servo, or an index into an external servo list.
        servo_placement: Shell surface the servo bay is cut into.
        rel_chord_servo_position: Chordwise servo position as a fraction of chord.
        rel_length_servo_position: Spanwise servo position as a fraction of the segment length.
        positive_deflection_deg: Stop in the positive sense; never read by the kernel (ch. 8.11).
        negative_deflection_deg: Stop in the negative sense; never read by the kernel (ch. 8.11).
        deflection_deg: Current deflection, degrees.
        trailing_edge_offset_factor: Clearance multiplier on the rib cutout; around 1, not a fraction.
        hinge_type: Hinge geometry.
        symmetric: Whether left and right deflect together.
        mix_gain_primary: AVL gain on the symmetric axis.
        mix_gain_secondary: AVL gain on the antisymmetric axis.
        differential_ratio: Up/down throw ratio; display only.
    """

    name: str | None = None
    role: Literal[
        "elevator",
        "aileron",
        "rudder",
        "elevon",
        "flaperon",
        "ruddervator",
        "stabilator",
        "flap",
        "other",
    ] = "other"
    label: str | None = None
    rel_chord_root: Num | None = None
    rel_chord_tip: Num | None = None
    hinge_spacing_m: Millimetres | None = Field(default=None, validation_alias="hinge_spacing")
    side_spacing_root_m: Millimetres | None = Field(
        default=None, validation_alias="side_spacing_root"
    )
    side_spacing_tip_m: Millimetres | None = Field(
        default=None, validation_alias="side_spacing_tip"
    )
    servo: Servo | Count | None = None
    servo_placement: Literal["top", "bottom"] = "top"
    rel_chord_servo_position: Num | None = None
    rel_length_servo_position: Num | None = None
    positive_deflection_deg: Num | None = None
    negative_deflection_deg: Num | None = None
    deflection_deg: Num | None = 0.0
    trailing_edge_offset_factor: Num | None = 1.0
    hinge_type: Literal["middle", "top", "top_simple", "round_inside", "round_outside"] | None = (
        None
    )
    symmetric: Flag | None = None
    mix_gain_primary: Num = 1.0
    mix_gain_secondary: Num = 1.0
    differential_ratio: Num = 1.0


class Turbulator(_Frozen):
    """Upper-surface turbulator strip on one segment (gh-934).

    Attributes:
        form: Build form of the strip.
        height_m: Strip or thread height, metres (format key ``height_mm``, millimetres).
        position_root: Chordwise position x/c at the segment root.
        position_tip: Chordwise position x/c at the segment tip.
        enabled: Whether the strip is cut into the CAD output.
    """

    form: Literal["zigzag", "dots", "thread"] = "zigzag"
    height_m: Millimetres = Field(
        default=_mm_to_m(0.3),
        validation_alias="height_mm",
        # the published JSON Schema speaks the format: millimetres under the format's key
        json_schema_extra={"default": 0.3},
    )
    position_root: Num
    position_tip: Num | None = None
    enabled: Flag = True


class WingXSec(_Frozen):
    """One rib: its geometry plus the detail of the segment that starts here (ch. 4.1).

    Attributes:
        xyz_le: Leading-edge point, absolute, metres.
        chord: Chord length, metres.
        twist: Cumulative twist against the x axis, degrees.
        dihedral: Dihedral increment at this rib (absolute on the root rib), degrees.
        airfoil: Designation or inline coordinates.
        x_sec_type: Role of the segment starting at this rib.
        tip_type: How the outboard end is closed; meaningful on a ``tip`` segment.
        number_interpolation_points: Intermediate profiles used when lofting the segment.
        control_surface: Aerodynamic view of the control surface on the segment.
        spare_list: Spars of the segment, in order; the index carries meaning (ch. 5).
        trailing_edge_device: Construction definition of the movable surface on the segment.
        turbulator: Upper-surface turbulator strip on the segment.
    """

    xyz_le: Point3
    chord: Num
    twist: Num
    dihedral: Num | None = None
    airfoil: Airfoil
    x_sec_type: Literal["root", "segment", "tip"] | None = None
    tip_type: Literal["flat", "round"] | None = None
    number_interpolation_points: Count | None = None
    control_surface: ControlSurface | None = None
    spare_list: tuple[SpareDetail, ...] | None = None
    trailing_edge_device: TrailingEdgeDevice | None = None
    turbulator: Turbulator | None = None


# The function of a wing (ARCHITECTURE ch. 8.5): the type follows the function, not the position.
SurfaceType = Literal[
    "main_wing",
    "horizontal_tail",
    "vertical_tail",
    "v_tail",
    "canard",
    "tandem_wing",
    "winglet",
]


class Wing(_Frozen):
    """One lifting surface: an ordered chain of ribs, root first.

    Attributes:
        name: Wing name.
        symmetric: Whether the surface is mirrored about the XZ plane (only one half is stored).
        surface_type: The function of the surface (ARCHITECTURE ch. 8.5, D9); required, never
            inferred. Optional in the type because ``validate.py`` reports its absence
            (``missing_surface_type``); the geometry format (version 2, #1187) requires it.
        design_model: Which editor owns the wing; geometry-neutral.
        x_secs: Ribs from root to tip.
        units: Declared units; the constants when absent.
    """

    name: str
    symmetric: Flag = True
    surface_type: SurfaceType | None = None
    design_model: Literal["wc", "asb"] | None = None
    x_secs: tuple[WingXSec, ...]
    units: WingUnits = Field(default_factory=WingUnits)


class AirplaneGeometry(_Frozen):
    """The geometry document of one aeroplane (AIRPLANE-GEOMETRY.md ch. 3).

    Attributes:
        name: Aeroplane name.
        total_mass_kg: Total mass in kg; a consistency check only (a warning when it differs from the passed mass, a hint when the mass is missing), the mass itself always comes from the values (ch. 8.11, #1302).
        xyz_ref: Moment reference point in metres.
        wings: Wing surfaces by name.
        fuselages: Fuselage bodies by name.
    """

    name: str
    total_mass_kg: Num | None = None
    xyz_ref: Point3 = (0.0, 0.0, 0.0)
    wings: dict[str, Wing] | None = None
    fuselages: dict[str, Fuselage] | None = None
