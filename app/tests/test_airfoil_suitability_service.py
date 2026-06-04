"""Tests for search_suitability service (Task 7, gh-821).

Uses mocked DB rows and in-memory SQLite. NO real AeroSandbox.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def in_memory_db():
    """In-memory SQLite with all tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.base import Base
    import app.models  # noqa: F401
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def seeded_db(in_memory_db):
    """DB with 2 seeded airfoils + polars for suitability testing."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
    from app.models.aeroplanemodel import AeroplaneModel
    from app.models.mission_objective import MissionObjectiveModel

    with in_memory_db() as session:
        # Airfoil 1: good low-Re performer (sd7037-like)
        af1 = AirfoilModel(name="sd7037", coordinates=[[0, 0], [0.5, 0.06], [1, 0]])
        session.add(af1)
        session.flush()
        g1 = AirfoilGeometryModel(
            airfoil_name="sd7037",
            max_thickness_pct=9.2,
            max_camber_pct=2.5,
            camber_at_te=0.001,
            family="cambered",
            computed_at=datetime.now(timezone.utc),
        )
        session.add(g1)
        # Polars for sd7037 at two Re points
        for re_val, ld, cl_max, cd_min, cd0, k, cl0, bucket in [
            (100_000, 45.0, 1.2, 0.010, 0.012, 0.04, 0.3, 0.6),
            (200_000, 55.0, 1.3, 0.009, 0.011, 0.035, 0.3, 0.7),
        ]:
            session.add(
                AirfoilLowRePolarModel(
                    airfoil_name="sd7037",
                    reynolds=float(re_val),
                    ld_max=ld,
                    cl_max=cl_max,
                    alpha_attached_lo=-3.0,
                    alpha_attached_hi=12.0,
                    drag_bucket_width=bucket,
                    cd_min=cd_min,
                    stall_gentleness=-0.05,
                    cd0=cd0,
                    k=k,
                    cl0=cl0,
                    cl_valid_lo=0.0,
                    cl_valid_hi=1.2,
                    min_analysis_confidence=0.95,
                    neuralfoil_model_size="xxxlarge",
                    n_crit=9.0,
                    computed_at=datetime.now(timezone.utc),
                )
            )

        # Airfoil 2: poor performer (naca0012-like)
        af2 = AirfoilModel(name="naca0012", coordinates=[[0, 0], [0.5, 0.06], [1, 0]])
        session.add(af2)
        session.flush()
        g2 = AirfoilGeometryModel(
            airfoil_name="naca0012",
            max_thickness_pct=12.0,
            max_camber_pct=0.0,
            camber_at_te=0.0,
            family="symmetric",
            computed_at=datetime.now(timezone.utc),
        )
        session.add(g2)
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="naca0012",
                reynolds=100_000.0,
                ld_max=20.0,
                cl_max=0.9,
                alpha_attached_lo=-5.0,
                alpha_attached_hi=10.0,
                drag_bucket_width=0.2,
                cd_min=0.020,
                stall_gentleness=-0.3,
                cd0=0.022,
                k=0.06,
                cl0=0.0,
                cl_valid_lo=-0.2,
                cl_valid_hi=0.8,
                min_analysis_confidence=0.90,
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )
        )

        # Create an aeroplane with mission + context
        ap_uuid = uuid.uuid4()
        aeroplane = AeroplaneModel(
            name="test-plane",
            uuid=ap_uuid,
            total_mass_kg=2.0,
            assumption_computation_context={
                "mass_kg": 2.0,
                "v_cruise_mps": 18.0,
                "s_ref_m2": 0.35,
                "v_min_sink_mps": 12.0,
            },
        )
        session.add(aeroplane)
        session.flush()
        mission_obj = MissionObjectiveModel(
            aeroplane_id=aeroplane.id,
            mission_type="trainer",
        )
        session.add(mission_obj)
        session.commit()
        session.refresh(aeroplane)

    return in_memory_db, ap_uuid


def test_search_suitability_returns_results(seeded_db):
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
        )
    assert resp is not None
    assert len(resp.results) > 0


def test_search_suitability_ranked_desc_by_re_agnostic(seeded_db):
    """Without aeroplane context, results are ranked by re_agnostic (desc)."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)

    scores = [r.re_agnostic for r in resp.results]
    # Verify descending order
    assert scores == sorted(scores, reverse=True)
    # active_lens must be re_agnostic when no context
    assert resp.query.active_lens == "re_agnostic"


