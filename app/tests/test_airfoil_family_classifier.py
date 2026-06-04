"""Tests for the airfoil family classifier (Task 4, gh-821).

Uses hand-built minimal coordinate arrays to test each family type.
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
    """Flat-bottom airfoil: lower surface is flat (y_lower ≈ 0 everywhere)."""
    x = np.linspace(0, 1, 30)
    upper = np.column_stack([x, 0.1 * np.sin(np.pi * x)])
    lower = np.column_stack([x, np.zeros_like(x)])
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
        (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * x - x**2),
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


@pytest.mark.parametrize("coords_fn,expected", [
    (_make_symmetric_naca0012, "symmetric"),
    (_make_flat_bottom, "flat_bottom"),
    (_make_cambered, "cambered"),
    (_make_reflexed, "reflexed"),
    (_make_semi_symmetric, "semi_symmetric"),
])
def test_classify_family(coords_fn, expected):
    from app.services.airfoil_low_re_service import classify_family

    coords = coords_fn()
    result = classify_family(coords)
    assert result == expected, f"Expected {expected}, got {result}"
    # Also verify output is one of the frozen literals
    assert result in VALID_FAMILIES


def test_classify_family_output_always_valid_literal():
    """Verify every output is in the frozen literal set."""
    from app.services.airfoil_low_re_service import classify_family

    for coords_fn in [_make_symmetric_naca0012, _make_flat_bottom, _make_cambered,
                      _make_reflexed, _make_semi_symmetric]:
        result = classify_family(coords_fn())
        assert result in VALID_FAMILIES, f"classify_family returned invalid literal: {result!r}"
