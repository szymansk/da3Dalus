"""Unit tests for app/services/airfoil_tags.py (gh-835).

These tests exercise the pure tag-computation helpers with hand-built metric
dicts — no DB required.  They serve as the spec for tag definitions; any change
to threshold values must update both the module docstring and these tests.

Canonical examples used as anchors:
  - NACA 0012 (symmetric, ~12 % t/c, ~0 camber)   → v_stabilizer, h_stabilizer, acro
  - MH60      (reflexed, ~9 % t/c, ~0.5–2 % camber) → winglet-eligible + low_re
  - Clark Y   (flat_bottom, ~11.7 % t/c)            → none of the symmetric roles
"""

from __future__ import annotations

import pytest

from app.services.airfoil_tags import (
    ALL_FAMILIES,
    ALL_ROLE_TAGS,
    HIGH_RE_LOWER_BOUND,
    LOW_RE_CONFIDENCE_GATE,
    LOW_RE_UPPER_BOUND,
    compute_tags,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _polar(reynolds: float, confidence: float) -> dict:
    return {"reynolds": float(reynolds), "min_analysis_confidence": confidence}


# ── Constants contract ────────────────────────────────────────────────────────


def test_threshold_constants():
    assert LOW_RE_UPPER_BOUND == 150_000
    assert HIGH_RE_LOWER_BOUND == 500_000
    assert LOW_RE_CONFIDENCE_GATE == pytest.approx(0.85)


def test_all_role_tags_set():
    assert ALL_ROLE_TAGS == {"v_stabilizer", "h_stabilizer", "acro", "winglet", "low_re", "high_re"}


def test_all_families_set():
    assert ALL_FAMILIES == {"flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"}


# ── No-polar / empty-polar edge cases ────────────────────────────────────────


def test_no_polars_symmetric_gets_stab_and_acro():
    """Symmetric 12 % t/c with zero camber: stab + acro tags even with no polars."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=12.0,
        max_camber_pct=0.0,
        polars=[],
    )
    assert "v_stabilizer" in tags
    assert "h_stabilizer" in tags
    assert "acro" in tags
    # winglet and low_re require polars
    assert "winglet" not in tags
    assert "low_re" not in tags


def test_no_polars_no_low_re():
    """No polar rows → no low_re tag regardless of family/thickness."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=8.0,
        max_camber_pct=0.0,
        polars=[],
    )
    assert "low_re" not in tags
    assert "high_re" not in tags


# ── NACA 0012 canonical case ──────────────────────────────────────────────────


def test_naca0012_gets_v_stab_h_stab_acro():
    """NACA 0012: symmetric, 12 % t/c, ≈ 0 camber → v_stab + h_stab + acro."""
    good_low_re_polar = [_polar(100_000, 0.90), _polar(500_000, 0.92)]
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=12.0,
        max_camber_pct=0.0,
        polars=good_low_re_polar,
    )
    assert "v_stabilizer" in tags
    assert "h_stabilizer" in tags
    assert "acro" in tags


def test_naca0012_also_gets_low_re_when_confident():
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=12.0,
        max_camber_pct=0.0,
        polars=[_polar(100_000, 0.90)],
    )
    assert "low_re" in tags


def test_naca0012_gets_high_re_when_upper_grid_present():
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=12.0,
        max_camber_pct=0.0,
        polars=[_polar(600_000, 0.91)],
    )
    assert "high_re" in tags


# ── v_stabilizer / h_stabilizer gate ─────────────────────────────────────────


