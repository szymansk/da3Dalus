"""BRYAN: aileron differential that cancels adverse yaw in slow flight — AVL.

Operating point (maintainer, 2026-10-01): approach, 1.3 * V_S, steady roll at full aileron
command. Up-going aileron DELTA_UP, down-going DELTA_UP / d (d = up:down ratio).

Why AVL, not AeroBuildup: AeroBuildup evaluates the wings WITHOUT induced drag
(aero_buildup.py:262) and adds the induced drag afterwards as one force for the whole
aircraft with no lever arm (:279-298) — it cannot produce the yaw from the induced-drag
asymmetry, which is the main adverse-yaw mechanism (Sadraey §12.4.3). AVL's vortex lattice
does, and it carries the roll rate. The run is INVISCID: ASB writes zero CDCL polars, so
profile drag — including the extra drag of the deflected ailerons — is absent. Declared.
ASB's AVL wrapper sets only "d1 = 1 deg" and ignores ControlSurface.deflection (avl.py:389),
so the geometry is written with ASB and the run is driven here.

Two readings of adverse yaw:
  * total      — roll rate free, rolling moment = 0 (steady roll): deflection + roll-rate part
  * deflection — roll rate held at 0: the part Sadraey treats ("equal drag on both wings")
"""
import pathlib, re, runpy, subprocess, tempfile, numpy as np
from avl_binary import avl_path

ns = runpy.run_path(str(pathlib.Path(__file__).parent / "run_bryan.py"), run_name="lib")
asb, m, g, atm, af, d_geo, fus = ns["asb"], ns["m"], ns["g"], ns["atm"], ns["af"], ns["d"], ns["fus"]
DELTA_UP = 20.0
# the tip carries many closely spaced sections: one wing-level spacing starves them of vortices
AVL_WING = dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)
AVL_XSEC = dict(spanwise_resolution=3, spanwise_spacing="uniform")
main = d_geo["wings"]["Tragflaeche"]

def half(side):
    """Main-wing half as its own surface, sections always ordered in +y (AVL and ASB need it)."""
    secs = main["x_secs"]
    ted = [bool(x.get("trailing_edge_device")) for x in secs]          # segment i -> i+1
    order = range(len(secs)) if side > 0 else range(len(secs) - 1, -1, -1)
    xs = []
    for k, i in enumerate(order):
        x = secs[i]; le = list(x["xyz_le"]); le[1] *= side
        seg = i if side > 0 else i - 1                                   # segment this section starts
        cs = []
        if 0 <= seg < len(secs) - 1 and ted[seg]:
            cs = [asb.ControlSurface(name=f"ail_{'R' if side > 0 else 'L'}", symmetric=True,
                                     hinge_point=secs[seg]["trailing_edge_device"]["rel_chord_root"])]
        xs.append(asb.WingXSec(xyz_le=le, chord=x["chord"], twist=x["twist"], airfoil=af[x["airfoil"]],
                               control_surfaces=cs, analysis_specific_options={asb.AVL: AVL_XSEC}))
    return asb.Wing(name=f"main_{'R' if side > 0 else 'L'}", symmetric=False, xsecs=xs,
                    analysis_specific_options={asb.AVL: AVL_WING})

def with_opts(w):
    return asb.Wing(name=w.name, symmetric=w.symmetric, analysis_specific_options={asb.AVL: AVL_WING},
                    xsecs=[asb.WingXSec(xyz_le=x.xyz_le, chord=x.chord, twist=x.twist, airfoil=x.airfoil,
                                        analysis_specific_options={asb.AVL: AVL_XSEC}) for x in w.xsecs])
tails = [with_opts(w) for w in ns["wings"] if w.name != "Tragflaeche"]
W0 = ns["wings"][0]
plane = asb.Airplane(name="BRYAN", xyz_ref=d_geo["xyz_ref"], wings=[half(+1), half(-1)] + tails,
                     fuselages=fus(True), s_ref=W0.area(), c_ref=W0.mean_aerodynamic_chord(), b_ref=W0.span())

work = pathlib.Path(tempfile.mkdtemp(prefix="bryan_avl_", dir=__import__('os').environ.get('AVL_WORK')))
geom = work / "bryan.avl"
asb.AVL(airplane=plane, op_point=asb.OperatingPoint(atm, velocity=7, alpha=3)).write_avl(geom)
# ASB's AVL export re-panels the airfoil and writes points with x > 1 at the trailing edge
# for this section; AVL then returns C_L = -2.6 at alpha = 5 deg. Point AFIL at the plugin's
# original coordinate files instead (main wing: bryan_profil.dat, tails: bryan_platte.dat).
_src = pathlib.Path(__file__).parent / "bryan"
_parts = geom.read_text().split("SURFACE")
for _k in range(1, len(_parts)):
    _dat = _src / ("bryan_profil.dat" if _parts[_k].strip().startswith("main") else "bryan_platte.dat")
    _parts[_k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(_dat) + "\n", _parts[_k])
geom.write_text("SURFACE".join(_parts))

def run(CL, d1, d2, roll_free=True):
    cmds = ["oper", f"a c {CL}", "r rm 0" if roll_free else "r r 0", f"d1 d1 {d1}", f"d2 d2 {d2}",
            "b b 0", "y y 0", "x", "", "quit"]
    out = subprocess.run([avl_path(), str(geom)], input="\n".join(cmds) + "\n",
                         capture_output=True, text=True, cwd=work, timeout=60).stdout
    def get(k):
        f = re.findall(rf"{re.escape(k)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
        if not f: raise RuntimeError(f"AVL output lacks {k}:\n" + out[-3000:])
        return float(f[-1])
    return dict(Cn=get("Cntot"), Cl=get("Cltot"), phat=get("pb/2V"), alpha=get("Alpha"), CL=get("CLtot"))

def table(V, roll_free):
    q = 0.5 * float(atm.density()) * V ** 2
    CL = m * g / (q * plane.s_ref)
    rows = []
    for d in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0):
        rows.append((d, run(CL, -DELTA_UP, DELTA_UP / d, roll_free)))   # right up, left down -> roll right
    cn = np.array([r["Cn"] for _, r in rows]); ds = [d for d, _ in rows]
    z = np.where(np.diff(np.sign(cn)) != 0)[0]
    d_star = None if not len(z) else ds[z[0]] + (0 - cn[z[0]]) * (ds[z[0] + 1] - ds[z[0]]) / (cn[z[0] + 1] - cn[z[0]])
    return CL, rows, d_star

if __name__ == "__main__":
    print("Kontrolle ohne Ausschlag (Symmetrie):", run(0.9, 0, 0))
    V_S = 5.29
    for V, label in ((1.3 * V_S, "Anflug 1,3 V_S"), (15.0, "Kontrolle 15 m/s")):
        for roll_free, name in ((True, "gesamt (Ausschlag + Rollbewegung)"), (False, "nur Ausschlag (Rollrate 0)")):
            CL, rows, d_star = table(V, roll_free)
            print(f"\n=== {label}: V = {V:.2f} m/s, C_L = {CL:.3f}, aufwaerts {DELTA_UP:.0f} deg — {name} ===")
            for d, r in rows:
                print(f"  1:{d:<4}  ab {DELTA_UP/d:5.1f} deg   Cn = {r['Cn']:+.5f}   pb/2V = {r['phat']:+.4f}   alpha = {r['alpha']:.2f}")
            print(f"  -> Cn = 0 bei 1:{d_star:.2f}" if d_star else "  -> kein Nulldurchgang zwischen 1:1 und 1:4")
