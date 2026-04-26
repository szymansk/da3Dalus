"""Tests for Construction Plans CRUD + Creator Catalog + Execute (gh#101).

Covers sub-tickets #109 (DB model), #110 (CRUD), #111 (creators), #112 (execute).
Also: #315 (frontend JSON ↔ backend decoder compatibility).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _can_import_cad() -> bool:
    """Check if cadquery/cad_designer is available (excluded on linux/aarch64)."""
    try:
        from cad_designer.airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder  # noqa: F401

        return True
    except (ImportError, ModuleNotFoundError):
        return False


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
            for internal in (
                "self",
                "loglevel",
                "creator_id",
                "wing_config",
                "printer_settings",
                "servo_information",
                "engine_information",
                "component_information",
            ):
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


# ── Frontend JSON → Backend Decoder Tests (#315) ─────────────────


# This is the exact JSON structure that the frontend's toBackendTree()
# produces. It must be accepted by GeneralJSONDecoder without error.
FRONTEND_GENERATED_TREE = {
    "$TYPE": "ConstructionRootNode",
    "creator_id": "eHawk-wing",
    "loglevel": 50,
    "successors": {
        "fuse1": {
            "$TYPE": "ConstructionStepNode",
            "creator_id": "fuse1",
            "loglevel": 50,
            "creator": {
                "$TYPE": "Fuse2ShapesCreator",
                "creator_id": "fuse1",
                "shape_a": "wing_left",
                "shape_b": "wing_right",
                "loglevel": 20,
            },
            "successors": {},
        },
    },
}


class TestFrontendJsonDecoderCompat:
    """Verify that JSON produced by the frontend's toBackendTree() is
    accepted by GeneralJSONDecoder — the exact chain that broke in #310."""

    @pytest.mark.skipif(
        not _can_import_cad(),
        reason="cadquery / cad_designer not available on this platform",
    )
    def test_decoder_accepts_frontend_json(self):
        """GeneralJSONDecoder can deserialize a frontend-produced plan
        into a ConstructionRootNode with the correct creator."""
        import json
        from cad_designer.airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder
        from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
        from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode

        json_string = json.dumps(FRONTEND_GENERATED_TREE)
        root = json.loads(
            json_string,
            cls=GeneralJSONDecoder,
            wing_config={},
            printer_settings={},
            servo_information={},
            engine_information=None,
            component_information=None,
        )

        # Root is a ConstructionRootNode
        assert isinstance(root, ConstructionRootNode)
        # Has one successor
        assert len(root.successors) == 1
        # Successor is a ConstructionStepNode
        step = root.successors["fuse1"]
        assert isinstance(step, ConstructionStepNode)
        # Step wraps the correct creator
        assert step.creator.__class__.__name__ == "Fuse2ShapesCreator"
        assert step.creator.shape_a == "wing_left"
        assert step.creator.shape_b == "wing_right"

    @pytest.mark.skipif(
        not _can_import_cad(),
        reason="cadquery / cad_designer not available on this platform",
    )
    def test_decoder_accepts_nested_frontend_json(self):
        """Nested successors from frontend are correctly deserialized."""
        import json
        from cad_designer.airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder
        from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode

        nested_tree = {
            "$TYPE": "ConstructionRootNode",
            "creator_id": "root",
            "loglevel": 50,
            "successors": {
                "fuse1": {
                    "$TYPE": "ConstructionStepNode",
                    "creator_id": "fuse1",
                    "loglevel": 50,
                    "creator": {
                        "$TYPE": "Fuse2ShapesCreator",
                        "creator_id": "fuse1",
                        "shape_a": "a",
                        "shape_b": "b",
                        "loglevel": 50,
                    },
                    "successors": {
                        "fuse2": {
                            "$TYPE": "ConstructionStepNode",
                            "creator_id": "fuse2",
                            "loglevel": 50,
                            "creator": {
                                "$TYPE": "Fuse2ShapesCreator",
                                "creator_id": "fuse2",
                                "shape_a": "c",
                                "shape_b": "d",
                                "loglevel": 50,
                            },
                            "successors": {},
                        },
                    },
                },
            },
        }

        json_string = json.dumps(nested_tree)
        root = json.loads(
            json_string,
            cls=GeneralJSONDecoder,
            wing_config={},
            printer_settings={},
            servo_information={},
            engine_information=None,
            component_information=None,
        )

        assert isinstance(root, ConstructionRootNode)
        step1 = root.successors["fuse1"]
        assert step1.creator.shape_a == "a"
        step2 = step1.successors["fuse2"]
        assert step2.creator.shape_a == "c"
        assert step2.creator.shape_b == "d"


