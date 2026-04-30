"""Tests for AvlGeometryFileModel — TDD red → green cycle for Task 1 (gh-381).

The top-level import of AvlGeometryFileModel is required so that the table is
registered with Base.metadata before the client_and_db fixture calls
Base.metadata.create_all().
"""

from __future__ import annotations

import uuid

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


# ── Schema Tests ──────────────────────────────────────────────────────────────


from app.schemas.avl_geometry import AvlGeometryResponse, AvlGeometryUpdateRequest


class TestAvlGeometrySchemas:
    def test_response_schema(self):
        resp = AvlGeometryResponse(
            content="SURFACE\nWing\n",
            is_dirty=False,
            is_user_edited=True,
        )
        assert resp.content == "SURFACE\nWing\n"
        assert resp.is_dirty is False
        assert resp.is_user_edited is True

    def test_update_request_schema(self):
        req = AvlGeometryUpdateRequest(content="SURFACE\nWing\nSECTION\n")
        assert req.content == "SURFACE\nWing\nSECTION\n"

    def test_update_request_empty_content_rejected(self):
        with pytest.raises(Exception):
            AvlGeometryUpdateRequest(content="")


# ── Service Tests ─────────────────────────────────────────────────────────────


from unittest.mock import patch

from app.services.avl_geometry_service import (
    delete_avl_geometry,
    generate_avl_content,
    get_avl_geometry,
    regenerate_avl_geometry,
    save_avl_geometry,
)
from app.core.exceptions import NotFoundError


class TestAvlGeometryService:
    def test_get_avl_geometry_no_saved_file_generates(self, db: Session):
        """When no saved file exists, generate content on the fly."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="GENERATED\nCONTENT\n",
        ):
            result = get_avl_geometry(db, aeroplane.uuid)

        assert result.content == "GENERATED\nCONTENT\n"
        assert result.is_user_edited is False
        assert result.is_dirty is False

    def test_get_avl_geometry_returns_saved(self, db: Session):
        """When a saved file exists, return it."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="USER CONTENT",
            is_user_edited=True,
        )
        db.add(geom)
        db.flush()

        result = get_avl_geometry(db, aeroplane.uuid)
        assert result.content == "USER CONTENT"
        assert result.is_user_edited is True

    def test_save_avl_geometry_creates_new(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        result = save_avl_geometry(db, aeroplane.uuid, "NEW CONTENT")
        assert result.content == "NEW CONTENT"
        assert result.is_user_edited is True
        assert result.is_dirty is False

    def test_save_avl_geometry_updates_existing(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="OLD",
            is_dirty=True,
        )
        db.add(geom)
        db.flush()

        result = save_avl_geometry(db, aeroplane.uuid, "UPDATED")
        assert result.content == "UPDATED"
        assert result.is_dirty is False
        assert result.is_user_edited is True

    def test_regenerate_returns_fresh_content(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="FRESH\nGENERATED\n",
        ):
            result = regenerate_avl_geometry(db, aeroplane.uuid)

        assert result.content == "FRESH\nGENERATED\n"
        assert result.is_user_edited is False

    def test_delete_avl_geometry(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="DATA")
        db.add(geom)
        db.flush()

        delete_avl_geometry(db, aeroplane.uuid)
        assert (
            db.query(AvlGeometryFileModel)
            .filter_by(aeroplane_id=aeroplane.id)
            .first()
            is None
        )

    def test_delete_avl_geometry_not_found(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with pytest.raises(NotFoundError):
            delete_avl_geometry(db, aeroplane.uuid)

    def test_get_avl_geometry_aeroplane_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_avl_geometry(db, uuid.uuid4())


# ── Dirty Flag Event Hook Tests ───────────────────────────────────────────────


from app.models.aeroplanemodel import WingModel, WingXSecModel, FuselageModel
import app.models.avl_geometry_events  # noqa: F401 — registers event listeners


class TestAvlGeometryDirtyFlag:
    def test_wing_insert_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_wing_update_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        wing.name = "Updated Wing"
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_wing_delete_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        db.delete(wing)
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_no_geom_file_no_error(self, db: Session):
        """Event fires but no geometry file exists — should be a no-op."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()  # Should not raise
