"""Minimal repro: AeroBuildup C_lβ of a plain wing vs AVL, sweep vs dihedral (2026-10-03).

Wing alone, AR 7.7, taper 0.55, NACA 0009 (symmetric, so no camber effect), C_L 0.4.
Theory: a swept wing at lift has a dihedral effect C_lβ ≈ -C_L·sin(2Λ)/(…) even without geometric dihedral
(Sadraey §12 / DATCOM): it should be clearly non-zero at Λ = 17°.
"""
import pathlib

import aerosandbox as asb
import numpy as np

import fleet_eval as fe

FOIL = asb.Airfoil("naca0009", coordinates=str(pathlib.Path(__file__).parent / "fleet/airfoils/naca0009.dat"))
atm = asb.Atmosphere(0)


def wing(sweep, dih, avl=False):
    b, ar, lam = 1.5, 7.7, 0.55
    s = b * b / ar
    cr = 2 * s / (b * (1 + lam))
    ow = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=8)} if avl else {}
    ox = {asb.AVL: dict(spanwise_resolution=12, spanwise_spacing="cosine")} if avl else {}
    xs = []
    for f in (0, 1):
        y = f * b / 2
        c = cr * (1 + (lam - 1) * f)
        xs.append(asb.WingXSec(xyz_le=[0.25 * cr + y * np.tan(np.radians(sweep)) - 0.25 * c, y, y * np.tan(np.radians(dih))],
                               chord=c, airfoil=FOIL, analysis_specific_options=ox))
    w = asb.Wing(name="W", symmetric=True, xsecs=xs, analysis_specific_options=ow)
    return asb.Airplane(name="w", wings=[w], xyz_ref=[0.25 * cr, 0, 0], s_ref=s, c_ref=w.mean_aerodynamic_chord(), b_ref=b)


for sweep, dih in ((0, 0), (17, 0), (30, 0), (0, 5)):
    p = wing(sweep, dih)
    a = 4.0
    r = asb.AeroBuildup(p, asb.OperatingPoint(atm, velocity=15, alpha=a)).run_with_stability_derivatives()
    cl = float(np.ravel(r["CL"])[0])
    out, _ = fe.avl_run(wing(sweep, dih, True), asb.OperatingPoint(atm, velocity=15, alpha=a), [p.xyz_ref[0], 0, 0],
                        ["oper", f"a c {cl}", "x", "st", "", "", "quit"])
    der = out[out.find("Stability-axis derivatives"):]
    import re
    clb_avl = float(re.findall(r"\bClb\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", der)[0])
    print(f"sweep {sweep:2d}°, dihedral {dih}°, C_L {cl:.3f}: C_lβ AeroBuildup {float(np.ravel(r['Clb'])[0]):+.4f}  AVL {clb_avl:+.4f}")
