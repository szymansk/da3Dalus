"""Pydantic schema for a single row in the Reynolds-dependent polar table (gh-493).

A row represents the polar coefficients (cd0, e_oswald) fitted to the fine-sweep
data within one V-band (centred on a velocity anchor point).

This schema is the cache boundary: ``build_re_table`` returns
``list[PolarReTableRow]``.  Callers serialise with ``.model_dump()`` before
writing to JSON-persisted context.  The ``_k_fit`` internal slope is NOT
included here (it is only used as an intermediate quantity inside
``_fit_band_with_ar``).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PolarReTableRow(BaseModel):
    """One Reynolds-band entry in the polar Re table.

    Fields
    ------
    re          : Reynolds number label Re = ρ·V·MAC/μ (at ISA SL) [dimensionless]
    v_mps       : Band centre velocity [m/s]
    cd0         : Fitted zero-lift drag coefficient, or None if fit failed
    e_oswald    : Fitted Oswald efficiency factor in (0.4, 1.0], or None if fit failed
    cl_max      : Maximum lift coefficient used as OLS window upper bound
    r2          : Coefficient of determination of the OLS fit (0–1), or None
    fallback_used : True when no valid fit was obtained for this band
    """

    re: int = Field(..., description="Aircraft-level Reynolds number ρ·V·MAC/μ")
    v_mps: float = Field(..., description="Band centre velocity [m/s]")
    cd0: float | None = Field(None, description="Fitted zero-lift drag coefficient")
    e_oswald: float | None = Field(
        None, description="Oswald span efficiency factor in (0.4, 1.0]"
    )
    cl_max: float = Field(..., description="CL_max used as OLS window upper bound")
    r2: float | None = Field(None, description="OLS R² (0–1); None when fit failed")
    fallback_used: bool = Field(
        ..., description="True when no valid polar fit was obtained for this band"
    )
