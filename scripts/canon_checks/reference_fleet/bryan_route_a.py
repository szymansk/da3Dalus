"""BRYAN (variant A: Pichler Pulsar Micro 1510, 2000 KV, 45 W; APC 6x4E; 2S) through the
canon's thrust-dependent problems on route A (no R_m published -> fixed rpm, Q-PT-6).

Two readings of route A are computed side by side:
  * "A as built"  — rpm = K_v * U_bat, thrust at that rpm; the power ceiling caps only the
                    reported shaft power, not the thrust (powertrain_performance.py).
  * "A limited"   — rpm lowered until the propeller absorbs no more than the shaft-power
                    ceiling 45 W * 0.85 (motor rating x default motor efficiency, BR-PM3).
Assumptions, declared: APC 6x4E for the plan's "6 x 4"; U_bat = 2 * 3.7 V nominal;
n_lim = 3 (canon default); propeller drag beyond zero thrust not modelled (Q-PT-10).
"""
import sqlite3, runpy, sys, numpy as np
from scipy.optimize import brentq

ns = runpy.run_path(str(__import__("pathlib").Path(__file__).parent / "run_bryan.py"), run_name="lib")
asb, plane, m, g, atm = ns["asb"], ns["build"](True), ns["m"], ns["g"], ns["atm"]
rho = float(atm.density())

c = sqlite3.connect("db/test.db")
pid, D_in = c.execute("select id,diameter_in from propeller_polars where name='APC 6x4E'").fetchone()
rows = np.array(c.execute("select rpm,J,Ct,Cp from propeller_polar_samples where propeller_id=?", (pid,)).fetchall())
D, RPMS = D_in * 0.0254, np.unique(rows[:, 0])
def coef(rpm, J, col):
    i = int(np.clip(np.searchsorted(RPMS, rpm), 1, len(RPMS) - 1)); r0, r1 = RPMS[i - 1], RPMS[i]
    f = lambda r: np.interp(J, rows[rows[:, 0] == r, 1], rows[rows[:, 0] == r, col], right=0.0)
    w = np.clip((rpm - r0) / (r1 - r0), 0, 1); return (1 - w) * f(r0) + w * f(r1)
KV, U, P_SHAFT = 2000, 2 * 3.7, 45 * 0.85
RPM_FREE = KV * U
def thrust(V, limited):
    rpm = RPM_FREE
    if limited:
        P = lambda r: coef(r, V / (r / 60 * D), 3) * rho * (r / 60) ** 3 * D ** 5 - P_SHAFT
        if P(RPM_FREE) > 0: rpm = brentq(P, 3000, RPM_FREE)
    n = rpm / 60; return max(coef(rpm, V / (n * D), 2), 0) * rho * n ** 2 * D ** 4, rpm

Vg = np.linspace(0, 40, 81)
def model(limited):
    T = np.array([thrust(v, limited)[0] for v in Vg])
    return asb.InterpolatedModel({"V": Vg}, T, method="bspline"), T

N_LIM = 3.0
def solve(Tm, kind, V0=None):
    if kind == "Vmax" and V0 is None:   # multi-start: the level-speed maximum has a spurious low-speed branch past the stall
        best = None
        for v0 in (15, 25, 35):
            try:
                r_ = solve(Tm, kind, v0)
                if best is None or r_[0] > best[0]: best = r_
            except Exception: pass
        if best is None: raise RuntimeError("no start converged")
        return best
    o = asb.Opti()
    V = o.variable(init_guess=V0 or {"Vmax": 25, "VD": 30, "omega": 9, "radius": 9}.get(kind, 12), lower_bound=2, upper_bound=40)
    a = o.variable(init_guess=3, lower_bound=-10, upper_bound=25)
    r = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()
    T = Tm({"V": V})
    if kind in ("ROC", "gamma"):
        gam = o.variable(init_guess=0.5, lower_bound=0, upper_bound=np.pi / 2)
        o.subject_to([r["L"] == m * g * np.cos(gam), T - r["D"] >= m * g * np.sin(gam)])  # full throttle is the ceiling
        o.maximize(V * np.sin(gam) if kind == "ROC" else gam)
        s = o.solve(verbose=False, max_iter=500); return s(V), s(a), np.degrees(s(gam)), s(V * np.sin(gam))
    if kind in ("omega", "radius"):
        n = o.variable(init_guess=2.0, lower_bound=1.0001, upper_bound=N_LIM)
        o.subject_to([r["L"] == n * m * g, T >= r["D"]])
        k = (n ** 2 - 1) ** 0.5
        o.maximize(g * k / V) if kind == "omega" else o.minimize(V ** 2 / (g * k))
        s = o.solve(verbose=False, max_iter=500); return s(V), s(a), s(n), s(g * k / V), s(V ** 2 / (g * k))
    if kind == "Vmax":
        o.subject_to([r["L"] == m * g, T >= r["D"]]); o.maximize(V)
        s = o.solve(verbose=False, max_iter=500); return s(V), s(a)
    if kind == "VD":
        o.subject_to([r["L"] == 0, r["D"] == m * g + T]); o.minimize(V)
        s = o.solve(verbose=False, max_iter=500); return s(V), s(a)

for limited, label in ((False, "A wie gebaut (Schub bei Leerlaufdrehzahl)"), (True, "A leistungsbegrenzt (45 W x 0,85)")):
    Tm, T = model(limited)
    print(f"\n=== {label} ===")
    print(f"  Standschub {T[0]:.2f} N = {T[0]/g*1000:.0f} g  (T/W = {T[0]/(m*g):.2f}), Drehzahl im Stand {thrust(0, limited)[1]:.0f} U/min")
    for kind in (sys.argv[1:] or ("ROC", "gamma", "omega", "radius", "Vmax", "VD")):
        try:
            res = solve(Tm, kind)
        except Exception as e:
            print(f"  {kind:6s} Solver gescheitert: {type(e).__name__}"); continue
        if kind == "ROC":    print(f"  bestes Steigen   V_y = {res[0]:5.2f} m/s  gamma = {res[2]:5.1f} deg  ROC_max = {res[3]:5.2f} m/s" + ("  [senkrecht]" if res[2] > 89.9 else ""))
        if kind == "gamma":  print(f"  steilstes Steigen V_x = {res[0]:5.2f} m/s  gamma_max = {res[2]:5.1f} deg" + ("  [senkrecht]" if res[2] > 89.9 else ""))
        if kind == "omega":  print(f"  schnellste Kurve V = {res[0]:5.2f} m/s  n = {res[2]:4.2f}  omega = {np.degrees(res[3]):5.1f} deg/s" + ("  [n_lim aktiv]" if res[2] > N_LIM - 1e-3 else "") + (f"  [alpha {res[1]:.1f} deg]"))
        if kind == "radius": print(f"  engste Kurve     V = {res[0]:5.2f} m/s  n = {res[2]:4.2f}  r_min = {res[4]:5.2f} m" + ("  [n_lim aktiv]" if res[2] > N_LIM - 1e-3 else "") + (f"  [alpha {res[1]:.1f} deg]"))
        if kind == "Vmax":   print(f"  V_max = {res[0]:5.2f} m/s ({res[0]*3.6:.0f} km/h)  alpha = {res[1]:.2f} deg")
        if kind == "VD":     print(f"  V_D   = {res[0]:5.2f} m/s ({res[0]*3.6:.0f} km/h)  alpha = {res[1]:.2f} deg")
