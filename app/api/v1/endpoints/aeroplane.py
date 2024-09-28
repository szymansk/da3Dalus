import http
import json
import os
import uuid
from json import JSONDecodeError
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from airplane import ConstructionStepNode, GeneralJSONDecoder
from airplane.aircraft_topology.components import ServoInformation, Servo
from airplane.aircraft_topology.printer3d import Printer3dSettings
from app.models.AeroplaneRequest import CreateAeroPlaneRequest
from app.models.wing import Wing
from app.services.create_wing_configuration import create_wing_configuration, create_servo

router = APIRouter()

# In-Memory-Aufgabenverwaltung
tasks = {}
tasks_lock = Lock()
executor = ThreadPoolExecutor(max_workers=4)  # Passen Sie die Anzahl der Worker an Ihre Bedürfnisse an

def create_aeroplane_task(task_id, request_dict):
    try:
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
        structure = blue_print.create_shape()

        zipfile = f"./tmp/{task_id}.zip"
        exports = "./tmp/exports"

        # zip files
        with ZipFile(zipfile, 'w') as zipf:
            for file in os.scandir(exports):
                zipf.write(file.path)

        # delete files
        for file in os.scandir(exports):
            os.unlink(file.path)

        result = {"zipfile": zipfile}
        with tasks_lock:
            tasks[task_id]['status'] = 'SUCCESS'
            tasks[task_id]['result'] = result
    except Exception as err:
        with tasks_lock:
            tasks[task_id]['status'] = 'FAILURE'
            tasks[task_id]['error'] = str(err)

@router.post("/aeroplanes")
async def create_aeroplane(request: CreateAeroPlaneRequest):
    try:
        task_id = str(uuid.uuid4())
        with tasks_lock:
            tasks[task_id] = {'status': 'PENDING'}
        executor.submit(create_aeroplane_task, task_id, request.dict())
        return JSONResponse(
            status_code= http.HTTPStatus.ACCEPTED,
            content={"task_id": task_id, "href": f"/aeroplanes/{task_id}"}
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.get("/aeroplanes/{aeroplane_id}")
async def get_aeroplane_task_status(aeroplane_id: str):
    with tasks_lock:
        task = tasks.get(aeroplane_id)
    if not task:
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail={"task_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": "Task not found"}
        )
    if task['status'] == 'PENDING':
        return JSONResponse(
            status_code= http.HTTPStatus.OK,
            content={"task_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'], "message": "Task is pending."}
        )
    elif task['status'] == 'FAILURE':
        return JSONResponse(
            status_code= http.HTTPStatus.OK,
            content={"task_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'], "message": task.get('error', 'An error occurred')}
        )
    elif task['status'] == 'SUCCESS':
        return JSONResponse(
            status_code= http.HTTPStatus.OK,
            content={"task_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'], "result": task.get('result')}
        )
    else:
        return JSONResponse(
            status_code= http.HTTPStatus.OK,
            content={"task_id": aeroplane_id, "href": f"/aeroplanes/{aeroplane_id}", "status": task['status'], "message": "Task is processing."}
        )

@router.get("/aeroplanes/{task_id}/zip")
async def download_aeroplane_zip(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task['status'] != 'SUCCESS':
        return JSONResponse(
            status_code=http.HTTPStatus.BAD_REQUEST,
            content={"detail": "Task not completed yet or failed"}
        )

    # Abrufen des Dateipfads aus dem Aufgabenergebnis
    file_info = task.get('result')
    if not file_info or 'zipfile' not in file_info:
        raise HTTPException(status_code=500, detail="File not available")

    file_path = file_info['zipfile']

    # Überprüfen, ob die Datei existiert
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Rückgabe der Datei als Antwort
    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=os.path.basename(file_path)
    )
