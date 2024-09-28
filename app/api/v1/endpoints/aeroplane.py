import json
import os
from json import JSONDecodeError
from os import PathLike
from pathlib import Path, PosixPath

from fastapi import APIRouter, HTTPException

from airplane import ConstructionStepNode, GeneralJSONDecoder
from airplane.aircraft_topology.components import ServoInformation, Servo
from airplane.aircraft_topology.printer3d import Printer3dSettings
from app.models.AeroplaneRequest import CreateAeroPlaneRequest
from app.models.wing import Wing
from app.services.create_wing_configuration import create_wing_configuration, create_servo

router = APIRouter()


@router.post("/aeroplanes/wings")
def create_wing(wing: Wing):
    wing_configuration = {"main_wing": create_wing_configuration(wing)}

    printer_settings = Printer3dSettings(layer_height=0.24,
                                         wall_thickness=0.42,
                                         rel_gap_wall_thickness=0.075)
    servo_aileron = ServoInformation(
        height=0,
        width=0,
        length=00,
        lever_length=0,
        servo=Servo(
            length=23,
            width=12.5,
            height=31.5,
            leading_length=6, latch_z=14.5,
            latch_x=7.25, latch_thickness=2.6,
            latch_length=6, cable_z=26,
            screw_hole_lx=0,
            screw_hole_d=0
        )
    )

    servo_information = {1: servo_aileron}

    construction_name = "eHawk-wing.root"
    json_file_path = os.path.abspath(f"./components/constructions/{construction_name}.json")
    json_file = open(json_file_path, "r")

    blue_print: ConstructionStepNode = json.load(json_file, cls=GeneralJSONDecoder,
                                                 wing_config=wing_configuration,
                                                 servo_information=servo_information,
                                                 printer_settings=printer_settings)
    try:
        structure = blue_print.create_shape()
        from pprint import pprint
        return {pprint(structure)}
    except ValueError as err:
        raise HTTPException(status_code=500, detail=err)
    except Exception as err:
        raise HTTPException(status_code=500, detail=err)


@router.post("/aeroplanes")
def create_aeroplane(request: CreateAeroPlaneRequest):
    try:
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
            ) for key, value in request.settings.servo_information.items()}

        if type(request.blueprint) is dict: # Any
            blue_print: ConstructionStepNode = json.loads(
                str(request.blueprint).replace("'",'"'),
                cls=GeneralJSONDecoder,
                wing_config=wings,
                fuselage_config=request.fuselages,
                **settings
            )
        elif os.path.isfile(request.blueprint):
            json_file = open(request.blueprint, "r")
            blue_print: ConstructionStepNode = json.load(
                json_file,
                cls=GeneralJSONDecoder,
                wing_config=wings,
                fuselage_config=request.fuselages,
                **settings
            )
        structure = blue_print.create_shape()
        from pprint import pprint
        return {pprint(structure)}
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="'blueprint' is not in a valid json format")
    except ValueError as err:
        raise HTTPException(status_code=500, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
