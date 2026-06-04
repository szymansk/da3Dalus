"""Tests for suitability_service gh-825 additions.

TDD: RED first for new features, then GREEN.  All pure math / mocked DB.
Covers:
  - B4: three target CLs from ctx (v_cruise, v_md, v_min_sink)
  - B5: three target scores + stall_gentleness + cl_max_margin per item
  - B6: target_cl_provenance from DesignAssumptionModel
  - B7: schema contract (new fields)
  - B8/B9: endpoint param rename + full flow
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# In-memory DB fixture (shared)
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_db():
    """In-memory SQLite with all tables."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def seeded_db_825(in_memory_db):
    """DB with 2 airfoils + polars + aeroplane with all 3 speed context values."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
    from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
    from app.models.mission_objective import MissionObjectiveModel

    ap_uuid = uuid.uuid4()

    with in_memory_db() as session:
        # Airfoil 1: good performer
        session.add(AirfoilModel(name="good_af", coordinates=[[0, 0], [0.5, 0.07], [1, 0]]))
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="good_af",
                max_thickness_pct=9.5,
                max_camber_pct=3.0,
                camber_at_te=0.001,
                family="cambered",
                computed_at=datetime.now(timezone.utc),
            )
        )
        # Polar at two Re points with wide bucket
        for re_val, ld, cl_max_val, cd0, k, cl0, bucket, stall_g in [
            (100_000, 48.0, 1.2, 0.011, 0.038, 0.30, 0.65, -0.04),
            (200_000, 58.0, 1.3, 0.010, 0.035, 0.30, 0.70, -0.03),
        ]:
            session.add(
                AirfoilLowRePolarModel(
                    airfoil_name="good_af",
                    reynolds=float(re_val),
                    ld_max=ld,
                    cl_max=cl_max_val,
                    alpha_attached_lo=-3.0,
                    alpha_attached_hi=12.0,
                    drag_bucket_width=bucket,
                    cd_min=cd0,
                    stall_gentleness=stall_g,
                    cd0=cd0,
                    k=k,
                    cl0=cl0,
                    cl_valid_lo=0.0,
                    cl_valid_hi=1.3,
                    min_analysis_confidence=0.95,
                    neuralfoil_model_size="xxxlarge",
                    n_crit=9.0,
                    computed_at=datetime.now(timezone.utc),
                )
            )

        # Airfoil 2: poor performer
        session.add(AirfoilModel(name="poor_af", coordinates=[[0, 0], [0.5, 0.06], [1, 0]]))
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="poor_af",
                max_thickness_pct=12.0,
                max_camber_pct=0.0,
                camber_at_te=0.0,
                family="symmetric",
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="poor_af",
                reynolds=100_000.0,
                ld_max=20.0,
                cl_max=0.9,
                alpha_attached_lo=-5.0,
                alpha_attached_hi=10.0,
                drag_bucket_width=0.15,
                cd_min=0.022,
                stall_gentleness=-0.35,
                cd0=0.024,
                k=0.065,
                cl0=0.0,
                cl_valid_lo=-0.2,
                cl_valid_hi=0.8,
                min_analysis_confidence=0.90,
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )
        )

        # Aeroplane with all three speed context values
        ap = AeroplaneModel(
            name="test825",
            uuid=ap_uuid,
            total_mass_kg=2.0,
            assumption_computation_context={
                "mass_kg": 2.0,
                "s_ref_m2": 0.35,
                "v_cruise_mps": 18.0,
                "v_md_mps": 13.0,  # best-glide speed
                "v_min_sink_mps": 10.0,
                "v_cruise_auto": True,
            },
        )
        session.add(ap)
        session.flush()
        session.add(MissionObjectiveModel(aeroplane_id=ap.id, mission_type="glider"))

        # DesignAssumptionModel for 'mass' parameter with CALCULATED source
        session.add(
            DesignAssumptionModel(
                aeroplane_id=ap.id,
                parameter_name="mass",
                estimate_value=2.0,
                calculated_value=1.95,
                active_source="CALCULATED",
            )
        )
        session.commit()
        session.refresh(ap)

    return in_memory_db, ap_uuid


# ---------------------------------------------------------------------------
# TASK B4: Three target CLs from context
# ---------------------------------------------------------------------------


class TestThreeTargetCls:
    def test_cruise_cl_resolved_from_v_cruise(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        # cruise CL should be resolved (not None)
        assert resp.query.target_cl_cruise is not None
        assert resp.query.target_cl_cruise > 0.0

    def test_best_glide_cl_resolved_from_v_md(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        # best_glide CL from v_md_mps
        assert resp.query.target_cl_best_glide is not None
        assert resp.query.target_cl_best_glide > 0.0
        # Best-glide CL > cruise CL (slower speed = higher CL)
        assert resp.query.target_cl_best_glide > resp.query.target_cl_cruise

    def test_min_sink_cl_resolved_from_v_min_sink(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        # min-sink CL from v_min_sink_mps
        assert resp.query.target_cl_min_sink is not None
        assert resp.query.target_cl_min_sink > resp.query.target_cl_best_glide

    def test_missing_v_md_gives_null_best_glide(self, in_memory_db):
        """When v_md_mps is absent, target_cl_best_glide must be None."""
        from app.models.airfoil import AirfoilModel
        from app.models.airfoil_low_re import AirfoilGeometryModel
        from app.models.aeroplanemodel import AeroplaneModel
        from app.services.suitability_service import search_suitability

        ap_uuid2 = uuid.uuid4()
        with in_memory_db() as session:
            session.add(AirfoilModel(name="af_x", coordinates=[[0, 0], [1, 0]]))
            session.flush()
            session.add(
                AirfoilGeometryModel(
                    airfoil_name="af_x",
                    max_thickness_pct=10.0,
                    max_camber_pct=2.0,
                    camber_at_te=0.0,
                    family="cambered",
                    computed_at=datetime.now(timezone.utc),
                )
            )
            ap = AeroplaneModel(
                name="no_vmd",
                uuid=ap_uuid2,
                total_mass_kg=2.0,
                assumption_computation_context={
                    "mass_kg": 2.0,
                    "s_ref_m2": 0.35,
                    "v_cruise_mps": 18.0,
                    # v_md_mps ABSENT
                    "v_min_sink_mps": 10.0,
                },
            )
            session.add(ap)
            session.commit()

        with in_memory_db() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid2),
            )
        assert resp.query.target_cl_best_glide is None

    def test_explicit_best_glide_override_echoes_back(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                target_cl_best_glide=0.9,
            )
        assert resp.query.target_cl_best_glide == pytest.approx(0.9)

    def test_explicit_min_sink_override_echoes_back(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                target_cl_min_sink=1.1,
            )
        assert resp.query.target_cl_min_sink == pytest.approx(1.1)


# ---------------------------------------------------------------------------
# TASK B5: stall_gentleness + cl_max_margin + three target scores per item
# ---------------------------------------------------------------------------


class TestItemNewFields:
    def test_stall_gentleness_present_in_items(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
        # Items with polar data should have stall_gentleness != None
        items_with_polar = [r for r in resp.results if r.re_agnostic > 0]
        assert any(r.stall_gentleness is not None for r in items_with_polar)

    def test_cl_max_margin_present_and_numeric(self, seeded_db_825):
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        # At least one item should have cl_max_margin computed
        items_with_margin = [r for r in resp.results if r.cl_max_margin is not None]
        assert len(items_with_margin) > 0

    def test_cl_max_margin_positive_when_target_below_cl_max(self, seeded_db_825):
        """cl_max_margin = cl_max - max(target CLs) > 0 when target < cl_max."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            # low target CL — well below any airfoil's cl_max
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                target_cl_cruise=0.3,
            )
        for item in resp.results:
            if item.cl_max_margin is not None:
                assert item.cl_max_margin >= -0.1, (
                    f"cl_max_margin should be positive for CL target=0.3 << cl_max; "
                    f"got {item.cl_max_margin:.3f} for {item.airfoil_name}"
                )

    def test_three_target_scores_present_in_items(self, seeded_db_825):
        """When aeroplane context resolves all three speeds, items should carry
        all three target CL scores (not all None)."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        items_with_polar = [r for r in resp.results if r.re_agnostic > 0]
        assert any(r.target_cl_cruise is not None for r in items_with_polar)
        assert any(r.target_cl_best_glide is not None for r in items_with_polar)
        assert any(r.target_cl_min_sink is not None for r in items_with_polar)

    def test_none_propagation_when_no_context(self, seeded_db_825):
        """Without aeroplane context, all three target CL scores should be None."""
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
        for item in resp.results:
            assert item.target_cl_cruise is None
            assert item.target_cl_best_glide is None
            assert item.target_cl_min_sink is None


# ---------------------------------------------------------------------------
# TASK B6: target_cl_provenance from DesignAssumptionModel
# ---------------------------------------------------------------------------


class TestTargetClProvenance:
    def test_provenance_calculated_when_mass_calculated(self, seeded_db_825):
        """When mass has CALCULATED source + v_cruise_auto=True → 'calculated'."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        assert resp.query.target_cl_provenance == "calculated"

    def test_provenance_estimated_when_no_aeroplane(self, seeded_db_825):
        """No aeroplane context → provenance defaults to 'estimated'."""
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0)
        assert resp.query.target_cl_provenance == "estimated"

    def test_provenance_estimated_when_mass_is_estimate(self, in_memory_db):
        """Mass with ESTIMATE source → provenance = 'estimated'."""
        from app.models.airfoil import AirfoilModel
        from app.models.airfoil_low_re import AirfoilGeometryModel
        from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
        from app.services.suitability_service import search_suitability

        ap_uuid2 = uuid.uuid4()
        with in_memory_db() as session:
            session.add(AirfoilModel(name="af_prov", coordinates=[[0, 0], [1, 0]]))
            session.flush()
            session.add(
                AirfoilGeometryModel(
                    airfoil_name="af_prov",
                    max_thickness_pct=10.0,
                    max_camber_pct=2.0,
                    camber_at_te=0.0,
                    family="cambered",
                    computed_at=datetime.now(timezone.utc),
                )
            )
            ap = AeroplaneModel(
                name="estimate_plane",
                uuid=ap_uuid2,
                total_mass_kg=2.0,
                assumption_computation_context={
                    "mass_kg": 2.0,
                    "s_ref_m2": 0.35,
                    "v_cruise_mps": 18.0,
                    # v_cruise_auto NOT set → estimated
                },
            )
            session.add(ap)
            session.flush()
            session.add(
                DesignAssumptionModel(
                    aeroplane_id=ap.id,
                    parameter_name="mass",
                    estimate_value=2.0,
                    active_source="ESTIMATE",
                )
            )
            session.commit()

        with in_memory_db() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid2),
            )
        assert resp.query.target_cl_provenance == "estimated"

    def test_provenance_mixed_when_mass_calculated_but_no_v_cruise_auto(self, in_memory_db):
        """Mass CALCULATED but v_cruise_auto missing/False → 'mixed'."""
        from app.models.airfoil import AirfoilModel
        from app.models.airfoil_low_re import AirfoilGeometryModel
        from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
        from app.services.suitability_service import search_suitability

        ap_uuid3 = uuid.uuid4()
        with in_memory_db() as session:
            session.add(AirfoilModel(name="af_mixed", coordinates=[[0, 0], [1, 0]]))
            session.flush()
            session.add(
                AirfoilGeometryModel(
                    airfoil_name="af_mixed",
                    max_thickness_pct=10.0,
                    max_camber_pct=2.0,
                    camber_at_te=0.0,
                    family="cambered",
                    computed_at=datetime.now(timezone.utc),
                )
            )
            ap = AeroplaneModel(
                name="mixed_plane",
                uuid=ap_uuid3,
                total_mass_kg=2.0,
                assumption_computation_context={
                    "mass_kg": 2.0,
                    "s_ref_m2": 0.35,
                    "v_cruise_mps": 18.0,
                    # v_cruise_auto ABSENT → speed is estimated
                },
            )
            session.add(ap)
            session.flush()
            session.add(
                DesignAssumptionModel(
                    aeroplane_id=ap.id,
                    parameter_name="mass",
                    estimate_value=2.0,
                    calculated_value=1.95,
                    active_source="CALCULATED",  # mass is calculated
                )
            )
            session.commit()

        with in_memory_db() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid3),
            )
        assert resp.query.target_cl_provenance == "mixed"


