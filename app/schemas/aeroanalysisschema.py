from typing import List, Optional

from pydantic import BaseModel, Field

# Schema für OperatingPointSet
class OperatingPointSetSchema(BaseModel):
    name: str
    description: str
    operating_points: list[int]

    class Config:
        from_attributes = True

class OperatingPointSchema(BaseModel):
    name: Optional[str] = Field(None, description="Name of the operating point")
    description: Optional[str] = Field(None, description="Description of the operating point")

    # Operating point parameters
    velocity: float = Field(10.0, description="Velocity in m/s")
    alpha: float = Field(0.0, description="Angle of attack in degrees")
    beta: float = Field(0.0, description="Sideslip angle in degrees")
    p: float = Field(0.0, description="Roll rate in rad/s")
    q: float = Field(0.0, description="Pitch rate in rad/s")
    r: float = Field(0.0, description="Yaw rate in rad/s")

    xyz_ref: List[float] \
        = Field([0.0, 0.0, 0.0], description="default location in meters about which moments and rotation rates are defined (if doing trim calculations, xyz_ref must be the CG location)")

    # Atmosphere parameters
    altitude: float = Field(0.0, description="Altitude in meters")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "level_flight",
                "description": "Level flight at sea level",
                "velocity": 15.0,
                "alpha": 0.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "altitude": 0.0,
                "xyz_ref": [0.0, 0.0, 0.0],
            }
        }
