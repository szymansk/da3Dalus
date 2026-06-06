"""Assumption compute service — gh-465.

Single public entry point: recompute_assumptions(db, aeroplane_uuid).

Runs a two-phase AeroSandbox AeroBuildup sweep:
  Phase 1 — stability run at cruise → (x_np, MAC, CD0)
  Phase 2 — coarse alpha sweep → stall_alpha; fine alpha×velocity sweep → CL_max

Writes cl_max, cd0, cg_x back to the design_assumptions table and caches
the computation context (v_cruise, Re, MAC, NP, SM, CG_agg) on the
aeroplane row for the UI Info Chip Row.

This is a sync function. Callers from async context MUST wrap with
asyncio.to_thread().
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.api.utils import analyse_aerodynamics
from app.converters.model_schema_converters import (
    aeroplane_model_to_aeroplane_schema_async,
    aeroplane_schema_to_asb_airplane_async,
)
from app.core.events import AssumptionChanged, event_bus
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel
from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.models.mission_objective import MissionObjectiveModel
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.polar_by_config import (
    ParabolicPolar,
    PolarRejection,
    RejectionCategory,
    RejectionGate,
)
from app.services.design_assumptions_service import (
    _get_aeroplane,
    seed_defaults,
    update_calculated_value,
)
from app.services.mass_cg_service import aggregate_weight_items
from app.services.stability_service import _scalar

logger = logging.getLogger(__name__)


def recompute_assumptions(db: Session, aeroplane_uuid) -> None:
    """Recompute cl_max, cd0, cg_x from geometry via AeroSandbox.

    Sync function — caller MUST wrap in asyncio.to_thread() when invoked
    from async context (see app/main.py recompute wrapper).

    Skips silently if aircraft has no wings.
    """
    aircraft = _get_aeroplane(db, aeroplane_uuid)
    asb_airplane = _build_asb_airplane(aircraft)

    if not asb_airplane.wings:
        logger.info("No wings on aircraft %s — skipping assumption recompute", aeroplane_uuid)
        return

    # Override ASB's reference area / chord / span so all CL/CD numbers
    # produced by AeroBuildup are normalised by the MAIN WING. ASB's
    # default is the first wing in the list, which may be a tail or
    # rudder for unusual orderings — that produces wildly inflated CL_max.
    main_wing = _select_main_wing(asb_airplane)
    if main_wing is not None:
        asb_airplane.s_ref = float(main_wing.area())
        asb_airplane.c_ref = float(main_wing.mean_aerodynamic_chord())
        asb_airplane.b_ref = float(main_wing.span())

    # Ensure assumption rows + computation config exist (idempotent).
    # Wings can be created before the user opens the Assumptions tab,
    # so we cannot rely on the user having seeded them already.
    seed_defaults(db, aeroplane_uuid)

    config = _load_or_create_config(db, aircraft.id)
    v_cruise, v_max, user_set_cruise = _load_flight_profile_speeds(db, aircraft)

    try:
        x_np, mac, cd0, s_ref = _stability_run_at_cruise(asb_airplane, v_cruise)
        stall_alpha = _coarse_alpha_sweep(asb_airplane, v_cruise, config)
        # _fine_sweep_cl_max returns (cl_max, cl_arr, cd_arr, v_arr, cdi_arr).
        # gh-486 parabolic fit + gh-493 Re-table builder consume cl/cd/v.
        # gh-636 Oswald extraction consumes cdi (CDi = D_induced / (q·S_ref)
        # collected per (V, α) sample inside the sweep — zero extra AB calls).
        fine_result = _fine_sweep_cl_max(asb_airplane, stall_alpha, v_cruise, v_max, config)
        cl_max, sweep_cl_arr, sweep_cd_arr, sweep_v_arr, sweep_cdi_arr = fine_result
    except Exception:
        logger.exception(
            "AeroBuildup failed during recompute for aircraft %s — aborting", aeroplane_uuid
        )
        return

    target_sm = _load_effective_assumption(db, aircraft.id, "target_static_margin")
    cg_x = x_np - target_sm * mac

    old_cg = _get_current_calculated_value(db, aircraft.id, "cg_x")

    update_calculated_value(
        db,
        aeroplane_uuid,
        "cl_max",
        round(cl_max, 4),
        "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db,
        aeroplane_uuid,
        "cd0",
        round(cd0, 5),
        "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db,
        aeroplane_uuid,
        "cg_x",
        round(cg_x, 4),
        "aerobuildup",
        auto_switch_source=True,
    )

    # --- Parabolic polar fit (gh-486) -----------------------------------
    # Fit C_D = C_D0 + C_L² / (π·e·AR) to the raw sweep data; cache the
    # derived Oswald efficiency e in the assumption_computation_context so
    # that _min_drag_speed / _min_sink_speed use aircraft-specific e instead
    # of the fallback constant 0.8.
    aspect_ratio = _main_wing_aspect_ratio(asb_airplane)
    cl_max_effective_for_fit = _load_effective_assumption(db, aircraft.id, "cl_max")
    _cd0_fit, e_oswald_fit, e_r2, polar_rejection, polar_auto_refined = (
        _fit_parabolic_polar_with_refinement(
            asb_airplane=asb_airplane,
            stall_alpha_deg=stall_alpha,
            v_cruise=v_cruise,
            v_max=v_max,
            config=config,
            aspect_ratio=aspect_ratio if aspect_ratio is not None else 0.0,
            cl_max_for_fit=cl_max_effective_for_fit,
            cd0_stability=cd0,
            cl=np.asarray(sweep_cl_arr, dtype=float),
            cd=np.asarray(sweep_cd_arr, dtype=float),
        )
    )
    # gh-636: derive (L/D)max + e_oswald directly from the AeroBuildup sweep
    # — no parabolic-fit dependency for e. The fit still gives us cd0; e is
    # now sourced from AeroBuildup's D_induced output at the (L/D)max point.
    ld_max_clean, cl_at_ld_max_clean, ld_max_idx_clean = _ld_max_from_sweep(
        np.asarray(sweep_cl_arr, dtype=float),
        np.asarray(sweep_cd_arr, dtype=float),
    )
    e_oswald_ab = _e_oswald_from_sweep(
        np.asarray(sweep_cl_arr, dtype=float),
        np.asarray(sweep_cdi_arr, dtype=float),
        aspect_ratio,
        ld_max_idx_clean,
    )
    # Provenance chain: prefer AeroBuildup-Trefftz; fall back to the parabolic
    # fit's e if AB-path didn't yield a sane value; finally the 0.8 default.
    if e_oswald_ab is not None:
        e_oswald_final: float | None = e_oswald_ab
        e_oswald_provenance_clean = "aerobuildup_trefftz"
    elif e_oswald_fit is not None:
        e_oswald_final = e_oswald_fit
        e_oswald_provenance_clean = "fit"
    else:
        e_oswald_final = None
        e_oswald_provenance_clean = "fallback"
    e_oswald_fallback = e_oswald_final is None
    e_oswald_effective = e_oswald_final if e_oswald_final is not None else 0.8
    # gh-636 diagnostic. ASB AeroBuildup packs all non-planar effects
    # (winglets via multi-section dihedral, V-tails, etc.) into
    # `oswalds_efficiency` while keeping geometric AR fixed — so our polar
    # formulas `(L/D)max = ½·√(π·e·AR/CD0)` etc. are already consistent for
    # non-planar wings. `span_effective` from `wing_aero_components[0]` is
    # the projected (Y-axis) span, NOT a classical-LL "effective span > b_ref":
    # empirically b_eff ≤ b_ref (slightly under for steeply dihedraled tips,
    # because the out-of-plane part doesn't project). Diagnostic value:
    # large |b_eff/b_ref - 1| flags unusual geometry for sanity-check.
    logger.info(
        "gh-636 e_oswald: value=%s provenance=%s ld_max=%s cl_at_ld_max=%s ar=%s",
        e_oswald_final,
        e_oswald_provenance_clean,
        ld_max_clean,
        cl_at_ld_max_clean,
        aspect_ratio,
    )
    # -----------------------------------------------------------------------

    # --- gh-526 / epic gh-525 C1: per-configuration parabolic polar -------
    # Run AeroBuildup once per high-lift configuration so V_s0 (landing)
    # and V_s1 (clean) reflect physics instead of the 0.95 / 0.90 heuristic
    # the OPG used historically (audit §5.5).
    polar_clean = ParabolicPolar(
        cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
        e_oswald=round(e_oswald_final, 4) if e_oswald_final is not None else None,
        cl_max=round(cl_max, 4),
        e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
        e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        flap_deflection_deg=0.0,
        provenance="aerobuildup",
        rejection=polar_rejection,
        ld_max=round(ld_max_clean, 2) if ld_max_clean is not None else None,
        cl_at_ld_max=round(cl_at_ld_max_clean, 3) if cl_at_ld_max_clean is not None else None,
        e_oswald_provenance=e_oswald_provenance_clean,
        auto_refined=polar_auto_refined,
    )

    ted_max = _extract_flap_ted_max(aircraft)
    # gh-537: parity guard between the schema walker
    # (`_extract_flap_ted_max`, model.wings.x_secs.trailing_edge_device)
    # and the ASB walker (`_detect_first_flap_name`, asb_airplane.wings.
    # xsecs.control_surfaces). If the model claims a flap exists but the
    # ASB conversion didn't propagate it (converter desync), route to the
    # no-flap fallback with a clear warning — never let
    # `_run_polar_for_deflection` raise AssertionError on the live path.
    if ted_max is not None and _detect_first_flap_name(asb_airplane) is None:
        logger.warning(
            "Schema/ASB flap-name parity mismatch for aircraft %s: schema "
            "reports a flap TED (positive_deflection_deg=%.1f°) but the ASB "
            "airplane has no flap-role control surface. Falling back to "
            "clean polar for takeoff/landing — investigate the converter.",
            aeroplane_uuid,
            ted_max,
        )
        ted_max = None  # route through the no-flap fallback below.

    if ted_max is None:
        # No flap geometry — fallback path: clone clean to takeoff & landing.
        polar_takeoff = polar_clean.model_copy(update={"provenance": "no_flap_geometry"})
        polar_landing = polar_clean.model_copy(update={"provenance": "no_flap_geometry"})
    else:
        # gh-534: takeoff keeps a moderate 15° seed (high deflection at TO
        # hurts climb performance — Scholz §8 / Loftin). Landing uses the
        # FULL TED limit so a real Fowler flap doesn't get capped at 30°
        # and over-state V_s0 / V_APP (Cessna-172 POH cross-check was off
        # by 23 % with the old 30° cap).
        delta_to = min(15.0, float(ted_max))
        delta_ldg = float(ted_max)
        # Independent try blocks per configuration (gh-526 review feedback):
        # a takeoff-sweep failure must not prevent the landing sweep from
        # running — they are physically independent passes.
        try:
            polar_takeoff = _run_polar_for_deflection(
                asb_airplane=asb_airplane,
                flap_deflection_deg=delta_to,
                v_cruise=v_cruise,
                v_max=v_max,
                config=config,
                aspect_ratio=aspect_ratio,
                cd0_stability=cd0,
                cl_max_effective_for_fit=cl_max_effective_for_fit,
            )
        except Exception:
            logger.exception(
                "Takeoff-config AeroBuildup failed for aircraft %s (δ=%.1f°) — "
                "falling back to clean polar",
                aeroplane_uuid,
                delta_to,
            )
            polar_takeoff = polar_clean.model_copy(update={"provenance": "aerobuildup_failed"})

        try:
            polar_landing = _run_polar_for_deflection(
                asb_airplane=asb_airplane,
                flap_deflection_deg=delta_ldg,
                v_cruise=v_cruise,
                v_max=v_max,
                config=config,
                aspect_ratio=aspect_ratio,
                cd0_stability=cd0,
                cl_max_effective_for_fit=cl_max_effective_for_fit,
            )
        except Exception:
            logger.exception(
                "Landing-config AeroBuildup failed for aircraft %s (δ=%.1f°) — "
                "falling back to clean polar",
                aeroplane_uuid,
                delta_ldg,
            )
            polar_landing = polar_clean.model_copy(update={"provenance": "aerobuildup_failed"})

    polar_by_config = {
        "clean": polar_clean.model_dump(),
        "takeoff": polar_takeoff.model_dump(),
        "landing": polar_landing.model_dump(),
    }
    # -----------------------------------------------------------------------

    # --- gh-493: Reynolds-dependent polar table ----------------------------
    # Build a 3-band Re table by rebinning the existing fine-sweep data.
    # V-bands: {V_s_approx, V_cruise, max(1.3·V_cruise, V_max_goal)}.
    # NO new AeroBuildup invocations — marginal cost ≤ 200 ms (3× OLS fits).
    # V_max heuristic is decoupled from the powertrain to prevent chicken-egg.
    # I2: clamp top anchor to actual sweep max to avoid sparse top band.
    v_stall_approx_re = max(v_cruise * 0.5, 3.0)  # same heuristic as _fine_sweep_cl_max
    v_sweep_max_re = v_max  # actual upper bound of the fine sweep velocity range
    v_max_re_anchor = min(max(1.3 * v_cruise, v_max), v_sweep_max_re)
    v_anchor_points_re = [v_stall_approx_re, v_cruise, v_max_re_anchor]
    polar_re_table_top_band_fallback = False
    try:
        from app.services.polar_re_table_service import build_re_table

        polar_re_table, polar_re_table_degenerate = build_re_table(
            v_array=np.asarray(sweep_v_arr, dtype=float),
            cl_array=np.asarray(sweep_cl_arr, dtype=float),
            cd_array=np.asarray(sweep_cd_arr, dtype=float),
            mac_m=mac,
            rho=1.225,
            v_anchor_points=v_anchor_points_re,
            cl_max=cl_max_effective_for_fit if cl_max_effective_for_fit else cl_max,
            ar=aspect_ratio if aspect_ratio is not None else 0.0,
            v_sweep_max=v_sweep_max_re,
        )
        # I2: set top_band_fallback flag if any non-degenerate row has fallback_used=True
        if not polar_re_table_degenerate and polar_re_table:
            top_row = max(polar_re_table, key=lambda r: r.get("re", 0))
            polar_re_table_top_band_fallback = top_row.get("fallback_used", False)
        # I3: validate + serialize through PolarReTableRow schema at cache boundary
        # This strips any internal fields and enforces schema discipline.
        from app.schemas.polar_re_table import PolarReTableRow

        polar_re_table = [PolarReTableRow(**row).model_dump() for row in polar_re_table]
    except Exception:
        logger.exception(
            "Re-table build failed for aircraft %s — skipping (non-fatal)", aeroplane_uuid
        )
        polar_re_table = []
        polar_re_table_degenerate = True
    # -----------------------------------------------------------------------

    # --- gh-488: Loading + Stability envelopes ---------------------------
    # cg_agg_m now reflects the is_default loading scenario's CG (per
    # spec gh-488). Falls back to legacy weight-item aggregation for
    # pre-migration aeroplanes that have no loading scenarios yet.
    from app.services.loading_scenario_service import (
        compute_cg_agg_for_aeroplane,
        compute_loading_envelope_for_aeroplane,
        compute_stability_envelope,
        enrich_context_with_cg_envelope,
    )

    cg_agg = compute_cg_agg_for_aeroplane(db, aircraft)

    _loading = compute_loading_envelope_for_aeroplane(db, aircraft)
    _stability = compute_stability_envelope(
        x_np=float(x_np), mac=float(mac), target_sm=float(target_sm)
    )

    # gh-500: Replace 0.30·MAC stub with physics-based forward CG limit.
    # On failure, keeps the stub from compute_stability_envelope (safe fallback).
    try:
        from app.services.elevator_authority_service import compute_forward_cg_limit

        _fwd_cg_result = compute_forward_cg_limit(db, aircraft)
        # Persist the full result so UI / sm_sizing can read confidence, warnings, etc.
        _stability["forward_cg_result"] = _fwd_cg_result.model_dump()
        if _fwd_cg_result.cg_fwd_m is not None:
            _stability["cg_stability_fwd_m"] = _fwd_cg_result.cg_fwd_m
            if _fwd_cg_result.warnings:
                logger.info(
                    "Elevator authority forward CG (aircraft %s): %s",
                    aircraft.id,
                    "; ".join(_fwd_cg_result.warnings),
                )
        else:
            # Infeasibility: no feasible forward CG limit from physics.
            # Keep the stub (conservative) and log a warning.
            logger.warning(
                "Elevator authority infeasibility for aircraft %s — keeping stub forward CG limit. "
                "Warnings: %s",
                aircraft.id,
                "; ".join(_fwd_cg_result.warnings),
            )
    except ValueError as exc:
        # gh-685: cold-start chicken-and-egg. On the first recompute of an
        # aeroplane the assumption store doesn't have `x_np` / `mac` yet —
        # `compute_forward_cg_limit` reads from the store and raises before
        # this recompute pass writes the new values back. Functionally
        # harmless (the stub fallback covers it), but the previous broad
        # `except Exception + exc_info=True` dumped a full traceback that
        # looked like a real bug. Demote that specific case to INFO without
        # traceback; keep WARNING+traceback for genuine errors.
        msg = str(exc)
        if "x_np=None" in msg or "mac=None" in msg:
            logger.info(
                "Forward-CG limit deferred for aircraft %s "
                "(first recompute — x_np/mac not yet in store).",
                aircraft.id,
            )
        else:
            logger.warning(
                "Elevator authority forward CG failed for aircraft %s — keeping stub.",
                aircraft.id,
                exc_info=True,
            )
    except Exception:
        logger.warning(
            "Elevator authority forward CG failed for aircraft %s — keeping stub.",
            aircraft.id,
            exc_info=True,
        )

    re = _reynolds_number(v_cruise, mac)
    mass = _load_effective_assumption(db, aircraft.id, "mass")
    # Use EFFECTIVE values so user overrides (toggle to ESTIMATE)
    # actually change V_stall, V_md, and V_max.
    cl_max_effective = _load_effective_assumption(db, aircraft.id, "cl_max")
    cd0_effective = _load_effective_assumption(db, aircraft.id, "cd0")
    p_to_w = _load_effective_assumption(db, aircraft.id, "power_to_weight")
    prop_eta = _load_effective_assumption(db, aircraft.id, "prop_efficiency")
    v_stall = _stall_speed(mass, s_ref, cl_max_effective)
    # gh-526: per-configuration stall speeds derived from physics. The OPG
    # consumes these instead of its historical 0.95 / 0.90 heuristic.
    # v_s1 = clean (alias of v_stall_mps for backward compat).
    # v_s_to = takeoff (with flaps clipped to TED limit), v_s0 = landing.
    # When no flap geometry exists, all three fall back to V_s1.
    v_s1 = v_stall
    v_s_to = _stall_speed(mass, s_ref, polar_by_config["takeoff"]["cl_max"])
    v_s0 = _stall_speed(mass, s_ref, polar_by_config["landing"]["cl_max"])
    # Use fitted Oswald e (or fallback 0.8) for V_md and V_min_sink.
    v_md = _min_drag_speed(mass, s_ref, cd0_effective, aspect_ratio, oswald_e=e_oswald_effective)
    v_min_sink = _min_sink_speed(
        mass, s_ref, cd0_effective, aspect_ratio, oswald_e=e_oswald_effective
    )
    # gh-692: w_min — vertical speed at V_min_sink, derived in closed form
    # from the same parabolic-polar scalars. Picard iteration below refines
    # V_min_sink by <5% for healthy polars; we keep w_min on the scalar
    # average to match how pilots read it off the speed polar chart.
    min_sink_rate = _min_sink_rate(
        mass, s_ref, cd0_effective, aspect_ratio, oswald_e=e_oswald_effective
    )

    # V_max from physics if powered (P/W > 0); otherwise fall back to
    # the user-set goal in the flight profile (gliders set max speed
    # via structural limits, not thrust).
    # V_max also uses the fitted Oswald e for consistency with V_md/V_min_sink.
    v_max_computed = _max_level_speed(
        mass,
        s_ref,
        cd0_effective,
        aspect_ratio,
        p_to_w,
        prop_eta,
        oswald_e=e_oswald_effective,
    )
    v_max_effective = v_max_computed if v_max_computed is not None else v_max
    is_glider = p_to_w <= 0

    # --- gh-493 Amendment 7: Picard iteration for V_md / V_min_sink ----------
    # One Picard pass: re-lookup cd0/e at the converged scalar V, re-solve once.
    # Backward-compat: only runs when polar_re_table is available (non-empty).
    if polar_re_table and mac > 0:
        from app.services.polar_re_table_service import lookup_cd0_at_v, lookup_e_oswald_at_v

        v_md = _picard_iterate_speed(
            v0=v_md,
            speed_fn=_min_drag_speed,
            speed_fn_kwargs=dict(mass_kg=mass, s_ref_m2=s_ref, aspect_ratio=aspect_ratio),
            polar_table=polar_re_table,
            mac_m=mac,
        )
        v_min_sink = _picard_iterate_speed(
            v0=v_min_sink,
            speed_fn=_min_sink_speed,
            speed_fn_kwargs=dict(mass_kg=mass, s_ref_m2=s_ref, aspect_ratio=aspect_ratio),
            polar_table=polar_re_table,
            mac_m=mac,
        )
        # For V_max: use Re-table cd0/e at converged V_max
        if v_max_computed is not None:
            v_max_computed = _picard_iterate_speed(
                v0=v_max_computed,
                speed_fn=_max_level_speed,
                speed_fn_kwargs=dict(
                    mass_kg=mass,
                    s_ref_m2=s_ref,
                    aspect_ratio=aspect_ratio,
                    power_to_weight=p_to_w,
                    prop_eta=prop_eta,
                ),
                polar_table=polar_re_table,
                mac_m=mac,
            )
            v_max_effective = v_max_computed if v_max_computed is not None else v_max

    # gh-683: clamp V_md / V_min_sink to V_stall. The closed-form CL formulas
    # (CL_opt = √(CD0·π·AR·e), CL_mp = √(3·π·AR·e·CD0)) assume the polar is
    # parabolic up to the optimum CL — for high-AR / draggy polars the optimum
    # CL exceeds CL_max and the formula back-solves a sub-stall V. That speed
    # is physically unreachable. Clamping to V_stall surfaces the actual
    # operating point (stall) instead of a fictitious sub-stall point.
    if v_md is not None and v_stall is not None:
        v_md = max(v_md, v_stall)
    if v_min_sink is not None and v_stall is not None:
        v_min_sink = max(v_min_sink, v_stall)

    # If the user hasn't set a flight profile, suggest V_md as the
    # cruise speed (best L/D = best range for prop aircraft). Once the
    # user creates a profile and sets cruise_speed_mps, we respect it.
    v_cruise_effective = v_md if (not user_set_cruise and v_md is not None) else v_cruise
    cruise_is_auto = not user_set_cruise and v_md is not None

    # gh-476: extended V-speed set surfaced on the dashboard chip row.
    # Must run AFTER v_max_effective is finalised (Picard iteration) and
    # AFTER v_cruise_effective is resolved (drives the V_a cap).
    g_limit_effective = _load_effective_assumption(db, aircraft.id, "g_limit")
    v_a = _compute_v_a(v_s1_mps=v_s1, g_limit=g_limit_effective, v_cruise_mps=v_cruise_effective)
    v_dive = _compute_v_dive(v_max_effective)
    v_x, v_y = _read_vx_vy_from_ops(db, aircraft.id)

    # CL_α from linear-range alpha-sweep (gh-487 — gust envelope).
    # Regression over α ∈ [-2°, +6°] with R² > 0.995 quality gate.
    # Cached as cl_alpha_per_rad; downstream compute_vn_curve uses it
    # for the Pratt-Walker gust alleviation computation.
    cl_alpha_per_rad, alpha_0_deg = _extract_cl_alpha_from_linear_sweep(asb_airplane, v_cruise)

    # gh-871: α at characteristic speeds from the linear lift curve.
    # CL at stall = cl_max_effective; CL at best-glide and min-sink come from
    # the closed-form parabolic-polar optima (same scalars used by _min_drag_speed
    # / _min_sink_speed). All three are mass-independent.
    alpha_stall_ctx: float | None = None
    alpha_md_ctx: float | None = None
    alpha_min_sink_ctx: float | None = None
    if cl_alpha_per_rad is not None and alpha_0_deg is not None:
        alpha_stall_ctx = _cl_to_alpha_deg(cl_max_effective or 0.0, cl_alpha_per_rad, alpha_0_deg)
        if (
            cd0_effective is not None
            and cd0_effective > 0
            and aspect_ratio is not None
            and aspect_ratio > 0
        ):
            k = 1.0 / (math.pi * aspect_ratio * e_oswald_effective)
            cl_bg = math.sqrt(cd0_effective / k)
            cl_ms = math.sqrt(3.0 * cd0_effective / k)
            alpha_md_ctx = _cl_to_alpha_deg(cl_bg, cl_alpha_per_rad, alpha_0_deg)
            alpha_min_sink_ctx = _cl_to_alpha_deg(cl_ms, cl_alpha_per_rad, alpha_0_deg)

    # Build base context; enrich_context_with_cg_envelope appends gh-488 keys
    # additively (cg_forward_m, cg_aft_m, sm_at_fwd, sm_at_aft) without
    # disturbing existing keys (esp. cg_agg_m — backward compat).
    context: dict = {
        "v_cruise_mps": round(v_cruise_effective, 1),
        "v_cruise_auto": cruise_is_auto,
        "v_max_mps": round(v_max_effective, 1),
        "v_stall_mps": round(v_stall, 1) if v_stall is not None else None,
        # gh-526: v_s1_mps is the clean-config alias of v_stall_mps; v_s0_mps
        # is the landing-config stall (with flaps deflected, if geometry has
        # a flap); v_s_to_mps is the takeoff-config stall. All three derived
        # from physics, not heuristic scalars.
        "v_s1_mps": round(v_s1, 1) if v_s1 is not None else None,
        "v_s_to_mps": round(v_s_to, 1) if v_s_to is not None else None,
        "v_s0_mps": round(v_s0, 1) if v_s0 is not None else None,
        "v_md_mps": round(v_md, 1) if v_md is not None else None,
        "v_min_sink_mps": round(v_min_sink, 1) if v_min_sink is not None else None,
        # gh-692: vertical speed at V_min_sink — Glider/Motorsegler chip.
        "min_sink_rate_mps": round(min_sink_rate, 2) if min_sink_rate is not None else None,
        # gh-476: extended V-speed set surfaced on the chip row.
        # V_a, V_dive: physics / heuristic (provenance noted in field doc).
        # V_x, V_y: pulled from operating-point rows when they exist;
        # None until OPG has run.
        "v_a_mps": round(v_a, 1) if v_a is not None else None,
        "v_dive_mps": round(v_dive, 1) if v_dive is not None else None,
        "v_x_mps": round(v_x, 1) if v_x is not None else None,
        "v_y_mps": round(v_y, 1) if v_y is not None else None,
        "is_glider": is_glider,
        "reynolds": round(re),
        "mac_m": round(mac, 4),
        "s_ref_m2": round(s_ref, 4),
        # gh-625 Bug B: publish the effective `mass` design assumption to the
        # context so consumers (mission KPI _kpi_wing_loading,
        # field_length_service.compute_field_lengths_for_aeroplane introduced
        # in gh-548, _kpi_field_friendliness) can find it without falling back
        # to the AeroplaneModel.total_mass_kg column that is None on most
        # aeroplanes.
        "mass_kg": round(mass, 3) if mass is not None and mass > 0 else None,
        # gh-625 Bug A: publish the effective `g_limit` as the design-limit
        # peak load factor so _kpi_maneuver can compute. A physics-aware
        # refinement reading the V-n curve's gust-augmented peak can replace
        # this later; for now the design-limit value is the correct source.
        "flight_envelope_n_max": (
            g_limit_effective if g_limit_effective is not None and g_limit_effective > 0 else None
        ),
        # b_ref_m — main-wing span (gh-491 sub-task: was set on asb_airplane but not cached)
        "b_ref_m": round(float(main_wing.span()), 4) if main_wing is not None else None,
        "aspect_ratio": round(aspect_ratio, 2) if aspect_ratio is not None else None,
        "x_np_m": round(x_np, 4),
        "target_static_margin": target_sm,
        # cg_agg_m = CG of the is_default scenario (or plain weight-item CG).
        # Kept for backward compat — single-value consumers still get a CG.
        "cg_agg_m": round(cg_agg, 4) if cg_agg is not None else None,
        # Parabolic polar fit results (gh-486)
        # ctx["cd0"] scalar = stability-run cd0 (backward-compat key for gh-486 consumers)
        "cd0": round(cd0, 5),
        # gh-636: top-level e_oswald uses the same provenance chain as
        # polar_by_config[clean].e_oswald — i.e. AB-Trefftz preferred, then
        # parabolic-fit, then None. Matches `e_oswald_fallback_used` semantics.
        "e_oswald": round(e_oswald_final, 4) if e_oswald_final is not None else None,
        "e_oswald_r2": round(e_r2, 4) if e_r2 is not None else None,
        "e_oswald_quality": _classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        "e_oswald_fallback_used": e_oswald_fallback,
        # Linear-range CL_α from α-sweep (gh-487) — consumed by compute_vn_curve for gust loads
        "cl_alpha_per_rad": round(cl_alpha_per_rad, 4) if cl_alpha_per_rad is not None else None,
        # gh-871: zero-lift angle α₀ [degrees] — paired with cl_alpha_per_rad to invert CL→α
        # at characteristic speeds (V_stall, V_min_sink, V_md) for the speed-chip display.
        "alpha_0_deg": round(alpha_0_deg, 4) if alpha_0_deg is not None else None,
        # gh-871: α at characteristic speeds [degrees], surfaced on the speed-chip row.
        # Derived from the linear lift curve; None when lift-curve data is absent.
        "alpha_stall_deg": round(alpha_stall_ctx, 2) if alpha_stall_ctx is not None else None,
        "alpha_best_glide_deg": round(alpha_md_ctx, 2) if alpha_md_ctx is not None else None,
        "alpha_min_sink_deg": round(alpha_min_sink_ctx, 2)
        if alpha_min_sink_ctx is not None
        else None,
        # Reynolds-dependent polar table (gh-493) — 3 V-bands from existing fine-sweep rebinning.
        # No extra AeroBuildup runs. Schema per row: {re, v_mps, cd0, e_oswald, cl_max, r2, fallback_used}
        # ctx["cd0"] and ctx["e_oswald"] scalar keys REMAIN for backward compat (gh-486 consumers).
        "polar_re_table": polar_re_table,
        "polar_re_table_degenerate": polar_re_table_degenerate,
        "polar_re_table_top_band_fallback": polar_re_table_top_band_fallback,
        # gh-526: per-configuration polar fits {clean, takeoff, landing}.
        # See app/schemas/polar_by_config.py.  Replaces the implicit
        # 0.95 / 0.90 V_s heuristic in operating_point_generator_service.
        "polar_by_config": polar_by_config,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # gh-477: required landing field length from the energy balance
    # using the landing-config CL_max (with flaps), the user's chosen
    # surface (or grass_short default), and safety factor. Compared
    # against ``available_field_length_m`` from the mission spec so the
    # UI can render the chip green / red / neutral.
    mission_obj = db.query(MissionObjectiveModel).filter_by(aeroplane_id=aircraft.id).first()
    landing_field_m, surface_used = _compute_landing_field_length(
        mass_kg=mass,
        s_ref_m2=s_ref,
        cl_max_landing=polar_by_config["landing"]["cl_max"],
        landing_surface=mission_obj.landing_surface if mission_obj is not None else None,
        landing_safety_factor=(
            mission_obj.landing_safety_factor if mission_obj is not None else None
        ),
    )
    available = mission_obj.available_field_length_m if mission_obj is not None else None
    landing_field_sufficient: bool | None
    if landing_field_m is None or available is None:
        landing_field_sufficient = None
    else:
        landing_field_sufficient = available >= landing_field_m

    context["landing_field_length_m"] = (
        round(landing_field_m, 1) if landing_field_m is not None else None
    )
    context["landing_surface_used"] = surface_used
    context["landing_field_sufficient"] = landing_field_sufficient

    enrich_context_with_cg_envelope(
        ctx=context,
        cg_loading_fwd_m=_loading["cg_loading_fwd_m"],
        cg_loading_aft_m=_loading["cg_loading_aft_m"],
        cg_stability_fwd_m=_stability["cg_stability_fwd_m"],
        cg_stability_aft_m=_stability["cg_stability_aft_m"],
    )
    _cache_context(db, aircraft, context)

    if old_cg is None or abs(cg_x - old_cg) > 1e-6:
        # Mirror update_assumption: mark OPs DIRTY in the same transaction
        # before emitting AssumptionChanged. Otherwise the retrim handler
        # finds no DIRTY ops and does nothing.
        from app.services.invalidation_service import mark_ops_dirty

        mark_ops_dirty(db, aircraft.id)
        event_bus.publish(AssumptionChanged(aeroplane_id=aircraft.id, parameter_name="cg_x"))


def _build_asb_airplane(aircraft: AeroplaneModel):
    schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
    return aeroplane_schema_to_asb_airplane_async(plane_schema=schema)


def _run_polar_for_deflection(
    *,
    asb_airplane: Any,
    flap_deflection_deg: float,
    v_cruise: float,
    v_max: float,
    config: Any,
    aspect_ratio: float | None,
    cd0_stability: float,
    cl_max_effective_for_fit: float | None,
) -> ParabolicPolar:
    """Run AeroBuildup with the flap deflected; return the fitted polar.

    Strategy (gh-526):
    - Deep-copy the airplane with ``with_control_deflections`` so the
      original (clean) airplane is unaffected.
    - Re-use ``_coarse_alpha_sweep`` and ``_fine_sweep_cl_max`` against the
      deflected airplane to get C_L_max for this configuration.
    - Re-fit a parabolic polar against the deflected sweep so C_D0 / e
      reflect the high-lift drag rise.

    On any AeroBuildup error the caller is responsible for falling back
    to a cloned clean polar with ``provenance="fit_rejected"``.
    """
    flap_name = _detect_first_flap_name(asb_airplane)
    if flap_name is None:
        # Caller must route to the no-flap fallback BEFORE invoking this
        # helper. Returning a sentinel here would feed cl_max=0.0 into
        # _stall_speed and produce an infinite V_s (review feedback).
        raise AssertionError(
            "_run_polar_for_deflection called without a flap surface present — "
            "this is a caller-side routing bug"
        )
    deflected = asb_airplane.with_control_deflections({flap_name: flap_deflection_deg})
    stall_alpha = _coarse_alpha_sweep(deflected, v_cruise, config)
    cl_max, cl_arr, cd_arr, _v_arr, cdi_arr = _fine_sweep_cl_max(
        deflected, stall_alpha, v_cruise, v_max, config
    )
    _cd0_fit, e_oswald_fit, e_r2, polar_rejection, polar_auto_refined = (
        _fit_parabolic_polar_with_refinement(
            asb_airplane=deflected,
            stall_alpha_deg=stall_alpha,
            v_cruise=v_cruise,
            v_max=v_max,
            config=config,
            aspect_ratio=aspect_ratio if aspect_ratio is not None else 0.0,
            cl_max_for_fit=cl_max_effective_for_fit if cl_max_effective_for_fit else cl_max,
            cd0_stability=cd0_stability,
            cl=np.asarray(cl_arr, dtype=float),
            cd=np.asarray(cd_arr, dtype=float),
        )
    )
    # gh-636: empirical (L/D)max + AB-Trefftz e for this configuration.
    ld_max_cfg, cl_at_ld_max_cfg, ld_max_idx_cfg = _ld_max_from_sweep(
        np.asarray(cl_arr, dtype=float),
        np.asarray(cd_arr, dtype=float),
    )
    e_oswald_ab_cfg = _e_oswald_from_sweep(
        np.asarray(cl_arr, dtype=float),
        np.asarray(cdi_arr, dtype=float),
        aspect_ratio,
        ld_max_idx_cfg,
    )
    if e_oswald_ab_cfg is not None:
        e_final: float | None = e_oswald_ab_cfg
        provenance_e = "aerobuildup_trefftz"
    elif e_oswald_fit is not None:
        e_final = e_oswald_fit
        provenance_e = "fit"
    else:
        e_final = None
        provenance_e = "fallback"
    return ParabolicPolar(
        cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
        e_oswald=round(e_final, 4) if e_final is not None else None,
        cl_max=round(float(cl_max), 4),
        e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
        e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        flap_deflection_deg=float(flap_deflection_deg),
        provenance="aerobuildup",
        rejection=polar_rejection,
        ld_max=round(ld_max_cfg, 2) if ld_max_cfg is not None else None,
        cl_at_ld_max=round(cl_at_ld_max_cfg, 3) if cl_at_ld_max_cfg is not None else None,
        e_oswald_provenance=provenance_e,
        auto_refined=polar_auto_refined,
    )


def _detect_first_flap_name(asb_airplane) -> str | None:
    """Return the ASB control-surface name of the first flap-role surface.

    Mirrors ``operating_point_generator_service._pick_control_name`` for
    the FLAP_ROLES set. Avoids cross-service imports by re-implementing
    the trivial role-tag parse locally.
    """
    for wing in getattr(asb_airplane, "wings", []) or []:
        for xsec in getattr(wing, "xsecs", []) or []:
            for cs in getattr(xsec, "control_surfaces", []) or []:
                raw = str(getattr(cs, "name", "")).strip()
                # role tag is the substring between the first '[' and ']'
                if raw.startswith("[") and "]" in raw:
                    role = raw[1 : raw.index("]")].lower()
                    if role == "flap":
                        return raw
    return None


def _compute_v_a(
    v_s1_mps: float | None,
    g_limit: float | None,
    v_cruise_mps: float | None,
) -> float | None:
    """Manoeuvring speed V_a = V_s1 · √n_max, capped at V_C (gh-476).

    Anderson §6.7 / CS-25.335(c) / Scholz lecture §6: at V_a the wing
    reaches C_L_max exactly at the structural load limit n_max, so a
    full-deflection pitch input cannot exceed n_max. Scholz further
    requires V_a ≤ V_C — without this cap, V_a can drift above cruise
    on high-load-limit designs (e.g. acrobatic n+ = 6).

    Returns ``None`` when any input is missing or non-positive.
    """
    if v_s1_mps is None or v_s1_mps <= 0 or g_limit is None or g_limit <= 0:
        return None
    raw = v_s1_mps * math.sqrt(g_limit)
    if v_cruise_mps is not None and v_cruise_mps > 0:
        return min(raw, v_cruise_mps)
    return raw


def _compute_v_dive(v_max_mps: float | None) -> float | None:
    """V_dive heuristic = 1.4 · V_max (gh-476).

    Provenance: ``heuristic`` — flutter analysis is out of project scope.
    Anchored on V_max per the ticket spec; the audit (§5.5 / M3) prefers
    anchoring on V_C, which is tracked as a separate follow-up.
    """
    if v_max_mps is None or v_max_mps <= 0:
        return None
    return 1.4 * v_max_mps


def _read_vx_vy_from_ops(db: Session, aircraft_id: int) -> tuple[float | None, float | None]:
    """Read V_x / V_y from existing operating-point rows (gh-476).

    Both speeds come from the OPG's `best_angle_climb_vx` and
    `best_rate_climb_vy` operating points. When the OPG has not yet
    been run, returns ``(None, None)`` — the chip row renders '–'.
    """
    from app.models.analysismodels import OperatingPointModel

    rows = (
        db.query(OperatingPointModel)
        .filter(
            OperatingPointModel.aircraft_id == aircraft_id,
            OperatingPointModel.name.in_(["best_angle_climb_vx", "best_rate_climb_vy"]),
        )
        .all()
    )
    by_name = {row.name: row for row in rows}
    v_x_row = by_name.get("best_angle_climb_vx")
    v_y_row = by_name.get("best_rate_climb_vy")
    v_x = float(v_x_row.velocity) if v_x_row is not None else None
    v_y = float(v_y_row.velocity) if v_y_row is not None else None
    return v_x, v_y


def _extract_flap_ted_max(aircraft: AeroplaneModel) -> float | None:
    """Return the positive deflection limit of the first flap-role TED.

    Walks ``aircraft.wings → x_secs → trailing_edge_device`` and returns the
    ``positive_deflection_deg`` of the first TED whose ``role`` is
    ``"flap"``. Returns ``None`` when no flap-role TED exists — callers use
    this signal to fall back to a single clean-config polar.

    gh-526 / epic gh-525 finding C1.
    """
    for wing in getattr(aircraft, "wings", []) or []:
        for xsec in getattr(wing, "x_secs", []) or []:
            ted = getattr(xsec, "trailing_edge_device", None)
            if ted is None:
                continue
            role = (getattr(ted, "role", None) or "other").lower()
            if role == "flap":
                limit = getattr(ted, "positive_deflection_deg", None)
                if limit is None:
                    return 25.0  # mirror converter fallback (gh-526)
                return float(limit)
    return None


def _load_or_create_config(db: Session, aeroplane_id: int) -> AircraftComputationConfigModel:
    config = (
        db.query(AircraftComputationConfigModel)
        .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
        .first()
    )
    if config is None:
        config = AircraftComputationConfigModel(
            aeroplane_id=aeroplane_id, **COMPUTATION_CONFIG_DEFAULTS
        )
        db.add(config)
        db.flush()
    return config


def _load_flight_profile_speeds(db: Session, aircraft: AeroplaneModel) -> tuple[float, float, bool]:
    """Returns (cruise_mps, v_max_goal_mps, user_set_cruise).

    user_set_cruise=False when the aircraft has no flight profile (we
    fall back to the default profile). Callers can use this signal to
    decide whether to override cruise with a computed value (V_md).
    """
    from app.services.operating_point_generator_service import (
        _load_effective_flight_profile,
    )

    profile, source_profile_id = _load_effective_flight_profile(db, aircraft)
    goals = profile.get("goals", {})
    cruise = float(goals.get("cruise_speed_mps", 18.0))
    v_max = float(goals.get("max_level_speed_mps") or max(1.35 * cruise, cruise + 8.0))
    user_set_cruise = source_profile_id is not None
    return cruise, v_max, user_set_cruise


def _select_main_wing(asb_airplane):
    """Pick the main wing — the wing with the largest planform area.

    A typical configuration has main wing + horizontal tail + vertical
    tail. ASB's `reference.Cref` defaults to the FIRST wing in the list,
    which may not be the main wing for the user's geometry. Picking by
    planform area is robust across user-defined wing orderings.
    """
    if not asb_airplane.wings:
        return None
    return max(asb_airplane.wings, key=lambda w: float(w.area()))


def _stability_run_at_cruise(asb_airplane, v_cruise: float) -> tuple[float, float, float, float]:
    """Returns (x_np, MAC, CD0, S_ref).

    Uses analyse_aerodynamics → AnalysisModel for x_np and CD0 (same
    path as stability_service, keeps NP consistent across the app).

    For MAC and S_ref, takes the **main wing** (largest planform area)
    rather than ASB's reference. The reference may point at a tail or
    rudder for unusual wing orderings.
    """
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    op_schema = OperatingPointSchema(velocity=v_cruise, alpha=0.0, xyz_ref=xyz_ref)
    result, _ = analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, op_schema, asb_airplane)
    x_np = _scalar(result.reference.Xnp)
    cd0 = _scalar(result.coefficients.CD)

    main_wing = _select_main_wing(asb_airplane)
    if main_wing is None:
        raise ValueError("Cannot compute MAC: no wings on aircraft")
    mac = float(main_wing.mean_aerodynamic_chord())
    s_ref = float(main_wing.area())

    if x_np is None or cd0 is None or mac <= 0 or s_ref <= 0:
        raise ValueError("AeroBuildup returned NULL or non-positive values")
    return float(x_np), mac, float(cd0), s_ref


def _coarse_alpha_sweep(
    asb_airplane, v_cruise: float, config: AircraftComputationConfigModel
) -> float:
    """Returns approximate stall_alpha_deg (alpha where CL peaks).

    gh-690: vectorised — one ``AeroBuildup.run()`` call over the whole α
    sweep. AeroSandbox 4.2.x accepts numpy-array op-points and returns
    same-shape result fields.
    """
    import aerosandbox as asb

    alphas = np.arange(
        config.coarse_alpha_min_deg,
        config.coarse_alpha_max_deg + 0.01,
        config.coarse_alpha_step_deg,
    )
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    op = asb.OperatingPoint(
        velocity=np.full_like(alphas, v_cruise, dtype=float),
        alpha=alphas.astype(float),
    )
    r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()
    cls = _extract_array(r, "CL", n=len(alphas), default=0.0)
    return float(alphas[int(np.argmax(cls))])


def _fine_sweep_cl_max(
    asb_airplane,
    stall_alpha_deg: float,
    v_cruise: float,
    v_max: float,
    config: AircraftComputationConfigModel,
    *,
    alpha_step_override: float | None = None,
    alpha_margin_override: float | None = None,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns (CL_max, cl_array, cd_array, v_array, cdi_array) from a fine α × V sweep.

    All returned arrays have the same length (one entry per (V, α) sample).

    - cl_array / cd_array drive the gh-486 parabolic polar fit and the gh-493
      Re-table builder.
    - cdi_array (gh-636) is the AeroBuildup-internal induced-drag coefficient
      at each sample. It lets `recompute_assumptions` extract Oswald e directly
      via ``e = CL² / (π·AR·CDi)`` at the (L/D)max point, without re-fitting a
      parabola. Costs zero extra AeroBuildup calls.

    ``alpha_step_override`` / ``alpha_margin_override`` (gh-672) let the
    polar-fit auto-recovery re-run a *finer* sweep without mutating the stored
    config. They default to the config's values.
    """
    import aerosandbox as asb

    alpha_step = (
        alpha_step_override if alpha_step_override is not None else config.fine_alpha_step_deg
    )
    alpha_margin = (
        alpha_margin_override if alpha_margin_override is not None else config.fine_alpha_margin_deg
    )
    alpha_min = stall_alpha_deg - alpha_margin
    alpha_max = stall_alpha_deg + alpha_margin
    alphas = np.arange(alpha_min, alpha_max + 0.01, alpha_step)

    v_stall_approx = max(v_cruise * 0.5, 3.0)
    velocities = np.linspace(v_stall_approx, v_max, config.fine_velocity_count)

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    s_ref = float(asb_airplane.s_ref)

    # gh-690: one vectorised .run() over the flattened V × α grid (was
    # ~150 calls per polar config). meshgrid + indexing="xy" gives
    # V-outer / α-inner ravel order, which matches the pre-refactor
    # nested-loop order that downstream consumers index against.
    a_grid, v_grid = np.meshgrid(alphas, velocities, indexing="xy")
    v_flat = v_grid.ravel().astype(float)
    a_flat = a_grid.ravel().astype(float)
    n_pts = v_flat.size
    op = asb.OperatingPoint(velocity=v_flat, alpha=a_flat)
    r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()

    cl_arr = _extract_array(r, "CL", n=n_pts, default=0.0)
    cd_arr = _extract_array(r, "CD", n=n_pts, default=0.0)
    # gh-636: D_induced exposed per op-point. CDi = D_induced / (q · S_ref).
    # Keep NaNs where AeroBuildup returned NaN/missing so the consumer can
    # detect and skip these entries (same contract as the pre-refactor code).
    d_induced = _extract_array(r, "D_induced", n=n_pts, default=float("nan"))
    q = 0.5 * 1.225 * v_flat**2  # ISA sea-level rho; consistent with op
    with np.errstate(invalid="ignore", divide="ignore"):
        cdi_arr = np.where(
            (s_ref > 0) & np.isfinite(d_induced),
            d_induced / (q * s_ref),
            np.nan,
        )

    cl_max = float(np.max(cl_arr)) if cl_arr.size > 0 else -float("inf")
    return (cl_max, cl_arr, cd_arr, v_flat, cdi_arr)


