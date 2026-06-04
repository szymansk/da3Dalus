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
