"""Neutral point by the RC-practice geometric method, against AeroBuildup and AVL (2026-10-03).

rcplanedesigner, "Airplane balance — build the neutral point" (vault page
airplane-balance-finding-the-first-flight-cg--build-the-neutral-point): the NP is the barycentre of the
wing aerodynamic centre weighted by the wing area and the horizontal-tail aerodynamic centre weighted by
HALF the tail area; then shifted forward by 5 % MAC for the fuselage. Aerodynamic centres at 25 % of each
surface's MAC. For the V-tail the horizontal share is the projected area A·cos²(nu) (Drela, BAENDER §3b).
"""

import json
import pathlib

import aerosandbox as asb
import numpy as np

HERE = pathlib.Path(__file__).parent


def surfaces(path, af):
    d = json.loads(path.read_text())
    out = []
    for name, w in d["wings"].items():
        wing = asb.Wing(name=name, symmetric=w["symmetric"],
                        xsecs=[asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], airfoil=af) for x in w["x_secs"]])
        out.append(wing)
    return d, out


def np_rc(main, tails):
    mac = main.mean_aerodynamic_chord()
    x_ac_w = main.aerodynamic_center()[0]
    num, den = main.area() * x_ac_w, main.area()
    for t, s_h in tails:
        num += 0.5 * s_h * t.aerodynamic_center()[0]
        den += 0.5 * s_h
    x_np = num / den - 0.05 * mac
    return x_np, mac, x_ac_w - 0.25 * mac


af = asb.Airfoil("naca0010")
rows = []
d, ws = surfaces(HERE / "bryan" / "bryan.airplane.json", af)
main, hlw = ws[0], [w for w in ws if w.name == "Hoehenleitwerk"][0]
rows.append(("BRYAN", d["xyz_ref"][0], np_rc(main, [(hlw, hlw.area())]), 43.7, 32.9))
d, ws = surfaces(HERE / "ehawk" / "ehawk.airplane.json", af)
main, vt = ws[0], ws[1]
z = [x["xyz_le"][2] for x in d["wings"]["V-Leitwerk"]["x_secs"]]
y = [x["xyz_le"][1] for x in d["wings"]["V-Leitwerk"]["x_secs"]]
nu = np.arctan2(z[-1] - z[0], y[-1] - y[0])
rows.append(("e-Hawk", d["xyz_ref"][0], np_rc(main, [(vt, vt.area() * np.cos(nu) ** 2)]), 58.4, 48.8))

print(f"{'':8s} {'RC-Methode':>11s} {'AVL':>6s} {'AeroBuildup':>12s} {'Plan-SP':>8s}  SM (RC-Methode)")
for name, x_cg, (x_np, mac, le), ab, avl in rows:
    pn, pc = 100 * (x_np - le) / mac, 100 * (x_cg - le) / mac
    print(f"{name:8s} {pn:10.1f}% {avl:5.1f}% {ab:11.1f}% {pc:7.1f}%   {100*(x_np-x_cg)/mac:5.1f} %")
