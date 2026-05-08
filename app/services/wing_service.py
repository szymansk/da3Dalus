"""
Wing Service - Business logic for wing and cross-section operations.

This module contains the core logic for wing management,
separated from HTTP concerns for better testability and reusability.
"""

import logging
from datetime import datetime
from typing import List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import NotFoundError, ValidationError, InternalError
from app.models.aeroplanemodel import (
    AeroplaneModel,
    WingModel,
    WingXSecModel,
    WingXSecDetailModel,
    WingXSecSpareModel,
    WingXSecTrailingEdgeDeviceModel,
    WingXSecTedServoModel,
)
from app.schemas.Servo import Servo as ServoSchema
from app.schemas.wing import Wing as WingConfigurationSchema
from app.services.create_wing_configuration import create_wing_configuration
from app.converters.model_schema_converters import wing_config_to_wing_model, wing_model_to_wing_config

logger = logging.getLogger(__name__)

# --- Shared error messages (S1192) ---
_ERR_XSEC_NOT_FOUND = "Cross-section not found"
_ERR_TED_NOT_FOUND = "Trailing-edge device not found on this cross-section."

# --- Unit conversion constant (mm → m) ---
_MM_TO_M = 0.001


_M_TO_MM = 1000.0


def _convert_spare_to_meters(spare: schemas.SpareDetailSchema) -> schemas.SpareDetailSchema:
    """Convert SpareDetailSchema dimensional fields from mm (DB storage) to meters (API response).

    spare_vector is dimensionless (unit direction vector) and is NOT scaled.
    """
    return spare.model_copy(
        update={
            "spare_support_dimension_width": spare.spare_support_dimension_width * _MM_TO_M,
            "spare_support_dimension_height": spare.spare_support_dimension_height * _MM_TO_M,
            "spare_length": spare.spare_length * _MM_TO_M if spare.spare_length is not None else None,
            "spare_start": spare.spare_start * _MM_TO_M,
            "spare_origin": [v * _MM_TO_M for v in spare.spare_origin] if spare.spare_origin is not None else None,
        }
    )


def _convert_spare_to_mm(spare: schemas.SpareDetailSchema) -> schemas.SpareDetailSchema:
    """Convert SpareDetailSchema dimensional fields from meters (API input) to mm (DB storage).

    spare_origin is converted as a defensive fallback for when _recompute_spare_vectors
    fails silently (ImportError on linux/aarch64, FileNotFoundError for missing airfoils).
    spare_vector is dimensionless (unit direction vector) and is NOT scaled.
    """
    return spare.model_copy(
        update={
            "spare_support_dimension_width": spare.spare_support_dimension_width * _M_TO_MM,
            "spare_support_dimension_height": spare.spare_support_dimension_height * _M_TO_MM,
            "spare_length": spare.spare_length * _M_TO_MM if spare.spare_length is not None else None,
            "spare_start": spare.spare_start * _M_TO_MM,
            "spare_origin": [v * _M_TO_MM for v in spare.spare_origin] if spare.spare_origin is not None else None,
        }
    )


def _convert_xsec_spares_to_meters(
    xsec: schemas.WingXSecReadSchema,
) -> schemas.WingXSecReadSchema:
    """Convert spare detail fields on a cross-section schema from mm to meters."""
    if not xsec.spare_list:
        return xsec
    return xsec.model_copy(
        update={"spare_list": [_convert_spare_to_meters(s) for s in xsec.spare_list]}
    )


