"""CRUD endpoint tests for Weight Items and Copilot History.

Each test function creates its own aeroplane via the REST API and then
exercises the subresource CRUD operations.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _create_aeroplane(client, name: str = "test-plane") -> str:
    """Create an aeroplane via POST and return its UUID."""
    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


# ===========================================================================
# Weight Items
# ===========================================================================


class TestWeightItems:
    BATTERY_ITEM = {
        "name": "Battery",
        "mass_kg": 0.5,
        "x_m": 0.1,
        "y_m": 0,
        "z_m": 0,
        "category": "battery",
    }

    def test_create_and_list_weight_items(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        post_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/weight-items", json=self.BATTERY_ITEM
        )
        assert post_resp.status_code in (200, 201), post_resp.text

        get_resp = client.get(f"/aeroplanes/{aeroplane_id}/weight-items")
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Battery"
        assert data["total_mass_kg"] == pytest.approx(0.5)

    def test_update_weight_item(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        post_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/weight-items", json=self.BATTERY_ITEM
        )
        item_id = post_resp.json()["id"]

        update_body = {**self.BATTERY_ITEM, "mass_kg": 0.8}
        put_resp = client.put(
            f"/aeroplanes/{aeroplane_id}/weight-items/{item_id}",
            json=update_body,
        )
        assert put_resp.status_code == 200, put_resp.text

        get_resp = client.get(f"/aeroplanes/{aeroplane_id}/weight-items")
        data = get_resp.json()
        assert data["items"][0]["mass_kg"] == pytest.approx(0.8)
        assert data["total_mass_kg"] == pytest.approx(0.8)

    def test_delete_weight_item(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        post_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/weight-items", json=self.BATTERY_ITEM
        )
        item_id = post_resp.json()["id"]

        del_resp = client.delete(
            f"/aeroplanes/{aeroplane_id}/weight-items/{item_id}"
        )
        assert del_resp.status_code == 204, del_resp.text

    def test_list_weight_items_empty_after_delete(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        post_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/weight-items", json=self.BATTERY_ITEM
        )
        item_id = post_resp.json()["id"]

        client.delete(f"/aeroplanes/{aeroplane_id}/weight-items/{item_id}")

        get_resp = client.get(f"/aeroplanes/{aeroplane_id}/weight-items")
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert len(data["items"]) == 0


# ===========================================================================
# Copilot History
# ===========================================================================


class TestCopilotHistory:
    def test_post_and_get_copilot_history(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        message = {"role": "user", "content": "hello"}
        post_resp = client.post(
            f"/aeroplanes/{aeroplane_id}/copilot-history", json=message
        )
        assert post_resp.status_code in (200, 201), post_resp.text

        get_resp = client.get(
            f"/aeroplanes/{aeroplane_id}/copilot-history"
        )
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert "messages" in data
        assert len(data["messages"]) >= 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "hello"

    def test_delete_copilot_history_clears_all(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        client.post(
            f"/aeroplanes/{aeroplane_id}/copilot-history",
            json={"role": "user", "content": "hello"},
        )

        del_resp = client.delete(
            f"/aeroplanes/{aeroplane_id}/copilot-history"
        )
        assert del_resp.status_code == 204, del_resp.text

    def test_get_copilot_history_empty_after_clear(self, client_and_db):
        client, _ = client_and_db
        aeroplane_id = _create_aeroplane(client)

        client.post(
            f"/aeroplanes/{aeroplane_id}/copilot-history",
            json={"role": "user", "content": "hello"},
        )
        client.delete(f"/aeroplanes/{aeroplane_id}/copilot-history")

        get_resp = client.get(
            f"/aeroplanes/{aeroplane_id}/copilot-history"
        )
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert len(data["messages"]) == 0
