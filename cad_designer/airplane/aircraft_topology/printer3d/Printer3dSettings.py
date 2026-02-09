from pydantic import PositiveFloat


class Printer3dSettings:
    def __init__(self,
                 layer_height: PositiveFloat = 0.24,
                 wall_thickness: PositiveFloat = 0.42,
                 rel_gap_wall_thickness: PositiveFloat = 0.075):
        self.layer_height = layer_height
        self.wall_thickness = wall_thickness
        self.rel_gap_wall_thickness = rel_gap_wall_thickness