def get_aeroplane_or_raise(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """
    Get an aeroplane by UUID or raise NotFoundError.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = db.query(AeroplaneModel).filter(
            AeroplaneModel.uuid == aeroplane_uuid
        ).first()
        
        if not aeroplane:
            raise NotFoundError(
                message="Aeroplane not found",
                details={"aeroplane_id": str(aeroplane_uuid)}
            )
        return aeroplane
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing_or_raise(aeroplane: AeroplaneModel, wing_name: str) -> WingModel:
    """
    Get a wing by name from an aeroplane or raise NotFoundError.
    
    Raises:
        NotFoundError: If the wing does not exist.
    """
    wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
    if not wing:
        raise NotFoundError(
            message="Wing not found",
            details={"wing_name": wing_name, "aeroplane_id": str(aeroplane.uuid)}
        )
    return wing


def _get_xsec_or_raise(wing: WingModel, index: int) -> WingXSecModel:
    x_secs = wing.x_secs
    if index < 0 or index >= len(x_secs):
        raise NotFoundError(
            message=_ERR_XSEC_NOT_FOUND,
            details={"index": index, "wing_name": wing.name},
        )
    return x_secs[index]


def _assert_non_terminal_xsec_or_raise(xsec_index: int, xsec_count: int) -> None:
    if xsec_index == xsec_count - 1:
        raise ValidationError(
            message="Segment-specific data is not allowed on the terminal cross-section.",
            details={"index": xsec_index},
        )


def get_wing_design_model(db: Session, aeroplane_uuid, wing_name: str) -> str | None:
    """Return the design_model of an existing wing, or None if the wing does not exist."""
    from sqlalchemy import select

    try:
        plane_exists = db.execute(
            select(AeroplaneModel.id).filter(AeroplaneModel.uuid == aeroplane_uuid)
        ).scalar_one_or_none()
        if plane_exists is None:
            raise NotFoundError(
                message="Aeroplane not found",
                details={"aeroplane_id": str(aeroplane_uuid)},
            )

        return db.execute(
            select(WingModel.design_model)
            .join(AeroplaneModel, WingModel.aeroplane_id == AeroplaneModel.id)
            .filter(AeroplaneModel.uuid == aeroplane_uuid, WingModel.name == wing_name)
        ).scalar_one_or_none()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing design_model: {e}")
        raise InternalError(message="Failed to query wing design model")


def _ensure_segment_detail_or_raise(
    x_sec: WingXSecModel,
    xsec_index: int,
    xsec_count: int,
) -> WingXSecDetailModel:
    _assert_non_terminal_xsec_or_raise(xsec_index, xsec_count)
    if x_sec.detail is None:
        x_sec.detail = WingXSecDetailModel()
    return x_sec.detail


def _materialize_wing_relations(wing: WingModel) -> None:
    """
    Force-load nested wing relationships while a DB session is active.

    This avoids lazy-loading attempts during schema serialization after session scope ends.
    """
    for x_sec in wing.x_secs or []:
        detail = x_sec.detail
        if detail is None:
            continue
        _ = list(detail.spares or [])
        ted = detail.trailing_edge_device
        if ted is not None:
            _ = ted.servo_data


def _serialize_control_surface_from_ted(
    ted: WingXSecTrailingEdgeDeviceModel,
) -> schemas.ControlSurfaceSchema:
    projected = WingModel._control_surface_from_ted(ted)
    return schemas.ControlSurfaceSchema.model_validate(projected)


def _ensure_ted_exists(detail: WingXSecDetailModel) -> WingXSecTrailingEdgeDeviceModel:
    if detail.trailing_edge_device is None:
        detail.trailing_edge_device = WingXSecTrailingEdgeDeviceModel()
    return detail.trailing_edge_device


def _existing_ted_for_control_surface_or_raise(
    wing: WingModel,
    x_sec: WingXSecModel,
    xsec_index: int,
    wing_name: str,
) -> WingXSecTrailingEdgeDeviceModel:
    _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
    ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
    if ted is None:
        raise ValidationError(
            message="Control surface must exist before CAD details can be modified.",
            details={"index": xsec_index, "wing_name": wing_name},
        )
    return ted


def _serialize_control_surface_cad_details(
    ted: WingXSecTrailingEdgeDeviceModel,
) -> schemas.ControlSurfaceCadDetailsSchema:
    return schemas.ControlSurfaceCadDetailsSchema(
        rel_chord_tip=ted.rel_chord_tip,
        hinge_spacing=ted.hinge_spacing,
        side_spacing_root=ted.side_spacing_root,
        side_spacing_tip=ted.side_spacing_tip,
        servo_placement=ted.servo_placement,
        rel_chord_servo_position=ted.rel_chord_servo_position,
        rel_length_servo_position=ted.rel_length_servo_position,
        positive_deflection_deg=ted.positive_deflection_deg,
        negative_deflection_deg=ted.negative_deflection_deg,
        trailing_edge_offset_factor=ted.trailing_edge_offset_factor,
        hinge_type=ted.hinge_type,
    )


def list_wing_names(db: Session, aeroplane_uuid) -> List[str]:
    """
    Get list of wing names for an aeroplane.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
    return [w.name for w in aeroplane.wings]


def create_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    wing_data: schemas.AsbWingGeometryWriteSchema
) -> None:
    """
    Create a new wing for an aeroplane.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        ValidationError: If the wing name already exists.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
            
        if any(w.name == wing_name for w in plane.wings):
            raise ValidationError(
                message="Wing name must be unique for this aeroplane",
                details={"wing_name": wing_name}
            )
            
        wing = WingModel.from_dict(name=wing_name, data=wing_data.model_dump())
        wing.design_model = "asb"
        plane.wings.append(wing)
        db.add(wing)
        plane.updated_at = datetime.now()

        # Auto-sync: create group in component tree (gh#108)
        from app.services.component_tree_service import sync_group_for_wing
        sync_group_for_wing(db, str(aeroplane_uuid), wing_name)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating wing: {e}")
        raise InternalError(message=f"Database error: {e}")


def create_wing_from_wing_configuration(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    wing_config_data: WingConfigurationSchema,
    scale: float = 0.001,
) -> None:
    """
    Create a new wing for an aeroplane from WingConfiguration JSON.

    The WingConfiguration schema is interpreted in millimeters by default and converted
    to ASB/DB units via `scale` (default 0.001 -> meters).

    Raises:
        NotFoundError: If the aeroplane does not exist.
        ValidationError: If the wing name already exists or input is invalid.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)

        if any(w.name == wing_name for w in plane.wings):
            raise ValidationError(
                message="Wing name must be unique for this aeroplane",
                details={"wing_name": wing_name},
            )

        wing_configuration = create_wing_configuration(wing_config_data)
        wing_model = wing_config_to_wing_model(
            wing_config=wing_configuration,
            wing_name=wing_name,
            scale=scale,
        )
        wing_model.design_model = "wc"
        plane.wings.append(wing_model)
        db.add(wing_model)
        db.flush()
        # Recompute spare_origin/spare_vector and store in mm (gh-402)
        _recompute_spare_vectors(wing_model)
        plane.updated_at = datetime.now()

        # Auto-sync: create group in component tree (gh#108)
        from app.services.component_tree_service import sync_group_for_wing
        sync_group_for_wing(db, str(aeroplane_uuid), wing_name)
    except (NotFoundError, ValidationError):
        raise
    except (ValueError, TypeError) as e:
        raise ValidationError(message=f"Invalid WingConfiguration payload: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating wing from WingConfiguration: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing_as_wingconfig(db: Session, aeroplane_uuid, wing_name: str) -> dict:
    """Return the wing converted back to WingConfiguration format.

    Uses the roundtrip converter wing_model_to_wing_config to produce
    the segment-based representation with root/tip airfoils,
    length, sweep, dihedral — without any estimation or loss.
    """
    aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
    wing = get_wing_or_raise(aeroplane, wing_name)
    try:
        wing_config = wing_model_to_wing_config(wing, scale=1000.0)
    except Exception as exc:
        logger.error("Failed to convert wing %s to WingConfig: %s", wing_name, exc)
        raise InternalError(
            message=f"Wing conversion failed for '{wing_name}': {exc}",
        )
    return _wing_config_to_dict(wing_config)


def _wing_config_to_dict(wc) -> dict:
    """Serialize a cad_designer WingConfiguration to a JSON-safe dict."""
    from app.converters.model_schema_converters import (
        _trailing_edge_device_to_schema,
        _spare_to_schema,
    )

    segments = []
    for seg in wc.segments:
        seg_dict: dict = {
            "root_airfoil": {
                "airfoil": seg.root_airfoil.airfoil,
                "chord": seg.root_airfoil.chord,
                "dihedral_as_rotation_in_degrees": seg.root_airfoil.dihedral_as_rotation_in_degrees or 0,
                "incidence": seg.root_airfoil.incidence or 0,
            },
            "tip_airfoil": {
                "airfoil": seg.tip_airfoil.airfoil,
                "chord": seg.tip_airfoil.chord,
                "dihedral_as_rotation_in_degrees": seg.tip_airfoil.dihedral_as_rotation_in_degrees or 0,
                "incidence": seg.tip_airfoil.incidence or 0,
            },
            "length": seg.length,
            "sweep": seg.sweep,
            "number_interpolation_points": seg.number_interpolation_points,
            "tip_type": getattr(seg, 'tip_type', None),
        }

        # Preserve spars (gh#107)
        if seg.spare_list:
            seg_dict["spare_list"] = [
                _spare_to_schema(spare).model_dump() for spare in seg.spare_list
            ]

        # Preserve TED (gh#107)
        if seg.trailing_edge_device is not None:
            seg_dict["trailing_edge_device"] = _trailing_edge_device_to_schema(
                seg.trailing_edge_device,
            ).model_dump()

        segments.append(seg_dict)

    return {
        "segments": segments,
        "nose_pnt": list(wc.nose_pnt) if wc.nose_pnt else [0, 0, 0],
        "symmetric": wc.symmetric,
        "parameters": wc.parameters if hasattr(wc, 'parameters') else "relative",
    }


def put_wing_as_wingconfig(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    wing_config_data: WingConfigurationSchema,
    scale: float = 0.001,
) -> None:
    """Replace an existing wing from WingConfiguration JSON.

    Unlike create_wing_from_wing_configuration, this deletes
    the existing wing first (idempotent PUT semantics).
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        # Remove existing wing if present
        existing = next((w for w in plane.wings if w.name == wing_name), None)
        if existing:
            db.delete(existing)
            db.flush()

        wing_configuration = create_wing_configuration(wing_config_data)
        wing_model = wing_config_to_wing_model(
            wing_config=wing_configuration,
            wing_name=wing_name,
            scale=scale,
        )
        wing_model.design_model = "wc"
        plane.wings.append(wing_model)
        db.add(wing_model)
        db.flush()
        # Recompute spare_origin/spare_vector and store in mm (gh-402)
        _recompute_spare_vectors(wing_model)
        plane.updated_at = datetime.now()

        # Auto-sync: ensure group in component tree (gh#108)
        from app.services.component_tree_service import sync_group_for_wing
        sync_group_for_wing(db, str(aeroplane_uuid), wing_name)
    except (NotFoundError, ValidationError):
        raise
    except (ValueError, TypeError) as e:
        raise ValidationError(message=f"Invalid WingConfiguration payload: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Database error in put_wing_as_wingconfig: {e}")
        raise InternalError(message=f"Database error: {e}")


def update_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    wing_data: schemas.AsbWingGeometryWriteSchema
) -> None:
    """
    Update an existing wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(plane, wing_name)
            
        new_wing = WingModel.from_dict(name=wing_name, data=wing_data.model_dump())
        new_wing.design_model = "asb"
        plane.wings.remove(wing)
        plane.wings.append(new_wing)
        plane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating wing: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing(db: Session, aeroplane_uuid, wing_name: str) -> schemas.AsbWingReadSchema:
    """
    Get a wing as schema.

    All values in the response use meters — spare detail fields stored in mm
    are converted at read time (gh-366).

    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(plane, wing_name)
        _materialize_wing_relations(wing)
        schema = schemas.AsbWingReadSchema.model_validate(wing, from_attributes=True)
        # Convert spare detail fields from mm (DB) to meters (API)
        converted_xsecs = [_convert_xsec_spares_to_meters(xs) for xs in schema.x_secs]
        return schema.model_copy(update={"x_secs": converted_xsecs})
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing: {e}")
        raise InternalError(message=f"Database error: {e}")
    except Exception as exc:
        logger.error("Failed to serialize wing %s: %s", wing_name, exc)
        raise InternalError(message=f"Wing data conversion failed for '{wing_name}': {exc}")


def delete_wing(db: Session, aeroplane_uuid, wing_name: str) -> None:
    """
    Delete a wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(plane, wing_name)
        db.delete(wing)
        plane.updated_at = datetime.now()

        # Auto-sync: remove wing group + servos from component tree (gh#108)
        from app.services.component_tree_service import delete_synced_nodes
        delete_synced_nodes(db, str(aeroplane_uuid), f"wing:{wing_name}")
        delete_synced_nodes(db, str(aeroplane_uuid), f"servo:{wing_name}:")
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting wing: {e}")
        raise InternalError(message=f"Database error: {e}")


# Cross-section operations

def get_wing_cross_sections(
    db: Session,
    aeroplane_uuid,
    wing_name: str
) -> List[schemas.WingXSecReadSchema]:
    """
    Get all cross-sections for a wing.

    Spare detail fields are converted from mm (DB) to meters (gh-366).

    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        _materialize_wing_relations(wing)
        return [
            _convert_xsec_spares_to_meters(
                schemas.WingXSecReadSchema.model_validate(xs, from_attributes=True)
            )
            for xs in wing.x_secs
        ]
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting cross-sections: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_all_cross_sections(db: Session, aeroplane_uuid, wing_name: str) -> None:
    """
    Delete all cross-sections from a wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        wing.x_secs.clear()
        aeroplane.updated_at = datetime.now()
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting cross-sections: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_cross_section(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    index: int
) -> schemas.WingXSecReadSchema:
    """
    Get a specific cross-section by index.

    Spare detail fields are converted from mm (DB) to meters (gh-366).

    Raises:
        NotFoundError: If the aeroplane, wing, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        _materialize_wing_relations(wing)
        x_sec = _get_xsec_or_raise(wing, index)
        return _convert_xsec_spares_to_meters(
            schemas.WingXSecReadSchema.model_validate(x_sec, from_attributes=True)
        )
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


def _build_cross_section_model(
    xsec_data: schemas.WingXSecGeometryWriteSchema,
    sort_index: int,
    is_terminal_xsec: bool,
) -> WingXSecModel:
    data = xsec_data.model_dump()

    # The three segment-metadata fields live on ``WingXSecDetailModel``,
    # not directly on ``WingXSecModel``. Pop them before constructing
    # the xsec model, then attach a detail row if any were set.
    x_sec_type = data.pop("x_sec_type", None)
    tip_type = data.pop("tip_type", None)
    number_interpolation_points = data.pop("number_interpolation_points", None)

    new_xsec = WingXSecModel(sort_index=sort_index, **data)

    if is_terminal_xsec:
        # Terminal x_sec does not carry segment metadata by
        # design; silently drop to match the AsbWingSchema invariant.
        return new_xsec

    if any(
        value is not None
        for value in (x_sec_type, tip_type, number_interpolation_points)
    ):
        new_xsec.detail = WingXSecDetailModel(
            x_sec_type=x_sec_type,
            tip_type=tip_type,
            number_interpolation_points=number_interpolation_points,
        )

    return new_xsec


def create_cross_section(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    index: int,
    xsec_data: schemas.WingXSecGeometryWriteSchema
) -> None:
    """
    Create a new cross-section at the specified index.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)

        existing = wing.x_secs
        if index == -1 or index >= len(existing):
            insertion_index = len(existing)
        else:
            insertion_index = index

        new_xsec = _build_cross_section_model(
            xsec_data=xsec_data,
            sort_index=insertion_index,
            is_terminal_xsec=(insertion_index == len(existing)),
        )
            
        for xs in existing[insertion_index:]:
            xs.sort_index = xs.sort_index + 1
            db.add(xs)

        if insertion_index == len(existing):
            wing.x_secs.append(new_xsec)
        else:
            wing.x_secs.insert(insertion_index, new_xsec)

        aeroplane.updated_at = datetime.now()
        db.add(new_xsec)
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


