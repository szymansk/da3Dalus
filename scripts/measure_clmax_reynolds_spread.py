"""Measure the Reynolds-number inconsistency of C_L,max across the fleet (gh-1142).

Acceptance item 1 of gh-1142: *"Measure first: sweep C_L,max(V) instead of max over all,
and report the spread between the low and high end for real aircraft."*

For every aeroplane in the database this replays what the application does — the coarse
alpha sweep, then ``_fine_sweep_cl_max`` over its velocity x alpha grid — and then asks
the question the approved canon entry demands (``canon/formulas/stall-speed.md``):

    Is the C_L,max that sizes V_stall the C_L,max that holds *at* V_stall?

It also records whether the grid's lower bound, ``max(v_cruise * 0.5, 3.0)``, actually
brackets the stall speed. That is the second acceptance item, and the numbers suggest it
is what governs how large the error becomes.

Run:  poetry run python scripts/measure_clmax_reynolds_spread.py
"""

from __future__ import annotations

import math
import sys

import numpy as np

G = 9.81
RHO = 1.225


def _cl_max_at(plane, velocity_mps, stall_alpha_deg, config):
    """C_L,max at a single velocity — that is, at one Reynolds number."""
    import aerosandbox as asb

    alphas = np.arange(
        stall_alpha_deg - config.fine_alpha_margin_deg,
        stall_alpha_deg + config.fine_alpha_margin_deg + 0.01,
        config.fine_alpha_step_deg,
    )
    op = asb.OperatingPoint(velocity=np.full_like(alphas, float(velocity_mps)), alpha=alphas)
    res = asb.AeroBuildup(airplane=plane, op_point=op, xyz_ref=plane.xyz_ref).run()
    return float(np.max(np.atleast_1d(np.asarray(res["CL"], dtype=float))))


def main() -> int:
    from app.db.session import SessionLocal
    from app.models.aeroplanemodel import AeroplaneModel
    from app.services.assumption_compute_service import (
        _build_asb_airplane,
        _coarse_alpha_sweep,
        _fine_sweep_cl_max,
        _load_effective_assumption,
        _load_flight_profile_speeds,
        _load_or_create_config,
        _select_main_wing,
    )

    db = SessionLocal()
    rows = []
    try:
        aircraft_list = db.query(AeroplaneModel).all()
        print(f"{len(aircraft_list)} aircraft in the database\n")
        header = (
            f"{'aircraft':22s} {'m[kg]':>6s} {'S[m2]':>6s} {'grid_lo':>8s} {'V_S':>7s} "
            f"{'brackets':>9s} {'CLmax_app':>10s} {'CLmax@VS':>9s} {'spread':>8s}"
        )
        print(header)
        print("-" * len(header))

        for aircraft in aircraft_list:
            name = (aircraft.name or f"id={aircraft.id}")[:22]
            try:
                plane = _build_asb_airplane(aircraft)
                main_wing = _select_main_wing(plane)
                if main_wing is None:
                    print(f"{name:22s} — no wing")
                    continue
                plane.s_ref = float(main_wing.area())
                plane.c_ref = float(main_wing.mean_aerodynamic_chord())
                plane.b_ref = float(main_wing.span())

                aid = int(aircraft.id)
                mass = _load_effective_assumption(db, aid, "mass")
                if not mass or mass <= 0:
                    print(f"{name:22s} — no mass assumption")
                    continue

                config = _load_or_create_config(db, aid)
                v_cruise, v_max, _ = _load_flight_profile_speeds(db, aircraft)

                stall_alpha = _coarse_alpha_sweep(plane, v_cruise, config)
                cl_app, *_ = _fine_sweep_cl_max(plane, stall_alpha, v_cruise, v_max, config)
                if not math.isfinite(cl_app) or cl_app <= 0:
                    print(f"{name:22s} — no usable C_L,max")
                    continue

                s_ref = float(plane.s_ref)
                v_stall_app = math.sqrt(2.0 * mass * G / (RHO * s_ref * cl_app))
                cl_at_stall = _cl_max_at(plane, v_stall_app, stall_alpha, config)
                v_stall_true = math.sqrt(2.0 * mass * G / (RHO * s_ref * cl_at_stall))
                spread = (v_stall_true - v_stall_app) / v_stall_app

                grid_lo = max(v_cruise * 0.5, 3.0)
                brackets = "yes" if grid_lo <= v_stall_app else "NO"
                rows.append((name, spread, brackets, grid_lo, v_stall_app))
                print(
                    f"{name:22s} {mass:6.2f} {s_ref:6.3f} {grid_lo:8.2f} {v_stall_app:7.2f} "
                    f"{brackets:>9s} {cl_app:10.4f} {cl_at_stall:9.4f} {100 * spread:+7.1f}%"
                )
            except Exception as exc:  # noqa: BLE001 — a survey must not stop at one aircraft
                print(f"{name:22s} — skipped: {type(exc).__name__}: {str(exc)[:56]}")

        if rows:
            spreads = [abs(r[1]) for r in rows]
            missed = [r for r in rows if r[2] == "NO"]
            print(f"\n{len(rows)} aircraft measured")
            print(
                f"  spread   median {100 * float(np.median(spreads)):.1f} %   "
                f"max {100 * max(spreads):.1f} %   "
                f"over 2 % : {sum(1 for s in spreads if s > 0.02)}"
            )
            print(f"  grid does NOT bracket the stall speed: {len(missed)} of {len(rows)}")
            if missed:
                worst = sorted(missed, key=lambda r: -abs(r[1]))[:5]
                for n, s, _brackets, lo, vs in worst:
                    print(f"    {n:22s} grid starts {lo:.2f} m/s, stall at {vs:.2f} m/s"
                          f"  -> {100 * s:+.1f} %")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
