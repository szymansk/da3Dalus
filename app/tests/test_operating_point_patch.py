"""Tests for PATCH /operating_points/{op_id}/deflections endpoint.

Covers partial update of control_deflections on an operating point,
including field update, null clearing, 404 handling, and preservation
of other fields.
"""

from __future__ import annotations

import pytest

from app.core.platform import aerosandbox_available

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="operating_points router requires aerosandbox",
)


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
        status="TRIMMED",
        warnings=[],
        controls={"elevator": -0.02},
        xyz_ref=[0.0, 0.0, 0.0],
    )
    base.update(overrides)
    return base


class TestPatchDeflections:
    """Tests for PATCH /operating_points/{op_id}/deflections."""

    def test_patch_deflections_updates_field_and_sets_not_trimmed(self, client_and_db):
        """Patching deflections updates the field and resets status to NOT_TRIMMED."""
        client, _ = client_and_db

        # Create an OP with TRIMMED status
        create_resp = client.post("/operating_points/", json=_op_payload(status="TRIMMED"))
        assert create_resp.status_code == 200
        op_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "TRIMMED"

        # Patch deflections
        deflections = {"aileron": 5.0, "elevator": -2.0}
        patch_resp = client.patch(
            f"/operating_points/{op_id}/deflections",
            json={"control_deflections": deflections},
        )

        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["control_deflections"] == deflections
        assert data["status"] == "NOT_TRIMMED"
        assert data["id"] == op_id

    def test_patch_deflections_clears_with_null(self, client_and_db):
        """Patching with null clears the control_deflections field."""
        client, _ = client_and_db

        # Create an OP with existing deflections
        create_resp = client.post(
            "/operating_points/",
            json=_op_payload(control_deflections={"rudder": 3.0}),
        )
        assert create_resp.status_code == 200
        op_id = create_resp.json()["id"]
        assert create_resp.json()["control_deflections"] == {"rudder": 3.0}

        # Patch with null to clear
        patch_resp = client.patch(
            f"/operating_points/{op_id}/deflections",
            json={"control_deflections": None},
        )

        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["control_deflections"] is None

    def test_patch_deflections_not_found(self, client_and_db):
        """Patching a non-existent OP returns 404."""
        client, _ = client_and_db

        patch_resp = client.patch(
            "/operating_points/99999/deflections",
            json={"control_deflections": {"aileron": 1.0}},
        )

        assert patch_resp.status_code == 404
        assert "not found" in patch_resp.json()["detail"].lower()

    def test_patch_deflections_preserves_other_fields(self, client_and_db):
        """Patching deflections does not modify other OP fields."""
        client, _ = client_and_db

        original = _op_payload(
            name="preserve_test",
            velocity=42.0,
            alpha=0.1,
            altitude=500.0,
            controls={"throttle": 0.8},
        )
        create_resp = client.post("/operating_points/", json=original)
        assert create_resp.status_code == 200
        op_id = create_resp.json()["id"]

        # Patch only deflections
        patch_resp = client.patch(
            f"/operating_points/{op_id}/deflections",
            json={"control_deflections": {"flap": 10.0}},
        )

        assert patch_resp.status_code == 200
        data = patch_resp.json()

        # Verify all other fields are unchanged
        assert data["name"] == "preserve_test"
        assert data["velocity"] == 42.0
        assert data["alpha"] == 0.1
        assert data["altitude"] == 500.0
        assert data["controls"] == {"throttle": 0.8}
        assert data["description"] == "Cruise flight"
        assert data["beta"] == 0.0
        assert data["p"] == 0.0
        assert data["q"] == 0.0
        assert data["r"] == 0.0
        assert data["config"] == "clean"
        assert data["xyz_ref"] == [0.0, 0.0, 0.0]
        assert data["warnings"] == []

        # And the patched field is correct
        assert data["control_deflections"] == {"flap": 10.0}
