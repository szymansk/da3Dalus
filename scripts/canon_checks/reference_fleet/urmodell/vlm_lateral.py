"""ASB VortexLatticeMethod lateral derivatives vs AVL on the Urmodell fleet (2026-10-04).

Question (maintainer): can AeroSandbox's VLM replace AVL as the single tool for lateral derivatives?
Mesh exactly as the app's VLM path (gh-855: app/services/vlm_strip_forces._remesh_airplane, 40 spanwise
panels per half, chordwise 8). Same operating point as lateral_avl.py: V_md, alpha such that
C_L = m g / (q S) (secant on two VLM solves). Writes vlm_lateral.csv next to the AVL and AB values.
Also re-runs the plain-wing sweep repro (sweep_clb_repro.py geometry) with the VLM.
"""

import csv
import json
import multiprocessing as mp
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[3]


def vlm(plane, atm, v, alpha, stab=False):
    import aerosandbox as asb
    import numpy as np

    sys.path.insert(0, str(ROOT))
    from app.services.vlm_strip_forces import _remesh_airplane

    m = _remesh_airplane(plane)
    solver = asb.VortexLatticeMethod(airplane=m, op_point=asb.OperatingPoint(atm, velocity=v, alpha=alpha),
                                     spanwise_resolution=1, chordwise_resolution=8,
                                     spanwise_spacing_function=np.linspace)
    return solver.run_with_stability_derivatives(alpha=False, beta=True, p=True, q=False, r=True) if stab else solver.run()


def one(row):
    import aerosandbox as asb
    import numpy as np

    import fleet_eval as fe

    d = json.loads((HERE / "fleet" / f"{row['id']}.airplane.json").read_text())
    atm = asb.Atmosphere(altitude=0)
    v = float(row["V_md"])
    cl_t = d["total_mass_kg"] * 9.80665 / (0.5 * float(atm.density()) * v * v * d["urmodell"]["S_m2"])
    p = fe.asb_plane(d)
    a0, a1 = 0.0, 4.0
    c0, c1 = (float(np.ravel(vlm(p, atm, v, a)["CL"])[0]) for a in (a0, a1))
    a = a0 + (cl_t - c0) * (a1 - a0) / (c1 - c0)
    r = vlm(p, atm, v, a, stab=True)
    res = {"id": row["id"], "alpha_VLM": round(a, 2), "CL_VLM": round(float(np.ravel(r["CL"])[0]), 3)}
    for k in ("Clb", "Cnb", "Clr", "Cnr", "Clp"):
        res[k + "_VLM"] = float(np.ravel(r[k])[0])
    res["E_VLM"] = res["Clb_VLM"] * res["Cnr_VLM"] - res["Cnb_VLM"] * res["Clr_VLM"]
    return res


if __name__ == "__main__":
    avl = {r["id"]: r for r in csv.DictReader(open(HERE / "lateral_avl.csv"))}
    rows = [r for r in csv.DictReader(open(HERE / "fleet_results.csv")) if r["status"] == "ok"]
    with mp.get_context("spawn").Pool(6) as pool:
        res = pool.map(one, rows)
    for r in res:
        a = avl[r["id"]]
        for k in ("Clb", "Cnb", "E"):
            r[k + "_AVL"] = float(a[k + "_AVL"])
        for k in ("Clb", "Cnb"):
            r[k + "_AB"] = float(a[k + "_AB"])
        r["E_AB"] = float(a["E_spiral_AB"])
    with open(HERE / "vlm_lateral.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)
    print("-> vlm_lateral.csv")
