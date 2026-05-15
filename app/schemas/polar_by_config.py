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

from pydantic import BaseModel, Field

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


PolarByConfig = dict[ConfigName, ParabolicPolar]
"""Three-entry mapping cached under `ComputationContext.polar_by_config`.

Serialised to JSON as ``{cfg: ParabolicPolar.model_dump() for cfg in ...}``
so it survives the round-trip through SQLAlchemy's JSON column.
"""
