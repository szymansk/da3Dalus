"""Import a reference-fleet aircraft (plan-reconstruction plugin export) into the app DB.

Goes through the public REST API in-process (FastAPI TestClient, no server,
no lifespan), so every write passes the same validation as the frontend.
Run from the repo root: the app's DB URL is relative (./db/test.db).

    poetry run python scripts/canon_checks/reference_fleet/import_to_db.py bryan
    poetry run python scripts/canon_checks/reference_fleet/import_to_db.py snack --no-airfoil-table

Battery: from <key>.konstruktion.json (komponenten.akku.typ, e.g. "2S 450 mAh") or, if that file
is absent, from <key>.zusatz.json ("akku": "2S 600-800 mAh ..."; the upper capacity is taken and
reported as an assumption).
--no-airfoil-table: copy the .dat files but do not register them in the airfoil catalogue — for
models whose format needs one file per station (absolute thickness), which would flood it.

Writes: aeroplane, wings (geometry, spars, trailing-edge devices, servos),
fuselages, total mass, design assumptions (mass, cg_x, battery energy), and
copies the referenced .dat airfoils into components/airfoils/.
"""
import json, pathlib, re, shutil, sys
from fastapi.testclient import TestClient
from app.main import app

key = sys.argv[1]
AIRFOIL_TABLE = "--no-airfoil-table" not in sys.argv
SRC = pathlib.Path(__file__).parent / key
geo = json.loads((SRC / f"{key}.airplane.json").read_text())
kon_p, zus_p = SRC / f"{key}.konstruktion.json", SRC / f"{key}.zusatz.json"
if kon_p.exists():
    akku = json.loads(kon_p.read_text())["komponenten"]["akku"]["typ"]          # e.g. "2S 450 mAh"
else:
    akku = json.loads(zus_p.read_text())["akku"]                               # e.g. "2S 600-800 mAh ..."
_m = re.match(r"\s*(\d+)S\s+(?:\d+\s*-\s*)?(\d+)\s*mAh", akku)
CELLS, MAH = int(_m.group(1)), float(_m.group(2))
AF_DIR = pathlib.Path("components/airfoils")
c = TestClient(app)

def ok(r, what):
    if r.status_code >= 300:
        sys.exit(f"FEHLER {what}: {r.status_code} {r.text[:400]}")
    return r

# airfoils: copy the .dat files and reference them where the app looks for them
af_map = {}
for w in geo["wings"].values():
    for x in w["x_secs"]:
        f = pathlib.Path(x["airfoil"]).name
        if f not in af_map:
            shutil.copy(SRC / f, AF_DIR / f)
            af_map[f] = f"./components/airfoils/{f}"
# the import endpoint only scans inside components/ — stage just these files there
if AIRFOIL_TABLE:
    stage = pathlib.Path("components/_reference_fleet_import")
    stage.mkdir(exist_ok=True)
    for f in af_map:
        shutil.copy(SRC / f, stage / f)
    try:
        r = ok(c.post("/airfoils/import", json={"directory": str(stage.resolve())}), "Profile in Profiltabelle")
        print("Profile:", r.json())
    finally:
        shutil.rmtree(stage)
else:
    print(f"Profile: {len(af_map)} Dateien kopiert, nicht in die Profiltabelle eingetragen")

pid = ok(c.post("/aeroplanes", params={"name": geo["name"]}), "Flugzeug").json()["id"]
print("Flugzeug", geo["name"], pid)

for wname, w in geo["wings"].items():
    xs = w["x_secs"]
    ok(c.put(f"/aeroplanes/{pid}/wings/{wname}", json={
        "name": wname, "symmetric": w["symmetric"],
        "x_secs": [{k: v for k, v in {
            "xyz_le": x["xyz_le"], "chord": x["chord"], "twist": x["twist"],
            "airfoil": af_map[pathlib.Path(x["airfoil"]).name],
            "x_sec_type": x.get("x_sec_type"), "tip_type": x.get("tip_type"),
        }.items() if v is not None} for x in xs]}), f"Fluegel {wname}")
    n_sp = n_ted = 0
    for i, x in enumerate(xs[:-1]):                     # terminal section carries no segment data
        base = f"/aeroplanes/{pid}/wings/{wname}/cross_sections/{i}"
        for sp in x.get("spare_list") or []:
            ok(c.post(f"{base}/spars", json=sp), f"{wname} Holm @{i}"); n_sp += 1
        ted = x.get("trailing_edge_device")
        if ted:
            servo = ted.get("servo")
            ok(c.patch(f"{base}/trailing_edge_device",
                       json={k: v for k, v in ted.items() if k != "servo" and v is not None}),
               f"{wname} Ruder @{i}"); n_ted += 1
            if servo:
                ok(c.patch(f"{base}/trailing_edge_device/servo",
                           json={"servo": {k: v for k, v in servo.items() if k != "component_id"}}),
                   f"{wname} Servo @{i}")
    print(f"  {wname}: {len(xs)} Schnitte, {n_sp} Holme, {n_ted} Rudersegmente")

for fname, f in geo["fuselages"].items():
    ok(c.put(f"/aeroplanes/{pid}/fuselages/{fname}",
             json={"name": fname, "x_secs": f["x_secs"]}), f"Rumpf {fname}")
    print(f"  {fname}: {len(f['x_secs'])} Schnitte")

m = geo["total_mass_kg"]
ok(c.post(f"/aeroplanes/{pid}/total_mass_kg", json={"total_mass_kg": m}), "Masse")
ok(c.post(f"/aeroplanes/{pid}/assumptions"), "Annahmen anlegen")
cells, mah = CELLS, MAH
e_wh = cells * 3.7 * mah / 1000                          # nominal LiPo cell voltage
for p, v in (("mass", m), ("cg_x", geo["xyz_ref"][0]), ("battery_capacity_wh", e_wh)):
    ok(c.put(f"/aeroplanes/{pid}/assumptions/{p}", json={"estimate_value": v}), f"Annahme {p}")
print(f"  Masse {m} kg, cg_x {geo['xyz_ref'][0]} m, Akku {akku.split(',')[0]} -> {cells}S {mah:.0f} mAh = {e_wh:.2f} Wh")