def test_search_suitability_re_clamped_flag(seeded_db):
    """Very high speed → Re above grid → re_clamped=True."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        # chord=0.5m, speed=200 m/s → Re = 1.225*200*0.5/1.81e-5 >> 750k
        resp = search_suitability(db=session, chord_m=0.5, speed_ms=200.0)
    assert resp.query.re_clamped is True


def test_search_suitability_no_re_clamped_for_midrange(seeded_db):
    """Normal RC speed/chord → Re in grid → re_clamped=False."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        # chord=0.15m, speed=15m/s → Re ≈ 152k (inside grid)
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
    assert resp.query.re_clamped is False


def test_search_suitability_with_aeroplane_id_resolves_uuid(seeded_db):
    """With aeroplane_id (UUID str), mission + target_cl lenses become available."""
    from app.services.suitability_service import search_suitability

    SessionLocal, ap_uuid = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            aeroplane_id=str(ap_uuid),
        )
    # Mission type comes from the aeroplane's mission_objective → "trainer"
    assert resp.query.mission_type == "trainer"
    # At least one result should have a non-null mission score
    mission_scores = [r.mission for r in resp.results]
    assert any(s is not None for s in mission_scores)


def test_search_suitability_unknown_uuid_degrades_gracefully(seeded_db):
    """Unknown UUID → degrade to re_agnostic-only, NOT 500."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        unknown_uuid = str(uuid.uuid4())
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            aeroplane_id=unknown_uuid,
        )
    # No crash; mission scores should all be None
    assert resp is not None
    assert resp.query.active_lens == "re_agnostic"


def test_search_suitability_explicit_mission_type_overrides(seeded_db):
    """explicit mission_type parameter overrides model-derived value."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            mission_type="aerobatic",
        )
    assert resp.query.mission_type == "aerobatic"


def test_search_suitability_explicit_target_cl_overrides(seeded_db):
    """Explicit target_cl_cruise param is echoed in query block."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            target_cl_cruise=0.5,
        )
    assert resp.query.target_cl_cruise == pytest.approx(0.5)


def test_search_suitability_active_lens_is_never_glide_points(seeded_db):
    """active_lens must never be 'target_cl_min_sink' or 'target_cl_best_glide'
    (these are display-only glide-point lenses, not ranking lenses)."""
    from app.services.suitability_service import search_suitability

    SessionLocal, ap_uuid = seeded_db
    with SessionLocal() as session:
        for params in [
            {},
            {"aeroplane_id": str(ap_uuid)},
            {"target_cl_min_sink": 0.8},
            {"target_cl_best_glide": 0.7},
            {"mission_type": "glider"},
        ]:
            resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0, **params)
            assert resp.query.active_lens not in ("target_cl_min_sink", "target_cl_best_glide"), (
                f"active_lens must not be a glide-point lens, got '{resp.query.active_lens}'"
            )


def test_search_suitability_target_cl_min_sink_echoed_in_query(seeded_db):
    """Explicit target_cl_min_sink is echoed in the query block."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            target_cl_min_sink=1.1,
        )
    assert resp.query.target_cl_min_sink == pytest.approx(1.1)
    # The min-sink score must be non-None for at least some airfoils
    scores = [r.target_cl_min_sink for r in resp.results]
    # At CL=1.1, some airfoils should score > 0
    assert any(s is not None for s in scores)


