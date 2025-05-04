import http
import json
import logging
import os
import uuid
import tempfile
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import aerosandbox as asb
import numpy as np

from app import schemas
from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.models.analysis_model import AvlAnalysisModel
from app.models.AeroplaneRequest import CreateAeroPlaneRequest, CreateWingLoftRequest, CreatorUrlType, ExporterUrlType, \
    AnalysisToolUrlType
from app.models.WingAnalysisRequest import WingAnalysisRequest
from app.services.create_wing_configuration import create_wing_configuration, create_servo
from app.db.session import SessionLocal, get_db
from app.models.aeroplane import Aeroplane
import logging
from app import schemas

router = APIRouter()

# In-Memory-Aufgabenverwaltung
tasks = {}
tasks_lock = Lock()
executor = ThreadPoolExecutor(max_workers=4)  # Passen Sie die Anzahl der Worker an Ihre Bedürfnisse an

AeroPlaneID = UUID4

def create_aeroplane_task(aeroplane_id, request_dict):
    try:
        logging.info(f"create aeroplane with 'aeroplane_id: {aeroplane_id}'")

        request = CreateAeroPlaneRequest(**request_dict)
        wings = {key: create_wing_configuration(value) for key, value in request.wings.items()}

        settings = request.settings.__dict__.copy()
        settings['servo_information'] = {
            key: ServoInformation(
                height=value.height,
                width=value.width,
                length=value.length,
                lever_length=value.lever_length,
                rot_x=value.rot_x,
                rot_y=value.rot_y,
                rot_z=value.rot_z,
                trans_x=value.trans_x,
                trans_y=value.trans_y,
                trans_z=value.trans_z,
                servo=create_servo(value.servo)
            ) for key, value in request.settings.servo_information.items()
        }

        if isinstance(request.blueprint, dict):
            blue_print: ConstructionStepNode = json.loads(
                json.dumps(request.blueprint),
                cls=GeneralJSONDecoder,
                wing_config=wings,
                fuselage_config=request.fuselages,
                **settings
            )
        elif os.path.isfile(request.blueprint):
            with open(request.blueprint, "r") as json_file:
                blue_print: ConstructionStepNode = json.load(
                    json_file,
                    cls=GeneralJSONDecoder,
                    wing_config=wings,
                    fuselage_config=request.fuselages,
                    **settings
                )
        blue_print.create_shape()
        logging.info(f"finished aeroplane with 'aeroplane_id: {aeroplane_id}'")
        zipfile = f"./tmp/{aeroplane_id}.zip"
        exports = "./tmp/exports"

        # zip files
        with ZipFile(zipfile, 'w') as zipf:
            logging.info(f"zipping files for 'aeroplane_id: {aeroplane_id}'")
            for file in os.scandir(exports):
                zipf.write(file.path)

        # delete files
        for file in os.scandir(exports):
            os.unlink(file.path)

        result = {"zipfile": zipfile}
        with tasks_lock:
            tasks[aeroplane_id]['status'] = 'SUCCESS'
            tasks[aeroplane_id]['result'] = result
    except Exception as err:
        with tasks_lock:
            tasks[aeroplane_id]['status'] = 'FAILURE'
            tasks[aeroplane_id]['error'] = str(err)

# Handle an aeroplane
@router.get("/aeroplanes")
async def get_aeroplanes():
    """
    Returns a list of all aeroplanes names with ids
    """
    pass


@router.post("/aeroplane")
async def create_aeroplane(
        name: str = Query(... , description="The aeroplanes name.", examples=["RV-7", "eHawk"]),
        db: Session = Depends(get_db)
) -> AeroPlaneID:
    """
    Create a new aeroplane instance and return its ID.
    """
    try:
        # Create a new aeroplane instance
        aeroplane = Aeroplane(name=name)

        # Add to database
        with db.begin():
            db.add(aeroplane)
            db.flush() # sets the aeroplane.id
            db.refresh(aeroplane)

        # Return the UUID
        return aeroplane.uuid
    except SQLAlchemyError as e:
        logging.error(f"Database error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        pass

@router.get("/aeroplane")
async def get_aeroplane(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db)
) -> schemas.aeroplane.Aeroplane:
    """
    Returns the aeroplane definition.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        return schemas.aeroplane.Aeroplane.model_validate(aeroplane, from_attributes=True)
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException as e:
        # re-raise FastAPI HTTPExceptions (e.g., 404) without modification
        raise e
    except Exception as e:
        logging.error(f"Unexpected error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.delete("/aeroplane")
async def delete_aeroplane(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane to be deleted"),
    db: Session = Depends(get_db)
):
    """
    Deletes the aeroplane.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        with db.begin():
            db.delete(aeroplane)
        return {"deleted": aeroplane_id}
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane wings
from fastapi import Depends, Query, Body, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.aeroplane import Aeroplane, Wing
from app import schemas
import logging
from pydantic import UUID4 as AeroPlaneID

