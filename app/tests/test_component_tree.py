"""Tests for the component tree (GH#34)."""

import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _uid():
    return f"test-{uuid.uuid4().hex[:8]}"


class TestComponentTreeCRUD:

    def test_get_empty_tree(self):
        aero = _uid()
        res = client.get(f"/aeroplanes/{aero}/component-tree")
        assert res.status_code == 200
        data = res.json()
        assert data["root_nodes"] == []
        assert data["total_nodes"] == 0

    def test_add_root_group_node(self):
        aero = _uid()
        res = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "eHawk",
        })
        assert res.status_code == 201
        assert res.json()["node_type"] == "group"
        assert res.json()["parent_id"] is None

    def test_add_child_node(self):
        aero = _uid()
        parent = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "main_wing",
        }).json()
        child = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "segment 0",
            "shape_key": "seg0_shell",
        }).json()
        assert child["parent_id"] == parent["id"]

    def test_add_cots_node(self):
        aero = _uid()
        comp = client.post("/components", json={
            "name": "TreeTestServo", "component_type": "servo",
            "mass_g": 14.0, "specs": {},
        }).json()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "cots", "name": "Servo",
            "component_id": comp["id"], "quantity": 2,
        }).json()
        assert node["component_id"] == comp["id"]
        assert node["quantity"] == 2

    def test_get_tree_nested(self):
        aero = _uid()
        root = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "root",
        }).json()
        client.post(f"/aeroplanes/{aero}/component-tree", json={
            "parent_id": root["id"],
            "node_type": "group", "name": "wing",
        })
        tree = client.get(f"/aeroplanes/{aero}/component-tree").json()
        assert tree["total_nodes"] == 2
        assert tree["root_nodes"][0]["children"][0]["name"] == "wing"

    def test_update_node(self):
        aero = _uid()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "old",
        }).json()
        res = client.put(f"/aeroplanes/{aero}/component-tree/{node['id']}", json={
            "node_type": "group", "name": "new",
        })
        assert res.status_code == 200
        assert res.json()["name"] == "new"

    def test_delete_node(self):
        aero = _uid()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "delete_me",
        }).json()
        res = client.delete(f"/aeroplanes/{aero}/component-tree/{node['id']}")
        assert res.status_code == 204

    def test_delete_synced_node_rejected(self):
        aero = _uid()
        from app.db.session import get_db
        from app.models.component_tree import ComponentTreeNodeModel
        db = next(get_db())
        node = ComponentTreeNodeModel(
            aeroplane_id=aero, node_type="group", name="synced",
            synced_from="wing:main_wing",
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        res = client.delete(f"/aeroplanes/{aero}/component-tree/{node.id}")
        assert res.status_code == 422


class TestMoveNode:

    def test_move_node(self):
        aero = _uid()
        p1 = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "p1",
        }).json()
        p2 = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "p2",
        }).json()
        child = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "parent_id": p1["id"], "node_type": "group", "name": "child",
        }).json()
        res = client.post(f"/aeroplanes/{aero}/component-tree/{child['id']}/move", json={
            "new_parent_id": p2["id"], "sort_index": 0,
        })
        assert res.json()["parent_id"] == p2["id"]


class TestWeightCalculation:

    def test_cots_weight(self):
        aero = _uid()
        comp = client.post("/components", json={
            "name": "WtMotor", "component_type": "brushless_motor",
            "mass_g": 50.0, "specs": {},
        }).json()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "cots", "name": "motor",
            "component_id": comp["id"],
        }).json()
        wt = client.get(f"/aeroplanes/{aero}/component-tree/{node['id']}/weight").json()
        assert wt["own_weight_g"] == 50.0
        assert wt["source"] == "cots"

    def test_override_weight(self):
        aero = _uid()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "cad_shape", "name": "shell",
            "weight_override_g": 25.5,
        }).json()
        wt = client.get(f"/aeroplanes/{aero}/component-tree/{node['id']}/weight").json()
        assert wt["own_weight_g"] == 25.5
        assert wt["source"] == "override"

    def test_recursive_weight(self):
        aero = _uid()
        parent = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "group", "name": "assembly",
        }).json()
        client.post(f"/aeroplanes/{aero}/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "a", "weight_override_g": 10.0,
        })
        client.post(f"/aeroplanes/{aero}/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "b", "weight_override_g": 20.0,
        })
        wt = client.get(f"/aeroplanes/{aero}/component-tree/{parent['id']}/weight").json()
        assert wt["children_weight_g"] == 30.0
        assert wt["total_weight_g"] == 30.0

    def test_calculated_volume_weight(self):
        aero = _uid()
        mat = client.post("/components", json={
            "name": "PLA", "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        }).json()
        node = client.post(f"/aeroplanes/{aero}/component-tree", json={
            "node_type": "cad_shape", "name": "wing_shell",
            "volume_mm3": 10000, "material_id": mat["id"],
            "print_type": "volume", "scale_factor": 1.0,
        }).json()
        wt = client.get(f"/aeroplanes/{aero}/component-tree/{node['id']}/weight").json()
        assert wt["source"] == "calculated"
        assert abs(wt["own_weight_g"] - 12.4) < 0.1
