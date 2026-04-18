import logging
from typing import Union

import math
import numpy as np
from cadquery import Workplane, Plane
from pydantic import NonNegativeInt

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration


class StandWingSegmentOnPrinterCreator(AbstractShapeCreator):
    """Transforms wing segment shapes to stand on the XY-plane for 3D printing.

    Attributes:
        shape_dict (dict): Mapping of segment index to shape key for each segment to transform.
        wing_index (Union[str, int]): Index or identifier of the wing in the configuration.
    """
    def __init__(self, creator_id: str,
                 shape_dict: dict[NonNegativeInt, str],
                 wing_index: Union[str, NonNegativeInt],
                 wing_config: dict[NonNegativeInt, WingConfiguration] = None,
                 loglevel=logging.INFO):
        self.shape_dict: dict[NonNegativeInt, str] = shape_dict
        self.wing_index: Union[str, NonNegativeInt] = wing_index
        self._wing_config: dict[NonNegativeInt, WingConfiguration] = wing_config
        super().__init__(creator_id, shapes_of_interest_keys=[*shape_dict.values()], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"stand segment on print surface: '{shapes_of_interest.keys()}'")
        wing_config: WingConfiguration = self._wing_config[self.wing_index]

        final_dict: dict[str, Workplane] = {}
        for i, wing_seg in enumerate(shape_list):
            segment = int(list(self.shape_dict.keys())[i])
            logging.info(f"==> stand segment '{segment}' on print surface: {self.shape_dict[str(i)]}.print")
            wp: Plane = wing_config.get_wing_workplane(segment=segment).plane if i != 0 else Workplane('XY').plane
            y = np.array(wp.yDir.toTuple())  # Initial vector
            angle_x = math.degrees(np.arctan2(y[1], y[2]))  # Angle to rotate around x-axis
            final_segment = (wing_seg.translate((-wp.origin.x, -wp.origin.y, -wp.origin.z))
                             .rotate((0, 0, 0), (1, 0, 0), angle_x))
            final_dict[f"{self.shape_dict[str(i)]}.print"] = final_segment.display(name=f"{self.shape_dict[str(i)]}.print", severity=logging.DEBUG)

        return final_dict
