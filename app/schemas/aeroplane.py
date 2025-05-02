from typing import OrderedDict, Optional

from pydantic import BaseModel, Field, HttpUrl


class AeroplaneBase(BaseModel):
    name: str = Field(..., description="Aeroplane name", examples=["Vanilla"])
    wings: Optional[OrderedDict[str, OrderedDict[str, "Wing"]]] = Field(
        None, description="Aeroplane wings dictionary",
        examples=[
            {
                "name": "Main Wing",
                "symmetric": True,
                "x_secs": [
                    {
                        "xyz_le": [0, 0, 0],
                        "chord": 0.18,
                        "twist": 2,
                        "airfoil": "./components/airfoil/naca0015.dat",
                    },
                    {
                        "xyz_le": [0.01, 0.5, 0],
                        "chord": 0.16,
                        "twist": 0,
                        "airfoil": "./components/airfoil/naca0015.dat",
                    },
                ],
            }
        ]
    )
    fuselages: Optional[OrderedDict[str, OrderedDict[str, "Fuselage"]]] = Field(
        None, description="Aeroplane fuselages dictionary",
        examples=[
            {
                "name": "Fuselage",
                "x_secs": [
                    {
                        "xyz": [0, 0, 0],
                        "a": 0.5,
                        "b": 0.5,
                        "n": 2,
                    },
                    {
                        "xyz": [0.01, 0.5, 0],
                        "a": 0.6,
                        "b": 0.4,
                        "n": 1.5,
                    },
                ],
            }
        ],
    )
    xyz_ref: Optional[list[float]] = Field(
        [0, 0, 0],
        description="Reference point (e.g. CG) of the aeroplane in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )


class ControlSurface(BaseModel):
    name: str = Field(..., description="Control surface name",
                      examples=["Aileron", "Elevator", "Rudder", "Flap", "Elevon"])
    hinge_point: float = Field(
        0.8,
        description="Hinge point location of the control surface as a factor of the chord length",
        examples=[0.8, 0.7, 0.5],
    )
    symmetric: bool = Field(
        True,
        description="Whether the control surface moves symmetric (e.g flaps, elevator) or anti-symmetric (e.g. aileron, elevon, v-tail) to the left and right wing",
    )
    deflection: float = Field(
        0.0,
        description="Deflection angle of the control surface in degrees",
        examples=[5, 2, 0],
    )


class WingXSec(BaseModel):
    xyz_le: list[float] = Field(
        ...,
        description="Coordinates of the leading edge of the cross-section in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )
    chord: float = Field(
        ...,
        description="Chord length of the cross-section in meters",
        examples=[0.2, 0.18, 0.16],
    )
    twist: float = Field(
        ...,
        description="Twist angle of the cross-section in degrees",
        examples=[5, 2, 0],
    )
    airfoil: str | HttpUrl = Field(
        ...,
        description="Airfoil dat file location of the cross-section (file or URL)",
        examples=["./components/airfoil/naca0015.dat", "https://m-selig.ae.illinois.edu/ads/coord/naca0015.dat"],
    )
    control_surface: Optional[ControlSurface] = Field(
        None,
        description="Control surface on the cross-section",
        examples=[
            {
                "name": "Aileron",
                "hinge_point": 0.8,
                "symmetric": False,
                "deflection": 5,
            },
            {
                "name": "Flap",
                "hinge_point": 0.5,
                "symmetric": True,
                "deflection": 10,
            },
        ],
    )


class Wing(BaseModel):
    name: str = Field(..., description="Wing name", examples=["Main Wing", "Horizontal Stabilizer"])
    symmetric: bool = Field(
        True,
        description="Is the wing symmetric?",
        examples=[True, False],
    )
    x_secs: list[WingXSec] = Field(
        ...,
        description="List of cross-sections of the wing",
        min_length=2,
        examples=[
            [
                {
                    "xyz_le": [0, 0, 0],
                    "chord": 0.18,
                    "twist": 2,
                    "airfoil": "./components/airfoil/naca0015.dat",
                },
                {
                    "xyz_le": [0.01, 0.5, 0],
                    "chord": 0.16,
                    "twist": 0,
                    "airfoil": "./components/airfoil/naca0015.dat",
                },
            ]
        ],
    )


class FuselageXSecSuperEllipse(BaseModel):
    xyz: list[float] = Field(
        ...,
        description="Coordinates of the center of the cross-section in the local coordinate system",
        examples=[[0, 0, 0], [0.01, 0.5, 0], [0.08, 1, 0.1]],
    )
    a: float = Field(
        ...,
        description="Semi-major axis of the superellipse in meters",
        examples=[0.5, 0.6],
    )
    b: float = Field(
        ...,
        description="Semi-minor axis of the superellipse in meters",
        examples=[0.5, 0.4],
    )
    n: float = Field(
        ...,
        description="Superellipse exponent",
        examples=[2, 1.5],
    )


class Fuselage(BaseModel):
    name: str = Field(..., description="Fuselage name", examples=["Fuselage"])
    x_secs: list[FuselageXSecSuperEllipse] = Field(
        ...,
        description="List of cross-sections of the fuselage",
        min_length=2,
        examples=[
            [
                {
                    "xyz": [0, 0, 0],
                    "a": 0.5,
                    "b": 0.5,
                    "n": 2,
                },
                {
                    "xyz_ref": [0.01, 0.5, 0],
                    "a": 0.6,
                    "b": 0.4,
                    "n": 1.5,
                },
            ]
        ],
    )
