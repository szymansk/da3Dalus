import logging
import math

from tigl3.configuration import CCPACSWingSegment
from tigl3.geometry import CNamedShape

from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class WingSegment:
    def __init__(self, root_x_list, tip_x_list, root_y_min, root_z_min, tip_y_min, tip_z_min, root_z_mid, tip_z_mid,
                 height, width, sweep_angle):
        """

        :param root_z_mid:
        :param tip_z_mid:
        :param tip_y_min:
        :param tip_z_min:
        :param root_x_list: a list with x coordinate values where the ribs should start
        :param tip_x_list: a list with x coordinate values where the ribs should end
        :param root_y_min: y coordinate where the rib should start
        :param root_z_min: z coordinate where the rib should start
        :param height: of the rib
        :param width: of the rib
        :param sweep_angle:
        """
        self.tip_z_mid = tip_z_mid
        self.root_z_mid = root_z_mid
        self.tip_z_min = tip_z_min
        self.tip_y_min = tip_y_min
        self.sweep_angle = sweep_angle
        self.root_x_list = root_x_list
        self.tip_x_list = tip_x_list
        self.root_y_min = root_y_min
        self.root_z_min = root_z_min

        self.height = height  # dicke des Profils
        self.width = width  # abstand von inside und outside


class WingInformation:
    def __init__(self, segments: list[WingSegment]):
        self.segments: list[WingSegment] = segments

    def get_max_height(self) -> float:
        current_max = 0
        for ws in self.segments:
            current_max = max(current_max, ws.height)
        return current_max

    def get_wing_length(self):
        return abs(self.segments[0].root_y_min - self.segments[-1].root_y_min)


class CPACSWingInformation(WingInformation):

    def __init__(self, cpacs_configuration, wing_index, horizontal_rib_quantity: int):
        wing = cpacs_configuration.get_wing(wing_index)
        wing_shape = wing.get_loft()
        segments = []
        for index in range(1, wing.get_segment_count() + 1):
            logging.debug(f"{index=}")
            segment: CCPACSWingSegment = wing.get_segment(index)
            inner_closure: CNamedShape = CNamedShape(segment.get_inner_closure(), "inner_closure")
            outer_closure: CNamedShape = CNamedShape(segment.get_outer_closure(), "outer_closure")

            ConstructionStepsViewer.instance().display_this_shape(inner_closure, logging.NOTSET, msg="inner_closure")
            ConstructionStepsViewer.instance().display_this_shape(outer_closure, logging.NOTSET, msg="outer_closure")

            inner_dimensions = ShapeDimensions(inner_closure)
            outer_dimensions = ShapeDimensions(outer_closure)
            inner_x_list = inner_dimensions.get_coordinates_on_axis(horizontal_rib_quantity)
            outer_x_list = outer_dimensions.get_coordinates_on_axis(horizontal_rib_quantity)

            lenght = inner_dimensions.get_length()
            # height = inner_dimensions.get_height()
            height = ShapeDimensions(wing_shape).get_height()
            logging.debug(f"{lenght=} {height=}")

            x_dif = abs(inner_dimensions.get_x_min() - outer_dimensions.get_x_min())
            y_dif = abs(inner_dimensions.get_y_min() - outer_dimensions.get_y_min())
            width = math.hypot(x_dif, y_dif)

            new_segment = WingSegment(root_x_list=inner_x_list, tip_x_list=outer_x_list,
                                      root_y_min=inner_dimensions.get_y_min(), root_z_min=inner_dimensions.get_z_min(),
                                      tip_y_min=outer_dimensions.get_y_min(), tip_z_min=outer_dimensions.get_z_min(),
                                      root_z_mid=inner_dimensions.get_z_mid(), tip_z_mid=outer_dimensions.get_z_mid(),
                                      height=height, width=width,
                                      sweep_angle=math.degrees(math.atan(x_dif / y_dif)))
            segments.append(new_segment)

        super().__init__(segments)