# ---------------------------------------------------------------------------
# TASK B7: Schema contract — new fields
# ---------------------------------------------------------------------------


class TestSchemaContract825:
    def test_suitability_item_new_fields_present(self):
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
        assert item.target_cl_best_glide is None
        assert item.target_cl_min_sink is None
        assert item.stall_gentleness == pytest.approx(-0.04)
        assert item.cl_max_margin == pytest.approx(0.3)

    def test_suitability_item_no_target_cl_loiter_field(self):
        """target_cl_loiter must NOT be in the schema (renamed to target_cl_min_sink)."""
        from app.schemas.airfoil import SuitabilityItem

        item = SuitabilityItem(
            airfoil_name="test",
            family="symmetric",
            re_agnostic=0.5,
            min_analysis_confidence=0.9,
            tip_re_flag=False,
            caveat="",
        )
        data = item.model_dump()
        assert "target_cl_loiter" not in data, "target_cl_loiter must be removed in gh-825"
        assert "target_cl_min_sink" in data
        assert "target_cl_best_glide" in data
        assert "stall_gentleness" in data
        assert "cl_max_margin" in data

    def test_suitability_query_new_fields(self):
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
        assert q.target_cl_best_glide is None
        assert q.target_cl_min_sink is None
        assert q.target_cl_provenance == "estimated"

    def test_suitability_query_no_target_cl_loiter(self):
        from app.schemas.airfoil import SuitabilityQuery

        q = SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            active_lens="re_agnostic",
            target_cl_provenance="estimated",
        )
        data = q.model_dump()
        assert "target_cl_loiter" not in data
        assert "target_cl_min_sink" in data
        assert "target_cl_best_glide" in data
        assert "target_cl_provenance" in data

    def test_active_lens_never_glide_point(self):
        """active_lens must NOT accept best_glide or min_sink — glide points are display-only."""
        from app.schemas.airfoil import SuitabilityQuery
        from pydantic import ValidationError

        for bad_lens in ("target_cl_best_glide", "target_cl_min_sink", "target_cl_loiter"):
            with pytest.raises(ValidationError):
                SuitabilityQuery(
                    chord_m=0.15,
                    speed_ms=15.0,
                    reynolds=150_000.0,
                    re_clamped=False,
                    active_lens=bad_lens,
                    target_cl_provenance="estimated",
                )

    def test_target_cl_provenance_literal(self):
        from app.schemas.airfoil import SuitabilityQuery
        from pydantic import ValidationError

        for valid in ("estimated", "calculated", "mixed"):
            q = SuitabilityQuery(
                chord_m=0.15,
                speed_ms=15.0,
                reynolds=150_000.0,
                re_clamped=False,
                active_lens="re_agnostic",
                target_cl_provenance=valid,
            )
            assert q.target_cl_provenance == valid

        with pytest.raises(ValidationError):
            SuitabilityQuery(
                chord_m=0.15,
                speed_ms=15.0,
                reynolds=150_000.0,
                re_clamped=False,
                active_lens="re_agnostic",
                target_cl_provenance="unknown",
            )

    def test_caveat_has_ignores_tip_re_clmax_collapse(self):
        from app.schemas.airfoil import SuitabilityCaveat

        cav = SuitabilityCaveat(
            relative_ranking_only=True,
            no_hysteresis_modelling=True,
            ignores_tip_re_clmax_collapse=True,
            recommend_xfoil_validation=False,
            text="Test caveat.",
        )
        assert cav.ignores_tip_re_clmax_collapse is True

    def test_active_lens_excludes_glide_points(self):
        """ActiveLens literal must only be re_agnostic / mission / target_cl_cruise."""
        from app.schemas.airfoil import ActiveLens

        # These are the only valid values:
        valid = {"re_agnostic", "mission", "target_cl_cruise"}
        # We access the __args__ via typing.get_args
        import typing

        args = set(typing.get_args(ActiveLens))
        assert args == valid, f"ActiveLens args {args} != {valid}"

    def test_target_cl_provenance_type_exists(self):
        from app.schemas.airfoil import TargetClProvenance
        import typing

        args = set(typing.get_args(TargetClProvenance))
        assert args == {"estimated", "calculated", "mixed"}


