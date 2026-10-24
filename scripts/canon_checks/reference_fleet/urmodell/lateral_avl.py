"""AVL lateral derivatives for the whole Urmodell fleet at V_md (2026-10-03).

Tests the A11 rule-5 decision of 2026-10-03 ("C_nβ and the spiral criterion stay crisp, AeroBuildup,
because sign and spiral verdict agree in both methods") on 74 aircraft instead of two.
Writes lateral_avl.csv: AVL Clb, Cnb, Clr, Cnr, E_spiral next to the AeroBuildup values.
"""

import csv
import json
import multiprocessing as mp
import pathlib
import re

HERE = pathlib.Path(__file__).parent


def one(row):
    import aerosandbox as asb

    import fleet_eval as fe

    d = json.loads((HERE / "fleet" / f"{row['id']}.airplane.json").read_text())
    atm = asb.Atmosphere(altitude=0)
    v = float(row["V_md"])
    cl = d["total_mass_kg"] * 9.80665 / (0.5 * float(atm.density()) * v * v * d["urmodell"]["S_m2"])
    out, _ = fe.avl_run(fe.asb_plane(d, with_avl_opts=True), asb.OperatingPoint(atm, velocity=v, alpha=3),
                        d["xyz_ref"], ["oper", f"a c {cl}", "x", "st", "", "", "quit"])
    res = {"id": row["id"]}
    try:
        der = out[out.find("Stability-axis derivatives"):]
        for k in ("Clb", "Cnb", "Clr", "Cnr"):
            res[k + "_AVL"] = float(re.findall(rf"\b{k}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", der)[0])
        res["E_AVL"] = res["Clb_AVL"] * res["Cnr_AVL"] - res["Cnb_AVL"] * res["Clr_AVL"]
    except (IndexError, ValueError) as e:
        res["fehler"] = str(e)
    for k in ("Clb", "Cnb", "E_spiral"):
        res[k + "_AB"] = float(row[k])
    return res


if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(HERE / "fleet_results.csv")) if r["status"] == "ok"]
    with mp.get_context("spawn").Pool(6) as pool:
        res = pool.map(one, rows)
    keys = list(dict.fromkeys(k for r in res for k in r))
    with open(HERE / "lateral_avl.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(res)
    bad = [r for r in res if "fehler" in r]
    good = [r for r in res if "fehler" not in r]
    agree_cnb = sum((r["Cnb_AVL"] > 0) == (r["Cnb_AB"] > 0) for r in good)
    agree_sp = sum((r["E_AVL"] > 0) == (r["E_spiral_AB"] > 0) for r in good)
    print(f"{len(good)} ok, {len(bad)} Fehler")
    print(f"Vorzeichen C_nβ gleich: {agree_cnb}/{len(good)};  Spiralurteil gleich: {agree_sp}/{len(good)}")
    for r in good:
        if (r["E_AVL"] > 0) != (r["E_spiral_AB"] > 0) or (r["Cnb_AVL"] > 0) != (r["Cnb_AB"] > 0):
            print(f"  {r['id']}: Cnb AB {r['Cnb_AB']:+.4f} AVL {r['Cnb_AVL']:+.4f} | "
                  f"E AB {r['E_spiral_AB']:+.5f} AVL {r['E_AVL']:+.5f}")
