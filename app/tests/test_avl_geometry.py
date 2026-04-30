"""Tests for AvlGeometryFileModel — TDD red → green cycle for Task 1 (gh-381).

The top-level import of AvlGeometryFileModel is required so that the table is
registered with Base.metadata before the client_and_db fixture calls
Base.metadata.create_all().
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.models.avl_geometry_file import AvlGeometryFileModel


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def db(client_and_db):
    """Provide a raw SQLAlchemy session from the client_and_db fixture."""
    _, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestAvlGeometryFileModel:
    def test_create_avl_geometry_file(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="SURFACE\nWing\n",
        )
        db.add(geom)
        db.flush()

        assert geom.id is not None
        assert geom.content == "SURFACE\nWing\n"
        assert geom.is_dirty is False
        assert geom.is_user_edited is False
        assert geom.created_at is not None
        assert geom.updated_at is not None

    def test_unique_aeroplane_constraint(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom1 = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="v1")
        db.add(geom1)
        db.flush()

        geom2 = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="v2")
        db.add(geom2)
        with pytest.raises(Exception):
            db.flush()

    def test_cascade_delete(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="data")
        db.add(geom)
        db.flush()
        geom_id = geom.id

        db.delete(aeroplane)
        db.flush()

        assert db.get(AvlGeometryFileModel, geom_id) is None