def update_cross_section(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    index: int,
    xsec_data: schemas.WingXSecGeometryWriteSchema
) -> None:
    """
    Update an existing cross-section.

    Writes the four ASB-minimum fields (``xyz_le``, ``chord``,
    ``twist``, ``airfoil``) unconditionally. The three optional
    segment-metadata fields (``wing_segment_type``, ``tip_type``,
    ``number_interpolation_points``) are only written when the
    payload provides a non-``None`` value so that partial updates
    do not accidentally clear an existing detail. The terminal
    x_sec is special-cased: per the ``AsbWingSchema`` invariant,
    segment-level metadata is not allowed on the last x_sec and
    is silently dropped here too.

    Raises:
        NotFoundError: If the aeroplane, wing, or cross-section does not exist.
        ValidationError: If the payload tries to set segment metadata on the terminal x_sec.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_secs = wing.x_secs

        if index < 0 or index >= len(x_secs):
            raise NotFoundError(
                message=_ERR_XSEC_NOT_FOUND,
                details={"index": index}
            )
        xsec = x_secs[index]
        xsec.xyz_le = xsec_data.xyz_le
        xsec.chord = xsec_data.chord
        xsec.twist = xsec_data.twist
        xsec.airfoil = str(xsec_data.airfoil)

        # Optional segment metadata — only write if the client
        # sent something, so that a geometry-only PUT doesn't
        # wipe previously-set fields.
        has_metadata = any(
            value is not None
            for value in (
                xsec_data.x_sec_type,
                xsec_data.tip_type,
                xsec_data.number_interpolation_points,
            )
        )
        if has_metadata:
            is_terminal = index == len(x_secs) - 1
            if is_terminal:
                raise ValidationError(
                    message=(
                        "Segment-specific fields (x_sec_type, "
                        "tip_type, number_interpolation_points) are not "
                        "allowed on the last cross-section."
                    ),
                    details={"index": index},
                )
            if xsec.detail is None:
                xsec.detail = WingXSecDetailModel()
            if xsec_data.x_sec_type is not None:
                xsec.detail.x_sec_type = xsec_data.x_sec_type
            if xsec_data.tip_type is not None:
                xsec.detail.tip_type = xsec_data.tip_type
            if xsec_data.number_interpolation_points is not None:
                xsec.detail.number_interpolation_points = (
                    xsec_data.number_interpolation_points
                )

        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_cross_section(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    index: int
) -> None:
    """
    Delete a cross-section.
    
    Raises:
        NotFoundError: If the aeroplane, wing, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_secs = wing.x_secs
            
        if index < 0 or index >= len(x_secs):
            raise NotFoundError(
                message=_ERR_XSEC_NOT_FOUND,
                details={"index": index}
            )
            
        xsec = x_secs.pop(index)
        db.delete(xsec)
        aeroplane.updated_at = datetime.now()
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