def test_stab_requires_symmetric():
    """Non-symmetric airfoil (even thin, zero-camber) does NOT get stab tag."""
    for family in ("flat_bottom", "semi_symmetric", "cambered", "reflexed"):
        tags = compute_tags(
            family=family,
            max_thickness_pct=10.0,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "v_stabilizer" not in tags, f"family={family} should not get v_stabilizer"
        assert "h_stabilizer" not in tags, f"family={family} should not get h_stabilizer"


def test_stab_requires_thickness_between_6_and_15():
    """thickness < 6 or > 15 → no stab tag, even for symmetric."""
    for t in (5.9, 15.1, 20.0):
        tags = compute_tags(
            family="symmetric",
            max_thickness_pct=t,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "v_stabilizer" not in tags, f"t={t} should not get v_stabilizer"
        assert "h_stabilizer" not in tags, f"t={t} should not get h_stabilizer"

    # Boundary values: 6 and 15 must be included
    for t in (6.0, 15.0):
        tags = compute_tags(
            family="symmetric",
            max_thickness_pct=t,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "v_stabilizer" in tags, f"t={t} should get v_stabilizer"
        assert "h_stabilizer" in tags, f"t={t} should get h_stabilizer"


def test_stab_requires_camber_le_0_5():
    """Camber > 0.5 % → no stab tag."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.6,
        polars=[],
    )
    assert "v_stabilizer" not in tags
    assert "h_stabilizer" not in tags


# ── acro gate ────────────────────────────────────────────────────────────────


def test_acro_thickness_window_7_to_12():
    """acro requires 7 <= t <= 12 for symmetric, zero-camber."""
    for t in (6.9, 12.1):
        tags = compute_tags(
            family="symmetric",
            max_thickness_pct=t,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "acro" not in tags, f"t={t} should not get acro"

    # Boundary values: 7 and 12 must be included
    for t in (7.0, 12.0):
        tags = compute_tags(
            family="symmetric",
            max_thickness_pct=t,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "acro" in tags, f"t={t} should get acro"


def test_symmetric_12_5_gets_stab_not_acro():
    """12.5 % t/c: in stab window (6–15) but outside acro window (7–12)."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=12.5,
        max_camber_pct=0.0,
        polars=[],
    )
    assert "v_stabilizer" in tags
    assert "h_stabilizer" in tags
    assert "acro" not in tags


def test_acro_requires_symmetric():
    for family in ("flat_bottom", "cambered", "reflexed", "semi_symmetric"):
        tags = compute_tags(
            family=family,
            max_thickness_pct=10.0,
            max_camber_pct=0.0,
            polars=[],
        )
        assert "acro" not in tags, f"family={family} should not get acro"


# ── winglet gate ──────────────────────────────────────────────────────────────


def test_winglet_requires_thin_low_camber_and_low_re_polar():
    """Thin reflexed with good low-Re polar → winglet tag."""
    tags = compute_tags(
        family="reflexed",
        max_thickness_pct=9.0,
        max_camber_pct=2.0,
        polars=[_polar(100_000, 0.90)],
    )
    assert "winglet" in tags


def test_winglet_missing_when_no_polar():
    """Thin + right family + low camber, but no polar → no winglet tag."""
    tags = compute_tags(
        family="reflexed",
        max_thickness_pct=9.0,
        max_camber_pct=2.0,
        polars=[],
    )
    assert "winglet" not in tags


def test_winglet_missing_when_polar_too_high_re_only():
    """Only high-Re polar present (> 150k) → no winglet tag (needs low-Re)."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=8.0,
        max_camber_pct=1.0,
        polars=[_polar(200_000, 0.92)],  # Re > 150k
    )
    assert "winglet" not in tags


def test_winglet_missing_when_polar_low_confidence():
    """Low-Re polar but confidence below gate → no winglet."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=8.0,
        max_camber_pct=1.0,
        polars=[_polar(100_000, 0.84)],  # confidence just below gate
    )
    assert "winglet" not in tags


def test_winglet_missing_when_too_thick():
    """t/c > 10 → no winglet."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=11.0,
        max_camber_pct=1.0,
        polars=[_polar(100_000, 0.90)],
    )
    assert "winglet" not in tags


def test_winglet_missing_for_cambered_family():
    """'cambered' family is not in the winglet-eligible set."""
    tags = compute_tags(
        family="cambered",
        max_thickness_pct=8.0,
        max_camber_pct=1.0,
        polars=[_polar(100_000, 0.90)],
    )
    assert "winglet" not in tags


def test_winglet_missing_for_flat_bottom():
    """'flat_bottom' family is not in the winglet-eligible set."""
    tags = compute_tags(
        family="flat_bottom",
        max_thickness_pct=8.0,
        max_camber_pct=1.0,
        polars=[_polar(100_000, 0.90)],
    )
    assert "winglet" not in tags


def test_winglet_eligible_families():
    """symmetric, semi_symmetric, reflexed are all winglet-eligible (given other gates met)."""
    for family in ("symmetric", "semi_symmetric", "reflexed"):
        tags = compute_tags(
            family=family,
            max_thickness_pct=8.0,
            max_camber_pct=1.0,
            polars=[_polar(100_000, 0.90)],
        )
        assert "winglet" in tags, f"family={family} should get winglet"


# ── Clark Y canonical case ────────────────────────────────────────────────────


def test_clark_y_gets_no_symmetric_roles():
    """Clark Y is flat_bottom (~11.7 % t/c): none of the symmetric-gated tags."""
    tags = compute_tags(
        family="flat_bottom",
        max_thickness_pct=11.7,
        max_camber_pct=3.9,
        polars=[_polar(100_000, 0.90), _polar(500_000, 0.92)],
    )
    assert "v_stabilizer" not in tags
    assert "h_stabilizer" not in tags
    assert "acro" not in tags
    # winglet also out: flat_bottom family + camber > 3
    assert "winglet" not in tags
    # low_re and high_re are family-agnostic — Clark Y can earn these
    assert "low_re" in tags
    assert "high_re" in tags


# ── MH60 canonical case (reflexed) ───────────────────────────────────────────


def test_mh60_reflexed_gets_winglet_and_low_re():
    """MH60 is reflexed ~9 % t/c, camber ~1.5 %: gets winglet and low_re."""
    tags = compute_tags(
        family="reflexed",
        max_thickness_pct=9.0,
        max_camber_pct=1.5,
        polars=[_polar(100_000, 0.91), _polar(500_000, 0.93)],
    )
    assert "winglet" in tags
    assert "low_re" in tags
    assert "high_re" in tags
    # Not symmetric → no stab / acro
    assert "v_stabilizer" not in tags
    assert "h_stabilizer" not in tags
    assert "acro" not in tags


# ── low_re and high_re confidence gate ───────────────────────────────────────


def test_low_re_only_counts_confident_rows():
    """Polar row at Re=100k with confidence < 0.85 → no low_re tag."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[_polar(100_000, 0.84)],
    )
    assert "low_re" not in tags


