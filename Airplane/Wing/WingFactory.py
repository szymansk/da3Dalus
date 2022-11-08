from __future__ import print_function

import time

from Airplane.ReinforcementPipeFactory import *
from Airplane.Wing.CablePipeFactory import CablePipeFactory
from Airplane.Wing.RuderFactory import RuderFactory
from Airplane.Wing.ServoRecessFactory import ServoRecessFactory
from Airplane.Wing.WingRibFactory import *
from Dimensions.ShapeDimensions import ShapeDimensions
from factories.RibFactory import *


class WingFactory:
    def __init__(self, tigl_handle, wingNr):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_dimensions = PDim.ShapeDimensions(self.wing_shape)
        self.shape: OTopo.TopoDS_Shape = OTopo.TopoDS_Shape()
        self.shapes: list = []
        self.wing_rib_factory: WingRibFactory = WingRibFactory(tigl_handle, wingNr)
        self.reinforcement_pipe_factory: ReinforcementePipeFactory = ReinforcementePipeFactory(tigl_handle, wingNr)
        self.ruder_factory: RuderFactory = RuderFactory(tigl_handle, wingNr)
        self.servo_recces_factory: ServoRecessFactory = ServoRecessFactory(tigl_handle, wingNr)
        self.cable_pipe_factory: CablePipeFactory = CablePipeFactory(tigl_handle, wingNr)
        self.m = myDisplay.instance()

    def create_wing_option1(self) -> OTopo.TopoDS_Shape:
        """
        Creates wing with its internat Strukture, made out of Ribs, Pipe for Carbon Rod, Servo Reccess,
        CablePipe and Cutout for the Ruder
        :return:
        """
        internal_struktur = []

        # Ribs
        self.wing_rib_factory.create_ribs_option1(5)
        internal_struktur.append(self.wing_rib_factory.get_shape())

        # Pipese for CarbonRod
        self.reinforcement_pipe_factory.create_reinforcemente_pipe_option1_wing(radius=0.003, thickness=0.0004,
                                                                                quantity=5,
                                                                                pipe_position=[0, 1])
        internal_struktur.append(self.reinforcement_pipe_factory.get_shape())

        # Servo Reccess
        servo_size = (0.024, 0.024, 0.012)
        ruder_shape = self.ruder_factory.get_trailing_edge_shape()
        self.servo_recces_factory.create_servoRecess_option1(ruder_shape, servo_size)
        servo = self.servo_recces_factory.get_shape()
        servo_dimensions = ShapeDimensions(servo, "servo")
        internal_struktur.append(servo)

        # Cable Pipe
        fuselage: TConfig.CCPACSWing = self.cpacs_configuration.get_fuselage(1)
        fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
        fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
        fuselage_dimensions = ShapeDimensions(fuselage_shape, "fuselage")

        points = self.cable_pipe_factory.points_route_thru(servo_dimensions, fuselage_dimensions)
        self.cable_pipe_factory.create_complete_pipe(points, servo_dimensions.get_height() / 2)
        cable_pipe: OTopo.TopoDS_Shape = self.cable_pipe_factory.get_shape()
        internal_struktur.append(cable_pipe)

        # Fuse internal Strukture
        self.shapes.append(fuse_list_of_shapes(internal_struktur))

        # Cut internal Strukture from Wing
        offset = 0.001
        toleranz = offset / 8
        wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_shape, offset, toleranz).Shape()
        while wing_offset is None and offset < 0.01:
            offset *= 1.2  # 20% mehr
            toleranz *= 1.2
            wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_shape, offset,
                                                                                 toleranz).Shape()
            logging.info(f"Offseting wing with {offset=} {toleranz=} {type(wing_offset)}")

        # self.shapes.append(OAlgo.BRepAlgoAPI_Cut(self.wing_shape, self.shapes[-1]).Shape())
        self.shapes.append(OAlgo.BRepAlgoAPI_Cut(wing_offset, self.shapes[-1]).Shape())
        self.m.display_cut(self.shapes[-1], wing_offset, self.shapes[-2])

        # Cut-Out Ruder
        offset: float = 0.002
        ruder_cutout: OTopo.TopoDS_Shape = self.ruder_factory.get_trailing_edge_cutout(offset)
        self.shapes.append(OAlgo.BRepAlgoAPI_Cut(self.shapes[-1], ruder_cutout).Shape())
        self.m.display_cut(self.shapes[-1], self.shapes[-2], ruder_cutout)
        return self.shapes[-1]

    def get_shape(self) -> OTopo.TopoDS_Shape:
        return self.shapes[-1]
