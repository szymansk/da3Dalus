"""BRYAN: steady roll rate at full aileron, AeroBuildup vs AVL (2026-10-03).

AeroBuildup's roll damping C_lp is 2.3x AVL's (bryan_lateral_avl.py). Whether that makes the roll
RATE wrong depends on the aileron moment too: if AeroBuildup overstates both (strip-wise, no induced
relief of an antisymmetric load), the errors partly cancel. This compares p*b/2V directly.

Point: approach 1.3 V_S (V_S = 5.29 m/s), L = m g, ailerons +-20 deg (1:1), steady roll (C_l = 0).
AVL: the model of bryan_aileron_differential.py (inviscid, original airfoil files).
AeroBuildup: ailerons as an antisymmetric control surface on the aileron segments.
"""

import pathlib
import runpy

import aerosandbox as asb
import numpy as np

HERE = pathlib.Path(__file__).parent
dif = runpy.run_path(str(HERE / "bryan_aileron_differential.py"), run_name="lib")
m, g, atm, d_geo, af, fus = dif["m"], dif["g"], dif["atm"], dif["d_geo"], dif["af"], dif["fus"]
DELTA = 20.0
V = 1.3 * 5.29

q = 0.5 * float(atm.density()) * V**2
cl_req = m * g / (q * dif["plane"].s_ref)
avl = dif["run"](cl_req, -DELTA, DELTA, True)
print(f"AVL:          pb/2V = {abs(avl['phat']):.4f}   (alpha {avl['alpha']:.2f}°, C_L {cl_req:.3f})")


def build(delta):
    wings = []
    for name, w in d_geo["wings"].items():
        xs = []
        for x in w["x_secs"]:
            cs = []
            ted = x.get("trailing_edge_device")
            if ted and ted.get("role") == "aileron":
                cs = [asb.ControlSurface(name="aileron", symmetric=False,
                                         hinge_point=x["control_surface"]["hinge_point"], deflection=delta)]
            xs.append(asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], twist=x["twist"],
                                   airfoil=af[x["airfoil"]], control_surfaces=cs))
        wings.append(asb.Wing(name=name, symmetric=w["symmetric"], xsecs=xs))
    w0 = wings[0]
    return asb.Airplane(name="BRYAN", xyz_ref=d_geo["xyz_ref"], wings=wings, fuselages=fus(True),
                        s_ref=w0.area(), c_ref=w0.mean_aerodynamic_chord(), b_ref=w0.span())


p_ab = build(DELTA)
b = p_ab.b_ref
o = asb.Opti()
a = o.variable(init_guess=3, lower_bound=-5, upper_bound=12)
p = o.variable(init_guess=1.0, lower_bound=-30, upper_bound=30)
r = asb.AeroBuildup(p_ab, asb.OperatingPoint(atm, velocity=V, alpha=a, p=p)).run()
o.subject_to([r["L"] == m * g, r["Cl"] == 0])
s = o.solve(verbose=False, max_iter=500)
phat_ab = abs(float(s(p))) * b / (2 * V)
print(f"AeroBuildup:  pb/2V = {phat_ab:.4f}   (alpha {float(s(a)):.2f}°)")

r0 = asb.AeroBuildup(p_ab, asb.OperatingPoint(atm, velocity=V, alpha=float(s(a)), p=0.0)).run()
print(f"AeroBuildup:  C_l aus 20° Querruder bei p = 0: {float(np.ravel(r0['Cl'])[0]):+.4f}")
print(f"Verhältnis AeroBuildup / AVL: {phat_ab / abs(avl['phat']):.2f}")
