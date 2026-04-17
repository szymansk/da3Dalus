from pydantic import BaseModel, NonNegativeFloat, PositiveFloat, Field


class Servo(BaseModel):
    """Physical dimensions of a servo actuator.

    All fields are required — they describe the mechanical envelope that the
    CAD modeller needs to cut a servo pocket into the wing skin.
    """

    length: PositiveFloat = Field(description="X-dimension of the servo body (mm)")
    width: PositiveFloat = Field(description="Y-dimension of the servo body (mm)")
    height: PositiveFloat = Field(description="Z-dimension of the servo body (mm)")
    leading_length: NonNegativeFloat = Field(
        description="X from the front edge to the rotation axis (mm)"
    )
    latch_z: NonNegativeFloat = Field(
        description="Z-position of the lower edge of the latch (mm)"
    )
    latch_x: NonNegativeFloat = Field(
        description="X-dimension of the latch (mm)"
    )
    latch_thickness: NonNegativeFloat = Field(
        description="Thickness of the latch (mm)"
    )
    latch_length: NonNegativeFloat = Field(
        description="Length of the latch (mm)"
    )
    cable_z: NonNegativeFloat = Field(
        description="Z-position of the cable exit (mm)"
    )
    screw_hole_lx: NonNegativeFloat = Field(
        description="X-distance of the screw hole from the leading edge (mm)"
    )
    screw_hole_d: NonNegativeFloat = Field(
        description="Diameter of the screw hole (mm)"
    )
