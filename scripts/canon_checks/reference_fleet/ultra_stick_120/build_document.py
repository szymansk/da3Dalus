"""Build the geometry document of the Hangar 9 Ultra Stick 120 (NASA FASER) from published values.

Run from the repository root:

    python scripts/canon_checks/reference_fleet/ultra_stick_120/build_document.py

It writes ``aero_kernel/reference/ultra_stick_120/ultra_stick_120.airplane.json``. Every number
below names its source; ``aero_kernel/reference/README.md`` repeats which values are published,
which are measured on the plan and which are assumptions.

Sources:
    [A] Jim Feldmann, "Ultra Stick LW - A Modified Hangar 9 Ultra Stick", RCM February 2002,
        pp. 100-114: the table of dimensions on p. 101. The conversion leaves wing, stabiliser
        and elevator "just as they come".
    [L] RCM plan no. 1307 of the same article (Outerzone oz13447): a side view at full size of the
        kit fuselage (drawn upside-down), the wing section, the stabiliser section and the fin
        with rudder. Measured on the bitmap (72 points per inch, checked on the plan's own scale
        bar); sheet coordinates in inches, x to the right (aft), y downwards.
    [F] Owens, Cox, Morelli, "Development of a Low-Cost Sub-Scale Aircraft for Flight Research:
        The FASER Project", NASA NTRS 20060022541 (2006), Tables 1 and 2: the same kit as flown by
        NASA.

The document's axes: x aft from the kit firewall, y to the right wing, z up from the flat bottom of
the kit fuselage (the plan draws the fuselage upside-down, so the plan's flat top line is the
bottom here).
"""

import json
from pathlib import Path
from typing import Any

OUTPUT = (
    Path(__file__).resolve().parents[4]
    / "aero_kernel"
    / "reference"
    / "ultra_stick_120"
    / "ultra_stick_120.airplane.json"
)

INCH = 0.0254
FOOT = 0.3048
WING_AIRFOIL = "./naca0015.dat"  # ASSUMPTION, see WING_THICKNESS_IN
TAIL_AIRFOIL = "./naca0006.dat"  # ASSUMPTION: [A] "stab airfoil section: flat", 0.5 in thick on [L]

# --- Sheet coordinates of [L], inches ----------------------------------------------------------
SHEET_FIREWALL_X = 10.33  # the line labelled KIT FIREWALL
SHEET_FLAT_LINE_Y = 15.80  # the straight edge of the kit fuselage, its bottom when upright
SHEET_WING_LE_X = 17.96
SHEET_WING_HINGE_X = 32.14  # the blunt end of the drawn section: where the aileron starts
SHEET_WING_CHORD_LINE_Y = 20.65  # midway between the surfaces, 19.38 and 21.92 at x = 21
SHEET_STAB_LE_X = 54.45
SHEET_STAB_PLANE_Y = 16.01  # midway between its faces at 15.76 and 16.26
SHEET_RUDDER_HINGE_X = 62.30  # the fin post, 62.16 to 62.45
# Fin leading edge and rudder trailing edge are straight lines on [L]; two points of each, as
# (height above the stabiliser plane, sheet x).
SHEET_FIN_LE = ((1.01, 50.60), (7.01, 58.34))
SHEET_RUDDER_TE = ((1.01, 68.22), (7.01, 65.56))
FIN_TIP_HEIGHT_IN = 7.90  # the flat top of the fin above the stabiliser plane
# The sloping edge of the kit fuselage (its top when upright), as (sheet x, sheet y).
SHEET_FUSELAGE_TOP = (
    (10.33, 20.20),
    (12.00, 20.42),
    (17.96, 20.80),
    (32.14, 20.94),
    (36.00, 20.42),
    (40.00, 19.84),
    (44.00, 19.30),
    (48.00, 18.76),
    (52.00, 18.22),
    (62.30, 16.85),
)

