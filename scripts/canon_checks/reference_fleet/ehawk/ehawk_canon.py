"""e-Hawk (glider, 280 g) through the canon — second member of the reference fleet.

Entries: stall-speed (first C_L peak, O3 gate), minimum-drag / minimum-sink speed, (L/D)max,
neutral-point, static-margin, cg-for-target-margin, lateral-static-stability-md with an AVL
cross-check (V-tail), and Drela's glider sizing checks against BAENDER.md §3b.
Geometry and declared assumptions: build_ehawk.py.
"""

import json
import pathlib
import re
import subprocess
import tempfile

import aerosandbox as asb
import numpy as np
from avl_binary import avl_path

HERE = pathlib.Path(__file__).parent
d = json.loads((HERE / "ehawk.airplane.json").read_text())
AF = {p: asb.Airfoil(p[2:-4], coordinates=str(HERE / p[2:])) for p in ("./mh32.dat", "./platte_2mm.dat")}
M, G = d["total_mass_kg"], 9.80665
X_CG = d["xyz_ref"][0]
atm = asb.Atmosphere(altitude=0)
RHO = float(atm.density())


def sc(v):
    return float(np.ravel(v)[0])


def build(with_fuselage=True, avl_opts=False):
    ow = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)} if avl_opts else {}
    ox = {asb.AVL: dict(spanwise_resolution=3, spanwise_spacing="uniform")} if avl_opts else {}
    wings = [asb.Wing(name=n, symmetric=w["symmetric"], analysis_specific_options=ow,
                      xsecs=[asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], twist=x["twist"],
                                          airfoil=AF[x["airfoil"]], analysis_specific_options=ox)
                             for x in w["x_secs"]])
             for n, w in d["wings"].items()]
    fus = [asb.Fuselage(name=n, xsecs=[asb.FuselageXSec(xyz_c=x["xyz"], width=2 * x["a"], height=2 * x["b"],
                                                         shape=x["n"]) for x in f["x_secs"]])
           for n, f in d["fuselages"].items()] if with_fuselage else []
    w0 = wings[0]
    return asb.Airplane(name="e-Hawk", xyz_ref=d["xyz_ref"], wings=wings, fuselages=fus,
                        s_ref=w0.area(), c_ref=w0.mean_aerodynamic_chord(), b_ref=w0.span())


plane = build()
W = plane.wings[0]
S, B, MAC = W.area(), W.span(), W.mean_aerodynamic_chord()
X_MAC_LE = W.aerodynamic_center()[0] - 0.25 * MAC


def pct(x):
    return 100 * (x - X_MAC_LE) / MAC


def aero(V, a, p=plane):
    return asb.AeroBuildup(p, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()


def first_peak_alpha(V):
    al = np.arange(-4, 26, 0.5)
    cl = np.ravel(aero(V, al)["CL"])
    i = next((k for k in range(1, len(cl) - 1) if cl[k] >= cl[k - 1] and cl[k] > cl[k + 1]), int(np.argmax(cl)))
    return float(al[i]), float(cl[i])


V = 5.0
for _ in range(3):
    a_pk, cl_pk = first_peak_alpha(V)
    V = float(np.sqrt(2 * M * G / (RHO * S * cl_pk)))


def level(objective):
    o = asb.Opti()
    v = o.variable(init_guess=7, lower_bound=1, upper_bound=40)
    a = o.variable(init_guess=3, lower_bound=-8, upper_bound=a_pk + 1.0)
    r = aero(v, a)
    o.subject_to(r["L"] == M * G)
    o.minimize({"VS": v, "Vmd": r["D"], "Vmp": r["D"] * v}[objective])
    s = o.solve(verbose=False, max_iter=500)
    return float(s(v)), float(s(a)), float(s(r["D"]))


print(f"Geometrie: b = {B*1000:.0f} mm, S = {S*100:.2f} dm², AR = {B**2/S:.1f}, MAC = {MAC*1000:.1f} mm, "
      f"m = {M*1000:.0f} g, W/S = {M*1000/(S*100):.1f} g/dm² (Bericht: 14,0)")
vs, a_s, _ = level("VS")
vmd, a_md, d_md = level("Vmd")
vmp, a_mp, d_mp = level("Vmp")
print(f"\nAbriss (erstes C_L-Maximum {cl_pk:.3f} bei {a_pk:.1f}°): V_S = {vs:.2f} m/s")
print(f"V_md = {vmd:.2f} m/s (alpha {a_md:.2f}°): (L/D)max = {M*G/d_md:.1f}")
print(f"V_mp = {vmp:.2f} m/s (alpha {a_mp:.2f}°): geringstes Sinken = {d_mp*vmp/(M*G):.3f} m/s")

r_md = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=vmd, alpha=a_md)).run_with_stability_derivatives()
x_np = sc(r_md["x_np"])
print(f"\nNeutralpunkt {x_np*1000:.1f} mm = {pct(x_np):.1f} % MAC; Plan-Schwerpunkt {X_CG*1000:.1f} mm = "
      f"{pct(X_CG):.1f} % MAC (Bericht: 33 %) -> Stabilitätsmaß {100*(x_np-X_CG)/MAC:.1f} % MAC")
