from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Schema für OperatingPointSet
class OperatingPointSetSchema(BaseModel):
    name: str
    description: str
    operating_points: list[int]

    model_config = ConfigDict(from_attributes=True)

class OperatingPointSchema(BaseModel):
    name: Optional[str] = Field(None, description="Name of the operating point")
    description: Optional[str] = Field(None, description="Description of the operating point")

    # Operating point parameters
    velocity: float = Field(10.0, description="Velocity in m/s")
    alpha: float | list[float] = Field(0.0, description="Angle of attack in degrees")
    beta: float = Field(0.0, description="Sideslip angle in degrees")
    p: float = Field(0.0, description="Roll rate in rad/s")
    q: float = Field(0.0, description="Pitch rate in rad/s")
    r: float = Field(0.0, description="Yaw rate in rad/s")

    xyz_ref: List[float] \
        = Field([0.0, 0.0, 0.0], description="default location in meters about which moments and rotation rates are defined (if doing trim calculations, xyz_ref must be the CG location)")

    # Atmosphere parameters
    altitude: float = Field(0.0, description="Altitude in meters")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "level_flight",
                "description": "Level flight at sea level",
                "velocity": 15.0,
                "alpha": [0.0],
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "altitude": 0.0,
                "xyz_ref": [0.0, 0.0, 0.0],
            }
        },
    )


class OperatingPointStatus(str, Enum):
    TRIMMED = "TRIMMED"
    NOT_TRIMMED = "NOT_TRIMMED"
    LIMIT_REACHED = "LIMIT_REACHED"


class StoredOperatingPointCreate(BaseModel):
    name: str
    description: str
    aircraft_id: Optional[int] = None
    config: str = Field("clean", description="Aircraft configuration name, e.g. clean/takeoff/landing.")
    status: OperatingPointStatus = Field(OperatingPointStatus.NOT_TRIMMED)
    warnings: list[str] = Field(default_factory=list)
    controls: dict[str, float] = Field(default_factory=dict, description="Trim outputs such as throttle/elevator.")
    velocity: float = Field(..., description="Velocity in m/s")
    alpha: float = Field(..., description="Angle of attack in radians")
    beta: float = Field(..., description="Sideslip angle in radians")
    p: float = Field(..., description="Roll rate in rad/s")
    q: float = Field(..., description="Pitch rate in rad/s")
    r: float = Field(..., description="Yaw rate in rad/s")
    xyz_ref: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    altitude: float = Field(..., description="Altitude in meters")

    model_config = ConfigDict(from_attributes=True)


class StoredOperatingPointRead(StoredOperatingPointCreate):
    id: int


class GenerateOperatingPointSetRequest(BaseModel):
    replace_existing: bool = Field(
        False,
        description="If true, delete existing operating points and sets for the aircraft before generating new ones.",
    )
    profile_id_override: Optional[int] = Field(
        default=None,
        description="Optional profile ID to use instead of the aircraft-assigned flight profile.",
    )


class TrimOperatingPointRequest(BaseModel):
    name: str = Field(
        "custom_trim_point",
        description="Name of the operating point to trim.",
    )
    config: str = Field(
        "clean",
        description="Aircraft configuration label, for example clean/takeoff/landing.",
    )
    velocity: float = Field(..., gt=0.0, description="Target velocity in m/s.")
    altitude: float = Field(0.0, description="Target altitude in meters.")
    beta_target_deg: float = Field(0.0, description="Target sideslip in degrees.")
    n_target: float = Field(1.0, gt=0.0, description="Target load factor n.")
    profile_id_override: Optional[int] = Field(
        default=None,
        description="Optional profile ID to use instead of the aircraft-assigned flight profile.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Optional custom warning tags to carry into the trim output.",
    )


class TrimmedOperatingPointRead(BaseModel):
    source_flight_profile_id: Optional[int] = None
    point: StoredOperatingPointCreate

    model_config = ConfigDict(from_attributes=True)


class GeneratedOperatingPointSetRead(BaseModel):
    id: int
    name: str
    description: str
    aircraft_id: Optional[int] = None
    source_flight_profile_id: Optional[int] = None
    operating_points: list[StoredOperatingPointRead]

    model_config = ConfigDict(from_attributes=True)