# --- Wing ---------------------------------------------------------------------------------------
WING_SPAN_IN = 76.0  # [A]
WING_AREA_IN2 = 1214.0  # [A]
# ASSUMPTION: constant chord = area / span. [A] calls the planform a "slight taper" and gives an
# average chord of 16-3/4 in, which with 76 in is 1273 in2, not its own 1214 in2; [F] gives taper
# ratio 1 and 8.28 ft2 with 6.29 ft, a mean of 15.8 in. Area and span are used.
WING_CHORD_IN = WING_AREA_IN2 / WING_SPAN_IN
WING_TIP_RISE_IN = 1.0  # [A] "dihedral, each tip: 1 inch"
# The section drawn on [L] is 2.54 in thick at its thickest (x = 21), 15.9 % of the chord, and
# symmetrical ([A]). ASSUMPTION: NACA 0015 stands in for the kit's section, whose thickest point
# lies further forward (22 % of the chord against 30 %).
WING_THICKNESS_IN = 2.54
# ASSUMPTION: the aileron spans the outer half of each wing. The kit wing has an inboard flap and
# an outboard aileron of unpublished spans; the flaps are not modelled (no published deflection).
AILERON_START_IN = 19.0
AILERON_END_IN = 37.0
# [A] gives the throws as lengths only (elevator and aileron 3/4 in to 1-1/4 in, rudder 1-3/4 in to
# 3 in); with control-surface chords that are measured or assumed here they give no reliable angle,
# so the document states no deflection stops.

# --- Horizontal stabiliser, [A] -----------------------------------------------------------------
STAB_SPAN_IN = 28.75
STAB_ROOT_CHORD_IN = 11.25  # "stabilizer chord (inc. elev.)"; 11.2 in on [L]
STAB_AREA_IN2 = 302.0
# ASSUMPTION: a straight taper with an unswept trailing edge reproduces span, root chord and area;
# the elevator takes a third of the root chord with a constant chord. Neither is published.
ELEVATOR_CHORD_IN = STAB_ROOT_CHORD_IN / 3.0

# --- Mass properties and body, [F] --------------------------------------------------------------
CG_FRACTION_OF_CHORD = 0.25  # Table 2, x_cg / c
CG_HEIGHT_FRACTION_OF_CHORD = 0.165  # Table 2, above the bottom of the fuselage
FASER_CHORD_FT = 1.42  # Table 1, mean geometric chord: the length Table 2 refers to
FUSELAGE_MAX_WIDTH_FT = 0.3958  # Table 1
# ASSUMPTION: the body has its greatest width from the firewall to the wing's hinge line and
# narrows in a straight line to this width at the fin post; superellipse exponent 4 (the kit body
# is a box; with exponent 10 and the open front face the kernel's glide optimisation returned NaN).
FUSELAGE_TAIL_WIDTH_IN = 1.0
FUSELAGE_EXPONENT = 4.0


def at_height(line: tuple[tuple[float, float], tuple[float, float]], height: float) -> float:
    """Sheet x of a straight edge of the fin at a height above the stabiliser plane."""
    (h0, x0), (h1, x1) = line
    return x0 + (x1 - x0) * (height - h0) / (h1 - h0)


def aft(sheet_x: float) -> float:
    """Sheet x as metres aft of the kit firewall."""
    return round((sheet_x - SHEET_FIREWALL_X) * INCH, 6)


def up(sheet_y: float) -> float:
    """Sheet y as metres above the flat bottom of the upright kit fuselage."""
    return round((sheet_y - SHEET_FLAT_LINE_Y) * INCH, 6)


def device(name: str, role: str, hinge_root: float, hinge_tip: float) -> Any:
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
            "deflection_deg": 0.0,
            "symmetric": symmetric,
        },
    }


def section(x_m: float, y_m: float, z_m: float, chord_in: float, foil: str) -> Any:
    """One rib; every surface of this aircraft sits at zero incidence ([L]: "0-0")."""
    return {
        "xyz_le": [x_m, round(y_m, 6), round(z_m, 6)],
        "chord": round(chord_in * INCH, 6),
        "twist": 0.0,
        "airfoil": foil,
    }