for t in (0.05, 0.10, 0.12):
    print(f"  cg-for-target-margin {t:.0%}: x_CG = {(x_np-t*MAC)*1000:.1f} mm = {pct(x_np-t*MAC):.1f} % MAC")

# Drela checks (BAENDER §3b) from the design data of the report
aus = json.loads((HERE / "ehawk_rumpf_auslegung.json").read_text())
SH, SV, lH, Sw, b_mm, mac_mm = aus["SH"], aus["SV"], aus["lH"], aus["S"], aus["b"], aus["mac"]
VH, VV = SH / Sw * lH / mac_mm, SV / Sw * lH / b_mm
eda = np.degrees(np.arctan2(sum(x["xyz_le"][2] for x in d["wings"]["Tragflaeche"]["x_secs"][-1:]),
                            d["wings"]["Tragflaeche"]["x_secs"][-1]["xyz_le"][1]))
Bpar = eda * (lH / b_mm) / 0.7
print(f"\nDrela: V_H = {VH:.2f} (Band 0,3–0,6), V_V = {VV:.3f} (mit Querrudern 0,015–0,025), "
      f"äquivalente V-Form ≈ {eda:.1f}° -> B = {Bpar:.1f} (mit Querrudern 2–5)")

# lateral: AeroBuildup vs AVL at V_md, equal C_L
KEYS = ("Clb", "Cnb", "Clp", "Cnr", "Clr")
rows = {"AeroBuildup": {k: sc(r_md[k]) for k in KEYS} | {"CL": sc(r_md["CL"])}}


def run_avl(p, cl):
    work = pathlib.Path(tempfile.mkdtemp(prefix="ehawk_"))
    geom = work / "ehawk.avl"
    asb.AVL(airplane=p, op_point=asb.OperatingPoint(atm, velocity=vmd, alpha=a_md), xyz_ref=d["xyz_ref"]).write_avl(geom)
    parts = geom.read_text().split("SURFACE")
    for k in range(1, len(parts)):
        dat = HERE / ("mh32.dat" if parts[k].strip().startswith("Tragflaeche") else "platte_2mm.dat")
        parts[k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(dat) + "\n", parts[k])
    geom.write_text("SURFACE".join(parts))
    cmds = ["oper", f"a c {cl}", "b b 0", "r r 0", "p p 0", "y y 0", "x", "st", "", "", "quit"]
    out = subprocess.run([str(avl_path()), str(geom)], input="\n".join(cmds) + "\n",
                         capture_output=True, text=True, cwd=work, timeout=60).stdout

    def get(key):
        f = re.findall(rf"\b{re.escape(key)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
        if not f:
            raise RuntimeError(f"AVL output lacks {key}")
        return float(f[0])  # first: AVL also prints "Clb Cnr / Clr Cnb = <spiral ratio>"

    return {k: get(k) for k in KEYS} | {"CL": get("CLtot"), "Xnp": get("Xnp")}


rows["AVL"] = run_avl(build(True, avl_opts=True), rows["AeroBuildup"]["CL"])
print(f"\nSeitenstabilität bei V_md (C_L = {rows['AeroBuildup']['CL']:.3f}):")
print(f"{'':12s}" + "".join(f"{k:>9s}" for k in KEYS) + "   E_spiral")
for lab, v in rows.items():
    e = v["Clb"] * v["Cnr"] - v["Cnb"] * v["Clr"]
    print(f"{lab:12s}" + "".join(f"{v[k]:9.4f}" for k in KEYS) + f"   {e:+.5f}")

x_np_avl = rows["AVL"]["Xnp"]
print(f"\nNeutralpunkt: AeroBuildup {pct(x_np):.1f} % MAC, AVL {pct(x_np_avl):.1f} % MAC "
      f"-> Stabilitätsmaß beim Plan-Schwerpunkt {100*(x_np-X_CG)/MAC:.1f} % bzw. {100*(x_np_avl-X_CG)/MAC:.1f} %")