@router.get("/aeroplane/wings", response_model=List[schemas.Wing])
async def get_aeroplane_wings(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db)
) -> List[schemas.Wing]:
    """
    Returns the aeroplane's wings.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wings = aeroplane.wings
        return [
            schemas.aeroplane.Wing.model_validate(w, from_attributes=True)
            for w in wings
        ]
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane wing
@router.put("/aeroplane/wing", response_model=schemas.aeroplane.Wing)
async def create_aeroplane_wing(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    wing_name: str = Query(..., description="The ID of the wing"),
    request: schemas.aeroplane.Wing = Body(...),
    db: Session = Depends(get_db)
) -> schemas.aeroplane.Wing:
    """
    Create the wing for the aeroplane.
    """
    try:
        # perform read and write in a single transaction to avoid nested begin
        with db.begin():
            plane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = Wing.from_dict(name=wing_name, data=request.model_dump())
            plane.wings.append(wing)
            db.add(wing)
        return schemas.aeroplane.Wing.model_validate(wing, from_attributes=True)
    except SQLAlchemyError as e:
        logging.error(f"Database error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.post("/aeroplane/wing", response_model=schemas.aeroplane.Wing)
async def update_aeroplane_wing(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    wing_name: AeroPlaneID = Query(..., description="The ID of the wing"),
    request: schemas.aeroplane.Wing = Body(...),
    db: Session = Depends(get_db)
) -> schemas.aeroplane.Wing:
    """
    Updates the wing for the aeroplane.
    """
    try:
        with db.begin():
            plane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in plane.wings if str(w.name) == str(wing_name)), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            data = request.model_dump()
            data.pop("id", None)
            for key, value in data.items():
                setattr(wing, key, value)

            db.add(wing)
        return schemas.aeroplane.Wing.model_validate(wing, from_attributes=True)
    except SQLAlchemyError as e:
        logging.error(f"Database error when updating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when updating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get("/aeroplane/wing", response_model=schemas.aeroplane.Wing)
async def get_aeroplane_wing(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    wing_name: AeroPlaneID = Query(..., description="The ID of the wing"),
    db: Session = Depends(get_db)
) -> schemas.aeroplane.Wing:
    """
    Returns the aeroplane wing.
    """
    try:
        # Load the parent aeroplane
        plane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not plane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        # Find the wing belonging to this aeroplane
        wing = next((w for w in plane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        return schemas.aeroplane.Wing.model_validate(wing, from_attributes=True)
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when getting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.delete("/aeroplane/wing")
async def delete_aeroplane_wing(
    aeroplane_id: AeroPlaneID = Query(..., description="The ID of the aeroplane"),
    wing_name: AeroPlaneID = Query(..., description="The ID of the wing"),
    db: Session = Depends(get_db)
):
    """
    Delete a wing.
    """
    try:
        # Find the plane and the wing belonging to it
        with db.begin():
            plane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in plane.wings if str(w.name) == str(wing_name)), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            db.delete(wing)
        return {"deleted": wing_name}
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

# Handle an aeroplane wing cross sections
@router.get("/aeroplane/wing/cross_sections")
async def get_aeroplane_wing_cross_sections(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                             wing_name: str =Query(..., description="The ID of the wing")) -> dict:
     """
     Returns the aeroplane wing cross sections.
     """
     pass

@router.post("/aeroplane/wing/cross_section")
async def create_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                  wing_name: str =Query(..., description="The ID of the wing"),
                                                  request: CreateWingLoftRequest = Body(...)) -> dict:
     """
     Creates a new cross section for the wing.
     """
     pass

@router.put("/aeroplane/wing/cross_section")
async def update_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                  wing_name: str =Query(..., description="The ID of the wing"),
                                                  cross_section_id: str =Query(..., description="The ID of the cross section"),
                                                  request: CreateWingLoftRequest = Body(...)) -> dict:
     """
     Updates the cross section for the aeroplane.
     """
     pass

@router.post("/aeroplane/wing/cross_section")
async def create_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                wing_name: str =Query(..., description="The ID of the wing"),
                                                cross_section_id: str =Query(..., description="The ID of the cross section"),
                                                request: CreateWingLoftRequest = Body(...)) -> dict:
         """
         Creates a new cross section for the aeroplane.

         response:
                 200: OK
                 500: Internal Server Error
         """
         pass


@router.delete("/aeroplane/wing/cross_section")
async def delete_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                wing_name: str =Query(..., description="The ID of the wing"),
                                                cross_section_id: str =Query(..., description="The ID of the cross section")):
         """
         Delete a cross section.

         response:
                 200: OK
                 500: Internal Server Error
         """
         pass


@router.get("/aeroplane/wing/cross_section/spars")
async def get_aeroplane_wing_cross_section_spars(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                  wing_name: str =Query(..., description="The ID of the wing")) -> dict:
    """
    Returns the aeroplane wing spars.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.post("/aeroplane/wing/cross_section/spars")
async def create_aeroplane_wing_cross_section_spars(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                      wing_name: str =Query(..., description="The ID of the wing"),
                                      request: CreateWingLoftRequest = Body(...)) -> dict:
    """
    Creates a new spar for the aeroplane.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.put("/aeroplane/wing/cross_section/spar")
async def update_aeroplane_wing_cross_section_spar(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                     wing_name: str =Query(..., description="The ID of the wing"),
                                    spar_id: str =Query(..., description="The ID of the spar"),
                                    request: CreateWingLoftRequest = Body(...)) -> dict:
    """
    Updates the spar for the aeroplane.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.delete("/aeroplane/wing/cross_section/spar")
async def delete_aeroplane_wing_cross_section_spar(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                     wing_name: str =Query(..., description="The ID of the wing"),
                                    spar_id: str =Query(..., description="The ID of the spar")):
    """
    Delete a spar.

    response:
        200: OK
        500: Internal Server Error
    """
    pass
