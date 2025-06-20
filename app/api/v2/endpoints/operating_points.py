from inspect import Parameter

from fastapi import FastAPI, HTTPException, Depends, APIRouter, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.schemas.aeroanalysisschema import OperatingPointSchema, OperatingPointSetSchema

router = APIRouter()

# CRUD für OperatingPointModel
@router.post("/operating_points/", response_model=OperatingPointSchema, operation_id="create_operating_point")
def create_operating_point(op_data: OperatingPointSchema,
                           db: Session = Depends(get_db)):
    op = OperatingPointModel(**op_data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op

@router.get("/operating_points/{op_id}", response_model=OperatingPointSchema, operation_id="get_operating_point")
def read_operating_point(op_id: int,
                         db: Session = Depends(get_db)):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operating point not found")
    return op

@router.put("/operating_points/{op_id}", response_model=OperatingPointSchema, operation_id="update_operating_point")
def update_operating_point(op_id: int,
                           op_data: OperatingPointSchema,
                           db: Session = Depends(get_db)):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operating point not found")
    for key, value in op_data.dict().items():
        setattr(op, key, value)
    db.commit()
    db.refresh(op)
    return op

@router.delete("/operating_points/{op_id}", operation_id="delete_operating_point")
def delete_operating_point(op_id: int, db: Session = Depends(get_db)):
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operating point not found")
    db.delete(op)
    db.commit()
    return {"detail": "Operating point deleted"}

# CRUD für OperatingPointSetModel
@router.post("/operating_pointsets/", response_model=OperatingPointSetSchema, operation_id="create_operating_pointset")
def create_operating_pointset(opset_data: OperatingPointSetSchema,
                              db: Session = Depends(get_db)):
    opset = OperatingPointSetModel(**opset_data.model_dump())
    db.add(opset)
    db.commit()
    db.refresh(opset)
    return opset

@router.get("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="get_operating_pointset")
def read_operating_pointset(opset_id: int, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=404, detail="Operating point set not found")
    return opset

@router.put("/operating_pointsets/{opset_id}", response_model=OperatingPointSetSchema, operation_id="update_operating_pointset")
def update_operating_pointset(opset_id: int, opset_data: OperatingPointSetSchema, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=404, detail="Operating point set not found")
    for key, value in opset_data.dict().items():
        setattr(opset, key, value)
    db.commit()
    db.refresh(opset)
    return opset

@router.delete("/operating_pointsets/{opset_id}", operation_id="delete_operating_pointset")
def delete_operating_pointset(opset_id: int, db: Session = Depends(get_db)):
    opset = db.query(OperatingPointSetModel).filter(OperatingPointSetModel.id == opset_id).first()
    if not opset:
        raise HTTPException(status_code=404, detail="Operating point set not found")
    db.delete(opset)
    db.commit()
    return {"detail": "Operating point set deleted"}
