import json
import logging
import os
import sys
from pathlib import Path

from cadquery import Vector

from cad_designer.aerosandbox.convert2aerosandbox import convert_step_to_asb_fuselage
from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder, GeneralJSONEncoder, EngineMountShapeCreator, \
    EngineCoverAndMountPanelAndFuselageShapeCreator, Cut2ShapesCreator, StepImportCreator, WingLoftCreator, \
    SimpleOffsetShapeCreator, ServoImporterCreator, Fuse2ShapesCreator, EngineCapeShapeCreator, \
    FuselageReinforcementShapeCreator, ScaleRotateTranslateCreator, FuselageWingSupportShapeCreator, \
    FuselageElectronicsAccessCutOutShapeCreator, CutMultipleShapesCreator, Intersect2ShapesCreator, \
    ComponentImporterCreator
from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
from cad_designer.airplane.aircraft_topology.Position import Position
from cad_designer.airplane.aircraft_topology.components import ServoInformation, EngineInformation, \
    ComponentInformation
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.creator.cad_operations import FuseMultipleShapesCreator
from cad_designer.airplane.creator.export_import import ExportToStepCreator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


# TODO: * cutouts for hinges
#       * cutout for elevator flap rod (carbon 1mm) in elevator and in rudder
#       * wings with servos for aileron and flaps
#       * cutouts for elevator and rudder rods (anlenkung carbonstab 1mm)
#       * ruderhörner der Anlenkpunkt sollte über der Drehachse liegen und der Abstand beider
#         Drehpunkte sollte mit dem Abstand der Anschlusspunkte übereinstimmen vergleich:
#         (https://www.rc-network.de/threads/die-kinematik-ungewollter-differenzierung.11779720/)

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.INFO, stream=sys.stdout)

    base_scale = 38
    printer_resolution = 0.2  # 0.2 mm layer hight
    
    ribcage_factor = 0.49
    mount_plate_thickness = 5
    engine_screw_hole_circle = 42.0
    engine_mount_box_length = 13.3 * 2.5

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")
    pwd = os.path.curdir

    full_wing_loft_node_a = ConstructionStepNode(
        StepImportCreator("full_wing_loft_a",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/wing.step"),
                          scale=base_scale, loglevel=logging.DEBUG))
    root_node.append(full_wing_loft_node_a)

    full_wing_loft_node = ConstructionStepNode(
        WingLoftCreator("full_wing_loft",
                        wing_index="main_wing", wing_side="BOTH", loglevel=logging.DEBUG))
    root_node.append(full_wing_loft_node)

    flaps_node = ConstructionStepNode(
    StepImportCreator("flaps",
                      step_file=os.path.abspath(f"../components/aircraft/RV-7/flaps.step"),
                      scale=base_scale))
    root_node.append(flaps_node)

    aileron_node = ConstructionStepNode(
        StepImportCreator("aileron",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/aileron_right.step"),
                          scale=base_scale))
    root_node.append(aileron_node)

    fuselage_hull = ConstructionStepNode(
        StepImportCreator("fuselage_hull_imp",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage_inlets.step"),
                          scale=base_scale,
                          loglevel=logging.INFO))
    root_node.append(fuselage_hull)

    fuselage_small_hull = ConstructionStepNode(
        SimpleOffsetShapeCreator("fuselage_small_hull",
                                 offset=-4 * printer_resolution,
                                 shape="fuselage_hull_imp",
                                 loglevel=logging.DEBUG))
    fuselage_hull.append(fuselage_small_hull)

    cockpit = ConstructionStepNode(
        StepImportCreator("cockpit",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/cockpit.step"),
                          scale=base_scale))
    fuselage_hull.append(cockpit)

    cut_cockpit_node = ConstructionStepNode(
        Cut2ShapesCreator("cockpit"))
    cockpit.append(cut_cockpit_node)

    elevator = ConstructionStepNode(
        StepImportCreator("elevator",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/full_elevator_straight.step"),
                          scale=base_scale,
                          loglevel=logging.DEBUG))
    root_node.append(elevator)

    rudder = ConstructionStepNode(
        StepImportCreator("rudder",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_fix_final.step"),
                          scale=base_scale,
                          loglevel=logging.DEBUG))
    root_node.append(rudder)

    rudder_flap = ConstructionStepNode(
        StepImportCreator("rudder_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_flap.step"),
                          scale=base_scale))
    root_node.append(rudder_flap)

    elevator_flap = ConstructionStepNode(
        StepImportCreator("elevator_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/elevator_flap_straight.step"),
                          scale=base_scale))
    root_node.append(elevator_flap)

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
                                cutout_thickness=mount_plate_thickness+4*printer_resolution, loglevel=logging.DEBUG))
    root_node.append(engine_mount_init)

    engine_mount_plate = ConstructionStepNode(
        EngineCoverAndMountPanelAndFuselageShapeCreator(
            "engine_mount_plate", engine_index=1, mount_plate_thickness=mount_plate_thickness,
                      full_fuselage_loft="fuselage_hull_imp", loglevel=logging.DEBUG))
    engine_mount_init.append(engine_mount_plate)

    engine_mount_plate_cutout = ConstructionStepNode(
        Cut2ShapesCreator("engine_mount_plate_cutout",
                          minuend=engine_mount_plate.creator_id,
                          subtrahend=f"{engine_mount_init.creator_id}.cutout"))
    engine_mount_plate.append(engine_mount_plate_cutout)

    engine_mount = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount",
                           shape_a=engine_mount_plate_cutout.creator_id,
                           shape_b=engine_mount_init.creator_id,
                           loglevel=logging.DEBUG))
    engine_mount_plate_cutout.append(engine_mount)
    # engine mount END

    fuselage_hull_split = ConstructionStepNode(
        EngineCapeShapeCreator("fuselage_hull",
                               engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="fuselage_hull_imp"))
    root_node.append(fuselage_hull_split)

    fuselage_small_hull_split = ConstructionStepNode(
        EngineCapeShapeCreator("fuselage_small_hull", engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="fuselage_small_hull"))
    root_node.append(fuselage_small_hull_split)

    #wing_attachment_bolt_node = ConstructionStepNode(
    #    WingAttachmentBoltCutoutShapeCreator("attachment_bolts",
    #                                         fuselage_loft="fuselage_hull.loft",
    #                                         full_wing_loft="full_wing_loft", bolt_diameter=6))
    #root_node.append(wing_attachment_bolt_node)

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement_raw",
                                          rib_width=4 * printer_resolution, rib_spacing=5.0,
                                          ribcage_factor=ribcage_factor, reinforcement_pipes_diameter=2.0,
                                          print_resolution=printer_resolution, fuselage_loft=f"{fuselage_hull_split.creator_id}.loft",
                                          full_wing_loft=full_wing_loft_node_a.creator_id))
    root_node.append(fuselage_reinforcement_node)

    translate_rods_node = ConstructionStepNode(
        ScaleRotateTranslateCreator("translated_rods",
                                    shape_id="fuselage_reinforcement_raw.rods",
                                    trans_x=-mount_plate_thickness*2,
                                    loglevel=logging.DEBUG))
    fuselage_reinforcement_node.append(translate_rods_node)

    cut_rods_from_motor_mount_node = ConstructionStepNode(
        Cut2ShapesCreator("motor_mount_with_rod_holes",
                          minuend=engine_mount.creator_id,
                          loglevel=logging.DEBUG))
    translate_rods_node.append(cut_rods_from_motor_mount_node)


    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support_raw",
                                        rib_quantity=7, rib_width=4 * printer_resolution, rib_height_factor=1.2,
                                        rib_z_offset=0, fuselage_loft="fuselage_hull.loft",
                                        full_wing_loft=full_wing_loft_node_a.creator_id, loglevel=logging.DEBUG))
    root_node.append(wing_support_node)

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support_raw",
                                        rib_quantity=5, rib_width=4 * printer_resolution,
                                        rib_height_factor=6, rib_z_offset=25, fuselage_loft="fuselage_hull.loft",
                                        full_wing_loft="elevator"))
    root_node.append(full_elevator_support_loft_node)

    all_raw_fuselage_reinforcements_fused = ConstructionStepNode(
        FuseMultipleShapesCreator("all_raw_fuselage_reinforcements_fused",
                                  shapes=["fuselage_reinforcement_raw",
                                          "wing_support_raw",
                                          "elevator_support_raw",
                                          "elevator_servo.feature",
                                          "rudder_servo.feature"]))
    root_node.append(all_raw_fuselage_reinforcements_fused)

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
                                                    ribcage_factor=ribcage_factor,
                                                    length_factor=0.7,
                                                    fuselage_loft="fuselage_hull.loft",
                                                    full_wing_loft=full_wing_loft_node_a.creator_id,
                                                    wing_position=None))
    root_node.append(electronics_access_node)

    cut_electronics_fuse_rei = ConstructionStepNode(
        CutMultipleShapesCreator("cut_electronics_fuse_rei",
                                 minuend="all_raw_fuselage_reinforcements_fused",
                                 subtrahends=["electronics_cutout",
                                              "elevator_servo.stamp",
                                              "rudder_servo.stamp"],
                                 loglevel=logging.INFO))
    root_node.append(cut_electronics_fuse_rei)

    intersect_raw_fus_reinf_fuselage_small_hull = ConstructionStepNode(
        Intersect2ShapesCreator("intersect_raw_fus_reinf_fuselage_small_hull",
                                shape_a="cut_electronics_fuse_rei",
                                shape_b="fuselage_small_hull.loft",
                                loglevel=logging.DEBUG))
    root_node.append(intersect_raw_fus_reinf_fuselage_small_hull)

    fuselage_hull_final = ConstructionStepNode(
        CutMultipleShapesCreator("fuselage_hull_final",
                                 minuend="fuselage_hull.loft",
                                 subtrahends=["intersect_raw_fus_reinf_fuselage_small_hull",
                                              f"{engine_mount_init.creator_id}.cutout"],
                                 loglevel=logging.INFO))
    root_node.append(fuselage_hull_final)

    # holes_in_engine_mount = ConstructionStepNode(
    #     Cut2ShapesCreator("engine_mount",
    #                       minuend="engine_mount"))
    # #reinforcement_node.append(holes_in_engine_mount) # geht aktuell nicht
    #

    cut_wing_from_fuselage_node = ConstructionStepNode(
        CutMultipleShapesCreator("final_fuselage",
                                 minuend="fuselage_hull_final",
                                 subtrahends=[full_wing_loft_node_a.creator_id,
#                                              "rudder",
                                              "elevator",
                                              #"attachment_bolts",
                                              #"elevator_servo.filling",
                                              #"rudder_servo.filling",
                                              #"engine_mount"
                                              ],
                                 loglevel=logging.DEBUG))
    root_node.append(cut_wing_from_fuselage_node)
    #
    # shape_slicer_node = ConstructionStepNode(
    #     SliceShapesCreator("fuselage_slicer",
    #                        shapes_to_slice=["final_fuselage"],
    #                        number_of_parts=5))
    # cut_wing_from_fuselage_node.append(shape_slicer_node)

    rudder_cut_elevator_node = ConstructionStepNode(
        Cut2ShapesCreator("rudder_cut",
                          minuend=rudder.creator_id,
                          subtrahend=elevator.creator_id))
    root_node.append(rudder_cut_elevator_node)

    # elevator_slicer_node = ConstructionStepNode(
    #     SliceShapesCreator("elevator_slicer",
    #                        shapes_to_slice=["elevator"],
    #                        number_of_parts=2))
    # rudder_cut_elevator_node.append(elevator_slicer_node)

    brushless_shape_import = ConstructionStepNode(
        ComponentImporterCreator("brushless",
                                 component_file=os.path.abspath(f"../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.step"),
                                 component_idx="brushless",
                                 loglevel=logging.INFO))
    root_node.append(brushless_shape_import)

    lipo_model_import = ConstructionStepNode(
        ComponentImporterCreator("lipo_model",
                                 component_file=os.path.abspath(f"../components/lipo/D-Power HD-2200 4S Lipo (14,8V) 30C v1.iges"),
                                 component_idx="lipo",
                                 loglevel=logging.DEBUG
                                 ))
    root_node.append(lipo_model_import)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[# "fuselage_with_shell",
                                              # engine_mount.creator_id,
                                              cut_rods_from_motor_mount_node.creator_id,
                                              brushless_shape_import.creator_id,
                                              lipo_model_import.creator_id,
                                              "fuselage_hull.cape",
                                              "final_fuselage",
                                              full_wing_loft_node_a.creator_id,
                                              # "final_fuselage[0]",
                                              # "final_fuselage[1]",
                                              # "final_fuselage[2]",
                                              # "final_fuselage[3]",
                                              # "final_fuselage[4]",
                                              elevator.creator_id,
                                              rudder_cut_elevator_node.creator_id,
                                              #"elevator_cut",
                                              # #"elevator_cut[1]",
                                              elevator_flap.creator_id,
                                              #"rudder",
                                              rudder_flap.creator_id,
                                              "flaps",
                                              "aileron",
                                              cockpit.creator_id,
                                              "elevator_servo.model",
                                              "rudder_servo.model"
                                              ]))
    root_node.append(aircraft_step_export_node)

    ###### END: DESGIN TREE

    ######
    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    ########
    #### CONFIGURATION
    ########
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
                                     screw_length=0.016*1000,
                                     rot_x=45)

    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031*1000, height=0.035*1000, length=0.108*1000,
                                            trans_x=0.129*1000, trans_y=0.0, trans_z=-0.021*1000,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    airfoil = "../components/airfoils/naca23013.5.dat"
    elevator_airfoile = "../components/airfoils/n12.dat"
    wing_configuration = {
        "main_wing": WingConfiguration(
            nose_pnt=(192.113, 0, -44.5),
             root_airfoil=Airfoil(airfoil=airfoil, chord=183, dihedral_as_rotation_in_degrees=3.7,
                                  incidence=0), length=410, sweep=0,
             tip_airfoil=Airfoil(chord=183, dihedral_as_rotation_in_degrees=0, incidence=0)),
        "elevator": WingConfiguration(
            nose_pnt=(593.573, 0, 31.608),
            root_airfoil=Airfoil(airfoil=elevator_airfoile, chord=118.771, dihedral_as_rotation_in_degrees=0,
                                 incidence=0), length=165.5, sweep=27.945,
            tip_airfoil=Airfoil(chord=75.849, dihedral_as_rotation_in_degrees=0, incidence=0)),
        "rudder": WingConfiguration(
            nose_pnt=(581.4, 0, -9.652),
            root_airfoil=Airfoil(airfoil=elevator_airfoile,
                                 chord=186.2,
                                 dihedral_as_rotation_in_degrees=90,
                                 incidence=0),
            length=188.1, sweep=68.463,
            tip_airfoil=Airfoil(chord=79.8, dihedral_as_rotation_in_degrees=0, incidence=0)),
    }

    #######
    import aerosandbox as asb
    mm_to_m_scale = 1.0e-3
    asb_wing: asb.Wing = wing_configuration["main_wing"].get_asb_wing(scale=mm_to_m_scale)
    asb_elevator: asb.Wing = wing_configuration["elevator"].get_asb_wing(scale=mm_to_m_scale)
    asb_rudder: asb.Wing = wing_configuration["rudder"].get_asb_wing(symmetric=False,scale=mm_to_m_scale)

    fuselage = convert_step_to_asb_fuselage(
        f"../components/aircraft/RV-7/fuselage.step",
        number_of_slices = 100, spacing = None, plot = True, scale=base_scale*mm_to_m_scale)

    airplane = asb.Airplane(
        name="RV7",
        xyz_ref = None,
        wings = [asb_wing, asb_elevator, asb_rudder],
        fuselages = fuselage,
        propulsors = None,
    )

    def add_cylinder(figure, position, length, name: str, color:str = 'red'):
        # Add a cylinder along the x-axis
        cylinder_x = [position.x, position.x]
        cylinder_y = [position.y, position.y]
        cylinder_z = [position.z, position.z + length]
        figure.add_scatter3d(
            x=cylinder_x,
            y=cylinder_y,
            z=cylinder_z,
            mode="lines",
            line=dict(width=20, color=color),
            name=f"{name} Cylinder"
        )

        # Add text at the top of the cylinder
        figure.add_scatter3d(
            x=[position.x],
            y=[position.y],
            z=[position.z + length],
            mode="text",
            text=[name],
            textposition="top center",
            textfont=dict(size=20, color="black"),
            name=f"{name} Label"
        )

    # Add the main wing
    figure = airplane.draw(backend="plotly", show=False)

    # calculate mean aerodynamic chord (MAC) of the main wing
    mac = asb_wing.mean_aerodynamic_chord()

    # calculate the neutral point (NP) of the airplane
    np = airplane.aerodynamic_center(chord_fraction=0.25)
    add_cylinder(figure, Vector(*np), 0.2, "NP", color="green")

    # static margin 15%-7,5% of MAC for the Center of Gravity (CG)
    static_margin = 0.15
    cg_position = Vector(*np) + Vector(-mac * static_margin, 0, 0)
    add_cylinder(figure, cg_position, 0.2,f"CG-{static_margin*100}%", color="red")

    static_margin = 0.075
    cg_position = Vector(*np) + Vector(-mac * static_margin, 0, 0)
    add_cylinder(figure, cg_position, 0.2,f"CG-{static_margin*100}%", color="red")

    static_margin = 0.125
    cg_position = Vector(*np) + Vector(-mac * static_margin, 0, 0)
    add_cylinder(figure, cg_position, 0.2,f"XYZ_REF-{static_margin*100}%", color="blue")

    # set the reference point of the airplane to the estimated CG position for dynamic analysis
    airplane.xyz_ref = cg_position

    figure.show()
    airplane.draw_three_view()

    ######

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
                                             servo_information=servo_information,
                                             component_information=component_information,
                                             wing_config=wing_configuration)

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
