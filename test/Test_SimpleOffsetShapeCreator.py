import sys
import logging
from pathlib import Path

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode, JSONStepNode
from Airplane.FuselageConstructionSteps import FullWingLoftShapeCreator, Cut2ShapesCreator, SliceShapesCreator, \
    EngineMountShapeCreator, EngineCapeShapeCreator, FuselageReinforcementShapeCreator, IgesImportCreator, \
    Fuse2ShapesCreator, FuselageWingSupportShapeCreator, FuselageElectronicsAccessCutOutShapeCreator, \
    Intersect2ShapesCreator, SimpleOffsetShapeCreator, WingAttachmentBoltHolesShapeCreator, ExportToStlCreator, \
    StepImportCreator, ExportToIgesCreator, ExportToStepCreator
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.DEBUG, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)



    # =============
    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="root")


    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", fuselage_index=1, engine_index=1, engine_total_cover_length=0.0452,
                               engine_mount_box_length=0.0133 * 2.5, mount_plate_thickness=0.005))
    root_node.append(engine_cape_node)
    # -> "engine_cape.cape", "engine_cape.loft"

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement", rib_width=0.001, rib_spacing=0.003,
                                          ribcage_factor=0.5, reinforcement_pipes_radius=0.002,
                                          fuselage_loft="engine_cape.loft", full_wing_loft="full_wing_loft"))
    engine_cape_node.append(fuselage_reinforcement_node)
    # "engine_cape.loft" -> "fuselage_reinforcement"

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
    # fuselage_reinforcement_node.append(servo_shape_import)
    # # -> "servo"
    #
    # fuse_servo_with_fuselage = ConstructionStepNode(
    #     Fuse2ShapesCreator("fuselage_reinforcement",
    #                        shape_a="fuselage_reinforcement",
    #                        # shape_b="servo"
    #                        ))
    # servo_shape_import.append(fuse_servo_with_fuselage)
    # # "fuselage_reinforcement" + "servo" -> "reinforcement3"
    #
    # wing_support_node = ConstructionStepNode(
    #     FuselageWingSupportShapeCreator("wing_support",
    #                                     fuselage_index=1,
    #                                     right_main_wing_index=1,
    #                                     rib_quantity=6,
    #                                     rib_width=0.0008,
    #                                     rib_height_factor=1))
    # fuse_servo_with_fuselage.append(wing_support_node)
    # # -> "wing_support"
    #
    # fuse_reinforcement_wing_sup_node = ConstructionStepNode(
    #     Fuse2ShapesCreator("fuselage_reinforcement",
    #                        shape_a="fuselage_reinforcement",
    #                        # shape_b="wing_support"
    #                        ))
    # wing_support_node.append(fuse_reinforcement_wing_sup_node)
    # # "reinforcement3" + "wing_support" -> "reinforcement0"
    #
    # full_elevator_support_loft_node = ConstructionStepNode(
    #     FuselageWingSupportShapeCreator("elevator_support",
    #                                     fuselage_index=1,
    #                                     right_main_wing_index=2,
    #                                     rib_quantity=8,
    #                                     rib_width=0.0004,
    #                                     rib_height_factor=20))
    # fuse_reinforcement_wing_sup_node.append(full_elevator_support_loft_node)
    # # -> "elevator_support"
    #
    # fuse_reinforcement_elevator_sup_node = ConstructionStepNode(
    #     Fuse2ShapesCreator("fuselage_reinforcement",
    #                        shape_a="fuselage_reinforcement",
    #                        # shape_b="elevator_support"
    #                        ))
    # full_elevator_support_loft_node.append(fuse_reinforcement_elevator_sup_node)
    # # "reinforcement0 + "elevator_support" -> "reinforcement1"
    #
    # electronics_access_node = ConstructionStepNode(
    #     FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
    #                                                 fuselage_index=1,
    #                                                 ribcage_factor=0.5,
    #                                                 right_main_wing_index=1,
    #                                                 wing_position=None))
    # fuse_reinforcement_elevator_sup_node.append(electronics_access_node)
    # # -> "electronics_cutout"
    #
    # reinforcement_node = ConstructionStepNode(
    #     Cut2ShapesCreator("fuselage_reinforcement",
    #                       minuend="fuselage_reinforcement",
    #                       # subtrahend="electronics_cutout"
    #                       ))
    # electronics_access_node.append(reinforcement_node)
    # # "reinforcement1" - "electronics_cutout" -> "reinforcement2"

    offset_fuselage_node = ConstructionStepNode(
        SimpleOffsetShapeCreator("offset_fuselage",
                                 shape="engine_cape.loft",
                                 offset=-0.0008))
    fuselage_reinforcement_node.append(offset_fuselage_node)
    # "engine_cape.loft" -> "offset_fuselage"

    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="offset_fuselage",
                                shape_b="fuselage_reinforcement"
                                ))
    offset_fuselage_node.append(internal_structure_node)
    # "engine_cape.loft" / "reinforcement2" -> "internal_structure"


    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="engine_cape.loft",
                          #subtrahend="internal_structure"
                          ))
    internal_structure_node.append(reinforced_fuselage_node)
    # "offset_fuselage" - "internal_structure" -> "reinforced_fuselage",


    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer", number_of_parts=5))
    reinforced_fuselage_node.append(shape_slicer_node)
    # "final_fuselage" -> "fuselage_slicer[0] .. [4]"


    shape_stl_export_node = ConstructionStepNode(
        ExportToStlCreator("stl_exporter", None))
    shape_slicer_node.append(shape_stl_export_node)

    mount_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(CPACS_FILE_NAME).stem,
                            file_path="../exports",
                            shapes_to_export=["final_fuselage"]))
    root_node.append(mount_step_export_node)
    # "engine_mount", "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
    try:
        # build on basis of deserialized json
        structure = myMap._create_shape(all_shapes, )
        from pprint import pprint

        pprint(structure)
    except Exception as err:
        logging.fatal(f"{err}")

    shapeDisplay.start()

    pass
