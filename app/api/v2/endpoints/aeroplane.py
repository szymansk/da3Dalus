import json
import os
from datetime import datetime
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile
from typing import List, OrderedDict

from fastapi import Response, status

from fastapi import Path, Depends, Body, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
import logging
from datetime import datetime

from pydantic import UUID4, BaseModel

from fastapi import APIRouter, Path, Depends, Query, Body, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation

from app import schemas
from app.models.AeroplaneRequest import CreateAeroPlaneRequest, CreateWingLoftRequest
from app.services.create_wing_configuration import create_wing_configuration, create_servo
from app.db.session import get_db
from app.models.aeroplane import Aeroplane, Wing, WingXSec, ControlSurface

import logging

logger = logging.getLogger(__name__)

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


class GetAeroplaneResponse(BaseModel):
    class NameIdMap(BaseModel):
        name: str
        id: AeroPlaneID
        created_at: datetime
        updated_at: datetime

    aeroplanes: List[NameIdMap]


# Handle an aeroplane
@router.get("/aeroplanes",
            response_model=GetAeroplaneResponse,
            status_code=status.HTTP_200_OK,
            tags=["aeroplanes"])
async def get_aeroplanes(db: Session = Depends(get_db)) -> GetAeroplaneResponse:
    """
    Returns a list of all aeroplanes names with ids alphabetically sorted by the name.
    """
    try:
        # Query all aeroplanes, ordered by name
        aeroplanes = db.query(Aeroplane).order_by(Aeroplane.name).all()
        items = [
            GetAeroplaneResponse.NameIdMap(
                name=ap.name,
                id=ap.uuid,
                created_at=ap.created_at,
                updated_at=ap.updated_at,
            )
            for ap in aeroplanes
        ]
        return GetAeroplaneResponse(aeroplanes=items)
    except SQLAlchemyError as e:
        logging.error(f"Database error when listing aeroplanes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error when listing aeroplanes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/aeroplanes",
             status_code=status.HTTP_201_CREATED,
             tags=["aeroplanes"])
