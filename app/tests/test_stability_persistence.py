"""Tests for stability service persistence helpers."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.stability_result import StabilityResultModel
from app.schemas.stability import StabilitySummaryResponse
from app.services.stability_service import (
    get_cached_stability,
    mark_stability_dirty,
    persist_stability_result,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_aeroplane(session: Session) -> AeroplaneModel:
    a = AeroplaneModel(name="test", uuid=uuid.uuid4())
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _make_summary(**overrides) -> StabilitySummaryResponse:
    defaults = {
        "static_margin": 0.16,
        "neutral_point_x": 0.12,
        "cg_x": 0.08,
        "Cma": -0.8,
        "Cnb": 0.05,
        "Clb": -0.03,
        "is_statically_stable": True,
        "is_directionally_stable": True,
        "is_laterally_stable": True,
        "analysis_method": "avl",
        "static_margin_pct": 16.0,
        "stability_class": "stable",
        "cg_range_forward": 0.0375,
        "cg_range_aft": 0.1075,
        "mac": 0.25,
        "trim_alpha_deg": 2.0,
        "trim_elevator_deg": -1.5,
    }
    defaults.update(overrides)
    return StabilitySummaryResponse(**defaults)


class TestPersistStabilityResult:

    def test_creates_new_row(self, db_session):
        a = _make_aeroplane(db_session)
        summary = _make_summary()
        persist_stability_result(db_session, a.id, "avl", summary, "abc123")
        db_session.commit()
        row = db_session.query(StabilityResultModel).first()
        assert row is not None
        assert row.solver == "avl"
        assert row.neutral_point_x == pytest.approx(0.12)
        assert row.status == "CURRENT"
        assert row.geometry_hash == "abc123"

    def test_upserts_existing_row(self, db_session):
        a = _make_aeroplane(db_session)
        persist_stability_result(db_session, a.id, "avl", _make_summary(), "hash1")
        db_session.commit()
        persist_stability_result(
            db_session, a.id, "avl",
            _make_summary(neutral_point_x=0.15, static_margin_pct=20.0),
            "hash2",
        )
        db_session.commit()
        count = db_session.query(StabilityResultModel).filter_by(
            aeroplane_id=a.id, solver="avl"
        ).count()
        assert count == 1
        row = db_session.query(StabilityResultModel).first()
        assert row.neutral_point_x == pytest.approx(0.15)
        assert row.geometry_hash == "hash2"

    def test_different_solvers_create_separate_rows(self, db_session):
        a = _make_aeroplane(db_session)
        persist_stability_result(db_session, a.id, "avl", _make_summary(), None)
        persist_stability_result(db_session, a.id, "aerobuildup", _make_summary(), None)
        db_session.commit()
        count = db_session.query(StabilityResultModel).filter_by(aeroplane_id=a.id).count()
        assert count == 2


class TestGetCachedStability:

    def test_returns_none_when_empty(self, db_session):
        a = _make_aeroplane(db_session)
        result = get_cached_stability(db_session, a.id)
        assert result is None

    def test_returns_result(self, db_session):
        a = _make_aeroplane(db_session)
        persist_stability_result(db_session, a.id, "avl", _make_summary(), "h1")
        db_session.commit()
        result = get_cached_stability(db_session, a.id)
        assert result is not None
        assert result.solver == "avl"
        assert result.neutral_point_x == pytest.approx(0.12)

    def test_prefers_current_over_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        persist_stability_result(db_session, a.id, "avl", _make_summary(), "h1")
        persist_stability_result(
            db_session, a.id, "aerobuildup",
            _make_summary(neutral_point_x=0.15),
            "h2",
        )
        db_session.commit()
        db_session.execute(
            StabilityResultModel.__table__.update()
            .where(StabilityResultModel.solver == "avl")
            .values(status="DIRTY")
        )
        db_session.commit()
        result = get_cached_stability(db_session, a.id)
        assert result.solver == "aerobuildup"
        assert result.status == "CURRENT"


class TestMarkStabilityDirty:

    def test_marks_all_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        persist_stability_result(db_session, a.id, "avl", _make_summary(), None)
        persist_stability_result(db_session, a.id, "vlm", _make_summary(), None)
        db_session.commit()
        mark_stability_dirty(db_session, a.id)
        db_session.commit()
        rows = db_session.query(StabilityResultModel).filter_by(aeroplane_id=a.id).all()
        assert all(r.status == "DIRTY" for r in rows)

    def test_no_crash_when_no_results(self, db_session):
        a = _make_aeroplane(db_session)
        mark_stability_dirty(db_session, a.id)
        db_session.commit()

    def test_only_affects_target_aeroplane(self, db_session):
        a1 = _make_aeroplane(db_session)
        a2 = AeroplaneModel(name="other", uuid=uuid.uuid4())
        db_session.add(a2)
        db_session.commit()
        db_session.refresh(a2)
        persist_stability_result(db_session, a1.id, "avl", _make_summary(), None)
        persist_stability_result(db_session, a2.id, "avl", _make_summary(), None)
        db_session.commit()
        mark_stability_dirty(db_session, a1.id)
        db_session.commit()
        r1 = db_session.query(StabilityResultModel).filter_by(aeroplane_id=a1.id).first()
        r2 = db_session.query(StabilityResultModel).filter_by(aeroplane_id=a2.id).first()
        assert r1.status == "DIRTY"
        assert r2.status == "CURRENT"
