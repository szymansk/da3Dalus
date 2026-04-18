"""Tests for auto-sync of Wings/Fuselages into the Component Tree (gh#108)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


def _create_aeroplane(client: TestClient) -> str:
    resp = client.post("/aeroplanes", params={"name": "sync_test"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _make_wingconfig() -> dict:
    return {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
            }
        ],
        "nose_pnt": [0, 0, 0],
        "symmetric": True,
    }


def _get_tree(client: TestClient, aero_id: str) -> list:
    resp = client.get(f"/aeroplanes/{aero_id}/component-tree")
    assert resp.status_code == 200
    return resp.json()["root_nodes"]


def _find_synced(nodes: list, synced_from: str) -> dict | None:
    for n in nodes:
        if n.get("synced_from") == synced_from:
            return n
        found = _find_synced(n.get("children", []), synced_from)
        if found:
            return found
    return None


class TestWingAutoSync:
    """Creating/deleting wings auto-syncs groups in the component tree."""

    def test_wing_creates_synced_group(self, client):
        aero_id = _create_aeroplane(client)
        resp = client.post(
            f"/aeroplanes/{aero_id}/wings/main_wing/from-wingconfig",
            json=_make_wingconfig(),
        )
        assert resp.status_code == 201

        nodes = _get_tree(client, aero_id)
        group = _find_synced(nodes, "wing:main_wing")
        assert group is not None, "Synced wing group not found"
        assert group["name"] == "main_wing"
        assert group["node_type"] == "group"

    def test_wing_group_not_deletable(self, client):
        aero_id = _create_aeroplane(client)
        client.post(
            f"/aeroplanes/{aero_id}/wings/main_wing/from-wingconfig",
            json=_make_wingconfig(),
        )
        nodes = _get_tree(client, aero_id)
        group = _find_synced(nodes, "wing:main_wing")
        resp = client.delete(f"/aeroplanes/{aero_id}/component-tree/{group['id']}")
        assert resp.status_code == 422, "Synced node should not be deletable"

    def test_wing_delete_removes_synced_group(self, client):
        aero_id = _create_aeroplane(client)
        client.post(
            f"/aeroplanes/{aero_id}/wings/main_wing/from-wingconfig",
            json=_make_wingconfig(),
        )
        # Verify group exists
        assert _find_synced(_get_tree(client, aero_id), "wing:main_wing") is not None

        # Delete the wing
        resp = client.delete(f"/aeroplanes/{aero_id}/wings/main_wing")
        assert resp.status_code == 200

        # Group should be gone
        assert _find_synced(_get_tree(client, aero_id), "wing:main_wing") is None

    def test_duplicate_wing_no_duplicate_group(self, client):
        aero_id = _create_aeroplane(client)
        # Create wing twice (PUT semantics — idempotent)
        client.put(
            f"/aeroplanes/{aero_id}/wings/main_wing",
            json={"name": "main_wing", "symmetric": True, "x_secs": [
                {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0015"},
                {"xyz_le": [0, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0015"},
            ]},
        )
        client.put(
            f"/aeroplanes/{aero_id}/wings/main_wing",
            json={"name": "main_wing", "symmetric": True, "x_secs": [
                {"xyz_le": [0, 0, 0], "chord": 0.15, "twist": 0, "airfoil": "naca0015"},
                {"xyz_le": [0, 0.5, 0], "chord": 0.12, "twist": 0, "airfoil": "naca0015"},
            ]},
        )
        nodes = _get_tree(client, aero_id)
        groups = [n for n in _flatten(nodes) if n.get("synced_from") == "wing:main_wing"]
        assert len(groups) == 1, f"Expected 1 synced group, got {len(groups)}"


class TestFuselageAutoSync:
    """Creating/deleting fuselages auto-syncs groups."""

    def test_fuselage_creates_synced_group(self, client):
        aero_id = _create_aeroplane(client)
        resp = client.put(
            f"/aeroplanes/{aero_id}/fuselages/fuse_1",
            json={
                "name": "fuse_1",
                "x_secs": [
                    {"xyz": [0, 0, 0], "a": 0.05, "b": 0.05, "n": 2.0},
                    {"xyz": [0.3, 0, 0], "a": 0.04, "b": 0.04, "n": 2.0},
                ],
            },
        )
        assert resp.status_code in (200, 201)

        nodes = _get_tree(client, aero_id)
        group = _find_synced(nodes, "fuselage:fuse_1")
        assert group is not None, "Synced fuselage group not found"
        assert group["name"] == "fuse_1"

    def test_fuselage_delete_removes_synced_group(self, client):
        aero_id = _create_aeroplane(client)
        client.put(
            f"/aeroplanes/{aero_id}/fuselages/fuse_1",
            json={"name": "fuse_1", "x_secs": [
                {"xyz": [0, 0, 0], "a": 0.05, "b": 0.05, "n": 2.0},
                {"xyz": [0.3, 0, 0], "a": 0.04, "b": 0.04, "n": 2.0},
            ]},
        )
        assert _find_synced(_get_tree(client, aero_id), "fuselage:fuse_1") is not None

        resp = client.delete(f"/aeroplanes/{aero_id}/fuselages/fuse_1")
        assert resp.status_code in (200, 204)
        assert _find_synced(_get_tree(client, aero_id), "fuselage:fuse_1") is None


def _flatten(nodes: list) -> list:
    """Flatten nested tree to a flat list."""
    result = []
    for n in nodes:
        result.append(n)
        result.extend(_flatten(n.get("children", [])))
    return result
