"""
Aeroplane Service - Business logic for aeroplane CRUD operations.

This module contains the core logic for aeroplane management,
separated from HTTP concerns for better testability and reusability.
"""

import logging
from datetime import datetime
from typing import List, OrderedDict

import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import NotFoundError, InternalError, ValidationError
from app.converters.model_schema_converters import fuselage_model_to_fuselage_config, wing_model_to_wing_config
from app.models.aeroplanemodel import AeroplaneModel
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration

logger = logging.getLogger(__name__)


def _to_json_compatible(value):
    if isinstance(value, dict):
        return {key: _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, tuple):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_to_json_compatible(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    return value


def list_all_aeroplanes(db: Session) -> List[AeroplaneModel]:
    """
    Get all aeroplanes ordered by name.
    
    Raises:
        InternalError: If a database error occurs.
    """
    try:
        return db.query(AeroplaneModel).order_by(AeroplaneModel.name).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error when listing aeroplanes: {e}")
        raise InternalError(message=f"Database error: {e}")


def create_aeroplane(db: Session, name: str) -> AeroplaneModel:
    """
    Create a new aeroplane.
    
    Raises:
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = AeroplaneModel(name=name)
        with db.begin():
            db.add(aeroplane)
            db.flush()
            db.refresh(aeroplane)
        return aeroplane
    except SQLAlchemyError as e:
        logger.error(f"Database error when creating aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_aeroplane_by_uuid(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """
    Get an aeroplane by UUID.
    
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


def get_aeroplane_schema(db: Session, aeroplane_uuid) -> schemas.AeroplaneSchema:
    """
    Get an aeroplane as a schema with wings and fuselages.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    aeroplane = get_aeroplane_by_uuid(db, aeroplane_uuid)

    # Materialize nested wing relations before schema conversion to avoid lazy-load
    # issues outside of active session scope during response serialization.
    for wing in aeroplane.wings or []:
        for x_sec in wing.x_secs or []:
            detail = x_sec.detail
            if detail is None:
                continue
            _ = list(detail.spares or [])
            ted = detail.trailing_edge_device
            if ted is not None:
                _ = ted.servo_data
    
    wing_map: OrderedDict[str, schemas.AsbWingSchema] = OrderedDict({
        w.name: schemas.AsbWingSchema.model_validate(w, from_attributes=True)
        for w in aeroplane.wings
    })
    fuselage_map: OrderedDict[str, schemas.FuselageSchema] = OrderedDict({
        f.name: schemas.FuselageSchema.model_validate(f, from_attributes=True)
        for f in aeroplane.fuselages
    })
    
    return schemas.AeroplaneSchema(
        name=aeroplane.name,
        xyz_ref=aeroplane.xyz_ref,
        wings=wing_map,
        fuselages=fuselage_map
    )


def delete_aeroplane(db: Session, aeroplane_uuid) -> None:
    """
    Delete an aeroplane.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(
                AeroplaneModel.uuid == aeroplane_uuid
            ).first()
            
            if not aeroplane:
                raise NotFoundError(
                    message="Aeroplane not found",
                    details={"aeroplane_id": str(aeroplane_uuid)}
                )
            db.delete(aeroplane)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when deleting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_aeroplane_mass(db: Session, aeroplane_uuid) -> float:
    """
    Get the total mass of an aeroplane.
    
    Raises:
        NotFoundError: If the aeroplane or mass does not exist.
        InternalError: If a database error occurs.
    """
    aeroplane = get_aeroplane_by_uuid(db, aeroplane_uuid)
    
    if aeroplane.total_mass_kg is None:
        raise NotFoundError(
            message="Aeroplane weight not set",
            details={"aeroplane_id": str(aeroplane_uuid)}
        )
    return aeroplane.total_mass_kg


def set_aeroplane_mass(db: Session, aeroplane_uuid, total_mass_kg: float) -> bool:
    """
    Set the total mass of an aeroplane.
    
    Returns:
        bool: True if mass was created, False if updated.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        created = False
        with db.begin():
            aeroplane = db.query(AeroplaneModel).filter(
                AeroplaneModel.uuid == aeroplane_uuid
            ).first()
            
            if not aeroplane:
                raise NotFoundError(
                    message="Aeroplane not found",
                    details={"aeroplane_id": str(aeroplane_uuid)}
                )
            
            if aeroplane.total_mass_kg is None:
                created = True
            
            aeroplane.total_mass_kg = total_mass_kg
            aeroplane.updated_at = datetime.now()
        
        return created
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when setting aeroplane mass: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_aeroplane_airplane_configuration(db: Session, aeroplane_uuid) -> dict:
    """
    Build and return an AirplaneConfiguration payload for the selected aeroplane.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        ValidationError: If required data for configuration export is missing.
        InternalError: If a database error occurs.
    """
    aeroplane = get_aeroplane_by_uuid(db, aeroplane_uuid)

    if aeroplane.total_mass_kg is None:
        raise ValidationError(
            message="Aeroplane total_mass_kg must be set to build AirplaneConfiguration.",
            details={"aeroplane_id": str(aeroplane_uuid)},
        )

    try:
        wing_configurations = [wing_model_to_wing_config(wing) for wing in aeroplane.wings]
    except Exception as exc:
        logger.error("Failed to convert wings for aeroplane %s: %s", aeroplane_uuid, exc)
        raise InternalError(
            message=f"Wing data conversion failed: {exc}",
        )
    try:
        fuselage_configurations = (
            [fuselage_model_to_fuselage_config(fuselage) for fuselage in aeroplane.fuselages]
            if aeroplane.fuselages
            else None
        )
    except Exception as exc:
        logger.error("Failed to convert fuselages for aeroplane %s: %s", aeroplane_uuid, exc)
        raise InternalError(
            message=f"Fuselage data conversion failed: {exc}",
        )

    airplane_configuration = AirplaneConfiguration(
        name=aeroplane.name,
        total_mass_kg=aeroplane.total_mass_kg,
        wings=wing_configurations,
        fuselages=fuselage_configurations,
    )
    return _to_json_compatible(airplane_configuration.to_dict())
