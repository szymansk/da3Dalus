"""Plausibility test of the proposed fuzzy propagation (2026-10-03) on BRYAN.

Chain:  cause(s) -> x_NP -> x_CG,first-flight = x_NP - SM_t*MAC -> static margin at the plan CG
                      \\-> forward trim margin  m_fwd = x_CG,first-flight - x_fwd(K)
Causes:
  * method choice for x_NP (worlds): textbook (eta 0.9), Pappas, AVL  -> np_methods.py / AVL value
  * tail effectiveness K in the barycentre form, as a continuous cause that ALSO drives the forward trim
    limit (a weaker tail trims less: x_fwd moves aft).  Bounds 0.24..0.32 around the textbook K = 0.27.

Checks:
  1. dependency problem: naive interval-on-interval vs propagation of the cause through the whole chain
  2. vertex method vs dense sampling of the cause (monotonicity)
x_fwd(K) is a deliberately simple stand-in (linear in tail authority) to test the PROPAGATION, not a
canon value: x_fwd = x_fwd0 + c*(K0 - K) with x_fwd0 = 14.3 % MAC (mass-envelope, AeroBuildup) and
c chosen so a 30 % weaker tail moves it 6 % MAC aft.
"""

import runpy
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
ns = runpy.run_path(str(HERE / "np_methods.py"), run_name="lib")
g = ns["geometry"](HERE / "bryan" / "bryan.airplane.json", "Hoehenleitwerk")
bary = ns["bary"]
mac, le, x_cg_plan = g["mac"], g["le"], g["x_cg"]
pct = lambda x: 100 * (x - le) / mac  # noqa: E731
SM_T = 0.10
K0, KLO, KHI = 0.27, 0.24, 0.32
X_FWD0 = le + 0.143 * mac
C = 0.06 * mac / (0.3 * K0)


def chain(x_np, k):
    x_cg1 = x_np - SM_T * mac
    x_fwd = X_FWD0 + C * (K0 - k)
    return {"x_NP": pct(x_np), "SM_plan": 100 * (x_np - x_cg_plan) / mac,
            "x_CG,1": pct(x_cg1), "m_fwd": 100 * (x_cg1 - x_fwd) / mac}


print("== 1. Methodenwahl als Welten (Kette je Welt)")
worlds = {"Lehrbuch η0,9": bary(g, 0.9 * ns["methods"](g)[2]), "Pappas": bary(g, ns["methods"](g)[1]),
          "AVL": le + 0.329 * mac}
res = {w: chain(x, K0) for w, x in worlds.items()}
for w, r in res.items():
    print(f"  {w:14s} " + "  ".join(f"{k} {v:6.1f}" for k, v in r.items()))
for k in ("x_NP", "SM_plan", "x_CG,1", "m_fwd"):
    v = sorted(r[k] for r in res.values())
    print(f"  -> {k:8s} [{v[0]:6.1f}, {np.median(v):6.1f}, {v[-1]:6.1f}]")

print("\n== 2. Abhängigkeitsproblem: Leitwerkswirksamkeit K treibt x_NP UND x_fwd")
xs = {k: bary(g, k) for k in (KLO, KHI)}
x_np_iv = sorted(pct(x) for x in xs.values())
x_cg1_iv = [x_np_iv[0] - 100 * SM_T, x_np_iv[1] - 100 * SM_T]
x_fwd_iv = sorted(pct(X_FWD0 + C * (K0 - k)) for k in (KLO, KHI))
naive = [x_cg1_iv[0] - x_fwd_iv[1], x_cg1_iv[1] - x_fwd_iv[0]]
prop = sorted(chain(bary(g, k), k)["m_fwd"] for k in (KLO, KHI))
print(f"  naiv Intervall auf Intervall:  Trimmreserve m_fwd [{naive[0]:5.1f}, {naive[1]:5.1f}] % MAC")
print(f"  Ursache durch die Kette:       Trimmreserve m_fwd [{prop[0]:5.1f}, {prop[1]:5.1f}] % MAC")

print("\n== 3. Eckpunkte gegen dichte Abtastung (Monotonie)")
dense = [chain(bary(g, k), k)["m_fwd"] for k in np.linspace(KLO, KHI, 201)]
print(f"  Eckpunkte: [{min(prop):5.2f}, {max(prop):5.2f}]   dicht: [{min(dense):5.2f}, {max(dense):5.2f}]")

print("\n== 2b. Abhängigkeit mit gegenläufiger Wirkung: Stabilitätsmaß des Erstflug-Schwerpunkts")
np_lo, np_hi = res["AVL"]["x_NP"], res["Lehrbuch η0,9"]["x_NP"]
cg_lo, cg_hi = np_lo - 100 * SM_T, np_hi - 100 * SM_T
print(f"  naiv (x_NP-Intervall minus x_CG,1-Intervall): [{np_lo - cg_hi:5.1f}, {np_hi - cg_lo:5.1f}] % MAC")
sm1 = sorted(r["x_NP"] - r["x_CG,1"] for r in res.values())
print(f"  je Welt durch die Kette:                      [{sm1[0]:5.1f}, {sm1[-1]:5.1f}] % MAC  (exakt 10 per Konstruktion)")
