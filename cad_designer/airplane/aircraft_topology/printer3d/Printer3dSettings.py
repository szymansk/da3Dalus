from pydantic.v1 import PositiveFloat


class Printer3dSettings:
    def __init__(self,
                 layer_height: PositiveFloat,
                 wall_thickness: PositiveFloat,
                 rel_gap_wall_thickness: PositiveFloat):
        self.layer_height = layer_height
        self.wall_thickness = wall_thickness
        self.rel_gap_wall_thickness = rel_gap_wall_thickness
