import http
import json
import logging
import os
import uuid
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse, FileResponse

import aerosandbox as asb

from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.models.analysis_model import AvlAnalysisModel
from app.schemas.AeroplaneRequest import CreateAeroPlaneRequest, CreateWingLoftRequest, CreatorUrlType, ExporterUrlType, \
    AnalysisToolUrlType
from app.schemas.WingAnalysisRequest import WingAnalysisRequest
from app.services.create_wing_configuration import create_wing_configuration, create_servo

router = APIRouter()

# In-Memory-Aufgabenverwaltung
tasks = {}
tasks_lock = Lock()
executor = ThreadPoolExecutor(max_workers=4)  # Passen Sie die Anzahl der Worker an Ihre Bedürfnisse an


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


@router.post("/aeroplanes")
async def create_aeroplane(request: CreateAeroPlaneRequest):
    try:
        aeroplane_id = str(uuid.uuid4())
        logging.info(f"called create aeroplane endpoint for 'aeroplane_id: {aeroplane_id}'")
        with tasks_lock:
            tasks[aeroplane_id] = {'status': 'PENDING'}
        tasks[aeroplane_id]['future'] = executor.submit(create_aeroplane_task, aeroplane_id, request.dict())
        return JSONResponse(
            status_code=http.HTTPStatus.ACCEPTED,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}"}
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/aeroplanes/wings/{creator_url_type}/{exporter_url_type}")
async def create_wing_loft(request: CreateWingLoftRequest,
                           creator_url_type: CreatorUrlType=CreatorUrlType.WING_LOFT,
                           exporter_url_type: ExporterUrlType=ExporterUrlType.STL,
                           leading_edge_offset_factor: float = Query(0.1, description="only need for vase mode wing"),
                           trailing_edge_offset_factor: float = Query(0.15, description="only need for vase mode wing"),
                           ):
    try:
        aeroplane_id = str(uuid.uuid4())
        logging.info(f"called create aeroplanes/wing/loft/stl endpoint for 'aeroplane_id: {aeroplane_id}'")
        with tasks_lock:
            tasks[aeroplane_id] = {'status': 'PENDING'}

        construction = request.dict()
        construction['fuselages'] = None
        wings = list(construction['wings'].keys())
        construction['blueprint'] = {
            '$TYPE': 'ConstructionRootNode',
            'creator_id': 'eHawk-wing.root.root',
            'loglevel': 50,
            'successors': {}
        }

        for wing in wings:
            construction['blueprint']['successors'][wing] = \
                {
                    '$TYPE': 'ConstructionStepNode',
                    'creator': {
                        '$TYPE': "",
                        'creator_id': wing,
                        'loglevel': 10,
                        'offset': 0,
                        'wing_index': wing,
                        'wing_side': 'BOTH'
                    },
                    'creator_id': wing,
                    'loglevel': 50,
                    'successors': {}
                }
            if creator_url_type == CreatorUrlType.WING_LOFT:
                construction['blueprint']['successors'][wing]['creator']['$TYPE'] = 'WingLoftCreator'
            else: # creator == CreatorUrlType.VASE_MODE_WING:
                construction['blueprint']['successors'][wing]['creator']['$TYPE'] = 'VaseModeWingCreator'
                construction['blueprint']['successors'][wing]['creator']['leading_edge_offset_factor'] = \
                    leading_edge_offset_factor
                construction['blueprint']['successors'][wing]['creator']['trailing_edge_offset_factor'] = \
                    trailing_edge_offset_factor

        if exporter_url_type == ExporterUrlType.STL:
            exporter_class = 'ExportToStlCreator'
        elif exporter_url_type == ExporterUrlType.STEP:
            exporter_class = 'ExportToStepCreator'
        elif exporter_url_type == ExporterUrlType.IGES:
            exporter_class = 'ExportToIgesCreator'
        else: # exporter_url_type == ExporterUrlType.3MF:
            exporter_class = 'ExportTo3MFCreator'

        construction['blueprint']['successors']['output-wing']=\
            {
                    '$TYPE': 'ConstructionStepNode',
                    'creator': {
                        '$TYPE': exporter_class,
                        'angular_tolerance': 0.1,
                        'creator_id': 'output-wing',
                        'file_path': './tmp/exports',
                        'loglevel': 20,
                        #'shapes_to_export': wings,
                        'tolerance': 0.1
                    },
                    'creator_id': 'output-wing',
                    'loglevel': 50,
                    'successors': {}
                }

        tasks[aeroplane_id]['future'] = executor.submit(create_aeroplane_task, aeroplane_id, construction)
        return JSONResponse(
            status_code=http.HTTPStatus.ACCEPTED,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}"}
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/aeroplanes/{aeroplane_id}")
async def get_aeroplane_task_status(aeroplane_id: str):
    logging.info(f"called get aeroplane endpoint for 'aeroplane_id: {aeroplane_id}'")
    with tasks_lock:
        task = tasks.get(aeroplane_id)
    if not task:
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": "Task not found"}
        )
    if task['future'].running():
        task['status'] = 'RUNNING'
    if task['status'] == 'PENDING':
        return JSONResponse(
            status_code=http.HTTPStatus.OK,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'],
                     "message": "Task is pending."}
        )
    elif task['status'] == 'FAILURE':
        return JSONResponse(
            status_code=http.HTTPStatus.OK,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'],
                     "message": task.get('error', 'An error occurred')}
        )
    elif task['status'] == 'SUCCESS':
        return JSONResponse(
            status_code=http.HTTPStatus.OK,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'],
                     "result": task.get('result')}
        )
    else:
        return JSONResponse(
            status_code=http.HTTPStatus.OK,
            content={"aeroplane_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'],
                     "message": "Task is processing."}
        )


