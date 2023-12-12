import sys

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.JSONStepNode import JSONStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.creator.EngineCapeShapeCreator import EngineCapeShapeCreator
from Airplane.creator.EngineMountPanelShapeCreator import EngineMountPanelShapeCreator
from Airplane.creator.EngineMountShapeCreator import EngineMountShapeCreator
from Airplane.creator.FuselageElectronicsAccessCutOutShapeCreator import FuselageElectronicsAccessCutOutShapeCreator
from Airplane.creator.FuselageReinforcementShapeCreator import FuselageReinforcementShapeCreator
from Airplane.creator.FuselageWingSupportShapeCreator import FuselageWingSupportShapeCreator
from Airplane.creator.StepImportCreator import StepImportCreator
from Airplane.creator.WingAttachmentBoltCutoutShapeCreator import WingAttachmentBoltCutoutShapeCreator

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
    root_node = ConstructionRootNode(creator_id="root")

    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("full_wing_loft",
                                 right_main_wing_index=1))
    root_node.append(full_wing_loft_node)

    # full_wing_node = ConstructionStepNode(
    #     FullWingShapeCreator("full_wing", right_main_wing_index=1))
    # root_node.append(full_wing_node)

    full_fuselage_loft_node = ConstructionStepNode(
        FullFuselageLoftShapeCreator("full_fuselage_loft", fuselage_index=1))
    root_node.append(full_fuselage_loft_node)

    full_elevator_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("elevator",
                                 right_main_wing_index=2))
    root_node.append(full_elevator_loft_node)
    # -> "elevator"

    full_rudder_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("rudder",
                                 right_main_wing_index=3))
    full_elevator_loft_node.append(full_rudder_loft_node)
    # -> "rudder"

    cut_rudder_from_elevator_node = ConstructionStepNode(
        Cut2ShapesCreator("rudder",
                          # minuend="rudder",
                          subtrahend="elevator"))
    full_rudder_loft_node.append(cut_rudder_from_elevator_node)
    # "rudder" - "elevator" -> "rudder_with_slot"

    elevator_slicer_node = ConstructionStepNode(
        SliceShapesCreator("elevators", number_of_parts=2))
    full_elevator_loft_node.append(elevator_slicer_node)
    # "elevator" -> "elevator[0]", "elevator[1]"

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

    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", engine_index=1, mount_plate_thickness=0.005 + 0.0008,
                               engine_mount_box_length=0.0133 * 2.5, engine_total_cover_length=0.0452,
                               full_fuselage_loft="full_fuselage_loft"))
    root_node.append(engine_cape_node)
    # -> "engine_cape.cape", "engine_cape.loft"

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement", rib_width=0.001, rib_spacing=0.003,
                                          ribcage_factor=0.5, reinforcement_pipes_diameter=0.002, print_resolution=0.2,
                                          fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft"))
    engine_cape_node.append(fuselage_reinforcement_node)
    # "engine_cape.loft" -> "fuselage_reinforcement"

    servo_shape_import = ConstructionStepNode(
        IgesImportCreator("servo", iges_file="../components/servos/unknown/Servo.iges", trans_x=0.67, trans_y=-0.02066,
                          trans_z=.0, rot_x=.0, rot_y=90.0, rot_z=-90.0 + 3.4, scale=0.001))
    fuselage_reinforcement_node.append(servo_shape_import)
    # -> "servo"

    fuse_servo_with_fuselage = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="servo"
                           ))
    servo_shape_import.append(fuse_servo_with_fuselage)
    # "fuselage_reinforcement" + "servo" -> "reinforcement3"

    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support", rib_quantity=6, rib_width=0.0008, rib_height_factor=1,
                                        rib_z_offset=0, fuselage_loft="engine_cape.loft",
                                        full_wing_loft="full_wing_loft"))
    fuse_servo_with_fuselage.append(wing_support_node)
    # -> "wing_support"

    fuse_reinforcement_wing_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="wing_support"
                           ))
    wing_support_node.append(fuse_reinforcement_wing_sup_node)
    # "reinforcement3" + "wing_support" -> "reinforcement0"

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support", rib_quantity=8, rib_width=0.0004, rib_height_factor=20,
                                        rib_z_offset=0, fuselage_loft="engine_cape.loft", full_wing_loft="elevator"))
    fuse_reinforcement_wing_sup_node.append(full_elevator_support_loft_node)
    # -> "elevator_support"

    fuse_reinforcement_elevator_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="elevator_support"
                           ))
    full_elevator_support_loft_node.append(fuse_reinforcement_elevator_sup_node)
    # "reinforcement0 + "elevator_support" -> "reinforcement1"

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout", ribcage_factor=0.5, length_factor=0.8,
                                                    fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft",
                                                    wing_position=None))
    fuse_reinforcement_elevator_sup_node.append(electronics_access_node)
    # -> "electronics_cutout"

    reinforcement_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_reinforcement",
                          minuend="fuselage_reinforcement",
                          # subtrahend="electronics_cutout"
                          ))
    electronics_access_node.append(reinforcement_node)
    # "reinforcement1" - "electronics_cutout" -> "reinforcement2"

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
    # "engine_cape.loft" / "reinforcement2" -> "internal_structure"

    offset_fuselage_node = ConstructionStepNode(
        SimpleOffsetShapeCreator("final_fuselage",
                                 shape="engine_cape.loft",
                                 offset=0.0008))
    internal_structure_node.append(offset_fuselage_node)
    # "engine_cape.loft" -> "offset_fuselage"

    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          # minuend="offset_fuselage",
                          subtrahend="internal_structure"))
    offset_fuselage_node.append(reinforced_fuselage_node)
    # "offset_fuselage" - "internal_structure" -> "reinforced_fuselage",


    load_create_fullwing_from_json = JSONStepNode(json_file_path="../components/constructions/wings.root.json",
                                                  cpacs_configuration=ccpacs_configuration)
    reinforced_fuselage_node.append(load_create_fullwing_from_json)
    # -> "wings"

    cut_wing_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="wings"
                          ))
    load_create_fullwing_from_json.append(cut_wing_from_fuselage_node)
    # "reinforced_fuselage" - "wings" -> "fuselage_wo_wings"

    cut_elevator_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          # minuend="fuselage_wo_wings",
                          subtrahend="elevator"))
    cut_wing_from_fuselage_node.append(cut_elevator_from_fuselage_node)
    # "fuselage_wo_wings" - "elevator" -> "fuselage_wo_elevator"

    wing_attachment_bolt_node = ConstructionStepNode(
        WingAttachmentBoltCutoutShapeCreator("attachment_bolts", fuselage_loft="engine_cape.loft",
                                             full_wing_loft="full_wing_loft", bolt_diameter=6))
    cut_elevator_from_fuselage_node.append(wing_attachment_bolt_node)
    # -> "attachment_bolts"

    cut_bolts_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="attachment_bolts"
                          ))
    wing_attachment_bolt_node.append(cut_bolts_from_fuselage_node)
    # "fuselage_wo_elevator" - "attachment_bolts" -> "final_fuselage"

    stamp_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp", iges_file="../components/servos/unknown/servo_stamp.iges", trans_x=0.67,
                          trans_y=-0.02066, trans_z=.0, rot_x=.0, rot_y=90.0, rot_z=-90.0 + 3.4, scale=0.001))
    cut_bolts_from_fuselage_node.append(stamp_shape_import)
    # -> "servo_stamp"

    cut_servo_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="servo_stamp"
                          ))
    stamp_shape_import.append(cut_servo_from_fuselage_node)
    # "final_fuselage" - "servo_stamp" -> "final_fuselage"

    fuse_servo_with_final_fuselage_node = ConstructionStepNode(
        Fuse2ShapesCreator("final_fuselage",
                           shape_a="final_fuselage",
                           # shape_b="servo_stamp"
                           ))
    stamp_shape_import.append(fuse_servo_with_final_fuselage_node)
    # "final_fuselage" + "servo_stamp" -> "final_fuselage"

    stamp_fill_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp_fill", iges_file="../components/servos/unknown/servo_stamp_fill.iges",
                          trans_x=0.67, trans_y=-0.02066, trans_z=.0, rot_x=.0, rot_y=90.0, rot_z=-90.0 + 3.4,
                          scale=0.001))
    fuse_servo_with_final_fuselage_node.append(stamp_fill_shape_import)
    # -> "servo_stamp"

    cut_servo_fill_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="servo_stamp_fill"
                          ))
    stamp_fill_shape_import.append(cut_servo_fill_from_fuselage_node)
    # "final_fuselage" - "servo_stamp" -> "final_fuselage"

    # offset_cape_node = ConstructionStepNode(
    #     SimpleOffsetShapeCreator("engine_cape.big",
    #                              shape="engine_cape.cape",
    #                              offset=0.0008))
    # cut_servo_fill_from_fuselage_node.append(offset_cape_node)
    # "engine_cape.loft" -> "offset_fuselage"

    cut_engine_mount_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          subtrahend="engine_mount"
                          ))
    cut_servo_fill_from_fuselage_node.append(cut_engine_mount_from_fuselage_node)

    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer", number_of_parts=5))
    cut_engine_mount_from_fuselage_node.append(shape_slicer_node)
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
    # >>>> shape_slicer_node.append(shape_stl_export_node)
    # "fuselage_slicer[0] .. [4]", "engine_mount", "engine_cape.cape",
    # "elevator[0]", "elevator[1]", "rudder_with_slot" -> *

    brushless_shape_import = ConstructionStepNode(
        IgesImportCreator("brushless", iges_file="../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.iges",
                          trans_x=.0, trans_y=.0, trans_z=.0, rot_x=.0, rot_y=-2.5, rot_z=-2.5, scale=0.001))
    root_node.append(brushless_shape_import)

    servo_model_import = ConstructionStepNode(
        StepImportCreator("servo_model",
                          step_file="../components/servos/AS215BBMG v4.step",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=90.0,
                          rot_y=0.0,
                          rot_z=3.4,
                          scale=0.001))
    root_node.append(servo_model_import)
    # -> "servo"

    lipo_model_import = ConstructionStepNode(
        IgesImportCreator("lipo_model", iges_file="../components/lipo/D-Power HD-2200 4S Lipo (14,8V) 30C v1.iges",
                          trans_x=0.09, trans_y=0.0, trans_z=-0.029, rot_x=0.0, rot_y=0.0, rot_z=0, scale=0.001))
    root_node.append(lipo_model_import)
    # -> "servo"

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(CPACS_FILE_NAME).stem,
                            file_path="../exports",
                            shapes_to_export=["engine_mount",
                                              "brushless",
                                              "lipo_model",
                                              #"engine_cape.big",
                                              "engine_cape.cape",
                                              "elevator",
                                              "final_fuselage",
                                              "rudder",
                                              "servo_model",
                                              "full_wing.right",
                                              "full_wing.left",
                                              "full_wing.right_ail",
                                              "full_wing.left_ail"
                                              ]))
    root_node.append(aircraft_step_export_node)
    # "engine_mount", "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->


    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration, 0.042, 0.0133 * 2.5, 0.0032, 0.016)}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration,
                                             engine_information=engine_information)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
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
