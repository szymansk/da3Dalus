"""Build the geometry document of the Great Planes Avistar Elite (UAVDB) from its published values.

Run from the repository root:

    python scripts/canon_checks/reference_fleet/avistar_elite/build_document.py

It writes ``aero_kernel/reference/avistar_elite/avistar_elite.airplane.json``. Every number below
names its source; ``aero_kernel/reference/README.md`` repeats which values are published and which
are assumptions.

Sources:
    [P] Dantsker, Caccamo, Vahora, Mancuso: "Flight & Ground Testing Data Set for an Unmanned
        Aircraft: Great Planes Avistar Elite", AIAA 2020-0780. Table 1 (airframe), Table 4 (flight
        surfaces from the 3D scan; x towards the tail, y towards the right wing, z up, millimetres),
        Figures 4 and 5 (side and top outline of the scan).
    [M] Great Planes, Avistar Elite instruction manual GPMA1005: balance point and control throws.
"""

import json
import math
from pathlib import Path
from typing import Any

OUTPUT = (
    Path(__file__).resolve().parents[4]
    / "aero_kernel"
    / "reference"
    / "avistar_elite"
    / "avistar_elite.airplane.json"
)

MM = 1e-3
WING_AIRFOIL = "./avistar.dat"  # [P]: AVISTAR, verified against the UIUC Airfoil Database
TAIL_AIRFOIL = "./naca0006.dat"  # ASSUMPTION: [P] only plots the thin symmetric tail sections

# --- Wing, [P] Table 4 -------------------------------------------------------------------------
WING_LE_X_MM = 380.4
WING_LE_Z_MM = 95.5
WING_INCIDENCE_DEG = 3.58
WING_CHORD_MM = 237.10
WING_HALF_SPAN_MM = 793.75
WING_DIHEDRAL_DEG = 0.9

# Control surfaces. Chord: [M] p. 29 gives each throw as a length at the trailing edge, measured at
# the widest part of the surface, and an angle, so chord = throw / sin(angle). Aileron: 10 mm at
# 11 deg and 14 mm at 17 deg, 48 to 52 mm.
# ASSUMPTION: every control surface has that chord over its whole span.
# ASSUMPTION: the aileron runs from mid half-span to just inside the tip; no source publishes its
# span. The flaps inboard of it are not modelled: every published test flew with 0 deg of flap
# ([P] section V) and neither their span nor their throw is published.
AILERON_CHORD_MM = 50.0
AILERON_START_MM = 400.0
AILERON_END_MM = 770.0
AILERON_STOP_DEG = 17.0  # [M] high rate

# --- Horizontal stabiliser, [P] Table 4 --------------------------------------------------------
HTAIL_LE_X_MM = 1160.0
HTAIL_LE_Z_MM = -2.04
HTAIL_INCIDENCE_DEG = 2.36
HTAIL_ROOT_CHORD_MM = 210.0
HTAIL_TIP_Y_MM = 291.0
HTAIL_TIP_CHORD_MM = 110.0
HTAIL_TIP_OFFSET_MM = 100.0
ELEVATOR_CHORD_MM = 41.0  # [M]: 8 mm at 11 deg and 11 mm at 16 deg, 40 to 42 mm
ELEVATOR_STOP_DEG = 16.0  # [M] high rate

# --- Vertical stabiliser, [P] Table 4 ("y span pos" is the height above the root) ---------------
VTAIL_LE_X_MM = 1160.0
VTAIL_LE_Z_MM = 17.96
VTAIL_ROOT_CHORD_MM = 273.0
VTAIL_ROOT_OFFSET_MM = -95.0
VTAIL_TIP_HEIGHT_MM = 200.0
VTAIL_TIP_CHORD_MM = 96.0
VTAIL_TIP_OFFSET_MM = 133.0
# ASSUMPTION: the fin has no incidence. Table 4 prints 2.36 deg in the fin's row, the stabiliser's
# value; a fin set 2.36 deg to the plane of symmetry is taken as a copying slip of the table.
VTAIL_INCIDENCE_DEG = 0.0
RUDDER_CHORD_MM = 58.0  # [M]: 13 mm at 13 deg and 22 mm at 22 deg
RUDDER_STOP_DEG = 22.0  # [M] high rate

# --- Balance point, [M]: 84 mm behind the leading edge at the fuselage side ---------------------
# ASSUMPTION: the tested aircraft balances there ([P] does not publish its centre of gravity).
# ASSUMPTION: the reference point lies on the x axis of the scan (z = 0); no source gives its height.
CG_BEHIND_LE_MM = 84.0

# --- Fuselage: read off [P] Figures 4 and 5 (about +-5 mm) ---------------------------------------
# (x, top z, bottom z, half width) in millimetres. Between x = 380 and x = 617 the top is the
# underside of the wing. ASSUMPTION: superellipse exponent 4 (a box with rounded corners).
FUSELAGE_STATIONS_MM = (
    (0.0, 0.0, 0.0, 0.0),
    (80.0, 15.0, -35.0, 30.0),
    (160.0, 35.0, -65.0, 45.0),
    (255.0, 40.0, -82.0, 49.0),
    (380.0, 95.0, -92.0, 53.0),
    (450.0, 95.0, -91.0, 54.0),
    (617.0, 80.0, -82.0, 52.0),
    (730.0, 50.0, -75.0, 48.0),
    (800.0, 42.0, -72.0, 45.0),
    (1000.0, 28.0, -58.0, 33.0),
    (1150.0, 22.0, -45.0, 21.0),
    (1320.0, 5.0, -35.0, 8.0),
)
FUSELAGE_EXPONENT = 4.0


