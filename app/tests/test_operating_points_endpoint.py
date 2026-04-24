"""Tests for app/api/v2/endpoints/operating_points.py.

Covers CRUD for operating points and operating point sets, plus the
generate-default and trim endpoints (mocked at the service layer).
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationDomainError,
    ValidationError,
)
from app.core.platform import aerosandbox_available
from app.schemas.aeroanalysisschema import (
    GeneratedOperatingPointSetRead,
    OperatingPointStatus,
    StoredOperatingPointRead,
    TrimmedOperatingPointRead,
    StoredOperatingPointCreate,
)
from app.models.analysismodels import OperatingPointModel
from app.tests.conftest import make_aeroplane

# The operating_points router is only registered when aerosandbox is available.
pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="operating_points router requires aerosandbox",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _op_payload(**overrides) -> dict:
    """Return a valid StoredOperatingPointCreate payload dict."""
    base = dict(
        name="cruise",
        description="Cruise flight",
        velocity=25.0,
        alpha=0.05,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        altitude=100.0,
        config="clean",
        status="NOT_TRIMMED",
        warnings=[],
        controls={},
        xyz_ref=[0.0, 0.0, 0.0],
    )
    base.update(overrides)
    return base


def _make_aeroplane_detached(SessionLocal, name="test-plane"):
    """Create an aeroplane and return (uuid_str, pk) without a live session."""
    db = SessionLocal()
    try:
        aeroplane = make_aeroplane(db, name=name)
        return str(aeroplane.uuid), aeroplane.id
    finally:
        db.close()


def _opset_payload(**overrides) -> dict:
    """Return a valid OperatingPointSetSchema payload dict."""
    base = dict(
        name="default_set",
        description="Default operating point set",
        operating_points=[1, 2, 3],
    )
    base.update(overrides)
    return base


# =========================================================================
# Operating Point CRUD
# =========================================================================


class TestCreateOperatingPoint:
    def test_success(self, client_and_db):
        client, _ = client_and_db
        payload = _op_payload()
        resp = client.post("/operating_points/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "cruise"
        assert data["velocity"] == 25.0
        assert "id" in data

    def test_missing_required_field(self, client_and_db):
        client, _ = client_and_db
        payload = _op_payload()
        del payload["velocity"]
        resp = client.post("/operating_points/", json=payload)
        assert resp.status_code == 422

    def test_empty_body(self, client_and_db):
        client, _ = client_and_db
        resp = client.post("/operating_points/", json={})
        assert resp.status_code == 422


class TestListOperatingPoints:
    def test_empty_list(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_points")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_points(self, client_and_db):
        client, _ = client_and_db
        client.post("/operating_points/", json=_op_payload(name="op1"))
        client.post("/operating_points/", json=_op_payload(name="op2"))
        resp = client.get("/operating_points")
        assert resp.status_code == 200
        names = [op["name"] for op in resp.json()]
        assert "op1" in names
        assert "op2" in names

    def test_filter_by_aircraft_id(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            aeroplane = make_aeroplane(db, name="filter-test")
            aircraft_uuid = str(aeroplane.uuid)
            op = OperatingPointModel(
                name="linked_op",
                description="linked op desc",
                aircraft_id=aeroplane.id,
                velocity=20.0,
                alpha=0.05,
                beta=0.0,
                p=0.0,
                q=0.0,
                r=0.0,
                altitude=0.0,
                config="clean",
                status="TRIMMED",
                warnings=[],
                controls={},
                xyz_ref=[0.0, 0.0, 0.0],
            )
            db.add(op)
            db.commit()
        finally:
            db.close()

        # Filter by existing aircraft UUID
        resp = client.get(f"/operating_points?aircraft_id={aircraft_uuid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(o["name"] == "linked_op" for o in data)

    def test_filter_by_nonexistent_aircraft_returns_empty(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())
        resp = client.get(f"/operating_points?aircraft_id={fake_uuid}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination_skip_and_limit(self, client_and_db):
        client, _ = client_and_db
        for i in range(5):
            client.post("/operating_points/", json=_op_payload(name=f"op_{i}"))
        resp = client.get("/operating_points?skip=2&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_invalid_skip_negative(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_points?skip=-1")
        assert resp.status_code == 422

    def test_invalid_limit_zero(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_points?limit=0")
        assert resp.status_code == 422


class TestReadOperatingPoint:
    def test_success(self, client_and_db):
        client, _ = client_and_db
        create_resp = client.post("/operating_points/", json=_op_payload())
        op_id = create_resp.json()["id"]
        resp = client.get(f"/operating_points/{op_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == op_id

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_points/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestUpdateOperatingPoint:
    def test_success(self, client_and_db):
        client, _ = client_and_db
        create_resp = client.post("/operating_points/", json=_op_payload())
        op_id = create_resp.json()["id"]
        updated = _op_payload(name="updated_cruise", velocity=30.0)
        resp = client.put(f"/operating_points/{op_id}", json=updated)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated_cruise"
        assert data["velocity"] == 30.0

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.put("/operating_points/99999", json=_op_payload())
        assert resp.status_code == 404

    def test_invalid_body(self, client_and_db):
        client, _ = client_and_db
        create_resp = client.post("/operating_points/", json=_op_payload())
        op_id = create_resp.json()["id"]
        resp = client.put(f"/operating_points/{op_id}", json={"name": "no_velocity"})
        assert resp.status_code == 422


class TestDeleteOperatingPoint:
    def test_success(self, client_and_db):
        client, _ = client_and_db
        create_resp = client.post("/operating_points/", json=_op_payload())
        op_id = create_resp.json()["id"]
        resp = client.delete(f"/operating_points/{op_id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["detail"].lower()
        # Verify it is gone
        get_resp = client.get(f"/operating_points/{op_id}")
        assert get_resp.status_code == 404

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.delete("/operating_points/99999")
        assert resp.status_code == 404


# =========================================================================
# Operating Point Set CRUD
# =========================================================================


class TestCreateOperatingPointSet:
    def test_success(self, client_and_db):
        client, _ = client_and_db
        payload = _opset_payload()
        resp = client.post("/operating_pointsets/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "default_set"
        assert data["operating_points"] == [1, 2, 3]

    def test_missing_required_field(self, client_and_db):
        client, _ = client_and_db
        resp = client.post("/operating_pointsets/", json={"name": "no_desc"})
        assert resp.status_code == 422


class TestListOperatingPointSets:
    def test_empty(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_pointsets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_sets(self, client_and_db):
        client, _ = client_and_db
        client.post("/operating_pointsets/", json=_opset_payload(name="set1"))
        client.post("/operating_pointsets/", json=_opset_payload(name="set2"))
        resp = client.get("/operating_pointsets")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert "set1" in names
        assert "set2" in names

    def test_filter_by_nonexistent_aircraft_returns_empty(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/operating_pointsets?aircraft_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination(self, client_and_db):
        client, _ = client_and_db
        for i in range(4):
            client.post("/operating_pointsets/", json=_opset_payload(name=f"set_{i}"))
        resp = client.get("/operating_pointsets?skip=1&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestReadOperatingPointSet:
    def _create_opset_and_get_id(self, client, SessionLocal):
        """Create an opset via API and resolve its DB id via ORM."""
        from app.models.analysismodels import OperatingPointSetModel

        client.post("/operating_pointsets/", json=_opset_payload())
        db = SessionLocal()
        try:
            opset = db.query(OperatingPointSetModel).order_by(
                OperatingPointSetModel.id.desc()
            ).first()
            return opset.id
        finally:
            db.close()

    def test_success(self, client_and_db):
        client, SessionLocal = client_and_db
        opset_id = self._create_opset_and_get_id(client, SessionLocal)
        resp = client.get(f"/operating_pointsets/{opset_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "default_set"

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/operating_pointsets/99999")
        assert resp.status_code == 404


class TestUpdateOperatingPointSet:
    def _create_opset_and_get_id(self, client, SessionLocal):
        from app.models.analysismodels import OperatingPointSetModel

        client.post("/operating_pointsets/", json=_opset_payload())
        db = SessionLocal()
        try:
            opset = db.query(OperatingPointSetModel).order_by(
                OperatingPointSetModel.id.desc()
            ).first()
            return opset.id
        finally:
            db.close()

    def test_success(self, client_and_db):
        client, SessionLocal = client_and_db
        opset_id = self._create_opset_and_get_id(client, SessionLocal)
        updated = _opset_payload(name="renamed_set", operating_points=[10, 20])
        resp = client.put(f"/operating_pointsets/{opset_id}", json=updated)
        assert resp.status_code == 200
        assert resp.json()["name"] == "renamed_set"
        assert resp.json()["operating_points"] == [10, 20]

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.put("/operating_pointsets/99999", json=_opset_payload())
        assert resp.status_code == 404


class TestDeleteOperatingPointSet:
    def _create_opset_and_get_id(self, client, SessionLocal):
        from app.models.analysismodels import OperatingPointSetModel

        client.post("/operating_pointsets/", json=_opset_payload())
        db = SessionLocal()
        try:
            opset = db.query(OperatingPointSetModel).order_by(
                OperatingPointSetModel.id.desc()
            ).first()
            return opset.id
        finally:
            db.close()

    def test_success(self, client_and_db):
        client, SessionLocal = client_and_db
        opset_id = self._create_opset_and_get_id(client, SessionLocal)
        resp = client.delete(f"/operating_pointsets/{opset_id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["detail"].lower()
        get_resp = client.get(f"/operating_pointsets/{opset_id}")
        assert get_resp.status_code == 404

    def test_not_found(self, client_and_db):
        client, _ = client_and_db
        resp = client.delete("/operating_pointsets/99999")
        assert resp.status_code == 404


# =========================================================================
# Generate default operating point set (service-mocked)
# =========================================================================


class TestGenerateDefaultOperatingPointSet:
    _SERVICE = "app.api.v2.endpoints.operating_points.operating_point_generator_service"

    def test_success_default_request(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, aircraft_pk = _make_aeroplane_detached(SessionLocal, "gen-test")

        mock_return = GeneratedOperatingPointSetRead(
            id=1,
            name="auto_set",
            description="Generated set",
            aircraft_id=aircraft_pk,
            source_flight_profile_id=None,
            operating_points=[
                StoredOperatingPointRead(
                    id=1, name="op1", description="desc", velocity=20.0,
                    alpha=0.05, beta=0.0, p=0.0, q=0.0, r=0.0,
                    altitude=0.0, config="clean",
                    status=OperatingPointStatus.TRIMMED,
                    warnings=[], controls={}, xyz_ref=[0, 0, 0],
                ),
            ],
        )
        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            return_value=mock_return,
        ) as mock_gen:
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "auto_set"
            assert len(data["operating_points"]) == 1
            mock_gen.assert_called_once()

    def test_with_explicit_request_body(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, aircraft_pk = _make_aeroplane_detached(SessionLocal, "gen-body-test")

        mock_return = GeneratedOperatingPointSetRead(
            id=2, name="custom_set", description="desc",
            operating_points=[], aircraft_id=aircraft_pk,
        )
        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            return_value=mock_return,
        ) as mock_gen:
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
                json={"replace_existing": True, "profile_id_override": 42},
            )
            assert resp.status_code == 200
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["replace_existing"] is True
            assert call_kwargs["profile_id_override"] == 42

    def test_not_found_error(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = uuid.uuid4()
        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            side_effect=NotFoundError("Aircraft not found"),
        ):
            resp = client.post(
                f"/aeroplanes/{fake_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 404

    def test_validation_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "val-err-test")

        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            side_effect=ValidationError("Invalid config"),
        ):
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 422

    def test_validation_domain_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "domain-err-test")

        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            side_effect=ValidationDomainError("Domain rule violated"),
        ):
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 422

    def test_conflict_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "conflict-test")

        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            side_effect=ConflictError("Already exists"),
        ):
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 409

    def test_internal_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "internal-err-test")

        with patch(
            f"{self._SERVICE}.generate_default_set_for_aircraft",
            side_effect=InternalError("Something broke"),
        ):
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-pointsets/generate-default",
            )
            assert resp.status_code == 500

    def test_invalid_uuid_path(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            "/aeroplanes/not-a-uuid/operating-pointsets/generate-default",
        )
        assert resp.status_code == 422


# =========================================================================
# Trim operating point (service-mocked)
# =========================================================================


class TestTrimOperatingPoint:
    _SERVICE = "app.api.v2.endpoints.operating_points.operating_point_generator_service"

    def test_success(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "trim-test")

        mock_return = TrimmedOperatingPointRead(
            source_flight_profile_id=None,
            point=StoredOperatingPointCreate(
                name="trimmed_pt", description="desc",
                velocity=20.0, alpha=0.05, beta=0.0,
                p=0.0, q=0.0, r=0.0, altitude=0.0,
                config="clean", status=OperatingPointStatus.TRIMMED,
                warnings=[], controls={"elevator": -0.02},
                xyz_ref=[0, 0, 0],
            ),
        )
        with patch(
            f"{self._SERVICE}.trim_operating_point_for_aircraft",
            return_value=mock_return,
        ) as mock_trim:
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-points/trim",
                json={
                    "name": "custom_trim",
                    "config": "clean",
                    "velocity": 20.0,
                    "altitude": 0.0,
                    "beta_target_deg": 0.0,
                    "n_target": 1.0,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["point"]["name"] == "trimmed_pt"
            assert data["point"]["controls"]["elevator"] == -0.02
            mock_trim.assert_called_once()

    def test_missing_velocity(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "trim-missing")

        resp = client.post(
            f"/aeroplanes/{aircraft_uuid}/operating-points/trim",
            json={"name": "bad_trim", "config": "clean"},
        )
        assert resp.status_code == 422

    def test_velocity_must_be_positive(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "trim-negative-v")

        resp = client.post(
            f"/aeroplanes/{aircraft_uuid}/operating-points/trim",
            json={"velocity": 0.0, "n_target": 1.0},
        )
        assert resp.status_code == 422

    def test_not_found_error(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = uuid.uuid4()
        with patch(
            f"{self._SERVICE}.trim_operating_point_for_aircraft",
            side_effect=NotFoundError("Aircraft not found"),
        ):
            resp = client.post(
                f"/aeroplanes/{fake_uuid}/operating-points/trim",
                json={"velocity": 20.0, "n_target": 1.0},
            )
            assert resp.status_code == 404

    def test_conflict_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "trim-conflict")

        with patch(
            f"{self._SERVICE}.trim_operating_point_for_aircraft",
            side_effect=ConflictError("Trim conflict"),
        ):
            resp = client.post(
                f"/aeroplanes/{aircraft_uuid}/operating-points/trim",
                json={"velocity": 20.0, "n_target": 1.0},
            )
            assert resp.status_code == 409

    def test_empty_body(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "trim-empty")

        resp = client.post(
            f"/aeroplanes/{aircraft_uuid}/operating-points/trim",
            json={},
        )
        assert resp.status_code == 422


# =========================================================================
# _raise_http_from_domain helper (unit-level)
# =========================================================================


class TestRaiseHttpFromDomain:
    """Direct unit tests for the error-mapping helper."""

    def test_generic_service_exception_maps_to_500(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.operating_points import _raise_http_from_domain
        from app.core.exceptions import ServiceException

        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ServiceException("generic error"))
        assert exc_info.value.status_code == 500
