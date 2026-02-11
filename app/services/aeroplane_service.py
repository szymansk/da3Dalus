"""
Aeroplane Service - Business logic for aeroplane CRUD operations.

This module contains the core logic for aeroplane management,
separated from HTTP concerns for better testability and reusability.
"""

import logging
from datetime import datetime
from typing import List, OrderedDict

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import NotFoundError, InternalError
from app.models.aeroplanemodel import AeroplaneModel

logger = logging.getLogger(__name__)


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
