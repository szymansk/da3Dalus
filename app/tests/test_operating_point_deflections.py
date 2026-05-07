"""Tests for control surface deflection overrides on operating points (#416)."""

from __future__ import annotations

import pytest
from app.core.platform import aerosandbox_available
from app.schemas.aeroanalysisschema import OperatingPointSchema, StoredOperatingPointCreate
from app.models.analysismodels import OperatingPointModel

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="operating_points router requires aerosandbox",
)


class TestOperatingPointSchemaDeflections:
    def test_accepts_control_deflections_dict(self):
        op = OperatingPointSchema(control_deflections={"elevator": -2.0, "aileron": 1.5})
        assert op.control_deflections == {"elevator": -2.0, "aileron": 1.5}

    def test_default_is_none(self):
        op = OperatingPointSchema()
        assert op.control_deflections is None

    def test_accepts_none_explicitly(self):
        op = OperatingPointSchema(control_deflections=None)
        assert op.control_deflections is None

    def test_accepts_empty_dict(self):
        op = OperatingPointSchema(control_deflections={})
        assert op.control_deflections == {}


class TestStoredOperatingPointCreateDeflections:
    def test_accepts_control_deflections(self):
        op = StoredOperatingPointCreate(
            name="test",
            description="test",
            velocity=10.0,
            alpha=0.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            altitude=0.0,
            control_deflections={"elevator": -2.0},
        )
        assert op.control_deflections == {"elevator": -2.0}

    def test_default_is_none(self):
        op = StoredOperatingPointCreate(
            name="test",
            description="test",
            velocity=10.0,
            alpha=0.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            altitude=0.0,
        )
        assert op.control_deflections is None

    def test_round_trip_model_dump(self):
        deflections = {"elevator": -2.0, "flap": 15.0}
        op = StoredOperatingPointCreate(
            name="test",
            description="test",
            velocity=10.0,
            alpha=0.0,
            beta=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            altitude=0.0,
            control_deflections=deflections,
        )
        data = op.model_dump()
        assert data["control_deflections"] == deflections
        restored = StoredOperatingPointCreate(**data)
        assert restored.control_deflections == deflections


class TestOperatingPointCRUDDeflections:
    """Test CRUD endpoints handle control_deflections."""

    def _op_payload(self, **overrides):
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

    def test_create_with_deflections(self, client_and_db):
        client, _ = client_and_db
        payload = self._op_payload(control_deflections={"elevator": -2.0})
        resp = client.post("/operating_points/", json=payload)
        assert resp.status_code == 200
        assert resp.json()["control_deflections"] == {"elevator": -2.0}

    def test_create_without_deflections(self, client_and_db):
        client, _ = client_and_db
        payload = self._op_payload()
        resp = client.post("/operating_points/", json=payload)
        assert resp.status_code == 200
        assert resp.json()["control_deflections"] is None

    def test_update_with_deflections(self, client_and_db):
        client, _ = client_and_db
        # Create without
        payload = self._op_payload()
        resp = client.post("/operating_points/", json=payload)
        op_id = resp.json()["id"]
        # Update with deflections
        payload["control_deflections"] = {"aileron": 3.0}
        resp = client.put(f"/operating_points/{op_id}", json=payload)
        assert resp.status_code == 200
        assert resp.json()["control_deflections"] == {"aileron": 3.0}

    def test_list_includes_deflections(self, client_and_db):
        client, _ = client_and_db
        payload = self._op_payload(control_deflections={"rudder": 5.0})
        client.post("/operating_points/", json=payload)
        resp = client.get("/operating_points")
        assert resp.status_code == 200
        points = resp.json()
        assert any(p["control_deflections"] == {"rudder": 5.0} for p in points)

    def test_get_single_includes_deflections(self, client_and_db):
        client, _ = client_and_db
        payload = self._op_payload(control_deflections={"elevator": -1.0})
        resp = client.post("/operating_points/", json=payload)
        op_id = resp.json()["id"]
        resp = client.get(f"/operating_points/{op_id}")
        assert resp.status_code == 200
        assert resp.json()["control_deflections"] == {"elevator": -1.0}
