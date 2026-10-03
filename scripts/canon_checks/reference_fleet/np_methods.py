"""Neutral point of the reference fleet by every documented RC / textbook method (2026-10-03).

All methods are the barycentre form  x_NP = (S_w*x_ac,w + K*S_h*x_ac,h) / (S_w + K*S_h)  (+ fuselage
shift), differing only in the tail weight K and the fuselage term, except Lennon's two rules.
Sources (verbatim formulas collected in NP_NIEDRIGE_RE.md):
  A  rcplanedesigner "build the neutral point": K = 0.5, then -5 % MAC for the fuselage
  B  Harding, Model Aviation 08/2004 "Fundamentals of Stability": K = tail effectiveness, example 0.5;
     no fuselage term
  C  Pappas, Model Aviation 10/2009 "If It Flies": K = (1 - 3.24/AR_w) * [1/(1+2/AR_h)] / [1/(1+2/AR_w)]
  D  textbook (Sadraey Eq. 6.67 / downwash 2*a_w/(pi*AR)) with a = 2*pi*AR/(AR+2):
     K = eta * (1 - 4/(AR_w+2)) * [AR_h/(AR_h+2)] / [AR_w/(AR_w+2)], eta 1.0 and 0.9
  E  Krauss, stunthanger: K = 0.75 (flagged there as ignoring downwash)
  F  Lennon 1996 ch. 7: most AFT CG = [0.17 + 0.30 * V_H * HTE] * MAC, HTE 0.4-0.9 (not the NP)
  G  Lennon 1996 ch. 6: NP fixed at 35 % MAC
Measured for comparison: AVL (ASB thickness-rule CLAF) and AeroBuildup (no wing-tail downwash, #1154).
"""

import json
import pathlib

import aerosandbox as asb
import numpy as np

HERE = pathlib.Path(__file__).parent
AF = asb.Airfoil("naca0010")


def wing(w):
    return asb.Wing(symmetric=w["symmetric"],
                    xsecs=[asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], airfoil=AF) for x in w["x_secs"]])


def geometry(path, tail_name, v_tail=False):
    d = json.loads(path.read_text())
    m = wing(d["wings"]["Tragflaeche"])
    t = wing(d["wings"][tail_name])
    s_h, b_h = t.area(), t.span()
    if v_tail:  # horizontal projection (Drela): area A cos^2(nu), span projected
        xs = d["wings"][tail_name]["x_secs"]
        nu = np.arctan2(xs[-1]["xyz_le"][2] - xs[0]["xyz_le"][2], xs[-1]["xyz_le"][1] - xs[0]["xyz_le"][1])
        s_h = s_h * np.cos(nu) ** 2
        b_h = 2 * xs[-1]["xyz_le"][1]
    mac = m.mean_aerodynamic_chord()
    return dict(S=m.area(), AR=m.aspect_ratio(), mac=mac, x_acw=m.aerodynamic_center()[0], le=m.aerodynamic_center()[0] - 0.25 * mac,
                S_h=s_h, AR_h=b_h**2 / s_h, x_ach=t.aerodynamic_center()[0], x_cg=d["xyz_ref"][0])


def bary(g, k, shift=0.0):
    return (g["S"] * g["x_acw"] + k * g["S_h"] * g["x_ach"]) / (g["S"] + k * g["S_h"]) - shift * g["mac"]


def methods(g):
    arw, arh = g["AR"], g["AR_h"]
    k_pappas = (1 - 3.24 / arw) * (1 / (1 + 2 / arh)) / (1 / (1 + 2 / arw))
    k_text = (1 - 4 / (arw + 2)) * (arh / (arh + 2)) / (arw / (arw + 2))
    vh = g["S_h"] * (g["x_ach"] - g["x_acw"]) / (g["S"] * g["mac"])
    return vh, k_pappas, k_text, {
        "A rcplanedesigner (K 0,5, −5 %)": bary(g, 0.5, 0.05),
        "B Harding (K 0,5)": bary(g, 0.5),
        f"C Pappas (K {k_pappas:.2f})": bary(g, k_pappas),
        f"D Lehrbuch η 1,0 (K {k_text:.2f})": bary(g, k_text),
        f"D Lehrbuch η 0,9 (K {0.9*k_text:.2f})": bary(g, 0.9 * k_text),
        "E Krauss (K 0,75)": bary(g, 0.75),
        "G Lennon fest 35 %": g["le"] + 0.35 * g["mac"],
    }


fleet = [("BRYAN", geometry(HERE / "bryan" / "bryan.airplane.json", "Hoehenleitwerk"), 32.9, 43.7),
         ("e-Hawk", geometry(HERE / "ehawk" / "ehawk.airplane.json", "V-Leitwerk", v_tail=True), 48.8, 58.4)]
for name, g, avl, ab in fleet:
    vh, kp, kt, res = methods(g)
    le, mac = g["le"], g["mac"]

    def pct(x, le=le, mac=mac):
        return 100 * (x - le) / mac

    print(f"\n{name}: AR {g['AR']:.2f}, AR_h {g['AR_h']:.2f}, S_h/S {g['S_h']/g['S']:.3f}, V_H {vh:.3f}, "
          f"Plan-Schwerpunkt {pct(g['x_cg']):.1f} % MAC")
    print(f"  {'Methode':34s} {'NP % MAC':>9s} {'SM am Plan-SP':>14s}")
    for k, x in res.items():
        print(f"  {k:34s} {pct(x):8.1f}  {pct(x)-pct(g['x_cg']):12.1f} %")
    print(f"  {'AVL (gemessen)':34s} {avl:8.1f}  {avl-pct(g['x_cg']):12.1f} %")
    print(f"  {'AeroBuildup (gemessen)':34s} {ab:8.1f}  {ab-pct(g['x_cg']):12.1f} %")
    for hte in (0.4, 0.5, 0.9):
        print(f"  F Lennon hinterster Schwerpunkt, HTE {hte}: {100*(0.17+0.30*vh*hte):.1f} % MAC")
