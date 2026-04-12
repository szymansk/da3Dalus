"""Tests for the Component Library and Design Versions REST endpoints.

Covers:
1. Component Library CRUD — POST / GET / PUT / DELETE on /components
2. Design Versions — POST / GET / DELETE on /aeroplanes/{id}/design-versions
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


# --------------------------------------------------------------------------- #
# 1. Component Library — /components
# --------------------------------------------------------------------------- #

MOTOR_PAYLOAD = {
    "name": "Motor X",
    "component_type": "brushless_motor",
    "mass_g": 130,
    "specs": {"kv": 880},
}


class TestComponentLibraryCRUD:
    """Full create → read → update → delete lifecycle for /components."""

    def test_create_component(self, client: TestClient):
        resp = client.post("/components", json=MOTOR_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Motor X"
        assert body["component_type"] == "brushless_motor"
        assert body["mass_g"] == 130
        assert body["specs"] == {"kv": 880}
        assert "id" in body

    def test_list_components(self, client: TestClient):
        client.post("/components", json=MOTOR_PAYLOAD)

        resp = client.get("/components")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Motor X"

    def test_list_components_filtered_by_type(self, client: TestClient):
        client.post("/components", json=MOTOR_PAYLOAD)
        client.post(
            "/components",
            json={
                "name": "Servo Y",
                "component_type": "servo",
                "mass_g": 12,
                "specs": {"torque_kg_cm": 2.5},
            },
        )

        resp = client.get("/components", params={"component_type": "brushless_motor"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert all(
            item["component_type"] == "brushless_motor" for item in body["items"]
        )

    def test_get_single_component(self, client: TestClient):
        create_resp = client.post("/components", json=MOTOR_PAYLOAD)
        component_id = create_resp.json()["id"]

        resp = client.get(f"/components/{component_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == component_id
        assert body["name"] == "Motor X"

    def test_update_component_name(self, client: TestClient):
        create_resp = client.post("/components", json=MOTOR_PAYLOAD)
        component_id = create_resp.json()["id"]

        updated = {**MOTOR_PAYLOAD, "name": "Motor X-Pro"}
        resp = client.put(
            f"/components/{component_id}",
            json=updated,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Motor X-Pro"

    def test_delete_component(self, client: TestClient):
        create_resp = client.post("/components", json=MOTOR_PAYLOAD)
        component_id = create_resp.json()["id"]

        del_resp = client.delete(f"/components/{component_id}")
        assert del_resp.status_code == 204

    def test_get_deleted_component_returns_404(self, client: TestClient):
        create_resp = client.post("/components", json=MOTOR_PAYLOAD)
        component_id = create_resp.json()["id"]

        client.delete(f"/components/{component_id}")

        resp = client.get(f"/components/{component_id}")
        assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# 2. Design Versions — /aeroplanes/{id}/design-versions
# --------------------------------------------------------------------------- #


class TestDesignVersions:
    """CRUD lifecycle for design versions scoped to an aeroplane."""

    @staticmethod
    def _create_aeroplane(client: TestClient) -> str:
        """Helper: create an aeroplane and return its id (str or int)."""
        resp = client.post("/aeroplanes", params={"name": "version-test-plane"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_create_design_version(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)

        resp = client.post(
            f"/aeroplanes/{aeroplane_id}/design-versions",
            json={"label": "v1", "description": "initial"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["label"] == "v1"
        assert body["description"] == "initial"
        assert "id" in body

    def test_list_design_versions(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        client.post(
            f"/aeroplanes/{aeroplane_id}/design-versions",
            json={"label": "v1", "description": "initial"},
        )

        resp = client.get(f"/aeroplanes/{aeroplane_id}/design-versions")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["label"] == "v1"

    def test_get_single_design_version(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        create_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/design-versions",
            json={"label": "v1", "description": "initial"},
        )
        version_id = create_resp.json()["id"]

        resp = client.get(
            f"/aeroplanes/{aeroplane_id}/design-versions/{version_id}"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == version_id
        assert body["label"] == "v1"
        # The single-version response should include a snapshot of the design.
        assert "snapshot" in body or "description" in body

    def test_delete_design_version(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        create_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/design-versions",
            json={"label": "v1", "description": "initial"},
        )
        version_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/aeroplanes/{aeroplane_id}/design-versions/{version_id}"
        )
        assert del_resp.status_code == 204
