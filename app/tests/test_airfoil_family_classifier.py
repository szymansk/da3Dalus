"""Tests for the airfoil family classifier (Task 4, gh-821; Item 1, gh-825).

Uses hand-built minimal coordinate arrays to test each family type AND loads
real Clark Y coordinates from components/airfoils/clarky.dat to verify the
canonical flat-bottom airfoil is classified correctly.

gh-825 item 1 (re-tuned): Improved flat-bottom detection.
  The previous aft-flatness heuristic (max |y_lower| over aft region) failed
  for real flat-bottom airfoils like Clark Y because their lower surface runs
  significantly below the chord line (y ≈ −0.02 to −0.03 in the aft region).
  The new heuristic uses the QUADRATIC COEFFICIENT of a polynomial fit to
  y_lower over [0.30, 1.0]: flat-bottom airfoils have a near-linear lower
  surface (coeff < 0.005) while truly cambered airfoils (NACA 4412, NACA 4418)
  have a curved lower surface (coeff > 0.009).

  Additionally, the symmetric check now fires BEFORE flat_bottom to prevent
  purely symmetric airfoils (NACA 0000) from being mis-labelled as flat_bottom.

NOTE: Stored AirfoilGeometryModel.family values change after this re-tune.
A PO-run re-backfill (--force) is required post-merge (gh-825 item 1).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


# Frozen set of valid output labels
VALID_FAMILIES = frozenset(["flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"])

# Relative path from project root to the bundled airfoil .dat files
_AIRFOILS_DIR = Path("components/airfoils")


def _load_dat(filename: str) -> np.ndarray:
    """Load airfoil coordinates from a Selig .dat file in components/airfoils/."""
    path = _AIRFOILS_DIR / filename
    coords = []
    with open(path) as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    coords.append([float(parts[0]), float(parts[1])])
                except ValueError:
                    pass  # skip header / comment lines
    if len(coords) < 10:
        raise ValueError(f"Too few coordinates in {filename}: {len(coords)}")
    return np.array(coords, dtype=float)


def _make_symmetric_naca0012():
    """Build minimal NACA 0012-like coords: truly symmetric, no camber."""
    x = np.linspace(0, 1, 30)
    # Symmetric: upper == -lower, no camber
    t = 0.12 * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    upper = np.column_stack([x, t])
    lower = np.column_stack([x, -t])
    return np.vstack([upper[::-1], lower[1:]])


def _make_flat_bottom():
    """Strict flat-bottom: lower surface is exactly y=0 everywhere."""
    x = np.linspace(0, 1, 30)
    upper = np.column_stack([x, 0.1 * np.sin(np.pi * x)])
    lower = np.column_stack([x, np.zeros_like(x)])
    return np.vstack([upper[::-1], lower[1:]])


def _make_clark_y_like():
    """Clark-Y-like flat-bottom: lower surface has a small forward bulge
    (~1.2% chord peak at x≈0.1) then is nearly flat from ~25% chord to TE.

    This mimics real flat-bottom airfoils (Clark Y, Gottingen 417a) where the
    lower surface is NOT a perfect y=0 line — it has a slight convex forward
    section but the aft lower surface (x > 0.25) has max |y_lower| ≤ ~0.004,
    well within the flat-bottom detection band.

    The aft lower surface (x ≥ 0.25) has values ≤ 0.004 with very low curvature,
    which clearly distinguishes it from semi-symmetric airfoils where the lower
    surface tracks the camber line (y_lower ≈ 0.005–0.007 in the aft region).
    """
    x = np.linspace(0, 1, 50)
    # Upper surface: cambered and thick, Clark-Y-like (~11.5% max thickness)
    t = 0.115 * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    m, p = 0.035, 0.35
    camber_upper = np.where(
        x <= p,
        (m / p**2) * (2 * p * x - x**2),
        (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x**2),
    )
    y_upper = camber_upper + t

    # Lower surface: small forward bulge (~1.2% at x=0.12), then near-flat aft
    # Forward (x ≤ 0.25): sinusoidal bulge, peaks at x~0.12
    # Aft (x > 0.25): very small nearly-flat values (max ~0.003–0.004)
    y_lower = np.where(
        x <= 0.25,
        0.012 * np.sin(np.pi * x / 0.25),  # forward bulge, peak ~1.2% at x≈0.125
        0.003 * (1.0 - (x - 0.25) / 0.75),  # linear taper from 0.003 to 0 at TE
    )

    upper = np.column_stack([x, y_upper])
    lower = np.column_stack([x, y_lower])
    return np.vstack([upper[::-1], lower[1:]])


def _make_cambered():
    """Clearly cambered airfoil (NACA 4412-like): significant positive camber throughout.

    Uses the correct NACA 4-digit camber formula: positive camber for all x.
    m=0.04 (max camber), p=0.4 (position of max camber).
    """
    x = np.linspace(0, 1, 30)
    m, p = 0.04, 0.4
    # NACA camber line: always positive for forward-loaded airfoil
    camber = np.where(
        x <= p,
        (m / p**2) * (2 * p * x - x**2),
        (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x**2),
    )
    t = 0.12 * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    upper = np.column_stack([x, camber + t])
    lower = np.column_stack([x, camber - t])
    return np.vstack([upper[::-1], lower[1:]])


def _make_reflexed():
    """Reflexed airfoil: camber line has negative (reflexed) value at the TE."""
    x = np.linspace(0, 1, 40)
    # Camber line: rises then dips below at TE (reflex)
    camber = 0.03 * np.sin(np.pi * x) - 0.03 * x**3
    t = 0.09 * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    upper = np.column_stack([x, camber + t])
    lower = np.column_stack([x, camber - t])
    return np.vstack([upper[::-1], lower[1:]])


def _make_semi_symmetric():
    """Semi-symmetric: small camber, between symmetric and cambered."""
    x = np.linspace(0, 1, 30)
    camber = 0.015 * np.sin(np.pi * x)
    t = 0.10 * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    upper = np.column_stack([x, camber + t])
    lower = np.column_stack([x, camber - t])
    return np.vstack([upper[::-1], lower[1:]])


@pytest.mark.parametrize(
    "coords_fn,expected",
    [
        (_make_symmetric_naca0012, "symmetric"),
        (_make_flat_bottom, "flat_bottom"),
        (
            _make_clark_y_like,
            "flat_bottom",
        ),  # gh-825 item 3: Clark-Y-like must detect as flat_bottom
        (_make_cambered, "cambered"),
        (_make_reflexed, "reflexed"),
        (_make_semi_symmetric, "semi_symmetric"),
    ],
)
def test_classify_family(coords_fn, expected):
    from app.services.airfoil_low_re_service import classify_family

    coords = coords_fn()
    result = classify_family(coords)
    assert result == expected, f"Expected {expected}, got {result}"
    # Also verify output is one of the frozen literals
    assert result in VALID_FAMILIES


def test_classify_family_output_always_valid_literal():
    """Verify every output is in the frozen literal set (gh-825 item 1)."""
    from app.services.airfoil_low_re_service import classify_family

    for coords_fn in [
        _make_symmetric_naca0012,
        _make_flat_bottom,
        _make_clark_y_like,
        _make_cambered,
        _make_reflexed,
        _make_semi_symmetric,
    ]:
        result = classify_family(coords_fn())
        assert result in VALID_FAMILIES, f"classify_family returned invalid literal: {result!r}"


# ---------------------------------------------------------------------------
# Real-coordinates tests — gh-825 item 1
# ---------------------------------------------------------------------------


def test_classify_real_clarky_is_flat_bottom():
    """Clark Y (clarky.dat) must classify as 'flat_bottom'.

    This is the canonical RC flat-bottom airfoil.  Previous code misclassified
    it as 'cambered' because the max-|y_lower| aft heuristic failed: Clark Y's
    lower surface runs at y ≈ −0.02 to −0.03, well above the 0.005 threshold.

    The fix (gh-825 item 1): detect flat-bottom by lower-surface LINEARITY
    (quadratic coefficient of polynomial fit to y_lower over [0.30, 1.0] < 0.005)
    rather than absolute y magnitude.
    """
    from app.services.airfoil_low_re_service import classify_family

    coords = _load_dat("clarky.dat")
    result = classify_family(coords)
    assert result == "flat_bottom", (
        f"Clark Y (clarky.dat) must be 'flat_bottom', got {result!r}. "
        "This regression means the lower-surface linearity fix was reverted."
    )


@pytest.mark.parametrize(
    "filename,expected,description",
    [
        # Flat-bottom family — RC canonical flat-bottoms
        ("clarky.dat", "flat_bottom", "Clark Y (canonical RC flat-bottom)"),
        ("clarkx.dat", "flat_bottom", "Clark X (flat-bottom)"),
        ("clarkv.dat", "flat_bottom", "Clark V (flat-bottom)"),
        ("clarkk.dat", "flat_bottom", "Clark K (flat-bottom)"),
        # Cambered family — must NOT be reclassified as flat_bottom
        ("naca4412.dat", "cambered", "NACA 4412 (genuinely cambered — must NOT be flat_bottom)"),
        # Symmetric family — must NOT be mis-labelled as flat_bottom
        ("naca0006.dat", "symmetric", "NACA 0006 (symmetric — check before flat_bottom)"),
    ],
)
def test_classify_real_airfoil_family_regression(filename: str, expected: str, description: str):
    """Regression suite: real .dat files must classify to their canonical family.

    gh-825 item 1: Verifies the re-tuned heuristic against real airfoil data.
    Key cases:
      - Clark Y family → flat_bottom (the primary fix)
      - NACA 4412 → cambered (must NOT be mis-classified as flat_bottom)
      - NACA 0006 → symmetric (symmetric check fires before flat_bottom)
    """
    from app.services.airfoil_low_re_service import classify_family

    coords = _load_dat(filename)
    result = classify_family(coords)
    assert result == expected, (
        f"{description}: expected {expected!r}, got {result!r} for {filename}"
    )
    assert result in VALID_FAMILIES
