from typing import Annotated, Optional

from fastapi import Depends, APIRouter, Query, Path, Body, HTTPException, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.schemas.aeroanalysisschema import (
    GeneratedOperatingPointSetRead,
    GenerateOperatingPointSetRequest,
    OperatingPointSetSchema,
    StoredOperatingPointCreate,
    StoredOperatingPointRead,
    TrimmedOperatingPointRead,
    TrimOperatingPointRequest,
)
from app.services import operating_point_generator_service

router = APIRouter()


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _resolve_aircraft_pk(db: Session, aircraft_uuid: UUID4) -> Optional[int]:
    aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_uuid).first()
    return aircraft.id if aircraft else None


@router.post(
    "/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default",
    operation_id="generate_default_operating_point_set"
)
async def generate_default_operating_point_set(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    request: Annotated[GenerateOperatingPointSetRequest, Body()] = None,
) -> GeneratedOperatingPointSetRead:
    try:
        req = request or GenerateOperatingPointSetRequest()
        return operating_point_generator_service.generate_default_set_for_aircraft(
            db=db,
            aircraft_uuid=aeroplane_id,
            replace_existing=req.replace_existing,
            profile_id_override=req.profile_id_override,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/operating-points/trim",
    operation_id="trim_operating_point"
)
async def trim_operating_point(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    request: Annotated[TrimOperatingPointRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> TrimmedOperatingPointRead:
    try:
        return operating_point_generator_service.trim_operating_point_for_aircraft(
            db=db,
            aircraft_uuid=aeroplane_id,
            request=request,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post("/operating_points/", response_model=StoredOperatingPointRead, operation_id="create_operating_point")
def create_operating_point(
    op_data: StoredOperatingPointCreate,
    db: Annotated[Session, Depends(get_db)],
):
    op = OperatingPointModel(**op_data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


@router.get("/operating_points", response_model=list[StoredOperatingPointRead], operation_id="list_operating_points")
def list_operating_points(
    db: Annotated[Session, Depends(get_db)],
    aircraft_id: Annotated[Optional[UUID4], Query(description="Optional aircraft UUID filter")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
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
    db: Annotated[Session, Depends(get_db)],
):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPoint {op_id} not found")
    return op


@router.put("/operating_points/{op_id}", response_model=StoredOperatingPointRead, operation_id="update_operating_point")
def update_operating_point(
    op_id: int,
    op_data: StoredOperatingPointCreate,
    db: Annotated[Session, Depends(get_db)],
):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPoint {op_id} not found")
    for key, value in op_data.model_dump().items():
        setattr(op, key, value)
    db.commit()
    db.refresh(op)
    return op


@router.delete("/operating_points/{op_id}", operation_id="delete_operating_point")
def delete_operating_point(op_id: int, db: Annotated[Session, Depends(get_db)]):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPoint {op_id} not found")
    db.delete(op)
    db.commit()
    return {"detail": "Operating point deleted"}


@router.post("/operating_pointsets/", response_model=OperatingPointSetSchema, operation_id="create_operating_pointset")
def create_operating_pointset(
    opset_data: OperatingPointSetSchema,
    db: Annotated[Session, Depends(get_db)],
):
    opset = OperatingPointSetModel(**opset_data.model_dump())
    db.add(opset)
    db.commit()
    db.refresh(opset)
    return opset


@router.get("/operating_pointsets", response_model=list[OperatingPointSetSchema], operation_id="list_operating_pointsets")
def list_operating_pointsets(
    db: Annotated[Session, Depends(get_db)],
    aircraft_id: Annotated[Optional[UUID4], Query(description="Optional aircraft UUID filter")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
):
    query = db.query(OperatingPointSetModel).order_by(OperatingPointSetModel.id)
    if aircraft_id is not None:
        aircraft_pk = _resolve_aircraft_pk(db, aircraft_id)
        if aircraft_pk is None:
            return []
        query = query.filter(OperatingPointSetModel.aircraft_id == aircraft_pk)
    return query.offset(skip).limit(limit).all()


@router.get("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="get_operating_pointset")
def read_operating_pointset(opset_id: int, db: Annotated[Session, Depends(get_db)]):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPointSet {opset_id} not found")
    return opset


@router.put("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="update_operating_pointset")
def update_operating_pointset(opset_id: int, opset_data: OperatingPointSetSchema, db: Annotated[Session, Depends(get_db)]):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPointSet {opset_id} not found")
    for key, value in opset_data.model_dump().items():
        setattr(opset, key, value)
    db.commit()
    db.refresh(opset)
    return opset


@router.delete("/operating_pointsets/{opset_id}", operation_id="delete_operating_pointset")
def delete_operating_pointset(opset_id: int, db: Annotated[Session, Depends(get_db)]):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperatingPointSet {opset_id} not found")
    db.delete(opset)
    db.commit()
    return {"detail": "Operating point set deleted"}
