"""
Wing Service - Business logic for wing and cross-section operations.

This module contains the core logic for wing management,
separated from HTTP concerns for better testability and reusability.
"""

import logging
from datetime import datetime
from typing import List, Optional

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
    ControlSurfaceModel,
)
from app.schemas.wing import Wing as WingConfigurationSchema
from app.services.create_wing_configuration import create_wing_configuration
from app.converters.model_schema_converters import wingConfigToWingModel

logger = logging.getLogger(__name__)


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
    wing_data: schemas.AsbWingSchema
) -> None:
    """
    Create a new wing for an aeroplane.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        ValidationError: If the wing name already exists.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            plane = get_aeroplane_or_raise(db, aeroplane_uuid)
            
            if any(w.name == wing_name for w in plane.wings):
                raise ValidationError(
                    message="Wing name must be unique for this aeroplane",
                    details={"wing_name": wing_name}
                )
            
            wing = WingModel.from_dict(name=wing_name, data=wing_data.model_dump())
            plane.wings.append(wing)
            db.add(wing)
            plane.updated_at = datetime.now()
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
        with db.begin():
            plane = get_aeroplane_or_raise(db, aeroplane_uuid)

            if any(w.name == wing_name for w in plane.wings):
                raise ValidationError(
                    message="Wing name must be unique for this aeroplane",
                    details={"wing_name": wing_name},
                )

            wing_configuration = create_wing_configuration(wing_config_data)
            wing_model = wingConfigToWingModel(
                wing_config=wing_configuration,
                wing_name=wing_name,
                scale=scale,
            )
            plane.wings.append(wing_model)
            db.add(wing_model)
            plane.updated_at = datetime.now()
    except (NotFoundError, ValidationError):
        raise
    except (ValueError, TypeError) as e:
        raise ValidationError(message=f"Invalid WingConfiguration payload: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating wing from WingConfiguration: {e}")
        raise InternalError(message=f"Database error: {e}")


def update_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    wing_data: schemas.AsbWingSchema
) -> None:
    """
    Update an existing wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            plane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(plane, wing_name)
            
            new_wing = WingModel.from_dict(name=wing_name, data=wing_data.model_dump())
            plane.wings.remove(wing)
            plane.wings.append(new_wing)
            plane.updated_at = datetime.now()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when updating wing: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing(db: Session, aeroplane_uuid, wing_name: str) -> schemas.AsbWingSchema:
    """
    Get a wing as schema.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(plane, wing_name)
        return schemas.AsbWingSchema.model_validate(wing, from_attributes=True)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_wing(db: Session, aeroplane_uuid, wing_name: str) -> None:
    """
    Delete a wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            plane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(plane, wing_name)
            db.delete(wing)
            plane.updated_at = datetime.now()
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
) -> List[schemas.WingXSecSchema]:
    """
    Get all cross-sections for a wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        return [
            schemas.WingXSecSchema.model_validate(xs, from_attributes=True)
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
        with db.begin():
            aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(aeroplane, wing_name)
            wing.x_secs.clear()
            aeroplane.updated_at = datetime.now()
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
) -> schemas.WingXSecSchema:
    """
    Get a specific cross-section by index.
    
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
                message="Cross-section not found",
                details={"index": index, "wing_name": wing_name}
            )
        
        return schemas.WingXSecSchema.model_validate(x_secs[index], from_attributes=True)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


def _build_cross_section_model(
    xsec_data: schemas.WingXSecSchema,
    sort_index: int,
    is_terminal_xsec: bool,
    fallback_control_surface: Optional[ControlSurfaceModel] = None,
) -> WingXSecModel:
    data = xsec_data.model_dump()

    control_surface = WingModel._as_payload(data.pop("control_surface", None))
    trailing_edge_device = WingModel._as_payload(data.pop("trailing_edge_device", None))
    spare_list = data.pop("spare_list", None)
    x_sec_type = data.pop("x_sec_type", None)
    tip_type = data.pop("tip_type", None)
    number_interpolation_points = data.pop("number_interpolation_points", None)

    fallback_cs_payload = WingModel._as_payload(fallback_control_surface)

    if is_terminal_xsec:
        trailing_edge_device = None
        spare_list = None
        x_sec_type = None
        tip_type = None
        number_interpolation_points = None
    elif trailing_edge_device is not None:
        control_surface = WingModel._control_surface_from_ted(
            trailing_edge_device,
            fallback=control_surface or fallback_cs_payload,
        )
    elif control_surface is not None:
        trailing_edge_device = WingModel._minimal_ted_from_control_surface(control_surface)
    elif fallback_cs_payload is not None:
        control_surface = fallback_cs_payload
        trailing_edge_device = WingModel._minimal_ted_from_control_surface(fallback_cs_payload)

    new_xsec = WingXSecModel(sort_index=sort_index, **data)

    if control_surface is not None:
        new_xsec.control_surface = ControlSurfaceModel(**control_surface)

    detail_required = any(
        value is not None
        for value in [
            x_sec_type,
            tip_type,
            number_interpolation_points,
            trailing_edge_device,
            spare_list,
        ]
    )
    if detail_required:
        detail = WingXSecDetailModel(
            x_sec_type=x_sec_type,
            tip_type=tip_type,
            number_interpolation_points=number_interpolation_points,
        )

        for spare_index, spare in enumerate(spare_list or []):
            spare_payload = WingModel._as_payload(spare)
            if spare_payload is None:
                continue
            detail.spares.append(WingXSecSpareModel(sort_index=spare_index, **spare_payload))

        ted_model = WingModel._build_ted_model(trailing_edge_device)
        if ted_model is not None:
            detail.trailing_edge_device = ted_model

        new_xsec.detail = detail

    return new_xsec


