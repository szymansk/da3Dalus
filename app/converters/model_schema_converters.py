import math
import os
from typing import Any, List, Optional

import aerosandbox as asb
from aerosandbox import FuselageXSec

from app import schemas
from app.models import AeroplaneModel, WingModel
from app.models.aeroplanemodel import FuselageModel
from app.schemas import AeroplaneSchema
from app.schemas.Servo import Servo as ServoSchema
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.components.Servo import Servo as WingServo
from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import FuselageConfiguration
from cad_designer.airplane.aircraft_topology.wing import Spare, TrailingEdgeDevice, WingConfiguration


async def aeroplane_model_to_aeroplane_schema_async(plane: AeroplaneModel) -> AeroplaneSchema:
    plane_dict = plane.__dict__.copy()
    plane_dict["wings"] = {w.name: w for w in plane.wings}
    plane_dict["fuselages"] = {f.name: f for f in plane.fuselages}
    plane_schema: AeroplaneSchema = AeroplaneSchema.model_validate(plane_dict)
    return plane_schema


def _build_asb_airfoil(airfoil_ref) -> asb.Airfoil:
    from app.services.create_wing_configuration import _resolve_airfoil_reference

    airfoil_ref_str = str(airfoil_ref)

    # Use the central resolver (handles case-insensitive lookup, bare names, paths)
    resolved = _resolve_airfoil_reference(airfoil_ref_str)
    if os.path.isfile(resolved):
        return asb.Airfoil(
            name=os.path.splitext(os.path.basename(resolved))[0],
            coordinates=resolved,
        )

    # Fall back to ASB name-based lookup (e.g. "naca2412", "sd7037", UIUC names).
    airfoil_name = os.path.splitext(os.path.basename(airfoil_ref_str))[0] or airfoil_ref_str
    return asb.Airfoil(name=airfoil_name)


def _normalize_airfoil_reference_for_schema(airfoil_ref: asb.Airfoil | str) -> str:
    """Return a stable airfoil reference string for API/database schemas.

    Converts absolute paths, bare names ("ag10"), and names with extension
    ("ag10.dat") into portable relative paths like "./components/airfoils/ag10.dat"
    so that worker subprocesses with a different CWD can resolve them.
    """
    raw_reference = str(getattr(airfoil_ref, "name", airfoil_ref) or "")
    if not raw_reference:
        return raw_reference

    # Already a portable relative path -- keep as-is.
    normalized = raw_reference.replace("\\", "/")
    if normalized.startswith("./components/airfoils/"):
        return raw_reference

    # Convert absolute paths inside ".../components/airfoils/..." back to a portable relative path.
    parts = [part for part in normalized.split("/") if part]
    for index in range(len(parts) - 1):
        if parts[index].lower() == "components" and parts[index + 1].lower() == "airfoils":
            relative = "/".join(parts[index:])
            return f"./{relative}"

    # Bare name or name.dat -- try to resolve via case-insensitive lookup.
    from app.services.create_wing_configuration import _find_airfoil_case_insensitive

    found = _find_airfoil_case_insensitive(raw_reference)
    if found:
        return f"./components/airfoils/{found.name}"

    return raw_reference


def _wing_configuration_sections(wing_config: WingConfiguration):
    """
    Return wing cross-section descriptors in section order (root first, then each segment tip).
    """
    if not wing_config.segments:
        return []

    sections = [(wing_config.segments[0].root_airfoil, wing_config.segments[0].trailing_edge_device)]
    for segment in wing_config.segments:
        sections.append((segment.tip_airfoil, segment.trailing_edge_device))
    return sections


def _normalize_wing_config_ted_for_asb(wing_config: WingConfiguration):
    """
    Temporarily enforce rel_chord_tip == rel_chord_root for ASB conversion.

    WingConfiguration.asb_wing() requires this, but rel_chord_tip is still preserved in schema details.
    """
    original_tip_values = []
    for segment in wing_config.segments or []:
        ted = segment.trailing_edge_device
        if ted is None:
            continue
        original_tip_values.append((ted, ted.rel_chord_tip))
        if ted.rel_chord_root is not None:
            ted.rel_chord_tip = ted.rel_chord_root
    return original_tip_values


def _restore_wing_config_ted_after_asb(original_tip_values) -> None:
    for ted, original_tip in original_tip_values:
        ted.rel_chord_tip = original_tip


