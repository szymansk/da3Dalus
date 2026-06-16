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
    # brushless_motor seed schema requires kv_rpm_per_volt (gh#83)
    "specs": {"kv_rpm_per_volt": 880},
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
        assert body["specs"] == {"kv_rpm_per_volt": 880}
        assert "id" in body

    def test_list_components(self, client: TestClient):
        # The components table is not empty at baseline: gh-1008 seeds the
        # structural materials (Pine + Carbon Fiber) into every DB. Assert
        # relative to that baseline rather than assuming an empty table.
        baseline = client.get("/components").json()["total"]

        client.post("/components", json=MOTOR_PAYLOAD)

        resp = client.get("/components")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] == baseline + 1
        assert any(item["name"] == "Motor X" for item in body["items"])

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
        assert all(item["component_type"] == "brushless_motor" for item in body["items"])

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
    """Design-version endpoints are retired (gh-903) — table has been dropped.

    The service stubs now raise NotFoundError (404) for every call.
    These tests document that expectation while gh-905 (new version ops) is
    not yet merged.

    TODO(gh-905): replace with real version-tree endpoint tests.
    """

    @staticmethod
    def _create_aeroplane(client: TestClient) -> str:
        """Helper: create an aeroplane and return its id (str or int)."""
        resp = client.post("/aeroplanes", params={"name": "version-test-plane"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_create_design_version_retired(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        resp = client.post(
            f"/aeroplanes/{aeroplane_id}/design-versions",
            json={"label": "v1", "description": "initial"},
        )
        # Retired endpoint now returns 404 (stub raises NotFoundError).
        assert resp.status_code == 404

    def test_list_design_versions_retired(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        resp = client.get(f"/aeroplanes/{aeroplane_id}/design-versions")
        # Retired endpoint now returns 404.
        assert resp.status_code == 404

    def test_get_single_design_version_retired(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        resp = client.get(f"/aeroplanes/{aeroplane_id}/design-versions/1")
        assert resp.status_code == 404

    def test_delete_design_version_retired(self, client: TestClient):
        aeroplane_id = self._create_aeroplane(client)
        resp = client.delete(f"/aeroplanes/{aeroplane_id}/design-versions/1")
        assert resp.status_code == 404
