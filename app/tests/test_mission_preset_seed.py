"""Tests for the seeded Mission Presets (gh-546)."""

from __future__ import annotations

from app.services.mission_preset_seed import SEED_PRESETS


def test_seed_presets_exist():
    """gh-581: flying_wing added to the canonical preset set."""
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
        "flying_wing",
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
    """gh-580: the motor glider preset carries the Scholz-review-verified defaults."""
    preset = next(p for p in SEED_PRESETS if p.id == "motor_glider")
    assert preset.label == "Motor Glider"
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


def test_flying_wing_preset_defaults():
    """gh-581: the flying wing preset carries the review-verified defaults (Scholz + Anderson + Apogee + Lennon)."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    assert preset.label == "Flying Wing"
    est = preset.suggested_estimates
    # Tighter SM corridor for tailless (range 5–10 %, default 7.5 %) — see #579
    assert est.target_static_margin == 0.075
    # Reflex/symmetric airfoils lose 9–15 % cl_max vs. cambered (Apogee)
    assert est.cl_max == 1.0
    # Sport-class g-limit for RC flying wings
    assert est.g_limit == 5.0
    # Powered default: most RC flying wings are EDF or prop
    assert est.power_to_weight == 100.0
    assert est.prop_efficiency == 0.65
    # KPI polygon: high maneuver USP, mid cruise, low stall-safety
    polygon = preset.target_polygon
    assert polygon["stall_safety"] == 0.40
    assert polygon["glide"] == 0.55
    assert polygon["climb"] == 0.50
    assert polygon["cruise"] == 0.65
    assert polygon["maneuver"] == 0.75
    assert polygon["wing_loading"] == 0.55
    assert polygon["field_friendliness"] == 0.50


def test_flying_wing_description_documents_washout_airfoil_pairing_correctly():
    """gh-581 CRITICAL: the description must pair washout with airfoil family in the
    CORRECT direction (3–5° symmetric / 5–9° reflex). The draft inverted it, and
    if shipped reversed would cause tip-stall + nose-up pitch break on reflex
    sections (the exact failure mode Northrop's LE slots were invented for)."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    # Both ranges must appear in the description
    assert "3–5°" in desc, "symmetric washout range missing"
    assert "5–9°" in desc, "reflex washout range missing"
    # The pairing must be present in the description text
    assert "symmetric" in desc.lower()
    assert "reflex" in desc.lower()
    # Reflex sections need MORE washout (not less) — pin the wording so a future
    # edit can't quietly re-invert the pairing without tripping this guard
    assert "MORE washout" in desc or "more washout" in desc.lower()


def test_flying_wing_description_documents_sweep_convention():
    """gh-581 (Anderson review): sweep convention (LE vs c/4) must be explicit
    in the description — they differ by ~5° for typical taper."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "LE-sweep" in desc or "leading-edge" in desc.lower()


def test_flying_wing_description_documents_taper_hard_constraint():
    """gh-581: taper 0.4 ≤ λ ≤ 0.6 is a HARD CONSTRAINT for tailless, not just
    the default — Lennon + Sadraey converge on tip-stall risk above 4:1."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "0.4" in desc
    assert "0.6" in desc
    assert "HARD CONSTRAINT" in desc or "hard constraint" in desc.lower()


def test_flying_wing_description_documents_pendulum_caveat():
    """gh-581 (Apogee review): symmetric airfoil on a tailless wing requires
    CG below the chord plane (dx/dα = 0 from the section alone, so the wing
    is statically unstable without pendulum effect). Must be in the
    description so users see the caveat in the UI."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "pendulum" in desc.lower()
    assert "below" in desc.lower()
    # dx/dα framework explicitly cited
    assert "dx/dα" in desc


def test_flying_wing_description_prefers_hybrid_strategy():
    """gh-581 (Apogee review): hybrid strategy (moderate reflex + sweep + washout)
    is the preferred default per Apogee — best modern flying wings. The
    description must surface this as the recommended pick."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "HYBRID" in desc or "hybrid" in desc.lower()
    assert "preferred" in desc.lower()


def test_flying_wing_description_documents_stability_guard():
    """gh-581: sweep<20° AND washout<3° simultaneously is rejected — the
    stability guard must be documented in the description so users know
    the rule before encountering it."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "sweep < 20°" in desc or "sweep<20°" in desc.lower().replace(" ", "")
    assert "washout < 3°" in desc or "washout<3°" in desc.lower().replace(" ", "")


def test_flying_wing_description_documents_yaw_oos():
    """gh-581: yaw stability (drag rudders / split rudders / vertical fins) is
    explicitly OOS — must be flagged in the description so users know to plan
    yaw separately."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    desc = preset.description
    assert "yaw" in desc.lower()
    assert "out of scope" in desc.lower() or "separate ticket" in desc.lower()


def test_flying_wing_is_powered_by_default():
    """gh-581: most RC flying wings are powered (EDF / prop). The preset
    defaults to powered so downstream ``is_glider = p_to_w <= 0`` returns
    False (V_max chip and other powered-only chips remain enabled)."""
    preset = next(p for p in SEED_PRESETS if p.id == "flying_wing")
    assert preset.suggested_estimates.power_to_weight > 0


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
