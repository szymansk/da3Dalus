"""Tail volume coefficient sizing service — gh-491.

Computes horizontal/vertical tail volume coefficients:
    V_H = S_H · l_H / (S_w · c_ref)     (Raymer 6e Eq. 6.27)
    V_V = S_V · l_V / (S_w · b_ref)     (Raymer 6e Eq. 6.28)

Two l_H definitions:
    l_h_m               — wing-AC → tail-AC   (drives recommendation, CG-independent)
    l_h_eff_from_aft_cg_m — aft-CG → tail-AC  (display-only, for SM cross-check)

Sources:
    Roskam Vol II §8.2 / Table 8.13
    Raymer 6e §6.4 Eq. 6.27/6.28
    Lennon "R/C Model Aircraft Design" Ch. 5
    Thomas "Fundamentals of Sailplane Design" Ch. 7
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical validity guards
# ---------------------------------------------------------------------------

V_H_PHYSICAL_MIN = 0.20
V_H_PHYSICAL_MAX = 1.20
V_V_PHYSICAL_MIN = 0.01
V_V_PHYSICAL_MAX = 0.12

# ---------------------------------------------------------------------------
# Target ranges by aircraft class
# (V_H_min, V_H_max, V_V_min, V_V_max, v_h_citation, v_v_citation)
# ---------------------------------------------------------------------------

AIRCRAFT_CLASS_TARGETS: dict[str, dict] = {
    "rc_trainer": {
        "v_h_range": (0.55, 0.70),
        "v_v_range": (0.040, 0.050),
        "v_h_citation": "Lennon Ch.5",
        "v_v_citation": "Lennon Ch.5",
    },
    "rc_aerobatic": {
        "v_h_range": (0.35, 0.55),   # deliberately lower — snappy pitch response
        "v_v_range": (0.025, 0.040),
        "v_h_citation": "Lennon Ch.5",
        "v_v_citation": "Lennon Ch.5",
    },
    "rc_combust": {
        "v_h_range": (0.45, 0.65),
        "v_v_range": (0.030, 0.045),
        "v_h_citation": "Roskam Vol II Table 8.13",
        "v_v_citation": "Roskam Vol II Table 8.13",
    },
    "rc_pylon_3d": {
        "v_h_range": (0.30, 0.45),
        "v_v_range": (0.025, 0.035),
        "v_h_citation": "Lennon, pylon-race convention",
        "v_v_citation": "Lennon",
    },
    "uav_survey": {
        "v_h_range": (0.50, 0.70),
        "v_v_range": (0.035, 0.060),
        "v_h_citation": "Roskam Vol II Table 8.13",
        "v_v_citation": "Roskam Vol II Table 8.13",
    },
    "glider": {
        "v_h_range": (0.40, 0.55),
        "v_v_range": (0.020, 0.030),
        "v_h_citation": "Thomas Ch.7",
        "v_v_citation": "Thomas Ch.7",
    },
    "boxwing": {
        # boxwing has different empennage philosophy; use generic GA-trainer range
        "v_h_range": (0.55, 0.70),
        "v_v_range": (0.035, 0.050),
        "v_h_citation": "Roskam Vol II Table 8.13",
        "v_v_citation": "Roskam Vol II Table 8.13",
    },
}

_DEFAULT_TARGETS = AIRCRAFT_CLASS_TARGETS["rc_trainer"]

# Single-value classification literal
_Classification = str   # "below_range" | "in_range" | "above_range" | "out_of_physical_range" | "not_applicable"


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class TailVolumeResult:
    """All tail-volume sizing outputs."""

    # Current computed values
    v_h_current: float | None = None
    v_v_current: float | None = None

    # Arm lengths (metres)
    l_h_m: float | None = None                   # wing-AC → tail-AC (recommendation driver)
    l_h_eff_from_aft_cg_m: float | None = None   # aft-CG → tail-AC (display-only)

    # Recommended surfaces (mm² — consistent with frontend wing units)
    s_h_recommended_mm2: float | None = None
    s_v_recommended_mm2: float | None = None

    # Top-level classification (not_applicable if N/A, else best of H+V)
    classification: _Classification = "not_applicable"

    # Per-surface classifications
    classification_h: _Classification = "not_applicable"
    classification_v: _Classification = "not_applicable"

    # Aircraft class used for targets
    aircraft_class_used: str = "rc_trainer"

    # Whether x_NP was available (affects l_H reference)
    cg_aware: bool = False

    # Target range for UI display
    v_h_target_range: tuple[float, float] | None = None
    v_v_target_range: tuple[float, float] | None = None
    v_h_citation: str = ""
    v_v_citation: str = ""

    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_tail_volumes(ctx: dict) -> TailVolumeResult:
    """Compute tail volume coefficients from the assumption context dict.

    The *ctx* dict must supply:
        mac_m, s_ref_m2, b_ref_m      — main wing reference values
        x_wing_ac_m                    — wing AC (25 % MAC from root LE)
        x_np_m (optional)             — neutral point; if None → cg_aware=False
        cg_aft_m (optional)           — aft CG for display-only l_h_eff
        s_h_m2, x_htail_le_m, htail_mac_m  — horizontal tail geometry
        s_v_m2, x_vtail_le_m, vtail_mac_m  — vertical tail geometry
        aircraft_class                 — class string for target lookup
        is_canard, is_tailless, is_v_tail  — configuration flags

    Returns a TailVolumeResult.  classification == "not_applicable" when
    the sizing cannot be performed (canard, tailless, negative l_H, etc.).
    """
    result = TailVolumeResult()

    # --- Configuration guards -------------------------------------------------
    if ctx.get("is_canard") or ctx.get("is_tailless") or ctx.get("is_v_tail"):
        result.classification = "not_applicable"
        return result

    # --- Fetch reference values -----------------------------------------------
    mac_m: float | None = ctx.get("mac_m")
    s_ref_m2: float | None = ctx.get("s_ref_m2")
    b_ref_m: float | None = ctx.get("b_ref_m")

    if not mac_m or not s_ref_m2 or not b_ref_m:
        result.classification = "not_applicable"
        result.warnings.append("Missing main-wing reference values (mac_m / s_ref_m2 / b_ref_m)")
        return result

    x_wing_ac_m: float | None = ctx.get("x_wing_ac_m")
    if x_wing_ac_m is None:
        # Fallback: estimate from first xsec leading edge = 0, AC at 25% MAC
        x_wing_ac_m = 0.25 * mac_m

    x_np_m: float | None = ctx.get("x_np_m")
    cg_aft_m: float | None = ctx.get("cg_aft_m")

    result.cg_aware = x_np_m is not None

    # --- Horizontal tail geometry ---------------------------------------------
    s_h_m2: float | None = ctx.get("s_h_m2")
    x_htail_le_m: float | None = ctx.get("x_htail_le_m")
    htail_mac_m: float | None = ctx.get("htail_mac_m")

    if s_h_m2 is None or x_htail_le_m is None or htail_mac_m is None:
        result.classification = "not_applicable"
        result.warnings.append("Missing horizontal tail geometry (s_h_m2 / x_htail_le_m / htail_mac_m)")
        return result

    # Tail AC = leading-edge X + 25 % tail MAC (Roskam Vol II §8.2.1)
    x_htail_ac_m = x_htail_le_m + 0.25 * htail_mac_m

    # l_H: wing-AC → tail-AC (CG-independent — drives recommendation)
    l_h = x_htail_ac_m - x_wing_ac_m
    if l_h <= 0:
        # Tail is ahead of the wing → canard-like → not applicable
        result.classification = "not_applicable"
        result.warnings.append(
            "Horizontal tail AC is ahead of wing AC (l_H ≤ 0) — canard-like configuration"
        )
        return result

    result.l_h_m = round(l_h, 4)

    # l_H_eff from aft CG (display-only)
    if cg_aft_m is not None:
        result.l_h_eff_from_aft_cg_m = round(x_htail_ac_m - cg_aft_m, 4)

    # --- Vertical tail geometry -----------------------------------------------
    s_v_m2: float | None = ctx.get("s_v_m2")
    x_vtail_le_m: float | None = ctx.get("x_vtail_le_m")
    vtail_mac_m: float | None = ctx.get("vtail_mac_m")

    x_vtail_ac_m: float | None = None
    l_v: float | None = None
    if s_v_m2 is not None and x_vtail_le_m is not None and vtail_mac_m is not None:
        x_vtail_ac_m = x_vtail_le_m + 0.25 * vtail_mac_m
        l_v = x_vtail_ac_m - x_wing_ac_m

    # --- Volume coefficients --------------------------------------------------
    v_h = (s_h_m2 * l_h) / (s_ref_m2 * mac_m)
    result.v_h_current = round(v_h, 4)

    v_v: float | None = None
    if l_v is not None and l_v > 0:
        v_v = (s_v_m2 * l_v) / (s_ref_m2 * b_ref_m)
        result.v_v_current = round(v_v, 4)

    # --- Target ranges --------------------------------------------------------
    aircraft_class: str = ctx.get("aircraft_class", "rc_trainer")
    targets = AIRCRAFT_CLASS_TARGETS.get(aircraft_class, _DEFAULT_TARGETS)
    result.aircraft_class_used = aircraft_class
    v_h_range: tuple[float, float] = targets["v_h_range"]
    v_v_range: tuple[float, float] = targets["v_v_range"]
    result.v_h_target_range = v_h_range
    result.v_v_target_range = v_v_range
    result.v_h_citation = targets["v_h_citation"]
    result.v_v_citation = targets["v_v_citation"]

    # --- Classify V_H ---------------------------------------------------------
    result.classification_h = _classify_volume(
        v_h, V_H_PHYSICAL_MIN, V_H_PHYSICAL_MAX, v_h_range[0], v_h_range[1]
    )

    # --- Classify V_V ---------------------------------------------------------
    if v_v is not None:
        result.classification_v = _classify_volume(
            v_v, V_V_PHYSICAL_MIN, V_V_PHYSICAL_MAX, v_v_range[0], v_v_range[1]
        )

    # --- Recommended areas (m² → mm²) ----------------------------------------
    v_h_mid = (v_h_range[0] + v_h_range[1]) / 2.0
    result.s_h_recommended_mm2 = round(v_h_mid * s_ref_m2 * mac_m / l_h * 1e6, 0)

    if l_v is not None and l_v > 0:
        v_v_mid = (v_v_range[0] + v_v_range[1]) / 2.0
        result.s_v_recommended_mm2 = round(v_v_mid * s_ref_m2 * b_ref_m / l_v * 1e6, 0)

    # --- Warnings -------------------------------------------------------------
    if result.classification_h == "out_of_physical_range":
        result.warnings.append(
            f"V_H = {v_h:.3f} outside physical range [{V_H_PHYSICAL_MIN}, {V_H_PHYSICAL_MAX}]"
        )
    elif result.classification_h == "below_range":
        result.warnings.append(
            f"V_H = {v_h:.3f} below target {v_h_range[0]:.2f}–{v_h_range[1]:.2f} "
            f"for {aircraft_class}"
        )
    elif result.classification_h == "above_range":
        result.warnings.append(
            f"V_H = {v_h:.3f} above target {v_h_range[0]:.2f}–{v_h_range[1]:.2f} "
            f"for {aircraft_class}"
        )

    if v_v is not None:
        if result.classification_v == "out_of_physical_range":
            result.warnings.append(
                f"V_V = {v_v:.3f} outside physical range [{V_V_PHYSICAL_MIN}, {V_V_PHYSICAL_MAX}]"
            )
        elif result.classification_v == "below_range":
            result.warnings.append(
                f"V_V = {v_v:.3f} below target {v_v_range[0]:.3f}–{v_v_range[1]:.3f} "
                f"for {aircraft_class}"
            )
        elif result.classification_v == "above_range":
            result.warnings.append(
                f"V_V = {v_v:.3f} above target {v_v_range[0]:.3f}–{v_v_range[1]:.3f} "
                f"for {aircraft_class}"
            )

    # Top-level classification: worst of H and V
    result.classification = _worst_classification(
        result.classification_h,
        result.classification_v if v_v is not None else "in_range",
    )

    if not result.cg_aware:
        result.warnings.append(
            "No neutral point available — recommendation based on wing-AC reference only"
        )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_volume(
    value: float,
    phys_min: float,
    phys_max: float,
    target_min: float,
    target_max: float,
) -> _Classification:
    """Classify a tail-volume coefficient."""
    if value < phys_min or value > phys_max:
        return "out_of_physical_range"
    if value < target_min:
        return "below_range"
    if value > target_max:
        return "above_range"
    return "in_range"


_CLASSIFICATION_RANK = {
    "in_range": 0,
    "below_range": 1,
    "above_range": 1,
    "out_of_physical_range": 2,
    "not_applicable": 3,
}


def _worst_classification(cls_h: _Classification, cls_v: _Classification) -> _Classification:
    """Return whichever classification is more severe."""
    if _CLASSIFICATION_RANK.get(cls_h, 0) >= _CLASSIFICATION_RANK.get(cls_v, 0):
        return cls_h
    return cls_v


def build_tail_sizing_context_from_aeroplane(aircraft) -> dict | None:
    """Extract the tail-sizing context dict from an AeroplaneModel.

    Reads:
      - assumption_computation_context (mac_m, s_ref_m2, b_ref_m, x_np_m)
      - wing geometry (area, leading-edge x, MAC) by wing name convention
      - aircraft_class from the is_default loading scenario

    Returns None when the aircraft lacks wings or the context is not yet
    computed.
    """
    ctx_cache: dict = aircraft.assumption_computation_context or {}

    mac_m = ctx_cache.get("mac_m")
    s_ref_m2 = ctx_cache.get("s_ref_m2")
    b_ref_m = ctx_cache.get("b_ref_m")
    x_np_m = ctx_cache.get("x_np_m")

    # CG aft from CG envelope (gh-488)
    cg_aft_m = ctx_cache.get("cg_aft_m")

    if not mac_m or not s_ref_m2:
        return None

    # ------------------------------------------------------------------
    # Identify wing roles by name convention
    # Convention: name contains "horizontal" → htail; "vertical" → vtail
    # Canard: name contains "canard"
    # Flying-wing / tailless: no wing with "horizontal" in name and wing
    #   count == 1 (only main wing).
    # ------------------------------------------------------------------
    wings = aircraft.wings if hasattr(aircraft, "wings") else []
    main_wing = None
    htail = None
    vtail = None
    is_canard = False

    for w in wings:
        wname = (w.name or "").lower()
        if "canard" in wname:
            is_canard = True
        elif "horizontal" in wname or "htail" in wname:
            htail = w
        elif "vertical" in wname or "vtail" in wname:
            vtail = w
        elif "main" in wname or "wing" in wname:
            if main_wing is None or _wing_area_approx(w) > _wing_area_approx(main_wing):
                main_wing = w

    # Fallback: if no main_wing found explicitly, pick largest non-tail wing
    if main_wing is None and wings:
        candidates = [
            w for w in wings
            if "horizontal" not in (w.name or "").lower()
            and "vertical" not in (w.name or "").lower()
            and "canard" not in (w.name or "").lower()
        ]
        if candidates:
            main_wing = max(candidates, key=_wing_area_approx)

    is_tailless = htail is None and not is_canard
    is_v_tail = False  # V-tail decomposition is out-of-scope (gh-491)

    # Wing AC: first x_sec leading-edge X + 25% MAC
    x_wing_ac_m = None
    if main_wing is not None and main_wing.x_secs:
        root_le = main_wing.x_secs[0].xyz_le
        if root_le and len(root_le) >= 1:
            x_wing_ac_m = float(root_le[0]) + 0.25 * (mac_m or 0.0)

    # Horizontal tail geometry
    s_h_m2 = None
    x_htail_le_m = None
    htail_mac_m = None
    if htail is not None and htail.x_secs:
        s_h_m2 = _wing_area_approx(htail)
        root_le = htail.x_secs[0].xyz_le
        if root_le and len(root_le) >= 1:
            x_htail_le_m = float(root_le[0])
        htail_mac_m = _wing_mac_approx(htail)

    # Vertical tail geometry
    s_v_m2 = None
    x_vtail_le_m = None
    vtail_mac_m = None
    if vtail is not None and vtail.x_secs:
        s_v_m2 = _wing_area_approx(vtail)
        root_le = vtail.x_secs[0].xyz_le
        if root_le and len(root_le) >= 1:
            x_vtail_le_m = float(root_le[0])
        vtail_mac_m = _wing_mac_approx(vtail)

    # Aircraft class from default loading scenario
    aircraft_class = "rc_trainer"
    if hasattr(aircraft, "loading_scenarios"):
        for scenario in aircraft.loading_scenarios:
            if scenario.is_default:
                aircraft_class = scenario.aircraft_class or "rc_trainer"
                break

    return {
        "mac_m": mac_m,
        "s_ref_m2": s_ref_m2,
        "b_ref_m": b_ref_m,
        "x_wing_ac_m": x_wing_ac_m,
        "x_np_m": x_np_m,
        "cg_aft_m": cg_aft_m,
        "s_h_m2": s_h_m2,
        "x_htail_le_m": x_htail_le_m,
        "htail_mac_m": htail_mac_m,
        "s_v_m2": s_v_m2,
        "x_vtail_le_m": x_vtail_le_m,
        "vtail_mac_m": vtail_mac_m,
        "aircraft_class": aircraft_class,
        "is_canard": is_canard,
        "is_tailless": is_tailless,
        "is_v_tail": is_v_tail,
    }


def _wing_area_approx(wing) -> float:
    """Rough trapezoidal area from x_secs chord and span segments."""
    xsecs = wing.x_secs if hasattr(wing, "x_secs") else []
    if not xsecs:
        return 0.0
    total = 0.0
    for i in range(len(xsecs) - 1):
        c0 = xsecs[i].chord or 0.0
        c1 = xsecs[i + 1].chord or 0.0
        le0 = xsecs[i].xyz_le or [0.0, 0.0, 0.0]
        le1 = xsecs[i + 1].xyz_le or [0.0, 0.0, 0.0]
        dy = abs(float(le1[1]) - float(le0[1]))
        dz = abs(float(le1[2]) - float(le0[2]))
        span_seg = (dy ** 2 + dz ** 2) ** 0.5
        total += 0.5 * (c0 + c1) * span_seg
    symmetric = getattr(wing, "symmetric", True)
    return total * (2.0 if symmetric else 1.0)


def _wing_mac_approx(wing) -> float | None:
    """Arithmetic mean chord as MAC approximation."""
    xsecs = wing.x_secs if hasattr(wing, "x_secs") else []
    chords = [x.chord for x in xsecs if x.chord]
    if not chords:
        return None
    return sum(chords) / len(chords)