class TestFrontendJsonIntegration:
    """Integration test: create a plan with frontend-format JSON via the
    REST API, then execute it. This is the full chain that was broken."""

    def test_create_and_execute_frontend_format_plan(self, client):
        """POST plan with frontend JSON → execute → no decoder error."""
        # Create aeroplane (needed for execution)
        aid = _create_aeroplane(client)

        # Create plan with exact frontend-produced JSON
        plan = _create_plan(
            client,
            "frontend-format-test",
            tree=FRONTEND_GENERATED_TREE,
            plan_type="plan",
            aeroplane_id=aid,
        )

        # Execute — this is where #310 crashed with 'list has no attribute get'
        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": aid},
        )
        # We expect 200 (success or soft error from missing shapes),
        # NOT 422 (decoder failure)
        assert resp.status_code == 200, (
            f"Execute returned {resp.status_code}: {resp.text}. "
            "If 422, the frontend JSON format is not accepted by GeneralJSONDecoder."
        )
        result = resp.json()
        # The plan should decode successfully — even if execution
        # fails (missing input shapes), it's a runtime error not a decode error
        assert result["status"] in ("success", "error")
        if result["status"] == "error":
            assert "'list' object has no attribute 'get'" not in result["error"], (
                "The original #310 bug is still present — frontend JSON has wrong structure"
            )
            assert "Failed to decode" not in result["error"], (
                "GeneralJSONDecoder rejected the frontend JSON format"
            )

    def test_roundtrip_store_and_retrieve_preserves_structure(self, client):
        """Plan stored with frontend JSON can be retrieved with identical structure."""
        plan = _create_plan(
            client,
            "roundtrip-test",
            tree=FRONTEND_GENERATED_TREE,
        )
        resp = client.get(f"/construction-plans/{plan['id']}")
        assert resp.status_code == 200
        stored = resp.json()["tree_json"]

        # Verify the structure survived the DB round-trip
        assert stored["$TYPE"] == "ConstructionRootNode"
        assert stored["loglevel"] == 50
        assert isinstance(stored["successors"], dict)
        step = stored["successors"]["fuse1"]
        assert step["$TYPE"] == "ConstructionStepNode"
        assert step["creator"]["$TYPE"] == "Fuse2ShapesCreator"
        assert step["creator"]["shape_a"] == "wing_left"


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


# ── Zip download (gh#339) ───────────────────────────────────────


class TestZipDownload:
    """GH#339 — zip download endpoint for an execution dir."""

    def test_zip_endpoint_returns_zip_with_all_files(self, client, tmp_path, monkeypatch):
        from app.core.config import settings
        from app.services import artifact_service

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        execution_id, exec_dir = artifact_service.create_execution_dir("aero-zipper", 501)
        (exec_dir / "alpha.stl").write_bytes(b"AAA")
        (exec_dir / "beta.txt").write_text("bb")

        resp = client.get(f"/construction-plans/501/artifacts/{execution_id}/zip")

        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers.get("content-disposition", "")

        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert sorted(zf.namelist()) == ["alpha.stl", "beta.txt"]

    def test_zip_endpoint_404_for_missing_execution(self, client, tmp_path, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        tmp_path.mkdir(exist_ok=True)

        resp = client.get("/construction-plans/9999/artifacts/missing/zip")
        assert resp.status_code == 404

    def test_zip_endpoint_returns_empty_zip_for_empty_execution(
        self, client, tmp_path, monkeypatch
    ):
        from app.core.config import settings
        from app.services import artifact_service

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        execution_id, _ = artifact_service.create_execution_dir("aero-empty", 502)

        resp = client.get(f"/construction-plans/502/artifacts/{execution_id}/zip")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert zf.namelist() == []


# ── Template execution (gh#339) ─────────────────────────────────


class TestTemplateExecution:
    """GH#339 — templates can be executed against a chosen aeroplane."""

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_execute_template_returns_success(self, client, client_and_db, tmp_path, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-tpl-exec")
            aero_id = str(aero.uuid)

        # Create a template (plan_type defaults to "template" in helper)
        template = _create_plan(client, "Tpl A", tree=SAMPLE_TREE, plan_type="template")

        resp = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # decode may fail (no real Creator) but status code must not be 422
        assert body["status"] in ("success", "error"), body

    def test_execute_template_without_aeroplane_id_returns_422(self, client):
        template = _create_plan(client, "Tpl B", tree=SAMPLE_TREE, plan_type="template")

        resp = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={},
        )

        assert resp.status_code == 422
        assert "aeroplane_id" in resp.json()["detail"].lower()

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_template_execution_replaces_previous_run(
        self, client, client_and_db, tmp_path, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-replace")
            aero_id = str(aero.uuid)

        template = _create_plan(client, "Tpl C", tree=SAMPLE_TREE, plan_type="template")

        # First execute
        resp1 = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp1.status_code == 200
        first_exec_id = resp1.json()["execution_id"]

        # Second execute
        resp2 = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp2.status_code == 200
        second_exec_id = resp2.json()["execution_id"]

        assert first_exec_id != second_exec_id
        # First execution dir is gone
        first_dir = tmp_path / "_template_runs" / str(template["id"]) / first_exec_id
        assert not first_dir.exists()
        # Second execution dir exists
        second_dir = tmp_path / "_template_runs" / str(template["id"]) / second_exec_id
        assert second_dir.is_dir()


class TestPlanExecutionPathRegression:
    """Plan executions still write to <aero>/<plan>/<exec> (gh#339)."""

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_plan_execution_path_unchanged(self, client, client_and_db, tmp_path, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-plan")
            aero_id = str(aero.uuid)

        plan = _create_plan(
            client,
            "Real Plan",
            tree=SAMPLE_TREE,
            plan_type="plan",
            aeroplane_id=aero_id,
        )

        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp.status_code == 200
        exec_id = resp.json()["execution_id"]

        # Plan dir under aeroplane root, NOT under _template_runs
        plan_dir = tmp_path / aero_id / str(plan["id"]) / exec_id
        assert plan_dir.is_dir()
        assert not (tmp_path / "_template_runs" / str(plan["id"])).exists()
