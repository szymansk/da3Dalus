import sys

import json 
import os

from Airplane.creator.Cut2ShapesCreator import Cut2ShapesCreator
from Airplane.creator.CutMultipleShapesCreator import CutMultipleShapesCreator
from Airplane.creator.Fuse2ShapesCreator import Fuse2ShapesCreator
from Airplane.creator.FuselageShellShapeCreator import FuselageShellShapeCreator
from Airplane.creator.Intersect2ShapesCreator import Intersect2ShapesCreator
from Airplane.creator.ServoImporterCreator import ServoImporterCreator
from Airplane.creator.SimpleOffsetShapeCreator import SimpleOffsetShapeCreator
from Airplane.creator.EngineCapeShapeCreator import EngineCapeShapeCreator
from Airplane.creator import EngineCoverAndMountPanelAndFuselageShapeCreator
from Airplane.creator.EngineMountShapeCreator import EngineMountShapeCreator
from Airplane.creator.FuselageElectronicsAccessCutOutShapeCreator import FuselageElectronicsAccessCutOutShapeCreator
from Airplane.creator.FuselageReinforcementShapeCreator import FuselageReinforcementShapeCreator
from Airplane.creator.FuselageWingSupportShapeCreator import FuselageWingSupportShapeCreator
from Airplane.creator.WingAttachmentBoltCutoutShapeCreator import WingAttachmentBoltCutoutShapeCreator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position, EngineInformation

