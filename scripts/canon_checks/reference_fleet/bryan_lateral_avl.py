"""BRYAN: lateral-directional derivatives, AeroBuildup vs AVL (approval check of
canon lateral-static-stability-md: "whether AeroBuildup captures the dihedral effect of the wing
position and the fin in the fuselage wake is unchecked — a cross-check with AVL on BRYAN").

Same point for both: V_md = 7.82 m/s, alpha from L = m g in AeroBuildup, moment reference = plan CG.
AVL: vortex lattice, inviscid; the wing tip's many close sections get their own spanwise vortices
(as in bryan_aileron_differential.py). AVL is run with and without the fuselage body to see what
the fuselage adds.
"""

import pathlib
import re
import runpy
import subprocess
import tempfile

import aerosandbox as asb
import numpy as np
from avl_binary import avl_path

ns = runpy.run_path(str(pathlib.Path(__file__).parent / "run_bryan.py"), run_name="lib")
m, g, atm, fus, d_geo = ns["m"], ns["g"], ns["atm"], ns["fus"], ns["d"]
AVL_WING = dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)
AVL_XSEC = dict(spanwise_resolution=3, spanwise_spacing="uniform")


def with_opts(w):
    return asb.Wing(name=w.name, symmetric=w.symmetric, analysis_specific_options={asb.AVL: AVL_WING},
                    xsecs=[asb.WingXSec(xyz_le=x.xyz_le, chord=x.chord, twist=x.twist, airfoil=x.airfoil,
                                        analysis_specific_options={asb.AVL: AVL_XSEC}) for x in w.xsecs])


wings = [with_opts(w) for w in ns["wings"]]
W0 = wings[0]


def plane(with_fuselage):
    return asb.Airplane(name="BRYAN", xyz_ref=d_geo["xyz_ref"], wings=wings,
                        fuselages=fus(True) if with_fuselage else [],
                        s_ref=W0.area(), c_ref=W0.mean_aerodynamic_chord(), b_ref=W0.span())


V = 7.82
o = asb.Opti()
a = o.variable(init_guess=1, lower_bound=-5, upper_bound=10)
o.subject_to(asb.AeroBuildup(plane(True), asb.OperatingPoint(atm, velocity=V, alpha=a)).run()["L"] == m * g)
alpha = float(o.solve(verbose=False)(a))
op = asb.OperatingPoint(atm, velocity=V, alpha=alpha)
print(f"Punkt: V = {V} m/s, alpha = {alpha:.2f}°, Bezug = Plan-Schwerpunkt x = {d_geo['xyz_ref'][0]*1000:.1f} mm\n")

KEYS = ("CL", "Clb", "Cnb", "Clp", "Cnr", "Clr", "Cnp", "Cyb")


def sc(v):
    return float(np.ravel(v)[0])


rows = {}
for label, p in (("AeroBuildup (mit Rumpf)", plane(True)), ("AeroBuildup (ohne Rumpf)", plane(False))):
    r = asb.AeroBuildup(p, op).run_with_stability_derivatives()
    rows[label] = {k: sc(r[k]) for k in KEYS if k in r}
AVL_MAP = {"Clb": "Clb", "Cnb": "Cnb", "Clp": "Clp", "Cnr": "Cnr", "Clr": "Clr", "Cnp": "Cnp",
           "Cyb": "CYb", "CL": "CLtot"}


def run_avl(p, cl_target):
    """Write the geometry with ASB, point AFIL at the original coordinate files (ASB's re-panelled
    export puts points at x > 1 for this section, AVL then returns nonsense), run AVL directly."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="bryan_lat_"))
    geom = work / "bryan.avl"
    asb.AVL(airplane=p, op_point=op, xyz_ref=d_geo["xyz_ref"]).write_avl(geom)
    src = pathlib.Path(__file__).parent / "bryan"
    parts = geom.read_text().split("SURFACE")
    for k in range(1, len(parts)):
        dat = src / ("bryan_profil.dat" if parts[k].strip().startswith("Tragflaeche") else "bryan_platte.dat")
        parts[k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(dat) + "\n", parts[k])
    geom.write_text("SURFACE".join(parts))
    cmds = ["oper", f"a c {cl_target}", "b b 0", "r r 0", "p p 0", "y y 0", "x", "st", "", "", "quit"]
    out = subprocess.run([str(avl_path()), str(geom)], input="\n".join(cmds) + "\n",
                         capture_output=True, text=True, cwd=work, timeout=60).stdout

    def get(key):
        f = re.findall(rf"\b{re.escape(key)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
        if not f:
            raise RuntimeError(f"AVL output lacks {key}")
        return float(f[0])  # first: AVL also prints "Clb Cnr / Clr Cnb = <spiral ratio>"

    return {k: get(v) for k, v in AVL_MAP.items()} | {"alpha": get("Alpha")}


cl0 = rows["AeroBuildup (mit Rumpf)"]["CL"]
for label, p in (("AVL (mit Rumpf)", plane(True)), ("AVL (ohne Rumpf)", plane(False))):
    try:
        rows[label] = run_avl(p, cl0)
        print(f"{label}: alpha bei C_L = {cl0:.3f}: {rows[label]['alpha']:.2f}°")
    except Exception as e:  # noqa: BLE001 — report and continue
        rows[label] = {"Fehler": str(e).splitlines()[-1][:80]}

print(f"{'':28s}" + "".join(f"{k:>9s}" for k in KEYS))
for label, vals in rows.items():
    if "Fehler" in vals:
        print(f"{label:28s} {vals['Fehler']}")
        continue
    print(f"{label:28s}" + "".join(f"{vals.get(k, float('nan')):9.4f}" for k in KEYS))
