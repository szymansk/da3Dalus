"""Pydantic schema for per-configuration parabolic polar (gh-526).

A `ParabolicPolar` carries the C_D0 / e_Oswald / C_L_max fit for ONE
high-lift configuration (clean / takeoff / landing). The
`assumption_compute_service` runs one `AeroBuildup` pass per
configuration and caches the three polars in
`ComputationContext.polar_by_config`.

Audit reference: gh-525 (epic) finding C1.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ConfigName = Literal["clean", "takeoff", "landing"]
"""Configuration keys for `polar_by_config`."""

Provenance = Literal[
    "aerobuildup",  # full AeroBuildup pass with deflected flap
    "no_flap_geometry",  # aircraft has no flap → cloned from clean
    "aerobuildup_failed",  # the flap-deflected AeroBuildup raised → cloned from clean
]
"""How the polar entry was produced.

`aerobuildup_failed` covers any exception during the deflected sweep
(AeroBuildup convergence, parabolic-fit rejection, downstream NaN) —
the UI should treat it as "we tried, the solver fell over, falling back
to clean polar" rather than a successful but low-quality fit.
"""

RejectionGate = Literal[
    "insufficient_points",
    "non_monotonic_polar",
    "negative_slope_k",
    "non_positive_cd0",
    "unphysical_e_oswald",
    "cd0_stability_mismatch",
]
"""Which gate in `_fit_parabolic_polar` rejected the fit (gh-630)."""

RejectionCategory = Literal["sweep", "data", "design", "consistency"]
"""Coarse class of the rejection (gh-630).

- `sweep` — α-resolution too coarse; raise α density to fix.
- `data` — polar shape contaminated (laminar bubble, stall); profile / Re issue.
- `design` — geometry/config aerodynamically implausible; user-facing warning.
- `consistency` — fit conflicts with the stability-run baseline; internal sanity.
"""


_GATE_CATEGORY: dict[RejectionGate, RejectionCategory] = {
    "insufficient_points": "sweep",
    "non_monotonic_polar": "data",
    "negative_slope_k": "design",
    "non_positive_cd0": "consistency",
    "unphysical_e_oswald": "design",
    "cd0_stability_mismatch": "consistency",
}
"""Canonical gate→category mapping (gh-630). Enforced by the
`PolarRejection` model validator to prevent nonsensical pairs like
internal-only gates marked `design` (which would surface to users) or
design gates marked `sweep` (which would suppress real warnings)."""


class PolarRejection(BaseModel):
    """Why `_fit_parabolic_polar` could not produce a fit (gh-630).

    Disjoint from `e_oswald_quality`: set ONLY when no fit was produced.
    Surfaced to the UI only when `category == "design"`.
    """

    gate: RejectionGate = Field(..., description="Which rejection guard fired")
    category: RejectionCategory = Field(..., description="Coarse class — controls UI visibility")
    fitted_value: float | None = Field(
        None, description="Numeric value that triggered the rejection, when meaningful"
    )
    threshold: str = Field(..., description="Threshold expression the value failed against")
    hint: str = Field(..., description="Human-readable explanation; shown to user when design")

    @model_validator(mode="after")
    def _check_canonical_gate_category(self) -> "PolarRejection":
        expected = _GATE_CATEGORY[self.gate]
        if self.category != expected:
            raise ValueError(
                f"non-canonical gate/category pair: gate={self.gate!r} requires "
                f"category={expected!r}, got {self.category!r}"
            )
        return self


class ParabolicPolar(BaseModel):
    """Parabolic drag polar for one high-lift configuration.

    Fields mirror the gh-486 `e_oswald*` keys at the top level of
    `ComputationContext`, but scoped to one configuration. The clean
    entry duplicates the existing top-level keys for backward compat;
    `takeoff` / `landing` entries are new.
    """

    cd0: float | None = Field(None, description="Zero-lift drag coefficient (parabolic fit)")
    e_oswald: float | None = Field(None, description="Oswald span efficiency factor in (0.4, 1.0]")
    cl_max: float = Field(..., description="Maximum lift coefficient for this configuration")
    e_oswald_r2: float | None = Field(None, description="R² of the parabolic OLS fit (0–1)")
    e_oswald_quality: Literal["high", "medium", "low", "unknown"] = Field(
        "unknown", description="Bucketed quality label derived from R²"
    )
    flap_deflection_deg: float = Field(
        0.0, description="Flap deflection used to produce this polar"
    )
    provenance: Provenance = Field("aerobuildup", description="How the polar entry was produced")
    rejection: PolarRejection | None = Field(
        None,
        description="Set only when the parabolic fit was rejected (gh-630); "
        "disjoint from e_oswald_quality which applies to successful fits.",
    )


PolarByConfig = dict[ConfigName, ParabolicPolar]
"""Three-entry mapping cached under `ComputationContext.polar_by_config`.

Serialised to JSON as ``{cfg: ParabolicPolar.model_dump() for cfg in ...}``
so it survives the round-trip through SQLAlchemy's JSON column.
"""
