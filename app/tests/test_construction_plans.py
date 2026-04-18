"""Tests for Construction Plans CRUD + Creator Catalog + Execute (gh#101).

Covers sub-tickets #109 (DB model), #110 (CRUD), #111 (creators), #112 (execute).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


SAMPLE_TREE = {
    "$TYPE": "ConstructionRootNode",
    "creator_id": "test_root",
    "successors": {},
}

TREE_3_STEPS = {
    "$TYPE": "ConstructionRootNode",
    "creator_id": "root",
    "successors": {
        "step_a": {
            "$TYPE": "ConstructionStepNode",
            "creator": {"$TYPE": "Fuse2ShapesCreator", "creator_id": "step_a"},
            "successors": {
                "step_b": {
                    "$TYPE": "ConstructionStepNode",
                    "creator": {"$TYPE": "Fuse2ShapesCreator", "creator_id": "step_b"},
                    "successors": {},
                }
            },
        },
        "step_c": {
            "$TYPE": "ConstructionStepNode",
            "creator": {"$TYPE": "ExportToStepCreator", "creator_id": "step_c"},
            "successors": {},
        },
    },
}


def _create_plan(
    client: TestClient,
    name: str,
    tree: dict = None,
    plan_type: str = "template",
    aeroplane_id: str | None = None,
) -> dict:
    body: dict = {"name": name, "tree_json": tree or SAMPLE_TREE, "plan_type": plan_type}
    if aeroplane_id:
        body["aeroplane_id"] = aeroplane_id
    resp = client.post("/construction-plans", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── CRUD Tests (#110) ───────────────────────────────────────────


class TestConstructionPlansCRUD:
    def test_create_plan(self, client):
        """POST → 201 with id."""
        plan = _create_plan(client, "Build A")
        assert plan["id"] is not None
        assert plan["name"] == "Build A"
        assert plan["tree_json"] == SAMPLE_TREE

    def test_list_plans(self, client):
        """GET → list with all plans."""
        _create_plan(client, "Plan A")
        _create_plan(client, "Plan B")
        resp = client.get("/construction-plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 2

    def test_list_plans_includes_step_count(self, client):
        """GET list → step_count correctly computed from tree."""
        _create_plan(client, "ThreeSteps", TREE_3_STEPS)
        plans = client.get("/construction-plans").json()
        plan = next(p for p in plans if p["name"] == "ThreeSteps")
        assert plan["step_count"] == 3

    def test_get_plan_by_id(self, client):
        """GET /{id} → full tree_json."""
        plan = _create_plan(client, "Detail")
        resp = client.get(f"/construction-plans/{plan['id']}")
        assert resp.status_code == 200
        assert resp.json()["tree_json"] == SAMPLE_TREE

    def test_update_plan(self, client):
        """PUT → name + tree_json updated."""
        plan = _create_plan(client, "Original")
        updated_tree = {**SAMPLE_TREE, "creator_id": "updated_root"}
        resp = client.put(
            f"/construction-plans/{plan['id']}",
            json={"name": "Updated", "tree_json": updated_tree},
        )
        assert resp.status_code == 200
        reloaded = client.get(f"/construction-plans/{plan['id']}").json()
        assert reloaded["name"] == "Updated"
        assert reloaded["tree_json"]["creator_id"] == "updated_root"

    def test_delete_plan(self, client):
        """DELETE → 204, then GET → 404."""
        plan = _create_plan(client, "ToDelete")
        resp = client.delete(f"/construction-plans/{plan['id']}")
        assert resp.status_code == 204
        assert client.get(f"/construction-plans/{plan['id']}").status_code == 404

    def test_get_nonexistent_plan(self, client):
        """GET /999 → 404."""
        assert client.get("/construction-plans/999").status_code == 404

    def test_create_without_name_fails(self, client):
        """POST without name → 422."""
        resp = client.post("/construction-plans", json={"tree_json": SAMPLE_TREE})
        assert resp.status_code == 422

    def test_create_without_type_fails(self, client):
        """POST with tree_json missing $TYPE → 422."""
        resp = client.post(
            "/construction-plans",
            json={"name": "bad", "tree_json": {"creator_id": "x"}},
        )
        assert resp.status_code == 422

    def test_duplicate_name_allowed(self, client):
        """Two plans with same name → both 201."""
        _create_plan(client, "Same")
        resp = client.post(
            "/construction-plans",
            json={"name": "Same", "tree_json": SAMPLE_TREE},
        )
        assert resp.status_code == 201


# ── Creator Catalog Tests (#111) ────────────────────────────────


class TestCreatorCatalog:
    def test_list_creators_returns_many(self, client):
        """GET /creators → at least 20 creators."""
        resp = client.get("/construction-plans/creators")
        assert resp.status_code == 200
        creators = resp.json()
        assert len(creators) >= 20

    def test_known_creators_present(self, client):
        """Key creators are in the list."""
        creators = client.get("/construction-plans/creators").json()
        names = {c["class_name"] for c in creators}
        assert "VaseModeWingCreator" in names
        assert "ExportToStepCreator" in names
        assert "Fuse2ShapesCreator" in names
        assert "FuselageShellShapeCreator" in names

    def test_creator_has_parameters(self, client):
        """VaseModeWingCreator has expected parameters."""
        creators = client.get("/construction-plans/creators").json()
        vase = next(c for c in creators if c["class_name"] == "VaseModeWingCreator")
        param_names = {p["name"] for p in vase["parameters"]}
        assert "wing_index" in param_names
        assert "leading_edge_offset_factor" in param_names
        assert "creator_id" not in param_names  # internal, filtered out

    def test_creator_categories(self, client):
        """All 5 categories present."""
        creators = client.get("/construction-plans/creators").json()
        categories = {c["category"] for c in creators}
        assert categories >= {"wing", "fuselage", "cad_operations", "export_import", "components"}

    def test_excludes_internal_params(self, client):
        """Internal and runtime-injected params not in parameters."""
        for c in client.get("/construction-plans/creators").json():
            param_names = {p["name"] for p in c["parameters"]}
            for internal in ("self", "loglevel", "creator_id", "wing_config",
                             "printer_settings", "servo_information",
                             "engine_information", "component_information"):
                assert internal not in param_names, f"{c['class_name']} exposes {internal}"

    def test_excludes_infrastructure_classes(self, client):
        """ConstructionRootNode, ConstructionStepNode, JSONStepNode not listed."""
        creators = client.get("/construction-plans/creators").json()
        names = {c["class_name"] for c in creators}
        assert "ConstructionRootNode" not in names
        assert "ConstructionStepNode" not in names
        assert "JSONStepNode" not in names


# ── Execute Tests (#112) ────────────────────────────────────────


class TestPlanExecution:
    def test_execute_nonexistent_plan(self, client):
        """POST execute on plan 999 → 404."""
        resp = client.post(
            "/construction-plans/999/execute",
            json={"aeroplane_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_execute_nonexistent_aeroplane(self, client):
        """POST execute with unknown aeroplane → 404."""
        plan = _create_plan(client, "exec_404", plan_type="plan")
        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404

    def test_execute_template_rejected(self, client):
        """POST execute on a template → 422."""
        plan = _create_plan(client, "tmpl_no_exec", plan_type="template")
        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 422

    def test_execute_plan_with_invalid_creator_returns_error(self, client):
        """Plan with unknown creator type → decode error → 422."""
        bad_tree = {
            "$TYPE": "ConstructionRootNode",
            "creator_id": "root",
            "successors": {
                "bad": {
                    "$TYPE": "NonExistentCreator",
                    "creator_id": "bad",
                    "successors": {},
                }
            },
        }
        plan = _create_plan(client, "bad_plan", bad_tree, plan_type="plan")
        # Need an aeroplane
        resp = client.post("/aeroplanes", params={"name": "exec_test"})
        assert resp.status_code == 201
        aid = resp.json()["id"]

        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": aid},
        )
        assert resp.status_code == 422


# ── Template / Plan Duality Tests (#126) ───────────────────────


def _create_aeroplane(client: TestClient, name: str = "test_plane") -> str:
    """Create an aeroplane and return its ID."""
    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestTemplatePlanDuality:
    def test_list_templates_only(self, client):
        """GET /construction-templates returns only templates."""
        _create_plan(client, "Tmpl A", plan_type="template")
        aid = _create_aeroplane(client)
        _create_plan(client, "Plan A", plan_type="plan", aeroplane_id=aid)
        resp = client.get("/construction-templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert all(t["plan_type"] == "template" for t in templates)
        names = {t["name"] for t in templates}
        assert "Tmpl A" in names
        assert "Plan A" not in names

    def test_create_template_via_templates_endpoint(self, client):
        """POST /construction-templates forces plan_type=template."""
        resp = client.post(
            "/construction-templates",
            json={
                "name": "Forced Template",
                "tree_json": SAMPLE_TREE,
                "plan_type": "plan",  # should be overridden
            },
        )
        assert resp.status_code == 201
        assert resp.json()["plan_type"] == "template"
        assert resp.json()["aeroplane_id"] is None

    def test_list_plans_filter_by_type(self, client):
        """GET /construction-plans?plan_type=template filters correctly."""
        _create_plan(client, "FilterTmpl", plan_type="template")
        aid = _create_aeroplane(client)
        _create_plan(client, "FilterPlan", plan_type="plan", aeroplane_id=aid)
        resp = client.get("/construction-plans", params={"plan_type": "template"})
        assert resp.status_code == 200
        assert all(p["plan_type"] == "template" for p in resp.json())

    def test_instantiate_template(self, client):
        """POST from-template creates a plan bound to aeroplane."""
        tmpl = _create_plan(client, "Base Template")
        aid = _create_aeroplane(client)
        resp = client.post(
            f"/aeroplanes/{aid}/construction-plans/from-template/{tmpl['id']}",
        )
        assert resp.status_code == 201
        plan = resp.json()
        assert plan["plan_type"] == "plan"
        assert plan["aeroplane_id"] == aid
        assert plan["tree_json"] == SAMPLE_TREE

    def test_instantiate_template_custom_name(self, client):
        """Instantiate with custom name override."""
        tmpl = _create_plan(client, "Named Template")
        aid = _create_aeroplane(client)
        resp = client.post(
            f"/aeroplanes/{aid}/construction-plans/from-template/{tmpl['id']}",
            json={"name": "Custom Plan Name"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Custom Plan Name"

    def test_instantiate_non_template_rejected(self, client):
        """Instantiating a plan (not template) returns 422."""
        aid = _create_aeroplane(client)
        plan = _create_plan(client, "A Plan", plan_type="plan", aeroplane_id=aid)
        resp = client.post(
            f"/aeroplanes/{aid}/construction-plans/from-template/{plan['id']}",
        )
        assert resp.status_code == 422

    def test_plan_to_template(self, client):
        """POST to-template creates a template from a plan."""
        aid = _create_aeroplane(client)
        plan = _create_plan(client, "My Plan", plan_type="plan", aeroplane_id=aid)
        resp = client.post(
            f"/aeroplanes/{aid}/construction-plans/{plan['id']}/to-template",
        )
        assert resp.status_code == 201
        tmpl = resp.json()
        assert tmpl["plan_type"] == "template"
        assert tmpl["aeroplane_id"] is None
        assert tmpl["tree_json"] == SAMPLE_TREE

    def test_plan_to_template_custom_name(self, client):
        """to-template with custom name override."""
        aid = _create_aeroplane(client)
        plan = _create_plan(client, "Source", plan_type="plan", aeroplane_id=aid)
        resp = client.post(
            f"/aeroplanes/{aid}/construction-plans/{plan['id']}/to-template",
            json={"name": "My Custom Template"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Custom Template"

    def test_list_aeroplane_plans(self, client):
        """GET /aeroplanes/{id}/construction-plans returns plans for that aeroplane."""
        aid1 = _create_aeroplane(client, "plane1")
        aid2 = _create_aeroplane(client, "plane2")
        _create_plan(client, "P1", plan_type="plan", aeroplane_id=aid1)
        _create_plan(client, "P2", plan_type="plan", aeroplane_id=aid2)
        resp = client.get(f"/aeroplanes/{aid1}/construction-plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert all(p["aeroplane_id"] == aid1 for p in plans)
        names = {p["name"] for p in plans}
        assert "P1" in names
        assert "P2" not in names

    def test_plan_summary_includes_plan_type(self, client):
        """PlanSummary includes plan_type and aeroplane_id."""
        aid = _create_aeroplane(client)
        _create_plan(client, "Typed Plan", plan_type="plan", aeroplane_id=aid)
        resp = client.get("/construction-plans")
        assert resp.status_code == 200
        plan = next(p for p in resp.json() if p["name"] == "Typed Plan")
        assert plan["plan_type"] == "plan"
        assert plan["aeroplane_id"] == aid


# ── Printer Settings Seed (#115) ────────────────────────────────


class TestPrinterSettingsSeed:
    def test_printer_settings_type_seeded(self, client):
        """GET /component-types contains printer_settings with 3 properties."""
        resp = client.get("/component-types")
        assert resp.status_code == 200
        types = resp.json()
        ps = next((t for t in types if t["name"] == "printer_settings"), None)
        assert ps is not None
        assert len(ps["schema"]) == 3
        prop_names = {p["name"] for p in ps["schema"]}
        assert prop_names == {"layer_height", "wall_thickness", "rel_gap_wall_thickness"}
