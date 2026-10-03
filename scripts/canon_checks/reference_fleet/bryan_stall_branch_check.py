"""Which canon optimisation problems fall into the post-stall local optimum? (BRYAN, 2026-10-03)

The aircraft lift curve has its first C_L peak at alpha_peak and a second, lower local maximum
on the post-stall plateau. Each problem is solved twice:
  A  as solved so far (generic start, alpha <= 25 deg)
  B  restricted to the pre-stall branch (alpha <= alpha_peak + 1 deg)
A problem is affected when A ends past alpha_peak or A and B disagree.
Same declared assumptions as bryan_stability_mass.py (thrust route A power-limited, n_lim = 3).
"""

import pathlib

import aerosandbox as asb
import aerosandbox.numpy as anp
import numpy as np

LIB = pathlib.Path(__file__).with_name("bryan_stability_mass.py")
ns = {"__file__": str(LIB)}
exec(compile(LIB.read_text().split("# --- run ---")[0], str(LIB), "exec"), ns)  # noqa: S102
plane, atm, TM, G, M0, aero = ns["plane"], ns["atm"], ns["TM"], ns["G"], ns["M0"], ns["aero"]
stall_branch_alpha = ns["stall_branch_alpha"]
N_LIM = 3.0


def solve(kind, a_max, a0=3.0, v0=10.0):
    o = asb.Opti()
    V = o.variable(init_guess=v0, lower_bound=1, upper_bound=40)
    a = o.variable(init_guess=a0, lower_bound=-8, upper_bound=a_max)
    r = aero(plane, V, a)
    T = TM({"V": V})
    m = M0
    if kind == "V_A (Manöver)":
        o.subject_to(r["L"] == N_LIM * m * G)
        o.minimize(V)
    elif kind in ("r_min (engste Kurve)", "omega_max (schnellste Kurve)"):
        n = o.variable(init_guess=1.5, lower_bound=1.0001, upper_bound=N_LIM)
        o.subject_to([r["L"] == n * m * G, T >= r["D"]])
        k = (n**2 - 1) ** 0.5
        if kind.startswith("r_min"):
            o.minimize(V**2 / (G * k))
        else:
            o.maximize(G * k / V)
    elif kind in ("V_x (steilstes Steigen)", "V_y (bestes Steigen)"):
        gam = o.variable(init_guess=0.3, lower_bound=0, upper_bound=np.pi / 2)
        o.subject_to([r["L"] == m * G * anp.cos(gam), T - r["D"] >= m * G * anp.sin(gam)])
        o.maximize(gam if kind.startswith("V_x") else V * anp.sin(gam))
    elif kind == "V_mp (geringstes Sinken)":
        o.subject_to(r["L"] == m * G)
        o.minimize(r["D"] * V)
    elif kind == "V_md (geringster Widerstand)":
        o.subject_to(r["L"] == m * G)
        o.minimize(r["D"])
    elif kind == "V_max":
        o.subject_to([r["L"] == m * G, T >= r["D"]])
        o.maximize(V)
    s = o.solve(verbose=False, max_iter=600)
    return float(s(V)), float(s(a))


a_pk1 = stall_branch_alpha(M0)
a_pkn = stall_branch_alpha(N_LIM * M0)
print(f"erstes C_L-Maximum: alpha = {a_pk1:.1f}° bei 1 g, {a_pkn:.1f}° bei {N_LIM:.0f} g\n")
print(f"{'Problem':30s} {'A: V / alpha':>18s} {'B: V / alpha':>18s}  Befund")
for kind in ("V_A (Manöver)", "r_min (engste Kurve)", "omega_max (schnellste Kurve)",
             "V_x (steilstes Steigen)", "V_y (bestes Steigen)", "V_mp (geringstes Sinken)",
             "V_md (geringster Widerstand)", "V_max"):
    a_pk = a_pkn if kind.startswith(("V_A", "r_min", "omega")) else a_pk1
    res = {}
    for tag, a_max in (("A", 25.0), ("B", a_pk + 1.0)):
        try:
            res[tag] = solve(kind, a_max)
        except RuntimeError:
            res[tag] = None
    fa = f"{res['A'][0]:6.2f} / {res['A'][1]:5.1f}°" if res["A"] else "gescheitert"
    fb = f"{res['B'][0]:6.2f} / {res['B'][1]:5.1f}°" if res["B"] else "gescheitert"
    if not res["A"] or not res["B"]:
        verdict = "prüfen"
    elif res["A"][1] > a_pk + 1.0:
        verdict = "BETROFFEN: A jenseits des Abrisses"
    elif abs(res["A"][0] - res["B"][0]) > 0.02:
        verdict = "BETROFFEN: A und B weichen ab"
    else:
        verdict = "unauffällig"
    print(f"{kind:30s} {fa:>18s} {fb:>18s}  {verdict}")