def create_cross_section(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    index: int,
    xsec_data: schemas.WingXSecSchema
) -> None:
    """
    Create a new cross-section at the specified index.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
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
    xsec_data: schemas.WingXSecSchema
) -> None:
    """
    Update an existing cross-section.
    
    Raises:
        NotFoundError: If the aeroplane, wing, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(aeroplane, wing_name)
            x_secs = wing.x_secs
            
            if index < 0 or index >= len(x_secs):
                raise NotFoundError(
                    message="Cross-section not found",
                    details={"index": index}
                )

            existing_xsec = x_secs[index]
            fallback_control_surface = existing_xsec.control_surface if existing_xsec.control_surface is not None else None
            new_xsec = _build_cross_section_model(
                xsec_data=xsec_data,
                sort_index=index,
                is_terminal_xsec=(index == len(x_secs) - 1),
                fallback_control_surface=fallback_control_surface,
            )
            
            wing.x_secs[index] = new_xsec
            aeroplane.updated_at = datetime.now()
    except NotFoundError:
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
        with db.begin():
            aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(aeroplane, wing_name)
            x_secs = wing.x_secs
            
            if index < 0 or index >= len(x_secs):
                raise NotFoundError(
                    message="Cross-section not found",
                    details={"index": index}
                )
            
            xsec = x_secs.pop(index)
            db.delete(xsec)
            aeroplane.updated_at = datetime.now()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting cross-section: {e}")
        raise InternalError(message=f"Database error: {e}")


# Control surface operations

def get_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int
) -> schemas.ControlSurfaceSchema:
    """
    Get the control surface for a cross-section.
    
    Raises:
        NotFoundError: If the aeroplane, wing, cross-section, or control surface does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        wing = get_wing_or_raise(aeroplane, wing_name)
        x_secs = wing.x_secs
        
        if xsec_index < 0 or xsec_index >= len(x_secs):
            raise NotFoundError(
                message="Cross-section not found",
                details={"index": xsec_index}
            )
        
        cs = x_secs[xsec_index].control_surface
        if not cs:
            raise NotFoundError(
                message="Control surface not found",
                details={"xsec_index": xsec_index}
            )
        
        return schemas.ControlSurfaceSchema.model_validate(cs, from_attributes=True)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting control surface: {e}")
        raise InternalError(message=f"Database error: {e}")


def upsert_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int,
    cs_data: schemas.ControlSurfaceSchema
) -> None:
    """
    Create or update a control surface.
    
    Raises:
        NotFoundError: If the aeroplane, wing, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(aeroplane, wing_name)
            x_secs = wing.x_secs
            
            if xsec_index < 0 or xsec_index >= len(x_secs):
                raise NotFoundError(
                    message="Cross-section not found",
                    details={"index": xsec_index}
                )
            
            xs = x_secs[xsec_index]
            data = cs_data.model_dump()
            
            if xs.control_surface:
                for key, value in data.items():
                    setattr(xs.control_surface, key, value)
            else:
                cs = ControlSurfaceModel(**data)
                xs.control_surface = cs
                db.add(cs)
            
            aeroplane.updated_at = datetime.now()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when upserting control surface: {e}")
        raise InternalError(message=f"Database error: {e}")


def delete_control_surface(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    xsec_index: int
) -> None:
    """
    Delete a control surface.
    
    Raises:
        NotFoundError: If the aeroplane, wing, cross-section, or control surface does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
            wing = get_wing_or_raise(aeroplane, wing_name)
            x_secs = wing.x_secs
            
            if xsec_index < 0 or xsec_index >= len(x_secs):
                raise NotFoundError(
                    message="Cross-section not found",
                    details={"index": xsec_index}
                )
            
            xs = x_secs[xsec_index]
            cs = xs.control_surface
            if not cs:
                raise NotFoundError(
                    message="Control surface not found",
                    details={"xsec_index": xsec_index}
                )
            
            xs.control_surface = None
            db.delete(cs)
            aeroplane.updated_at = datetime.now()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting control surface: {e}")
        raise InternalError(message=f"Database error: {e}")
