"""Fleet comparison: extremal closures as asb.Opti problems vs the fixed-point iteration.

For every aeroplane in the database: stall speed by fixed-point iteration (alpha sweep at
V, take C_L,max, recompute V) and by optimisation (minimise V s.t. L = m g); plus the
minimum-drag and minimum-power problems, recording only whether they converge and whether
a bound is active at the optimum.

The database is test data. This measures how the method behaves on the aircraft that are
there; an anomaly is a question for the maintainer, not a conclusion.

Run:  PYTHONPATH=$PWD poetry run python scripts/canon_checks/fleet_opti_vs_fixed_point.py
"""
from __future__ import annotations
import math, sys, time
import numpy as np

V_LO, V_HI, A_LO, A_HI = 1.0, 60.0, -5.0, 25.0
G = 9.81

def fixed_point(asb, plane, atm, m):
    rho = float(atm.density()); S = float(plane.s_ref)
    alphas = np.arange(A_LO, A_HI + 0.01, 0.25)
    V = 12.0
    for it in range(1, 16):
        r = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=np.full_like(alphas, V), alpha=alphas)).run()
        cl = np.asarray(r["CL"], dtype=float)
        i = int(np.argmax(cl)); clmax = float(cl[i])
        if not math.isfinite(clmax) or clmax <= 0: return None, it, "no CL"
        Vn = math.sqrt(2 * m * G / (rho * S * clmax))
        edge = i in (0, len(alphas) - 1)
        if abs(Vn - V) / V < 1e-4:
            return Vn, it, "edge" if edge else "ok"
        V = Vn
    return V, 15, "no convergence"

def opti(asb, plane, atm, m, objective):
    o = asb.Opti()
    V = o.variable(init_guess=12, lower_bound=V_LO, upper_bound=V_HI)
    a = o.variable(init_guess=5, lower_bound=A_LO, upper_bound=A_HI)
    r = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()
    o.subject_to(r["L"] == m * G)
    o.minimize({"V": V, "D": r["D"], "DV": r["D"] * V}[objective])
    try:
        s = o.solve(verbose=False, max_iter=300)
    except Exception as exc:  # noqa: BLE001 — a survey records failures, it does not stop on them
        return None, None, f"fail: {type(exc).__name__}"
    v, al = float(s(V)), float(s(a))
    tol = 1e-3
    bound = []
    if abs(v - V_LO) < tol or abs(v - V_HI) < tol: bound.append("V")
    if abs(al - A_LO) < tol or abs(al - A_HI) < tol: bound.append("alpha")
    return v, al, ("bound " + "+".join(bound)) if bound else "ok"

def main():
    import aerosandbox as asb
    from app.db.session import SessionLocal
    from app.models.aeroplanemodel import AeroplaneModel
    from app.services.assumption_compute_service import (
        _build_asb_airplane, _load_effective_assumption, _select_main_wing)
    db = SessionLocal(); atm = asb.Atmosphere(altitude=0)
    rows = []
    hdr = f"{'aircraft':22s} {'m':>5s} {'V_S fp':>7s} {'it':>2s} {'V_S opt':>7s} {'a':>5s} {'diff%':>6s} {'stall':>11s} {'V_md':>6s} {'md':>9s} {'V_mp':>6s} {'mp':>9s} {'s':>4s}"
    print(hdr); print("-" * len(hdr))
    try:
        for ac in db.query(AeroplaneModel).all():
            name = (ac.name or f"id={ac.id}")[:22]
            try:
                plane = _build_asb_airplane(ac); w = _select_main_wing(plane)
                if w is None: print(f"{name:22s} — kein Flügel"); continue
                plane.s_ref = float(w.area()); plane.c_ref = float(w.mean_aerodynamic_chord()); plane.b_ref = float(w.span())
                m = _load_effective_assumption(db, int(ac.id), "mass")
                if not m or m <= 0: print(f"{name:22s} — keine Masse"); continue
                t0 = time.time()
                vf, it, sf = fixed_point(asb, plane, atm, m)
                vo, ao, so = opti(asb, plane, atm, m, "V")
                vmd, _, smd = opti(asb, plane, atm, m, "D")
                vmp, _, smp = opti(asb, plane, atm, m, "DV")
                dt = time.time() - t0
                diff = 100 * abs(vo - vf) / vf if (vo and vf) else float("nan")
                f = lambda x: f"{x:7.3f}" if x is not None else "    —  "
                g = lambda x: f"{x:6.2f}" if x is not None else "   —  "
                stall_state = so if sf == "ok" else f"{so}/fp:{sf}"
                print(f"{name:22s} {m:5.2f} {f(vf)} {it:2d} {f(vo)} {ao if ao is not None else float('nan'):5.1f} {diff:6.3f} {stall_state:>11s} {g(vmd)} {smd:>9s} {g(vmp)} {smp:>9s} {dt:4.1f}")
                rows.append(dict(name=name, diff=diff, so=so, sf=sf, smd=smd, smp=smp, vmd=vmd, vmp=vmp))
            except Exception as exc:  # noqa: BLE001
                print(f"{name:22s} — übersprungen: {type(exc).__name__}: {str(exc)[:50]}")
    finally:
        db.close()
    if rows:
        d = [r["diff"] for r in rows if math.isfinite(r["diff"])]
        print(f"\n{len(rows)} Flugzeuge gerechnet")
        if d: print(f"  V_S Opti gegen Fixpunkt: Median {np.median(d):.3f} %  Max {max(d):.3f} %  über 0,5 %: {sum(x>0.5 for x in d)}")
        for k, lab in (("so","Abriss"),("smd","geringster Widerstand"),("smp","geringste Leistung")):
            bad = [r["name"] for r in rows if r[k] != "ok"]
            print(f"  {lab:22s}: {len(rows)-len(bad)} ok, {len(bad)} auffällig {bad if bad else ''}")
        fpbad = [r["name"] for r in rows if r["sf"] != "ok"]
        print(f"  Fixpunkt selbst auffällig: {fpbad if fpbad else 'keiner'}")
        q = [r["vmp"]/r["vmd"] for r in rows if r["vmd"] and r["vmp"] and r["smd"]=="ok" and r["smp"]=="ok"]
        if q: print(f"  V_mp/V_md: Median {np.median(q):.2f}, Spanne {min(q):.2f}–{max(q):.2f}  (parabolisch: 0,76)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
