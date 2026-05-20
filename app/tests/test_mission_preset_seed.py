"""Tests for the seeded Mission Presets (gh-546)."""

from __future__ import annotations

from app.services.mission_preset_seed import SEED_PRESETS


def test_seed_presets_exist():
    """gh-580: motor_glider added to the canonical preset set."""
    ids = {p.id for p in SEED_PRESETS}
    assert ids == {
        "trainer",
        "sport",
        "sailplane",
        "wing_racer",
        "acro_3d",
        "stol_bush",
        "slope_soarer",
        "motor_glider",
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


def test_motor_glider_preset_defaults():
    """gh-580: Motorsegler carries the Scholz-review-verified defaults."""
    preset = next(p for p in SEED_PRESETS if p.id == "motor_glider")
    assert preset.label == "Motorsegler (Motor Glider)"
    est = preset.suggested_estimates
    # Powered: power_to_weight=100 W/kg covers self-launch climb (80–150 range)
    assert est.power_to_weight == 100.0
    # Climb-segment prop efficiency for folding/feathering prop
    assert est.prop_efficiency == 0.65
    # Slightly more stable than sport, conservative for cross-country glide
    assert est.target_static_margin == 0.10
    # Cambered laminar profile, no stall protection needed
    assert est.cl_max == 1.4
    # CS-22.337 utility-category ultimate factor (1.5 × +3.5 limit)
    assert est.g_limit == 5.3
    # KPI polygon: high glide, mid climb/cruise/stall, low maneuver
    polygon = preset.target_polygon
    assert polygon["glide"] >= 0.8
    assert polygon["stall_safety"] == 0.65
    assert polygon["climb"] == 0.50
    assert polygon["cruise"] == 0.55
    assert polygon["maneuver"] <= 0.35
    assert polygon["wing_loading"] == 0.45
    assert polygon["field_friendliness"] == 0.60


def test_motor_glider_is_powered_for_is_glider_flag():
    """gh-580: motor_glider has power_to_weight > 0 so downstream
    ``is_glider = p_to_w <= 0`` correctly treats it as a powered aircraft.
    This is the key behavioural distinction from the unpowered ``sailplane``
    and ``slope_soarer`` presets."""
    preset = next(p for p in SEED_PRESETS if p.id == "motor_glider")
    assert preset.suggested_estimates.power_to_weight > 0
    # Sanity: compare with the unpowered presets
    sailplane = next(p for p in SEED_PRESETS if p.id == "sailplane")
    slope_soarer = next(p for p in SEED_PRESETS if p.id == "slope_soarer")
    assert sailplane.suggested_estimates.power_to_weight == 0.0
    assert slope_soarer.suggested_estimates.power_to_weight == 0.0


def test_motor_glider_description_cites_cs22_and_clarifies_ld_market_convention():
    """gh-580 (Scholz review): the description must (a) cite CS-22.337 for
    g_limit and (b) explicitly state that L/D ≥ 20 is market convention,
    NOT a CS-22 requirement, to avoid propagating the regulatory myth."""
    preset = next(p for p in SEED_PRESETS if p.id == "motor_glider")
    description = preset.description
    assert "CS-22.337" in description
    assert "market convention" in description.lower()
    assert "L/D" in description


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