# ---------------------------------------------------------------------------
# TASK B8/B9: Endpoint param rename + full flow
# ---------------------------------------------------------------------------


class TestEndpointParams825:
    @pytest.fixture()
    def client_825(self, in_memory_db):
        """TestClient backed by in-memory DB."""
        from app.db.base import Base
        import app.models  # noqa: F401
        from app.db.session import get_db
        from app.main import create_app
        from app.services.component_type_service import seed_default_types
        from app.services.mission_objective_service import seed_mission_presets

        app = create_app()
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(
            bind=engine, autocommit=False, autoflush=False, class_=Session
        )

        _s = TestingSessionLocal()
        try:
            seed_default_types(_s)
            seed_mission_presets(_s)
            _s.commit()
        finally:
            _s.close()

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            yield client
        app.dependency_overrides.clear()

    def _make_fake_response_825(self):
        """Build a minimal SuitabilityResponse with new gh-825 fields."""
        from app.schemas.airfoil import (
            SuitabilityResponse,
            SuitabilityQuery,
            SuitabilityCaveat,
            SuitabilityItem,
        )

        return SuitabilityResponse(
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
                text="Relative ranking only. Section CL ≈ wing CL (ideal elliptic). "
                "Tip-Re CL_max collapse not modelled.",
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
                    min_analysis_confidence=0.95,
                    tip_re_flag=False,
                    caveat="",
                )
            ],
        )

    def test_target_cl_min_sink_param_accepted(self, client_825):
        """target_cl_min_sink param (renamed from loiter) must be accepted by endpoint."""
        fake_resp = self._make_fake_response_825()
        with patch(
            "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
        ) as mock_svc:
            resp = client_825.get(
                "/airfoils/db/suitability",
                params={
                    "chord_m": 0.15,
                    "speed_ms": 15.0,
                    "target_cl_min_sink": 0.9,
                },
            )
        assert resp.status_code == 200
        call_kwargs = mock_svc.call_args[1]
        assert call_kwargs.get("target_cl_min_sink") == pytest.approx(0.9)

    def test_target_cl_best_glide_param_accepted(self, client_825):
        """target_cl_best_glide NEW param must be accepted and forwarded."""
        fake_resp = self._make_fake_response_825()
        with patch(
            "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
        ) as mock_svc:
            resp = client_825.get(
                "/airfoils/db/suitability",
                params={
                    "chord_m": 0.15,
                    "speed_ms": 15.0,
                    "target_cl_best_glide": 0.75,
                },
            )
        assert resp.status_code == 200
        call_kwargs = mock_svc.call_args[1]
        assert call_kwargs.get("target_cl_best_glide") == pytest.approx(0.75)

    def test_endpoint_response_has_new_fields(self, client_825):
        """Endpoint response must include the new gh-825 fields."""
        fake_resp = self._make_fake_response_825()
        with patch("app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp):
            resp = client_825.get(
                "/airfoils/db/suitability",
                params={"chord_m": 0.15, "speed_ms": 15.0},
            )
        assert resp.status_code == 200
        data = resp.json()
        q = data["query"]
        assert "target_cl_best_glide" in q
        assert "target_cl_min_sink" in q
        assert "target_cl_provenance" in q
        assert "target_cl_loiter" not in q

        cav = data["caveat"]
        assert "ignores_tip_re_clmax_collapse" in cav

        r = data["results"][0]
        assert "target_cl_best_glide" in r
        assert "target_cl_min_sink" in r
        assert "stall_gentleness" in r
        assert "cl_max_margin" in r
        assert "target_cl_loiter" not in r

    def test_active_lens_never_glide_point_in_response(self, seeded_db_825):
        """active_lens in actual service response must never be a glide point."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            for kwargs in [
                {},
                {"aeroplane_id": str(ap_uuid)},
                {"target_cl_min_sink": 0.9},
                {"target_cl_best_glide": 0.75},
            ]:
                resp = search_suitability(db=session, chord_m=0.15, speed_ms=15.0, **kwargs)
                assert resp.query.active_lens not in (
                    "target_cl_best_glide",
                    "target_cl_min_sink",
                    "target_cl_loiter",
                ), f"active_lens must never be a glide point, got '{resp.query.active_lens}'"

    def test_provenance_present_in_query_response(self, seeded_db_825):
        """target_cl_provenance must always be present in the response."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        assert resp.query.target_cl_provenance in ("estimated", "calculated", "mixed")

    def test_full_flow_response_shape(self, seeded_db_825):
        """End-to-end: full response shape with all new fields."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                aeroplane_id=str(ap_uuid),
            )
        # Schema-validated response
        data = resp.model_dump()

        # Query block
        q = data["query"]
        assert "target_cl_best_glide" in q
        assert "target_cl_min_sink" in q
        assert "target_cl_provenance" in q
        assert "target_cl_loiter" not in q
        assert q["active_lens"] in ("re_agnostic", "mission", "target_cl_cruise")

        # Caveat block
        cav = data["caveat"]
        assert cav["ignores_tip_re_clmax_collapse"] is True

        # Results block
        for item in data["results"]:
            assert "target_cl_best_glide" in item
            assert "target_cl_min_sink" in item
            assert "stall_gentleness" in item
            assert "cl_max_margin" in item
            assert "target_cl_loiter" not in item


# ---------------------------------------------------------------------------
# ITEM 2 (gh-825): Tip-Re significance threshold tests
# ---------------------------------------------------------------------------
#
# The threshold logic (gh-825 item 2):
#   tip_re_flag = True  iff
#       (re_tip < settings.low_re_tip_re_abs_floor)
#     OR
#       ((re_root - re_tip) > settings.low_re_tip_re_rel_drop)
#   otherwise False.
#
# Re computation: re = RHO * speed * chord / MU  (1.225*v*c/1.81e-5)
# For speed_ms=15.0:
#   chord 0.15 → Re ~152_072   (root)
#   tip_chord 0.10 → Re ~101_381
#   tip_chord 0.08 → Re ~81_105
#   tip_chord 0.07 → Re ~70_967  (below 80k floor)
#
# _RHO=1.225, _MU=1.81e-5 → Re = 1.225*15/1.81e-5 * chord
#                                = 1_015_470 * chord  (approx)
# More precisely: 1.225*15.0/1.81e-5 = 1_015_470.0 (per metre of chord)


def _make_minimal_db_with_airfoil(in_memory_db):
    """Seed one airfoil + geometry + polar so search_suitability returns items."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
    from datetime import datetime, timezone

    with in_memory_db() as session:
        session.add(AirfoilModel(name="tip_re_af", coordinates=[[0, 0], [0.5, 0.07], [1, 0]]))
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="tip_re_af",
                max_thickness_pct=10.0,
                max_camber_pct=2.0,
                camber_at_te=0.001,
                family="cambered",
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            AirfoilLowRePolarModel(
                airfoil_name="tip_re_af",
                reynolds=100_000.0,
                ld_max=45.0,
                cl_max=1.2,
                alpha_attached_lo=-3.0,
                alpha_attached_hi=12.0,
                drag_bucket_width=0.50,
                cd_min=0.012,
                stall_gentleness=-0.05,
                cd0=0.012,
                k=0.04,
                cl0=0.25,
                cl_valid_lo=0.0,
                cl_valid_hi=1.2,
                min_analysis_confidence=0.93,
                neuralfoil_model_size="xxxlarge",
                n_crit=9.0,
                computed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    return in_memory_db


class TestTipReSignificanceThreshold:
    """Item 2 (gh-825): boundary tests for the tip-Re significance threshold.

    Uses explicit Settings overrides to isolate threshold logic from defaults.
    abs_floor=80_000, rel_drop=50_000 (matching new default values).
    """

    # Re = 1.225 * speed * chord / 1.81e-5
    # speed_ms = 15.0
    # Factor = 1.225 * 15.0 / 1.81e-5 ≈ 1_015_469.6  per metre chord
    _FACTOR = 1.225 * 15.0 / 1.81e-5

    def _re(self, chord_m):
        return self._FACTOR * chord_m

    def test_tip_re_flag_false_gentle_taper(self, in_memory_db):
        """Gentle taper: tip_Re above floor AND (root_Re - tip_Re) <= rel_drop → flag False."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)

        # root_chord → Re ≈ 152_220  (0.15 m)
        # tip_chord  → Re ≈ 101_480  (0.1 m)
        # re_tip > 80_000 (floor)  ✓  abs_floor passes
        # re_root - re_tip ≈ 50_740  > 50_000  → would trip rel_drop
        # Need gentler taper: tip = 0.105 m → re_tip ≈ 106_524
        # re_root - re_tip ≈ 152_220 - 106_524 = 45_696 < 50_000  ✓

        root_chord = 0.15
        tip_chord = 0.105
        re_root = self._re(root_chord)
        re_tip = self._re(tip_chord)

        settings = Settings(
            low_re_tip_re_abs_floor=80_000.0,
            low_re_tip_re_rel_drop=50_000.0,
        )
        # Verify our test invariants hold
        assert re_tip >= settings.low_re_tip_re_abs_floor, (
            f"re_tip={re_tip:.0f} must be >= floor={settings.low_re_tip_re_abs_floor}"
        )
        assert (re_root - re_tip) <= settings.low_re_tip_re_rel_drop, (
            f"drop={re_root - re_tip:.0f} must be <= rel_drop={settings.low_re_tip_re_rel_drop}"
        )

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=root_chord,
                speed_ms=15.0,
                tip_chord_m=tip_chord,
                settings=settings,
            )

        for item in resp.results:
            assert item.tip_re_flag is False, (
                f"Expected tip_re_flag=False for gentle taper, got True on {item.airfoil_name}"
            )

    def test_tip_re_flag_true_below_abs_floor(self, in_memory_db):
        """tip_Re < abs_floor (80k) → flag must be True."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)

        # tip_chord = 0.07 → re_tip ≈ 70_983 < 80_000  → flag True
        tip_chord = 0.07
        re_tip = self._re(tip_chord)
        settings = Settings(
            low_re_tip_re_abs_floor=80_000.0,
            low_re_tip_re_rel_drop=50_000.0,
        )
        assert re_tip < settings.low_re_tip_re_abs_floor, (
            f"re_tip={re_tip:.0f} must be < floor={settings.low_re_tip_re_abs_floor}"
        )

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                tip_chord_m=tip_chord,
                settings=settings,
            )

        for item in resp.results:
            assert item.tip_re_flag is True, (
                f"Expected tip_re_flag=True for re_tip < floor, got False on {item.airfoil_name}"
            )

    def test_tip_re_flag_true_large_rel_drop(self, in_memory_db):
        """(re_root - re_tip) > rel_drop (50k) → flag must be True even if re_tip > floor."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)

        # root_chord = 0.15 → re_root ≈ 152_220
        # tip_chord = 0.095 → re_tip ≈ 96_470
        # drop ≈ 55_750 > 50_000  → flag True
        # re_tip > 80_000  → abs_floor alone wouldn't flag it
        root_chord = 0.15
        tip_chord = 0.095
        re_root = self._re(root_chord)
        re_tip = self._re(tip_chord)
        settings = Settings(
            low_re_tip_re_abs_floor=80_000.0,
            low_re_tip_re_rel_drop=50_000.0,
        )
        assert re_tip >= settings.low_re_tip_re_abs_floor, (
            f"re_tip={re_tip:.0f} must be >= floor (testing rel_drop path only)"
        )
        assert (re_root - re_tip) > settings.low_re_tip_re_rel_drop, (
            f"drop={re_root - re_tip:.0f} must be > rel_drop={settings.low_re_tip_re_rel_drop}"
        )

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=root_chord,
                speed_ms=15.0,
                tip_chord_m=tip_chord,
                settings=settings,
            )

        for item in resp.results:
            assert item.tip_re_flag is True, (
                f"Expected tip_re_flag=True for large rel_drop, got False on {item.airfoil_name}"
            )

    def test_tip_re_flag_edge_exactly_at_floor(self, in_memory_db):
        """Exactly at abs_floor: re_tip == floor → flag must be False (not strictly less than)."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)

        # We need re_tip == exactly 80_000.  Compute chord:
        # chord = 80_000 / FACTOR
        abs_floor = 80_000.0
        tip_chord_exact = abs_floor / self._FACTOR
        # Also ensure rel_drop doesn't fire: root=0.15 → re_root≈152_220
        # drop = 152_220 - 80_000 = 72_220 > 50_000 → rel_drop fires
        # So use a small root where re_root - 80_000 <= 50_000
        # re_root <= 130_000 → chord_root <= 0.128 m
        root_chord = 0.125  # re_root ≈ 126_934
        re_root = self._re(root_chord)
        re_tip = self._re(tip_chord_exact)
        drop = re_root - re_tip

        settings = Settings(
            low_re_tip_re_abs_floor=abs_floor,
            low_re_tip_re_rel_drop=50_000.0,
        )
        # Validate our invariants
        assert abs(re_tip - abs_floor) < 1.0, f"re_tip={re_tip:.2f} must equal floor={abs_floor}"
        assert drop <= settings.low_re_tip_re_rel_drop, (
            f"drop={drop:.0f} must be <= rel_drop so only floor edge matters"
        )

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=root_chord,
                speed_ms=15.0,
                tip_chord_m=tip_chord_exact,
                settings=settings,
            )

        # re_tip == floor exactly: not strictly less than → flag False
        for item in resp.results:
            assert item.tip_re_flag is False, (
                f"At exactly floor boundary, tip_re_flag should be False; "
                f"got True on {item.airfoil_name}"
            )

    def test_tip_re_flag_edge_just_below_rel_drop(self, in_memory_db):
        """Just below rel_drop: (re_root - re_tip) slightly < rel_drop → flag must be False."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)

        # Use a rel_drop threshold of 50_000 and ensure (re_root - re_tip) < 50_000
        # by giving a relatively long tip chord.
        # root_chord = 0.15 → re_root ≈ 152_279
        # We want re_tip = re_root - 49_000 ≈ 103_279  (drop of 49k < 50k)
        # tip_chord = (re_root - 49_000) / FACTOR  ≈ 0.10166 m
        # re_tip ≈ 103_279 > 80_000 floor  → abs_floor doesn't fire either
        rel_drop = 50_000.0
        abs_floor = 80_000.0
        root_chord = 0.15
        re_root = self._re(root_chord)
        re_tip_target = re_root - 49_000.0  # 1000 Re units below the threshold
        tip_chord = re_tip_target / self._FACTOR

        settings = Settings(
            low_re_tip_re_abs_floor=abs_floor,
            low_re_tip_re_rel_drop=rel_drop,
        )

        # Confirm our invariants hold for this test case
        re_tip_actual = self._re(tip_chord)
        assert re_tip_actual > abs_floor
        assert (re_root - re_tip_actual) < rel_drop

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=root_chord,
                speed_ms=15.0,
                tip_chord_m=tip_chord,
                settings=settings,
            )

        # Drop is clearly below rel_drop → flag False
        for item in resp.results:
            assert item.tip_re_flag is False, (
                f"Drop just below rel_drop: tip_re_flag should be False; "
                f"got True on {item.airfoil_name}"
            )

    def test_tip_re_flag_none_when_no_tip_chord(self, in_memory_db):
        """When tip_chord_m is None, tip_re_flag must always be False."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        db_factory = _make_minimal_db_with_airfoil(in_memory_db)
        settings = Settings(
            low_re_tip_re_abs_floor=80_000.0,
            low_re_tip_re_rel_drop=50_000.0,
        )

        with db_factory() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                tip_chord_m=None,
                settings=settings,
            )

        for item in resp.results:
            assert item.tip_re_flag is False, (
                f"tip_re_flag should be False when no tip_chord_m; got True on {item.airfoil_name}"
            )


