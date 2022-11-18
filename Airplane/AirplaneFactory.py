import logging

import stl_exporter.Ausgabeservice as exp
from Airplane.Fuselage.FuselageFactory import FuselageFactory
from Airplane.Wing.WingFactory import WingFactory
from Extra.ShapeSlicer import ShapeSlicer
from Extra.mydisplay import myDisplay


class AirplaneFactory:
    '''
    With this class it is posible to create all the parts of an aiplane.
    '''

    def __init__(self, tigl_handle):
        '''
        :param tigl_handle: has the cpacs configuration in it  witch is need to crate all parts
        '''
        self.m = myDisplay.instance()
        self.tigl_handle = tigl_handle

    def create_airplane(self):
        '''
        Create the right, left main wing and fuselage. Stores sliced komponente .stl files
        '''
        logging.info("Creating airplane")
        self.create_right_mainwing()
        self.create_left_mainwing()
        self.create_fuselage()

    def create_wing(self, wing_index=1, name="wing"):
        '''
        Creates the .stl files of the wing describes in the CPACSConfiguration
        :param wing_index: indes of the wing in the CPACSConfiguration
        :param name: name to be used in the stl files
        :return:
        '''
        logging.info("Creating " + name)
        self.wing_factory = WingFactory(self.tigl_handle, wing_index)
        self.wing_factory.create_wing_with_inbuilt_servo()
        named_wing = self.wing_factory.get_shape()

        parts_quantity = 5
        slicer = ShapeSlicer(named_wing, parts_quantity)
        slicer.slice_by_cut()

        my_exporter = exp.exporter()
        my_exporter.write_stls_from_list(slicer.parts_list, name)

    def create_right_mainwing(self):
        '''
        Creates the right mainwing witch schould be defined first in the CPACS
        '''
        self.create_wing(1, "right_mainwing")

    def create_left_mainwing(self):
        '''
        Creates a mirrored shape of the "rightwing" in the factory, must be called after create_right_wing
        '''
        left_wing = self.wing_factory.create_mirrored_wing()

        parts_quantity = 5
        slicer = ShapeSlicer(left_wing, parts_quantity)
        slicer.slice_by_cut()

        my_exporter = exp.exporter()
        my_exporter.write_stls_from_list(slicer.parts_list, "left_mainwing")

    def create_right_horizontal_tailwing(self):
        '''
        Creates the rigth horizontal tailwing
        :return:
        '''
        # Todo Creat wing with ribs, rudercutout, hingecutout
        pass

    def create_left_horizontal_tailwing(self):
        '''
        Creates a mirrored shape of the "right_tailwing" in the factory, must be called after create_right_h_tailwing
        :return:
        '''
        pass

    def create_fuselage(self, name="fuselage"):
        '''
        Creates the fuselage described in the CPACSConfiguration
        :param name: name to be used in the stl files
        :return:
        '''
        fuselage_factory = FuselageFactory(self.tigl_handle, 1)
        fuselage_factory.create_fuselage_with_sharp_ribs()
        fuselage_shape = fuselage_factory.get_shape()

        parts_quantity = 6
        slicer = ShapeSlicer(fuselage_shape, parts_quantity)
        slicer.slice_by_cut()

        parts_to_export = fuselage_factory.fuselage_parts + slicer.parts_list
        self.m.display_slice_x(parts_to_export)

        my_exporter = exp.exporter()
        my_exporter.write_stls_from_list(slicer.parts_list, name)