def test_search_suitability_min_sink_score_positive_for_high_cl_glider(seeded_db):
    """gh-825 fix: for a glider min-sink CL of 1.0+, the score must be > 0.0
    for a good airfoil (sd7037). Before the fix, score_target_cl used CD-based
    normalisation that returned 0.0 for any CD > 0.05 (which all airfoils exceed
    at CL≈1.1)."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    # CL_min_sink for a glider might be ~1.1
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.20,
            speed_ms=14.0,
            target_cl_min_sink=1.1,
        )
    # sd7037 is our good airfoil — its min-sink score must be > 0
    sd_item = next((r for r in resp.results if r.airfoil_name == "sd7037"), None)
    assert sd_item is not None, "sd7037 must be in results"
    assert sd_item.target_cl_min_sink is not None, (
        "target_cl_min_sink score must not be None for sd7037"
    )
    assert sd_item.target_cl_min_sink > 0.0, (
        f"gh-825 bug: sd7037 target_cl_min_sink={sd_item.target_cl_min_sink} should be > 0 "
        f"for a good airfoil at CL_target=1.1"
    )


def test_search_suitability_stall_gentleness_and_cl_max_margin_populated(seeded_db):
    """gh-825: stall_gentleness and cl_max_margin are populated in each result."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            target_cl_cruise=0.5,
        )
    # stall_gentleness should be non-null for airfoils that have it in the polar
    items_with_stall = [r for r in resp.results if r.stall_gentleness is not None]
    assert len(items_with_stall) > 0, "At least some results should have stall_gentleness"
    # cl_max_margin should be non-null when target CL and polar cl_max are available
    items_with_margin = [r for r in resp.results if r.cl_max_margin is not None]
    assert len(items_with_margin) > 0, "At least some results should have cl_max_margin"


def test_search_suitability_tip_re_flag(seeded_db):
    """When tip_chord_m is given and tip Re < root Re, tip_re_flag=True."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.20,
            speed_ms=15.0,
            tip_chord_m=0.08,  # smaller tip chord → lower Re
        )
    # tip_re_flag should be True for all items when tip Re < root Re
    tip_re_root = 1.225 * 15.0 * 0.20 / 1.81e-5
    tip_re_tip = 1.225 * 15.0 * 0.08 / 1.81e-5
    if tip_re_tip < tip_re_root:
        assert all(r.tip_re_flag for r in resp.results)


def test_search_suitability_recommend_xfoil_when_low_confidence(seeded_db):
    """recommend_xfoil_validation=True when any item has min_confidence < 0.85."""
    from app.services.suitability_service import search_suitability
    from app.models.airfoil_low_re import AirfoilLowRePolarModel
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel

    SessionLocal, _ = seeded_db
    # Add an airfoil with low confidence polar
    with SessionLocal() as session:
        af = AirfoilModel(name="low_conf_af", coordinates=[[0, 0], [1, 0]])
        session.add(af)
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="low_conf_af",
                max_thickness_pct=10.0,
                max_camber_pct=1.0,
                camber_at_te=0.0,
                family="semi_symmetric",
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="low_conf_af",
                reynolds=100_000.0,
                ld_max=15.0,
                cl_max=0.8,
                alpha_attached_lo=-2.0,
                alpha_attached_hi=8.0,
                drag_bucket_width=0.2,
                cd_min=0.025,
                stall_gentleness=-0.5,
                cd0=0.028,
                k=0.06,
                cl0=0.1,
                cl_valid_lo=0.0,
                cl_valid_hi=0.7,
                min_analysis_confidence=0.80,  # below 0.85 flag threshold
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    with SessionLocal() as session:
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
    assert resp.caveat.recommend_xfoil_validation is True


def test_search_suitability_limit_parameter(seeded_db):
    """limit parameter caps the number of results."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0, limit=1)
    assert len(resp.results) <= 1


