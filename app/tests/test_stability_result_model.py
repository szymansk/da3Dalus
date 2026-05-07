"""Tests for StabilityResultModel: creation, upsert, cascade delete, relationship."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.stability_result import StabilityResultModel


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


def _make_aeroplane(session: Session, name: str = "test") -> AeroplaneModel:
    a = AeroplaneModel(name=name, uuid=uuid.uuid4())
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _make_result(session: Session, aeroplane_id: int, solver: str = "avl", **kwargs) -> StabilityResultModel:
    defaults = {
        "neutral_point_x": 0.12,
        "mac": 0.25,
        "cg_x_used": 0.08,
        "static_margin_pct": 16.0,
        "stability_class": "stable",
        "is_statically_stable": True,
        "is_directionally_stable": True,
        "is_laterally_stable": True,
        "status": "CURRENT",
    }
    defaults.update(kwargs)
    row = StabilityResultModel(aeroplane_id=aeroplane_id, solver=solver, **defaults)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class TestStabilityResultModel:

    def test_create_and_query(self, db_session):
        a = _make_aeroplane(db_session)
        row = _make_result(db_session, a.id)
        assert row.id is not None
        assert row.neutral_point_x == pytest.approx(0.12)
        assert row.stability_class == "stable"
        assert row.status == "CURRENT"

    def test_unique_constraint_aeroplane_solver(self, db_session):
        a = _make_aeroplane(db_session)
        _make_result(db_session, a.id, solver="avl")
        with pytest.raises(IntegrityError):
            _make_result(db_session, a.id, solver="avl")

    def test_different_solvers_allowed(self, db_session):
        a = _make_aeroplane(db_session)
        r1 = _make_result(db_session, a.id, solver="avl")
        r2 = _make_result(db_session, a.id, solver="aerobuildup")
        assert r1.id != r2.id

    def test_cascade_delete(self, db_session):
        a = _make_aeroplane(db_session)
        _make_result(db_session, a.id, solver="avl")
        _make_result(db_session, a.id, solver="vlm")
        db_session.delete(a)
        db_session.commit()
        count = db_session.query(StabilityResultModel).count()
        assert count == 0

    def test_relationship_from_aeroplane(self, db_session):
        a = _make_aeroplane(db_session)
        _make_result(db_session, a.id, solver="avl")
        db_session.refresh(a)
        assert len(a.stability_results) == 1
        assert a.stability_results[0].solver == "avl"

    def test_nullable_fields(self, db_session):
        a = _make_aeroplane(db_session)
        row = StabilityResultModel(
            aeroplane_id=a.id,
            solver="vlm",
            is_statically_stable=False,
            is_directionally_stable=False,
            is_laterally_stable=False,
            status="CURRENT",
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        assert row.neutral_point_x is None
        assert row.mac is None
        assert row.Cma is None
        assert row.geometry_hash is None

    def test_computed_at_auto_set(self, db_session):
        a = _make_aeroplane(db_session)
        row = _make_result(db_session, a.id)
        assert row.computed_at is not None
