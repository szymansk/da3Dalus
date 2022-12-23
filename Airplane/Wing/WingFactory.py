from __future__ import print_function

import OCC.Core.BRepBuilderAPI as OBui

from Airplane.ReinforcementPipeFactory import *
from Airplane.Wing.CablePipeFactory import CablePipeFactory
from Airplane.Wing.RuderFactory import RuderFactory
from Airplane.Wing.ServoRecessFactory import ServoRecessFactory
from Airplane.Wing.WingRibFactory import *
from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.CollisionDetector import CollisionDetector
from factories.RibFactory import *


class WingFactory:
    """
    This Class provides different methods to create wings
    """

    def __init__(self, wing, fuselage):
        """
        Initialize the class with the tigle handle with the CPACS configuration and the index of the wing to be created
        """
        self.m = ConstructionStepsViewer.instance()

        self.wing: TConfig.CCPACSWing = wing
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()

        self.fuselage = fuselage

        self.named_shape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list[TGeo.CNamedShape] = []

        self.wing_rib_factory: WingRibFactory = WingRibFactory(self.wing)
        self.reinforcement_pipe_factory: ReinforcementePipeFactory = ReinforcementePipeFactory(wing, fuselage)
        self.ruder_factory: RuderFactory = RuderFactory(wing)
        self.servo_recces_factory: ServoRecessFactory = ServoRecessFactory(wing)
        self.cable_pipe_factory: CablePipeFactory = CablePipeFactory(wing)

    def create_wing_with_inbuilt_servo(self) -> TGeo.CNamedShape:
        """
        Creates wing with its internat structure, made out of Ribs, Pipe for Carbon Rod, Servo Reccess,
        CablePipe and Cutout for the Ruder
        :return: the named shape of the constructed wing
        """
        internal_structure: list[TGeo.CNamedShape] = [self.wing_rib_factory.create_ribcage(horizontal_rib_quantity=4)]

        # Ribs

        # Pipese for Reinforcementrod, radius is given by the chosen carbonfiber stick, thickness is given by the
        # used printing configuration. Quantity has been choosen to ensure that the pipes
        # are at closer to the front edge of the wing.
        reinforcement_rod = self.reinforcement_pipe_factory.create_reinforcemente_pipe_wing(radius=0.003,
                                                                                            thickness=0.0004,
                                                                                            quantity=5,
                                                                                            pipe_position=[0, 1])
        internal_structure.append(reinforcement_rod)

        # Servo Reccess
        servo_size = (0.024, 0.024, 0.012)
        ruder_shape = self.ruder_factory.get_trailing_edge_shape()
        servo = self.servo_recces_factory.create_servoRecess_option1(ruder_shape, servo_size)
        servo_dimensions = ShapeDimensions(servo)
        internal_structure.append(servo)

        # Cable Pipe
        fuselage: TConfig.CCPACSWing = self.fuselage
        fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
        fuselage_dimensions = ShapeDimensions(fuselage_loft)

        points = self.cable_pipe_factory.points_route_through(servo_dimensions, fuselage_dimensions)
        cable_pipe = self.cable_pipe_factory.create_complete_pipe(points, servo_dimensions.get_height() / 2)
        internal_structure.append(cable_pipe)

        for ix in internal_structure:
            logging.debug(f"---{type(ix)}---")

        # Fuse internal Structure
        self.shapes.append(fuse_list_of_namedshapes(internal_structure, "internal structure"))

        # Cut internal Structure from Wing
        offset = 0.001
        toleranz = offset / 8
        wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_shape, offset, toleranz).Shape()

        while wing_offset is None and offset < 0.01:
            offset *= 1.2  # 20 % mehr
            toleranz *= 1.2
            wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_shape, offset,
                                                                                 toleranz).Shape()
            logging.debug(f"Offseting wing with {offset=} {toleranz=} {type(wing_offset)}")

        named_wing_offset = TGeo.CNamedShape(wing_offset, "Wingoffset")

        self.shapes.append(TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(wing_offset, self.shapes[-1].shape()).Shape(),
                                            f"{self.wing_loft.name()}"))
        self.m.display_cut(self.shapes[-1], named_wing_offset, self.shapes[-2], logging.NOTSET)

        # Cut-Out Ruder
        offset: float = 0.002
        ruder_cutout: TGeo.CNamedShape = self.ruder_factory.get_trailing_edge_cutout(offset)
        self.shapes.append(
            TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), ruder_cutout.shape()).Shape(),
                             f"{self.wing_loft.name()}"))
        self.m.display_cut(self.shapes[-1], self.shapes[-2], ruder_cutout, logging.NOTSET)

        # Collision Tests
        reinforcement_tests = [(servo, False), (cable_pipe, False), (ruder_cutout, False)]
        servo_tests = [(cable_pipe, True), (ruder_cutout, False)]
        ruder_test = [(cable_pipe, False)]
        all_test = {reinforcement_rod: reinforcement_tests, servo: servo_tests, ruder_cutout: ruder_test}
        collision_detector = CollisionDetector()
        collision_detector.multiple_collision_check(all_test)

        return self.shapes[-1]

    def create_wing_with_ribs(self) -> TGeo.CNamedShape:
        """
        Creates wing with its internal structure, made out of only Ribs
        :return: the named shape of the constructed wing
        """
        # Todo Create a wing that only has diagonal and horizontal ribs. for Vertikal tail wing
        pass

    def create_wing_with_ruder(self) -> TGeo.CNamedShape:
        """
        Creates wing with its internal Structure, made out of Ribs and Rudercutout
        :return: the named shape of the constructed wing
        """
        # Todo Create a wing that  has diagonal and horizontal ribs and a ruder. for horizontal tail wing
        pass

    def get_shape(self) -> TGeo.CNamedShape:
        return self.shapes[-1]

    def create_mirrored_wing(self) -> TGeo.CNamedShape:
        # Set up the mirror
        aTrsf = Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))
        # Apply the mirror transformation
        aBRespTrsf = OBui.BRepBuilderAPI_Transform(self.get_shape().shape(), aTrsf)

        # Get the mirrored shape back out of the transformation and convert back to a wire
        mirrord_wing_shape = aBRespTrsf.Shape()
        named_mirrored_wing_shape = TGeo.CNamedShape(mirrord_wing_shape, f"mirrored_{self.wing_loft.name()}")
        return named_mirrored_wing_shape
