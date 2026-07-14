"""Pydantic request/response schemas for the spar-plan endpoint (gh-1031).

The solver core (gh-1030,
:mod:`cad_designer.airplane.geometry.spar_solver`) produces a ``SparPlan`` in
**millimetres** (wing-local frame). This API exposes lengths in **metres**
(project convention) — the service converts mm -> m (x0.001).

The request carries the spar-layout knobs plus the spanwise bending-moment
distribution (from the #1002 spanwise-loads endpoint) and the #1008 material /
sizing inputs the solver needs to compute strength-required diameters.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class MomentSample(BaseModel):
    """One spanwise bending-moment sample (from #1002 spanwise loads)."""

    y_span: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Span fraction 0..1 across the semi-span (root=0, tip=1).",
    )
    bending_moment_Nm: float = Field(
        ...,
        description="Bending moment magnitude reference at this station (N·m).",
    )


class TorsionSample(BaseModel):
    """One spanwise torsion sample for the rear (torsion) spar (gh-1038).

    ``torsion_moment_Nm`` is the section torsion T(y) about the front-spar line
    (the wing's pitching moment carried into the structure). The rear spar
    reacts this couple over the front–rear spar spacing — see
    :func:`app.services.spar_plan_service._make_rear_moment_fn`.
    """

    y_span: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Span fraction 0..1 across the semi-span (root=0, tip=1).",
    )
    torsion_moment_Nm: float = Field(
        ...,
        description="Section torsion magnitude T(y) about the front spar line (N·m).",
    )


class SparPlanRequest(BaseModel):
    """Request body for ``POST /aeroplanes/{id}/spar-plan``.

    The spanwise moment distribution (``moments``) comes from the #1002
    spanwise-loads endpoint; the material + sizing knobs mirror #1008 spar
    sizing. Layout knobs (``front_x_over_chord`` / ``rear_x_over_chord`` /
    sampling ``n_span``) and clearance (``packing_factor``) are optional.

    gh-1038: the **rear** spar is sized from TORSION, not the primary bending
    moment. Supply ``torsion_moments`` (T(y) about the front spar) and the rear
    spar is sized for the couple T(y) reacted over the front–rear spar spacing
    (plus ``rear_secondary_bending_fraction`` of the bending moment). When no
    torsion distribution is given, a documented proxy
    T(y) ≈ ``pitching_moment_proxy_ratio`` · M(y) is used. The front spar stays
    bending-driven via ``moments``.
    """

    material_id: int = Field(
        ...,
        description=(
            "ID of a Component with component_type='material' and "
            "allowable_bending_stress_mpa set (used for strength sizing)."
        ),
    )
    moments: list[MomentSample] = Field(
        ...,
        min_length=1,
        description=(
            "Spanwise bending-moment distribution (root->tip) used to size the "
            "strength-required spar diameter at each station."
        ),
    )
    wing_name: Optional[str] = Field(
        None,
        description=("Name of the wing to plan. When omitted, the aeroplane's first wing is used."),
    )
    front_x_over_chord: Optional[float] = Field(
        None,
        gt=0.0,
        lt=1.0,
        description=(
            "Chord fraction for the front (bending) spar. When omitted, the "
            "section's max-thickness location is used."
        ),
    )
    rear_x_over_chord: float = Field(
        0.65,
        gt=0.0,
        lt=1.0,
        description="Chord fraction for the rear (torsion) spar. Default 0.65.",
    )
    n_span: int = Field(
        6,
        ge=2,
        le=200,
        description="Number of spanwise sample stations per half (root->tip).",
    )
    packing_factor: float = Field(
        0.8,
        gt=0.0,
        le=1.0,
        description=(
            "Fraction of the local section depth the spar may occupy; the "
            "remainder is skin/glue clearance. Default 0.8."
        ),
    )
    safety_factor_j: float = Field(
        1.5,
        gt=0.0,
        description="Safety factor applied to M_design = |M|·g_limit·j.",
    )
    sigma_allow_mpa_override: Optional[float] = Field(
        None,
        gt=0.0,
        description=(
            "Override allowable bending stress (MPa). When None, the material's "
            "allowable_bending_stress_mpa is used."
        ),
    )
    torsion_moments: Optional[list[TorsionSample]] = Field(
        None,
        description=(
            "gh-1038: Spanwise torsion distribution T(y) about the front spar "
            "(N·m). The REAR spar is sized for this couple reacted over the "
            "front–rear spar spacing. When omitted, a documented proxy "
            "T(y) ≈ pitching_moment_proxy_ratio · M(y) is used instead."
        ),
    )
    rear_secondary_bending_fraction: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description=(
            "gh-1038: Fraction of the bending moment M(y) the rear spar also "
            "carries as genuine secondary bending, added on top of the torsion "
            "reaction. Default 0 (rear is torsion-only)."
        ),
    )
    pitching_moment_proxy_ratio: float = Field(
        0.10,
        ge=0.0,
        description=(
            "gh-1038: Used ONLY when torsion_moments is not supplied. Proxy "
            "ratio T(y)/M(y) ≈ |Cm|/|CL| · 1 representing the section torsion "
            "as a fraction of the bending moment. Default 0.10 (a typical "
            "cambered-airfoil pitching-moment-to-bending ratio). Replace with a "
            "real T(y) from the strip pitching moments when available "
            "(follow-up #1002 extension)."
        ),
    )
    shape: Literal["tube", "rod", "rectangular", "capped"] = Field(
        "tube",
        description=(
            "gh-1080: Cross-section shape for both spars. "
            "'tube' (default) — hollow round tube, telescoping-capable; "
            "'rod' — solid round, no bore, joiner connections; "
            "'rectangular' — solid rectangular box; "
            "'capped' — I/C beam with flanges."
        ),
    )


