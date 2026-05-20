"""Tests for the seeded Mission Presets (gh-546)."""

from __future__ import annotations

from app.services.mission_preset_seed import SEED_PRESETS


def test_seed_presets_exist():
    """gh-582: slope_soarer added to the canonical preset set."""
    ids = {p.id for p in SEED_PRESETS}
    assert ids == {
        "trainer",
        "sport",
        "sailplane",
        "wing_racer",
        "acro_3d",
        "stol_bush",
        "slope_soarer",
    }


def test_slope_soarer_preset_defaults():
    """gh-582: RC slope soarer carries the review-verified defaults."""
    preset = next(p for p in SEED_PRESETS if p.id == "slope_soarer")
    assert preset.label == "Slope Soarer"
    est = preset.suggested_estimates
    assert est.power_to_weight == 0.0  # unpowered → is_glider auto
    assert est.prop_efficiency == 0.0
    assert est.target_static_margin == 0.08
    assert est.cl_max == 1.1
    assert est.g_limit == 6.0
    # KPI polygon: high maneuver + high cruise + mid stall + high field-friendliness
    polygon = preset.target_polygon
    assert polygon["maneuver"] >= 0.7
    assert polygon["cruise"] >= 0.7
    assert polygon["field_friendliness"] >= 0.8
    assert 0.3 <= polygon["stall_safety"] <= 0.6
    # Wing-loading axis covers RC slope range 50–150 g/dm² (in N/m²-equivalent scale)
    lo, hi = preset.axis_ranges["wing_loading"]
    assert lo == 50.0
    assert hi == 150.0


def test_each_preset_covers_all_seven_axes():
    expected_axes = {
        "stall_safety",
        "glide",
        "climb",
        "cruise",
        "maneuver",
        "wing_loading",
        "field_friendliness",
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
