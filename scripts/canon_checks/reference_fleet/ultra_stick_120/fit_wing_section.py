"""Fit a Kulfan airfoil to the wing section drawn on the Ultra Stick plan and write its ``.dat``.

Run from the repository root (needs AeroSandbox):

    python scripts/canon_checks/reference_fleet/ultra_stick_120/fit_wing_section.py

It writes ``aero_kernel/reference/ultra_stick_120/ultra_stick_120_main_wing_kulfan.dat``.

Source: RCM plan no. 1307 (Outerzone oz13447), the wing section of the kit drawn at full size. The
two surfaces were read off the bitmap at 72 points per inch, one column every 0.2 in, from the
leading edge (sheet x = 17.96) to the blunt end of the drawn section at the hinge line (32.14).
The section is symmetrical (the article's table says so, and the two surfaces lie mirrored about
sheet y = 20.65 within 0.01 in), so the table below holds its half thickness.

ASSUMPTION: behind the hinge line the plan draws nothing. The aileron is taken as a slab that
tapers in a straight line from the thickness at the hinge to a sharp trailing edge at the chord of
the document (wing area / span = 15.97 in, see ``build_document.py``).
"""

from pathlib import Path

import aerosandbox as asb
import numpy as np

OUTPUT = (
    Path(__file__).resolve().parents[4]
    / "aero_kernel"
    / "reference"
    / "ultra_stick_120"
    / "ultra_stick_120_main_wing_kulfan.dat"
)
NAME = "ultra_stick_120_main_wing_kulfan"

CHORD_IN = 1214.0 / 76.0  # wing area / span, as in build_document.py
SHEET_LEADING_EDGE_X = 17.96
SHEET_FIRST_COLUMN_X = 18.1
COLUMN_STEP_IN = 0.2
# Half the distance between the two surfaces, inches, at sheet x = 18.1, 18.3, ... 32.1.
HALF_THICKNESS_IN = (
    0.4132, 0.5833, 0.7153, 0.8194, 0.9097, 0.9722, 1.0347, 1.0833, 1.1285, 1.1771,
    1.1979, 1.2292, 1.2500, 1.2604, 1.2674, 1.2708, 1.2674, 1.2674, 1.2674, 1.2674,
    1.2604, 1.2500, 1.2465, 1.2396, 1.2292, 1.2188, 1.2083, 1.1979, 1.1840, 1.1736,
    1.1562, 1.1424, 1.1285, 1.1042, 1.0938, 1.0694, 1.0521, 1.0312, 1.0104, 0.9931,
    0.9583, 0.9410, 0.9201, 0.8924, 0.8681, 0.8403, 0.8194, 0.7917, 0.7743, 0.7396,
    0.7257, 0.6910, 0.6771, 0.6493, 0.6250, 0.6007, 0.5694, 0.5521, 0.5243, 0.5035,
    0.4722, 0.4514, 0.4271, 0.4028, 0.3785, 0.3438, 0.3194, 0.3021, 0.2708, 0.2431,
    0.2118,
)  # fmt: skip
KULFAN_WEIGHTS_PER_SIDE = 8  # AeroSandbox's default
POINTS_PER_SIDE = 81


def measured_coordinates() -> np.ndarray:
    """The digitised section as Selig coordinates (trailing edge, upper surface, lower surface)."""
    stations = (
        SHEET_FIRST_COLUMN_X
        - SHEET_LEADING_EDGE_X
        + COLUMN_STEP_IN * np.arange(len(HALF_THICKNESS_IN))
    )
    x = np.concatenate(([0.0], stations, [CHORD_IN])) / CHORD_IN
    half = np.concatenate(([0.0], HALF_THICKNESS_IN, [0.0])) / CHORD_IN
    upper = np.column_stack((x[::-1], half[::-1]))
    lower = np.column_stack((x[1:], -half[1:]))
    return np.vstack((upper, lower))


def fitted() -> asb.KulfanAirfoil:
    """The Kulfan airfoil through the digitised section."""
    measured = asb.Airfoil(name=NAME, coordinates=measured_coordinates())
    return measured.to_kulfan_airfoil(n_weights_per_side=KULFAN_WEIGHTS_PER_SIDE)


def dat_text() -> str:
    """The fitted airfoil as a Selig ``.dat`` file."""
    airfoil = fitted().to_airfoil(n_coordinates_per_side=POINTS_PER_SIDE)
    rows = (f"{x:9.6f} {y:9.6f}" for x, y in np.asarray(airfoil.coordinates).tolist())
    return "\n".join((NAME, *rows)) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(dat_text())
    print(OUTPUT)
