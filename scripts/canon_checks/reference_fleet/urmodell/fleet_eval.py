"""Run the canon over the Urmodell fleet (fleet/*.airplane.json) — 2026-10-03.

Per aircraft (canon entries, A11 worlds where the canon declares them):
  stall-speed (first C_L peak, O3 gate), V_md and (L/D)max, V_mp and minimum sink,
  neutral point: textbook / Pappas (geometric, tailed aircraft) and AVL; AeroBuildup for contrast,
  static margin at the generated CG per world, lateral derivatives (AeroBuildup), E_spiral,
  steady roll rate p*b/2V at 1.3 V_S with ailerons/elevons +-20 deg: AeroBuildup and AVL.
Output: fleet_results.csv. Failures are recorded per aircraft, never silently dropped.
  python3 fleet_eval.py [n_workers]
"""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import pathlib
import re
import subprocess
import sys
import tempfile
import traceback

HERE = pathlib.Path(__file__).parent
FLEET = HERE / "fleet"
DELTA_A = 20.0
ROLL = ("aileron", "elevon_roll")  # antisymmetric roll surfaces


def asb_plane(d, delta_a=0.0, with_avl_opts=False):
    import aerosandbox as asb

    afs = {}

    def af(p):
        if p not in afs:
            afs[p] = asb.Airfoil(pathlib.Path(p).stem, coordinates=str(FLEET / p[2:]))
        return afs[p]

    ow = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=8)} if with_avl_opts else {}
    ox = {asb.AVL: dict(spanwise_resolution=4, spanwise_spacing="uniform")} if with_avl_opts else {}
    wings = []
    for name, w in d["wings"].items():
        xs = []
        for x in w["x_secs"]:
            surfs = [asb.ControlSurface(name=c["name"], symmetric=c["symmetric"], hinge_point=c["hinge_point"],
                                        deflection=delta_a if c["name"] in ROLL else 0.0)
                     for c in x.get("control_surfaces", [])]
            xs.append(asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], twist=x["twist"], airfoil=af(x["airfoil"]),
                                   control_surfaces=surfs, analysis_specific_options=ox))
        wings.append(asb.Wing(name=name, symmetric=w["symmetric"], xsecs=xs, analysis_specific_options=ow))
    fus = [asb.Fuselage(name=n, xsecs=[asb.FuselageXSec(xyz_c=x["xyz"], width=2 * x["a"], height=2 * x["b"], shape=x["n"])
                                        for x in f["x_secs"]]) for n, f in d["fuselages"].items()]
    w0 = wings[0]
    return asb.Airplane(name=d["name"][:30], xyz_ref=d["xyz_ref"], wings=wings, fuselages=fus,
                        s_ref=d["urmodell"]["S_m2"], c_ref=d["urmodell"]["mac_m"], b_ref=w0.span())


def avl_run(plane, op, xyz_ref, cmds):
    import aerosandbox as asb
    from avl_binary import avl_path

    work = pathlib.Path(tempfile.mkdtemp(prefix="urm_"))
    geom = work / "a.avl"
    asb.AVL(airplane=plane, op_point=op, xyz_ref=xyz_ref).write_avl(geom)
    txt = geom.read_text()
    # point AFIL at the original coordinate files (ASB's re-panelled export can write x > 1)
    txt = re.sub(r"\nAFIL\n([^\n]+)\n", lambda m: "\nAFIL\n" + str(FLEET / "airfoils" / (pathlib.Path(m.group(1)).stem.split("_")[0] + ".dat")) + "\n"
                 if (FLEET / "airfoils" / (pathlib.Path(m.group(1)).stem.split("_")[0] + ".dat")).exists() else m.group(0), txt)
    geom.write_text(txt)
    out = subprocess.run([str(avl_path()), str(geom)], input="\n".join(cmds) + "\n", capture_output=True,
                         text=True, cwd=work, timeout=120).stdout
    controls = []
    for nm in re.findall(r"\nCONTROL\n#?[^\n]*\n?([A-Za-z_][^\s]*)", txt):
        if nm not in controls:
            controls.append(nm)
    return out, controls


