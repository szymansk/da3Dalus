import logging
from typing import Union, Literal

from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration

from cq_plugins.wing.wing_segment import wing_segment
from cq_plugins.wing.wing_root_segment import wing_root_segment
from cq_plugins.fix_shape.fix_shape import fix_shape

class WingLoftCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 wing_index: Union[str, int],
                 offset: float = 0,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT","RIGHT","BOTH"]="RIGHT",
                 loglevel=logging.INFO):
        self.wing_side = wing_side
        self.wing_index = wing_index
        self.offset = offset
        self._wing_config = wing_config
        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing loft from configuration --> '{self.identifier}'")

        wing_config: WingConfiguration = self._wing_config[self.wing_index]
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
                tip_airfoil=wing_config.segments[0].tip_airfoil,
                offset=self.offset))

        current: Workplane = right_wing
        for segment_config in wing_config.segments[1:]:
            current = current.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=self.offset)
            right_wing.add(current)

        #bb_right = right_wing.findSolid().BoundingBox(tolerance=1e-3)
        #right_wing = right_wing.translate((0,-abs(bb_right.ymin)-1, 0))
        #right_wing = right_wing.fix_shape()

        if self.wing_side == "LEFT":
            right_wing = right_wing.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing = right_wing.mirror("XZ")
            right_wing = right_wing.union(left_wing)

        right_wing = right_wing.fix_shape()
        right_wing = right_wing.translate(wing_config.nose_pnt).display(name=f"{self.identifier}", severity=logging.DEBUG)

        return {self.identifier: right_wing}
