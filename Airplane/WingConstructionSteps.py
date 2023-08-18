import logging
from typing import Literal, Union

from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ReinforcementPipeFactory import ReinforcementPipeFactory
from Airplane.Wing.CablePipeFactory import CablePipeFactory
from Airplane.Wing.RuderFactory import RuderFactory
from Airplane.Wing.ServoRecessFactory import ServoRecessFactory
from Airplane.Wing.WingFactory import WingFactory
from Airplane.Wing.WingRibFactory import WingRibFactory
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration
from Airplane.aircraft_topology.WingInformation import WingInformation
from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.BooleanOperationsForLists import BooleanCADOperation

from Extra.ConstructionStepsViewer import *


class WingRibCageCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_loft: str, wing_index: int, rib_distance, cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None, loglevel=logging.INFO):
        self.rib_distance = rib_distance
        self._wing_information = wing_information
        self.wing_loft = wing_loft
        self.wing_index = wing_index
        self._cpacs_configuration = cpacs_configuration
        super().__init__(creator_id, shapes_of_interest_keys=[self.wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"wing rib cage '{', '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        shape = WingRibFactory.create_ribcage(shapes_of_interest[self.wing_loft],
                                              wing_information=self._wing_information[self.wing_index],
                                              rib_distance=self.rib_distance)

        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class ReinforcementPipesCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_index: int, pipe_diameter: float, wall_thickness: float,
                 pipe_position: list[int], wing_information: dict[int, WingInformation] = None, loglevel=logging.INFO):
        self.pipe_position = pipe_position
        self.wall_thickness = wall_thickness
        self.pipe_diameter = pipe_diameter
        self._wing_information = wing_information
        self.wing_index = wing_index
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"wing pipes  --> '{self.identifier}'")

        # Pipes for reinforcement rod, radius is given by the chosen carbon fiber stick, thickness is given by the
        # used printing configuration. Quantity has been chosen to ensure tha the pipes
        # are at closer to the front edge of the wing.
        shape = ReinforcementPipeFactory.create_reinforcemente_pipe_wing(self._wing_information[self.wing_index],
                                                                         radius=self.pipe_diameter / 2,
                                                                         thickness=self.wall_thickness,
                                                                         pipe_position=self.pipe_position)

        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class CPACSTrailingEdgeDeviceCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 wing_index: int,
                 component_segment_index: int,
                 device_index: int,
                 cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None,
                 loglevel=logging.INFO):
        self.device_index = device_index
        self.component_segment_index = component_segment_index
        self._cpacs_configuration = cpacs_configuration
        self._wing_information = wing_information
        self.wing_index = wing_index
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"trailing edge device ''  --> '{self.identifier}'")
        factory = RuderFactory(self._cpacs_configuration, self.wing_index)
        wing: CCPACSWing = self._cpacs_configuration.get_wing(self.wing_index)
        shape = RuderFactory.get_trailing_edge_shape(wing, component_segment_index=self.component_segment_index,
                                                     device_index=self.device_index)
        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class CPACSTrailingEdgeDeviceCutOutCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 wing_index: int,
                 component_segment_index: int,
                 device_index: int,
                 cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None,
                 loglevel=logging.INFO):
        self.device_index = device_index
        self.component_segment_index = component_segment_index
        self._cpacs_configuration = cpacs_configuration
        self._wing_information = wing_information
        self.wing_index = wing_index
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"trailing edge device ''  --> '{self.identifier}'")
        wing: CCPACSWing = self._cpacs_configuration.get_wing(self.wing_index)
        shape, shape2 = RuderFactory.get_trailing_edge_cutout(wing,
                                                              offset=0.002,
                                                              component_segment_index=self.component_segment_index,
                                                              device_index=self.device_index)
        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {f"{self.identifier}.offset": shape, f"{self.identifier}": shape2}