async def create_aeroplane(
        name: str = Query(..., description="The aeroplanes name.", examples=["RV-7", "eHawk"]),
        db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Create a new aeroplane instance and returns its ID.
    """
    try:
        # Create a new aeroplane instance
        aeroplane = Aeroplane(name=name)

        # Add to database
        with db.begin():
            db.add(aeroplane)
            db.flush()  # sets the aeroplane.id
            db.refresh(aeroplane)

        # Return the UUID
        return JSONResponse(content={"id": str(aeroplane.uuid)})
    except SQLAlchemyError as e:
        logging.error(f"Database error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error when creating aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/aeroplanes/{aeroplane_id}",
            status_code=status.HTTP_200_OK,
            response_model=schemas.aeroplane.Aeroplane,
            tags=["aeroplanes"])
async def get_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> schemas.aeroplane.Aeroplane:
    """
    Returns the aeroplane definition.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")

        # Build wing and fuselage mappings for serialization
        wing_map: OrderedDict[str, schemas.Wing] = OrderedDict({
            w.name: schemas.Wing.model_validate(w, from_attributes=True)
            for w in aeroplane.wings
        })
        fuselage_map: OrderedDict[str, schemas.Fuselage] = OrderedDict({
            f.name: schemas.Fuselage.model_validate(f, from_attributes=True)
            for f in aeroplane.fuselages
        })

        # Construct response model instance
        result = schemas.aeroplane.Aeroplane(
            name=aeroplane.name,
            xyz_ref=aeroplane.xyz_ref,
            wings=wing_map,
            fuselages=fuselage_map
        )
        return result
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException as e:
        # re-raise FastAPI HTTPExceptions (e.g., 404) without modification
        raise e
    except Exception as e:
        logging.error(f"Unexpected error when getting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/aeroplanes/{aeroplane_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["aeroplanes"])
async def delete_aeroplane(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane to be deleted"),
        db: Session = Depends(get_db)
):
    """
    Deletes the aeroplane.
    """
    try:
        with db.begin():
            aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            db.delete(aeroplane)
        return
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when deleting aeroplane: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane wings
@router.get("/aeroplanes/{aeroplane_id}/wings",
            status_code=status.HTTP_200_OK,
            response_model=List[str],
            tags=["wings"])
async def get_aeroplane_wings(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        db: Session = Depends(get_db)
) -> List[str]:
    """
    Returns a list of aeroplane's wing names.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wings = aeroplane.wings
        return [w.name for w in wings]
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when getting aeroplane wings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Handle an aeroplane wing
@router.put("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            status_code=status.HTTP_201_CREATED,
            response_class=Response,
            tags=["wings"])
async def create_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        request: schemas.aeroplane.Wing = Body(..., description="The new wing data"),
        db: Session = Depends(get_db)
):
    """
    Create the wing for the aeroplane.
    """
    try:
        # perform read and write in a single transaction to avoid nested begin
        with db.begin():
            plane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not plane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")

            if any(w.name == wing_name for w in plane.wings):
                raise HTTPException(400, "Wing name must be unique for this aeroplane")

            wing = Wing.from_dict(name=wing_name, data=request.model_dump())
            plane.wings.append(wing)
            db.add(wing)
            plane.updated_at = datetime.now()
        return
    except SQLAlchemyError as e:
        logging.error(f"Database error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when creating aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["wings"]
)
async def update_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        request: schemas.aeroplane.Wing = Body(..., description="The new wing data"),
        db: Session = Depends(get_db),
):
    """
    Overwrite an existing wing with the data in the request.
    """
    try:
        with db.begin():
            plane = (
                db.query(Aeroplane)
                .filter(Aeroplane.uuid == aeroplane_id)
                .first()
            )
            if not plane:
                raise HTTPException(404, "Aeroplane not found")

            wing = next((w for w in plane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(404, "Wing not found")

            new_wing = Wing.from_dict(name=wing_name, data=request.model_dump())
            plane.wings.remove(wing)
            plane.wings.append(new_wing)
            plane.updated_at = datetime.now()
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error("DB error updating wing: %s", e)
        raise HTTPException(500, f"Database error: {e}")
    except Exception as e:
        logging.error("Unexpected error updating wing: %s", e)
        raise HTTPException(500, f"Unexpected error: {e}")


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}",
            response_model=schemas.aeroplane.Wing,
            tags=["wings"])
async def get_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
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


@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["wings"]
)
async def delete_aeroplane_wing(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
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
            plane.updated_at = datetime.now()
        return
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when deleting aeroplane wing: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


#########################################
# Handle an aeroplane wing cross sections
#########################################
@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    response_model=List[schemas.aeroplane.WingXSec],
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
)
async def get_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
) -> List[schemas.aeroplane.WingXSec]:
    """
    Returns the wing's cross-sections as an ordered list.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        # Serialize cross-sections
        return [
            schemas.aeroplane.WingXSec.model_validate(xs, from_attributes=True)
            for xs in wing.x_secs
        ]
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error when getting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

from fastapi.responses import Response
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging

@router.delete(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["cross-sections"]
)
async def delete_aeroplane_wing_cross_sections(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        db: Session = Depends(get_db)
):
    """
    Delete all cross-sections of a wing.
    """
    try:
        with db.begin():
            aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            # Remove all cross-sections (using delete-orphan cascade)
            wing.x_secs.clear()
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when deleting wing cross-sections: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_model=schemas.aeroplane.WingXSec,
    status_code=status.HTTP_200_OK,
    tags=["cross-sections"],
)
async def get_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
) -> schemas.aeroplane.WingXSec:
    """
    Returns the aeroplane wing cross sections as a list of names.
    """
    try:
        aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
        if not aeroplane:
            raise HTTPException(status_code=404, detail="Aeroplane not found")
        wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
        if not wing:
            raise HTTPException(status_code=404, detail="Wing not found")
        x_secs = wing.x_secs
        if cross_section_index < 0 or cross_section_index >= len(x_secs):
            raise HTTPException(status_code=404, detail="Cross-section not found")
        xs = x_secs[cross_section_index]
        return schemas.aeroplane.WingXSec.model_validate(xs, from_attributes=True)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error when getting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when getting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["cross-sections"],
)
async def create_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(...,
                                        description="The index where it will be spliced into the list of cross sections. (-1 is the end of the list, 0 is the start of the list)"),
        request: schemas.aeroplane.WingXSec = Body(..., description="Wing cross section request"),
        db: Session = Depends(get_db)
) :
    """
    Creates a new cross-section for the wing and splice it into the list of cross-sections.
    """
    try:
        with db.begin():
            aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            # build new WingXSec from request data
            data = request.model_dump()
            cs_dict = data.pop("control_surface", None)
            new_xsec = WingXSec(**data)

            if cs_dict is not None:
                # Accept both dict and pydantic model
                if hasattr(cs_dict, "model_dump"):
                    cs_dict = cs_dict.model_dump()
                new_xsec.control_surface = ControlSurface(**cs_dict)

            # determine insertion index
            existing = wing.x_secs  # already ordered by sort_index
            if cross_section_index == -1 or cross_section_index >= len(existing):
                insertion_index = len(existing)
            else:
                insertion_index = cross_section_index
            # shift sort_index of following cross-sections
            for xs in existing[insertion_index:]:
                xs.sort_index = xs.sort_index + 1
                db.add(xs)
            # assign sort_index and insert new cross-section
            new_xsec.sort_index = insertion_index
            if insertion_index == len(existing):
                wing.x_secs.append(new_xsec)
            else:
                wing.x_secs.insert(insertion_index, new_xsec)
            # touch parent timestamp
            aeroplane.updated_at = datetime.now()
            db.add(new_xsec)
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error when creating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when creating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.put(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
    response_class=Response,
    status_code=status.HTTP_201_CREATED,
    tags=["cross-sections"],
)
async def update_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        request: schemas.aeroplane.WingXSec = Body(...),
        db: Session = Depends(get_db)
):
    """
    Updates the cross section for the aeroplane.
    """
    try:
        with db.begin():
            aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")

            data = request.model_dump()
            cs_dict = data.pop("control_surface", None)
            new_xsec = WingXSec(**data)
            if cs_dict is not None:
                # Accept both dict and pydantic model
                if hasattr(cs_dict, "model_dump"):
                    cs_dict = cs_dict.model_dump()
                new_xsec.control_surface = ControlSurface(**cs_dict)

            wing.x_secs[cross_section_index] = new_xsec
            # Touch parent timestamp
            aeroplane.updated_at = datetime.now()
        return
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error when updating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when updating wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.delete("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["cross-sections"])
async def delete_aeroplane_wing_cross_section(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        db: Session = Depends(get_db)
):
    """
    Delete a cross section.
    """
    try:
        with db.begin():
            aeroplane = db.query(Aeroplane).filter(Aeroplane.uuid == aeroplane_id).first()
            if not aeroplane:
                raise HTTPException(status_code=404, detail="Aeroplane not found")
            wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
            if not wing:
                raise HTTPException(status_code=404, detail="Wing not found")
            x_secs = wing.x_secs
            if cross_section_index < 0 or cross_section_index >= len(x_secs):
                raise HTTPException(status_code=404, detail="Cross-section not found")
            # Remove and delete the cross-section
            xsec = x_secs.pop(cross_section_index)
            db.delete(xsec)
            aeroplane.updated_at = datetime.now()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error when deleting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error when deleting wing cross-section: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
            tags=["spars"])
async def get_aeroplane_wing_cross_section_spars(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
) -> dict:
    """
    Returns the aeroplane wing spars.
    """
    pass


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
             tags=["spars"])
async def create_aeroplane_wing_cross_section_spars(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        request: CreateWingLoftRequest = Body(...)) -> dict:
    """
    Creates a new spar for the aeroplane.
    """
    pass


@router.put("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
            tags=["spars"])
async def update_aeroplane_wing_cross_section_spar(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        spar_id: str = Query(..., description="The ID of the spar"),
        request: CreateWingLoftRequest = Body(...)) -> dict:
    """
    Updates the spar for the aeroplane.
    """
    pass


@router.delete("/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
               tags=["spars"])
async def delete_aeroplane_wing_cross_section_spar(
        aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
        wing_name: str = Path(..., description="The ID of the wing"),
        cross_section_index: int = Path(..., description="The index of the cross section"),
        spar_id: str = Query(..., description="The ID of the spar")):
    """
    Delete a spar.
    """
    pass
