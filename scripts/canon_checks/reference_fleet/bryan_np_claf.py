"""BRYAN: sensitivity of the AVL neutral point to the section lift slope (CLAF), 2026-10-03.

ASB writes CLAF = 1 + 0.77 t/c (Drela's potential-flow rule); this replaces that value per surface to test
low-Re lift slopes from NeuralFoil (wing 1.62, tail plate 1.09 x 2 pi at Re 71k / 40k).
Run from scripts/canon_checks/reference_fleet.
"""

import runpy
import re
import sys
import subprocess
import pathlib

sys.argv = ["x"]
ns = runpy.run_path("bryan_lateral_avl.py", run_name="lib")
asb, op, d_geo, plane, avl_path = ns["asb"], ns["op"], ns["d_geo"], ns["plane"], ns["avl_path"]
import tempfile


def xnp(claf_wing, claf_tail, cl=0.5649):
    work = pathlib.Path(tempfile.mkdtemp())
    geom = work / "b.avl"
    asb.AVL(airplane=plane(True), op_point=op, xyz_ref=d_geo["xyz_ref"]).write_avl(geom)
    src = pathlib.Path("bryan")
    parts = geom.read_text().split("SURFACE")
    for k in range(1, len(parts)):
        main = parts[k].strip().startswith("Tragflaeche")
        dat = src / ("bryan_profil.dat" if main else "bryan_platte.dat")
        claf = claf_wing if main else claf_tail
        parts[k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(dat) + "\n", parts[k])
        parts[k] = re.sub(r"\nCLAF\n[^\n]+\n", "\nCLAF\n" + str(claf) + "\n", parts[k])
    geom.write_text("SURFACE".join(parts))
    out = subprocess.run(
        [str(avl_path()), str(geom)],
        input="\n".join(["oper", f"a c {cl}", "x", "st", "", "", "quit"]) + "\n",
        capture_output=True,
        text=True,
        cwd=work,
        timeout=60,
    ).stdout
    return float(re.findall(r"Xnp\s*=\s*(-?[\d.]+)", out)[0])


W = plane(True).wings[0]
mac = W.mean_aerodynamic_chord()
le = W.aerodynamic_center()[0] - 0.25 * mac
for cw, ct, lab in (
    (1.0, 1.0, "CLAF 1,0 / 1,0"),
    (1.076, 1.02, "ASB-Dickenregel (bisher)"),
    (1.62, 1.09, "CLAF aus NeuralFoil"),
    (1.62, 1.0, "nur Flügel"),
    (1.0, 1.09, "nur Leitwerk"),
):
    x = xnp(cw, ct)
    print(f"{lab:22s} NP {100 * (x - le) / mac:5.1f} % MAC")
