import logging
from typing import Union, Literal, Optional

from cadquery import Workplane
from pydantic import NonNegativeInt

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration
from cad_designer.airplane.types import WingSides


class WingLoftCreator(AbstractShapeCreator):
    """Creates a solid loft shape of the full wing from wing configuration segments.

    Attributes:
        wing_index (Union[str, int]): Index or identifier of the wing in the configuration.
        offset (float): Inward offset applied to the wing surface in mm.
        wing_side (str): Which side to create: LEFT, RIGHT, or BOTH.
        connected (bool): Whether to fill the gap between wing halves when dihedral is non-zero.

    Returns:
        {id} (Workplane): Solid wing loft shape.
    """

    suggested_creator_id = "{wing_index}.loft"

    def __init__(self, creator_id: str, wing_index: Union[str, int], offset: float = 0,
                 wing_config: Optional[dict[NonNegativeInt, WingConfiguration]] = None,
                 wing_side: Optional[WingSides] = None, connected:bool=True, loglevel=logging.INFO):
        self.wing_side: WingSides = wing_side
        self.wing_index = wing_index
        self.offset = offset
        self.connected = connected
        self._wing_config: dict[int, WingConfiguration] = wing_config
        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing loft from configuration --> '{self.identifier}'")
        wing_config: WingConfiguration = self._wing_config[self.wing_index]
        if self.wing_side is None:
            if wing_config.symmetric:
                self._wing_side = "BOTH"
            else:
                self._wing_side = "RIGHT"

        segment: int = 0
        root_plane = wing_config.get_wing_workplane(segment).plane.rotated((90,0,0))
        tip_plane = wing_config.get_wing_workplane(segment+1).plane.rotated((90,0,0))

        right_wing: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[segment].root_airfoil.airfoil,
                root_chord=wing_config.segments[segment].root_airfoil.chord,
                root_dihedral=wing_config.segments[segment].root_airfoil.dihedral_as_rotation_in_degrees,
                root_incidence=wing_config.segments[segment].root_airfoil.incidence,
                length=wing_config.segments[segment].length,
                sweep=wing_config.segments[segment].sweep,
                tip_chord=wing_config.segments[segment].tip_airfoil.chord,
                tip_dihedral=wing_config.segments[segment].tip_airfoil.dihedral_as_rotation_in_degrees,
                tip_incidence=wing_config.segments[segment].tip_airfoil.incidence,
                tip_airfoil=wing_config.segments[segment].tip_airfoil.airfoil,
                offset=self.offset,
                number_interpolation_points=wing_config.segments[segment].number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane,
                connected=self.connected,
            ))

        current: Workplane = right_wing
        for idx, segment_config in enumerate(wing_config.segments[1:]):
            root_plane = wing_config.get_wing_workplane(idx + 1).plane.rotated((90, 0, 0))
            tip_plane = wing_config.get_wing_workplane(idx + 2).plane.rotated((90, 0, 0))

            current = current.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_airfoil.chord,
                tip_dihedral=segment_config.tip_airfoil.dihedral_as_rotation_in_degrees,
                tip_incidence=segment_config.tip_airfoil.incidence,
                tip_airfoil=segment_config.tip_airfoil.airfoil,
                offset=self.offset,
                number_interpolation_points=segment_config.number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane
            )
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
        right_wing.display(name=f"wing loft '{self.identifier}'")

        return {self.identifier: right_wing}
