"""Tests for app.services.copilot_tools — curated copilot tool facade (gh-917).

All heavy analysis services are mocked so these run fast with no real
aerosandbox/network call.  The hub is never reached.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import app.services.copilot_tools as tools_module
from app.services.copilot_tools import execute, list_schemas
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(client_and_db):
    _, SessionLocal = client_and_db
    return SessionLocal()


# ---------------------------------------------------------------------------
# list_schemas
# ---------------------------------------------------------------------------


class TestListSchemas:
    def test_returns_five_schemas(self):
        schemas = list_schemas()
        assert len(schemas) == 5

    def test_schema_names(self):
        names = {s["function"]["name"] for s in list_schemas()}
        # Slice 1 tools + Slice 2 write tools (gh-937/938)
        assert names == {
            "get_design_snapshot",
            "run_analysis",
            "get_version_tree",
            "apply_design_edits",
            "discard_proposal",
        }

    def test_each_schema_has_required_keys(self):
        for s in list_schemas():
            assert s["type"] == "function"
            fn = s["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_run_analysis_schema_has_kind_param(self):
        schema = next(
            s for s in list_schemas() if s["function"]["name"] == "run_analysis"
        )
        props = schema["function"]["parameters"]["properties"]
        assert "kind" in props
        assert props["kind"]["enum"] == ["polar", "stability"]


# ---------------------------------------------------------------------------
# execute — unknown tool
# ---------------------------------------------------------------------------


class TestExecuteUnknownTool:
    def test_returns_error_dict_for_unknown_tool(self, client_and_db):
        db = _make_db(client_and_db)
        try:
            result = execute("nonexistent_tool", db, aeroplane_id=1)
            assert "error" in result
            assert "nonexistent_tool" in result["error"]
        finally:
            db.close()

    def test_error_message_lists_known_tools(self, client_and_db):
        db = _make_db(client_and_db)
        try:
            result = execute("bad_tool", db, aeroplane_id=1)
            error_msg = result["error"]
            assert "get_design_snapshot" in error_msg
            assert "run_analysis" in error_msg
            assert "get_version_tree" in error_msg
        finally:
            db.close()


# ---------------------------------------------------------------------------
# get_design_snapshot
# ---------------------------------------------------------------------------


class TestGetDesignSnapshot:
    def test_returns_dict_for_known_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_design_snapshot", db, aeroplane_id=plane.id)
        assert isinstance(result, dict)
        assert "error" not in result

    def test_contains_basic_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="snapshot-plane")
            result = execute("get_design_snapshot", db, aeroplane_id=plane.id)
        assert result["id"] == plane.id
        assert result["name"] == "snapshot-plane"

    def test_returns_error_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = execute("get_design_snapshot", db, aeroplane_id=999999)
        assert "error" in result

    def test_returns_uuid_as_string(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_design_snapshot", db, aeroplane_id=plane.id)
        assert isinstance(result.get("uuid"), str)

    def test_wing_count_field_present(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_design_snapshot", db, aeroplane_id=plane.id)
        assert "wing_count" in result

    def test_wings_field_with_n_xsecs(self, client_and_db):
        """gh-938 Bug A: snapshot must return 'wings' list with n_xsecs per wing."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_design_snapshot", db, aeroplane_id=plane.id)
        # 'wings' key must be present (even if empty for a bare aeroplane)
        assert "wings" in result, "'wings' key missing from snapshot"
        assert isinstance(result["wings"], list)
        # Each entry must have 'name' and 'n_xsecs'
        for entry in result["wings"]:
            assert "name" in entry
            assert "n_xsecs" in entry
            assert isinstance(entry["n_xsecs"], int)


# ---------------------------------------------------------------------------
# run_analysis — unknown kind
# ---------------------------------------------------------------------------