class SparPieceOut(BaseModel):
    """One straight spar piece. Lengths in **metres**, wing-local frame."""

    role: str = Field(..., description="Structural role: 'front' (bending) or 'rear' (torsion).")
    spare_origin: list[float] = Field(
        ...,
        description="Piece root origin (x, y, z) in the wing-local frame (m).",
    )
    spare_vector: list[float] = Field(
        ...,
        description="Unit direction vector the piece runs along (dimensionless).",
    )
    outer_d: float = Field(..., description="Outer diameter (m).")
    inner_d: float = Field(..., description="Inner diameter / bore (m); 0 for a solid rod.")
    wall: float = Field(..., description="Wall thickness = (outer_d - inner_d)/2 (m).")
    shape: str = Field(..., description="Cross-section shape (e.g. 'tube').")
    governing_y: float = Field(
        ...,
        description="Spanwise position of the governing (highest-moment) station (m).",
    )
    x_over_chord: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "gh-1072: chordwise location (x/c, 0..1) this piece was placed at. "
            "Front (main) ≈ the section max-thickness location; rear (torsion) = "
            "the requested rear x/c clamped forward of the control-surface hinge."
        ),
    )
    y_start: float = Field(
        ...,
        description=(
            "Spanwise position where this piece starts (root-side, m; root=0). "
            "Equals the piece's spare_origin y (gh-1057)."
        ),
    )
    y_end: float = Field(
        ...,
        description=(
            "Spanwise position where this piece ends (tip-side, m). For a "
            "telescoping run, the next piece's y_start equals this value, and "
            "that is the telescoping joint position (gh-1057)."
        ),
    )
    utilisation: float = Field(
        ...,
        description=(
            "Fraction of the local containment band the piece OD uses. A value "
            ">1 means no round tube strong enough fits the section (see feasible)."
        ),
    )
    joint_to_next: Optional[str] = Field(
        None,
        description="Joint to the next (tip-side) piece, e.g. 'telescoping'. None if last.",
    )
    feasible: bool = Field(
        True,
        description="False when the section cannot contain a round tube strong enough.",
    )
    infeasibility_reason: Optional[str] = Field(
        None,
        description="Human-readable reason when the piece is infeasible; None otherwise.",
    )
    # gh-1080: extended dims for rectangular/capped shapes; None for tube/rod.
    width: Optional[float] = Field(
        None,
        description=(
            "gh-1080: Flange/web width (m) for a rectangular cross-section. None for tube and rod."
        ),
    )
    height: Optional[float] = Field(
        None,
        description=(
            "gh-1080: Profile height (m) for a rectangular cross-section — "
            "equals the contained-band depth at the governing station. "
            "None for tube and rod."
        ),
    )
    cap_width: Optional[float] = Field(
        None,
        description=(
            "gh-1080: Flange width (m) for a capped (I/C-beam) cross-section. "
            "None for tube, rod, and rectangular."
        ),
    )


class SparPlanResponse(BaseModel):
    """Response for ``POST /aeroplanes/{id}/spar-plan`` (gh-1031). Lengths in metres."""

    front_pieces: list[SparPieceOut] = Field(
        ...,
        description="Front (bending) spar pieces, root->tip.",
    )
    rear_pieces: list[SparPieceOut] = Field(
        ...,
        description="Rear (torsion) spar pieces, root->tip.",
    )
    front_joint: str = Field(
        ...,
        description="Front root joint: 'continuous' | 'reinforcement+joiner'.",
    )
    rear_joint: str = Field(
        ...,
        description="Rear root joint: 'continuous' | 'bent-pin'.",
    )
    reinforcement: Optional[SparPieceOut] = Field(
        None,
        description=(
            "Short collinear root reinforcement piece, present when the front "
            "halves cannot be a single collinear carry-through."
        ),
    )
    feasible: bool = Field(
        True,
        description=(
            "False when any spar piece cannot contain a round tube strong enough "
            "(see infeasibility_reason). A feasible=False plan is not buildable "
            "as-is."
        ),
    )
    infeasibility_reason: Optional[str] = Field(
        None,
        description="Reason for the first infeasible piece, or None when the plan is feasible.",
    )
