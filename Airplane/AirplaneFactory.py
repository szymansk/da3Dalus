import tigl3.tigl3wrapper as tg3
import tixi3.tixi3wrapper as tw3
from Airplane.Fuselage.FuselageFactory import FuselageFactory
from Airplane.Wing.WingFactory import WingFactory
from Extra.ShapeSlicer import ShapeSlicer
import stl_exporter.Ausgabeservice as exp
from Extra.mydisplay import myDisplay
import logging


class AirplaneFactory:
    def __init__(self, tigl_handle, dev=False):
        self.md = myDisplay.instance(dev)
        self.tigl_handle = tigl_handle

    def create_airplane(self):
        logging.info("Creating airplane")
        self.create_right_mainwing()
        self.create_fuselage()

    def create_right_mainwing(self, wing_index=1, name="right_mainwing"):
        """

        :param nr:
        :param name:
        :return:
        """
        logging.info("Creating " + name)
        wing_factory = WingFactory(self.tigl_handle, wing_index)
        wing_factory.create_wing_option1()
        wing_shape = wing_factory.get_shape()
        slicer = ShapeSlicer(wing_shape, 5)
        slicer.slice_by_cut()
        my_exporter = exp.exporter()
        my_exporter.write_stls_from_list(slicer.parts_list, name)

    def create_left_mainwing(self):
        '''
        Creates a mirrored shape of the "rightwing" in the factory, must be called after create_right_wing
        '''
        self.wing_factory.create_mirrored_wing()
        self.wing_factory.export_stl("left_mainwing.stl", True)
        self.airplane.set_left_mainwing(self.wing_factory.wing.mirrored_shape)

    def create_right_h_tailwing(self):
        self.create_wing(2, "right_h_tailwing.stl")
        self.airplane.set_right_tailwing(self.wing_factory.wing.with_ribs)

    def create_left_h_tailwing(self):
        self.wing_factory.create_mirrored_wing()
        self.wing_factory.export_stl("left_h_tailwing.stl", True)
        self.airplane.set_left_tailwing(self.wing_factory.wing.mirrored_shape)

    def create_fuselage(self, name="fuselage"):
        fuselage_factory = FuselageFactory(self.tigl_handle, 1)
        fuselage_factory.create_fuselage_option1()
        fuselage_shape = fuselage_factory.get_shape()
        slicer = ShapeSlicer(fuselage_shape, 6)
        slicer.slice_by_cut()
        my_exporter = exp.exporter()
        my_exporter.write_stls_from_list(slicer.parts_list, name)
