"""Tests for the MissionObjective + MissionPreset schemas (gh-546)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.mission_objective import (
    MissionObjective,
    MissionPreset,
    MissionPresetEstimates,
)


def test_mission_objective_full_payload():
    obj = MissionObjective(
        mission_type="trainer",
        target_cruise_mps=18.0,
        target_stall_safety=1.8,
        target_maneuver_n=3.0,
        target_glide_ld=12,
        target_climb_energy=22,
        target_wing_loading_n_m2=42 * 9.81,  # g/dm² → N/m² scale
        target_field_length_m=50,
        available_runway_m=50,
        runway_type="grass",
        t_static_N=18,
        takeoff_mode="runway",
    )
    assert obj.mission_type == "trainer"


def test_runway_type_enum_rejects_unknown():
    with pytest.raises(ValidationError):
        MissionObjective(
            mission_type="trainer",
            target_cruise_mps=18, target_stall_safety=1.8,
            target_maneuver_n=3, target_glide_ld=12,
            target_climb_energy=22, target_wing_loading_n_m2=400,
            target_field_length_m=50, available_runway_m=50,
            runway_type="diamond",   # invalid
            t_static_N=18, takeoff_mode="runway",
        )


def test_preset_has_polygon_and_estimates():
    pre = MissionPreset(
        id="trainer", label="Trainer", description="Forgiving trainer",
        target_polygon={
            "stall_safety": 1.0, "glide": 0.4, "climb": 0.3, "cruise": 0.3,
            "maneuver": 0.3, "wing_loading": 0.3, "field_friendliness": 0.9,
        },
        axis_ranges={
            "stall_safety": (1.3, 2.5), "glide": (5, 18),
            "climb": (5, 25), "cruise": (10, 25),
            "maneuver": (2, 5), "wing_loading": (20, 80),
            "field_friendliness": (3, 100),
        },
        suggested_estimates=MissionPresetEstimates(
            g_limit=3.0, target_static_margin=0.15, cl_max=1.4,
            power_to_weight=0.5, prop_efficiency=0.7,
        ),
    )
    assert pre.target_polygon["stall_safety"] == 1.0
