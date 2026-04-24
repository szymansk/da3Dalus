"""Tests for app.services.weight_items_service — per-aeroplane weight inventory CRUD."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import patch

from app.core.exceptions import InternalError, NotFoundError
from app.schemas.weight_item import WeightItemWrite
from app.services import weight_items_service as svc
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    name: str = "battery",
    mass_kg: float = 0.5,
    x_m: float = 0.1,
    y_m: float = 0.0,
    z_m: float = 0.0,
    description: str | None = None,
    category: str = "battery",
) -> WeightItemWrite:
    return WeightItemWrite(
        name=name,
        mass_kg=mass_kg,
        x_m=x_m,
        y_m=y_m,
        z_m=z_m,
        description=description,
        category=category,
    )


# ---------------------------------------------------------------------------
# _get_aeroplane
# ---------------------------------------------------------------------------

class TestGetAeroplane:
    def test_raises_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc._get_aeroplane(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# list_weight_items
# ---------------------------------------------------------------------------

class TestListWeightItems:
    def test_empty_list_for_new_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.list_weight_items(db, aeroplane.uuid)
            assert summary.items == []
            assert summary.total_mass_kg == 0.0

    def test_returns_items_and_total(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.create_weight_item(db, aeroplane.uuid, _make_item(name="a", mass_kg=1.5))
            svc.create_weight_item(db, aeroplane.uuid, _make_item(name="b", mass_kg=2.5))

            summary = svc.list_weight_items(db, aeroplane.uuid)
            assert len(summary.items) == 2
            assert summary.total_mass_kg == 4.0

    def test_total_mass_rounding(self, client_and_db):
        """Total is rounded to 6 decimal places."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.create_weight_item(db, aeroplane.uuid, _make_item(name="x", mass_kg=0.1))
            svc.create_weight_item(db, aeroplane.uuid, _make_item(name="y", mass_kg=0.2))

            summary = svc.list_weight_items(db, aeroplane.uuid)
            # 0.1 + 0.2 can have floating point imprecision; service rounds to 6
            assert summary.total_mass_kg == round(0.1 + 0.2, 6)

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.list_weight_items(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# create_weight_item
# ---------------------------------------------------------------------------

class TestCreateWeightItem:
    def test_create_minimal(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            item = svc.create_weight_item(db, aeroplane.uuid, _make_item())
            assert item.id is not None
            assert item.name == "battery"
            assert item.mass_kg == 0.5
            assert item.category == "battery"

    def test_create_with_all_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            item = svc.create_weight_item(
                db, aeroplane.uuid,
                _make_item(
                    name="motor",
                    mass_kg=0.3,
                    x_m=0.05,
                    y_m=0.01,
                    z_m=-0.02,
                    description="Brushless 2208",
                    category="electronics",
                ),
            )
            assert item.name == "motor"
            assert item.x_m == 0.05
            assert item.y_m == 0.01
            assert item.z_m == -0.02
            assert item.description == "Brushless 2208"
            assert item.category == "electronics"

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.create_weight_item(db, uuid.uuid4(), _make_item())

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.create_weight_item(db, aeroplane.uuid, _make_item())


# ---------------------------------------------------------------------------
# get_weight_item
# ---------------------------------------------------------------------------

class TestGetWeightItem:
    def test_get_existing_item(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = svc.create_weight_item(db, aeroplane.uuid, _make_item(name="esc"))
            fetched = svc.get_weight_item(db, aeroplane.uuid, created.id)
            assert fetched.id == created.id
            assert fetched.name == "esc"

    def test_raises_not_found_for_missing_item(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.get_weight_item(db, aeroplane.uuid, 99999)

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.get_weight_item(db, uuid.uuid4(), 1)


# ---------------------------------------------------------------------------
# update_weight_item
# ---------------------------------------------------------------------------

class TestUpdateWeightItem:
    def test_update_all_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = svc.create_weight_item(db, aeroplane.uuid, _make_item())
            updated = svc.update_weight_item(
                db, aeroplane.uuid, created.id,
                _make_item(
                    name="updated-batt",
                    mass_kg=0.8,
                    x_m=0.2,
                    y_m=0.3,
                    z_m=0.4,
                    description="new desc",
                    category="payload",
                ),
            )
            assert updated.name == "updated-batt"
            assert updated.mass_kg == 0.8
            assert updated.x_m == 0.2
            assert updated.y_m == 0.3
            assert updated.z_m == 0.4
            assert updated.description == "new desc"
            assert updated.category == "payload"

    def test_raises_not_found_for_missing_item(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.update_weight_item(db, aeroplane.uuid, 99999, _make_item())

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.update_weight_item(db, uuid.uuid4(), 1, _make_item())

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = svc.create_weight_item(db, aeroplane.uuid, _make_item())
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.update_weight_item(db, aeroplane.uuid, created.id, _make_item(name="new"))


# ---------------------------------------------------------------------------
# delete_weight_item
# ---------------------------------------------------------------------------

class TestDeleteWeightItem:
    def test_delete_existing_item(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = svc.create_weight_item(db, aeroplane.uuid, _make_item())

            svc.delete_weight_item(db, aeroplane.uuid, created.id)
            summary = svc.list_weight_items(db, aeroplane.uuid)
            assert len(summary.items) == 0

    def test_raises_not_found_for_missing_item(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.delete_weight_item(db, aeroplane.uuid, 99999)

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.delete_weight_item(db, uuid.uuid4(), 1)

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            created = svc.create_weight_item(db, aeroplane.uuid, _make_item())
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.delete_weight_item(db, aeroplane.uuid, created.id)

    def test_delete_one_leaves_others(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            keep = svc.create_weight_item(db, aeroplane.uuid, _make_item(name="keep"))
            remove = svc.create_weight_item(db, aeroplane.uuid, _make_item(name="remove"))

            svc.delete_weight_item(db, aeroplane.uuid, remove.id)
            summary = svc.list_weight_items(db, aeroplane.uuid)
            assert len(summary.items) == 1
            assert summary.items[0].id == keep.id