def test_search_suitability_caveat_block_always_present(seeded_db):
    """caveat block must be present with required fields in every response."""
    from app.services.suitability_service import search_suitability

    SessionLocal, _ = seeded_db
    with SessionLocal() as session:
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
    assert resp.caveat.relative_ranking_only is True
    assert resp.caveat.no_hysteresis_modelling is True
    assert isinstance(resp.caveat.text, str)
    assert len(resp.caveat.text) > 0


# ---------------------------------------------------------------------------
# gh-821 persona-smoke fixes
# ---------------------------------------------------------------------------


def test_sailplane_mission_type_activates_mission_lens(seeded_db):
    """Blocker gh-821: aeroplane with mission_type='sailplane' must resolve to
    the 'glider' weighting lens — not null.  The eHawk persona exposed this:
    the _MISSION_TYPE_MAP was missing 'sailplane' so mission=null was returned
    for every result and the active_lens fell back to re_agnostic.
    """
    from app.services.suitability_service import search_suitability
    from app.models.aeroplanemodel import AeroplaneModel
    from app.models.mission_objective import MissionObjectiveModel

    SessionLocal, _ = seeded_db
    ap2_uuid = uuid.uuid4()
    with SessionLocal() as session:
        ap2 = AeroplaneModel(
            name="ehawk",
            uuid=ap2_uuid,
            total_mass_kg=2.5,
            assumption_computation_context={
                "mass_kg": 2.5,
                "v_cruise_mps": 16.0,
                "s_ref_m2": 0.50,
                "v_min_sink_mps": 10.0,
            },
        )
        session.add(ap2)
        session.flush()
        session.add(MissionObjectiveModel(aeroplane_id=ap2.id, mission_type="sailplane"))
        session.commit()

    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.20,
            speed_ms=14.0,
            aeroplane_id=str(ap2_uuid),
        )

    # mission_type must be resolved to "glider" (via the alias map)
    assert resp.query.mission_type == "glider", (
        f"Expected 'glider' from sailplane alias; got '{resp.query.mission_type}'"
    )
    # active_lens must be 'mission' (not re_agnostic) because mission is now resolved
    assert resp.query.active_lens == "mission", (
        f"Expected active_lens='mission'; got '{resp.query.active_lens}'"
    )
    # At least one result must have a non-null mission score
    assert any(r.mission is not None for r in resp.results), (
        "All mission scores are None — glider weighting was not applied"
    )


@pytest.mark.parametrize(
    "stored_mission_type,expected_lens_key",
    [
        ("sailplane", "glider"),
        ("motor_glider", "glider"),
        ("motorglider", "glider"),
        ("slope_soarer", "glider"),
        ("wing_racer", "sport"),
        ("acro_3d", "aerobatic"),
        ("stol_bush", "trainer"),
    ],
)
def test_mission_type_map_covers_all_stored_presets(
    seeded_db, stored_mission_type, expected_lens_key
):
    """Every valid stored mission_type must map to a weighting-enum key so the
    mission lens activates.  This test validates the _MISSION_TYPE_MAP
    exhaustiveness for all non-core preset ids introduced in mission_preset_seed.py.
    """
    from app.services.suitability_service import search_suitability
    from app.models.aeroplanemodel import AeroplaneModel
    from app.models.mission_objective import MissionObjectiveModel

    SessionLocal, _ = seeded_db
    ap_uuid = uuid.uuid4()
    with SessionLocal() as session:
        ap = AeroplaneModel(
            name=f"test-{stored_mission_type}",
            uuid=ap_uuid,
            total_mass_kg=2.0,
            assumption_computation_context={
                "mass_kg": 2.0,
                "v_cruise_mps": 18.0,
                "s_ref_m2": 0.35,
                "v_min_sink_mps": 12.0,
            },
        )
        session.add(ap)
        session.flush()
        session.add(MissionObjectiveModel(aeroplane_id=ap.id, mission_type=stored_mission_type))
        session.commit()

    with SessionLocal() as session:
        resp = search_suitability(
            db=session,
            chord_m=0.15,
            speed_ms=15.0,
            aeroplane_id=str(ap_uuid),
        )

    assert resp.query.mission_type == expected_lens_key, (
        f"mission_type='{stored_mission_type}' → expected '{expected_lens_key}', "
        f"got '{resp.query.mission_type}'"
    )
    assert resp.query.active_lens == "mission", (
        f"Expected active_lens='mission' for '{stored_mission_type}'; "
        f"got '{resp.query.active_lens}'"
    )


