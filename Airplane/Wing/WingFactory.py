from __future__ import print_function

import logging

import OCP.BRepBuilderAPI as OBui
from OCP.TopoDS import TopoDS_Vertex, TopoDS_Edge
from cadquery import Workplane

from Airplane.ReinforcementPipeFactory import *
from Airplane.Wing.CablePipeFactory import CablePipeFactory
from Airplane.Wing.RuderFactory import RuderFactory
from Airplane.Wing.ServoRecessFactory import ServoRecessFactory
from Airplane.Wing.WingRibFactory import *
from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.BooleanOperationsForLists import BooleanCADOperation
from Extra.CollisionDetector import CollisionDetector
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class WingFactory:
    '''
    This Class provides different methods to create wings
    '''

    def __init__(self, cpacs_configuration, wing_index):
        '''
        Initialize the class with the tigle handle with the CPACS configuration and the index of the wing to be created
        '''
        self.m = ConstructionStepsViewer.instance()

        self.cpacs_configuration: TConfig.CCPACSConfiguration = cpacs_configuration

        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wing_index)
        self.wing_loft: Workplane = self.wing.get_loft()

        self.namedshape: Workplane = Workplane()
        self.shapes: list[Workplane] = []

        self.ruder_factory: RuderFactory = RuderFactory(cpacs_configuration, wing_index)
        self.servo_recces_factory: ServoRecessFactory = ServoRecessFactory(cpacs_configuration, wing_index)
        self.cable_pipe_factory: CablePipeFactory = CablePipeFactory(cpacs_configuration, wing_index)

    def create_wing_with_inbuilt_servo(self, internal_structure, wing_information, named_wing_offset) -> Workplane:
        """
        Creates wing with its internat Strukture, made out of Ribs, Pipe for Carbon Rod, Servo Reccess,
        CablePipe and Cutout for the Ruder
        :param named_wing_offset:
        :param wing_information:
        :param internal_structure:
        :return: the namedshape of the konstrukted wing
        """
        self.shapes.append(internal_structure)
        #
        # # self.shapes.append(OAlgo.BRepAlgoAPI_Cut(self.wing_shape, self.shapes[-1]).Shape())
        # self.shapes.append(Workplane(OAlgo.BRepAlgoAPI_Cut(named_wing_offset.shape(), self.shapes[-1].shape()).Shape(),
        #                                     f"{self.wing_loft.name()}"))
        # self.m.display_cut(self.shapes[-1], named_wing_offset, self.shapes[-2], logging.NOTSET)

        # Cut-Out Ruder
        offset: float = 0.002
        ruder_cutout, ruder_cut_small = self.ruder_factory.get_trailing_edge_cutout(wing, offset)

        if ruder_cutout is not None:
            wing = self.shapes[-1]
            self.shapes.append(
                Workplane(OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), ruder_cutout.shape()).Shape(),
                                 f"{self.wing_loft.name()}"))
            self.m.display_cut(self.shapes[-1], self.shapes[-2], ruder_cutout, logging.NOTSET)

            # rudder
            aileron = BooleanCADOperation.intersect_shape_with_shape(wing, ruder_cut_small, "aileron")
            # self.m.display_cut(aileron, self.shapes[-1], aileron, logging.NOTSET)

            self.m.display_this_shape(aileron, logging.INFO)
            #raise RuntimeError

            # Collision Tests
            #reinforcement_tests = [(servo, False), (cable_pipe, False), (ruder_cutout, False)]
            #servo_tests = [(cable_pipe, True), (ruder_cutout, False)]
            #ruder_test = [(cable_pipe, False)]
            #all_test = {reinforcement_rod: reinforcement_tests, servo: servo_tests, ruder_cutout: ruder_test}
            #collision_detector = CollisionDetector()
            #collision_detector.multiple_collision_check(all_test)
        else:
            aileron = None

        return self.shapes[-1], aileron

    def create_wing_with_ruder(self, rib_cage_shape) -> Workplane:
        '''
        Creates wing with its internal Strukture, made out of Ribs and Rudercutout
        :param rib_cage_shape:
        :return: the namedshape of the konstrukted wing
        '''

        internal_structur: list[Workplane] = []
        # Ribs
        internal_structur.append(rib_cage_shape)

        # Cut internal Strukture from Wing
        offset = 0.001
        toleranz = offset / 8
        wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_loft.shape(), offset,
                                                                             0.000001).Shape()
        while wing_offset is None and offset < 0.01:
            offset *= 1.2  # 20% mehr
            toleranz *= 1.2
            wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_loft.shape(), offset,
                                                                                 toleranz).Shape()
            logging.info(f"Offseting wing with {offset=} {toleranz=} {type(wing_offset)}")

        named_wing_offset = Workplane(wing_offset, "Wingoffset")

        # Cut-Out Ruder
        offset: float = 0.002
        ruder_cutout, _ = self.ruder_factory.get_trailing_edge_cutout(wing, offset)
        if ruder_cutout is not None:
            self.shapes.append(
                Workplane(OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), ruder_cutout.shape()).Shape(),
                                 f"{self.wing_loft.name()}"))
            self.m.display_cut(self.shapes[-1], self.shapes[-2], ruder_cutout, logging.NOTSET)


    @classmethod
    def create_mirrored_wing(cls, shape) -> Workplane:
        # Set up the mirror
        aTrsf = Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))
        # Apply the mirror transformation
        aBRespTrsf = OBui.BRepBuilderAPI_Transform(shape.shape(), aTrsf)

        # Get the mirrored shape back out of the transformation and convert back to a wire
        mirrord_wing_shape = aBRespTrsf.Shape()
        named_mirrored_wing_shape = Workplane(mirrord_wing_shape, f"mirrored_{shape.name()}")
        return named_mirrored_wing_shape
