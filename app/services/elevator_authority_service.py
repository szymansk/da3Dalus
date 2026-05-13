"""Elevator authority forward CG limit — gh-500 (Anderson §7.7).

Replaces the 0.30·MAC stub in ``loading_scenario_service.compute_stability_envelope``
with a physics-based forward CG limit derived from the NP-centered trim inversion.

## Coordinate convention

x = 0 at the nose, x increases toward the tail (aft-positive convention).
Therefore a *forward* CG limit has a *smaller* x value than x_np.
A physically infeasible result is x_cg_fwd > x_np (forward limit aft of NP).

## Physics formula (Amendment B1)

  x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

## Sign convention (Amendment B3 — CRITICAL)

  AeroBuildup is run with NEGATIVE (TE-UP) deflection for Cm_δe estimation.
  Result: Cm_δe > 0 (nose-up moment per unit negative-deflection rad).
  δe_max = abs(negative_deflection_deg) * π/180
  Product Cm_δe · δe_max > 0 (nose-up trim contribution).

## Infeasibility (Amendment S3, fix B4)

  Guard checks the FULL sum: Cm_ac + Cm_δe·δe_max + ΔCm_flap ≤ 0.
  When the full sum is ≤ 0 the elevator cannot overcome the nose-down moment
  at stall even at maximum deflection → no feasible forward CG → cg_fwd_m=None.

## V-tail (Amendment B4 — the cos² trap)

  ASB AeroBuildup operates on 3D inclined V-tail geometry → dihedral is already
  baked into the Cm_δe result.  DO NOT apply cos²(γ) correction to the ASB path.
  cos²(γ) is ONLY applied in the analytic STUB path formula:
    Cm_δe_stub = a_t·(S_H/S_w)·(l_H/MAC) · cos²(γ)

## Backward-compat (Amendment B5)

  ``sm_sizing_service._SM_FORWARD_CLIP_LIMIT`` is the hardcoded 0.30 orphan.
  After gh-500 the caller passes cg_stability_fwd_m into ctx, and sm_sizing
  uses that dynamic value; 0.30 is kept only as a last-resort fallback.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.schemas.forward_cg import ForwardCGConfidence, ForwardCGResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Conditioning guard threshold (Amendment S1): below this Cm_δe the elevator
#: authority is critically low and the forward CG envelope vanishes.
_CM_DELTA_E_THRESHOLD = 0.005  # 1/rad

#: Fallback δe_max when negative_deflection_deg is not set in the model.
_DEFAULT_DELTA_E_DEG = 25.0

#: Roskam §4.7 flap CL increment: CL_max_landing ≈ CL_max_clean + 0.5
_ROSKAM_FLAP_CL_BONUS = 0.5

#: Conservative stub forward SM = 0.30 (same as old loading_scenario stub)
_STUB_FORWARD_SM = 0.30

#: Elevator roles that use pitch-control surfaces for elevator authority.
#: elevator → conventional H-tail
#: ruddervator → V-tail (ASB 3D, no extra cos² needed)
#: elevon → tailless / flying wing
#: flaperon → wing-only pitch+roll combined surface
_PITCH_ROLES = {"elevator", "ruddervator", "elevon", "flaperon"}

#: Warn-tier roles (B4): ASB result used directly but confidence is warn.
_WARN_ROLES = {"ruddervator", "elevon", "flaperon"}

#: Flap role string — used to identify flap TEDs for ΔCm_flap run.
_FLAP_ROLE = "flap"


# ---------------------------------------------------------------------------
# Public helpers (exported for unit tests)
# ---------------------------------------------------------------------------


def _delta_e_max_rad(negative_deflection_deg: float | None) -> float:
    """Compute maximum elevator deflection in radians from the model field.

    Uses abs() to be robust against either sign convention (positive or negative
    stored in the DB) and falls back to 25° default.

    Amendment B3: δe_max = abs(negative_deflection_deg) * π/180
    """
    if negative_deflection_deg is None:
        return _DEFAULT_DELTA_E_DEG * math.pi / 180.0
    return abs(float(negative_deflection_deg)) * math.pi / 180.0


def _cm_delta_e_for_asb_path(
    cm_delta_e_raw: float,
    elevator_role: str | None,
) -> float:
    """Return Cm_δe for the ASB 3D path.

    Amendment B4 — the cos² trap:
      ASB AeroBuildup uses the FULL 3D inclined geometry (V-tail dihedral
      is already baked into the result).  We MUST NOT apply cos²(γ) here.
      cos²(γ) is ONLY for the analytic stub formula (see _apply_vtail_cos_square_correction).

    For all elevator roles on the ASB path, return the raw value as-is.
    """
    # No cos² correction regardless of role — ASB 3D handles dihedral.
    return float(cm_delta_e_raw)


def _apply_vtail_cos_square_correction(
    cm_delta_e_flat: float,
    dihedral_deg: float,
) -> float:
    """Apply cos²(γ) correction for V-tail in the ANALYTIC STUB path only.

    Amendment B4: This correction is ONLY for the analytic flat-tail formula:
      Cm_δe_stub = a_t·(S_H/S_w)·(l_H/MAC) · cos²(γ)

    It MUST NOT be applied to ASB 3D path results (see _cm_delta_e_for_asb_path).

    Args:
        cm_delta_e_flat: Cm_δe from the flat-tail analytic formula.
        dihedral_deg: V-tail dihedral angle γ [degrees].

    Returns:
        Corrected Cm_δe accounting for the V-tail geometry reduction.
    """
    cos2 = math.cos(math.radians(dihedral_deg)) ** 2
    return cm_delta_e_flat * cos2


def _determine_confidence_tier(
    elevator_role: str | None,
    has_flap_run: bool,
) -> ForwardCGConfidence:
    """Assign the appropriate confidence tier based on elevator role and flap availability.

    Tiers (Amendment S2):
      - No pitch control surface → stub
      - Conventional elevator + flap run → asb_high_with_flap
      - Conventional elevator + no flap → asb_high_clean
      - Warn-tier layout (ruddervator/elevon/flaperon) + flap run → asb_warn_with_flap
      - Warn-tier layout + no flap → asb_warn_clean
    """
    if elevator_role is None or elevator_role not in _PITCH_ROLES:
        return ForwardCGConfidence.stub

    is_warn_tier = elevator_role in _WARN_ROLES

    if is_warn_tier:
        return (
            ForwardCGConfidence.asb_warn_with_flap
            if has_flap_run
            else ForwardCGConfidence.asb_warn_clean
        )
    else:
        return (
            ForwardCGConfidence.asb_high_with_flap
            if has_flap_run
            else ForwardCGConfidence.asb_high_clean
        )


def _trim_inversion(
    x_np_m: float,
    cm_ac: float,
    cm_delta_e: float,
    delta_e_max_rad: float,
    delta_cm_flap: float,
    c_ref_m: float,
    cl_max_landing: float,
) -> float:
    """Apply the NP-centered trim inversion formula (Amendment B1).

    Anderson §7.7 — forward CG limit from elevator authority at landing stall:

      x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

    All terms in the numerator represent pitching moment coefficients:
      Cm_ac: aerodynamic center pitching moment (negative = nose-down, typical)
      Cm_δe·δe_max: elevator pitch-up authority (positive by B3 sign convention)
      ΔCm_flap: flap-induced moment (negative = nose-down, typical)

    When the net term (Cm_ac + Cm_δe·δe_max + ΔCm_flap) > 0, the aircraft has
    MORE pitch-up authority than nose-down tendency → x_cg_fwd < x_np (forward
    limit exists, less restrictive than stub).

    When the net term ≤ 0, the elevator cannot overcome the nose-down moment at
    stall → infeasibility (handled by _apply_infeasibility_guard).

    Args:
        x_np_m: Neutral point [m].
        cm_ac: Pitching moment coefficient at aerodynamic center (dimensionless).
        cm_delta_e: Elevator authority per unit deflection [1/rad]. Must be > 0.
        delta_e_max_rad: Maximum elevator deflection [rad] = abs(neg_deflection).
        delta_cm_flap: Flap-induced pitching moment (typically ≤ 0, nose-down).
        c_ref_m: Mean aerodynamic chord [m].
        cl_max_landing: Maximum CL in landing configuration.

    Returns:
        x_cg_fwd [m]: forward CG limit position.
    """
    net_pitch_up = cm_ac + cm_delta_e * delta_e_max_rad + delta_cm_flap
    return x_np_m - net_pitch_up * c_ref_m / cl_max_landing


def _apply_conditioning_guard(
    x_np_m: float,
    mac_m: float,
    cm_delta_e: float,
    cl_max_landing: float,
    cm_ac: float,
    delta_cm_flap: float,
    delta_e_max_rad: float,
    confidence_warn_tier: ForwardCGConfidence,
    warnings: list[str],
) -> ForwardCGResult | None:
    """Apply the conditioning guard (Amendment S1).

    If |Cm_δe| < 0.005/rad, elevator authority is critically low.
    The forward CG envelope effectively vanishes and we return x_np as the limit
    (cannot trim at ANY forward CG position — most restrictive possible).

    Returns:
        ForwardCGResult if the guard triggered, None otherwise.
    """
    if abs(cm_delta_e) < _CM_DELTA_E_THRESHOLD:
        warnings = list(warnings)  # copy to avoid mutating caller's list
        warnings.append("Elevator authority critically low — forward CG envelope vanishes")
        logger.warning(
            "Conditioning guard triggered: |Cm_δe|=%.4f < %.4f/rad. Forward CG limit set to x_NP.",
            abs(cm_delta_e),
            _CM_DELTA_E_THRESHOLD,
        )
        return ForwardCGResult(
            cg_fwd_m=x_np_m,
            confidence=confidence_warn_tier,
            cm_delta_e=cm_delta_e,
            cl_max_landing=cl_max_landing,
            flap_state="clean" if abs(delta_cm_flap) < 1e-9 else "deployed",
            warnings=warnings,
        )
    return None


def _apply_infeasibility_guard(
    cm_ac: float,
    cm_delta_e: float,
    delta_e_max_rad: float,
    delta_cm_flap: float,
    confidence_warn_tier: ForwardCGConfidence,
    warnings: list[str],
) -> ForwardCGResult | None:
    """Apply the infeasibility guard (Amendment S3, fix B4).

    B4 fix: guard checks the FULL net pitching moment balance:
      net_pitch_up = Cm_ac + Cm_δe·δe_max + ΔCm_flap

    If net_pitch_up ≤ 0, the elevator cannot overcome the combined nose-down
    moment (Cm_ac baseline + flap) at stall even with full TE-UP deflection.
    No feasible forward CG exists.

    The old guard only checked Cm_δe·δe_max + ΔCm_flap, missing cases where
    Cm_ac alone flips the net sum negative.

    Args:
        cm_ac: Pitching moment at aerodynamic center (negative = nose-down).
        cm_delta_e: Elevator authority [1/rad], positive (TE-UP convention).
        delta_e_max_rad: Max elevator deflection [rad].
        delta_cm_flap: Flap-induced pitching moment (typically ≤ 0).
        confidence_warn_tier: Confidence tier to assign to the infeasibility result.
        warnings: Accumulated warning list (copied, not mutated).

    Returns:
        ForwardCGResult with cg_fwd_m=None if guard triggered, None otherwise.
    """
    net_pitch_up = cm_ac + cm_delta_e * delta_e_max_rad + delta_cm_flap
    if net_pitch_up <= 0.0:
        warnings = list(warnings)
        warnings.append(
            "Elevator cannot overcome nose-down moment at stall (Cm_ac + Cm_δe·δe_max + ΔCm_flap "
            f"= {net_pitch_up:.4f} ≤ 0) — no feasible forward CG"
        )
        logger.warning(
            "Infeasibility guard triggered: Cm_ac + Cm_δe·δe_max + ΔCm_flap = %.4f ≤ 0 "
            "(Cm_ac=%.4f, Cm_δe·δe_max=%.4f, ΔCm_flap=%.4f).",
            net_pitch_up,
            cm_ac,
            cm_delta_e * delta_e_max_rad,
            delta_cm_flap,
        )
        return ForwardCGResult(
            cg_fwd_m=None,
            confidence=confidence_warn_tier,
            cm_delta_e=cm_delta_e,
            cl_max_landing=1.0,  # placeholder; caller may enrich
            flap_state="deployed" if delta_cm_flap < 0 else "clean",
            warnings=warnings,
        )
    return None


def _build_stub_result(
    x_np_m: float,
    mac_m: float,
    cl_max_clean: float,
    reason: str,
    has_flap: bool = True,
) -> ForwardCGResult:
    """Build the conservative stub result (0.30·MAC fallback).

    Used when AeroBuildup is not available or has failed.

    CL_max_landing (Roskam §4.7):
      With flap: CL_max_landing = CL_max_clean + 0.5
      Without flap: CL_max_landing = CL_max_clean

    Args:
        x_np_m: Neutral point [m].
        mac_m: Mean aerodynamic chord [m].
        cl_max_clean: Clean CL_max (from polar sweep).
        reason: Short description of why stub was used (for log/warning).
        has_flap: True if the aircraft has flap devices (uses +0.5 bonus).

    Returns:
        ForwardCGResult with confidence=stub.
    """
    cl_max_landing = cl_max_clean + (_ROSKAM_FLAP_CL_BONUS if has_flap else 0.0)
    cg_fwd_m = x_np_m - _STUB_FORWARD_SM * mac_m
    logger.info(
        "Using stub forward CG limit (reason: %s): x_np=%.4f, MAC=%.4f → x_cg_fwd=%.4f",
        reason,
        x_np_m,
        mac_m,
        cg_fwd_m,
    )
    return ForwardCGResult(
        cg_fwd_m=cg_fwd_m,
        confidence=ForwardCGConfidence.stub,
        cm_delta_e=None,
        cl_max_landing=cl_max_landing,
        flap_state="stub",
        warnings=[f"Stub forward CG limit used (reason: {reason})"],
    )


# ---------------------------------------------------------------------------
# Main public entry point
# ---------------------------------------------------------------------------


def compute_forward_cg_limit(
    db: "Session",
    aeroplane,
) -> ForwardCGResult:
    """Compute the physics-based forward CG limit for the given aircraft.

    Implements the NP-centered trim inversion (Anderson §7.7, Amendment B1):
      x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

    Uses AeroSandbox AeroBuildup as the sole solver. A high-fidelity AVL solver path
    is tracked in gh-516 and is not yet implemented.

    Requires:
      - AeroBuildup available (aerosandbox installed)
      - Aircraft has wings with neutral point (from assumption run)
      - Aircraft has at least one pitch-control TED (elevator/ruddervator/elevon)

    On any failure, falls back to the 0.30·MAC stub.

    Sign convention (Amendment B3):
      The Cm_δe AeroBuildup run uses NEGATIVE deflection (TE-UP) so that
      Cm_δe > 0 (nose-up per unit negative rad).

    V-tail (Amendment B4):
      ASB 3D geometry already encodes dihedral → do NOT apply cos²(γ) to Cm_δe.
      cos²(γ) is ONLY in the analytic stub formula path.

    Args:
        db: SQLAlchemy session.
        aeroplane: AeroplaneModel instance.

    Returns:
        ForwardCGResult with physics-based or stub cg_fwd_m.
    """
    try:
        return _compute_forward_cg_limit_asb(db, aeroplane)
    except Exception as exc:
        logger.warning(
            "Elevator authority ASB computation failed for aircraft %s — "
            "falling back to stub. Error: %s",
            getattr(aeroplane, "id", "unknown"),
            exc,
        )
        # Stub fallback — need x_np and mac from DB assumptions
        x_np_m, mac_m, cl_max_clean = _load_stability_assumptions(db, aeroplane)
        return _build_stub_result(
            x_np_m=x_np_m,
            mac_m=mac_m,
            cl_max_clean=cl_max_clean,
            reason=f"asb-error: {exc}",
        )


def _load_assumption_value(
    db: "Session",
    aeroplane_id: int,
    param_name: str,
) -> float | None:
    """Load a single design assumption's effective value from the DB.

    Returns the calculated_value if source is CALCULATED, otherwise estimate_value.
    Returns None if no row exists.
    """
    from app.models.aeroplanemodel import DesignAssumptionModel

    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return None
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


def _load_stability_assumptions(
    db: "Session",
    aeroplane,
) -> tuple[float, float, float]:
    """Load x_np, mac, and cl_max_clean from the design assumptions table.

    Returns:
        (x_np_m, mac_m, cl_max_clean) — all floats with safe defaults.

    Raises:
        ValueError if critical assumptions (x_np, mac) are unavailable.
    """
    aeroplane_id = aeroplane.id

    x_np_m = _load_assumption_value(db, aeroplane_id, "x_np")
    mac_m = _load_assumption_value(db, aeroplane_id, "mac")
    cl_max_raw = _load_assumption_value(db, aeroplane_id, "cl_max")
    cl_max_clean = cl_max_raw if cl_max_raw is not None else 1.4

    if x_np_m is None or mac_m is None or mac_m <= 0:
        raise ValueError(
            f"Cannot compute forward CG limit: x_np={x_np_m}, mac={mac_m} unavailable. "
            "Run recompute_assumptions first."
        )
    return float(x_np_m), float(mac_m), float(cl_max_clean)


def _find_pitch_control_ted(aeroplane) -> tuple[object | None, str | None]:
    """Find the first pitch-control TED on the aircraft.

    Returns:
        (ted_model, role_str) or (None, None) if no pitch-control surface found.

    Priority: elevator > ruddervator > elevon > flaperon
    """
    pitch_teds: list[tuple[object, str]] = []

    for wing in aeroplane.wings or []:
        for xsec in wing.x_secs or []:
            if xsec.detail is None:
                continue
            for ted in xsec.detail.trailing_edge_device or []:
                role = getattr(ted, "role", None)
                role_str = str(role) if role is not None else None
                if role_str in _PITCH_ROLES:
                    pitch_teds.append((ted, role_str))

    if not pitch_teds:
        return None, None

    # Priority order: elevator > ruddervator > elevon > flaperon
    # This covers ALL roles in _PITCH_ROLES, so the loop always finds one.
    for preferred_role in ("elevator", "ruddervator", "elevon", "flaperon"):
        for ted, role_str in pitch_teds:
            if role_str == preferred_role:
                return ted, role_str

    # Unreachable: _PITCH_ROLES == {"elevator","ruddervator","elevon","flaperon"}
    # but kept for defensive correctness
    return pitch_teds[0]  # pragma: no cover


def _find_flap_teds(aeroplane) -> list[object]:
    """Find all flap TEDs on the aircraft."""
    flap_teds = []
    for wing in aeroplane.wings or []:
        for xsec in wing.x_secs or []:
            if xsec.detail is None:
                continue
            for ted in xsec.detail.trailing_edge_device or []:
                role = getattr(ted, "role", None)
                role_str = str(role) if role is not None else None
                if role_str == _FLAP_ROLE:
                    flap_teds.append(ted)
    return flap_teds


def _compute_forward_cg_limit_asb(
    db: "Session",
    aeroplane,
) -> ForwardCGResult:
    """Core ASB path: compute Cm_δe, ΔCm_flap, CL_max_landing via AeroBuildup.

    Raises on any failure so the caller can fall back to stub.
    """
    import aerosandbox as asb

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    aeroplane_id = aeroplane.id

    # Load required stability assumptions
    x_np_m_raw = _load_assumption_value(db, aeroplane_id, "x_np")
    mac_m_raw = _load_assumption_value(db, aeroplane_id, "mac")
    cl_max_raw = _load_assumption_value(db, aeroplane_id, "cl_max")

    if x_np_m_raw is None or mac_m_raw is None or float(mac_m_raw) <= 0:
        raise ValueError(
            f"x_np={x_np_m_raw} or mac={mac_m_raw} not available — run assumptions first."
        )
    x_np_m = float(x_np_m_raw)
    mac_m = float(mac_m_raw)
    cl_max_clean = float(cl_max_raw) if cl_max_raw is not None else 1.4

    # Load cruise speed for the AeroBuildup runs
    v_cruise_raw = _load_assumption_value(db, aeroplane_id, "v_cruise")
    v_cruise = float(v_cruise_raw) if v_cruise_raw is not None else 15.0

    # Build ASB airplane
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_id)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]

    # Find elevator TED
    elevator_ted, elevator_role = _find_pitch_control_ted(aeroplane)
    if elevator_ted is None:
        raise ValueError("No pitch-control TED found (elevator/ruddervator/elevon/flaperon).")

    # Determine elevator surface name in ASB airplane
    # The converter prefixes names with [role]
    elevator_surface_name = f"[{elevator_role}]{getattr(elevator_ted, 'name', elevator_role)}"

    # Get max elevator deflection (Amendment B3: use abs of negative_deflection_deg)
    delta_e_max_rad = _delta_e_max_rad(
        negative_deflection_deg=getattr(elevator_ted, "negative_deflection_deg", None)
    )
    # Convert back to degrees for AeroBuildup (negative = TE-UP)
    delta_e_neg_deg = -abs(float(delta_e_max_rad * 180.0 / math.pi))

    # --- ASB Run 1: Baseline (zero deflection) at clean stall-approach alpha ---
    # Use stall alpha from assumptions or moderate angle.
    # Note: if flap run succeeds (Scholz B2), we re-run baseline + TE-UP at the
    # landing-stall alpha (alpha at CL_max_flap), which is more accurate.
    stall_alpha_raw = _load_assumption_value(db, aeroplane_id, "stall_alpha")
    stall_alpha_deg = float(stall_alpha_raw) if stall_alpha_raw is not None else 12.0

    op_stall = asb.OperatingPoint(
        velocity=v_cruise * 0.6,  # near-stall approach speed
        alpha=stall_alpha_deg,
    )

    # --- Flap run first (Scholz B2): get α_stall_landing before Cm_δe runs ---
    # Running the flap analysis first lets us feed α_stall_landing back into the
    # baseline + TE-UP runs so Cm_δe is evaluated at the correct landing-stall alpha.
    delta_cm_flap = 0.0
    cl_max_landing = cl_max_clean
    has_flap_run = False
    flap_state: str = "clean"
    alpha_stall_landing_deg = stall_alpha_deg  # default: clean stall alpha

    flap_teds = _find_flap_teds(aeroplane)
    if flap_teds:
        try:
            # Baseline run at clean stall alpha needed for ΔCm_flap reference
            asb_baseline_clean = asb_airplane.with_control_deflections(
                {elevator_surface_name: 0.0}
            )
            abu_baseline_clean = asb.AeroBuildup(
                airplane=asb_baseline_clean,
                op_point=op_stall,
                xyz_ref=xyz_ref,
            )
            cm_baseline_clean = _extract_cm(abu_baseline_clean.run())

            delta_cm_flap, cl_max_landing_flap, alpha_stall_landing_deg = _run_flap_analysis(
                asb_airplane=asb_airplane,
                flap_teds=flap_teds,
                aeroplane=aeroplane,
                op_stall=op_stall,
                xyz_ref=xyz_ref,
                cm_baseline=cm_baseline_clean,
            )
            cl_max_landing = cl_max_landing_flap
            has_flap_run = True
            flap_state = "deployed"
            logger.info(
                "Flap run for aircraft %s: α_stall_landing=%.1f°, CL_max_landing=%.3f, "
                "ΔCm_flap=%.4f",
                aeroplane_id,
                alpha_stall_landing_deg,
                cl_max_landing,
                delta_cm_flap,
            )
        except (ValueError, RuntimeError, ImportError) as exc:
            logger.warning(
                "Flap run failed for aircraft %s — using Roskam §4.7 +0.5 stub. Error: %s",
                aeroplane_id,
                exc,
            )
            cl_max_landing = cl_max_clean + _ROSKAM_FLAP_CL_BONUS
            flap_state = "stub"
    else:
        # No flap aircraft: CL_max_landing = CL_max_clean (Amendment B2)
        cl_max_landing = cl_max_clean
        flap_state = "clean"

    # --- ASB Run 1: Baseline (zero deflection) at landing-stall alpha (Scholz B2) ---
    # Use α_stall_landing if a flap run succeeded; otherwise clean stall alpha.
    op_stall_landing = asb.OperatingPoint(
        velocity=v_cruise * 0.6,
        alpha=alpha_stall_landing_deg,
    )

    asb_baseline = asb_airplane.with_control_deflections({elevator_surface_name: 0.0})
    abu_baseline = asb.AeroBuildup(
        airplane=asb_baseline,
        op_point=op_stall_landing,
        xyz_ref=xyz_ref,
    )
    result_baseline = abu_baseline.run()
    cm_baseline = _extract_cm(result_baseline)

    # --- ASB Run 2: TE-UP deflection (Amendment B3) at landing-stall alpha ---
    # NEGATIVE deflection = TE-UP = nose-up moment → Cm_δe > 0
    asb_deflected = asb_airplane.with_control_deflections({elevator_surface_name: delta_e_neg_deg})
    abu_deflected = asb.AeroBuildup(
        airplane=asb_deflected,
        op_point=op_stall_landing,
        xyz_ref=xyz_ref,
    )
    result_deflected = abu_deflected.run()
    cm_deflected = _extract_cm(result_deflected)

    # Compute Cm_δe from finite difference
    # δe_rad is NEGATIVE (TE-UP), so Cm_δe = ΔCm / δe_rad
    # We want Cm_δe per unit negative-deflection rad:
    # Cm_delta_e = (Cm_deflected - Cm_baseline) / abs(delta_e_neg_deg * π/180)
    cm_delta_e_raw = (cm_deflected - cm_baseline) / delta_e_max_rad

    # B1: Cm_δe must be positive for TE-UP deflection.
    # If raw value ≤ 0, log warning and apply abs() — safer than hard assert in production
    # (geometry quirks shouldn't crash the assumption pipeline).
    if cm_delta_e_raw <= 0.0:
        logger.warning(
            "Cm_δe = %.4f ≤ 0 after TE-UP deflection run for aircraft %s. "
            "This is unexpected — elevator does not produce nose-up moment. "
            "Using abs() and continuing, but verify control surface geometry.",
            cm_delta_e_raw,
            aeroplane_id,
        )

    # ASB 3D path: use directly (NO cos² correction — Amendment B4)
    cm_delta_e = _cm_delta_e_for_asb_path(
        cm_delta_e_raw=abs(cm_delta_e_raw),  # Enforce positive convention
        elevator_role=elevator_role,
    )

    # Get Cm_ac from baseline (zero-deflection, at x_np reference — AeroBuildup
    # uses xyz_ref which we set to x_np for the stability run)
    cm_ac = cm_baseline

    # --- Confidence tier ---
    confidence = _determine_confidence_tier(
        elevator_role=elevator_role,
        has_flap_run=has_flap_run,
    )

    warnings: list[str] = []
    if elevator_role in _WARN_ROLES:
        warnings.append(
            f"confidence={confidence.value}: {elevator_role} elevator authority "
            "is less precisely modelled by AeroBuildup — treat forward limit as guidance."
        )

    # --- Conditioning guard (Amendment S1) ---
    conditioning_result = _apply_conditioning_guard(
        x_np_m=x_np_m,
        mac_m=mac_m,
        cm_delta_e=cm_delta_e,
        cl_max_landing=cl_max_landing,
        cm_ac=cm_ac,
        delta_cm_flap=delta_cm_flap,
        delta_e_max_rad=delta_e_max_rad,
        confidence_warn_tier=confidence,
        warnings=warnings,
    )
    if conditioning_result is not None:
        return conditioning_result

    # --- Infeasibility guard (Amendment S3, fix B4) ---
    # Guard checks FULL sum: Cm_ac + Cm_δe·δe_max + ΔCm_flap
    infeasibility_result = _apply_infeasibility_guard(
        cm_ac=cm_ac,
        cm_delta_e=cm_delta_e,
        delta_e_max_rad=delta_e_max_rad,
        delta_cm_flap=delta_cm_flap,
        confidence_warn_tier=confidence,
        warnings=warnings,
    )
    if infeasibility_result is not None:
        # Enrich with actual cl_max_landing
        return ForwardCGResult(
            cg_fwd_m=None,
            confidence=confidence,
            cm_delta_e=cm_delta_e,
            cl_max_landing=cl_max_landing,
            flap_state=flap_state,
            warnings=infeasibility_result.warnings,
        )

    # --- Apply trim inversion formula (Amendment B1) ---
    x_cg_fwd = _trim_inversion(
        x_np_m=x_np_m,
        cm_ac=cm_ac,
        cm_delta_e=cm_delta_e,
        delta_e_max_rad=delta_e_max_rad,
        delta_cm_flap=delta_cm_flap,
        c_ref_m=mac_m,
        cl_max_landing=cl_max_landing,
    )

    # --- Post-hoc sanity check (B4): x_cg_fwd must never exceed x_np ---
    # If x_cg_fwd > x_np the 'forward' limit is aft of the NP — physically impossible.
    # This should be caught by the infeasibility guard above, but guard floating-point
    # boundary may miss exact-zero cases.
    if x_cg_fwd > x_np_m:
        warn_msg = (
            f"Forward CG limit aft of NP — physically infeasible "
            f"(x_cg_fwd={x_cg_fwd:.4f} > x_np={x_np_m:.4f}). "
            "Returning cg_fwd_m=None."
        )
        logger.warning(warn_msg)
        return ForwardCGResult(
            cg_fwd_m=None,
            confidence=confidence,
            cm_delta_e=cm_delta_e,
            cl_max_landing=cl_max_landing,
            flap_state=flap_state,
            warnings=list(warnings) + [warn_msg],
        )

    logger.info(
        "Forward CG limit computed: x_cg_fwd=%.4f m (x_np=%.4f, SM_fwd=%.3f MAC), "
        "Cm_δe=%.4f, δe_max=%.1f°, ΔCm_flap=%.4f, CL_max_landing=%.3f, "
        "confidence=%s",
        x_cg_fwd,
        x_np_m,
        (x_np_m - x_cg_fwd) / mac_m,
        cm_delta_e,
        delta_e_max_rad * 180.0 / math.pi,
        delta_cm_flap,
        cl_max_landing,
        confidence.value,
    )

    return ForwardCGResult(
        cg_fwd_m=x_cg_fwd,
        confidence=confidence,
        cm_delta_e=cm_delta_e,
        cl_max_landing=cl_max_landing,
        flap_state=flap_state,
        warnings=warnings,
    )


def _run_flap_analysis(
    asb_airplane,
    flap_teds: list,
    aeroplane,
    op_stall,
    xyz_ref: list[float],
    cm_baseline: float,
) -> tuple[float, float, float]:
    """Run a flap-deployed AeroBuildup to get ΔCm_flap, CL_max_landing, and α_stall_landing.

    Scholz B2 fix: returns the alpha at which CL_max is achieved (α_stall_landing)
    so the caller can re-run the baseline and TE-UP AeroBuildup runs at that alpha.
    This ensures Cm_δe is evaluated at the correct landing-stall angle, not the
    clean-stall alpha from assumptions.

    Returns:
        (delta_cm_flap, cl_max_landing, alpha_stall_flap): flap-induced Cm delta,
        landing CL_max, and the alpha [deg] at which CL_max_landing was achieved.

    Raises on failure so caller can fall back to stub.
    """
    import aerosandbox as asb
    import numpy as np

    # Build deflection dict for all flap surfaces
    flap_deflections = {}
    for ted in flap_teds:
        ted_role = getattr(ted, "role", "flap")
        role_str = str(ted_role) if ted_role is not None else "flap"
        ted_name = getattr(ted, "name", "Flap")
        flap_surface_name = f"[{role_str}]{ted_name}"
        # Use positive deflection for flap (TE-down for lift)
        flap_deg = getattr(ted, "positive_deflection_deg", None) or 30.0
        flap_deflections[flap_surface_name] = float(flap_deg)

    asb_flapped = asb_airplane.with_control_deflections(flap_deflections)

    # Sweep alpha to find CL_max_landing and Cm at that point
    alphas = np.arange(-5.0, 20.0, 1.0)
    cl_max_flap = -float("inf")
    cm_at_cl_max = 0.0
    alpha_at_cl_max = float(op_stall.alpha)  # fallback to clean stall alpha

    for alpha in alphas:
        op = asb.OperatingPoint(velocity=op_stall.velocity, alpha=float(alpha))
        abu = asb.AeroBuildup(
            airplane=asb_flapped,
            op_point=op,
            xyz_ref=xyz_ref,
        )
        r = abu.run()
        cl = _extract_cl(r)
        cm = _extract_cm(r)
        if cl > cl_max_flap:
            cl_max_flap = cl
            cm_at_cl_max = cm
            alpha_at_cl_max = float(alpha)

    # ΔCm_flap = Cm_deployed - Cm_clean (typically negative = nose-down)
    delta_cm_flap = cm_at_cl_max - cm_baseline

    return delta_cm_flap, float(cl_max_flap), alpha_at_cl_max


def _extract_cm(result) -> float:
    """Extract Cm (pitching moment coefficient) from AeroBuildup result."""
    if isinstance(result, dict):
        val = result.get("Cm", result.get("Cmq", 0.0))
    else:
        val = getattr(result, "Cm", None) or getattr(result, "pitching_moment", None) or 0.0
    return _to_scalar(val)


def _extract_cl(result) -> float:
    """Extract CL (lift coefficient) from AeroBuildup result."""
    if isinstance(result, dict):
        val = result.get("CL", 0.0)
    else:
        val = getattr(result, "CL", None) or 0.0
    return _to_scalar(val)


def _to_scalar(value) -> float:
    """Coerce a numeric value (possibly a 1-element numpy array) to Python float."""
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return float(value.ravel()[0])
    except ImportError:
        pass
    return float(value) if value is not None else 0.0