def device(name: str, role: str, hinge_root: float, hinge_tip: float, stop_deg: float) -> Any:
    """The two representations of one control surface on the segment that starts at a section."""
    symmetric = role != "aileron"
    return {
        "control_surface": {
            "name": name,
            "hinge_point": round(hinge_root, 4),
            "symmetric": symmetric,
            "deflection": 0.0,
        },
        "trailing_edge_device": {
            "name": name,
            "role": role,
            "rel_chord_root": round(hinge_root, 4),
            "rel_chord_tip": round(hinge_tip, 4),
            "positive_deflection_deg": stop_deg,
            "negative_deflection_deg": stop_deg,
            "deflection_deg": 0.0,
            "symmetric": symmetric,
        },
    }


def section(x_mm: float, y_mm: float, z_mm: float, chord_mm: float, twist: float, foil: str) -> Any:
    """One rib in metres and degrees."""
    return {
        "xyz_le": [round(x_mm * MM, 6), round(y_mm * MM, 6), round(z_mm * MM, 6)],
        "chord": round(chord_mm * MM, 6),
        "twist": twist,
        "airfoil": foil,
    }


def wing() -> Any:
    """The rectangular main wing with its aileron segment."""
    hinge = 1.0 - AILERON_CHORD_MM / WING_CHORD_MM
    rise = math.tan(math.radians(WING_DIHEDRAL_DEG))  # "y span pos" is a y coordinate
    stations = (0.0, AILERON_START_MM, AILERON_END_MM, WING_HALF_SPAN_MM)
    devices = ({}, device("aileron", "aileron", hinge, hinge, AILERON_STOP_DEG), {}, {})
    return {
        "name": "main_wing",
        "surface_type": "main_wing",
        "symmetric": True,
        "design_model": "asb",
        "x_secs": [
            section(
                WING_LE_X_MM,
                s,
                WING_LE_Z_MM + s * rise,
                WING_CHORD_MM,
                WING_INCIDENCE_DEG,
                WING_AIRFOIL,
            )
            | extra
            for s, extra in zip(stations, devices, strict=True)
        ],
    }


def horizontal_tail() -> Any:
    """The tapered stabiliser with a straight trailing edge and a constant-chord elevator."""
    root = section(
        HTAIL_LE_X_MM, 0.0, HTAIL_LE_Z_MM, HTAIL_ROOT_CHORD_MM, HTAIL_INCIDENCE_DEG, TAIL_AIRFOIL
    ) | device(
        "elevator",
        "elevator",
        1.0 - ELEVATOR_CHORD_MM / HTAIL_ROOT_CHORD_MM,
        1.0 - ELEVATOR_CHORD_MM / HTAIL_TIP_CHORD_MM,
        ELEVATOR_STOP_DEG,
    )
    tip = section(
        HTAIL_LE_X_MM + HTAIL_TIP_OFFSET_MM,
        HTAIL_TIP_Y_MM,
        HTAIL_LE_Z_MM,
        HTAIL_TIP_CHORD_MM,
        HTAIL_INCIDENCE_DEG,
        TAIL_AIRFOIL,
    )
    return {
        "name": "horizontal_tail",
        "surface_type": "horizontal_tail",
        "symmetric": True,
        "design_model": "asb",
        "x_secs": [root, tip],
    }


def vertical_tail() -> Any:
    """The fin with a constant-chord rudder."""
    root = section(
        VTAIL_LE_X_MM + VTAIL_ROOT_OFFSET_MM,
        0.0,
        VTAIL_LE_Z_MM,
        VTAIL_ROOT_CHORD_MM,
        VTAIL_INCIDENCE_DEG,
        TAIL_AIRFOIL,
    ) | device(
        "rudder",
        "rudder",
        1.0 - RUDDER_CHORD_MM / VTAIL_ROOT_CHORD_MM,
        1.0 - RUDDER_CHORD_MM / VTAIL_TIP_CHORD_MM,
        RUDDER_STOP_DEG,
    )
    tip = section(
        VTAIL_LE_X_MM + VTAIL_TIP_OFFSET_MM,
        0.0,
        VTAIL_LE_Z_MM + VTAIL_TIP_HEIGHT_MM,
        VTAIL_TIP_CHORD_MM,
        VTAIL_INCIDENCE_DEG,
        TAIL_AIRFOIL,
    )
    return {
        "name": "vertical_tail",
        "surface_type": "vertical_tail",
        "symmetric": False,
        "design_model": "asb",
        "x_secs": [root, tip],
    }


def fuselage() -> Any:
    """The body as superellipse sections through the outline read off the scan figures."""
    return {
        "name": "fuselage",
        "x_secs": [
            {
                "xyz": [round(x * MM, 6), 0.0, round((top + bottom) / 2 * MM, 6)],
                "a": round(half_width * MM, 6),
                "b": round((top - bottom) / 2 * MM, 6),
                "n": FUSELAGE_EXPONENT,
            }
            for x, top, bottom, half_width in FUSELAGE_STATIONS_MM
        ],
        "symmetric": False,
        "role": "fuselage",
    }


def document() -> Any:
    """The whole aircraft."""
    return {
        "name": "AVISTAR_ELITE",
        "xyz_ref": [round((WING_LE_X_MM + CG_BEHIND_LE_MM) * MM, 6), 0.0, 0.0],
        "wings": {
            "main_wing": wing(),
            "horizontal_tail": horizontal_tail(),
            "vertical_tail": vertical_tail(),
        },
        "fuselages": {"fuselage": fuselage()},
    }


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document(), indent=2) + "\n")
    print(OUTPUT)
