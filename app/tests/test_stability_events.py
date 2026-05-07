"""Tests for stability_events — geometry change marks stability results DIRTY."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel, WingModel, WingXSecModel, FuselageModel
from app.models.stability_result import StabilityResultModel
import app.models.stability_events  # noqa: F401 — registers event listeners


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


def _seed_stability_result(session: Session, aeroplane_id: int, solver: str = "avl") -> StabilityResultModel:
    row = StabilityResultModel(
        aeroplane_id=aeroplane_id,
        solver=solver,
        neutral_point_x=0.12,
        status="CURRENT",
        is_statically_stable=True,
        is_directionally_stable=True,
        is_laterally_stable=True,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class TestStabilityEventsWing:

    def test_wing_insert_marks_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        _seed_stability_result(db_session, a.id)
        wing = WingModel(name="new_wing", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()
        row = db_session.query(StabilityResultModel).first()
        assert row.status == "DIRTY"

    def test_wing_update_marks_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        wing = WingModel(name="w1", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()
        _seed_stability_result(db_session, a.id)
        wing.name = "w1_modified"
        db_session.commit()
        row = db_session.query(StabilityResultModel).first()
        assert row.status == "DIRTY"

    def test_wing_delete_marks_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        wing = WingModel(name="w1", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()
        _seed_stability_result(db_session, a.id)
        db_session.delete(wing)
        db_session.commit()
        row = db_session.query(StabilityResultModel).first()
        assert row.status == "DIRTY"


class TestStabilityEventsFuselage:

    def test_fuselage_update_marks_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        fus = FuselageModel(name="f1", aeroplane_id=a.id)
        db_session.add(fus)
        db_session.commit()
        _seed_stability_result(db_session, a.id)
        fus.name = "f1_modified"
        db_session.commit()
        row = db_session.query(StabilityResultModel).first()
        assert row.status == "DIRTY"


class TestStabilityEventsNoOp:

    def test_no_crash_when_no_stability_results(self, db_session):
        a = _make_aeroplane(db_session)
        wing = WingModel(name="w1", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()
        count = db_session.query(StabilityResultModel).count()
        assert count == 0
