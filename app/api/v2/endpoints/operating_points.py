from typing import Optional

from fastapi import Depends, APIRouter, Query, Path, Body
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.schemas.aeroanalysisschema import (
    GeneratedOperatingPointSetRead,
    GenerateOperatingPointSetRequest,
    OperatingPointSetSchema,
    StoredOperatingPointCreate,
    StoredOperatingPointRead,
)
from app.services import operating_point_generator_service

router = APIRouter()


def _resolve_aircraft_pk(db: Session, aircraft_uuid: UUID4) -> Optional[int]:
    aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_uuid).first()
    return aircraft.id if aircraft else None


@router.post(
    "/aircraft/{aircraft_id}/operating-pointsets/generate-default",
    response_model=GeneratedOperatingPointSetRead,
    operation_id="generate_default_operating_point_set",
)
async def generate_default_operating_point_set(
    aircraft_id: UUID4 = Path(..., description="Aircraft UUID"),
    request: GenerateOperatingPointSetRequest = Body(default_factory=GenerateOperatingPointSetRequest),
    db: Session = Depends(get_db),
) -> GeneratedOperatingPointSetRead:
    return await operating_point_generator_service.generate_default_set_for_aircraft(
        db=db,
        aircraft_uuid=aircraft_id,
        replace_existing=request.replace_existing,
        profile_id_override=request.profile_id_override,
    )


@router.post("/operating_points/", response_model=StoredOperatingPointRead, operation_id="create_operating_point")
def create_operating_point(
    op_data: StoredOperatingPointCreate,
    db: Session = Depends(get_db),
):
    op = OperatingPointModel(**op_data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


@router.get("/operating_points", response_model=list[StoredOperatingPointRead], operation_id="list_operating_points")
def list_operating_points(
    aircraft_id: Optional[UUID4] = Query(default=None, description="Optional aircraft UUID filter"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(OperatingPointModel).order_by(OperatingPointModel.id)
    if aircraft_id is not None:
        aircraft_pk = _resolve_aircraft_pk(db, aircraft_id)
        if aircraft_pk is None:
            return []
        query = query.filter(OperatingPointModel.aircraft_id == aircraft_pk)
    return query.offset(skip).limit(limit).all()


@router.get("/operating_points/{op_id}", response_model=StoredOperatingPointRead, operation_id="get_operating_point")
def read_operating_point(
    op_id: int,
    db: Session = Depends(get_db),
):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPoint", resource_id=op_id)
    return op


@router.put("/operating_points/{op_id}", response_model=StoredOperatingPointRead, operation_id="update_operating_point")
def update_operating_point(
    op_id: int,
    op_data: StoredOperatingPointCreate,
    db: Session = Depends(get_db),
):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPoint", resource_id=op_id)
    for key, value in op_data.model_dump().items():
        setattr(op, key, value)
    db.commit()
    db.refresh(op)
    return op


@router.delete("/operating_points/{op_id}", operation_id="delete_operating_point")
def delete_operating_point(op_id: int, db: Session = Depends(get_db)):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPoint", resource_id=op_id)
    db.delete(op)
    db.commit()
    return {"detail": "Operating point deleted"}


@router.post("/operating_pointsets/", response_model=OperatingPointSetSchema, operation_id="create_operating_pointset")
def create_operating_pointset(
    opset_data: OperatingPointSetSchema,
    db: Session = Depends(get_db),
):
    opset = OperatingPointSetModel(**opset_data.model_dump())
    db.add(opset)
    db.commit()
    db.refresh(opset)
    return opset


@router.get("/operating_pointsets", response_model=list[OperatingPointSetSchema], operation_id="list_operating_pointsets")
def list_operating_pointsets(
    aircraft_id: Optional[UUID4] = Query(default=None, description="Optional aircraft UUID filter"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(OperatingPointSetModel).order_by(OperatingPointSetModel.id)
    if aircraft_id is not None:
        aircraft_pk = _resolve_aircraft_pk(db, aircraft_id)
        if aircraft_pk is None:
            return []
        query = query.filter(OperatingPointSetModel.aircraft_id == aircraft_pk)
    return query.offset(skip).limit(limit).all()


@router.get("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="get_operating_pointset")
def read_operating_pointset(opset_id: int, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPointSet", resource_id=opset_id)
    return opset


@router.put("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="update_operating_pointset")
def update_operating_pointset(opset_id: int, opset_data: OperatingPointSetSchema, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPointSet", resource_id=opset_id)
    for key, value in opset_data.model_dump().items():
        setattr(opset, key, value)
    db.commit()
    db.refresh(opset)
    return opset


@router.delete("/operating_pointsets/{opset_id}", operation_id="delete_operating_pointset")
def delete_operating_pointset(opset_id: int, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(entity="OperatingPointSet", resource_id=opset_id)
    db.delete(opset)
    db.commit()
    return {"detail": "Operating point set deleted"}