def _extract_cl_alpha_from_linear_sweep(
    asb_airplane,
    v_cruise: float,
    alpha_min_deg: float = -2.0,
    alpha_max_deg: float = 6.0,
    alpha_step_deg: float = 1.0,
    r2_threshold: float = 0.995,
) -> tuple[float | None, float | None]:
    """CL_α and zero-lift angle from a linear-range alpha-sweep at cruise speed (gh-487).

    Runs AeroBuildup at α ∈ [alpha_min_deg, alpha_max_deg] (default [-2°, +6°])
    and fits CL = CL_α·α + CL_0 with ordinary least squares.

    Quality gate: if R² < r2_threshold (default 0.995), the lift curve is
    nonlinear in this range (early stall, control surface interaction, etc.)
    and (None, None) is returned.  The downstream gust computation will then
    fall back to Helmbold-Diederich.

    Returns:
        (cl_alpha_per_rad, alpha_0_deg) — CL_α in rad⁻¹ and zero-lift angle α₀ in degrees.
        (None, None) on failure / quality-gate rejection.

    Sources: gh-487 spec; Anderson 6e §5.3; FAR-25.341(a)(2); gh-871.
    """
    import aerosandbox as asb

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    alphas_deg = np.arange(alpha_min_deg, alpha_max_deg + 0.01, alpha_step_deg)
    alphas_rad = np.deg2rad(alphas_deg)

    # gh-690: vectorised — one AeroBuildup.run over the whole α sweep.
    op = asb.OperatingPoint(
        velocity=np.full_like(alphas_deg, v_cruise, dtype=float),
        alpha=alphas_deg.astype(float),
    )
    r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()
    cls_arr = _extract_array(r, "CL", n=len(alphas_deg), default=float("nan"))
    alphas_arr = np.asarray(alphas_rad)

    # Discard NaN points (convergence failures)
    mask = np.isfinite(cls_arr)
    if mask.sum() < 3:
        logger.warning(
            "CL_α extraction: fewer than 3 valid data points in α ∈ [%.0f°, %.0f°] "
            "— skipping (will fall back to Helmbold).",
            alpha_min_deg,
            alpha_max_deg,
        )
        return None, None

    a_fit = alphas_arr[mask]
    cl_fit = cls_arr[mask]

    # Least-squares: CL = cl_alpha * alpha + cl_0
    # Normal equations: [sum(a²) sum(a); sum(a) N] [cl_alpha; cl_0] = [sum(a·CL); sum(CL)]
    a_mat = np.column_stack([a_fit, np.ones_like(a_fit)])
    coeffs, *_ = np.linalg.lstsq(a_mat, cl_fit, rcond=None)
    cl_alpha_fit = float(coeffs[0])
    cl_0 = float(coeffs[1])

    # R² quality gate
    cl_pred = cl_alpha_fit * a_fit + cl_0
    ss_res = float(np.sum((cl_fit - cl_pred) ** 2))
    ss_tot = float(np.sum((cl_fit - cl_fit.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    if r2 < r2_threshold:
        logger.warning(
            "CL_α extraction: R²=%.4f < %.3f in α ∈ [%.0f°, %.0f°]. "
            "Lift curve may be nonlinear — setting cl_alpha_per_rad=None "
            "(will fall back to Helmbold-Diederich for gust loads).",
            r2,
            r2_threshold,
            alpha_min_deg,
            alpha_max_deg,
        )
        return None, None

    if cl_alpha_fit <= 0:
        logger.warning(
            "CL_α extraction: fitted CL_α=%.4f ≤ 0 (degenerate geometry?). "
            "Setting cl_alpha_per_rad=None.",
            cl_alpha_fit,
        )
        return None, None

    # gh-871: zero-lift angle α₀ = -cl_0 / cl_alpha [radians] → degrees
    # The linear lift curve is CL = cl_alpha * (alpha - alpha_0), so
    # alpha_0 = -cl_0 / cl_alpha (in radians). Convert to degrees for storage.
    alpha_0_deg = math.degrees(-cl_0 / cl_alpha_fit)

    logger.debug(
        "CL_α extraction: CL_α=%.4f rad⁻¹, CL_0=%.4f, α₀=%.2f°, R²=%.4f (α ∈ [%.0f°, %.0f°]).",
        cl_alpha_fit,
        cl_0,
        alpha_0_deg,
        r2,
        alpha_min_deg,
        alpha_max_deg,
    )
    return cl_alpha_fit, alpha_0_deg


def _extract_scalar(result: Any, key: str, *, default: float) -> float:
    """Extract a CL/CD scalar from raw AeroBuildup result (dict or object)."""
    if isinstance(result, dict):
        val = result.get(key)
    else:
        val = getattr(result, key, None)
    scalar = _scalar(val)
    return float(scalar) if scalar is not None else default


def _extract_array(result: Any, key: str, *, n: int, default: float) -> np.ndarray:
    """Extract a length-``n`` 1-D float array from a vectorised AeroBuildup result.

    gh-690 companion to ``_extract_scalar``: when ``AeroBuildup.run()`` is
    called with an array-shaped ``OperatingPoint``, each result field is a
    same-shape array (or a 0-D array if the array happened to be length 1
    on certain CasADi paths). Always return a 1-D ``np.ndarray`` of length
    ``n``, filling with ``default`` on missing keys or non-array values to
    preserve the contract of the pre-refactor per-point loop.
    """
    if isinstance(result, dict):
        val = result.get(key)
    else:
        val = getattr(result, key, None)
    if val is None:
        return np.full(n, default, dtype=float)
    arr = np.asarray(val, dtype=float).ravel()
    if arr.size == n:
        return arr
    if arr.size == 1 and n == 1:
        return arr.reshape(1)
    # Shape mismatch (shouldn't happen with current ASB) — fall back to
    # default so a downstream NaN-aware consumer can still proceed.
    return np.full(n, default, dtype=float)


def _build_rejection(
    gate: RejectionGate,
    category: RejectionCategory,
    fitted_value: float | None,
    threshold: str,
    hint: str,
) -> PolarRejection:
    """Construct a PolarRejection (gh-630) with consistent rounding."""
    return PolarRejection(
        gate=gate,
        category=category,
        fitted_value=round(fitted_value, 6) if fitted_value is not None else None,
        threshold=threshold,
        hint=hint,
    )


def _ld_max_from_sweep(
    cl_arr: np.ndarray, cd_arr: np.ndarray
) -> tuple[float | None, float | None, int | None]:
    """Empirical (L/D)max and the CL at which it occurs (gh-636).

    Independent of any fit. Returns (ld_max, cl_at_ld_max, index) on success,
    or (None, None, None) if the sweep contains no usable point (all-NaN /
    non-positive CD).
    """
    # mask of valid points: finite CL/CD with CD > 0 and CL > 0 (positive lift).
    mask = np.isfinite(cl_arr) & np.isfinite(cd_arr) & (cd_arr > 0.0) & (cl_arr > 0.0)
    if not mask.any():
        return None, None, None
    ld = np.full_like(cl_arr, -np.inf, dtype=float)
    ld[mask] = cl_arr[mask] / cd_arr[mask]
    i = int(np.argmax(ld))
    if not np.isfinite(ld[i]):
        return None, None, None
    return float(ld[i]), float(cl_arr[i]), i


def _e_oswald_from_sweep(
    cl_arr: np.ndarray,
    cdi_arr: np.ndarray,
    ar: float | None,
    ld_max_index: int | None,
) -> float | None:
    """Oswald factor e from AeroBuildup's per-sample induced drag (gh-636).

    Uses ``e = CL² / (π · AR · CDi)`` at the (L/D)max sample. AeroBuildup
    exposes ``D_induced`` per op-point, so this is direct — no parabolic fit
    needed. Falls back to None when inputs are missing/non-physical.
    """
    if ld_max_index is None or ar is None or not np.isfinite(ar) or ar <= 0:
        return None
    cl = cl_arr[ld_max_index]
    cdi = cdi_arr[ld_max_index]
    if not (np.isfinite(cl) and np.isfinite(cdi) and cdi > 0 and cl > 0):
        return None
    e = float(cl**2 / (np.pi * ar * cdi))
    # Sanity clip: a meaningful e is in (0, ~1.05] (allow tiny VLM-Trefftz
    # overshoot above 1.0 for near-elliptical wings). Reject pathological
    # values rather than push them downstream.
    if not (0.0 < e <= 1.10):
        return None
    return e


def _fit_parabolic_polar(
    cl: np.ndarray,
    cd: np.ndarray,
    ar: float,
    cl_max: float,
    cd0_stability: float,
) -> tuple[float | None, float | None, float | None, PolarRejection | None]:
    """Fit C_D = C_D0 + C_L²/(π·e·AR) to raw polar data via OLS.

    Reference: Anderson §6.1.2 (drag polar), §6.7.2 ((L/D)_max derivation).

    Window: linear region of the polar in CL-space:
        C_L_lo = max(0.10, 0.10 · C_L,max)
        C_L_hi = 0.85 · C_L,max

    Requires ≥ 6 sample points in the window. All rejection guards must
    pass; otherwise returns (None, None, None, PolarRejection) and emits a logger.warning.

    Rejection guards:
    - ≥ 6 points in window
    - k > 0 (slope positive — physically required)
    - cd0_fit > 0 (positive intercept)
    - e_oswald ∈ (0.4, 1.0] (physical range)
    - dCD/d(CL²) monotonically non-decreasing (laminar-bubble guard)
    - |cd0_fit - cd0_stability| / cd0_stability ≤ 0.20 (sanity check)

    Returns:
        (cd0_fit, e_oswald, r2, None) on success, or
        (None, None, None, PolarRejection) on rejection.
    """
    if ar is None or ar <= 0:
        logger.warning("polar fit rejected: invalid aspect ratio %r", ar)
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="insufficient_points",
                category="sweep",
                fitted_value=float(ar) if ar is not None else None,
                threshold="ar > 0",
                hint="Ungültiges Streckenverhältnis — Wing-Geometrie nicht definiert.",
            ),
        )
    cl_lo = max(0.10, 0.10 * cl_max)
    cl_hi = 0.85 * cl_max

    mask = (cl >= cl_lo) & (cl <= cl_hi)
    cl_win = cl[mask]
    cd_win = cd[mask]

    if len(cl_win) < 6:
        logger.warning(
            "polar fit rejected: only %d points in window [%.3f, %.3f] (need ≥ 6)",
            len(cl_win),
            cl_lo,
            cl_hi,
        )
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="insufficient_points",
                category="sweep",
                fitted_value=float(len(cl_win)),
                threshold=">= 6 points",
                hint="Zu wenig Punkte im linearen Polar-Fenster — α-Auflösung zu grob.",
            ),
        )

    cl2_win = cl_win**2

    # Monotonicity guard: dCD/d(CL²) must be non-negative across window
    # (laminar-bubble dip produces a region where CD decreases as CL² increases)
    sort_idx = np.argsort(cl2_win)
    cl2_sorted = cl2_win[sort_idx]
    cd_sorted = cd_win[sort_idx]
    diffs = np.diff(cd_sorted)
    if np.any(diffs < -1e-6):
        logger.warning(
            "polar fit rejected: non-monotonic dCD/d(CL²) in window — "
            "possible laminar bubble or stall contamination"
        )
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="non_monotonic_polar",
                category="data",
                fitted_value=float(np.min(diffs)),
                threshold="dCD/d(CL²) >= 0",
                hint="Nicht-monotone Polare im linearen Bereich — möglicher Laminar-Bubble oder Stall-Kontamination.",
            ),
        )

    # OLS fit: C_D = k · C_L² + cd0  (numpy returns highest-degree first)
    k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)

    if k <= 0:
        logger.warning("polar fit rejected: non-positive slope k=%.6f (requires k>0)", k)
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="negative_slope_k",
                category="design",
                fitted_value=float(k),
                threshold="k > 0",
                hint=(
                    "Polare zeigt mit steigendem Auftrieb fallenden Widerstand — "
                    "wahrscheinlich Twist/Verwindung oder Planform-Kink unphysikalisch. "
                    "AVL-Run prüfen."
                ),
            ),
        )

    if cd0_fit <= 0:
        logger.warning("polar fit rejected: non-positive cd0_fit=%.6f (requires cd0>0)", cd0_fit)
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="non_positive_cd0",
                category="consistency",
                fitted_value=float(cd0_fit),
                threshold="cd0 > 0",
                hint="Parabolischer Fit liefert negatives cd0 — Datenrauschen am unteren Fensterrand.",
            ),
        )

    e_oswald = 1.0 / (np.pi * ar * k)

    if not (0.4 < e_oswald <= 1.0):
        logger.warning(
            "polar fit rejected: e_oswald=%.4f outside physical range (0.4, 1.0]",
            e_oswald,
        )
        return (
            None,
            None,
            None,
            _build_rejection(
                gate="unphysical_e_oswald",
                category="design",
                fitted_value=float(e_oswald),
                threshold="(0.4, 1.0]",
                hint=(
                    f"Berechnete Spannweiteneffizienz e = {e_oswald:.3f} außerhalb (0.4, 1.0]. "
                    "Konfiguration für AeroBuildup vermutlich ungeeignet, AVL nutzen."
                ),
            ),
        )

    if cd0_stability > 0:
        rel_dev = abs(cd0_fit - cd0_stability) / cd0_stability
        if rel_dev > 0.20:
            logger.warning(
                "polar fit rejected: cd0_fit=%.5f deviates %.1f%% from stability "
                "run cd0=%.5f (threshold 20%%)",
                cd0_fit,
                rel_dev * 100,
                cd0_stability,
            )
            return (
                None,
                None,
                None,
                _build_rejection(
                    gate="cd0_stability_mismatch",
                    category="consistency",
                    fitted_value=float(rel_dev),
                    threshold="<= 0.20",
                    hint="cd0 aus Polar-Fit weicht >20 % vom Stability-Run ab — Datenkonsistenz prüfen.",
                ),
            )

    # R² for quality reporting
    ss_res = float(np.sum((cd_win - (k * cl2_win + cd0_fit)) ** 2))
    ss_tot = float(np.sum((cd_win - np.mean(cd_win)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    n_pts = int(len(cl_win))
    logger.info(
        "polar fit success: e_oswald=%.4f cd0=%.5f R²=%.4f n_points=%d",
        e_oswald,
        cd0_fit,
        r2,
        n_pts,
    )
    return float(cd0_fit), float(e_oswald), float(r2), None


# gh-672: rejection gates that are caused by too-coarse α-resolution (vs a
# genuinely unphysical polar). Only these trigger an auto-refinement retry.
_REFINABLE_REJECTION_GATES = frozenset({"insufficient_points", "non_monotonic_polar"})


def _fit_parabolic_polar_with_refinement(
    *,
    asb_airplane,
    stall_alpha_deg: float,
    v_cruise: float,
    v_max: float,
    config: "AircraftComputationConfigModel",
    aspect_ratio: float,
    cl_max_for_fit: float | None,
    cd0_stability: float,
    cl: np.ndarray,
    cd: np.ndarray,
    max_retries: int = 2,
) -> tuple[float | None, float | None, float | None, "PolarRejection | None", bool]:
    """Fit the parabolic polar, auto-refining the α-resolution on resolution-
    related rejections (gh-672).

    If the fit is rejected with ``insufficient_points`` or
    ``non_monotonic_polar`` — both caused by a too-coarse sweep — re-run a
    *finer* ``_fine_sweep_cl_max`` (halved α-step, ×1.5 α-margin) and refit,
    up to ``max_retries`` times. Per memory ``feedback_aerobuildup_resolution``
    this only ever **increases resolution** — it never loosens a threshold.
    Other gates (negative slope, unphysical e, …) are genuine design/physics
    rejections and do not retry.

    Returns ``(cd0_fit, e_oswald, r2, rejection, auto_refined)`` where
    ``auto_refined`` is True only when a refinement produced a *successful* fit
    (so the UI banner is shown only when it actually helped).
    """
    fit = _fit_parabolic_polar(
        np.asarray(cl, dtype=float),
        np.asarray(cd, dtype=float),
        ar=aspect_ratio,
        cl_max=cl_max_for_fit,
        cd0_stability=cd0_stability,
    )
    did_refine = False
    for attempt in range(1, max_retries + 1):
        rejection = fit[3]
        if rejection is None or rejection.gate not in _REFINABLE_REJECTION_GATES:
            break
        step = config.fine_alpha_step_deg / (2**attempt)
        margin = config.fine_alpha_margin_deg * (1.5**attempt)
        logger.info(
            "gh-672: polar fit gate '%s' — auto-refining α-resolution "
            "(attempt %d/%d): step→%.3f°, margin→%.2f°",
            rejection.gate,
            attempt,
            max_retries,
            step,
            margin,
        )
        try:
            refined = _fine_sweep_cl_max(
                asb_airplane,
                stall_alpha_deg,
                v_cruise,
                v_max,
                config,
                alpha_step_override=step,
                alpha_margin_override=margin,
            )
        except Exception:
            logger.exception("gh-672: refined fine sweep failed; keeping original rejection")
            break
        did_refine = True
        fit = _fit_parabolic_polar(
            np.asarray(refined[1], dtype=float),
            np.asarray(refined[2], dtype=float),
            ar=aspect_ratio,
            cl_max=cl_max_for_fit,
            cd0_stability=cd0_stability,
        )

    cd0_fit, e_oswald, r2, rejection = fit
    auto_refined = did_refine and rejection is None
    return cd0_fit, e_oswald, r2, rejection, auto_refined


def _classify_polar_quality(r2: float) -> str:
    """Classify polar fit quality by R².

    Returns 'high' (R²>0.99), 'medium' (0.95≤R²≤0.99), or 'low' (R²<0.95).
    """
    if r2 > 0.99:
        return "high"
    if r2 >= 0.95:
        return "medium"
    return "low"


def _load_effective_assumption(db: Session, aeroplane_id: int, param_name: str) -> float:
    """Return the effective value of a design assumption (calculated or estimate)."""
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return PARAMETER_DEFAULTS.get(param_name, 0.0)
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


def _get_current_calculated_value(db: Session, aeroplane_id: int, param_name: str) -> float | None:
    """Return the current calculated_value for a design assumption, or None."""
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    return row.calculated_value if row else None


def _load_cg_agg(db: Session, aeroplane_id: int) -> float | None:
    """Return mass-weighted CG x from weight items, or None if no items exist."""
    rows = db.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == aeroplane_id).all()
    if not rows:
        return None
    items = [{"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m} for r in rows]
    _, cg_x, _, _ = aggregate_weight_items(items)
    return cg_x


def _reynolds_number(velocity: float, mac: float, rho: float = 1.225, mu: float = 1.81e-5) -> float:
    """Sea-level standard atmosphere Reynolds number.

    Sufficient for the UI chip; not altitude-aware. Operating points use
    their own atmosphere model.
    """
    return rho * velocity * mac / mu


def _stall_speed(
    mass_kg: float,
    s_ref_m2: float,
    cl_max: float,
    rho: float = 1.225,
    g: float = 9.81,
) -> float | None:
    """Sea-level stall speed: V_stall = sqrt(2 W / (rho S CL_max)).

    Returns None when CL_max or S_ref is non-positive. The 0.5 floor on
    CL_max prevents wildly inflated stall speeds when AeroBuildup
    misjudges stall on degenerate geometry.
    """
    if s_ref_m2 <= 0 or cl_max <= 0:
        return None
    cl_max_safe = max(cl_max, 0.5)
    weight_n = mass_kg * g
    return float(np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_max_safe)))


# gh-477: μ_eff for the landing-field-length energy balance. Values
# come from operational RC / UAV practice (the issue's "References /
# Formula derivation" section). Not from Anderson — aircraft
# performance is a separate textbook domain (Raymer ch. 17, Roskam P.7).
LANDING_SURFACE_MU: dict[str, float] = {
    "grass_short": 0.15,
    "grass_long": 0.22,
    "hard_paved": 0.07,  # no-brake default; brake flag is a future ticket
    "soft_soil": 0.30,
    "belly_grass": 0.40,
    "net_recovery": 0.0,  # special-cased to s_ground=0 below
}

_LANDING_FLARE_M: float = 15.0
_LANDING_SAFETY_DEFAULT: float = 1.5
_LANDING_SURFACE_DEFAULT: str = "grass_short"
_V_TD_OVER_V_S0: float = 1.15  # touchdown speed = 1.15 · V_S0 (RC rule of thumb)


def _compute_landing_field_length(
    mass_kg: float | None,
    s_ref_m2: float | None,
    cl_max_landing: float | None,
    landing_surface: str | None,
    landing_safety_factor: float | None,
    rho: float = 1.225,
    g: float = 9.81,
) -> tuple[float | None, str | None]:
    """Required landing field length (gh-477).

    Returns ``(L_landing_m, surface_used)``. Both are ``None`` when any
    of ``cl_max_landing``, ``mass_kg`` or ``s_ref_m2`` is missing or
    non-positive — the caller renders no chip in that case.

    Energy balance: ½·m·V_TD² = μ_eff·m·g·s_ground ⇒
    ``s_ground = V_TD² / (2·g·μ_eff)``. The mass cancels — the result
    depends only on V_TD (from V_S0 from physics) and surface friction.

    Special case: ``net_recovery`` is a catch / arrester — there is no
    ground roll, so ``L_landing`` collapses to the safety-padded flare.
    """
    if mass_kg is None or s_ref_m2 is None or cl_max_landing is None:
        return (None, None)
    if mass_kg <= 0 or s_ref_m2 <= 0 or cl_max_landing <= 0:
        return (None, None)

    surface_key = (
        landing_surface if landing_surface in LANDING_SURFACE_MU else _LANDING_SURFACE_DEFAULT
    )
    safety = (
        landing_safety_factor
        if landing_safety_factor is not None and landing_safety_factor >= 1.0
        else _LANDING_SAFETY_DEFAULT
    )

    v_s0 = _stall_speed(mass_kg, s_ref_m2, cl_max_landing, rho=rho, g=g)
    if v_s0 is None:
        return (None, None)
    v_td = _V_TD_OVER_V_S0 * v_s0

    if surface_key == "net_recovery":
        s_ground = 0.0
    else:
        mu = LANDING_SURFACE_MU[surface_key]
        # mu==0 would mean infinite roll — defensive, even though the
        # table has no such entry outside net_recovery.
        if mu <= 0:
            return (None, surface_key)
        s_ground = (v_td * v_td) / (2.0 * g * mu)

    return (float(safety * (_LANDING_FLARE_M + s_ground)), surface_key)


def _main_wing_aspect_ratio(asb_airplane) -> float | None:
    """Aspect ratio AR = b² / S of the main wing (largest planform)."""
    main = _select_main_wing(asb_airplane)
    if main is None:
        return None
    s = float(main.area())
    b = float(main.span())
    if s <= 0:
        return None
    return (b * b) / s


def _max_level_speed(
    mass_kg: float,
    s_ref_m2: float,
    cd0: float,
    aspect_ratio: float | None,
    power_to_weight: float,
    prop_eta: float,
    rho: float = 1.225,
    g: float = 9.81,
    oswald_e: float = 0.8,
) -> float | None:
    """Sea-level V_max from a power balance.

    At V_max, available shaft power × prop efficiency equals power
    required for level flight:

        P_avail · η_prop = D(V) · V

    With induced + parasitic drag this becomes a 4th-order polynomial
    in V:

        A · V⁴ − P_eta · V + B = 0

    where A = ½ρ·S·CD0, B = 2k·W²/(ρ·S), P_eta = (P/W) · m · η.

    Returns None for gliders (P/W ≤ 0) or other degenerate inputs;
    callers should fall back to the user-set max speed goal.
    """
    if (
        power_to_weight <= 0
        or prop_eta <= 0
        or s_ref_m2 <= 0
        or cd0 <= 1e-6
        or aspect_ratio is None
        or aspect_ratio <= 0
    ):
        return None

    weight_n = mass_kg * g
    p_eta = power_to_weight * mass_kg * prop_eta
    k = 1.0 / (np.pi * aspect_ratio * oswald_e)
    a = 0.5 * rho * s_ref_m2 * cd0
    b = 2.0 * k * weight_n * weight_n / (rho * s_ref_m2)

    # numpy.roots solves a · V⁴ + 0 · V³ + 0 · V² − P_eta · V + b = 0.
    coeffs = [a, 0.0, 0.0, -p_eta, b]
    roots = np.roots(coeffs)
    # Pick the largest real positive root above V_md.
    real_positive = [float(r.real) for r in roots if abs(r.imag) < 1e-6 and r.real > 0]
    if not real_positive:
        return None
    return max(real_positive)


def _min_drag_speed(
    mass_kg: float,
    s_ref_m2: float,
    cd0: float,
    aspect_ratio: float | None,
    rho: float = 1.225,
    g: float = 9.81,
    oswald_e: float = 0.8,
) -> float | None:
    """Sea-level minimum-drag speed (= best L/D = best range for prop).

    Derivation: at (L/D)_max the induced drag equals the parasitic
    drag, giving CL_opt = sqrt(CD0/k) with k = 1 / (pi · AR · e).
    Solving level flight L = W for V yields:

        V_md = sqrt( (2 m g) / (rho S sqrt(CD0/k)) )

    Returns None for degenerate inputs (no wing, zero AR, zero CD0).
    """
    if s_ref_m2 <= 0 or cd0 <= 1e-6 or aspect_ratio is None or aspect_ratio <= 0:
        return None
    k = 1.0 / (np.pi * aspect_ratio * oswald_e)
    cl_opt = float(np.sqrt(cd0 / k))
    if cl_opt <= 0:
        return None
    weight_n = mass_kg * g
    return float(np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_opt)))


