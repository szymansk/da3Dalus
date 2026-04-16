"""Tests for the component tree (GH#34).

Uses the client_and_db fixture for in-memory SQLite isolation.
"""

from app.models.component_tree import ComponentTreeNodeModel


class TestComponentTreeCRUD:

    def test_get_empty_tree(self, client_and_db):
        client, _ = client_and_db
        res = client.get("/aeroplanes/empty-aero/component-tree")
        assert res.status_code == 200
        assert res.json()["root_nodes"] == []
        assert res.json()["total_nodes"] == 0

    def test_add_root_group_node(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/aeroplanes/a1/component-tree", json={
            "node_type": "group", "name": "eHawk",
        })
        assert res.status_code == 201
        assert res.json()["node_type"] == "group"
        assert res.json()["parent_id"] is None

    def test_add_child_node(self, client_and_db):
        client, _ = client_and_db
        parent = client.post("/aeroplanes/a2/component-tree", json={
            "node_type": "group", "name": "main_wing",
        }).json()
        child = client.post("/aeroplanes/a2/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "segment 0",
            "shape_key": "seg0_shell",
        }).json()
        assert child["parent_id"] == parent["id"]

    def test_add_cots_node(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "TreeServo", "component_type": "servo",
            "mass_g": 14.0, "specs": {},
        }).json()
        node = client.post("/aeroplanes/a3/component-tree", json={
            "node_type": "cots", "name": "Servo",
            "component_id": comp["id"], "quantity": 2,
        }).json()
        assert node["component_id"] == comp["id"]
        assert node["quantity"] == 2

    def test_get_tree_nested(self, client_and_db):
        client, _ = client_and_db
        root = client.post("/aeroplanes/a4/component-tree", json={
            "node_type": "group", "name": "root",
        }).json()
        client.post("/aeroplanes/a4/component-tree", json={
            "parent_id": root["id"],
            "node_type": "group", "name": "wing",
        })
        tree = client.get("/aeroplanes/a4/component-tree").json()
        assert tree["total_nodes"] == 2
        assert tree["root_nodes"][0]["children"][0]["name"] == "wing"

    def test_update_node(self, client_and_db):
        client, _ = client_and_db
        node = client.post("/aeroplanes/a5/component-tree", json={
            "node_type": "group", "name": "old",
        }).json()
        res = client.put(f"/aeroplanes/a5/component-tree/{node['id']}", json={
            "node_type": "group", "name": "new",
        })
        assert res.status_code == 200
        assert res.json()["name"] == "new"

    def test_delete_node(self, client_and_db):
        client, _ = client_and_db
        node = client.post("/aeroplanes/a6/component-tree", json={
            "node_type": "group", "name": "delete_me",
        }).json()
        res = client.delete(f"/aeroplanes/a6/component-tree/{node['id']}")
        assert res.status_code == 204

    def test_delete_synced_node_rejected(self, client_and_db):
        client, session_factory = client_and_db
        db = session_factory()
        node = ComponentTreeNodeModel(
            aeroplane_id="a7", node_type="group", name="synced",
            synced_from="wing:main_wing",
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        res = client.delete(f"/aeroplanes/a7/component-tree/{node.id}")
        assert res.status_code == 422
        db.close()


class TestMoveNode:

    def test_move_node(self, client_and_db):
        client, _ = client_and_db
        p1 = client.post("/aeroplanes/m1/component-tree", json={
            "node_type": "group", "name": "p1",
        }).json()
        p2 = client.post("/aeroplanes/m1/component-tree", json={
            "node_type": "group", "name": "p2",
        }).json()
        child = client.post("/aeroplanes/m1/component-tree", json={
            "parent_id": p1["id"], "node_type": "group", "name": "child",
        }).json()
        res = client.post(f"/aeroplanes/m1/component-tree/{child['id']}/move", json={
            "new_parent_id": p2["id"], "sort_index": 0,
        })
        assert res.json()["parent_id"] == p2["id"]


class TestWeightCalculation:

    def test_cots_weight(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "WtMotor", "component_type": "brushless_motor",
            "mass_g": 50.0,
            # brushless_motor seed schema requires kv_rpm_per_volt (gh#83)
            "specs": {"kv_rpm_per_volt": 900},
        }).json()
        node = client.post("/aeroplanes/w1/component-tree", json={
            "node_type": "cots", "name": "motor",
            "component_id": comp["id"],
        }).json()
        wt = client.get(f"/aeroplanes/w1/component-tree/{node['id']}/weight").json()
        assert wt["own_weight_g"] == 50.0
        assert wt["source"] == "cots"

    def test_override_weight(self, client_and_db):
        client, _ = client_and_db
        node = client.post("/aeroplanes/w2/component-tree", json={
            "node_type": "cad_shape", "name": "shell",
            "weight_override_g": 25.5,
        }).json()
        wt = client.get(f"/aeroplanes/w2/component-tree/{node['id']}/weight").json()
        assert wt["own_weight_g"] == 25.5
        assert wt["source"] == "override"

    def test_recursive_weight(self, client_and_db):
        client, _ = client_and_db
        parent = client.post("/aeroplanes/w3/component-tree", json={
            "node_type": "group", "name": "assembly",
        }).json()
        client.post("/aeroplanes/w3/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "a", "weight_override_g": 10.0,
        })
        client.post("/aeroplanes/w3/component-tree", json={
            "parent_id": parent["id"],
            "node_type": "cad_shape", "name": "b", "weight_override_g": 20.0,
        })
        wt = client.get(f"/aeroplanes/w3/component-tree/{parent['id']}/weight").json()
        assert wt["children_weight_g"] == 30.0
        assert wt["total_weight_g"] == 30.0

    def test_calculated_volume_weight(self, client_and_db):
        client, _ = client_and_db
        mat = client.post("/components", json={
            "name": "PLA", "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        }).json()
        node = client.post("/aeroplanes/w4/component-tree", json={
            "node_type": "cad_shape", "name": "wing_shell",
            "volume_mm3": 10000, "material_id": mat["id"],
            "print_type": "volume", "scale_factor": 1.0,
        }).json()
        wt = client.get(f"/aeroplanes/w4/component-tree/{node['id']}/weight").json()
        assert wt["source"] == "calculated"
        assert abs(wt["own_weight_g"] - 12.4) < 0.1
