"""Schema for forward CG limit result — gh-500 (Anderson §7.7 elevator authority).

Produced by ``elevator_authority_service.compute_forward_cg_limit`` and consumed
by ``loading_scenario_service.compute_stability_envelope`` to replace the 0.30·MAC
stub with a physics-based limit.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ForwardCGConfidence(str, Enum):
    """Five-tier confidence classification for the forward CG limit calculation.

    Tiers reflect solver path and aircraft configuration:
      - asb_high_with_flap: ASB AeroBuildup on conventional aircraft + flap run (highest accuracy)
      - asb_high_clean: ASB on conventional aircraft, no flap (clean configuration)
      - asb_warn_with_flap: ASB on warn-tier layout (V-tail/elevon/heavy-flap) + flap run
      - asb_warn_clean: ASB on warn-tier layout, clean configuration
      - stub: 0.30·MAC conservative fallback (no physics data available)

    Note: An AVL high-fidelity tier (avl_full) is planned in gh-516.
    """

    asb_high_with_flap = "asb_high_with_flap"
    asb_high_clean = "asb_high_clean"
    asb_warn_with_flap = "asb_warn_with_flap"
    asb_warn_clean = "asb_warn_clean"
    stub = "stub"


class ForwardCGResult(BaseModel):
    """Result of the forward CG limit calculation (gh-500, Anderson §7.7).

    The forward CG limit is the furthest-forward position where the aircraft
    can still be trimmed at stall with full elevator deflection (TE-UP).

    Physics formula (NP-centered trim inversion, Amendment B1):
      x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

    Sign convention (Amendment B3):
      Cm_δe is computed with TE-UP (negative) deflection → Cm_δe > 0
      δe_max = abs(negative_deflection_deg) * π/180
      Product Cm_δe · δe_max > 0 (nose-up trim contribution)
    """

    cg_fwd_m: float | None = Field(
        description=(
            "Forward CG stability limit [m, positive forward from datum]. "
            "None when no feasible forward CG exists (infeasibility guard S3)."
        )
    )
    confidence: ForwardCGConfidence = Field(
        description="Confidence tier reflecting the solver path and aircraft configuration."
    )
    cm_delta_e: float | None = Field(
        default=None,
        description=(
            "Pitching moment coefficient sensitivity to elevator deflection [1/rad]. "
            "Positive when measured with TE-UP (negative) deflection (Amendment B3). "
            "None for stub path."
        ),
    )
    cl_max_landing: float = Field(
        description=(
            "Maximum lift coefficient in landing configuration. "
            "Includes flap contribution if flap run was performed. "
            "Fallback: CL_max_clean + 0.5 (Roskam §4.7)."
        )
    )
    flap_state: Literal["deployed", "clean", "stub"] = Field(
        description=(
            "'deployed' when ΔCm_flap was computed via a flap-down ASB run, "
            "'clean' when no flap devices exist on the aircraft, "
            "'stub' when no ASB run was possible (fallback path)."
        )
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Informational or caution messages about the result quality.",
    )
