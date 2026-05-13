"""SM sizing constraint service — gh-494 (Wave 4, Scholz Step 9 ↔ Step 11 iteration).

Two analytical sensitivity levers:
  1. wing_shift: move the main wing fore/aft → changes x_NP via Λ_VH downwash factor
  2. htail_scale: chord-scale the horizontal tail → changes S_H contribution to x_NP

Formulas (Anderson §7.6 Eq. 7.41, spec-gate A1):
  SM = (x_NP - x_CG) / MAC

  ∂SM/∂x_wing ≈ (1 - α_VH) / MAC
    where α_VH = (a_t/a)·(1 - dε/dα)·(S_H/S_w)·(1/c_ref)  [dimensionless, ~0.05–0.15]
    (a_t/a) ≈ 1.0  (assumption; split into separate wings TODO)
    (1 - dε/dα) = 0.6  (Roskam Vol I, §8.1; typical for conventional tail config)
    c_ref = MAC

  ∂SM/∂S_H = (a_t/a)·(1 - dε/dα)·l_H / (S_w·MAC)

Scope (spec-gate A4): aft-CG only.
  TODO(gh-500): after gh-500 merge → add fwd-CG trim-drag suggestion using
  Cm_δe, δe_max, ΔCm_flap.  Binding limit becomes min(aft_violation, fwd_violation).

Mass-coupling warning (spec-gate A5):
  Wing-mass ≈ 30% MTOW → Δx_wing = 0.05·MAC shifts CG by ~0.015·MAC ≈ 1 SM unit.
  MVP: warn in narrative; mass-coupling factor NOT included in formula.

Apply operations (spec-gate A3):
  wing_shift: batch update WingXSecModel.xyz_le[0] for all xsecs of the main wing.
  htail_scale: chord-scale each htail xsec chord by (1 + delta_pct).
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SM_UNSTABLE_LIMIT = 0.02     # below → ERROR, block_save
_SM_HEAVY_NOSE_WARN = 0.20    # above → overshoot suggestion

# Roskam Vol I §8.1: downwash factor (1 - dε/dα) for conventional tail
_DE_DA_FACTOR = 0.6   # (1 - dε/dα), typical for conventional aft tail

# Forward stability stub limit: SM = 0.30 (see loading_scenario_service.py)
_SM_FORWARD_CLIP_LIMIT = 0.30

# Maximum reasonable wing shift (5× MAC per iteration, safety clip)
_MAX_X_WING_SHIFT_MAC = 5.0

# Mass-coupling warning (spec-gate A5)
_MASS_COUPLING_WARNING = (
    "Suggestion ignoriert Wingbox-Mass-Shift; ggf. nach Apply iterieren. "
    "(Wing mass ~30% MTOW — a Δx_wing of 0.05·MAC shifts CG by ~0.015·MAC ≈ 1 SM unit.)"
)

# Negative S_H warning (overshoot path, spec-gate A6)
_NEGATIVE_SH_WARNING = (
    "Shrinking HS reduces yaw damping — verify Dutch-roll mode after Apply."
)


# ---------------------------------------------------------------------------
# Sensitivity helpers (public for unit-test access)
# ---------------------------------------------------------------------------

def _alpha_vh(ctx: dict) -> float:
    """Compute the tail efficiency factor α_VH (dimensionless, ~0.05–0.15).

    α_VH = (a_t/a)·(1 - dε/dα)·(S_H/S_w)·(1/c_ref)

    (a_t/a) is approximated as 1.0 (both wings in same freestream; a proper
    split requires separate 2π-per-rad estimates for wing vs tail — follow-up).
    """
    s_h_m2: float | None = ctx.get("s_h_m2")
    s_ref_m2: float | None = ctx.get("s_ref_m2")
    mac_m: float | None = ctx.get("mac_m")
    if not s_h_m2 or not s_ref_m2 or not mac_m or mac_m <= 0 or s_ref_m2 <= 0:
        return 0.10  # fallback typical value
    at_over_a = 1.0  # TODO: split tail/wing CL_α when separable
    a_vh = at_over_a * _DE_DA_FACTOR * (s_h_m2 / s_ref_m2) / mac_m
    # Clamp to physically meaningful range
    return max(0.02, min(0.30, a_vh))


def _dsm_dx_wing(ctx: dict) -> float:
    """Analytic ∂SM/∂x_wing [1/m].

    ∂SM/∂x_wing ≈ (1 - α_VH) / MAC

    Positive: moving the wing aft (larger x) increases x_NP → increases SM.
    """
    mac_m: float = ctx.get("mac_m") or 0.30
    a_vh = _alpha_vh(ctx)
    return (1.0 - a_vh) / mac_m


def _dsm_dsh(ctx: dict) -> float:
    """Analytic ∂SM/∂S_H [1/m²].

    ∂SM/∂S_H = (a_t/a)·(1 - dε/dα)·l_H / (S_w·MAC)

    Positive: increasing S_H increases S_H contribution to x_NP → increases SM.
    """
    mac_m: float = ctx.get("mac_m") or 0.30
    s_ref_m2: float = ctx.get("s_ref_m2") or 0.60
    l_h_m: float | None = ctx.get("l_h_m")
    if not l_h_m or l_h_m <= 0:
        # Fall back: estimate l_H as 2.0 × MAC
        l_h_m = 2.0 * mac_m
    at_over_a = 1.0
    return at_over_a * _DE_DA_FACTOR * l_h_m / (s_ref_m2 * mac_m)


# ---------------------------------------------------------------------------
# Configuration-guard helpers
# ---------------------------------------------------------------------------

def _is_not_applicable(ctx: dict) -> tuple[bool, str]:
    """Return (True, reason) when SM suggestion is not applicable for this config."""
    if ctx.get("is_canard"):
        return True, "Canard configuration — SM sizing not applicable (no aft-tail lever)."
    if ctx.get("is_tailless"):
        return True, "Tailless/flying-wing configuration — SM sizing not applicable."
    if ctx.get("is_boxwing"):
        return True, "Boxwing configuration — SM sizing not applicable (complex NP coupling)."
    if ctx.get("is_tandem"):
        return True, "Tandem-wing configuration — SM sizing not applicable."
    x_np_m = ctx.get("x_np_m")
    if x_np_m is None:
        return True, "Run analysis first to compute x_NP (assumption recompute not yet run)."
    return False, ""


# ---------------------------------------------------------------------------
# Main public service function
# ---------------------------------------------------------------------------

def suggest_corrections(
    ctx: dict,
    target_sm: float = 0.10,
    at_cg: Literal["aft"] = "aft",  # noqa: ARG001  (gh-500 will add fwd)
) -> dict[str, Any]:
    """Suggest geometry changes to hit target_sm for the aft-CG loading.

    Reads from the assumption_computation_context dict (produced by
    recompute_assumptions and enriched by loading-scenario/CG-envelope services).

    Returns a dict with:
      status: "ok" | "suggestion" | "error" | "not_applicable"
      options: list of {lever, delta_value, delta_unit, predicted_sm, narrative}
      block_save: True when SM < _SM_UNSTABLE_LIMIT (error state)
      mass_coupling_warning: str  (always present when wing_shift option is returned)
      message: str  (present for not_applicable / error)
    """
    # --- Guard: configuration not supported --------------------------------
    na, reason = _is_not_applicable(ctx)
    if na:
        return {
            "status": "not_applicable",
            "options": [],
            "message": reason,
            "hint": reason,
        }

    sm_at_aft: float | None = ctx.get("sm_at_aft")
    mac_m: float = ctx.get("mac_m") or 0.30

    # If sm_at_aft not pre-computed in context, derive it
    if sm_at_aft is None:
        x_np_m: float | None = ctx.get("x_np_m")
        cg_aft_m: float | None = ctx.get("cg_aft_m")
        if x_np_m is None or cg_aft_m is None:
            return {
                "status": "not_applicable",
                "options": [],
                "message": "Run analysis first to compute x_NP (assumption recompute not yet run).",
                "hint": "Run analysis first to compute x_NP (assumption recompute not yet run).",
            }
        sm_at_aft = (x_np_m - cg_aft_m) / mac_m

    # --- Edge: ERROR — SM below instability threshold ----------------------
    if sm_at_aft < _SM_UNSTABLE_LIMIT:
        delta_needed = target_sm - sm_at_aft
        dsm_dx = _dsm_dx_wing(ctx)
        dsm_dsh = _dsm_dsh(ctx)
        s_h_m2: float = ctx.get("s_h_m2") or 0.08
        delta_x = delta_needed / dsm_dx
        delta_sh_m2 = delta_needed / dsm_dsh
        delta_pct = delta_sh_m2 / s_h_m2

        return {
            "status": "error",
            "block_save": True,
            "message": (
                f"SM = {sm_at_aft:.3f} at aft CG is BELOW the minimum stability threshold "
                f"({_SM_UNSTABLE_LIMIT:.2f}) — aircraft may be aerodynamically unstable. "
                "Apply one of the suggested corrections before saving."
            ),
            "options": [
                _wing_shift_option(ctx, delta_x, sm_at_aft, target_sm),
                _htail_scale_option(ctx, delta_pct, sm_at_aft, target_sm),
            ],
            "mass_coupling_warning": _MASS_COUPLING_WARNING,
        }

    # --- Edge: OK — SM in [target_sm, 0.20] --------------------------------
    if target_sm <= sm_at_aft <= _SM_HEAVY_NOSE_WARN:
        return {
            "status": "ok",
            "options": [],
            "message": f"SM = {sm_at_aft:.3f} is within target range [{target_sm:.2f}, {_SM_HEAVY_NOSE_WARN:.2f}].",
        }

    # --- Suggestion: SM ≠ target (either too low or heavy-nose overshoot) --
    dsm_dx = _dsm_dx_wing(ctx)
    dsm_dsh = _dsm_dsh(ctx)
    s_h_m2 = ctx.get("s_h_m2") or 0.08

    # Invert: ΔSM = target_sm - sm_at_aft → Δlevers
    delta_needed = target_sm - sm_at_aft
    delta_x = delta_needed / dsm_dx        # metres (negative = move wing fwd)
    delta_sh_m2 = delta_needed / dsm_dsh   # m² (negative = shrink HS)
    delta_pct = delta_sh_m2 / s_h_m2      # fraction (negative = shrink)

    # Clip: wing shift must not violate forward SM stability limit
    # (forward stability fwd limit: SM <= 0.30 → cg_fwd >= x_NP - 0.30*MAC)
    # The clip prevents the suggestion from pushing the wing so far forward
    # that even the FORWARD CG loading exceeds the elevator-authority limit.
    x_np_m = ctx.get("x_np_m") or 0.0
    cg_aft_m = ctx.get("cg_aft_m")
    clip_warning = None
    if cg_aft_m is not None:
        sm_after_shift = sm_at_aft + dsm_dx * delta_x
        if sm_after_shift > _SM_FORWARD_CLIP_LIMIT:
            # Would overshoot forward limit: clip
            delta_x = (_SM_FORWARD_CLIP_LIMIT - sm_at_aft) / dsm_dx
            clip_warning = (
                "Suggestion limited by forward CG stability envelope "
                f"(SM would exceed {_SM_FORWARD_CLIP_LIMIT:.2f})."
            )

    warnings: list[str] = []
    if clip_warning:
        warnings.append(clip_warning)
    if delta_sh_m2 < 0:
        warnings.append(_NEGATIVE_SH_WARNING)

    wing_opt = _wing_shift_option(ctx, delta_x, sm_at_aft, target_sm)
    htail_opt = _htail_scale_option(ctx, delta_pct, sm_at_aft, target_sm)

    return {
        "status": "suggestion",
        "options": [wing_opt, htail_opt],
        "mass_coupling_warning": _MASS_COUPLING_WARNING,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Option builder helpers
# ---------------------------------------------------------------------------

def _wing_shift_option(
    ctx: dict,
    delta_x_m: float,
    sm_at_aft: float,
    target_sm: float,
) -> dict:
    """Build the wing_shift option dict."""
    mac_m: float = ctx.get("mac_m") or 0.30
    dsm_dx = _dsm_dx_wing(ctx)
    predicted_sm = sm_at_aft + dsm_dx * delta_x_m
    delta_mm = round(delta_x_m * 1000.0, 1)
    direction = "forward" if delta_x_m < 0 else "aft"
    narrative = (
        f"Move main wing {abs(delta_mm):.1f} mm {direction} (Δx = {delta_mm:+.1f} mm) "
        f"to reach SM ≈ {target_sm*100:.0f}% at aft CG. "
        f"MAC = {mac_m*1000:.0f} mm. "
        f"{_MASS_COUPLING_WARNING}"
    )
    return {
        "lever": "wing_shift",
        "delta_value": round(delta_x_m, 5),
        "delta_unit": "m",
        "predicted_sm": round(predicted_sm, 4),
        "narrative": narrative,
    }


def _htail_scale_option(
    ctx: dict,
    delta_pct: float,
    sm_at_aft: float,
    target_sm: float,
) -> dict:
    """Build the htail_scale option dict."""
    mac_m: float = ctx.get("mac_m") or 0.30
    s_h_m2: float = ctx.get("s_h_m2") or 0.08
    dsm_dsh = _dsm_dsh(ctx)
    predicted_sm = sm_at_aft + dsm_dsh * delta_pct * s_h_m2
    action = "Enlarge" if delta_pct > 0 else "Shrink"
    narrative = (
        f"{action} horizontal tail chord by {abs(delta_pct)*100:.1f}% "
        f"(Δ = {delta_pct*100:+.1f}%) to reach SM ≈ {target_sm*100:.0f}% at aft CG. "
        f"Chord-scale preserves AR. "
    )
    if delta_pct < 0:
        narrative += _NEGATIVE_SH_WARNING
    return {
        "lever": "htail_scale",
        "delta_value": round(delta_pct, 5),
        "delta_unit": "fraction",  # 0.20 = +20%
        "predicted_sm": round(predicted_sm, 4),
        "narrative": narrative,
    }


# ---------------------------------------------------------------------------
# Apply helpers
# ---------------------------------------------------------------------------

def _find_aeroplane(db: Session, aeroplane_uuid: str):
    """Find AeroplaneModel by UUID string, return None if not found."""
    from app.models.aeroplanemodel import AeroplaneModel
    return (
        db.query(AeroplaneModel)
        .filter(AeroplaneModel.uuid == aeroplane_uuid)
        .first()
    )


def _find_main_wing(aircraft):
    """Find the main wing (largest area, not horizontal/vertical/canard)."""
    wings = aircraft.wings if hasattr(aircraft, "wings") else []
    candidates = []
    for w in wings:
        wname = (w.name or "").lower()
        if (
            "horizontal" not in wname
            and "vertical" not in wname
            and "canard" not in wname
        ):
            candidates.append(w)
    if not candidates:
        return None
    # Pick by approximate area (sum of chord segments × span)
    def _approx_area(wing) -> float:
        xsecs = wing.x_secs if hasattr(wing, "x_secs") else []
        total = 0.0
        for i in range(len(xsecs) - 1):
            c0 = float(xsecs[i].chord or 0.0)
            c1 = float(xsecs[i + 1].chord or 0.0)
            le0 = xsecs[i].xyz_le or [0.0, 0.0, 0.0]
            le1 = xsecs[i + 1].xyz_le or [0.0, 0.0, 0.0]
            dy = abs(float(le1[1]) - float(le0[1]))
            dz = abs(float(le1[2]) - float(le0[2]))
            span_seg = (dy**2 + dz**2) ** 0.5
            total += 0.5 * (c0 + c1) * span_seg
        return total
    return max(candidates, key=_approx_area)


def _find_htail(aircraft):
    """Find the horizontal tail wing model."""
    wings = aircraft.wings if hasattr(aircraft, "wings") else []
    for w in wings:
        wname = (w.name or "").lower()
        if "horizontal" in wname or "htail" in wname:
            return w
    return None


def apply_wing_shift(
    db: Session,
    aeroplane_uuid: str,
    delta_m: float,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply (or preview) a main-wing longitudinal shift.

    Updates xyz_le[0] of ALL WingXSecModel rows belonging to the main wing
    by delta_m (positive = aft). Triggers assumption recompute when dry_run=False.

    Args:
        db: open SQLAlchemy session
        aeroplane_uuid: aeroplane UUID string
        delta_m: shift [m] (positive = aft, negative = forward)
        dry_run: when True, return predicted_sm only; do NOT flush/commit

    Returns:
        dict with dry_run, predicted_sm, (on real apply) new_sm.
    """
    aircraft = _find_aeroplane(db, aeroplane_uuid)
    if aircraft is None:
        raise ValueError(f"Aeroplane {aeroplane_uuid} not found")

    ctx = aircraft.assumption_computation_context or {}

    # Validate configuration
    na, reason = _is_not_applicable(ctx)
    if na:
        raise ValueError(f"not_applicable: {reason}")

    sm_at_aft: float | None = ctx.get("sm_at_aft")
    x_np_m: float | None = ctx.get("x_np_m")
    cg_aft_m: float | None = ctx.get("cg_aft_m")
    mac_m: float = ctx.get("mac_m") or 0.30

    if sm_at_aft is None and x_np_m is not None and cg_aft_m is not None:
        sm_at_aft = (x_np_m - cg_aft_m) / mac_m

    dsm_dx = _dsm_dx_wing(ctx)
    predicted_sm = (sm_at_aft or 0.0) + dsm_dx * delta_m

    if dry_run:
        return {
            "dry_run": True,
            "lever": "wing_shift",
            "delta_value": delta_m,
            "predicted_sm": round(predicted_sm, 4),
        }

    # --- Real apply: update all main-wing xsec xyz_le[0] ---
    main_wing = _find_main_wing(aircraft)
    if main_wing is None:
        raise ValueError("No main wing found on aeroplane")

    for xsec in (main_wing.x_secs or []):
        current_le = list(xsec.xyz_le or [0.0, 0.0, 0.0])
        current_le[0] = float(current_le[0]) + delta_m
        xsec.xyz_le = current_le

    db.flush()

    # Trigger assumption recompute via geometry event
    _trigger_geometry_recompute(aircraft)

    logger.info(
        "apply_wing_shift: aircraft=%s delta_m=%.4f predicted_sm=%.4f xsecs_updated=%d",
        aeroplane_uuid, delta_m, predicted_sm, len(main_wing.x_secs or []),
    )

    return {
        "dry_run": False,
        "lever": "wing_shift",
        "delta_value": delta_m,
        "predicted_sm": round(predicted_sm, 4),
    }


