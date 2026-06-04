"""Tests for low-Re airfoil scoring configuration defaults (Task 0, gh-821)."""

from __future__ import annotations

import pytest


def test_re_grid_default():
    """RE grid must contain exactly the 13 points from the spec."""
    from app.settings import Settings

    s = Settings()
    expected = [
        40_000,
        50_000,
        60_000,
        75_000,
        90_000,
        110_000,
        130_000,
        160_000,
        200_000,
        250_000,
        350_000,
        500_000,
        750_000,
    ]
    assert s.low_re_grid == expected


def test_re_grid_ascending():
    from app.settings import Settings

    grid = Settings().low_re_grid
    assert grid == sorted(grid), "Re grid must be ascending"


def test_neuralfoil_model_size_default():
    from app.settings import Settings

    s = Settings()
    assert s.low_re_neuralfoil_model_size == "xxxlarge"


def test_n_crit_default():
    from app.settings import Settings

    s = Settings()
    assert s.low_re_n_crit == 9.0


def test_confidence_gate_default():
    from app.settings import Settings

    s = Settings()
    assert s.low_re_confidence_gate == pytest.approx(0.90)


def test_low_confidence_flag_default():
    from app.settings import Settings

    s = Settings()
    assert s.low_re_low_confidence_flag == pytest.approx(0.85)


def test_mission_weights_keys():
    """Mission weight table must have all required mission types.

    gh-825 item 12: slope_soarer added as an additional key (additive — no renames).
    """
    from app.settings import Settings

    s = Settings()
    required_keys = {"trainer", "sport", "aerobatic", "glider", "flying_wing"}
    # All original keys must be present (additive — no renames)
    assert required_keys.issubset(set(s.low_re_mission_weights.keys())), (
        f"All original mission weight keys must be present; "
        f"missing: {required_keys - set(s.low_re_mission_weights.keys())}"
    )
    # slope_soarer is the new additive key (gh-825 item 12)
    assert "slope_soarer" in s.low_re_mission_weights


def test_mission_weights_structure():
    """Each mission weight entry must have required subkeys."""
    from app.settings import Settings

    s = Settings()
    for mission, weights in s.low_re_mission_weights.items():
        assert "thickness_min_pct" in weights, f"missing thickness_min_pct for {mission}"
        assert "thickness_max_pct" in weights, f"missing thickness_max_pct for {mission}"
        assert "cl_max_weight" in weights, f"missing cl_max_weight for {mission}"
        assert "preferred_families" in weights, f"missing preferred_families for {mission}"


def test_mission_weights_values_positive():
    from app.settings import Settings

    s = Settings()
    for mission, weights in s.low_re_mission_weights.items():
        assert weights["cl_max_weight"] > 0, f"cl_max_weight must be positive for {mission}"


# ---------------------------------------------------------------------------
# gh-825 new scoring constants
# ---------------------------------------------------------------------------


def test_low_re_score_r_poor_default():
    """low_re_score_r_poor must default to ~2.5 (relative drag-rise at Match→0)."""
    from app.settings import Settings

    s = Settings()
    assert s.low_re_score_r_poor == pytest.approx(2.5)


def test_low_re_bucket_tolerance_ref_default():
    """low_re_bucket_tolerance_ref must default to ~0.6 (full-credit bucket width)."""
    from app.settings import Settings

    s = Settings()
    assert s.low_re_bucket_tolerance_ref == pytest.approx(0.6)


def test_settings_gh825_fields_present():
    """Both gh-825 fields must be accessible on the Settings object."""
    from app.settings import Settings

    s = Settings()
    assert hasattr(s, "low_re_score_r_poor")
    assert hasattr(s, "low_re_bucket_tolerance_ref")
    assert s.low_re_score_r_poor > 1.0
    assert 0.0 < s.low_re_bucket_tolerance_ref <= 2.0
