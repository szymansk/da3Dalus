import sys
import logging
from pathlib import Path

from tigl3.tigl3wrapper import Tigl3

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode, JSONStepNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position

# TODO: * cutouts for hinges
#       * cutout for elevator flap rod (carbon 1mm) in elvator and in rudder
#       * wings with servos for aileron and flaps
#       * cutouts for elevator and rudder rods (anlenkung carbonstab 1mm)
#       * ruderhörner

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.DEBUG, stream=sys.stdout)

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    base_scale = 0.04
    ribcage_factor = 0.35
    mount_plate_thickness = 0.005
    engine_screw_hole_circle = 0.042
    engine_mount_box_length = 0.0133 * 2.5

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")

    full_wing_loft_node = ConstructionStepNode(
        StepImportCreator("full_wing_loft",
                          step_file="../components/aircraft/RV-7/wing.step",
                          scale=base_scale))
    root_node.append(full_wing_loft_node)

    flaps_node = ConstructionStepNode(
        StepImportCreator("flaps",
                          step_file="../components/aircraft/RV-7/flaps.step",
                          scale=base_scale))
    root_node.append(flaps_node)

    aileron_node = ConstructionStepNode(
        StepImportCreator("aileron",
                          step_file="../components/aircraft/RV-7/aileron.step",
                          scale=base_scale))
    root_node.append(aileron_node)

    full_fuselage_loft_node = ConstructionStepNode(
        StepImportCreator("full_fuselage",
                          step_file="../components/aircraft/RV-7/fuselage.step",
                          scale_x=base_scale,
                          scale_y=base_scale - base_scale*0.01,
                          scale_z=base_scale - base_scale*0.01))
    root_node.append(full_fuselage_loft_node)

    offset_fuselage_node = ConstructionStepNode(
        StepImportCreator("offset_fuselage",
                          step_file="../components/aircraft/RV-7/fuselage_inlets.step",
                          scale=base_scale))
    root_node.append(offset_fuselage_node)

    cockpit_node = ConstructionStepNode(
        StepImportCreator("cockpit",
                          step_file="../components/aircraft/RV-7/cockpit.step",
                          scale=base_scale))
    offset_fuselage_node.append(cockpit_node)

    cut_cockpit_node = ConstructionStepNode(
        Cut2ShapesCreator("cockpit"))
    cockpit_node.append(cut_cockpit_node)

    full_elevator_loft_node = ConstructionStepNode(
        StepImportCreator("elevator",
                          step_file="../components/aircraft/RV-7/full_elevator_straight.step",
                          scale=base_scale))
    root_node.append(full_elevator_loft_node)

    rudder_loft_node = ConstructionStepNode(
        StepImportCreator("rudder",
                          step_file="../components/aircraft/RV-7/rudder_fix_final.step",
                          scale=base_scale))
    root_node.append(rudder_loft_node)

    rudder_flap_loft_node = ConstructionStepNode(
        StepImportCreator("rudder_flap",
                          step_file="../components/aircraft/RV-7/rudder_flap.step",
                          scale=base_scale))
    root_node.append(rudder_flap_loft_node)

    elevator_flap_loft_node = ConstructionStepNode(
        StepImportCreator("elevator_flap",
                          step_file="../components/aircraft/RV-7/elevator_flap_straight.step",
                          scale=base_scale))
    root_node.append(elevator_flap_loft_node)

    elevator_servo_shape_import = ConstructionStepNode(
        ServoImporterCreator("elevator_servo",
                             servo_feature="../components/servos/unknown/servo_24x24x12_inside.step",
                             servo_stamp="../components/servos/unknown/servo_24x24x12_inside_stamp.step",
                             servo_filling=None,
                             servo_model="../components/servos/AS215BBMG_left.step",
                             servo_idx=1))
    root_node.append(elevator_servo_shape_import)

    rudder_servo_shape_import = ConstructionStepNode(
        ServoImporterCreator("rudder_servo",
                             servo_feature="../components/servos/unknown/servo_24x24x12_inside.step",
                             servo_stamp="../components/servos/unknown/servo_24x24x12_inside_stamp.step",
                             servo_filling=None,
                             servo_model="../components/servos/AS215BBMG.step",
                             servo_idx=2))
    root_node.append(rudder_servo_shape_import)
    # #########

    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount", engine_index=1, mount_plate_thickness=mount_plate_thickness))
    root_node.append(engine_mount_node)

    engine_panel_node = ConstructionStepNode(
        EngineMountPanelShapeCreator("engine_mount_plate", engine_index=1, mount_plate_thickness=mount_plate_thickness,
                                     full_fuselage_loft="offset_fuselage"))
    engine_mount_node.append(engine_panel_node)

    fuse_mount_with_plate = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount"))
    engine_panel_node.append(fuse_mount_with_plate)

    # engine mount END

    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape_offset",
                               engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="offset_fuselage"))
    root_node.append(engine_cape_node)

    engine_cape_full_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="full_fuselage"))
    root_node.append(engine_cape_full_node)

    # wing_attachment_bolt_node = ConstructionStepNode(
    #     WingAttachmentBoltHolesShapeCreator("attachment_bolts",
    #                                         fuselage_loft="engine_cape_offset.loft",
    #                                         #fuselage_loft="offset_fuselage",
    #                                         full_wing_loft="full_wing_loft"))
    # root_node.append(wing_attachment_bolt_node)

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement_0", rib_width=0.001, rib_spacing=0.00,  # 3,
                                          ribcage_factor=ribcage_factor, reinforcement_pipes_radius=0.002,
                                          fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft"))
    root_node.append(fuselage_reinforcement_node)

    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support", rib_quantity=6, rib_width=0.0008, rib_height_factor=1,
                                        fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft"))
    root_node.append(wing_support_node)

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support", rib_quantity=8, rib_width=0.0004, rib_height_factor=20,
                                        fuselage_loft="engine_cape.loft", full_wing_loft="elevator"))
    wing_support_node.append(full_elevator_support_loft_node)

    fuse_fuselage_reinforcements = ConstructionStepNode(
        FuseMultipleShapesCreator("fuselage_reinforcement_1",
                                  shapes=["fuselage_reinforcement_0",
                                          "elevator_servo.feature",
                                          "rudder_servo.feature",
                                          "wing_support",
                                          "elevator_support",
                                          ]))
    root_node.append(fuse_fuselage_reinforcements)

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
                                                    ribcage_factor=ribcage_factor,
                                                    length_factor=0.8,
                                                    fuselage_loft="engine_cape.loft",
                                                    full_wing_loft="full_wing_loft",
                                                    wing_position=None))
    root_node.append(electronics_access_node)

    reinforcement_node = ConstructionStepNode(
        CutMultipleShapesCreator("fuselage_reinforcement",
                                 minuend="fuselage_reinforcement_1",
                                 subtrahends=["electronics_cutout",
                                              "elevator_servo.stamp",
                                              "rudder_servo.stamp",
                                              #"attachment_bolts"
                                              ],
                                 loglevel=logging.DEBUG
                                 ))
    root_node.append(reinforcement_node)

    holes_in_engine_mount = ConstructionStepNode(
        Cut2ShapesCreator("engine_mount",
                          minuend="engine_mount"))
    reinforcement_node.append(holes_in_engine_mount)

    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="engine_cape.loft",
                                # shape_b="reinforcement2"
                                ))
    reinforcement_node.append(internal_structure_node)

    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          #  minuend="engine_cape.loft",
                          minuend="engine_cape_offset.loft",
                          subtrahend="internal_structure"))
    internal_structure_node.append(reinforced_fuselage_node)

    cut_wing_from_fuselage_node = ConstructionStepNode(
        CutMultipleShapesCreator("final_fuselage",
                                 minuend="final_fuselage",
                                 subtrahends=["full_wing_loft",
                                              "elevator",
                                              "rudder",
                                              #"attachment_bolts",
                                              #"elevator_servo.filling",
                                              #"rudder_servo.filling",
                                              "engine_mount"
                                              ]))
    reinforced_fuselage_node.append(cut_wing_from_fuselage_node)

    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer",
                           shapes_to_slice=["final_fuselage"],
                           number_of_parts=5))
    cut_wing_from_fuselage_node.append(shape_slicer_node)

    rudder_cut_elevator_node = ConstructionStepNode(
        Cut2ShapesCreator("elevator_cut",
                          minuend="elevator",
                          subtrahend="rudder"))
    root_node.append(rudder_cut_elevator_node)

    elevator_slicer_node = ConstructionStepNode(
        SliceShapesCreator("elevator_slicer",
                           shapes_to_slice=["elevator"],
                           number_of_parts=2))
    rudder_cut_elevator_node.append(elevator_slicer_node)

    brushless_shape_import = ConstructionStepNode(
        ComponentImporterCreator("brushless",
                                 component_file="../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.iges",
                                 component_idx="brushless"))
    root_node.append(brushless_shape_import)

    lipo_model_import = ConstructionStepNode(
        ComponentImporterCreator("lipo_model",
                                 component_file="../components/lipo/D-Power HD-2200 4S Lipo (14,8V) 30C v1.iges",
                                 component_idx="lipo"))
    root_node.append(lipo_model_import)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=["engine_mount",
                                              "brushless",
                                              "lipo_model",
                                              "engine_cape_offset.cape",
                                              "final_fuselage",
                                              "full_wing_loft",
                                              "final_fuselage[0]",
                                              "final_fuselage[1]",
                                              "final_fuselage[2]",
                                              "final_fuselage[3]",
                                              "final_fuselage[4]",
                                              "elevator",
                                              #"elevator_cut[0]",
                                              #"elevator_cut[1]",
                                              "elevator_flap",
                                              "rudder",
                                              "rudder_flap",
                                              "flaps",
                                              "aileron",
                                              "cockpit",
                                              "elevator_servo.model",
                                              "rudder_servo.model"
                                              ]))
    root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    servo_elevator = ServoInformation(
        height=0.022,
        width=0.012,
        length=0.023,
        lever_length=0.023,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28+0.02,
        trans_y=0.005,
        trans_z=0.044-0.0244)

    servo_rudder = ServoInformation(
        height=0.022,
        width=0.012,
        length=0.023,
        lever_length=0.023,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28+0.02,
        trans_y=-0.005-0.012,
        trans_z=0.044-0.0244)
    servo_information = {1: servo_elevator, 2: servo_rudder}

    engine_info1 = EngineInformation(down_thrust=-2.5, side_thrust=-2.5, position=Position(0.0458, 0, 0), length=0.0452,
                                     width=0.035, height=0.035, screw_hole_circle=0.042, mount_box_length=0.0133 * 2.5,
                                     screw_din_diameter=0.0032, screw_length=0.016)

    # engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration)}
    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031, height=0.035, length=0.108,
                                            trans_x=0.129, trans_y=0.0, trans_z=-0.021,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
                                             servo_information=servo_information,
                                             component_information=component_information)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
    json_file_path = f"../components/constructions/{root_node.identifier}.json"
    json_file = open(json_file_path, "w")
    json.dump(fp=json_file, obj=root_node, indent=4, cls=GeneralJSONEncoder)
    json_file.close()

    try:
        # build on basis of deserialized json
        structure = myMap.create_shape()
        from pprint import pprint

        pprint(structure)
        shapeDisplay.start()
    except Exception as err:
        shapeDisplay.start()
        raise err
    pass
