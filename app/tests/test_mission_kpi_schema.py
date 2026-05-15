"""Tests for the mission_kpi schemas (gh-546)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.mission_kpi import MissionAxisKpi, MissionKpiSet, MissionTargetPolygon


def test_axis_kpi_accepts_known_axes_only():
    kpi = MissionAxisKpi(
        axis="stall_safety",
        value=1.45,
        unit="-",
        score_0_1=0.72,
        range_min=1.3,
        range_max=3.0,
        provenance="computed",
        formula="V_cruise / V_s1",
    )
    assert kpi.axis == "stall_safety"


def test_axis_kpi_rejects_unknown_axis():
    with pytest.raises(ValidationError):
        MissionAxisKpi(
            axis="bogus_axis",
            value=1.0, unit="-", score_0_1=0.5,
            range_min=0, range_max=1, provenance="computed",
            formula="-",
        )


def test_axis_kpi_provenance_missing_allows_none_value():
    kpi = MissionAxisKpi(
        axis="glide", value=None, unit=None, score_0_1=None,
        range_min=0, range_max=1, provenance="missing", formula="-",
    )
    assert kpi.value is None
    assert kpi.score_0_1 is None


def test_kpi_set_round_trips_model_dump():
    ist = {
        "stall_safety": MissionAxisKpi(
            axis="stall_safety", value=1.45, unit="-", score_0_1=0.72,
            range_min=1.3, range_max=3.0, provenance="computed",
            formula="V_cruise / V_s1",
        ),
    }
    kset = MissionKpiSet(
        aeroplane_uuid="00000000-0000-0000-0000-000000000000",
        ist_polygon=ist,
        target_polygons=[
            MissionTargetPolygon(
                mission_id="trainer", label="Trainer",
                scores_0_1={"stall_safety": 0.78},
            ),
        ],
        active_mission_id="trainer",
        computed_at="2026-05-15T12:00:00Z",
        context_hash="0" * 64,
    )
    dumped = kset.model_dump()
    re_parsed = MissionKpiSet.model_validate(dumped)
    assert re_parsed == kset
