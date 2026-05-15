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
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.polar_by_config import ParabolicPolar
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
        # _fine_sweep_cl_max returns (cl_max, cl_array, cd_array, v_array) so that
        # the parabolic polar fit (gh-486) and Re-table builder (gh-493) can
        # consume the raw sweep data without extra AeroBuildup invocations.
        fine_result = _fine_sweep_cl_max(asb_airplane, stall_alpha, v_cruise, v_max, config)
        cl_max, sweep_cl_arr, sweep_cd_arr, sweep_v_arr = fine_result
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
    _cd0_fit, e_oswald_fit, e_r2 = _fit_parabolic_polar(
        np.asarray(sweep_cl_arr, dtype=float),
        np.asarray(sweep_cd_arr, dtype=float),
        ar=aspect_ratio if aspect_ratio is not None else 0.0,
        cl_max=cl_max_effective_for_fit,
        cd0_stability=cd0,
    )
    e_oswald_fallback = e_oswald_fit is None
    e_oswald_effective = e_oswald_fit if e_oswald_fit is not None else 0.8
    # -----------------------------------------------------------------------

    # --- gh-526 / epic gh-525 C1: per-configuration parabolic polar -------
    # Run AeroBuildup once per high-lift configuration so V_s0 (landing)
    # and V_s1 (clean) reflect physics instead of the 0.95 / 0.90 heuristic
    # the OPG used historically (audit §5.5).
    polar_clean = ParabolicPolar(
        cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
        e_oswald=round(e_oswald_fit, 4) if e_oswald_fit is not None else None,
        cl_max=round(cl_max, 4),
        e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
        e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        flap_deflection_deg=0.0,
        provenance="aerobuildup",
    )

    ted_max = _extract_flap_ted_max(aircraft)
    if ted_max is None:
        # No flap geometry — fallback path: clone clean to takeoff & landing.
        polar_takeoff = polar_clean.model_copy(update={"provenance": "no_flap_geometry"})
        polar_landing = polar_clean.model_copy(update={"provenance": "no_flap_geometry"})
    else:
        delta_to = min(15.0, float(ted_max))
        delta_ldg = min(30.0, float(ted_max))
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
            # Defensive: a flap-deflected sweep failure must not corrupt
            # the clean polar that is already correctly computed.
            logger.exception(
                "Flap-deflected AeroBuildup failed for aircraft %s — falling back to clean polar",
                aeroplane_uuid,
            )
            polar_takeoff = polar_clean.model_copy(update={"provenance": "fit_rejected"})
            polar_landing = polar_clean.model_copy(update={"provenance": "fit_rejected"})

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

    # If the user hasn't set a flight profile, suggest V_md as the
    # cruise speed (best L/D = best range for prop aircraft). Once the
    # user creates a profile and sets cruise_speed_mps, we respect it.
    v_cruise_effective = v_md if (not user_set_cruise and v_md is not None) else v_cruise
    cruise_is_auto = not user_set_cruise and v_md is not None

    # CL_α from linear-range alpha-sweep (gh-487 — gust envelope).
    # Regression over α ∈ [-2°, +6°] with R² > 0.995 quality gate.
    # Cached as cl_alpha_per_rad; downstream compute_vn_curve uses it
    # for the Pratt-Walker gust alleviation computation.
    cl_alpha_per_rad = _extract_cl_alpha_from_linear_sweep(asb_airplane, v_cruise)

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
        "is_glider": is_glider,
        "reynolds": round(re),
        "mac_m": round(mac, 4),
        "s_ref_m2": round(s_ref, 4),
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
        "e_oswald": round(e_oswald_fit, 4) if e_oswald_fit is not None else None,
        "e_oswald_r2": round(e_r2, 4) if e_r2 is not None else None,
        "e_oswald_quality": _classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        "e_oswald_fallback_used": e_oswald_fallback,
        # Linear-range CL_α from α-sweep (gh-487) — consumed by compute_vn_curve for gust loads
        "cl_alpha_per_rad": round(cl_alpha_per_rad, 4) if cl_alpha_per_rad is not None else None,
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
    asb_airplane,
    flap_deflection_deg: float,
    v_cruise: float,
    v_max: float,
    config,
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
        # Belt-and-braces: caller should have routed to fallback already.
        return ParabolicPolar(
            cl_max=0.0,
            flap_deflection_deg=0.0,
            provenance="no_flap_geometry",
        )
    deflected = asb_airplane.with_control_deflections({flap_name: flap_deflection_deg})
    stall_alpha = _coarse_alpha_sweep(deflected, v_cruise, config)
    cl_max, cl_arr, cd_arr, _v_arr = _fine_sweep_cl_max(
        deflected, stall_alpha, v_cruise, v_max, config
    )
    _cd0_fit, e_oswald_fit, e_r2 = _fit_parabolic_polar(
        np.asarray(cl_arr, dtype=float),
        np.asarray(cd_arr, dtype=float),
        ar=aspect_ratio if aspect_ratio is not None else 0.0,
        cl_max=cl_max_effective_for_fit if cl_max_effective_for_fit else cl_max,
        cd0_stability=cd0_stability,
    )
    return ParabolicPolar(
        cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
        e_oswald=round(e_oswald_fit, 4) if e_oswald_fit is not None else None,
        cl_max=round(float(cl_max), 4),
        e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
        e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
        flap_deflection_deg=float(flap_deflection_deg),
        provenance="aerobuildup",
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
    """Returns approximate stall_alpha_deg (alpha where CL peaks)."""
    import aerosandbox as asb

    alphas = np.arange(
        config.coarse_alpha_min_deg,
        config.coarse_alpha_max_deg + 0.01,
        config.coarse_alpha_step_deg,
    )
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cls: list[float] = []
    for a in alphas:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
        r = abu.run()
        cls.append(_extract_scalar(r, "CL", default=0.0))
    return float(alphas[int(np.argmax(cls))])


def _fine_sweep_cl_max(
    asb_airplane,
    stall_alpha_deg: float,
    v_cruise: float,
    v_max: float,
    config: AircraftComputationConfigModel,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Returns (CL_max, cl_array, cd_array, v_array) from a fine alpha × velocity sweep.

    The returned CL, CD, and V arrays span the full swept range.  CL and CD are
    used by the parabolic polar fitter (gh-486) to derive the Oswald efficiency
    factor.  V is additionally used by the Re-table builder (gh-493) to bin
    samples by velocity band.

    Note: the v_array is the velocity at which each (CL, CD) sample was taken.
    It has the same length as cl_array and cd_array.
    """
    import aerosandbox as asb

    alpha_min = stall_alpha_deg - config.fine_alpha_margin_deg
    alpha_max = stall_alpha_deg + config.fine_alpha_margin_deg
    alphas = np.arange(alpha_min, alpha_max + 0.01, config.fine_alpha_step_deg)

    v_stall_approx = max(v_cruise * 0.5, 3.0)
    velocities = np.linspace(v_stall_approx, v_max, config.fine_velocity_count)

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cl_max = -float("inf")
    cl_list: list[float] = []
    cd_list: list[float] = []
    v_list: list[float] = []
    for v in velocities:
        for a in alphas:
            op = asb.OperatingPoint(velocity=float(v), alpha=float(a))
            abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
            r = abu.run()
            cl = _extract_scalar(r, "CL", default=0.0)
            cd = _extract_scalar(r, "CD", default=0.0)
            cl_list.append(cl)
            cd_list.append(cd)
            v_list.append(float(v))
            if cl > cl_max:
                cl_max = cl
    return (
        float(cl_max),
        np.asarray(cl_list, dtype=float),
        np.asarray(cd_list, dtype=float),
        np.asarray(v_list, dtype=float),
    )


def _extract_cl_alpha_from_linear_sweep(
    asb_airplane,
    v_cruise: float,
    alpha_min_deg: float = -2.0,
    alpha_max_deg: float = 6.0,
    alpha_step_deg: float = 1.0,
    r2_threshold: float = 0.995,
) -> float | None:
    """CL_α from a linear-range alpha-sweep at cruise speed (gh-487).

    Runs AeroBuildup at α ∈ [alpha_min_deg, alpha_max_deg] (default [-2°, +6°])
    and fits CL = CL_α·α + CL_0 with ordinary least squares.

    Quality gate: if R² < r2_threshold (default 0.995), the lift curve is
    nonlinear in this range (early stall, control surface interaction, etc.)
    and cl_alpha_per_rad is returned as None.  The downstream gust computation
    will then fall back to Helmbold-Diederich.

    Returns CL_α in rad⁻¹ (radians, not degrees).

    Sources: gh-487 spec; Anderson 6e §5.3; FAR-25.341(a)(2).
    """
    import aerosandbox as asb

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    alphas_deg = np.arange(alpha_min_deg, alpha_max_deg + 0.01, alpha_step_deg)
    alphas_rad = np.deg2rad(alphas_deg)

    cls: list[float] = []
    for a in alphas_deg:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
        r = abu.run()
        cls.append(_extract_scalar(r, "CL", default=float("nan")))

    alphas_arr = np.array(alphas_rad)
    cls_arr = np.array(cls)

    # Discard NaN points (convergence failures)
    mask = np.isfinite(cls_arr)
    if mask.sum() < 3:
        logger.warning(
            "CL_α extraction: fewer than 3 valid data points in α ∈ [%.0f°, %.0f°] "
            "— skipping (will fall back to Helmbold).",
            alpha_min_deg,
            alpha_max_deg,
        )
        return None

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
        return None

    if cl_alpha_fit <= 0:
        logger.warning(
            "CL_α extraction: fitted CL_α=%.4f ≤ 0 (degenerate geometry?). "
            "Setting cl_alpha_per_rad=None.",
            cl_alpha_fit,
        )
        return None

    logger.debug(
        "CL_α extraction: CL_α=%.4f rad⁻¹, CL_0=%.4f, R²=%.4f (α ∈ [%.0f°, %.0f°]).",
        cl_alpha_fit,
        cl_0,
        r2,
        alpha_min_deg,
        alpha_max_deg,
    )
    return cl_alpha_fit


def _extract_scalar(result: Any, key: str, *, default: float) -> float:
    """Extract a CL/CD scalar from raw AeroBuildup result (dict or object)."""
    if isinstance(result, dict):
        val = result.get(key)
    else:
        val = getattr(result, key, None)
    scalar = _scalar(val)
    return float(scalar) if scalar is not None else default


def _fit_parabolic_polar(
    cl: np.ndarray,
    cd: np.ndarray,
    ar: float,
    cl_max: float,
    cd0_stability: float,
) -> tuple[float | None, float | None, float | None]:
    """Fit C_D = C_D0 + C_L²/(π·e·AR) to raw polar data via OLS.

    Reference: Anderson §6.1.2 (drag polar), §6.7.2 ((L/D)_max derivation).

    Window: linear region of the polar in CL-space:
        C_L_lo = max(0.10, 0.10 · C_L,max)
        C_L_hi = 0.85 · C_L,max

    Requires ≥ 6 sample points in the window. All rejection guards must
    pass; otherwise returns (None, None, None) and emits a logger.warning.

    Rejection guards:
    - ≥ 6 points in window
    - k > 0 (slope positive — physically required)
    - cd0_fit > 0 (positive intercept)
    - e_oswald ∈ (0.4, 1.0] (physical range)
    - dCD/d(CL²) monotonically non-decreasing (laminar-bubble guard)
    - |cd0_fit - cd0_stability| / cd0_stability ≤ 0.20 (sanity check)

    Returns:
        (cd0_fit, e_oswald, r2) on success, or (None, None, None) on rejection.
    """
    if ar is None or ar <= 0:
        logger.warning("polar fit rejected: invalid aspect ratio %r", ar)
        return None, None, None
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
        return None, None, None

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
        return None, None, None

    # OLS fit: C_D = k · C_L² + cd0  (numpy returns highest-degree first)
    k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)

    if k <= 0:
        logger.warning("polar fit rejected: non-positive slope k=%.6f (requires k>0)", k)
        return None, None, None

    if cd0_fit <= 0:
        logger.warning("polar fit rejected: non-positive cd0_fit=%.6f (requires cd0>0)", cd0_fit)
        return None, None, None

    e_oswald = 1.0 / (np.pi * ar * k)

    if not (0.4 < e_oswald <= 1.0):
        logger.warning(
            "polar fit rejected: e_oswald=%.4f outside physical range (0.4, 1.0]",
            e_oswald,
        )
        return None, None, None

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
            return None, None, None

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
    return float(cd0_fit), float(e_oswald), float(r2)


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
