import logging

import tigl3.geometry

import stl_exporter.Exporter as exp
from Airplane.Fuselage.FuselageFactory import FuselageFactory
from Airplane.Wing.WingFactory import WingFactory
from Extra.ShapeSlicer import ShapeSlicer
from Extra.mydisplay import myDisplay
from .Configuration import Configuration


def cut_component(component, quantity):
    """
    Cuts the component into serveral parts, defined by the quantity
    :param component: The component which should be cutted
    :param quantity: The number of parts the component will be cut into
    :return: The cut parts of the component
    """
    logging.info(f"Cut the {component.name()} into {quantity} parts")
    slicer = ShapeSlicer(component, quantity)
    slicer.slice_by_cut()
    return slicer.parts_list


def export_components_to_stl(components):
    """
    Export the components as .stl files
    :param components: The components that should be exported
    :return:
    """
    my_exporter = exp.Exporter()
    my_exporter.write_stls_from_list(components)



class AirplaneFactory:
    """
    With this class it is possible to create all the parts of an airplane.
    """

    def __init__(self, tigl_handle):
        """
        :param tigl_handle: has the cpacs configuration in it  which is needed to create all parts
        """
        self.m = myDisplay.instance()
        self.configuration = Configuration(tigl_handle)

    def create_airplane(self):
        """
        Create the right, left main wing and fuselage. Stores sliced components .stl files
        """
        logging.info("Creating airplane")
        self.create_right_main_wing()
        self.create_left_main_wing()
        self.create_fuselage()
        logging.info("Creation completed")

    def create_right_main_wing(self, parts_quantity=5):
        """
        Creates the .stl files of the wing describes in the CPACSConfiguration
        :param parts_quantity: The number of parts the wing is cut into
        :return:
        """
        logging.info("Creating right main wing")
        right_main_wing = self.configuration.get_right_main_wing()
        fuselage = self.configuration.get_fuselage()

        self.wing_factory = WingFactory(right_main_wing, fuselage)
        self.wing_factory.create_wing_with_inbuilt_servo()
        named_wing = self.wing_factory.get_shape()

        cut_parts = cut_component(named_wing, parts_quantity)
        export_components_to_stl(cut_parts)

    def create_left_main_wing(self, parts_quantity=5):
        """
        Creates a mirrored shape of the "rightwing" in the factory, must be called after create_right_wing
        """
        # mirror the right main wing
        left_wing = self.wing_factory.create_mirrored_wing()
        cut_parts = cut_component(left_wing, parts_quantity)
        export_components_to_stl(cut_parts)

    def create_right_horizontal_tail_wing(self):
        """
        Creates the rigth horizontal tail wing
        :return:
        """
        # Todo Creat wing with ribs, rudercutout, hingecutout
        pass

    def create_left_horizontal_tail_wing(self):
        """
        Creates a mirrored shape of the "right_tailwing" in the factory, must be called after create_right_h_tailwing
        :return:
        """
        pass

    def create_fuselage(self, parts_quantity=6):
        """
        Creates the fuselage described in the CPACSConfiguration
        :param parts_quantity: The number of parts the fuselage is cut into
        :return:
        """

        fuselage_factory = FuselageFactory(self.configuration)
        fuselage_factory.create_fuselage_with_sharp_ribs()
        fuselage_shape: tigl3.geometry.CNamedShape = fuselage_factory.get_shape()

        cut_parts = cut_component(fuselage_shape, parts_quantity)

        parts_to_export = fuselage_factory.fuselage_parts + cut_parts
        self.m.display_slice_x(parts_to_export)

        export_components_to_stl(cut_parts)