def get(out, key):
    out = out[out.find("Vortex Lattice Output"):] if "Vortex Lattice Output" in out else out
    f = re.findall(rf"\b{re.escape(key)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
    if not f:
        raise RuntimeError(f"AVL output lacks {key}")
    return float(f[0])


def evaluate(path: pathlib.Path) -> dict:
    import aerosandbox as asb
    import numpy as np

    sys.path.insert(0, str(HERE))
    from generate import geo_np

    d = json.loads(path.read_text())
    u = d["urmodell"]
    row = {k: u[k] for k in ("motor", "mission", "trag", "lage", "leitwerk", "steuerung")}
    row.update(id=d["name"], span_m=u["span_m"], mass_kg=d["total_mass_kg"], S_dm2=round(u["S_m2"] * 100, 2),
               AR=round(u["AR"], 2), WS_g_dm2=round(d["total_mass_kg"] * 1000 / (u["S_m2"] * 100), 1))
    try:
        atm = asb.Atmosphere(altitude=0)
        rho, g, m = float(atm.density()), 9.80665, d["total_mass_kg"]
        S = u["S_m2"]
        plane = asb_plane(d)
        ref = geo_np(d["wings"])
        x_le, mac_w = u["x_le_ref"], u["mac_m"]

        def pct(x):
            return 100 * (x - x_le) / mac_w

        def sc(v):
            return float(np.ravel(v)[0])

        def aero(V, a, p=plane, roll=0.0):
            return asb.AeroBuildup(p, asb.OperatingPoint(atm, velocity=V, alpha=a, p=roll)).run()

        V = 8.0
        for _ in range(3):
            al = np.arange(-4, 26, 0.5)
            cl = np.ravel(aero(V, al)["CL"])
            i = next((k for k in range(1, len(cl) - 1) if cl[k] >= cl[k - 1] and cl[k] > cl[k + 1]), int(np.argmax(cl)))
            V = math.sqrt(2 * m * g / (rho * S * cl[i]))
        a_pk = float(al[i])

        def level(obj):
            o = asb.Opti()
            v = o.variable(init_guess=1.3 * V, lower_bound=0.5, upper_bound=60)
            a = o.variable(init_guess=3, lower_bound=-8, upper_bound=a_pk + 1.0)
            r = aero(v, a)
            o.subject_to(r["L"] == m * g)
            o.minimize({"VS": v, "Vmd": r["D"], "Vmp": r["D"] * v}[obj])
            s = o.solve(verbose=False, max_iter=600)
            return float(s(v)), float(s(a)), float(s(r["D"]))

        vs, _a, _d = level("VS")
        vmd, a_md, dmd = level("Vmd")
        vmp, _a2, dmp = level("Vmp")
        row.update(V_S=round(vs, 2), CLmax=round(float(cl[i]), 3), V_md=round(vmd, 2), LD_max=round(m * g / dmd, 2),
                   V_mp=round(vmp, 2), sink_min=round(dmp * vmp / (m * g), 3))

        # neutral point worlds
        rd = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=vmd, alpha=a_md)).run_with_stability_derivatives()
        row["NP_AeroBuildup"] = round(pct(sc(rd["x_np"])), 1)
        row["NP_Lehrbuch"], row["NP_Pappas"] = (round(pct(x), 1) for x in ref["worlds"])
        cl_md = m * g / (0.5 * rho * vmd ** 2 * S)
        pa = asb_plane(d, with_avl_opts=True)
        out, _ = avl_run(pa, asb.OperatingPoint(atm, velocity=vmd, alpha=a_md), d["xyz_ref"],
                         ["oper", f"a c {cl_md}", "x", "st", "", "", "quit"])
        row["NP_AVL"] = round(pct(get(out, "Xnp")), 1)
        worlds = [row[k] for k in ("NP_Lehrbuch", "NP_Pappas", "NP_AVL")]
        row["NP_min"], row["NP_max"] = min(worlds), max(worlds)
        row["CG"] = round(pct(d["xyz_ref"][0]), 1)
        row["SM_min"], row["SM_max"] = round(row["NP_min"] - row["CG"], 1), round(row["NP_max"] - row["CG"], 1)
        row["SM_target"] = round(100 * u["sm_target"], 1)

        # lateral (AeroBuildup)
        clb, cnb, clr, cnr = (sc(rd[k]) for k in ("Clb", "Cnb", "Clr", "Cnr"))
        row.update(Clb=round(clb, 4), Cnb=round(cnb, 4), E_spiral=round(clb * cnr - cnb * clr, 5))

        # roll rate, both worlds
        if row["steuerung"] in ("hsq", "hq", "hsqk", "elevon", "elevon_s"):
            va = 1.3 * vs
            pr = asb_plane(d, delta_a=DELTA_A)
            o = asb.Opti()
            a = o.variable(init_guess=4, lower_bound=-6, upper_bound=a_pk)
            p = o.variable(init_guess=1.0, lower_bound=-60, upper_bound=60)
            r = aero(va, a, pr, p)
            o.subject_to([r["L"] == m * g, r["Cl"] == 0])
            s = o.solve(verbose=False, max_iter=600)
            row["roll_AB"] = round(abs(float(s(p))) * pr.b_ref / (2 * va), 4)
            pav = asb_plane(d, with_avl_opts=True)
            cl_app = m * g / (0.5 * rho * va ** 2 * S)
            out0, controls = avl_run(pav, asb.OperatingPoint(atm, velocity=va, alpha=4), d["xyz_ref"], ["quit"])
            name = "aileron" if "aileron" in controls else "elevon_roll"
            if name in controls:
                idx = controls.index(name) + 1
                out, _ = avl_run(pav, asb.OperatingPoint(atm, velocity=va, alpha=4), d["xyz_ref"],
                                 ["oper", f"a c {cl_app}", f"d{idx} d{idx} {DELTA_A}", "r rm 0", "x", "", "quit"])
                row["roll_AVL"] = round(abs(get(out, "pb/2V")), 4)
        row["status"] = "ok"
    except Exception as e:  # noqa: BLE001 — record, never drop silently
        row["status"] = f"FEHLER: {type(e).__name__}: {str(e).splitlines()[0][:120]}"
        row["trace"] = traceback.format_exc().splitlines()[-3][:200]
    return row


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    files = sorted(FLEET.glob("*.airplane.json"))
    with mp.get_context("spawn").Pool(n) as pool:
        rows = []
        for k, r in enumerate(pool.imap_unordered(evaluate, files), 1):
            rows.append(r)
            print(f"[{k}/{len(files)}] {r['id']}: {r['status']}", flush=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in rows[0], k))
    with open(HERE / "fleet_results.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(sorted(rows, key=lambda r: r["id"]))
    print("-> fleet_results.csv")