def wing() -> Any:
    """The constant-chord wing with its aileron segment."""
    half_span = WING_SPAN_IN / 2.0
    aileron_chord = WING_CHORD_IN - (SHEET_WING_HINGE_X - SHEET_WING_LE_X)
    hinge = 1.0 - aileron_chord / WING_CHORD_IN
    aileron = device("aileron", "aileron", hinge, hinge)
    stations = (0.0, AILERON_START_IN, AILERON_END_IN, half_span)
    return {
        "name": "main_wing",
        "surface_type": "main_wing",
        "symmetric": True,
        "design_model": "asb",
        "x_secs": [
            section(
                aft(SHEET_WING_LE_X),
                s * INCH,
                up(SHEET_WING_CHORD_LINE_Y) + s / half_span * WING_TIP_RISE_IN * INCH,
                WING_CHORD_IN,
                WING_AIRFOIL,
            )
            | extra
            for s, extra in zip(stations, ({}, aileron, {}, {}), strict=True)
        ],
    }


def horizontal_tail() -> Any:
    """The stabiliser: straight taper, unswept trailing edge, constant-chord elevator."""
    half_span = STAB_SPAN_IN / 2.0
    tip_chord = 2.0 * STAB_AREA_IN2 / STAB_SPAN_IN - STAB_ROOT_CHORD_IN
    elevator = device(
        "elevator",
        "elevator",
        1.0 - ELEVATOR_CHORD_IN / STAB_ROOT_CHORD_IN,
        1.0 - ELEVATOR_CHORD_IN / tip_chord,
    )
    z = up(SHEET_STAB_PLANE_Y)
    root = section(aft(SHEET_STAB_LE_X), 0.0, z, STAB_ROOT_CHORD_IN, TAIL_AIRFOIL) | elevator
    tip = section(
        aft(SHEET_STAB_LE_X + STAB_ROOT_CHORD_IN - tip_chord),
        half_span * INCH,
        z,
        tip_chord,
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
    """Fin and rudder from the stabiliser plane to the fin's top, as outlined on [L]."""
    ribs = []
    for height in (0.0, FIN_TIP_HEIGHT_IN):
        leading, trailing = at_height(SHEET_FIN_LE, height), at_height(SHEET_RUDDER_TE, height)
        rib = section(
            aft(leading),
            0.0,
            up(SHEET_STAB_PLANE_Y) + height * INCH,
            trailing - leading,
            TAIL_AIRFOIL,
        )
        ribs.append((rib, (SHEET_RUDDER_HINGE_X - leading) / (trailing - leading)))
    (root, hinge_root), (tip, hinge_tip) = ribs
    rudder = device("rudder", "rudder", hinge_root, hinge_tip)
    return {
        "name": "vertical_tail",
        "surface_type": "vertical_tail",
        "symmetric": False,
        "design_model": "asb",
        "x_secs": [root | rudder, tip],
    }


def fuselage() -> Any:
    """The kit fuselage from the firewall to the fin post: flat bottom, sloping top."""
    half_width = FUSELAGE_MAX_WIDTH_FT * FOOT / 2.0
    tail_half_width = FUSELAGE_TAIL_WIDTH_IN * INCH / 2.0
    sections = []
    for sheet_x, sheet_y in SHEET_FUSELAGE_TOP:
        behind_wing = (sheet_x - SHEET_WING_HINGE_X) / (SHEET_RUDDER_HINGE_X - SHEET_WING_HINGE_X)
        narrowing = min(max(behind_wing, 0.0), 1.0)
        height = up(sheet_y)
        sections.append(
            {
                "xyz": [aft(sheet_x), 0.0, round(height / 2.0, 6)],
                "a": round(half_width + (tail_half_width - half_width) * narrowing, 6),
                "b": round(height / 2.0, 6),
                "n": FUSELAGE_EXPONENT,
            }
        )
    return {"name": "fuselage", "x_secs": sections, "symmetric": False, "role": "fuselage"}


def document() -> Any:
    """The whole aircraft."""
    faser_chord = FASER_CHORD_FT * FOOT
    return {
        "name": "ULTRA_STICK_120",
        "xyz_ref": [
            round(aft(SHEET_WING_LE_X) + CG_FRACTION_OF_CHORD * faser_chord, 6),
            0.0,
            round(CG_HEIGHT_FRACTION_OF_CHORD * faser_chord, 6),
        ],
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