def _to_payload(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    if hasattr(value, "__dict__"):
        return {k: v for k, v in value.__dict__.items() if not k.startswith("_")}
    return value


def _servo_to_schema(servo_value: Any) -> Optional[ServoSchema | int]:
    if servo_value is None:
        return None
    if isinstance(servo_value, int):
        return servo_value

    payload = _to_payload(servo_value)
    if isinstance(payload, dict):
        try:
            return ServoSchema(**payload)
        except Exception:
            return None
    return None


def _servo_to_wing_servo(servo_value: Any) -> Optional[WingServo | int]:
    if servo_value is None:
        return None
    if isinstance(servo_value, int):
        return servo_value

    payload = _to_payload(servo_value)
    if isinstance(payload, dict):
        try:
            return WingServo(**payload)
        except Exception:
            return None
    return None


def _spare_to_schema(spare: Spare) -> schemas.SpareDetailSchema:
    vector = spare.spare_vector.toTuple() if getattr(spare, "spare_vector", None) is not None else None
    origin = spare.spare_origin.toTuple() if getattr(spare, "spare_origin", None) is not None else None
    return schemas.SpareDetailSchema(
        spare_support_dimension_width=float(spare.spare_support_dimension_width),
        spare_support_dimension_height=float(spare.spare_support_dimension_height),
        spare_position_factor=None if spare.spare_position_factor is None else float(spare.spare_position_factor),
        spare_length=None if spare.spare_length is None else float(spare.spare_length),
        spare_start=0.0 if spare.spare_start is None else float(spare.spare_start),
        spare_mode=spare.spare_mode,
        spare_vector=[float(value) for value in vector] if vector is not None else None,
        spare_origin=[float(value) for value in origin] if origin is not None else None,
    )


def _spare_schema_to_spare(spare_schema: schemas.SpareDetailSchema) -> Spare:
    return Spare(
        spare_support_dimension_width=float(spare_schema.spare_support_dimension_width),
        spare_support_dimension_height=float(spare_schema.spare_support_dimension_height),
        spare_position_factor=spare_schema.spare_position_factor,
        spare_length=spare_schema.spare_length,
        spare_start=spare_schema.spare_start,
        spare_vector=tuple(spare_schema.spare_vector) if spare_schema.spare_vector is not None else None,
        spare_origin=tuple(spare_schema.spare_origin) if spare_schema.spare_origin is not None else None,
        spare_mode=spare_schema.spare_mode or "standard",
    )


def _trailing_edge_device_to_schema(ted: TrailingEdgeDevice) -> schemas.TrailingEdgeDeviceDetailSchema:
    return schemas.TrailingEdgeDeviceDetailSchema(
        name=ted.name,
        rel_chord_root=ted.rel_chord_root,
        rel_chord_tip=ted.rel_chord_tip,
        hinge_spacing=ted.hinge_spacing,
        side_spacing_root=ted.side_spacing_root,
        side_spacing_tip=ted.side_spacing_tip,
        servo=_servo_to_schema(getattr(ted, "_servo", None)),
        servo_placement=ted.servo_placement,
        rel_chord_servo_position=ted.rel_chord_servo_position,
        rel_length_servo_position=ted.rel_length_servo_position,
        positive_deflection_deg=ted.positive_deflection_deg,
        negative_deflection_deg=ted.negative_deflection_deg,
        deflection_deg=getattr(ted, "deflection_deg", None),
        trailing_edge_offset_factor=ted.trailing_edge_offset_factor,
        hinge_type=ted.hinge_type,
        symmetric=ted.symmetric,
    )


def _trailing_edge_device_schema_to_wing_ted(
    ted_schema: schemas.TrailingEdgeDeviceDetailSchema,
) -> TrailingEdgeDevice:
    ted = TrailingEdgeDevice(
        name=ted_schema.name or "control_surface",
        rel_chord_root=ted_schema.rel_chord_root,
        rel_chord_tip=ted_schema.rel_chord_tip,
        hinge_spacing=ted_schema.hinge_spacing,
        side_spacing_root=ted_schema.side_spacing_root,
        side_spacing_tip=ted_schema.side_spacing_tip,
        servo=_servo_to_wing_servo(ted_schema.servo),
        servo_placement=ted_schema.servo_placement,
        rel_chord_servo_position=ted_schema.rel_chord_servo_position,
        rel_length_servo_position=ted_schema.rel_length_servo_position,
        positive_deflection_deg=25.0 if ted_schema.positive_deflection_deg is None else ted_schema.positive_deflection_deg,
        negative_deflection_deg=25.0 if ted_schema.negative_deflection_deg is None else ted_schema.negative_deflection_deg,
        trailing_edge_offset_factor=(
            1.0 if ted_schema.trailing_edge_offset_factor is None else ted_schema.trailing_edge_offset_factor
        ),
        hinge_type="top" if ted_schema.hinge_type is None else ted_schema.hinge_type,
        symmetric=True if ted_schema.symmetric is None else ted_schema.symmetric,
    )
    # CAD type has no dedicated field yet; keep value on instance for roundtrip/export use.
    ted.deflection_deg = 0.0 if ted_schema.deflection_deg is None else float(ted_schema.deflection_deg)
    return ted


def _control_surface_from_ted(
    ted: schemas.TrailingEdgeDeviceDetailSchema,
    fallback: Optional[schemas.ControlSurfaceSchema] = None,
) -> schemas.ControlSurfaceSchema:
    name = ted.name or (fallback.name if fallback else "Control Surface")

    if ted.rel_chord_root is not None:
        hinge_point = ted.rel_chord_root
    elif fallback:
        hinge_point = fallback.hinge_point
    else:
        hinge_point = 0.8

    if ted.symmetric is not None:
        symmetric = ted.symmetric
    elif fallback:
        symmetric = fallback.symmetric
    else:
        symmetric = True

    if ted.deflection_deg is not None:
        deflection = float(ted.deflection_deg)
    elif fallback:
        deflection = fallback.deflection
    else:
        deflection = 0.0

    return schemas.ControlSurfaceSchema(
        name=name,
        hinge_point=hinge_point,
        symmetric=symmetric,
        deflection=deflection,
    )


def _control_surface_for_xsec(
    x_sec: schemas.WingXSecSchema,
) -> Optional[schemas.ControlSurfaceSchema]:
    if x_sec.trailing_edge_device is not None:
        return _control_surface_from_ted(x_sec.trailing_edge_device, fallback=x_sec.control_surface)
    return x_sec.control_surface


def _asb_wing_xsecs_from_schema(wing: schemas.AsbWingSchema) -> List[asb.WingXSec]:
    xsecs: List[asb.WingXSec] = []
    for x_sec in wing.x_secs:
        control_surface = _control_surface_for_xsec(x_sec)
        xsecs.append(
            asb.WingXSec(
                xyz_le=x_sec.xyz_le,
                chord=x_sec.chord,
                twist=x_sec.twist,
                airfoil=_build_asb_airfoil(x_sec.airfoil),
                control_surfaces=[
                    asb.ControlSurface(
                        name=control_surface.name,
                        symmetric=control_surface.symmetric,
                        deflection=control_surface.deflection,
                        hinge_point=control_surface.hinge_point,
                        trailing_edge=True,
                    )
                ]
                if control_surface
                else [],
            )
        )
    return xsecs


def _scale_asb_wing_geometry_schema(
    wing: schemas.AsbWingSchema,
    scale: float,
) -> schemas.AsbWingSchema:
    if math.isclose(scale, 1.0):
        return wing

    scaled_x_secs: List[schemas.WingXSecSchema] = []
    for x_sec in wing.x_secs:
        scaled_x_secs.append(
            x_sec.model_copy(
                update={
                    "xyz_le": [float(value) * scale for value in x_sec.xyz_le],
                    "chord": float(x_sec.chord) * scale,
                }
            )
        )

    return wing.model_copy(update={"x_secs": scaled_x_secs})


def _asb_fuselage_xsecs_from_schema(
    fuselage: schemas.FuselageSchema,
) -> List[FuselageXSec]:
    return [
        FuselageXSec(
            xyz_c=[float(value) for value in x_sec.xyz],
            xyz_normal=[1.0, 0.0, 0.0],
            radius=None,
            height=float(x_sec.a),
            width=float(x_sec.b),
            shape=float(x_sec.n),
        )
        for x_sec in fuselage.x_secs
    ]


def fuselage_schema_to_fuselage_config(
    fuselage: schemas.FuselageSchema,
) -> FuselageConfiguration:
    fuselage_config = FuselageConfiguration(name=fuselage.name)
    fuselage_config.asb_fuselage = asb.Fuselage(
        name=fuselage.name,
        xsecs=_asb_fuselage_xsecs_from_schema(fuselage),
    )
    return fuselage_config


def fuselage_model_to_fuselage_config(
    fuselage: FuselageModel,
) -> FuselageConfiguration:
    fuselage_config = FuselageConfiguration(name=fuselage.name)
    fuselage_config.asb_fuselage = asb.Fuselage(
        name=fuselage.name,
        xsecs=[
            FuselageXSec(
                xyz_c=[float(value) for value in x_sec.xyz],
                xyz_normal=[1.0, 0.0, 0.0],
                radius=None,
                height=float(x_sec.a),
                width=float(x_sec.b),
                shape=float(x_sec.n),
            )
            for x_sec in (fuselage.x_secs or [])
        ],
    )
    return fuselage_config


def _hydrate_segment_from_xsec(
    segment, root_x_sec: schemas.WingXSecSchema, tip_x_sec: schemas.WingXSecSchema
) -> None:
    """Copy schema-level details (airfoils, TED, spares, metadata) onto a WingConfiguration segment."""
    segment.root_airfoil.airfoil = str(root_x_sec.airfoil)
    segment.tip_airfoil.airfoil = str(tip_x_sec.airfoil)

    if root_x_sec.x_sec_type is not None:
        segment.wing_segment_type = root_x_sec.x_sec_type
    if root_x_sec.tip_type is not None:
        segment.tip_type = root_x_sec.tip_type
    if root_x_sec.number_interpolation_points is not None:
        segment.number_interpolation_points = root_x_sec.number_interpolation_points

    ted_payload = WingModel._merge_ted_with_control_surface(
        trailing_edge_device=root_x_sec.trailing_edge_device,
        control_surface=root_x_sec.control_surface,
    )
    ted_schema = (
        schemas.TrailingEdgeDeviceDetailSchema.model_validate(ted_payload)
        if ted_payload is not None
        else None
    )
    segment.trailing_edge_device = (
        _trailing_edge_device_schema_to_wing_ted(ted_schema) if ted_schema is not None else None
    )

    if root_x_sec.spare_list is not None:
        segment.spare_list = [_spare_schema_to_spare(s) for s in root_x_sec.spare_list]


def _hydrate_wing_configuration_details(
    wing_config: WingConfiguration,
    wing_schema: schemas.AsbWingSchema,
) -> None:
    for segment_index, segment in enumerate(wing_config.segments or []):
        if segment_index >= len(wing_schema.x_secs) - 1:
            break
        _hydrate_segment_from_xsec(
            segment,
            wing_schema.x_secs[segment_index],
            wing_schema.x_secs[segment_index + 1],
        )

    _resolve_spare_vectors_and_origins(wing_config)


def _can_follow_previous_spare(
    wing_config: WingConfiguration, segment_index: int, spare_index: int
) -> bool:
    """Check if the spare can follow the previous segment's corresponding spare."""
    if segment_index == 0:
        return False
    previous_spares = wing_config.segments[segment_index - 1].spare_list or []
    if spare_index < 0 or spare_index >= len(previous_spares):
        return False
    prev: Spare = previous_spares[spare_index]
    return prev.spare_vector is not None and prev.spare_origin is not None


def _resolve_single_spare(
    wing_config: WingConfiguration, segment_index: int, spare_index: int, spare
) -> None:
    """Resolve vectors and origins for a single spare based on its mode."""
    mode = spare.spare_mode or "standard"

    if mode == "follow":
        if _can_follow_previous_spare(wing_config, segment_index, spare_index):
            wing_config._set_follow_spare_origin_vector(segment_index, spare, spare_index)
        else:
            wing_config._set_standard_spare_origin_vector(segment_index, spare)
        return

    if mode in {"standard", "standard_backward", "orthogonal_backward", "normal"}:
        wing_config._set_standard_spare_origin_vector(segment_index, spare)


def _resolve_spare_vectors_and_origins(wing_config: WingConfiguration) -> None:
    for segment_index, segment in enumerate(wing_config.segments or []):
        for spare_index, spare in enumerate(segment.spare_list or []):
            _resolve_single_spare(wing_config, segment_index, spare_index, spare)


async def aeroplane_schema_to_asb_airplane_async(plane_schema: AeroplaneSchema) -> "asb.Airplane":
    """
    Convert an AeroplaneSchema to an Aerosandbox Airplane object.

    Args:
        plane_schema (AeroplaneSchema): The schema to convert.

    Returns:
        asb.Airplane: The converted Aerosandbox Airplane object.
    """
    from aerosandbox import Airplane, Fuselage, Wing

    asb_airplane: Airplane = Airplane(
        name=plane_schema.name,
        wings=[
            Wing(
                name=wing_name,
                symmetric=wing.symmetric,
                xsecs=[xsec for xsec in _asb_wing_xsecs_from_schema(wing)] if wing.x_secs else None,
            )
            for wing_name, wing in plane_schema.wings.items()
        ]
        if plane_schema.wings
        else None,
        fuselages=[
            Fuselage(
                name=fuselage_name,
                xsecs=_asb_fuselage_xsecs_from_schema(fuselage) if fuselage.x_secs else None,
            )
            for fuselage_name, fuselage in plane_schema.fuselages.items()
        ]
        if plane_schema.fuselages
        else None,
        xyz_ref=plane_schema.xyz_ref,
    )

    return asb_airplane


async def aeroplane_schema_to_airplane_configuration_async(plane_schema: AeroplaneSchema) -> AirplaneConfiguration:
    if plane_schema.total_mass_kg is None:
        raise ValueError("AeroplaneSchema.total_mass_kg must be set to build AirplaneConfiguration.")

    wing_configs: List[WingConfiguration] = []
    for wing in (plane_schema.wings or {}).values():
        xsecs = _asb_wing_xsecs_from_schema(wing)
        wing_config = WingConfiguration.from_asb(xsecs=xsecs, symmetric=wing.symmetric)
        _hydrate_wing_configuration_details(wing_config, wing)
        wing_configs.append(wing_config)

    fuselage_configs: Optional[List[FuselageConfiguration]] = None
    if plane_schema.fuselages:
        fuselage_configs = [
            fuselage_schema_to_fuselage_config(fuselage_schema)
            for fuselage_schema in plane_schema.fuselages.values()
        ]

    return AirplaneConfiguration(
        name=plane_schema.name,
        total_mass_kg=plane_schema.total_mass_kg,
        wings=wing_configs,
        fuselages=fuselage_configs,
    )


def wing_model_to_asb_wing_schema(wing: WingModel) -> schemas.AsbWingSchema:
    """Convert a SQLAlchemy ``WingModel`` to its Pydantic
    ``AsbWingSchema`` representation.

    Split out from :func:`wing_model_to_wing_config` so that callers that
    need to cross a process boundary (e.g. the CAD ProcessPoolExecutor
    in ``app.services.cad_service``) can pickle the schema, which is
    picklable, instead of the final :class:`WingConfiguration`, which
    contains ``cq.Vector`` / OCCT ``gp_Vec`` objects that are not.

    The last x-section is a terminal boundary — segment-specific fields
    (TED, spars, x_sec_type, tip_type) are stripped if present in the
    DB to avoid validation errors from legacy data.
    """
    # Strip segment-specific fields from the last x-section to handle
    # legacy DB rows that have TED/spars on the terminal x-section.
    xsec_dicts = []
    for xs in wing.x_secs:
        xsec_dicts.append(schemas.WingXSecSchema.model_validate(
            xs, from_attributes=True,
        ).model_dump())

    # Strip segment-specific fields from last x-section
    if xsec_dicts:
        last = xsec_dicts[-1]
        last["trailing_edge_device"] = None
        last["spare_list"] = None
        last["x_sec_type"] = None
        last["tip_type"] = None
        last["number_interpolation_points"] = None

    return schemas.AsbWingSchema.model_validate({
        "name": wing.name,
        "symmetric": wing.symmetric,
        "x_secs": xsec_dicts,
    })


def asb_wing_schema_to_wing_config(
    asb_wing: schemas.AsbWingSchema,
    scale: float = 1.0,
) -> WingConfiguration:
    """Convert a ``AsbWingSchema`` to a live ``WingConfiguration``.

    This is the second half of :func:`wing_model_to_wing_config` and is
    suitable for calling inside a worker process after the schema has
    been transported via pickle.
    """
    geometry_scaled_schema = _scale_asb_wing_geometry_schema(asb_wing, scale=scale)
    xsecs = _asb_wing_xsecs_from_schema(geometry_scaled_schema)
    wing_config = WingConfiguration.from_asb(xsecs, geometry_scaled_schema.symmetric)
    _hydrate_wing_configuration_details(wing_config, asb_wing)
    return wing_config


def wing_model_to_wing_config(wing: WingModel, scale: float = 1.0) -> WingConfiguration:
    """Convert a SQLAlchemy ``WingModel`` to a live ``WingConfiguration``.

    Convenience wrapper around :func:`wing_model_to_asb_wing_schema` and
    :func:`asb_wing_schema_to_wing_config` for in-process callers. For
    cross-process transports prefer calling the two halves explicitly
    so the schema (not the config) crosses the process boundary.
    """
    asb_wing = wing_model_to_asb_wing_schema(wing)
    return asb_wing_schema_to_wing_config(asb_wing, scale=scale)


def _extract_control_surface_from_xsec(x_sec) -> Optional[schemas.ControlSurfaceSchema]:
    """Extract the first control surface from an ASB WingXSec, if any."""
    if not x_sec.control_surfaces:
        return None
    cs = x_sec.control_surfaces[0]
    return schemas.ControlSurfaceSchema(
        name=cs.name,
        hinge_point=float(cs.hinge_point),
        symmetric=bool(cs.symmetric),
        deflection=float(cs.deflection),
    )


def _resolve_airfoil_ref_for_index(index, section_data, x_sec):
    """Return the airfoil reference for the given xsec index."""
    if index < len(section_data):
        section_airfoil, _ = section_data[index]
        return section_airfoil.airfoil
    return x_sec.airfoil


def _build_segment_details(segment, control_surface):
    """Extract TED, spare list, and segment metadata from a WingConfiguration segment."""
    trailing_edge_device = None
    spare_list = None

    if segment.trailing_edge_device is not None:
        trailing_edge_device = _trailing_edge_device_to_schema(segment.trailing_edge_device)

    canonical_ted_payload = WingModel._merge_ted_with_control_surface(
        trailing_edge_device=trailing_edge_device,
        control_surface=control_surface,
    )
    if canonical_ted_payload is not None:
        trailing_edge_device = schemas.TrailingEdgeDeviceDetailSchema.model_validate(canonical_ted_payload)
        control_surface = _control_surface_from_ted(trailing_edge_device, fallback=control_surface)

    if segment.spare_list is not None:
        spare_list = [_spare_to_schema(spare) for spare in segment.spare_list]

    return (
        trailing_edge_device,
        spare_list,
        control_surface,
        segment.wing_segment_type,
        segment.tip_type,
        segment.number_interpolation_points,
    )


def wing_config_to_asb_wing_schema(
    wing_config: WingConfiguration,
    wing_name: str,
    scale: float = 1.0,
) -> schemas.AsbWingSchema:
    """Convert a WingConfiguration to the v2 ASB wing schema."""
    ted_original_tip_values = _normalize_wing_config_ted_for_asb(wing_config)
    try:
        asb_wing = wing_config.asb_wing(scale=scale)
    finally:
        _restore_wing_config_ted_after_asb(ted_original_tip_values)

    section_data = _wing_configuration_sections(wing_config)
    x_secs = []

    for index, x_sec in enumerate(asb_wing.xsecs):
        control_surface = _extract_control_surface_from_xsec(x_sec)
        section_airfoil_ref = _resolve_airfoil_ref_for_index(index, section_data, x_sec)

        trailing_edge_device = None
        spare_list = None
        x_sec_type = None
        tip_type = None
        number_interpolation_points = None

        segment = wing_config.segments[index] if index < len(wing_config.segments) else None
        if segment is not None:
            (
                trailing_edge_device, spare_list, control_surface,
                x_sec_type, tip_type, number_interpolation_points,
            ) = _build_segment_details(segment, control_surface)

        x_secs.append(
            schemas.WingXSecSchema(
                xyz_le=[float(value) for value in x_sec.xyz_le],
                chord=float(x_sec.chord),
                twist=float(x_sec.twist),
                airfoil=_normalize_airfoil_reference_for_schema(section_airfoil_ref),
                control_surface=control_surface,
                x_sec_type=x_sec_type,
                tip_type=tip_type,
                number_interpolation_points=number_interpolation_points,
                spare_list=spare_list,
                trailing_edge_device=trailing_edge_device,
            )
        )

    return schemas.AsbWingSchema(
        name=wing_name,
        symmetric=bool(asb_wing.symmetric),
        x_secs=x_secs,
    )


def wing_config_to_wing_model(
    wing_config: WingConfiguration,
    wing_name: str,
    scale: float = 1.0,
) -> WingModel:
    """
    Convert a WingConfiguration to the persisted WingModel representation.

    Args:
        wing_config: Source wing configuration.
        wing_name: Name to assign to the resulting wing model.
        scale: Scaling used when creating the internal ASB wing (e.g. 0.001 for mm->m).
    """
    asb_wing_schema = wing_config_to_asb_wing_schema(
        wing_config=wing_config,
        wing_name=wing_name,
        scale=scale,
    )
    return WingModel.from_dict(name=wing_name, data=asb_wing_schema.model_dump())
