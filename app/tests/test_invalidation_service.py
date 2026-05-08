"""Tests for app/services/invalidation_service.py — marks OPs as DIRTY."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import AssumptionChanged, GeometryChanged, event_bus
from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.services.invalidation_service import mark_ops_dirty, register_handlers


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


def _make_op(session: Session, aircraft_id: int, status: str = "TRIMMED") -> OperatingPointModel:
    op = OperatingPointModel(
        name="op_test",
        description="test op",
        aircraft_id=aircraft_id,
        velocity=20.0,
        alpha=0.05,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        altitude=100.0,
        config="clean",
        status=status,
        warnings=[],
        controls={},
        xyz_ref=[0.0, 0.0, 0.0],
    )
    session.add(op)
    session.commit()
    session.refresh(op)
    return op


class TestMarkOpsDirty:
    """Test mark_ops_dirty() function directly."""

    def test_marks_trimmed_to_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="TRIMMED")

        count = mark_ops_dirty(db_session, a.id)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"
        assert count == 1

    def test_marks_not_trimmed_to_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="NOT_TRIMMED")

        count = mark_ops_dirty(db_session, a.id)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"
        assert count == 1

    def test_marks_limit_reached_to_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="LIMIT_REACHED")

        count = mark_ops_dirty(db_session, a.id)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"
        assert count == 1

    def test_does_not_change_computing_status(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="COMPUTING")

        count = mark_ops_dirty(db_session, a.id)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "COMPUTING"
        assert count == 0

    def test_does_not_change_already_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="DIRTY")

        count = mark_ops_dirty(db_session, a.id)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"
        assert count == 0

    def test_returns_correct_rowcount(self, db_session):
        a = _make_aeroplane(db_session)
        _make_op(db_session, a.id, status="TRIMMED")
        _make_op(db_session, a.id, status="NOT_TRIMMED")
        _make_op(db_session, a.id, status="COMPUTING")
        _make_op(db_session, a.id, status="DIRTY")

        count = mark_ops_dirty(db_session, a.id)
        # Only TRIMMED and NOT_TRIMMED should be updated
        assert count == 2

    def test_only_affects_target_aeroplane(self, db_session):
        a1 = _make_aeroplane(db_session)
        a2 = _make_aeroplane(db_session)
        op1 = _make_op(db_session, a1.id, status="TRIMMED")
        op2 = _make_op(db_session, a2.id, status="TRIMMED")

        mark_ops_dirty(db_session, a1.id)
        db_session.commit()

        db_session.refresh(op1)
        db_session.refresh(op2)
        assert op1.status == "DIRTY"
        assert op2.status == "TRIMMED"


class TestRegisterHandlers:
    """Test that register_handlers() wires up event bus subscriptions."""

    def test_registers_geometry_and_assumption_handlers(self):
        # Clear event bus before test
        event_bus.clear()
        register_handlers()

        # Verify handlers are registered by checking subscriber counts
        geo_handlers = event_bus._subscribers.get(GeometryChanged, [])
        assumption_handlers = event_bus._subscribers.get(AssumptionChanged, [])
        assert len(geo_handlers) >= 1
        assert len(assumption_handlers) >= 1

        # Clean up
        event_bus.clear()