def _sync_spares_for_xsec(db_xsec, segment) -> None:
    """Copy computed spare_vector/spare_origin from a WingConfiguration segment
    back to the corresponding DB cross-section's spar records.

    spare_origin is computed in meters (scale=1.0) and scaled to mm for DB storage.
    spare_vector is a dimensionless unit direction vector and is stored as-is.
    """
    for spare_idx, spare in enumerate(segment.spare_list or []):
        if spare_idx >= len(db_xsec.detail.spares):
            break
        db_spare = db_xsec.detail.spares[spare_idx]
        if spare.spare_vector is not None:
            vec = spare.spare_vector.toTuple() if hasattr(spare.spare_vector, "toTuple") else spare.spare_vector
            db_spare.spare_vector = [float(v) for v in vec]
        if spare.spare_origin is not None:
            orig = spare.spare_origin.toTuple() if hasattr(spare.spare_origin, "toTuple") else spare.spare_origin
            db_spare.spare_origin = [float(v) * _M_TO_MM for v in orig]


def _recompute_spare_vectors(wing: WingModel) -> None:
    """Rebuild WingConfiguration to compute spare_vector/spare_origin for all spars,
    then persist the computed values back to the DB spar records.

    Uses ``scale=1.0`` so spare_origin is in metres, then ``_sync_spares_for_xsec``
    converts origin to mm. spare_vector is a dimensionless unit direction vector
    and is stored as-is (gh-402).
    """
    try:
        wing_config = wing_model_to_wing_config(wing, scale=1.0)

        for seg_idx, segment in enumerate(wing_config.segments or []):
            if seg_idx >= len(wing.x_secs) - 1:
                break
            db_xsec = wing.x_secs[seg_idx]
            if db_xsec.detail is None:
                continue
            _sync_spares_for_xsec(db_xsec, segment)
    except (ImportError, FileNotFoundError) as e:
        logger.warning("Skipping spare vector computation: %s", e)