def test_confidence_aware_ranking_high_score_low_conf_ranks_below_reliable(seeded_db):
    """BUG-3 fix: a high-score item with low analysis confidence must rank *below*
    a slightly-lower-score item that has high confidence (>= 0.85 threshold).

    Sort key change: items are grouped by confidence tier first
    (confident: min_analysis_confidence >= 0.85 come first),
    then sorted by active-lens score descending within each tier.
    The *displayed* scores (re_agnostic / mission / target_cl_cruise) are
    unchanged — only the sort order is confidence-aware.
    """
    from app.services.suitability_service import search_suitability
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel

    SessionLocal, _ = seeded_db

    # Add a third airfoil: excellent re_agnostic score BUT low confidence (0.046)
    # This simulates the sd7037 low-confidence scenario from the smoke-test report.
    with SessionLocal() as session:
        af = AirfoilModel(name="high_score_low_conf", coordinates=[[0, 0], [0.5, 0.07], [1, 0]])
        session.add(af)
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="high_score_low_conf",
                max_thickness_pct=10.0,
                max_camber_pct=3.0,
                camber_at_te=0.001,
                family="cambered",
                computed_at=datetime.now(timezone.utc),
            )
        )
        # Polar with an extremely high ld_max / cl_max but min_analysis_confidence=0.046
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="high_score_low_conf",
                reynolds=100_000.0,
                ld_max=999.0,  # would rank #1 on re_agnostic alone
                cl_max=2.0,
                alpha_attached_lo=-5.0,
                alpha_attached_hi=20.0,
                drag_bucket_width=1.0,
                cd_min=0.001,
                stall_gentleness=-0.01,
                cd0=0.002,
                k=0.01,
                cl0=0.5,
                cl_valid_lo=-0.5,
                cl_valid_hi=2.0,
                min_analysis_confidence=0.046,  # far below 0.85 flag threshold
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    with SessionLocal() as session:
        resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)

    # The low-confidence item must NOT be ranked first
    first_result = resp.results[0]
    assert first_result.airfoil_name != "high_score_low_conf", (
        "Low-confidence item 'high_score_low_conf' (conf=0.046) ranked #1 despite "
        "having a high re_agnostic score — confidence-aware sort is broken."
    )

    # All high-confidence items must appear before the low-confidence one
    from app.settings import Settings

    low_conf_flag = Settings().low_re_low_confidence_flag
    high_conf_names = {
        r.airfoil_name for r in resp.results if r.min_analysis_confidence >= low_conf_flag
    }
    low_conf_names = {
        r.airfoil_name for r in resp.results if r.min_analysis_confidence < low_conf_flag
    }

    # Verify that the positions are correct: last index of high-conf < first index of low-conf
    result_names = [r.airfoil_name for r in resp.results]
    if high_conf_names and low_conf_names:
        last_high_conf_idx = max(result_names.index(n) for n in high_conf_names)
        first_low_conf_idx = min(result_names.index(n) for n in low_conf_names)
        assert last_high_conf_idx < first_low_conf_idx, (
            f"High-confidence items should all appear before low-confidence items. "
            f"Last high-conf idx={last_high_conf_idx}, first low-conf idx={first_low_conf_idx}. "
            f"Order: {result_names}"
        )
