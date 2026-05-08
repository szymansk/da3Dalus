"""Integration tests: geometry changes mark operating points as DIRTY.

Tests that the SQLAlchemy event listeners in avl_geometry_events.py and
stability_events.py correctly cascade OP dirty-flagging when wing/fuselage
geometry changes.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import GeometryChanged, event_bus
from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel, FuselageModel, WingModel
from app.models.analysismodels import OperatingPointModel
import app.models.avl_geometry_events  # noqa: F401 — registers event listeners
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


class TestWingChangeMarksOpsDirty:
    """Creating/updating/deleting a wing marks OPs as DIRTY."""

    def test_wing_insert_marks_ops_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        op = _make_op(db_session, a.id, status="TRIMMED")

        wing = WingModel(name="new_wing", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"

    def test_wing_update_marks_ops_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        wing = WingModel(name="w1", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()

        op = _make_op(db_session, a.id, status="TRIMMED")

        wing.name = "w1_modified"
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"

    def test_wing_delete_marks_ops_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        wing = WingModel(name="w1", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()

        op = _make_op(db_session, a.id, status="TRIMMED")

        db_session.delete(wing)
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"

    def test_does_not_mark_computing_ops(self, db_session):
        a = _make_aeroplane(db_session)
        op_computing = _make_op(db_session, a.id, status="COMPUTING")

        wing = WingModel(name="new_wing", aeroplane_id=a.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()

        db_session.refresh(op_computing)
        assert op_computing.status == "COMPUTING"


class TestFuselageChangeMarksOpsDirty:
    """Creating/updating/deleting a fuselage marks OPs as DIRTY."""

    def test_fuselage_update_marks_ops_dirty(self, db_session):
        a = _make_aeroplane(db_session)
        fus = FuselageModel(name="f1", aeroplane_id=a.id)
        db_session.add(fus)
        db_session.commit()

        op = _make_op(db_session, a.id, status="TRIMMED")

        fus.name = "f1_modified"
        db_session.commit()

        db_session.refresh(op)
        assert op.status == "DIRTY"


class TestGeometryEventsPublished:
    """Test that GeometryChanged events are published on geometry changes."""

    def test_geometry_changed_event_published_on_wing_insert(self, db_session):
        received = []
        event_bus.subscribe(GeometryChanged, lambda e: received.append(e))

        try:
            a = _make_aeroplane(db_session)
            _make_op(db_session, a.id, status="TRIMMED")

            wing = WingModel(name="new_wing", aeroplane_id=a.id, symmetric=True)
            db_session.add(wing)
            db_session.commit()

            # At least one GeometryChanged event should have been published
            geo_events = [e for e in received if e.aeroplane_id == a.id]
            assert len(geo_events) >= 1
        finally:
            event_bus.clear()


class TestOnlyTargetAeroplaneAffected:
    """Geometry changes only affect OPs for the same aeroplane."""

    def test_other_aeroplane_ops_unaffected(self, db_session):
        a1 = _make_aeroplane(db_session)
        a2 = _make_aeroplane(db_session)
        op1 = _make_op(db_session, a1.id, status="TRIMMED")
        op2 = _make_op(db_session, a2.id, status="TRIMMED")

        wing = WingModel(name="new_wing", aeroplane_id=a1.id, symmetric=True)
        db_session.add(wing)
        db_session.commit()

        db_session.refresh(op1)
        db_session.refresh(op2)
        assert op1.status == "DIRTY"
        assert op2.status == "TRIMMED"
