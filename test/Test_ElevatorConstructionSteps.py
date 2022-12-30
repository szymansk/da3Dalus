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
    StepImportCreator, ExportToIgesCreator, ExportToStepCreator, FullWingShapeCreator, EngineMountPanelShapeCreator
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)

    # ============
    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("wings",
                                 right_main_wing_index=1))

    full_wing_file_path = "../components/constructions/full_wing.json"
    full_wing_file = open(full_wing_file_path, "w")
    json.dump(fp=full_wing_file, obj=full_wing_loft_node, indent=4, cls=GeneralJSONEncoder)
    full_wing_file.close()

    # =============
    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="root")

    full_wing_node = ConstructionStepNode(
        FullWingShapeCreator("full_wing", right_main_wing_index=2))
    root_node.append(full_wing_node)


    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(CPACS_FILE_NAME).stem,
                            file_path="../exports",
                            shapes_to_export=["full_wing.right",
                                              "full_wing.left",
                                              # "full_wing.right_ail",
                                              # "full_wing.left_ail"
                                              ]))
    root_node.append(aircraft_step_export_node)
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
        structure = myMap.create_shape()
        from pprint import pprint
        shapeDisplay.start()
        pprint(structure)
    except Exception as err:
        shapeDisplay.start()
        raise err
    pass
