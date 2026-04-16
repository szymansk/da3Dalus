"""Tests for weight fields enriched onto the component tree response (gh#78).

GET /aeroplanes/{id}/component-tree should populate per-node `own_weight_g`,
`own_weight_source`, `total_weight_g`, and `weight_status` so the frontend
can render per-row weight + a red/yellow/green status icon without fetching
the dedicated weight endpoint per node.
"""
from __future__ import annotations


def _make_material(client):
    """Create a material component used by cad_shape weight calc (density 1240 kg/m³)."""
    return client.post("/components", json={
        "name": "PLA+",
        "component_type": "material",
        "specs": {"density_kg_m3": 1240, "print_resolution_mm": 0.4},
    }).json()


def _make_cots(client, mass_g=10.0):
    return client.post("/components", json={
        "name": f"Servo{mass_g}",
        "component_type": "servo",
        "mass_g": mass_g,
        "specs": {},
    }).json()


# --------------------------------------------------------------------------- #
# Schema extension (AC-01): every node has the four new fields
# --------------------------------------------------------------------------- #

class TestResponseSchema:

    def test_empty_aeroplane_returns_empty_list(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/aeroplanes/empty/component-tree").json()
        assert body["root_nodes"] == []

    def test_every_node_exposes_weight_fields(self, client_and_db):
        client, _ = client_and_db
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "root",
            "weight_override_g": 100,
        })
        body = client.get("/aeroplanes/a/component-tree").json()
        node = body["root_nodes"][0]
        assert "own_weight_g" in node
        assert "own_weight_source" in node
        assert "total_weight_g" in node
        assert "weight_status" in node


# --------------------------------------------------------------------------- #
# Source + status for individual nodes (AC-02, AC-03)
# --------------------------------------------------------------------------- #

class TestIndividualNodeStatus:

    def test_cots_leaf_with_mass_is_valid(self, client_and_db):
        client, _ = client_and_db
        comp = _make_cots(client, mass_g=15.0)
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "cots", "name": "s",
            "component_id": comp["id"], "quantity": 2,
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert node["own_weight_g"] == 30.0  # 15 × 2
        assert node["own_weight_source"] == "cots"
        assert node["weight_status"] == "valid"
        assert node["total_weight_g"] == 30.0

    def test_cad_shape_leaf_with_volume_and_material_is_valid(self, client_and_db):
        client, _ = client_and_db
        material = _make_material(client)
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "cad_shape", "name": "part",
            "volume_mm3": 10_000,   # 10 cm³
            "material_id": material["id"],
            "scale_factor": 1.0,
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        # 10000 mm³ × 1240 kg/m³ × 1e-6 (mm³→m³ adjusted) — see service; source must be "calculated"
        assert node["own_weight_source"] == "calculated"
        assert node["weight_status"] == "valid"
        assert node["own_weight_g"] is not None and node["own_weight_g"] > 0

    def test_weight_override_wins(self, client_and_db):
        client, _ = client_and_db
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "cad_shape", "name": "fixed",
            "weight_override_g": 42,
            "volume_mm3": 999,  # would otherwise compute, but override wins
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert node["own_weight_g"] == 42.0
        assert node["own_weight_source"] == "override"
        assert node["weight_status"] == "valid"

    def test_leaf_without_weight_is_invalid(self, client_and_db):
        client, _ = client_and_db
        # CAD shape with no volume/material/override — cannot compute
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "cad_shape", "name": "unknown",
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert node["own_weight_g"] is None
        assert node["own_weight_source"] == "none"
        assert node["weight_status"] == "invalid"
        assert node["total_weight_g"] == 0.0  # counted as 0 in aggregates

    def test_empty_group_is_invalid(self, client_and_db):
        """A group with no children and no override cannot contribute weight → invalid."""
        client, _ = client_and_db
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "empty",
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert node["weight_status"] == "invalid"
        assert node["total_weight_g"] == 0.0

    def test_group_with_override_but_no_children_is_valid(self, client_and_db):
        client, _ = client_and_db
        client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "g",
            "weight_override_g": 50,
        })
        node = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert node["own_weight_source"] == "override"
        assert node["weight_status"] == "valid"
        assert node["total_weight_g"] == 50.0


