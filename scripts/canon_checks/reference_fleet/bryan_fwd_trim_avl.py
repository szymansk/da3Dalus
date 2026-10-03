"""BRYAN: forward trim limit x_fwd — AeroBuildup vs AVL (2026-10-03).

Canon mass-envelope, front edge (as clarified 2026-10-02): hold the angle of attack at the stall angle
alpha_S (first C_L peak), full up elevator (-14 deg as built), find the CG at which the pitching moment
vanishes. With the moment about a reference x_ref: Cm(x) = Cm_ref + (x - x_ref)/c * C_N, C_N ~ C_L cos a
+ C_D sin a  ->  x_fwd = x_ref - Cm_ref * c / C_N.

AeroBuildup has no wing-tail downwash (#1154), so it is expected to overstate elevator authority and put
x_fwd too far forward. AVL carries the downwash but is inviscid and linear (no stall, no low-Re flap
losses); it is run with CLAF 1.0 and with ASB's thickness rule. ASB's AVL export ignores control
deflections, so the elevator is driven directly ("d1 d1 -14").
"""

import pathlib
import re
import subprocess
import tempfile

import aerosandbox as asb
import numpy as np
from avl_binary import avl_path

HERE = pathlib.Path(__file__).parent
src = (HERE / "bryan_stability_mass.py").read_text().split("# --- run ---")[0]
ns = {"__file__": str(HERE / "bryan_stability_mass.py")}
exec(compile(src, "bryan_stability_mass", "exec"), ns)  # noqa: S102
build, atm, M0, G, MAC, pct = ns["build"], ns["atm"], ns["M0"], ns["G"], ns["MAC"], ns["pct"]
stall_branch_alpha, X_CG = ns["stall_branch_alpha"], ns["X_CG_PLAN"]
DE = -14.0


def sc(v):
    return float(np.ravel(v)[0])


a_s = stall_branch_alpha(M0)
p_ab = build(DE, X_CG)
V = 5.6
r = asb.AeroBuildup(p_ab, asb.OperatingPoint(atm, velocity=V, alpha=a_s)).run()
cl, cd, cm = sc(r["CL"]), sc(r["CD"]), sc(r["Cm"])
cn = cl * np.cos(np.radians(a_s)) + cd * np.sin(np.radians(a_s))
x_ab = X_CG - cm * MAC / cn
print(f"alpha_S = {a_s:.1f}°, Höhenruder {DE:.0f}°")
print(f"AeroBuildup: C_L {cl:.3f}, Cm(Plan-SP) {cm:+.4f} -> x_fwd = {pct(x_ab):.1f} % MAC")


AVL_WING = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)}
AVL_XSEC = {asb.AVL: dict(spanwise_resolution=3, spanwise_spacing="uniform")}
p_avl = asb.Airplane(
    name="BRYAN", xyz_ref=p_ab.xyz_ref, fuselages=p_ab.fuselages,
    s_ref=p_ab.s_ref, c_ref=p_ab.c_ref, b_ref=p_ab.b_ref,
    wings=[asb.Wing(name=w.name, symmetric=w.symmetric, analysis_specific_options=AVL_WING,
                    xsecs=[asb.WingXSec(xyz_le=x.xyz_le, chord=x.chord, twist=x.twist, airfoil=x.airfoil,
                                        control_surfaces=x.control_surfaces, analysis_specific_options=AVL_XSEC)
                           for x in w.xsecs]) for w in p_ab.wings])


def avl_xfwd(claf_wing, claf_tail):
    work = pathlib.Path(tempfile.mkdtemp(prefix="fwd_"))
    geom = work / "b.avl"
    asb.AVL(airplane=p_avl, op_point=asb.OperatingPoint(atm, velocity=V, alpha=a_s),
            xyz_ref=list(p_ab.xyz_ref)).write_avl(geom)
    parts = geom.read_text().split("SURFACE")
    for k in range(1, len(parts)):
        main = parts[k].strip().startswith("Tragflaeche")
        dat = HERE / "bryan" / ("bryan_profil.dat" if main else "bryan_platte.dat")
        parts[k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(dat) + "\n", parts[k])
        if claf_wing is not None:
            parts[k] = re.sub(r"\nCLAF\n[^\n]+\n", "\nCLAF\n" + str(claf_wing if main else claf_tail) + "\n", parts[k])
    geom.write_text("SURFACE".join(parts))
    if "CONTROL" not in geom.read_text():
        raise RuntimeError("no CONTROL in the AVL geometry — elevator not exported")
    cmds = ["oper", f"a a {a_s}", f"d1 d1 {DE}", "x", "", "quit"]
    out = subprocess.run([str(avl_path()), str(geom)], input="\n".join(cmds) + "\n",
                         capture_output=True, text=True, cwd=work, timeout=60).stdout

    def get(k):
        f = re.findall(rf"\b{re.escape(k)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
        if not f:
            raise RuntimeError("AVL output lacks " + k + ":\n" + out[-1500:])
        return float(f[0])

    cl_, cm_ = get("CLtot"), get("Cmtot")
    return X_CG - cm_ * MAC / cl_, cl_, cm_


for label, cw, ct in (("AVL, CLAF ASB-Dickenregel", None, None), ("AVL, CLAF 1,0", 1.0, 1.0)):
    x, cl_, cm_ = avl_xfwd(cw, ct)
    print(f"{label:26s}: C_L {cl_:.3f}, Cm(Plan-SP) {cm_:+.4f} -> x_fwd = {pct(x):.1f} % MAC")
print(f"Plan-Schwerpunkt {pct(X_CG):.1f} % MAC")
