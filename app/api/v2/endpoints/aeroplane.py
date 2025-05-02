import http
import json
import logging
import os
import uuid
import tempfile
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse, FileResponse

import aerosandbox as asb
import numpy as np

from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.models.analysis_model import AvlAnalysisModel
from app.models.AeroplaneRequest import CreateAeroPlaneRequest, CreateWingLoftRequest, CreatorUrlType, ExporterUrlType, \
    AnalysisToolUrlType
from app.models.WingAnalysisRequest import WingAnalysisRequest
from app.services.create_wing_configuration import create_wing_configuration, create_servo

router = APIRouter()

# In-Memory-Aufgabenverwaltung
tasks = {}
tasks_lock = Lock()
executor = ThreadPoolExecutor(max_workers=4)  # Passen Sie die Anzahl der Worker an Ihre Bedürfnisse an

AeroPlaneID = str

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
@router.post("/aeroplane")
async def create_aeroplane(request: CreateAeroPlaneRequest) -> AeroPlaneID:
    """
    Create a new aeroplane instance.

    response:
        202: Accepted
        500: Internal Server Error
    """
    try:
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    return aeroplane_id

@router.get("/aeroplane")
async def get_aeroplane(aeroplane_id: str =Query(..., description="The ID of the aeroplane")) -> dict:
    """
    Returns the aeroplane definition.
    """

    pass

@router.delete("/aeroplane")
async def delete_aeroplane(aeroplane_id: str =Query(..., description="The ID of the aeroplane")):
    """
    Deletes the aeroplane definition.
    """

    pass


# Handle an aeroplane wings
@router.post("/aeroplane/wings")
async def create_aeroplane_wings(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                 request: CreateWingLoftRequest = Body(...)) -> dict:
    """
    Creates a new wing for the aeroplane.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.get("/aeroplane/wings")
async def get_aeroplane_wings(aeroplane_id: str =Query(..., description="The ID of the aeroplane")) -> dict:
    """
    Returns the aeroplane wings.

    response:
        200: OK
        500: Internal Server Error
    """
    pass


# Handle an aeroplane wing
@router.post("/aeroplane/wing")
async def update_aeroplane_wing(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                    wing_id: str =Query(..., description="The ID of the wing"),
                                request: WingAnalysisRequest = Body(...)) -> dict:
    """
    Updates the wing for the aeroplane.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.get("/aeroplane/wing")
async def get_aeroplane_wing(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                              wing_id: str =Query(..., description="The ID of the wing")) -> dict:
    """
    Returns the aeroplane wing.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.delete("/aeroplane/wing")
async def delete_aeroplane_wing(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                wing_id: str =Query(..., description="The ID of the wing")):
    """
    Delete a wing.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

# Handle an aeroplane wing cross sections
@router.get("/aeroplane/wing/cross_sections")
async def get_aeroplane_wing_cross_sections(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                             wing_id: str =Query(..., description="The ID of the wing")) -> dict:
     """
     Returns the aeroplane wing cross sections.

     response:
          200: OK
          500: Internal Server Error
     """
     pass

@router.post("/aeroplane/wing/cross_sections")
async def create_aeroplane_wing_cross_sections(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                  wing_id: str =Query(..., description="The ID of the wing"),
                                                  request: CreateWingLoftRequest = Body(...)) -> dict:
     """
     Creates a new cross section for the aeroplane.

     response:
          200: OK
          500: Internal Server Error
     """
     pass

@router.put("/aeroplane/wing/cross_section")
async def update_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                  wing_id: str =Query(..., description="The ID of the wing"),
                                                  cross_section_id: str =Query(..., description="The ID of the cross section"),
                                                  request: CreateWingLoftRequest = Body(...)) -> dict:
     """
     Updates the cross section for the aeroplane.

     response:
             200: OK
             500: Internal Server Error
     """
     pass

@router.post("/aeroplane/wing/cross_section")
async def create_aeroplane_wing_cross_section(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                                wing_id: str =Query(..., description="The ID of the wing"),
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
                                                wing_id: str =Query(..., description="The ID of the wing"),
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
                                  wing_id: str =Query(..., description="The ID of the wing")) -> dict:
    """
    Returns the aeroplane wing spars.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

@router.post("/aeroplane/wing/cross_section/spars")
async def create_aeroplane_wing_cross_section_spars(aeroplane_id: str =Query(..., description="The ID of the aeroplane"),
                                      wing_id: str =Query(..., description="The ID of the wing"),
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
                                     wing_id: str =Query(..., description="The ID of the wing"),
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
                                     wing_id: str =Query(..., description="The ID of the wing"),
                                    spar_id: str =Query(..., description="The ID of the spar")):
    """
    Delete a spar.

    response:
        200: OK
        500: Internal Server Error
    """
    pass

