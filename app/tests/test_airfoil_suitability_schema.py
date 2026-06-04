"""Tests for the frozen Pydantic schemas for airfoil suitability (Task 3, gh-821)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_suitability_item_required_fields():
    from app.schemas.airfoil import SuitabilityItem

    item = SuitabilityItem(
        airfoil_name="sd7037",
        family="cambered",
        re_agnostic=0.85,
        mission=None,
        target_cl_cruise=None,
        target_cl_best_glide=None,
        target_cl_min_sink=None,
        stall_gentleness=-0.04,
        cl_max_margin=0.3,
        min_analysis_confidence=0.92,
        tip_re_flag=False,
        caveat="",
    )
    assert item.airfoil_name == "sd7037"
    assert item.family == "cambered"
    assert item.re_agnostic == pytest.approx(0.85)
    assert item.mission is None
    assert item.target_cl_cruise is None
    assert item.target_cl_best_glide is None
    assert item.target_cl_min_sink is None
    assert item.stall_gentleness == pytest.approx(-0.04)
    assert item.cl_max_margin == pytest.approx(0.3)
    assert item.min_analysis_confidence == pytest.approx(0.92)
    assert item.tip_re_flag is False
    assert item.caveat == ""


def test_suitability_item_family_literals():
    from app.schemas.airfoil import SuitabilityItem

    valid_families = ["flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"]
    for fam in valid_families:
        item = SuitabilityItem(
            airfoil_name="test",
            family=fam,
            re_agnostic=0.5,
            mission=None,
            target_cl_cruise=None,
            target_cl_best_glide=None,
            target_cl_min_sink=None,
            min_analysis_confidence=0.9,
            tip_re_flag=False,
            caveat="",
        )
        assert item.family == fam


def test_suitability_item_invalid_family():
    from app.schemas.airfoil import SuitabilityItem

    with pytest.raises(ValidationError):
        SuitabilityItem(
            airfoil_name="test",
            family="invalid_family",
            re_agnostic=0.5,
            mission=None,
            target_cl_cruise=None,
            target_cl_best_glide=None,
            target_cl_min_sink=None,
            min_analysis_confidence=0.9,
            tip_re_flag=False,
            caveat="",
        )


def test_suitability_query_required_fields():
    from app.schemas.airfoil import SuitabilityQuery

    q = SuitabilityQuery(
        chord_m=0.15,
        speed_ms=15.0,
        reynolds=150_000.0,
        re_clamped=False,
        mission_type=None,
        target_cl_cruise=None,
        target_cl_best_glide=None,
        target_cl_min_sink=None,
        target_cl_provenance="estimated",
        active_lens="re_agnostic",
    )
    assert q.chord_m == pytest.approx(0.15)
    assert q.speed_ms == pytest.approx(15.0)
    assert q.reynolds == pytest.approx(150_000.0)
    assert q.re_clamped is False
    assert q.mission_type is None
    assert q.target_cl_cruise is None
    assert q.target_cl_best_glide is None
    assert q.target_cl_min_sink is None
    assert q.target_cl_provenance == "estimated"
    assert q.active_lens == "re_agnostic"


def test_suitability_query_active_lens_literals():
    from app.schemas.airfoil import SuitabilityQuery

    # active_lens must be one of the three valid values
    for lens in ("re_agnostic", "mission", "target_cl_cruise"):
        q = SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            mission_type=None,
            target_cl_cruise=None,
            target_cl_best_glide=None,
            target_cl_min_sink=None,
            target_cl_provenance="estimated",
            active_lens=lens,
        )
        assert q.active_lens == lens


def test_suitability_query_active_lens_never_glide_point():
    """active_lens MUST NOT be any glide point per the gh-825 contract."""
    from app.schemas.airfoil import SuitabilityQuery

    for bad_lens in ("target_cl_loiter", "target_cl_best_glide", "target_cl_min_sink"):
        with pytest.raises(ValidationError):
            SuitabilityQuery(
                chord_m=0.15,
                speed_ms=15.0,
                reynolds=150_000.0,
                re_clamped=False,
                mission_type=None,
                target_cl_cruise=None,
                target_cl_best_glide=None,
                target_cl_min_sink=None,
                target_cl_provenance="estimated",
                active_lens=bad_lens,  # NOT valid
            )


def test_suitability_caveat_required_fields():
    from app.schemas.airfoil import SuitabilityCaveat

    cav = SuitabilityCaveat(
        relative_ranking_only=True,
        no_hysteresis_modelling=True,
        recommend_xfoil_validation=False,
        text="Nur relative Reihenfolge.",
    )
    assert cav.relative_ranking_only is True
    assert cav.no_hysteresis_modelling is True
    assert cav.recommend_xfoil_validation is False
    assert isinstance(cav.text, str)


def test_suitability_response_shape():
    from app.schemas.airfoil import (
        SuitabilityResponse,
        SuitabilityQuery,
        SuitabilityCaveat,
        SuitabilityItem,
    )

    resp = SuitabilityResponse(
        query=SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            mission_type=None,
            target_cl_cruise=None,
            target_cl_best_glide=None,
            target_cl_min_sink=None,
            target_cl_provenance="estimated",
            active_lens="re_agnostic",
        ),
        caveat=SuitabilityCaveat(
            relative_ranking_only=True,
            no_hysteresis_modelling=True,
            ignores_tip_re_clmax_collapse=True,
            recommend_xfoil_validation=False,
            text="Nur relative Reihenfolge.",
        ),
        results=[
            SuitabilityItem(
                airfoil_name="sd7037",
                family="cambered",
                re_agnostic=0.85,
                mission=None,
                target_cl_cruise=None,
                target_cl_best_glide=None,
                target_cl_min_sink=None,
                stall_gentleness=-0.04,
                cl_max_margin=0.4,
                min_analysis_confidence=0.92,
                tip_re_flag=False,
                caveat="",
            )
        ],
    )
    # Verify frozen field names serialize correctly
    data = resp.model_dump()
    assert "query" in data
    assert "caveat" in data
    assert "results" in data
    q = data["query"]
    assert "chord_m" in q
    assert "speed_ms" in q
    assert "reynolds" in q
    assert "re_clamped" in q
    assert "mission_type" in q
    assert "target_cl_cruise" in q
    assert "target_cl_best_glide" in q
    assert "target_cl_min_sink" in q
    assert "target_cl_provenance" in q
    assert "active_lens" in q
    assert "target_cl_loiter" not in q

    c = data["caveat"]
    assert "relative_ranking_only" in c
    assert "no_hysteresis_modelling" in c
    assert "ignores_tip_re_clmax_collapse" in c
    assert "recommend_xfoil_validation" in c
    assert "text" in c

    r = data["results"][0]
    assert "airfoil_name" in r
    assert "family" in r
    assert "re_agnostic" in r
    assert "mission" in r
    assert "target_cl_cruise" in r
    assert "target_cl_best_glide" in r
    assert "target_cl_min_sink" in r
    assert "stall_gentleness" in r
    assert "cl_max_margin" in r
    assert "min_analysis_confidence" in r
    assert "tip_re_flag" in r
    assert "caveat" in r
    assert "target_cl_loiter" not in r
