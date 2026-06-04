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
            session.add(AirfoilLowRePolarModel(
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
            ))

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
        session.add(AirfoilLowRePolarModel(
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
        ))

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


def test_search_suitability_active_lens_is_never_loiter(seeded_db):
    """active_lens must never be 'target_cl_loiter'."""
    from app.services.suitability_service import search_suitability

    SessionLocal, ap_uuid = seeded_db
    with SessionLocal() as session:
        for params in [
            {},
            {"aeroplane_id": str(ap_uuid)},
            {"target_cl_loiter": 0.8},
            {"mission_type": "glider"},
        ]:
            resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0, **params)
            assert resp.query.active_lens != "target_cl_loiter", (
                f"active_lens must never be 'target_cl_loiter', got '{resp.query.active_lens}'"
            )


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
        session.add(AirfoilGeometryModel(
            airfoil_name="low_conf_af",
            max_thickness_pct=10.0,
            max_camber_pct=1.0,
            camber_at_te=0.0,
            family="semi_symmetric",
            computed_at=datetime.now(timezone.utc),
        ))
        session.add(AirfoilLowRePolarModel(
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
        ))
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