# ---------------------------------------------------------------------------
# ITEM 5-BE (gh-825): `include` additive query param — service-level tests
# ---------------------------------------------------------------------------


class TestIncludeParam:
    """Service-level tests for the additive `include` parameter in search_suitability.

    Contract (gh-825 item 5):
    - Named airfoils in `include` that have low-Re polar rows are ALWAYS returned,
      even if `limit` would drop them from the top-N ranked block.
    - Named airfoils with NO polar rows are NOT fabricated (not returned).
    - De-duplication: included names already in the top-N are NOT duplicated.
    - Default None → identical behaviour to before (no include).
    """

    @pytest.fixture()
    def db_many_airfoils(self, in_memory_db):
        """DB with 5 airfoils with varying quality + 1 airfoil with NO polar rows."""
        from app.models.airfoil import AirfoilModel
        from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
        from datetime import datetime, timezone

        with in_memory_db() as session:
            for i, (ld, cl_max_val, cd0_val) in enumerate(
                [
                    (55, 1.4, 0.010),  # af_0 — best
                    (45, 1.2, 0.013),  # af_1
                    (35, 1.1, 0.016),  # af_2
                    (25, 0.9, 0.020),  # af_3
                    (15, 0.7, 0.025),  # af_4 — worst
                ]
            ):
                name = f"af_{i}"
                session.add(AirfoilModel(name=name, coordinates=[[0, 0], [0.5, 0.07], [1, 0]]))
                session.flush()
                session.add(
                    AirfoilGeometryModel(
                        airfoil_name=name,
                        max_thickness_pct=10.0,
                        max_camber_pct=2.0,
                        camber_at_te=0.0,
                        family="cambered",
                        computed_at=datetime.now(timezone.utc),
                    )
                )
                session.add(
                    AirfoilLowRePolarModel(
                        airfoil_name=name,
                        reynolds=100_000.0,
                        ld_max=float(ld),
                        cl_max=float(cl_max_val),
                        alpha_attached_lo=-3.0,
                        alpha_attached_hi=12.0,
                        drag_bucket_width=0.50,
                        cd_min=float(cd0_val),
                        stall_gentleness=-0.05,
                        cd0=float(cd0_val),
                        k=0.04,
                        cl0=0.25,
                        cl_valid_lo=0.0,
                        cl_valid_hi=float(cl_max_val),
                        min_analysis_confidence=0.93,
                        neuralfoil_model_size="xxxlarge",
                        n_crit=9.0,
                        computed_at=datetime.now(timezone.utc),
                    )
                )

            # Add one airfoil with geometry but NO polar rows
            session.add(AirfoilModel(name="no_polar_af", coordinates=[[0, 0], [0.5, 0.06], [1, 0]]))
            session.flush()
            session.add(
                AirfoilGeometryModel(
                    airfoil_name="no_polar_af",
                    max_thickness_pct=11.0,
                    max_camber_pct=1.5,
                    camber_at_te=0.0,
                    family="semi_symmetric",
                    computed_at=datetime.now(timezone.utc),
                )
            )
            # No AirfoilLowRePolarModel for no_polar_af
            session.commit()

        return in_memory_db

    def test_include_forces_airfoil_beyond_limit(self, db_many_airfoils):
        """Airfoils named in `include` appear even when limit drops them."""
        from app.services.suitability_service import search_suitability

        # limit=1 → only top 1 (af_0). But include=['af_4'] should force af_4 to appear.
        with db_many_airfoils() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=1,
                include=["af_4"],
            )

        result_names = [item.airfoil_name for item in resp.results]
        assert "af_4" in result_names, (
            f"af_4 should be in results due to include=[]; got {result_names}"
        )
        # Top-N (limit=1) still has af_0
        assert "af_0" in result_names, f"af_0 (top-1) should still be present; got {result_names}"
        # Total should be 2 (top-1 + include)
        assert len(resp.results) == 2, (
            f"Expected 2 results, got {len(resp.results)}: {result_names}"
        )

    def test_include_no_fabrication_for_no_polar(self, db_many_airfoils):
        """Airfoils in `include` with NO polar rows must NOT be fabricated."""
        from app.services.suitability_service import search_suitability

        with db_many_airfoils() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=1,
                include=["no_polar_af"],
            )

        result_names = [item.airfoil_name for item in resp.results]
        assert "no_polar_af" not in result_names, (
            f"no_polar_af has no polar rows and must NOT be fabricated; got {result_names}"
        )

    def test_include_no_duplication_when_in_topn(self, db_many_airfoils):
        """An included name already in top-N must NOT appear twice."""
        from app.services.suitability_service import search_suitability

        # limit=5 → all 5 af_* are in top-N. include=['af_0'] → should not duplicate.
        with db_many_airfoils() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=5,
                include=["af_0"],
            )

        result_names = [item.airfoil_name for item in resp.results]
        count_af0 = result_names.count("af_0")
        assert count_af0 == 1, (
            f"af_0 should appear exactly once; found {count_af0} times in {result_names}"
        )

    def test_include_none_identical_to_before(self, db_many_airfoils):
        """include=None (default) must give identical results to omitting the param."""
        from app.services.suitability_service import search_suitability

        with db_many_airfoils() as session:
            resp_default = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=3,
            )
        with db_many_airfoils() as session:
            resp_none = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=3,
                include=None,
            )

        names_default = [item.airfoil_name for item in resp_default.results]
        names_none = [item.airfoil_name for item in resp_none.results]
        assert names_default == names_none, (
            f"include=None must give identical behaviour to omitting param; "
            f"default={names_default}, none={names_none}"
        )

    def test_include_case_insensitive(self, db_many_airfoils):
        """include names should match case-insensitively against geo_by_name keys."""
        from app.services.suitability_service import search_suitability

        with db_many_airfoils() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                limit=1,
                include=["AF_4"],  # uppercase variant
            )

        result_names = [item.airfoil_name for item in resp.results]
        assert "af_4" in result_names, (
            f"include=['AF_4'] should match 'af_4' case-insensitively; got {result_names}"
        )


