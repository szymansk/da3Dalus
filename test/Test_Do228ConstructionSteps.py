import sys

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position
from Airplane.creator.EngineCapeShapeCreator import EngineCapeShapeCreator
from Airplane.creator.EngineMountPanelShapeCreator import EngineMountPanelShapeCreator
from Airplane.creator.EngineMountShapeCreator import EngineMountShapeCreator
from Airplane.creator.FuselageElectronicsAccessCutOutShapeCreator import FuselageElectronicsAccessCutOutShapeCreator
from Airplane.creator.FuselageReinforcementShapeCreator import FuselageReinforcementShapeCreator
from Airplane.creator.FuselageWingSupportShapeCreator import FuselageWingSupportShapeCreator
from Airplane.creator.StepImportCreator import StepImportCreator

if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.INFO, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="punisher")

    full_wing_loft_node = ConstructionStepNode(
        StepImportCreator("full_wing_loft",
                          step_file="../components/aircraft/punisher/wing_right.step",
                          scale=0.0001))
    root_node.append(full_wing_loft_node)

    full_fuselage_loft_node = ConstructionStepNode(
        StepImportCreator("full_fuselage_loft",
                          step_file="../components/aircraft/punisher/fuselage.step",
                          scale=0.0001))
    root_node.append(full_fuselage_loft_node)

    # full_elevator_loft_node = ConstructionStepNode(
    #     FullWingLoftShapeCreator("elevator",
    #                              right_main_wing_index=2))
    # root_node.append(full_elevator_loft_node)

    # wing_attachment_bolt_node = ConstructionStepNode(
    #     WingAttachmentBoltHolesShapeCreator("attachment_bolts",
    #                                         fuselage_loft="full_fuselage_loft",
    #                                         full_wing_loft="full_wing_loft"))
    # root_node.append(wing_attachment_bolt_node)

    # servo_shape_import = ConstructionStepNode(
    #     IgesImportCreator("servo",
    #                       iges_file="../components/servos/unknown/Servo.iges",
    #                       trans_x=0.67,
    #                       trans_y=-0.02066,
    #                       trans_z=.0,
    #                       rot_x=.0,
    #                       rot_y=90.0,
    #                       rot_z=-90.0 + 3.4,
    #                       scale=0.001))
    # root_node.append(servo_shape_import)
    #
    # stamp_shape_import = ConstructionStepNode(
    #     IgesImportCreator("servo_stamp",
    #                       iges_file="../components/servos/unknown/servo_stamp.iges",
    #                       trans_x=0.67,
    #                       trans_y=-0.02066,
    #                       trans_z=.0,
    #                       rot_x=.0,
    #                       rot_y=90.0,
    #                       rot_z=-90.0 + 3.4,
    #                       scale=0.001))
    # root_node.append(stamp_shape_import)
    #
    # stamp_fill_shape_import = ConstructionStepNode(
    #     IgesImportCreator("servo_stamp_fill",
    #                       iges_file="../components/servos/unknown/servo_stamp_fill.iges",
    #                       trans_x=0.67,
    #                       trans_y=-0.02066,
    #                       trans_z=.0,
    #                       rot_x=.0,
    #                       rot_y=90.0,
    #                       rot_z=-90.0 + 3.4,
    #                       scale=0.001))
    # root_node.append(stamp_fill_shape_import)

    # #########

    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount", engine_index=1, mount_plate_thickness=0.005,
                                engine_screw_hole_circle=0.042, engine_mount_box_length=0.0133 * 2.5,
                                engine_screw_din_diameter=0.0032, engine_screw_length=0.016,
                                engine_total_cover_length=None, engine_down_thrust_deg=None,
                                engine_side_thrust_deg=None))
    root_node.append(engine_mount_node)

    engine_panel_node = ConstructionStepNode(
        EngineMountPanelShapeCreator("engine_mount_plate", engine_index=1, mount_plate_thickness=0.005,
                                     engine_screw_hole_circle=0.042, engine_mount_box_length=0.0133 * 2.5,
                                     engine_total_cover_length=None, engine_side_thrust_deg=None,
                                     engine_down_thrust_deg=None, full_fuselage_loft="full_fuselage_loft"))
    engine_mount_node.append(engine_panel_node)

    fuse_mount_with_plate = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount"))
    engine_panel_node.append(fuse_mount_with_plate)

    # engine mount END

    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", engine_index=1, mount_plate_thickness=0.005 + 0.0008,
                               engine_mount_box_length=0.0133 * 2.5, engine_total_cover_length=0.0452,
                               full_fuselage_loft="full_fuselage_loft"))
    root_node.append(engine_cape_node)

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement_0", rib_width=0.001, rib_spacing=0.003,
                                          ribcage_factor=0.5, reinforcement_pipes_diameter=0.002, print_resolution=0.2,
                                          fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft"))
    root_node.append(fuselage_reinforcement_node)

    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support", rib_quantity=6, rib_width=0.0008, rib_height_factor=1,
                                        rib_z_offset=0, fuselage_loft="engine_cape.loft",
                                        full_wing_loft="full_wing_loft"))
    root_node.append(wing_support_node)

    # full_elevator_support_loft_node = ConstructionStepNode(
    #     FuselageWingSupportShapeCreator("elevator_support", rib_quantity=8, rib_width=0.0004, rib_height_factor=20,
    #                                     fuselage_loft="engine_cape.loft", full_wing_loft="elevator"))
    # engine_cape_node.append(full_elevator_support_loft_node)

    fuse_fuselage_reinforcements = ConstructionStepNode(
        FuseMultipleShapesCreator("fuselage_reinforcement_1",
                                  shapes=["fuselage_reinforcement_0",
                                          # "servo",
                                          "wing_support",
                                          # "elevator_support",
                                          ]))
    root_node.append(fuse_fuselage_reinforcements)

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout", ribcage_factor=0.5, length_factor=0.8,
                                                    fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft",
                                                    wing_position=None))
    root_node.append(electronics_access_node)
    # -> "electronics_cutout"

    reinforcement_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_reinforcement",
                          minuend="fuselage_reinforcement_1",
                          subtrahend="electronics_cutout"
                          ))
    root_node.append(reinforcement_node)

    # holes_in_engine_mount = ConstructionStepNode(
    #     Cut2ShapesCreator("engine_mount",
    #                       minuend="engine_mount"))
    # reinforcement_node.append(holes_in_engine_mount)

    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="engine_cape.loft",
                                # shape_b="reinforcement2"
                                ))
    reinforcement_node.append(internal_structure_node)

    offset_fuselage_node = ConstructionStepNode(
        SimpleOffsetShapeCreator("offset_fuselage",
                                 shape="engine_cape.loft",
                                 offset=0.0008))
    root_node.append(offset_fuselage_node)

    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="offset_fuselage",
                          subtrahend="internal_structure"))
    offset_fuselage_node.append(reinforced_fuselage_node)

    # fuse_servo_with_final_fuselage_node = ConstructionStepNode(
    #     Fuse2ShapesCreator("final_fuselage",
    #                        # shape_a="final_fuselage",
    #                        shape_b="servo_stamp"
    #                        ))
    # reinforced_fuselage_node.append(fuse_servo_with_final_fuselage_node)

    cut_wing_from_fuselage_node = ConstructionStepNode(
        CutMultipleShapesCreator("final_fuselage",
                                 subtrahends=["full_wing_loft",
                                              # "elevator",
                                              # "attachment_bolts",
                                              # "servo_stamp_fill",
                                              "engine_mount"
                                              ]))
    reinforced_fuselage_node.append(cut_wing_from_fuselage_node)

    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer", number_of_parts=5))
    cut_wing_from_fuselage_node.append(shape_slicer_node)
    # "final_fuselage" -> "fuselage_slicer[0] .. [4]"

    shape_stl_export_node = ConstructionStepNode(
        ExportToStlCreator("stl_exporter", shapes_to_export=["engine_mount",
                                                             "engine_cape.cape",
                                                             "final_fuselage[0]",
                                                             "final_fuselage[1]",
                                                             "final_fuselage[2]",
                                                             "final_fuselage[3]",
                                                             "final_fuselage[4]",
                                                             "elevator[1]",
                                                             "rudder"]))
    # >>>> root_node.append(shape_stl_export_node)
    # "fuselage_slicer[0] .. [4]", "engine_mount", "engine_cape.cape",
    # "elevator[0]", "elevator[1]", "rudder_with_slot" -> *

    engine_info1 = EngineInformation(down_thrust=-2.5, side_thrust=-2.5 - 180, position=Position(1.048, 0, 0),
                                     length=0.0512, width=0.035, height=0.035, screw_hole_circle=0.042,
                                     mount_box_length=0.0133 * 2.5, screw_din_diameter=0.0032, screw_length=0.016)

    # engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration)}
    engine_information = {1: engine_info1}

    brushless_shape_import = ConstructionStepNode(
        IgesImportCreator("brushless", iges_file="../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.iges",
                          trans_x=engine_information[1].position.get_x(),
                          trans_y=engine_information[1].position.get_y(),
                          trans_z=engine_information[1].position.get_z(), rot_x=0,
                          rot_y=engine_information[1].down_thrust, rot_z=engine_information[1].side_thrust,
                          scale=0.001))
    root_node.append(brushless_shape_import)
    #
    # servo_model_import = ConstructionStepNode(
    #     StepImportCreator("servo_model",
    #                       step_file="../components/servos/AS215BBMG v4.step",
    #                       trans_x=0.67,
    #                       trans_y=-0.02066,
    #                       trans_z=.0,
    #                       rot_x=90.0,
    #                       rot_y=0.0,
    #                       rot_z=3.4,
    #                       scale=0.001))
    # root_node.append(servo_model_import)

    lipo_model_import = ConstructionStepNode(
        IgesImportCreator("lipo_model", iges_file="../components/lipo/D-Power HD-2200 4S Lipo (14,8V) 30C v1.iges",
                          trans_x=0.09, trans_y=0.0, trans_z=-0.029, rot_x=0.0, rot_y=0.0, rot_z=0, scale=0.001))
    root_node.append(lipo_model_import)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}_{CPACS_FILE_NAME}").stem,
                            file_path="../exports",
                            shapes_to_export=["engine_mount",
                                              "brushless",
                                              "lipo_model",
                                              "engine_cape.cape",
                                              "engine_cape.loft",
                                              # "servo_model",
                                              "full_wing_loft"
                                              ]))
    root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration,
                                             engine_information=engine_information)

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