@router.get("/aeroplanes/{aeroplane_id}/zip")
async def download_aeroplane_zip(aeroplane_id: str):
    logging.info(f"called get download aeroplane endpoint for 'aeroplane_id: {aeroplane_id}'")

    task = tasks.get(aeroplane_id)
    if not task:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail="Task not found")

    if task['status'] != 'SUCCESS':
        return JSONResponse(
            status_code=http.HTTPStatus.BAD_REQUEST,
            content={"detail": "Task not completed yet or failed"}
        )

    # Abrufen des Dateipfads aus dem Aufgabenergebnis
    file_info = task.get('result')
    if not file_info or 'zipfile' not in file_info:
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="File not available"
        )

    file_path = file_info['zipfile']

    # Überprüfen, ob die Datei existiert
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail="File not found"
        )

    # Rückgabe der Datei als Antwort
    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=os.path.basename(file_path)
    )

@router.post("/aeroplanes/wings/{analysis_tool}")
async def analyze_wing_post(analysis_tool: AnalysisToolUrlType = AnalysisToolUrlType.AVL,
                            request: WingAnalysisRequest = Body(...)):
    """
    Analyze wings using AVL and return the analysis results.

    This endpoint accepts wing configurations in the request body and performs AVL analysis.

    Args:
        request: The wing analysis request containing wing configurations and operating parameters

    Returns:
        AvlAnalysisModel: The AVL analysis results
    """
    try:
        # Create a temporary directory

        # Convert wings from the request to WingConfiguration objects
        wings = {key: create_wing_configuration(value) for key, value in request.wings.items()}

        # Create an AirplaneConfiguration object
        airplane_config = AirplaneConfiguration(
            name="Temporary Airplane",
            total_mass_kg=1.0,  # Default mass
            wings=list(wings.values()),
            fuselages=None
        )

        # Create the atmosphere
        atmosphere = asb.Atmosphere(
            altitude=request.altitude
        )

        # Create the operating point
        op_point = asb.OperatingPoint(
            velocity=request.velocity,
            alpha=request.alpha,
            beta=request.beta,
            p=request.p,
            q=request.q,
            r=request.r,
            atmosphere=atmosphere
        )

        asb_airplane = airplane_config.asb_airplane
        asb_airplane.xyz_ref = request.xyz_ref

        if analysis_tool == AnalysisToolUrlType.AVL:
            # Run the AVL analysis
            avl = asb.AVL(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=request.xyz_ref
            )

            # Get the results
            avl_results = avl.run()
            analysis_model = AvlAnalysisModel.from_avl_dict(avl_results)
        elif analysis_tool == AnalysisToolUrlType.AEROBUILDUP:
            abu = asb.AeroBuildup(
                airplane=asb_airplane,
                    op_point=op_point,
                    xyz_ref=request.xyz_ref
                )

            # Get the results
            abu_results = abu.run_with_stability_derivatives()
            analysis_model = AvlAnalysisModel.from_abu_dict(
                abu_results,
                asb_airplan=asb_airplane
            )
        elif analysis_tool == AnalysisToolUrlType.VORTEX_LATTICE:
            vlm = asb.VortexLatticeMethod(
                airplane=asb_airplane,
                op_point=op_point,
                xyz_ref=request.xyz_ref
            )

            # Get the results
            vlm_results = vlm.run_with_stability_derivatives()
            analysis_model = AvlAnalysisModel.from_abu_dict(
                vlm_results,
                asb_airplan=asb_airplane
            )
            pass


        # Convert to AvlAnalysisModel

        # Return the results
        return analysis_model

    except Exception as err:
        logging.error(f"Error analyzing wing: {str(err)}")
        raise HTTPException(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(err)
        )
