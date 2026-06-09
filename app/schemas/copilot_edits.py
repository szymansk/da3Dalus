"""Edit-ops DSL for the agentic copilot (gh-937).

A small validated discriminated-union of operations the copilot may apply to
a design.  All ops are Pydantic models; the union is validated before any DB
write.

Units: WingConfiguration uses **millimetres** for chord and span dimensions;
dihedral/twist/incidence are in **degrees**.  This matches the cad_designer
WingConfiguration/XSec convention (see CLAUDE.md).
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Individual op models
# ---------------------------------------------------------------------------


class SetAssumption(BaseModel):
    """Set a design assumption estimate value."""

    type: Literal["SetAssumption"] = "SetAssumption"
    param: str = Field(
        ...,
        description=(
            "Parameter name to update (e.g. 'mass', 'cg_x', 'target_static_margin', "
            "'cd0', 'cl_max', 'g_limit').  Must be a valid VALID_PARAMETERS value."
        ),
    )
    value: float = Field(..., description="New estimate value in SI units or degrees.")


class SetXsec(BaseModel):
    """Modify one or more fields of an existing cross-section by index.

    Only fields that are explicitly provided (not None) are changed;
    the rest are preserved from the current WingConfiguration.
    """

    type: Literal["SetXsec"] = "SetXsec"
    wing: str = Field(..., description="Wing name (e.g. 'main_wing', 'horizontal_tail').")
    index: int = Field(
        ...,
        ge=0,
        description="Zero-based cross-section index in the segment list.",
    )
    chord: Optional[float] = Field(
        None,
        gt=0,
        description="Chord length in millimetres.  Modifies the tip_airfoil.chord of segment[index-1] and root_airfoil.chord of segment[index].",
    )
    twist: Optional[float] = Field(
        None,
        description="Incidence/twist angle in degrees (positive = leading edge up).",
    )
    airfoil: Optional[str] = Field(
        None,
        description="Airfoil file path (e.g. './components/airfoils/rg15.dat').",
    )
    dihedral: Optional[float] = Field(
        None,
        description="Dihedral angle in degrees (positive = wingtip up).",
    )


class AddXsec(BaseModel):
    """Insert a new cross-section at a given index.

    The new x-sec is spliced in: segment[at_index-1] gets a new tip and a
    new segment[at_index] is inserted before the existing one.
    Use dihedral to model a winglet (dihedral knee at the tip).
    """

    type: Literal["AddXsec"] = "AddXsec"
    wing: str = Field(..., description="Wing name.")
    at_index: int = Field(
        ...,
        ge=1,
        description=(
            "Position at which to insert the new cross-section (1-based from root). "
            "The new x-sec becomes the tip of the segment at at_index-1."
        ),
    )
    chord: float = Field(..., gt=0, description="Chord of the new x-sec in mm.")
    span: float = Field(
        ...,
        gt=0,
        description="Span (length) of the NEW segment from the previous x-sec to this one, in mm.",
    )
    airfoil: Optional[str] = Field(
        None,
        description="Airfoil for the new x-sec; defaults to the same airfoil as the preceding x-sec.",
    )
    twist: Optional[float] = Field(None, description="Incidence/twist in degrees; defaults to 0.")
    dihedral: Optional[float] = Field(
        None,
        description="Dihedral angle in degrees.  Use this to create a winglet knee.",
    )


class RemoveXsec(BaseModel):
    """Remove an interior cross-section (and its associated segment).

    Cannot remove the root (index 0) or the last x-sec.
    """

    type: Literal["RemoveXsec"] = "RemoveXsec"
    wing: str = Field(..., description="Wing name.")
    index: int = Field(
        ...,
        ge=1,
        description="Zero-based index of the cross-section to remove (must not be 0 or the last).",
    )


class SetWingParam(BaseModel):
    """Set wing-level parameters (currently: sweep per-segment or global dihedral).

    This op modifies the sweep and/or dihedral fields of every segment in the wing
    if provided at the top level.  For per-segment overrides, use SetXsec instead.
    """

    type: Literal["SetWingParam"] = "SetWingParam"
    wing: str = Field(..., description="Wing name.")
    sweep_mm: Optional[float] = Field(
        None,
        description=(
            "Sweep in mm (translation of tip relative to root along x). "
            "Applied uniformly to ALL segments."
        ),
    )
    dihedral: Optional[float] = Field(
        None,
        description="Dihedral angle in degrees applied uniformly to ALL x-sec transitions.",
    )


class ReplaceWingConfig(BaseModel):
    """Replace the entire WingConfiguration for a wing (escape hatch for exotic geometry).

    The provided wing_config is the full WingConfigurationSchema payload
    (same format as the PUT /wings/{name}/from-wingconfig endpoint).
    All units in mm.
    """

    type: Literal["ReplaceWingConfig"] = "ReplaceWingConfig"
    wing: str = Field(..., description="Wing name.")
    wing_config: dict = Field(
        ...,
        description=(
            "Full WingConfiguration JSON payload (segments, nose_pnt, symmetric). "
            "All chord/span dimensions in mm."
        ),
    )


# ---------------------------------------------------------------------------
# Discriminated union
# ---------------------------------------------------------------------------

EditOp = Annotated[
    Union[
        SetAssumption,
        SetXsec,
        AddXsec,
        RemoveXsec,
        SetWingParam,
        ReplaceWingConfig,
    ],
    Field(discriminator="type"),
]
