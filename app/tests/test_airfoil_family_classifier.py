"""Tests for the airfoil family classifier (Task 4, gh-821; Item 3, gh-825).

Uses hand-built minimal coordinate arrays to test each family type.

gh-825 item 3: Improved flat-bottom detection.
  The original strict threshold (mean |y_lower| < 0.002) was too narrow —
  it only detects true y=0 lower surfaces. Real flat-bottom airfoils
  (Clark Y, Gottingen 417a) have a slightly curved forward section with
  a near-flat aft region. The improved heuristic keys on low curvature
  of the lower surface aft of 20% chord, not on absolute y magnitude.

NOTE: Stored AirfoilGeometryModel.family values may change after this
improvement. A PO-run re-backfill is required post-merge.
"""

from __future__ import annotations

import numpy as np
import pytest


# Frozen set of valid output labels
VALID_FAMILIES = frozenset(["flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"])


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
    """Verify every output is in the frozen literal set (gh-825 item 3)."""
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
