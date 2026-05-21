"""Seed data for the six default Mission Presets (gh-546).

Used by the Alembic data migration. Values come from the brainstorming
spec §3 "Mission Soll-Polygone" — adjusted per the spec's normalisation
ranges. Source of truth: docs/superpowers/specs/2026-05-15-mission-spider-chart-design.md
"""

from __future__ import annotations

from app.schemas.mission_objective import MissionPreset, MissionPresetEstimates

SEED_PRESETS: list[MissionPreset] = [
    MissionPreset(
        id="trainer",
        label="Trainer",
        description="Forgiving low-loading trainer for first-flight pilots.",
        target_polygon={
            "stall_safety": 1.0,
            "glide": 0.4,
            "climb": 0.3,
            "cruise": 0.3,
            "maneuver": 0.3,
            "wing_loading": 0.3,
            "field_friendliness": 0.9,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.5),
            "glide": (5.0, 18.0),
            "climb": (5.0, 25.0),
            "cruise": (10.0, 25.0),
            "maneuver": (2.0, 5.0),
            "wing_loading": (20.0, 80.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=3.0,
            target_static_margin=0.15,
            cl_max=1.4,
            power_to_weight=0.5,
            prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="sport",
        label="Sport",
        description="All-rounder with moderate loading and honest control authority.",
        target_polygon={
            "stall_safety": 0.7,
            "glide": 0.6,
            "climb": 0.6,
            "cruise": 0.6,
            "maneuver": 0.6,
            "wing_loading": 0.6,
            "field_friendliness": 0.6,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.2),
            "glide": (8.0, 20.0),
            "climb": (8.0, 30.0),
            "cruise": (15.0, 35.0),
            "maneuver": (3.0, 7.0),
            "wing_loading": (40.0, 120.0),
            "field_friendliness": (5.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.0,
            target_static_margin=0.10,
            cl_max=1.3,
            power_to_weight=0.7,
            prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="sailplane",
        label="Sailplane",
        description="High-AR thermal glider with low minimum sink and high L/D.",
        target_polygon={
            "stall_safety": 0.8,
            "glide": 1.0,
            "climb": 0.5,
            "cruise": 0.3,
            "maneuver": 0.3,
            "wing_loading": 0.1,
            "field_friendliness": 0.5,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (15.0, 35.0),
            "climb": (15.0, 60.0),
            "cruise": (10.0, 25.0),
            "maneuver": (2.5, 5.5),
            "wing_loading": (10.0, 50.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.3,
            target_static_margin=0.10,
            cl_max=1.3,
            power_to_weight=0.0,
            prop_efficiency=0.0,
        ),
    ),
    MissionPreset(
        id="wing_racer",
        label="Wing-Racer",
        description="Low-AR pylon / FPV racer optimised for cruise + maneuver.",
        target_polygon={
            "stall_safety": 0.5,
            "glide": 0.7,
            "climb": 0.7,
            "cruise": 1.0,
            "maneuver": 0.7,
            "wing_loading": 0.9,
            "field_friendliness": 0.4,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (6.0, 18.0),
            "climb": (10.0, 35.0),
            "cruise": (30.0, 80.0),
            "maneuver": (5.0, 12.0),
            "wing_loading": (80.0, 250.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=10.0,
            target_static_margin=0.05,
            cl_max=1.0,
            power_to_weight=1.0,
            prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="acro_3d",
        label="3D / Acro",
        description="Neutral-stability 3D model with very high control authority.",
        target_polygon={
            "stall_safety": 0.5,
            "glide": 0.4,
            "climb": 0.7,
            "cruise": 0.5,
            "maneuver": 1.0,
            "wing_loading": 0.8,
            "field_friendliness": 0.5,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (6.0, 14.0),
            "climb": (15.0, 40.0),
            "cruise": (15.0, 30.0),
            "maneuver": (6.0, 12.0),
            "wing_loading": (60.0, 180.0),
            "field_friendliness": (3.0, 80.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=8.0,
            target_static_margin=0.0,
            cl_max=1.1,
            power_to_weight=1.4,
            prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="stol_bush",
        label="STOL / Bush",
        description="Short take-off / bush model with high CL_max and short field.",
        target_polygon={
            "stall_safety": 0.9,
            "glide": 0.5,
            "climb": 0.6,
            "cruise": 0.3,
            "maneuver": 0.4,
            "wing_loading": 0.2,
            "field_friendliness": 1.0,
        },
        axis_ranges={
            "stall_safety": (1.3, 3.0),
            "glide": (6.0, 16.0),
            "climb": (8.0, 30.0),
            "cruise": (10.0, 25.0),
            "maneuver": (2.5, 5.0),
            "wing_loading": (15.0, 80.0),
            "field_friendliness": (2.0, 50.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=4.0,
            target_static_margin=0.15,
            cl_max=2.0,
            power_to_weight=0.8,
            prop_efficiency=0.7,
        ),
    ),
    MissionPreset(
        id="slope_soarer",
        label="Slope Soarer",
        description=(
            "Unpowered RC slope soarer — higher wing loading (50–150 g/dm²) "
            "than thermal gliders for stable penetration in gusty ridge lift. "
            "Hand-launched, aerobatic-capable, low dihedral (0–2°) for roll "
            "responsiveness. Airfoil hints: RG14, RG15, NACA 0012, HN-354, "
            "HN-1033, SD7037. AR range 5–12 covers sport through F3F racers."
        ),
        target_polygon={
            "stall_safety": 0.45,
            "glide": 0.50,
            "climb": 0.30,
            "cruise": 0.75,
            "maneuver": 0.80,
            "wing_loading": 0.70,
            "field_friendliness": 0.85,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (10.0, 25.0),
            "climb": (5.0, 25.0),
            "cruise": (15.0, 45.0),
            "maneuver": (5.0, 8.0),
            "wing_loading": (50.0, 150.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=6.0,
            target_static_margin=0.08,
            cl_max=1.1,
            power_to_weight=0.0,
            prop_efficiency=0.0,
        ),
    ),
    MissionPreset(
        id="motor_glider",
        label="Motor Glider",
        description=(
            "Self-launching motor glider — high-AR sailplane geometry with a "
            "small climb-only powerplant (folding or retractable prop). "
            "Aspect ratio default 15 (range 14–22): Stemme S10 ≈ 22 (upper "
            "end), ASK-21 Mi ≈ 16, Grob G109 ≈ 16.6. Wing loading mid "
            "(~35 g/dm² typical for RC; ~30–45 kg/m² full-scale). "
            "Power-to-weight 80–150 W/kg covers self-launch climb. "
            "Caveat: prop_efficiency=0.65 reflects the climb segment with a "
            "folding/feathering prop; in glide the prop is stowed and the "
            "drag contribution is implicit (≈ 0). The current schema carries "
            "a single value, so 0.65 is the climb assumption. "
            "g_limit=5.3 cites CS-22.337 utility-category ultimate factor "
            "(1.5 × +3.5 limit) for sailplanes and powered sailplanes. "
            "Note: L/D ≥ 20 is a market convention (FAI Self-Launching "
            "Glider classification), NOT a CS-22 requirement; the achieved "
            "L/D depends on the cleanly retracted-prop polar and must be "
            "verified post-VLM."
        ),
        target_polygon={
            "stall_safety": 0.65,
            "glide": 0.85,
            "climb": 0.50,
            "cruise": 0.55,
            "maneuver": 0.30,
            "wing_loading": 0.45,
            "field_friendliness": 0.60,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (15.0, 30.0),
            "climb": (5.0, 25.0),
            "cruise": (15.0, 35.0),
            "maneuver": (3.0, 6.0),
            "wing_loading": (20.0, 80.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.3,
            target_static_margin=0.10,
            cl_max=1.4,
            power_to_weight=100.0,
            prop_efficiency=0.65,
        ),
    ),
    MissionPreset(
        id="flying_wing",
        label="Flying Wing",
        description=(
            "Tailless RC flying wing — longitudinal trim via "
            "sweep + washout + reflex airfoil. Tail-volume sizing not "
            "applicable; static-margin corridor tightened (5–10 % MAC, "
            "default 7.5 %) per #579 — this is a dynamic-stability / "
            "control-power floor, NOT a static-aerodynamic limit (C_m,q "
            "pitch damping is much smaller without a tail moment arm). "
            "Aspect ratio default 8 (range 6–12). Sweep default 25° "
            "leading-edge sweep (range 20–35°); sweep convention is "
            "LE-sweep, NOT c/4 — the two differ by ~5° for typical taper. "
            "Washout default 5° at the mid (range varies by airfoil): "
            "**3–5° for symmetric** sections (NACA 0012-class), "
            "**5–9° for reflex** sections (E184/E230, MH-series) — reflex "
            "sections have less inherent stabilising camber and need MORE "
            "washout, not less (Lennon Ch. 23 + NACA tunnel data). "
            "Taper ratio default 0.5 — HARD CONSTRAINT 0.4 ≤ λ ≤ 0.6 to "
            "avoid tip-stall + nose-up pitch break (Lennon: avoid 4:1 "
            "taper; Sadraey converges). Stability guard: simultaneously "
            "sweep < 20° AND washout < 3° is rejected (C_m,q margin "
            "phugoid-divergent). Airfoil hints: **classic** Eppler E184 "
            "(root) / E230 (tip); **modern** MH-series (MH45, MH60, MH61, "
            "MH64). PREFERRED STRATEGY: HYBRID (moderate reflex + moderate "
            "sweep + moderate washout) per Apogee — best modern flying "
            "wings. Symmetric-airfoil caveat: dx/dα = 0 from the section "
            "alone, so a symmetric airfoil on a flying wing requires "
            "CG BELOW the wing chord plane (pendulum stability) — "
            "otherwise the wing is not statically stable. Penalty of "
            "reflex sections per Apogee: −9–15 % cl_max, −5 % minimum "
            "profile drag (so cl_max = 1.0 is conservative: 1.25 cambered "
            "× 0.85–0.91). YAW STABILITY is out of scope here — drag "
            "rudders / split rudders / vertical fins / winglets are a "
            "separate ticket; see Sadraey §12.2 and Apogee for design "
            "guidance."
        ),
        target_polygon={
            "stall_safety": 0.40,
            "glide": 0.55,
            "climb": 0.50,
            "cruise": 0.65,
            "maneuver": 0.75,
            "wing_loading": 0.55,
            "field_friendliness": 0.50,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.0),
            "glide": (6.0, 18.0),
            "climb": (8.0, 30.0),
            "cruise": (15.0, 40.0),
            "maneuver": (4.0, 8.0),
            "wing_loading": (40.0, 150.0),
            "field_friendliness": (3.0, 100.0),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=5.0,
            target_static_margin=0.075,
            cl_max=1.0,
            power_to_weight=100.0,
            prop_efficiency=0.65,
        ),
    ),
]
