"""Tests for the frozen Pydantic schemas for airfoil suitability (gh-821, updated gh-825)."""

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
        target_cl_min_sink=None,
        target_cl_best_glide=None,
        stall_gentleness=None,
        cl_max_margin=None,
        min_analysis_confidence=0.92,
        tip_re_flag=False,
        caveat="",
    )
    assert item.airfoil_name == "sd7037"
    assert item.family == "cambered"
    assert item.re_agnostic == pytest.approx(0.85)
    assert item.mission is None
    assert item.target_cl_cruise is None
    assert item.target_cl_min_sink is None
    assert item.target_cl_best_glide is None
    assert item.stall_gentleness is None
    assert item.cl_max_margin is None
    assert item.min_analysis_confidence == pytest.approx(0.92)
    assert item.tip_re_flag is False
    assert item.caveat == ""


def test_suitability_item_no_target_cl_loiter_field():
    """gh-825: target_cl_loiter was renamed — the old name must not exist."""
    from app.schemas.airfoil import SuitabilityItem

    item = SuitabilityItem(
        airfoil_name="sd7037",
        family="cambered",
        re_agnostic=0.85,
        mission=None,
        target_cl_cruise=None,
        target_cl_min_sink=None,
        min_analysis_confidence=0.92,
        tip_re_flag=False,
        caveat="",
    )
    assert not hasattr(item, "target_cl_loiter"), (
        "SuitabilityItem must not have 'target_cl_loiter' field (renamed to target_cl_min_sink)"
    )


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
            target_cl_min_sink=None,
            min_analysis_confidence=0.9,
            tip_re_flag=False,
            caveat="",
        )


def test_suitability_item_gh825_fields():
    """gh-825: SuitabilityItem has target_cl_min_sink, target_cl_best_glide,
    stall_gentleness, cl_max_margin."""
    from app.schemas.airfoil import SuitabilityItem

    item = SuitabilityItem(
        airfoil_name="fx73cl2152",
        family="cambered",
        re_agnostic=0.90,
        mission=0.88,
        target_cl_cruise=0.75,
        target_cl_min_sink=0.85,
        target_cl_best_glide=0.78,
        stall_gentleness=-0.12,
        cl_max_margin=0.45,
        min_analysis_confidence=0.95,
        tip_re_flag=False,
        caveat="",
    )
    assert item.target_cl_min_sink == pytest.approx(0.85)
    assert item.target_cl_best_glide == pytest.approx(0.78)
    assert item.stall_gentleness == pytest.approx(-0.12)
    assert item.cl_max_margin == pytest.approx(0.45)


def test_suitability_query_required_fields():
    from app.schemas.airfoil import SuitabilityQuery

    q = SuitabilityQuery(
        chord_m=0.15,
        speed_ms=15.0,
        reynolds=150_000.0,
        re_clamped=False,
        mission_type=None,
        target_cl_cruise=None,
        target_cl_min_sink=None,
        active_lens="re_agnostic",
    )
    assert q.chord_m == pytest.approx(0.15)
    assert q.speed_ms == pytest.approx(15.0)
    assert q.reynolds == pytest.approx(150_000.0)
    assert q.re_clamped is False
    assert q.mission_type is None
    assert q.target_cl_cruise is None
    assert q.target_cl_min_sink is None
    assert q.active_lens == "re_agnostic"


def test_suitability_query_gh825_fields():
    """gh-825: SuitabilityQuery has target_cl_min_sink, target_cl_best_glide,
    target_cl_provenance (and no longer has target_cl_loiter)."""
    from app.schemas.airfoil import SuitabilityQuery

    q = SuitabilityQuery(
        chord_m=0.2,
        speed_ms=14.0,
        reynolds=191_781.0,
        re_clamped=False,
        mission_type="glider",
        target_cl_cruise=0.65,
        target_cl_min_sink=1.10,
        target_cl_best_glide=0.80,
        target_cl_provenance="calculated",
        active_lens="mission",
    )
    assert q.target_cl_min_sink == pytest.approx(1.10)
    assert q.target_cl_best_glide == pytest.approx(0.80)
    assert q.target_cl_provenance == "calculated"
    assert not hasattr(q, "target_cl_loiter"), (
        "SuitabilityQuery must not have 'target_cl_loiter' (renamed to target_cl_min_sink)"
    )


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
            target_cl_min_sink=None,
            active_lens=lens,
        )
        assert q.active_lens == lens


def test_suitability_query_active_lens_never_loiter():
    """active_lens MUST NOT be 'target_cl_loiter' per the frozen contract."""
    from app.schemas.airfoil import SuitabilityQuery

    with pytest.raises(ValidationError):
        SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            mission_type=None,
            target_cl_cruise=None,
            target_cl_min_sink=None,
            active_lens="target_cl_loiter",  # NOT valid
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


def test_suitability_caveat_gh825_ignores_tip_re_clmax_collapse():
    """gh-825: SuitabilityCaveat has ignores_tip_re_clmax_collapse field (always True)."""
    from app.schemas.airfoil import SuitabilityCaveat

    cav = SuitabilityCaveat(
        relative_ranking_only=True,
        no_hysteresis_modelling=True,
        ignores_tip_re_clmax_collapse=True,
        recommend_xfoil_validation=False,
        text="Test caveat.",
    )
    assert cav.ignores_tip_re_clmax_collapse is True


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
            target_cl_min_sink=None,
            active_lens="re_agnostic",
        ),
        caveat=SuitabilityCaveat(
            relative_ranking_only=True,
            no_hysteresis_modelling=True,
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
                target_cl_min_sink=None,
                min_analysis_confidence=0.92,
                tip_re_flag=False,
                caveat="",
            )
        ],
    )
    # Verify gh-825 field names serialize correctly
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
    assert "target_cl_min_sink" in q
    assert "target_cl_best_glide" in q
    assert "target_cl_provenance" in q
    assert "active_lens" in q
    # Old field must NOT be in serialised output
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
    assert "target_cl_min_sink" in r
    assert "target_cl_best_glide" in r
    assert "stall_gentleness" in r
    assert "cl_max_margin" in r
    assert "min_analysis_confidence" in r
    assert "tip_re_flag" in r
    assert "caveat" in r
    # Old field must NOT be in serialised output
    assert "target_cl_loiter" not in r