class CPACSServoCutOutCreator(AbstractShapeCreator):
    def __init__(self,
                 creator_id: str,
                 aileron: str,
                 wing_index: int,
                 cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None,
                 loglevel=logging.INFO):
        self.aileron = aileron
        self._cpacs_configuration = cpacs_configuration
        self._wing_information = wing_information
        self.wing_index = wing_index
        super().__init__(creator_id, shapes_of_interest_keys=[self.aileron], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"trailing edge device ''  --> '{self.identifier}'")

        servo_size = (0.024, 0.024, 0.012)
        ruder_shape = shapes_of_interest[self.aileron]
        servo_recces_factory: ServoRecessFactory = ServoRecessFactory(self._cpacs_configuration,
                                                                      self.wing_index)
        servo = servo_recces_factory.create_servoRecess_option1(ruder_shape, servo_size)
        servo_dimensions = ShapeDimensions(servo)

        # Cable Pipe
        fuselage: CCPACSWing = self._cpacs_configuration.get_fuselage(1)
        fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
        fuselage_dimensions = ShapeDimensions(fuselage_loft)

        cable_pipe_factory: CablePipeFactory = CablePipeFactory(self._cpacs_configuration,
                                                                self.wing_index)
        points = cable_pipe_factory.points_route_thru(servo_dimensions, fuselage_dimensions)
        cable_pipe = cable_pipe_factory.create_complete_pipe(points, servo_dimensions.get_height() / 2)

        ConstructionStepsViewer.instance().display_this_shape(servo, logging.DEBUG, msg=f"{self.identifier}.servo")
        ConstructionStepsViewer.instance().display_this_shape(cable_pipe, logging.DEBUG, msg=f"{self.identifier}.cable")

        return {f"{self.identifier}.servo": servo, f"{self.identifier}.cable": cable_pipe}


class WingOffsetCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_loft: str, loglevel=logging.INFO):
        self.wing_loft = wing_loft
        super().__init__(creator_id, shapes_of_interest_keys=[self.wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"wing offset '{', '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        # Cut internal structure from Wing
        offset = 0.0008
        toleranz = offset / 8
        wing_offset: OTopo.TopoDS_Shape = BRepOffsetAPI_MakeOffsetShape(shapes_of_interest[self.wing_loft].shape(),
                                                                        offset,
                                                                        toleranz).Shape()
        while wing_offset is None and offset < 0.01:
            offset *= 1.2  # 20% mehr
            toleranz *= 1.2
            wing_offset: OTopo.TopoDS_Shape = BRepOffsetAPI_MakeOffsetShape(shapes_of_interest[self.wing_loft].shape(),
                                                                            offset,
                                                                            toleranz).Shape()
            logging.info(f"Offseting wing with {offset=} {toleranz=} {type(wing_offset)}")

        shape = TGeo.CNamedShape(wing_offset, "wing offset")
        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class WingLoftCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_index: Union[str, int], wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT","RIGHT","BOTH"]="RIGHT",
                 loglevel=logging.INFO):
        self.wing_side = wing_side
        self.wing_index = wing_index
        self._wing_config = wing_config
        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing loft from configuration --> '{self.identifier}'")

        wing_config = self._wing_config[self.wing_index]
        right_wing: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[0].root_airfoil,
                root_chord=wing_config.segments[0].root_chord,
                root_dihedral=wing_config.segments[0].root_dihedral,
                root_incidence=wing_config.segments[0].root_incidence,
                length=wing_config.segments[0].length,
                sweep=wing_config.segments[0].sweep,
                tip_chord=wing_config.segments[0].tip_chord,
                tip_dihedral=wing_config.segments[0].tip_dihedral,
                tip_incidence=wing_config.segments[0].tip_incidence,
                tip_airfoil=wing_config.segments[0].tip_airfoil))

        for segment_config in wing_config.segments[1:]:
            right_wing: Workplane = (
                right_wing.wing_segment(
                    length=segment_config.length,
                    sweep=segment_config.sweep,
                    tip_chord=segment_config.tip_chord,
                    tip_dihedral=segment_config.tip_dihedral,
                    tip_incidence=segment_config.tip_incidence,
                    tip_airfoil=segment_config.tip_airfoil))

        bb_right = right_wing.findSolid().BoundingBox(tolerance=1e-3)
        right_wing = right_wing.translate((0,-abs(bb_right.ymin),0))

        if self.wing_side == "LEFT":
            right_wing = right_wing.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing = right_wing.mirror("XZ")
            right_wing = right_wing.union(left_wing)

        #right_wing = right_wing.fix_shape()
        right_wing = right_wing.translate(wing_config.nose_pnt).display(name=f"{self.identifier}", severity=logging.DEBUG)

        return {self.identifier: right_wing}