class TestRunAnalysisUnknownKind:
    def test_returns_error_for_bad_kind(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("run_analysis", db, aeroplane_id=plane.id, kind="avl_full")
        assert "error" in result
        assert "avl_full" in result["error"]

    def test_returns_error_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = execute("run_analysis", db, aeroplane_id=999999, kind="polar")
        assert "error" in result


# ---------------------------------------------------------------------------
# run_analysis — timeout path
# ---------------------------------------------------------------------------


class TestRunAnalysisTimeout:
    def test_polar_timeout_returns_status_dict(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)

            original_timeout = tools_module.DEFAULT_ANALYSIS_TIMEOUT_S
            tools_module.DEFAULT_ANALYSIS_TIMEOUT_S = 0.001  # near-zero → always times out

            async def _slow_polar(*args, **kwargs):
                await asyncio.sleep(10)
                return {}

            try:
                with patch.object(tools_module, "_run_polar_async", _slow_polar):
                    result = execute("run_analysis", db, aeroplane_id=plane.id, kind="polar")
            finally:
                tools_module.DEFAULT_ANALYSIS_TIMEOUT_S = original_timeout

        assert result.get("status") == "timeout"
        assert "note" in result

    def test_stability_timeout_returns_status_dict(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)

            original_timeout = tools_module.DEFAULT_ANALYSIS_TIMEOUT_S
            tools_module.DEFAULT_ANALYSIS_TIMEOUT_S = 0.001

            async def _slow_stability(*args, **kwargs):
                await asyncio.sleep(10)
                return {}

            try:
                with patch.object(tools_module, "_run_stability_async", _slow_stability):
                    result = execute("run_analysis", db, aeroplane_id=plane.id, kind="stability")
            finally:
                tools_module.DEFAULT_ANALYSIS_TIMEOUT_S = original_timeout

        assert result.get("status") == "timeout"
        assert "note" in result


# ---------------------------------------------------------------------------
# run_analysis — mocked happy-path (polar)
# ---------------------------------------------------------------------------


class TestRunAnalysisPolarMocked:
    def test_polar_returns_ok_shape(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)

            expected = {
                "status": "ok",
                "kind": "polar",
                "cl_max": 1.4,
                "cl_min": -0.3,
                "cd_min": 0.02,
                "cl_cd_max": 18.5,
            }

            async def _mock_polar(*args, **kwargs):
                return expected

            with patch.object(tools_module, "_run_polar_async", _mock_polar):
                result = execute("run_analysis", db, aeroplane_id=plane.id, kind="polar")

        assert result["status"] == "ok"
        assert result["kind"] == "polar"
        assert "cl_max" in result
        assert "cl_cd_max" in result

    def test_polar_values_are_finite_floats(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)

            async def _mock_polar(*args, **kwargs):
                return {
                    "status": "ok",
                    "kind": "polar",
                    "cl_max": 1.4,
                    "cd_min": 0.025,
                    "cl_cd_max": 16.0,
                }

            with patch.object(tools_module, "_run_polar_async", _mock_polar):
                result = execute("run_analysis", db, aeroplane_id=plane.id, kind="polar")

        for key in ("cl_max", "cd_min", "cl_cd_max"):
            assert isinstance(result[key], float)
            assert result[key] == result[key]  # not NaN


# ---------------------------------------------------------------------------
# run_analysis — mocked happy-path (stability)
# ---------------------------------------------------------------------------


class TestRunAnalysisStabilityMocked:
    def test_stability_returns_ok_shape(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)

            expected = {
                "status": "ok",
                "kind": "stability",
                "static_margin_pct": 12.3,
                "stability_class": "stable",
                "is_statically_stable": True,
                "neutral_point_x_m": 0.45,
                "mac_m": 0.25,
                "Cma": -0.8,
                "Cnb": 0.12,
                "Clb": -0.09,
                "is_directionally_stable": True,
                "is_laterally_stable": True,
                "cg_x_m": 0.40,
                "cg_range_forward_m": 0.35,
                "cg_range_aft_m": 0.48,
            }

            async def _mock_stability(*args, **kwargs):
                return expected

            with patch.object(tools_module, "_run_stability_async", _mock_stability):
                result = execute("run_analysis", db, aeroplane_id=plane.id, kind="stability")

        assert result["status"] == "ok"
        assert result["kind"] == "stability"
        assert "static_margin_pct" in result
        assert "stability_class" in result
        assert "is_statically_stable" in result


# ---------------------------------------------------------------------------
# get_version_tree
# ---------------------------------------------------------------------------


class TestGetVersionTree:
    def test_returns_dict_with_required_keys(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_version_tree", db, aeroplane_id=plane.id)
        assert isinstance(result, dict)
        assert "error" not in result
        assert "root_id" in result
        assert "nodes" in result
        assert "branches" in result

    def test_nodes_is_list(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_version_tree", db, aeroplane_id=plane.id)
        assert isinstance(result["nodes"], list)

    def test_branches_is_list(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_version_tree", db, aeroplane_id=plane.id)
        assert isinstance(result["branches"], list)

    def test_node_has_expected_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_version_tree", db, aeroplane_id=plane.id)
        # For a plain (non-versioned) aeroplane the node list contains just itself
        if result["nodes"]:
            node = result["nodes"][0]
            for field_name in ("id", "uuid", "name", "is_immutable"):
                assert field_name in node, f"Missing field: {field_name}"

    def test_returns_error_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = execute("get_version_tree", db, aeroplane_id=999999)
        assert "error" in result

    def test_result_is_json_serializable(self, client_and_db):
        import json

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            result = execute("get_version_tree", db, aeroplane_id=plane.id)
        # This must not raise
        serialized = json.dumps(result)
        assert serialized


# ---------------------------------------------------------------------------
# Tool registry structure
# ---------------------------------------------------------------------------


class TestDragBreakdown:
    """Deterministic induced/parasitic split (gh-925) — the LLM is unreliable
    at this arithmetic, so the tool computes it.
    """

    def test_split_is_correct_for_ehawk_best_glide(self):
        from app.services.copilot_tools import _drag_breakdown

        # eHawk best-glide point from the real polar (the case the LLM got
        # wrong by 10x): CL 0.552, CD 0.02302, AR 11.3, e 0.7916.
        bd = _drag_breakdown(cl=0.552, cd_total=0.02302, ar=11.3, e=0.7916)
        assert bd is not None and "note" not in bd
        # CD_i = 0.552^2 / (pi * 11.3 * 0.7916) ≈ 0.01084 (NOT 0.00108)
        assert bd["cd_induced"] == pytest.approx(0.01084, abs=2e-4)
        assert bd["cd_parasite"] == pytest.approx(0.02302 - 0.01084, abs=2e-4)
        # induced is ~47% of total — well above the ~5% the model hallucinated
        assert bd["induced_fraction"] == pytest.approx(0.47, abs=0.03)
        # components are physical
        assert 0 < bd["cd_induced"] < bd["cd_total"]
        assert 0 < bd["cd_parasite"] < bd["cd_total"]

    def test_components_sum_to_total(self):
        from app.services.copilot_tools import _drag_breakdown

        bd = _drag_breakdown(cl=0.5, cd_total=0.03, ar=10.0, e=0.8)
        assert bd["cd_induced"] + bd["cd_parasite"] == pytest.approx(0.03, abs=1e-9)

    def test_inconsistent_split_returns_note_not_wrong_numbers(self):
        from app.services.copilot_tools import _drag_breakdown

        # CD_i would exceed total → must NOT fabricate a negative parasitic
        bd = _drag_breakdown(cl=1.5, cd_total=0.01, ar=5.0, e=0.7)
        assert bd is not None
        assert "note" in bd
        assert "cd_parasite" not in bd

    def test_missing_inputs_return_none(self):
        from app.services.copilot_tools import _drag_breakdown

        assert _drag_breakdown(cl=0.5, cd_total=0.03, ar=None, e=0.8) is None
        assert _drag_breakdown(cl=None, cd_total=0.03, ar=10, e=0.8) is None
        assert _drag_breakdown(cl=0.5, cd_total=0.03, ar=0, e=0.8) is None


class TestPolarDragBreakdownWiring:
    """The polar wiring that picks best-glide and pulls AR/e from the snapshot
    context (gh-925). Mocks only _metrics_payload — no aero deps needed.
    """

    def test_breakdown_uses_context_ar_and_e(self, client_and_db):
        import numpy as np

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            # best L/D is at index 1 (CL 0.552 / CD 0.02302) — the eHawk point
            cl = np.array([0.1, 0.552, 1.2])
            cd = np.array([0.013, 0.02302, 0.10])
            with patch(
                "app.services.aeroplane_version_service._metrics_payload",
                return_value={
                    "assumption_computation_context": {
                        "aspect_ratio": 11.3,
                        "e_oswald": 0.7916,
                    }
                },
            ):
                bd = tools_module._polar_drag_breakdown(db, str(plane.uuid), cl, cd)

        assert bd is not None and "note" not in bd
        assert bd["cd_induced"] == pytest.approx(0.01084, abs=2e-4)
        assert bd["induced_fraction"] == pytest.approx(0.47, abs=0.03)
        assert bd["cd_total"] == pytest.approx(0.02302, abs=1e-5)

    def test_breakdown_none_when_context_missing_ar_e(self, client_and_db):
        import numpy as np

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            with patch(
                "app.services.aeroplane_version_service._metrics_payload",
                return_value={"assumption_computation_context": {}},
            ):
                bd = tools_module._polar_drag_breakdown(
                    db, str(plane.uuid), np.array([0.5]), np.array([0.03])
                )
        assert bd is None

    def test_breakdown_none_on_empty_arrays(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            assert (
                tools_module._polar_drag_breakdown(db, str(plane.uuid), None, None)
                is None
            )

    def test_breakdown_swallows_errors_and_returns_none(self, client_and_db):
        import numpy as np

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            # _metrics_payload blowing up must not break the polar — best-effort
            with patch(
                "app.services.aeroplane_version_service._metrics_payload",
                side_effect=RuntimeError("boom"),
            ):
                bd = tools_module._polar_drag_breakdown(
                    db, str(plane.uuid), np.array([0.5, 0.55]), np.array([0.03, 0.023])
                )
        assert bd is None


class TestToolRegistry:
    def test_registry_has_five_tools(self):
        # Slice 1: get_design_snapshot, run_analysis, get_version_tree
        # Slice 2 (gh-937/938): apply_design_edits, discard_proposal
        assert len(tools_module.TOOL_REGISTRY) == 5

    def test_registry_keys_match_schema_names(self):
        for key, entry in tools_module.TOOL_REGISTRY.items():
            assert entry.schema["function"]["name"] == key

    def test_each_entry_has_impl_callable(self):
        for entry in tools_module.TOOL_REGISTRY.values():
            assert callable(entry.impl)


class TestStabilityNeutralPointSingleSource:
    """gh-924: the copilot stability tool must report the ONE authoritative
    neutral point (the dashboard's cruise value from the design context), not a
    second divergent value from a fresh off-design run."""

    def test_reports_context_neutral_point_not_run_value(self, client_and_db):
        import asyncio
        from unittest.mock import patch
        from types import SimpleNamespace

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db)
            plane.assumption_computation_context = {"x_np_m": 0.0802, "v_cruise_mps": 18.0}
            db.flush()
            uuid = str(plane.uuid)

            # A fresh run would yield a DIFFERENT (divergent) neutral point
            async def _fake_summary(*a, **k):
                return SimpleNamespace(
                    static_margin_pct=30.0, stability_class="stable",
                    neutral_point_x=0.109, cg_x=0.066, Cma=-0.5, Cnb=0.1, Clb=-0.05,
                    is_statically_stable=True, is_directionally_stable=True,
                    is_laterally_stable=True, mac=0.14,
                    cg_range_forward=0.05, cg_range_aft=0.07,
                )

            with patch(
                "app.services.stability_service.get_stability_summary", _fake_summary
            ):
                out = asyncio.run(tools_module._run_stability_async(db, uuid))

        # The authoritative context NP (0.0802) wins over the run's 0.109
        assert out["neutral_point_x_m"] == 0.0802
        # static margin recomputed consistently against the SAME (context) NP
        assert out["static_margin_pct"] == pytest.approx((0.0802 - 0.066) / 0.14 * 100, abs=0.1)