# TODO: * cutouts for hinges
#       * cutout for elevator flap rod (carbon 1mm) in elvator and in rudder
#       * wings with servos for aileron and flaps
#       * cutouts for elevator and rudder rods (anlenkung carbonstab 1mm)
#       * ruderhörner der Anlenkpunkt sollte über der Drehachse liegen und der Abstand beider
#         Drehpunkte sollte mit dem Abstand der Anschlusspunkte übereinstimmen vergleich:
#         (https://www.rc-network.de/threads/die-kinematik-ungewollter-differenzierung.11779720/)

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.DEBUG, stream=sys.stdout)

    base_scale = 0.039*1000
    ribcage_factor = 0.5
    mount_plate_thickness = 0.005*1000
    engine_screw_hole_circle = 0.042*1000
    engine_mount_box_length = 0.0133 * 2.5*1000

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")
    pwd = os.path.curdir

    full_wing_loft_node = ConstructionStepNode(
        StepImportCreator("full_wing_loft",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/wing.step"),
                          scale=base_scale))
    root_node.append(full_wing_loft_node)

    flaps_node = ConstructionStepNode(
        StepImportCreator("flaps",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/flaps.step"),
                          scale=base_scale))
    #root_node.append(flaps_node)

    aileron_node = ConstructionStepNode(
        StepImportCreator("aileron",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/aileron_right.step"),
                          scale=base_scale))
    #root_node.append(aileron_node)

    fuselage_hull = ConstructionStepNode(
        StepImportCreator("fuselage_hull_imp",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage_inlets.step"),
                          scale=base_scale))
    root_node.append(fuselage_hull)

    fuselage_small_hull = ConstructionStepNode(
        SimpleOffsetShapeCreator("fuselage_small_hull",
                                 offset=-0.8,
                                 shape="fuselage_hull_imp"))
    fuselage_hull.append(fuselage_small_hull)

    cockpit = ConstructionStepNode(
        StepImportCreator("cockpit",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/cockpit.step"),
                          scale=base_scale))
    #fuselage_hull.append(cockpit)

    cut_cockpit_node = ConstructionStepNode(
        Cut2ShapesCreator("cockpit"))
    #cockpit.append(cut_cockpit_node)

    elevator = ConstructionStepNode(
        StepImportCreator("elevator",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/full_elevator_straight.step"),
                          scale=base_scale))
    root_node.append(elevator)

    rudder = ConstructionStepNode(
        StepImportCreator("rudder",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_fix_final.step"),
                          scale=base_scale))
    root_node.append(rudder)

    rudder_flap = ConstructionStepNode(
        StepImportCreator("rudder_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_flap.step"),
                          scale=base_scale))
    #root_node.append(rudder_flap)

    elevator_flap = ConstructionStepNode(
        StepImportCreator("elevator_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/elevator_flap_straight.step"),
                          scale=base_scale))
    #root_node.append(elevator_flap)

    elevator_servo = ConstructionStepNode(
        ServoImporterCreator("elevator_servo",
                             servo_feature=os.path.abspath(f"../components/servos/unknown/servo_24x24x12_inside.step"),
                             servo_stamp=os.path.abspath(f"../components/servos/unknown/servo_24x24x12_inside_stamp.step"),
                             servo_filling=None,
                             servo_model=os.path.abspath(f"../components/servos/AS215BBMG_left.step"),
                             servo_idx=1))
    root_node.append(elevator_servo)

    rudder_servo = ConstructionStepNode(
        ServoImporterCreator("rudder_servo",
                             servo_feature=os.path.abspath(f"../components/servos/unknown/servo_24x24x12_inside.step"),
                             servo_stamp=os.path.abspath(f"../components/servos/unknown/servo_24x24x12_inside_stamp.step"),
                             servo_filling=None,
                             servo_model=os.path.abspath(f"../components/servos/AS215BBMG.step"),
                             servo_idx=2))
    root_node.append(rudder_servo)

    # #########

    engine_mount_init = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount_init",
                                engine_index=1,
                                mount_plate_thickness=mount_plate_thickness,
                                cutout_thickness=12423))
    root_node.append(engine_mount_init)

    engine_mount_plate = ConstructionStepNode(
        EngineCoverAndMountPanelAndFuselageShapeCreator("engine_mount_plate", engine_index=1, mount_plate_thickness=mount_plate_thickness,
                                                        full_fuselage_loft="fuselage_hull_imp"))
    engine_mount_init.append(engine_mount_plate)

    engine_mount = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount"))
    engine_mount_plate.append(engine_mount)

    # engine mount END

    fuselage_hull_split = ConstructionStepNode(
        EngineCapeShapeCreator("fuselage_hull",
                               engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="fuselage_hull_imp"))
    root_node.append(fuselage_hull_split)

    fuselage_shell_node = ConstructionStepNode(
        FuselageShellShapeCreator("full_fuselage_shell",
                                  thickness=0.8,
                                  fuselage="fuselage_hull.loft"))
    #root_node.append(fuselage_shell_node)

    fuselage_small_hull_split = ConstructionStepNode(
        EngineCapeShapeCreator("fuselage_small_hull", engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="fuselage_small_hull"))
    root_node.append(fuselage_small_hull_split)

    wing_attachment_bolt_node = ConstructionStepNode(
        WingAttachmentBoltCutoutShapeCreator("attachment_bolts", fuselage_loft="fuselage_hull.loft",
                                             full_wing_loft="full_wing_loft", bolt_diameter=6))
    root_node.append(wing_attachment_bolt_node)

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement_raw", rib_width=0.0008 * 1000, rib_spacing=0.00 * 1000,
                                          ribcage_factor=ribcage_factor, reinforcement_pipes_diameter=0.002 * 1000,
                                          print_resolution=0.2, fuselage_loft="fuselage_hull.loft",
                                          full_wing_loft="full_wing_loft"))
    root_node.append(fuselage_reinforcement_node)

    ff = ConstructionStepNode(
        Intersect2ShapesCreator("fuselage_reinforcement",
                                shape_a="fuselage_reinforcement_raw",
                                shape_b="fuselage_small_hull.loft"))
    root_node.append(ff)

    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support_raw", rib_quantity=18, rib_width=0.0008 * 1000, rib_height_factor=1.2,
                                        rib_z_offset=0, fuselage_loft="fuselage_hull.loft",
                                        full_wing_loft="full_wing_loft", loglevel=logging.DEBUG))
    root_node.append(wing_support_node)

    ff_w = ConstructionStepNode(
        Intersect2ShapesCreator("wing_support",
                                shape_a="wing_support_raw",
                                shape_b="fuselage_small_hull.loft"))
    root_node.append(ff_w)

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support_raw", rib_quantity=8, rib_width=0.0008 * 1000,
                                        rib_height_factor=6, rib_z_offset=25, fuselage_loft="fuselage_hull.loft",
                                        full_wing_loft="elevator"))
    root_node.append(full_elevator_support_loft_node)

    ff_e = ConstructionStepNode(
        Intersect2ShapesCreator("elevator_support",
                                shape_a="elevator_support_raw",
                                shape_b="fuselage_small_hull.loft"))
    root_node.append(ff_e)

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
                                                    ribcage_factor=ribcage_factor,
                                                    length_factor=0.7,
                                                    fuselage_loft="fuselage_hull.loft",
                                                    full_wing_loft="full_wing_loft",
                                                    wing_position=None))
    root_node.append(electronics_access_node)

    cut_electronics_fuse_rei = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_reinforcement_cut",
                          minuend="fuselage_reinforcement",
                          subtrahend="electronics_cutout",
                          ))
    root_node.append(cut_electronics_fuse_rei)

    cut_electronics_wing_sup = ConstructionStepNode(
        Cut2ShapesCreator("wing_support_cut",
                          minuend="wing_support",
                          subtrahend="electronics_cutout",
                          ))
    root_node.append(cut_electronics_wing_sup)

    fuse_fuselage_reinforcements = ConstructionStepNode(
        CutMultipleShapesCreator("reinforced_fuselage_raw",
                                 minuend="fuselage_hull.loft",
                                 subtrahends=[
                                     "elevator_support",
                                     "wing_support_cut",
                                     "fuselage_reinforcement_cut",
                                     "elevator_servo.feature",
                                     "rudder_servo.feature",
                                 ],
                                 loglevel=logging.DEBUG
                                 ))
    #root_node.append(fuse_fuselage_reinforcements)

    reinforcement_node = ConstructionStepNode(
        CutMultipleShapesCreator("reinforced_fuselage",
                                 minuend="reinforced_fuselage_raw",
                                 subtrahends=["electronics_cutout",
                                              "elevator_servo.stamp",
                                              "rudder_servo.stamp",
                                              "attachment_bolts"
                                              ],
                                 loglevel=logging.DEBUG
                                 ))
    #root_node.append(reinforcement_node)

    # holes_in_engine_mount = ConstructionStepNode(
    #     Cut2ShapesCreator("engine_mount",
    #                       minuend="engine_mount"))
    # #reinforcement_node.append(holes_in_engine_mount) # geht aktuell nicht
    #
    # internal_structure_node = ConstructionStepNode(
    #     Intersect2ShapesCreator("internal_structure",
    #                             shape_a="fuselage_small_hull.loft",
    #                             # shape_b="reinforcement2"
    #                             ))
    # reinforcement_node.append(internal_structure_node)
    #
    # reinforced_fuselage_node = ConstructionStepNode(
    #     CutMultipleShapesCreator("final_fuselage",
    #                       #  minuend="fuselage_small_hull.loft",
    #                       minuend="fuselage_hull.loft",
    #                       subtrahends=["internal_structure"]))
    # #internal_structure_node.append(reinforced_fuselage_node)

    cut_wing_from_fuselage_node = ConstructionStepNode(
        CutMultipleShapesCreator("final_fuselage",
                                 minuend="reinforced_fuselage",
                                 subtrahends=["full_wing_loft",
                                              "elevator",
                                              "rudder",
                                              #"attachment_bolts",
                                              #"elevator_servo.filling",
                                              #"rudder_servo.filling",
                                              "engine_mount"
                                              ]))
    #root_node.append(cut_wing_from_fuselage_node)
    #
    # shape_slicer_node = ConstructionStepNode(
    #     SliceShapesCreator("fuselage_slicer",
    #                        shapes_to_slice=["final_fuselage"],
    #                        number_of_parts=5))
    # cut_wing_from_fuselage_node.append(shape_slicer_node)
    #
    # rudder_cut_elevator_node = ConstructionStepNode(
    #     Cut2ShapesCreator("elevator_cut",
    #                       minuend="elevator",
    #                       subtrahend="rudder"))
    # root_node.append(rudder_cut_elevator_node)
    #
    # elevator_slicer_node = ConstructionStepNode(
    #     SliceShapesCreator("elevator_slicer",
    #                        shapes_to_slice=["elevator"],
    #                        number_of_parts=2))
    # rudder_cut_elevator_node.append(elevator_slicer_node)
    #
    # brushless_shape_import = ConstructionStepNode(
    #     ComponentImporterCreator("brushless",
    #                              component_file=os.path.abspath(f"../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.step"),
    #                              component_idx="brushless"))
    # root_node.append(brushless_shape_import)
    #
    # lipo_model_import = ConstructionStepNode(
    #     ComponentImporterCreator("lipo_model",
    #                              component_file=os.path.abspath(f"../components/lipo/D-Power HD-2200 4S Lipo (14,8V) 30C v1.iges"),
    #                              component_idx="lipo",
    #                              loglevel=logging.DEBUG
    #                              ))
    # root_node.append(lipo_model_import)
    #
    # aircraft_step_export_node = ConstructionStepNode(
    #     ExportToStepCreator(Path(f"{root_node.identifier}").stem,
    #                         file_path="../exports",
    #                         shapes_to_export=["engine_mount",
    #                                           "brushless",
    #                                           "lipo_model",
    #                                           "fuselage_hull.cape",
    #                                           "final_fuselage",
    #                                           "full_wing_loft",
    #                                           "final_fuselage[0]",
    #                                           "final_fuselage[1]",
    #                                           "final_fuselage[2]",
    #                                           "final_fuselage[3]",
    #                                           "final_fuselage[4]",
    #                                           "elevator",
    #                                           #"elevator_cut[0]",
    #                                           #"elevator_cut[1]",
    #                                           "elevator_flap",
    #                                           "rudder",
    #                                           "rudder_flap",
    #                                           "flaps",
    #                                           "aileron",
    #                                           "cockpit",
    #                                           "elevator_servo.model",
    #                                           "rudder_servo.model"
    #                                           ]))
    # root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    servo_elevator = ServoInformation(
        height=0.022*1000,
        width=0.012*1000,
        length=0.023*1000,
        lever_length=0.023*1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28*1000+0.02*1000,
        trans_y=0.005*1000,
        trans_z=0.044*1000-0.0244*1000)

    servo_rudder = ServoInformation(
        height=0.022*1000,
        width=0.012*1000,
        length=0.023*1000,
        lever_length=0.023*1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28*1000+0.02*1000,
        trans_y=-0.005*1000-0.012*1000,
        trans_z=0.044*1000-0.0244*1000)
    servo_information = {1: servo_elevator, 2: servo_rudder}

    engine_info1 = EngineInformation(down_thrust=-2.5,
                                     side_thrust=-2.5,
                                     position=Position(0.0458*1000, 0, 0),
                                     length=0.0452*1000,
                                     width=0.035*1000,
                                     height=0.035*1000,
                                     screw_hole_circle=0.042*1000,
                                     mount_box_length=0.0133 * 2.5*1000,
                                     screw_din_diameter=0.0032*1000,
                                     screw_length=0.016*1000)

    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031*1000, height=0.035*1000, length=0.108*1000,
                                            trans_x=0.129*1000, trans_y=0.0, trans_z=-0.021*1000,
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
    json_file_path = os.path.abspath(f"../components/constructions/{root_node.identifier}.json")
    json_file = open(json_file_path, "w")
    json.dump(fp=json_file, obj=root_node, indent=4, cls=GeneralJSONEncoder)
    json_file.close()

    try:
        # build on basis of deserialized json
        structure = myMap.create_shape()
        from pprint import pprint

        pprint(structure)
    except Exception as err:
        raise err
    pass
