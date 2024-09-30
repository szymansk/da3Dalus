from typing import Optional

from pydantic import BaseModel

class Servo(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    leading_length: Optional[float] = None
    latch_z: Optional[float] = None
    latch_x: Optional[float] = None
    latch_thickness: Optional[float] = None
    latch_length: Optional[float] = None
    cable_z: Optional[float] = None
    screw_hole_lx: Optional[float] = None
    screw_hole_d: Optional[float] = None