# --------------------------------------------------------------------------- #
# Status propagation across nested trees (AC-04, AC-05)
# --------------------------------------------------------------------------- #

class TestStatusPropagation:

    def test_all_valid_children_roll_up_to_valid_group(self, client_and_db):
        client, _ = client_and_db
        comp = _make_cots(client, mass_g=10)
        parent = client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "root",
        }).json()
        for _ in range(3):
            client.post("/aeroplanes/a/component-tree", json={
                "parent_id": parent["id"],
                "node_type": "cots", "name": "s",
                "component_id": comp["id"],
            })
        body = client.get("/aeroplanes/a/component-tree").json()
        root = body["root_nodes"][0]
        assert root["weight_status"] == "valid"
        assert root["total_weight_g"] == 30.0  # 3 × 10

    def test_one_invalid_child_makes_parent_partial(self, client_and_db):
        client, _ = client_and_db
        comp = _make_cots(client, mass_g=10)
        parent = client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "root",
        }).json()
        client.post("/aeroplanes/a/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cots", "name": "valid",
            "component_id": comp["id"],
        })
        client.post("/aeroplanes/a/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "ghost",
        })
        root = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert root["weight_status"] == "partial"
        assert root["total_weight_g"] == 10.0  # ghost counted as 0

    def test_all_invalid_children_roll_up_to_invalid_when_group_has_no_override(self, client_and_db):
        client, _ = client_and_db
        parent = client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "root",
        }).json()
        client.post("/aeroplanes/a/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "ghost1",
        })
        client.post("/aeroplanes/a/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "ghost2",
        })
        root = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert root["weight_status"] == "invalid"
        assert root["total_weight_g"] == 0.0

    def test_all_invalid_children_but_group_has_override_is_partial(self, client_and_db):
        """Override gives the group a known weight; the children being invalid makes it partial."""
        client, _ = client_and_db
        parent = client.post("/aeroplanes/a/component-tree", json={
            "node_type": "group", "name": "root",
            "weight_override_g": 500,
        }).json()
        client.post("/aeroplanes/a/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "ghost",
        })
        root = client.get("/aeroplanes/a/component-tree").json()["root_nodes"][0]
        assert root["weight_status"] == "partial"
        # total includes the override (500) but not the ghost (0)
        assert root["total_weight_g"] == 500.0

    def test_deep_tree_propagates_partial_status_to_root(self, client_and_db):
        """Invalid leaf at depth 3 → partial all the way up."""
        client, _ = client_and_db
        comp = _make_cots(client, mass_g=10)
        a = client.post("/aeroplanes/x/component-tree", json={
            "node_type": "group", "name": "A",
        }).json()
        b = client.post("/aeroplanes/x/component-tree", json={
            "parent_id": a["id"], "node_type": "group", "name": "B",
        }).json()
        c = client.post("/aeroplanes/x/component-tree", json={
            "parent_id": b["id"], "node_type": "group", "name": "C",
        }).json()
        # one valid + one invalid leaf under C
        client.post("/aeroplanes/x/component-tree", json={
            "parent_id": c["id"], "node_type": "cots", "name": "ok",
            "component_id": comp["id"],
        })
        client.post("/aeroplanes/x/component-tree", json={
            "parent_id": c["id"], "node_type": "cad_shape", "name": "ghost",
        })
        body = client.get("/aeroplanes/x/component-tree").json()
        root = body["root_nodes"][0]
        assert root["weight_status"] == "partial"
        b_node = root["children"][0]
        c_node = b_node["children"][0]
        assert b_node["weight_status"] == "partial"
        assert c_node["weight_status"] == "partial"
        # the leaves
        statuses = {leaf["name"]: leaf["weight_status"] for leaf in c_node["children"]}
        assert statuses == {"ok": "valid", "ghost": "invalid"}