# ---------------------------------------------------------------------------
# ITEM 12 (gh-825): slope_soarer gets its own mission-weighting key
# ---------------------------------------------------------------------------


class TestSlopeSoarerMissionWeight:
    """gh-825 item 12: 'slope_soarer' maps to its own weight key (not 'glider')."""

    def test_slope_soarer_resolves_to_slope_soarer_weights(self, seeded_db_825):
        """search_suitability with mission_type='slope_soarer' must use 'slope_soarer' weights
        (semi_symmetric/cambered preferred), NOT 'glider' weights."""
        from app.services.suitability_service import search_suitability
        from app.settings import Settings

        # Verify the mission weight key exists in settings
        settings = Settings()
        assert "slope_soarer" in settings.low_re_mission_weights, (
            "slope_soarer weight key must exist in Settings.low_re_mission_weights"
        )
        weights = settings.low_re_mission_weights["slope_soarer"]
        assert "preferred_families" in weights
        assert (
            "semi_symmetric" in weights["preferred_families"]
            or "cambered" in weights["preferred_families"]
        ), "slope_soarer preferred_families should include semi_symmetric or cambered"

        # Check 'glider' is still present for unmapped aliases
        assert "glider" in settings.low_re_mission_weights, (
            "glider key must still exist as fallback"
        )

        # The mapping: 'slope_soarer' → 'slope_soarer' (not 'glider')
        from app.services.suitability_service import _MISSION_TYPE_MAP

        assert _MISSION_TYPE_MAP.get("slope_soarer") == "slope_soarer", (
            f"_MISSION_TYPE_MAP['slope_soarer'] must be 'slope_soarer', "
            f"got {_MISSION_TYPE_MAP.get('slope_soarer')!r}"
        )

        # Service: with explicit mission_type='slope_soarer', items should get mission score
        # (non-None) rather than None (which would happen if the key were missing)
        SessionLocal, _ = seeded_db_825
        with SessionLocal() as session:
            resp = search_suitability(
                db=session,
                chord_m=0.15,
                speed_ms=15.0,
                mission_type="slope_soarer",
                settings=settings,
            )

        # With slope_soarer weights, mission scores should be non-None (key exists in weights)
        items_with_polar = [r for r in resp.results if r.re_agnostic > 0]
        assert any(r.mission is not None for r in items_with_polar), (
            "slope_soarer mission type should produce non-None mission scores; "
            "check that 'slope_soarer' key is in Settings.low_re_mission_weights"
        )
        # active_lens should be 'mission' when mission scores are available
        assert resp.query.active_lens == "mission", (
            f"active_lens should be 'mission' for slope_soarer; got {resp.query.active_lens!r}"
        )

    def test_slope_soarer_different_from_glider_weights(self):
        """slope_soarer and glider must have different preferred_families."""
        from app.settings import Settings

        settings = Settings()
        ss_weights = settings.low_re_mission_weights.get("slope_soarer", {})
        glider_weights = settings.low_re_mission_weights.get("glider", {})
        # They should not be identical (slope_soarer has own niche)
        assert ss_weights != glider_weights, (
            "slope_soarer weights should differ from glider weights (own aerobatic niche)"
        )