def apply_htail_scale(
    db: Session,
    aeroplane_uuid: str,
    delta_pct: float,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply (or preview) a horizontal tail chord-scale.

    Scales chord of ALL horizontal-tail WingXSecModel rows by (1 + delta_pct).
    Chord-scale preserves AR (no span change). Triggers recompute when dry_run=False.

    Args:
        db: open SQLAlchemy session
        aeroplane_uuid: aeroplane UUID string
        delta_pct: fractional chord change (0.20 = +20%, -0.15 = -15%)
        dry_run: when True, return predicted_sm only; do NOT flush/commit

    Returns:
        dict with dry_run, predicted_sm, (on real apply) new_sm.
    """
    aircraft = _find_aeroplane(db, aeroplane_uuid)
    if aircraft is None:
        raise ValueError(f"Aeroplane {aeroplane_uuid} not found")

    ctx = aircraft.assumption_computation_context or {}

    na, reason = _is_not_applicable(ctx)
    if na:
        raise ValueError(f"not_applicable: {reason}")

    sm_at_aft: float | None = ctx.get("sm_at_aft")
    x_np_m: float | None = ctx.get("x_np_m")
    cg_aft_m: float | None = ctx.get("cg_aft_m")
    mac_m: float = ctx.get("mac_m") or 0.30
    s_h_m2: float = ctx.get("s_h_m2") or 0.08

    if sm_at_aft is None and x_np_m is not None and cg_aft_m is not None:
        sm_at_aft = (x_np_m - cg_aft_m) / mac_m

    dsm_dsh = _dsm_dsh(ctx)
    delta_sh_m2 = delta_pct * s_h_m2
    predicted_sm = (sm_at_aft or 0.0) + dsm_dsh * delta_sh_m2

    if dry_run:
        return {
            "dry_run": True,
            "lever": "htail_scale",
            "delta_value": delta_pct,
            "predicted_sm": round(predicted_sm, 4),
        }

    # --- Real apply: chord-scale all htail xsecs ---
    htail = _find_htail(aircraft)
    if htail is None:
        raise ValueError("No horizontal tail found on aeroplane")

    scale = 1.0 + delta_pct
    for xsec in (htail.x_secs or []):
        xsec.chord = float(xsec.chord or 0.0) * scale

    db.flush()

    _trigger_geometry_recompute(aircraft)

    logger.info(
        "apply_htail_scale: aircraft=%s delta_pct=%.4f predicted_sm=%.4f xsecs_updated=%d",
        aeroplane_uuid, delta_pct, predicted_sm, len(htail.x_secs or []),
    )

    return {
        "dry_run": False,
        "lever": "htail_scale",
        "delta_value": delta_pct,
        "predicted_sm": round(predicted_sm, 4),
    }


# ---------------------------------------------------------------------------
# Recompute trigger
# ---------------------------------------------------------------------------

def _trigger_geometry_recompute(aircraft) -> None:
    """Schedule a background assumption recompute by publishing GeometryChanged.

    The event bus handler (see invalidation_service.py) will pick this up and
    call job_tracker.schedule_recompute_assumptions(aeroplane_id).
    """
    try:
        from app.core.events import GeometryChanged, event_bus
        event_bus.publish(GeometryChanged(
            aeroplane_id=aircraft.id,
            source_model="WingXSecModel",  # geometry of wing changed
        ))
    except Exception:
        logger.warning(
            "Could not publish GeometryChanged event for aircraft %d", aircraft.id, exc_info=True
        )