def _min_sink_speed(
    mass_kg: float,
    s_ref_m2: float,
    cd0: float,
    aspect_ratio: float | None,
    rho: float = 1.225,
    g: float = 9.81,
    oswald_e: float = 0.8,
) -> float | None:
    """Sea-level minimum-sink speed (= minimum-power, V_mp).

    Anderson §6.7.2: at min-power the induced drag is three times the
    parasitic drag, giving C_L_mp = sqrt(3·π·e·AR·C_D0). Equivalent
    identity: V_mp = V_md / 3^(1/4) ≈ 0.760·V_md.

    Returns None for degenerate inputs (no wing, zero AR, zero CD0).
    """
    if s_ref_m2 <= 0 or cd0 <= 1e-6 or aspect_ratio is None or aspect_ratio <= 0:
        return None
    cl_mp = float(np.sqrt(3.0 * np.pi * oswald_e * aspect_ratio * cd0))
    if cl_mp <= 0:
        return None
    weight_n = mass_kg * g
    return float(np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_mp)))


def _min_sink_rate(
    mass_kg: float,
    s_ref_m2: float,
    cd0: float,
    aspect_ratio: float | None,
    rho: float = 1.225,
    g: float = 9.81,
    oswald_e: float = 0.8,
) -> float | None:
    """Sea-level minimum sink rate w_min [m/s] — vertical speed at V_min_sink.

    gh-692: the value pilots read off the speed polar as "wieviel Höhe
    verliere ich pro Sekunde am besten?". Derived in closed form from
    Anderson §6.7.2 at the min-power point:

        C_L_mp = sqrt(3·π·e·AR·C_D0)
        C_D_mp = 4·C_D0   (induced drag = 3 × parasitic at this point)
        (C_D/C_L)_mp = 4·sqrt(C_D0 / (3·π·e·AR))
        w_min = V_min_sink · (C_D/C_L)_mp

    Same degenerate-input contract as ``_min_sink_speed`` (no wing,
    zero AR, zero CD0 → None).
    """
    v_ms = _min_sink_speed(mass_kg, s_ref_m2, cd0, aspect_ratio, rho=rho, g=g, oswald_e=oswald_e)
    if v_ms is None:
        return None
    # aspect_ratio is guaranteed > 0 here (None / ≤ 0 already returned None above).
    cd_over_cl = 4.0 * float(np.sqrt(cd0 / (3.0 * np.pi * oswald_e * aspect_ratio)))
    return float(v_ms * cd_over_cl)