def get_spares(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> List[schemas.SpareDetailSchema]:
    """
    Get all spars for a wing cross-section.

    Values are returned in meters (converted from mm DB storage, gh-366).
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        _materialize_wing_relations(wing)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        spares = x_sec.detail.spares if x_sec.detail is not None else []
        return [
            _convert_spare_to_meters(
                schemas.SpareDetailSchema.model_validate(spare, from_attributes=True)
            )
            for spare in spares
        ]
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting spars: {e}")
        raise InternalError(message=f"Database error: {e}")


def create_spare(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    spare_data: schemas.SpareDetailSchema,
) -> None:
    """
    Create a spar on a wing cross-section.

    Input values are in meters (API convention). They are converted to mm
    for DB storage (gh-366).

    Spars are segment-specific and therefore cannot be assigned to the terminal cross-section.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        detail = _ensure_segment_detail_or_raise(x_sec, xsec_index, len(wing.x_secs))

        spare_payload = _convert_spare_to_mm(spare_data).model_dump()
        spare = WingXSecSpareModel(
            sort_index=len(detail.spares),
            **spare_payload,
        )
        detail.spares.append(spare)
        db.add(spare)
        db.flush()
        _recompute_spare_vectors(wing)
        aeroplane.updated_at = datetime.now()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating spar: {e}")
        raise InternalError(message=f"Database error: {e}")


def update_spare(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    spar_index: int,
    spare_data: schemas.SpareDetailSchema,
) -> None:
    """Replace a spar at the given index on a wing cross-section.

    Input values are in meters (API convention). They are converted to mm
    for DB storage (gh-366).
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        detail = _ensure_segment_detail_or_raise(x_sec, xsec_index, len(wing.x_secs))
        if spar_index < 0 or spar_index >= len(detail.spares):
            raise NotFoundError(
                message=f"Spar index {spar_index} out of range (0..{len(detail.spares) - 1}).",
                details={"spar_index": spar_index},
            )
        spare = detail.spares[spar_index]
        for key, value in _convert_spare_to_mm(spare_data).model_dump().items():
            setattr(spare, key, value)
        db.flush()
        _recompute_spare_vectors(wing)
        aeroplane.updated_at = datetime.now()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating spar: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_spare(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    spar_index: int,
) -> None:
    """Delete a spar at the given index on a wing cross-section."""
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        detail = _ensure_segment_detail_or_raise(x_sec, xsec_index, len(wing.x_secs))
        if spar_index < 0 or spar_index >= len(detail.spares):
            raise NotFoundError(
                message=f"Spar index {spar_index} out of range (0..{len(detail.spares) - 1}).",
                details={"spar_index": spar_index},
            )
        spare = detail.spares[spar_index]
        db.delete(spare)
        # Re-index remaining spares
        for i, s in enumerate(detail.spares):
            if s is not spare:
                s.sort_index = i if i < spar_index else i - 1
        db.flush()  # ensure delete is visible before recompute
        _recompute_spare_vectors(wing)
        aeroplane.updated_at = datetime.now()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting spar: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> schemas.ControlSurfaceSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message="Control surface not found on this cross-section.",
                details={"index": xsec_index, "wing_name": wing_name},
            )
        return _serialize_control_surface_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting control surface: {e}")
        raise InternalError(message=f"Database error: {e}")


def patch_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    patch: schemas.ControlSurfacePatchSchema,
) -> schemas.ControlSurfaceSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        detail = _ensure_segment_detail_or_raise(x_sec, xsec_index, len(wing.x_secs))
        ted = _ensure_ted_exists(detail)

        if patch.name is not None:
            ted.name = patch.name
        if patch.hinge_point is not None:
            ted.rel_chord_root = patch.hinge_point
            if ted.rel_chord_tip is None:
                ted.rel_chord_tip = patch.hinge_point
        if patch.symmetric is not None:
            ted.symmetric = patch.symmetric
        if patch.deflection is not None:
            ted.deflection_deg = patch.deflection

        db.add(ted)
        aeroplane.updated_at = datetime.now()
        return _serialize_control_surface_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when patching control surface: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> None:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message="Control surface not found on this cross-section.",
                details={"index": xsec_index, "wing_name": wing_name},
            )
        db.delete(ted)
        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting control surface: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_control_surface_cad_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> schemas.ControlSurfaceCadDetailsSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)
        return _serialize_control_surface_cad_details(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting control-surface CAD details: {e}")
        raise InternalError(message=f"Database error: {e}")


def patch_control_surface_cad_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    patch: schemas.ControlSurfaceCadDetailsPatchSchema,
) -> schemas.ControlSurfaceCadDetailsSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)

        for key, value in patch.model_dump(exclude_none=True).items():
            setattr(ted, key, value)

        db.add(ted)
        aeroplane.updated_at = datetime.now()
        return _serialize_control_surface_cad_details(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when patching control-surface CAD details: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_control_surface_cad_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> None:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)

        # Revert to minimal control-surface TED while keeping analysis fields intact.
        ted.rel_chord_tip = ted.rel_chord_root
        ted.hinge_spacing = None
        ted.side_spacing_root = None
        ted.side_spacing_tip = None
        ted.servo_placement = None
        ted.rel_chord_servo_position = None
        ted.rel_length_servo_position = None
        ted.positive_deflection_deg = None
        ted.negative_deflection_deg = None
        ted.trailing_edge_offset_factor = None
        ted.hinge_type = None
        ted.servo_index = None
        ted.servo_data = None

        db.add(ted)
        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting control-surface CAD details: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_trailing_edge_device(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> schemas.TrailingEdgeDeviceDetailSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message=_ERR_TED_NOT_FOUND,
                details={"index": xsec_index, "wing_name": wing_name},
            )
        return schemas.TrailingEdgeDeviceDetailSchema.model_validate(ted, from_attributes=True)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting trailing-edge device: {e}")
        raise InternalError(message=f"Database error: {e}")


def patch_trailing_edge_device(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    patch: schemas.TrailingEdgeDevicePatchSchema,
) -> schemas.TrailingEdgeDeviceDetailSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        detail = _ensure_segment_detail_or_raise(x_sec, xsec_index, len(wing.x_secs))
        ted = _ensure_ted_exists(detail)

        patch_payload = patch.model_dump(exclude_none=True)
        for key, value in patch_payload.items():
            setattr(ted, key, value)

        db.add(ted)
        db.flush()
        db.refresh(ted)
        aeroplane.updated_at = datetime.now()
        return schemas.TrailingEdgeDeviceDetailSchema.model_validate(ted, from_attributes=True)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when patching trailing-edge device: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_trailing_edge_device(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> None:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message=_ERR_TED_NOT_FOUND,
                details={"index": xsec_index, "wing_name": wing_name},
            )
        db.delete(ted)
        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting trailing-edge device: {e}")
        raise InternalError(message=f"Database error: {e}")


def _servo_schema_from_ted(ted: WingXSecTrailingEdgeDeviceModel) -> schemas.TrailingEdgeServoSchema:
    if ted.servo_data is not None:
        servo_value = ServoSchema.model_validate(ted.servo_data, from_attributes=True)
    elif ted.servo_index is not None:
        servo_value = ted.servo_index
    else:
        raise NotFoundError(message="No servo configured for this trailing-edge device.")
    return schemas.TrailingEdgeServoSchema(servo=servo_value)


def _control_surface_servo_details_schema_from_ted(
    ted: WingXSecTrailingEdgeDeviceModel,
) -> schemas.ControlSurfaceServoDetailsSchema:
    if ted.servo_data is not None:
        servo_value = ServoSchema.model_validate(ted.servo_data, from_attributes=True)
    elif ted.servo_index is not None:
        servo_value = ted.servo_index
    else:
        raise NotFoundError(message="No servo configured for this control-surface CAD detail.")
    return schemas.ControlSurfaceServoDetailsSchema(servo=servo_value)


def get_control_surface_cad_details_servo_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> schemas.ControlSurfaceServoDetailsSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)
        return _control_surface_servo_details_schema_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting control-surface CAD servo details: {e}")
        raise InternalError(message=f"Database error: {e}")


def patch_control_surface_cad_details_servo_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    patch: schemas.ControlSurfaceServoDetailsPatchSchema,
) -> schemas.ControlSurfaceServoDetailsSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)

        servo_payload = patch.servo
        if isinstance(servo_payload, int):
            ted.servo_index = servo_payload
            ted.servo_data = None
        else:
            ted.servo_index = None
            servo_dict = servo_payload.model_dump(exclude_none=True)
            if ted.servo_data is None:
                ted.servo_data = WingXSecTedServoModel(**servo_dict)
            else:
                for key, value in servo_dict.items():
                    setattr(ted.servo_data, key, value)

        db.add(ted)
        aeroplane.updated_at = datetime.now()

        # Auto-sync: upsert servo node in component tree (gh#108)
        from app.services.component_tree_service import upsert_synced_servo
        comp_id = None
        if not isinstance(servo_payload, int) and ted.servo_data:
            comp_id = ted.servo_data.component_id
        upsert_synced_servo(
            db, str(aeroplane_uuid), wing_name, xsec_index,
            component_id=comp_id,
            symmetric=wing.symmetric if hasattr(wing, "symmetric") else False,
        )

        return _control_surface_servo_details_schema_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when patching control-surface CAD servo details: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_control_surface_cad_details_servo_details(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> None:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        ted = _existing_ted_for_control_surface_or_raise(wing, x_sec, xsec_index, wing_name)
        if ted.servo_data is None and ted.servo_index is None:
            raise NotFoundError(
                message="No servo configured for this control-surface CAD detail.",
                details={"index": xsec_index, "wing_name": wing_name},
            )
        ted.servo_data = None
        ted.servo_index = None
        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting control-surface CAD servo details: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_trailing_edge_servo(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> schemas.TrailingEdgeServoSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message=_ERR_TED_NOT_FOUND,
                details={"index": xsec_index, "wing_name": wing_name},
            )
        return _servo_schema_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting trailing-edge servo: {e}")
        raise InternalError(message=f"Database error: {e}")


def patch_trailing_edge_servo(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    patch: schemas.TrailingEdgeServoPatchSchema,
) -> schemas.TrailingEdgeServoSchema:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise ValidationError(
                message="Trailing-edge device must exist before assigning a servo.",
                details={"index": xsec_index, "wing_name": wing_name},
            )

        servo_payload = patch.servo
        if isinstance(servo_payload, int):
            ted.servo_index = servo_payload
            ted.servo_data = None
        else:
            ted.servo_index = None
            servo_dict = servo_payload.model_dump(exclude_none=True)
            if ted.servo_data is None:
                ted.servo_data = WingXSecTedServoModel(**servo_dict)
            else:
                for key, value in servo_dict.items():
                    setattr(ted.servo_data, key, value)

        db.add(ted)
        aeroplane.updated_at = datetime.now()
        return _servo_schema_from_ted(ted)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when patching trailing-edge servo: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_trailing_edge_servo(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
) -> None:
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_sec = _get_xsec_or_raise(wing, xsec_index)
        _assert_non_terminal_xsec_or_raise(xsec_index, len(wing.x_secs))
        ted = x_sec.detail.trailing_edge_device if x_sec.detail is not None else None
        if ted is None:
            raise NotFoundError(
                message=_ERR_TED_NOT_FOUND,
                details={"index": xsec_index, "wing_name": wing_name},
            )
        if ted.servo_data is None and ted.servo_index is None:
            raise NotFoundError(
                message="No servo configured for this trailing-edge device.",
                details={"index": xsec_index, "wing_name": wing_name},
            )
        ted.servo_data = None
        ted.servo_index = None
        aeroplane.updated_at = datetime.now()
        db.flush()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting trailing-edge servo: {e}")
        raise InternalError(message=f"Database error: {e}")
