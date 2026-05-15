"""Tests for the seeded Mission Presets (gh-546)."""
from __future__ import annotations

from app.services.mission_preset_seed import SEED_PRESETS


def test_six_seed_presets_exist():
    ids = {p.id for p in SEED_PRESETS}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}


def test_each_preset_covers_all_seven_axes():
    expected_axes = {
        "stall_safety", "glide", "climb", "cruise",
        "maneuver", "wing_loading", "field_friendliness",
    }
    for p in SEED_PRESETS:
        assert set(p.target_polygon.keys()) == expected_axes, f"{p.id} target_polygon"
        assert set(p.axis_ranges.keys()) == expected_axes, f"{p.id} axis_ranges"


def test_axis_ranges_min_less_than_max():
    for p in SEED_PRESETS:
        for axis, (lo, hi) in p.axis_ranges.items():
            assert lo < hi, f"{p.id}.{axis}: range {lo} !< {hi}"


def test_stall_safety_range_floor_is_1_3():
    """Per spec: hard floor for Stall Safety is 1.3 across all missions."""
    for p in SEED_PRESETS:
        lo, _ = p.axis_ranges["stall_safety"]
        assert lo >= 1.3, f"{p.id} stall floor {lo} < 1.3"