def _cl_to_alpha_deg(
    cl: float,
    cl_alpha_per_rad: float | None,
    alpha_0_deg: float | None,
) -> float | None:
    """Convert a lift coefficient to angle of attack [degrees] via the linear lift curve.

    The linear lift curve is: CL = cl_alpha * (alpha - alpha_0)
    Inverted: alpha = alpha_0 + CL / cl_alpha [radians] → converted to degrees.

    gh-871: used to annotate characteristic speeds with their operating α.

    Returns None when cl_alpha_per_rad or alpha_0_deg are absent/invalid.
    """
    if cl_alpha_per_rad is None or alpha_0_deg is None:
        return None
    if cl_alpha_per_rad <= 0:
        return None
    alpha_0_rad = math.radians(alpha_0_deg)
    alpha_rad = alpha_0_rad + cl / cl_alpha_per_rad
    return math.degrees(alpha_rad)


def _picard_iterate_speed(
    v0: float | None,
    speed_fn,
    speed_fn_kwargs: dict,
    polar_table: list,
    mac_m: float,
    rho: float = 1.225,
    picard_tolerance: float = 0.05,
) -> float | None:
    """One Picard iteration pass for Re-dependent speed computations (gh-493 I2).

    Computes V_1 by evaluating ``speed_fn`` with cd0/e looked up at the
    scalar V_0.  If |V_1 - V_0| / V_0 < ``picard_tolerance`` (5%), accepts
    V_1.  Otherwise logs a warning and also accepts V_1 (one-pass policy).

    Parameters
    ----------
    v0              : Initial speed [m/s] from scalar-polar computation.
                      Returns ``None`` immediately if v0 is None.
    speed_fn        : One of ``_min_drag_speed``, ``_min_sink_speed``,
                      ``_max_level_speed`` — must accept keyword arguments
                      ``cd0`` and ``oswald_e`` plus ``**speed_fn_kwargs``.
    speed_fn_kwargs : Dict of additional kwargs forwarded to ``speed_fn``
                      (excludes ``cd0`` and ``oswald_e`` which are injected here).
    polar_table     : list[dict] from ``build_re_table``.
    mac_m           : Mean aerodynamic chord [m].
    rho             : Air density [kg/m³].
    picard_tolerance: Relative change threshold below which convergence is
                      declared (default 5 %).

    Returns
    -------
    V_1 (Picard-iterated speed) or None if ``speed_fn`` returns None.
    """
    if v0 is None:
        return None
    if not polar_table or mac_m <= 0:
        return v0

    from app.services.polar_re_table_service import lookup_cd0_at_v, lookup_e_oswald_at_v

    cd0_at_v0 = lookup_cd0_at_v(v_mps=v0, table=polar_table, mac_m=mac_m, rho=rho)
    e_at_v0 = lookup_e_oswald_at_v(v_mps=v0, table=polar_table)

    v1 = speed_fn(cd0=cd0_at_v0, oswald_e=e_at_v0, **speed_fn_kwargs)

    if v1 is None:
        return v0

    rel_change = abs(v1 - v0) / max(abs(v0), 1e-6)
    if rel_change >= picard_tolerance:
        logger.warning(
            "Picard iteration: speed changed by %.1f %% (V_0=%.2f m/s → V_1=%.2f m/s). "
            "Re table may not be representative at this V. Accepting V_1 (one-pass policy).",
            rel_change * 100.0,
            v0,
            v1,
        )

    return v1


def _cache_context(db: Session, aircraft: AeroplaneModel, context: dict[str, Any]) -> None:
    """Write computation context JSON to the aeroplane row."""
    aircraft.assumption_computation_context = context
    db.flush()
