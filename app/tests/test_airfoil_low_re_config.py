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
    """Mission weight table must have all required mission types."""
    from app.settings import Settings

    s = Settings()
    required_keys = {"trainer", "sport", "aerobatic", "glider", "flying_wing"}
    assert required_keys == set(s.low_re_mission_weights.keys())


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