def test_low_re_boundary_confidence():
    """Exactly at confidence gate → qualifies."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[_polar(100_000, 0.85)],
    )
    assert "low_re" in tags


def test_low_re_boundary_re_value():
    """Exactly at Re = 150 000 → qualifies."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[_polar(150_000, 0.86)],
    )
    assert "low_re" in tags


def test_high_re_boundary_re_value():
    """Exactly at Re = 500 000 → high_re tag."""
    tags = compute_tags(
        family="flat_bottom",
        max_thickness_pct=14.0,
        max_camber_pct=3.0,
        polars=[_polar(500_000, 0.88)],
    )
    assert "high_re" in tags


def test_high_re_just_below_boundary():
    """Re = 499 999 → no high_re tag."""
    tags = compute_tags(
        family="flat_bottom",
        max_thickness_pct=14.0,
        max_camber_pct=3.0,
        polars=[_polar(499_999, 0.88)],
    )
    assert "high_re" not in tags


# ── None / null handling ─────────────────────────────────────────────────────


def test_polar_with_none_confidence_is_skipped():
    """Polar row where min_analysis_confidence is None must not crash or count."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[{"reynolds": 100_000, "min_analysis_confidence": None}],
    )
    assert "low_re" not in tags


def test_polar_with_none_reynolds_is_skipped():
    """Polar row where reynolds is None must not crash or count."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[{"reynolds": None, "min_analysis_confidence": 0.90}],
    )
    assert "low_re" not in tags


# ── Return type contract ──────────────────────────────────────────────────────


def test_compute_tags_returns_sorted_list():
    """Tags list is always sorted alphabetically for determinism."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[_polar(100_000, 0.90), _polar(600_000, 0.92)],
    )
    assert tags == sorted(tags)


def test_compute_tags_no_duplicates():
    """Tags are never duplicated even when multiple gates are satisfied."""
    tags = compute_tags(
        family="symmetric",
        max_thickness_pct=10.0,
        max_camber_pct=0.0,
        polars=[_polar(100_000, 0.90), _polar(600_000, 0.92)],
    )
    assert len(tags) == len(set(tags))
