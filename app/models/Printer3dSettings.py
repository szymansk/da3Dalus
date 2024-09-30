from pydantic import BaseModel

class Printer3dSettings(BaseModel):
    layer_height: float
    wall_thickness: float
    rel_gap_wall_thickness: float
