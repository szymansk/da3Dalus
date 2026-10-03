"""Assemble the e-Hawk glider into one da3Dalus geometry file (ehawk.airplane.json).

Second member of the reference fleet (after BRYAN). Sources, all from the maintainer's projects:
  * wing:  e-Hawk.airplane.json (eHawk_Tragflaeche, MH32), copied as ehawk_fluegel.airplane.json
  * fuselage, V-tail, mass, CG, incidence: eHawk_Rumpf_R4 (Bericht_Rumpf_R4.md, auslegung.json,
    leitwerk.step, eHawk_R4_Rumpf.step). Frame: X aft from the wing-root leading edge, Y right, Z up.

Read from the STEP files (2026-10-03, cadquery sections):
  * pod: outer skins "Nase" (x -299..-58) and "Haut hinten" (x -82..205), width x height per station
    below; CFK tube 10 mm from x 205 to the tail; pod axis z = -19.
  * V-tail half: root LE (623.2, 10.5, -11.3) chord 87, tip LE (644.6, 194.0, 130.6) chord 57
    -> V angle atan(141.9 / 183.5) = 37.7 deg (Drela check from the design areas: 37.6 deg).
    Rudder ("ruddervator") from x 680.8 -> hinge at about 0.65 of the chord.
Declared assumptions:
  * tail airfoil: 2 mm balsa plate (platte_2mm.dat, the BRYAN plate section)
  * wing incidence +1.5 deg relative to the tube (EWD per the report, tail 0 deg) -> wing twist +1.5
  * pod sections are super-ellipses with n = 2 (round, 34 x 34 mm at the widest)
  * CG z = -0.015 m (pod centre; not stated in the report)
  * multi-segment control surface: consecutive segments with the same TED name form one surface and
    inherit the first segment's symmetric flag, throws and role (maintainer 2026-10-03; the source
    carries constructor defaults on the continuations — app bug #1155). The e-Hawk's four "aileron"
    segments are therefore one antisymmetric aileron, +-35 deg.
"""

import json
import pathlib

HERE = pathlib.Path(__file__).parent
wing_src = json.loads((HERE / "ehawk_fluegel.airplane.json").read_text())

wing = wing_src["wings"]["Tragflaeche"]
for x in wing["x_secs"]:
    x["twist"] = x.get("twist", 0.0) + 1.5
    x["airfoil"] = "./mh32.dat"

# inheritance along a run of same-named control surfaces (#1155)
first = None
for x in wing["x_secs"]:
    ted = x.get("trailing_edge_device")
    if not ted:
        first = None
        continue
    if first is None or ted.get("name") != first.get("name"):
        first = ted
        first["role"] = first.get("role") or ("aileron" if first.get("name") == "aileron" else None)
    else:
        for k in ("symmetric", "positive_deflection_deg", "negative_deflection_deg", "role"):
            ted[k] = first.get(k)
    if x.get("control_surface"):
        x["control_surface"]["symmetric"] = ted["symmetric"]

# pod stations from the STEP sections: x, width, height, z-centre  [mm]
POD = [(-298, 1.4, 1.4, -19.2), (-290, 6.7, 6.6, -19.2), (-270, 17.6, 17.4, -19.2),
       (-240, 28.7, 28.3, -19.2), (-200, 34.0, 33.5, -19.2), (-60, 34.0, 33.5, -19.2),
       (0, 33.4, 34.0, -17.2), (40, 32.4, 27.0, -18.2), (80, 30.6, 24.5, -16.8),
       (120, 28.1, 22.6, -15.8), (160, 24.6, 22.0, -15.4), (200, 19.7, 13.8, -18.7),
       (240, 10.0, 10.0, -19.0), (680, 10.0, 10.0, -19.0)]
fuselage = {"x_secs": [{"xyz": [x / 1000, 0.0, zc / 1000], "a": w / 2000, "b": h / 2000, "n": 2.0}
                       for x, w, h, zc in POD]}

ROOT, TIP = (0.6232, 0.0105, -0.0113, 0.087), (0.6446, 0.1940, 0.1306, 0.057)
rudder = {"name": "ruddervator", "hinge_point": 0.65, "symmetric": False, "deflection": 0.0}
vtail = {"symmetric": True, "x_secs": [
    {"xyz_le": list(ROOT[:3]), "chord": ROOT[3], "twist": 0.0, "airfoil": "./platte_2mm.dat",
     "control_surface": rudder,
     "trailing_edge_device": {"name": "ruddervator", "role": "ruddervator", "rel_chord_root": 0.65,
                              "rel_chord_tip": 0.63, "positive_deflection_deg": 28,
                              "negative_deflection_deg": 28, "symmetric": False}},
    {"xyz_le": list(TIP[:3]), "chord": TIP[3], "twist": 0.0, "airfoil": "./platte_2mm.dat"}]}

out = {"name": "e-Hawk", "total_mass_kg": 0.280, "xyz_ref": [0.0564, 0.0, -0.015],
       "wings": {"Tragflaeche": wing, "V-Leitwerk": vtail}, "fuselages": {"Rumpf": fuselage},
       "herkunft": __doc__.strip().splitlines()[0]}
(HERE / "ehawk.airplane.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print("-> ehawk.airplane.json")
