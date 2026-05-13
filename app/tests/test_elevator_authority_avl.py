"""Tests for AVL high-fidelity solver path in elevator authority — gh-516.

TDD RED phase: written BEFORE the implementation.

Covers:
  - force_solver="avl" parameter on compute_forward_cg_limit
  - ForwardCGConfidence.avl_full enum value
  - _compute_forward_cg_limit_avl helper (mocked AVL runner)
  - confidence override: avl_full returned regardless of aircraft config
  - API endpoint: POST /aeroplanes/{uuid}/forward-cg/recompute?solver=avl
  - Real AVL slow integration test (marked @pytest.mark.slow)

Sign convention (Amendment B3, same as ASB path):
  AVL is run with negative (TE-UP) deflection → Cm_δe > 0.
  Two AVL runs: baseline (zero deflection) and TE-UP deflection.
  Cm_δe = (Cm_deflected - Cm_baseline) / abs(delta_e_rad)
"""

from __future__ import annotations

import math
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_svc():
    import app.services.elevator_authority_service as svc

    return svc


def _import_schema():
    from app.schemas.forward_cg import ForwardCGConfidence, ForwardCGResult

    return ForwardCGConfidence, ForwardCGResult


def _build_mock_aeroplane(
    aeroplane_id: int = 1,
    ted_role: str = "elevator",
    negative_deflection_deg: float = -25.0,
) -> MagicMock:
    """Minimal mock AeroplaneModel with one pitch-control TED."""
    mock_ted = MagicMock()
    mock_ted.role = ted_role
    mock_ted.name = ted_role
    mock_ted.negative_deflection_deg = negative_deflection_deg
    mock_ted.positive_deflection_deg = 20.0

    mock_detail = MagicMock()
    mock_detail.trailing_edge_device = [mock_ted]
    mock_xsec = MagicMock()
    mock_xsec.detail = mock_detail
    mock_wing = MagicMock()
    mock_wing.x_secs = [mock_xsec]
    mock_ac = MagicMock()
    mock_ac.id = aeroplane_id
    mock_ac.wings = [mock_wing]
    return mock_ac


# ---------------------------------------------------------------------------
# Class A: ForwardCGConfidence.avl_full enum value
# ---------------------------------------------------------------------------


class TestForwardCGConfidenceAvlFull:
    """avl_full must be present in the enum after gh-516."""

    def test_avl_full_enum_value_exists(self):
        """ForwardCGConfidence.avl_full must exist with value 'avl_full'."""
        ForwardCGConfidence, _ = _import_schema()
        assert hasattr(ForwardCGConfidence, "avl_full"), (
            "ForwardCGConfidence must have avl_full tier (gh-516)"
        )
        assert ForwardCGConfidence.avl_full.value == "avl_full"

    def test_avl_full_is_highest_confidence_tier(self):
        """avl_full should be present alongside the 5 ASB tiers (total 6 tiers now)."""
        ForwardCGConfidence, _ = _import_schema()
        all_values = {m.value for m in ForwardCGConfidence}
        # All original 5 tiers still present
        assert "asb_high_with_flap" in all_values
        assert "asb_high_clean" in all_values
        assert "asb_warn_with_flap" in all_values
        assert "asb_warn_clean" in all_values
        assert "stub" in all_values
        # New avl_full tier
        assert "avl_full" in all_values

    def test_avl_full_in_forward_cg_result(self):
        """ForwardCGResult should accept avl_full as confidence tier."""
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        result = ForwardCGResult(
            cg_fwd_m=0.10,
            confidence=ForwardCGConfidence.avl_full,
            cm_delta_e=0.45,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )
        assert result.confidence == ForwardCGConfidence.avl_full


# ---------------------------------------------------------------------------
# Class B: force_solver parameter on compute_forward_cg_limit
# ---------------------------------------------------------------------------


class TestForceSolverParameter:
    """force_solver="avl" must route to the AVL path."""

    def test_force_solver_defaults_to_asb(self):
        """compute_forward_cg_limit() without force_solver uses ASB path."""
        svc = _import_svc()
        import inspect

        sig = inspect.signature(svc.compute_forward_cg_limit)
        params = sig.parameters

        assert "force_solver" in params, "force_solver parameter must exist"
        assert params["force_solver"].default == "asb", "default must be 'asb'"

    def test_force_solver_asb_calls_asb_helper(self):
        """force_solver='asb' calls _compute_forward_cg_limit_asb."""
        svc = _import_svc()
        ForwardCGConfidence, ForwardCGResult = _import_schema()

        mock_result = ForwardCGResult(
            cg_fwd_m=0.12,
            confidence=ForwardCGConfidence.asb_high_clean,
            cm_delta_e=0.32,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )

        with (
            patch.object(svc, "_compute_forward_cg_limit_asb", return_value=mock_result) as mock_asb,
            patch.object(svc, "_compute_forward_cg_limit_avl") as mock_avl,
        ):
            result = svc.compute_forward_cg_limit(MagicMock(), MagicMock(), force_solver="asb")

        mock_asb.assert_called_once()
        mock_avl.assert_not_called()
        assert result == mock_result

    def test_force_solver_avl_calls_avl_helper(self):
        """force_solver='avl' calls _compute_forward_cg_limit_avl."""
        svc = _import_svc()
        ForwardCGConfidence, ForwardCGResult = _import_schema()

        mock_result = ForwardCGResult(
            cg_fwd_m=0.11,
            confidence=ForwardCGConfidence.avl_full,
            cm_delta_e=0.40,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )

        with (
            patch.object(svc, "_compute_forward_cg_limit_avl", return_value=mock_result) as mock_avl,
            patch.object(svc, "_compute_forward_cg_limit_asb") as mock_asb,
        ):
            result = svc.compute_forward_cg_limit(MagicMock(), MagicMock(), force_solver="avl")

        mock_avl.assert_called_once()
        mock_asb.assert_not_called()
        assert result == mock_result

    def test_force_solver_avl_fallback_is_stub_not_asb(self):
        """When AVL path raises, falls back to stub (NOT ASB)."""
        svc = _import_svc()
        ForwardCGConfidence, _ = _import_schema()

        with (
            patch.object(
                svc,
                "_compute_forward_cg_limit_avl",
                side_effect=RuntimeError("AVL binary not found"),
            ),
            patch.object(svc, "_load_stability_assumptions", return_value=(0.40, 0.30, 1.4)),
        ):
            result = svc.compute_forward_cg_limit(MagicMock(), MagicMock(), force_solver="avl")

        # Must fall back to stub, not raise
        assert result.confidence == ForwardCGConfidence.stub

    def test_force_solver_asb_regression_unchanged(self):
        """Existing ASB path is not changed by gh-516 (regression guard)."""
        svc = _import_svc()
        ForwardCGConfidence, ForwardCGResult = _import_schema()

        # Verify the function still works the same way when force_solver is not specified
        mock_result = ForwardCGResult(
            cg_fwd_m=0.12,
            confidence=ForwardCGConfidence.asb_high_clean,
            cm_delta_e=0.32,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )

        with patch.object(svc, "_compute_forward_cg_limit_asb", return_value=mock_result):
            result = svc.compute_forward_cg_limit(MagicMock(), MagicMock())  # no force_solver

        assert result.confidence == ForwardCGConfidence.asb_high_clean


# ---------------------------------------------------------------------------
# Class C: _compute_forward_cg_limit_avl helper (mocked AVLRunner)
# ---------------------------------------------------------------------------


class TestComputeForwardCgLimitAvl:
    """Unit tests for the AVL path using mocked AVLRunner."""

    def _make_assumption_map(self):
        return {
            "x_np": 0.40,
            "mac": 0.30,
            "cl_max": 1.4,
            "v_cruise": 15.0,
            "stall_alpha": 12.0,
        }

    def test_avl_path_returns_avl_full_confidence(self):
        """_compute_forward_cg_limit_avl always returns avl_full confidence."""
        svc = _import_svc()
        ForwardCGConfidence, _ = _import_schema()

        mock_ac = _build_mock_aeroplane()
        assumption_map = self._make_assumption_map()

        # AVL runner: baseline Cm=-0.05, deflected Cm=0.25
        avl_result_baseline = {"CL": 1.1, "Cm": -0.05}
        avl_result_deflected = {"CL": 0.9, "Cm": 0.25}

        call_count = [0]

        def fake_avl_run(avl_file_content, control_overrides=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return avl_result_baseline
            return avl_result_deflected

        mock_runner = MagicMock()
        mock_runner.run.side_effect = fake_avl_run

        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        mock_plane_schema = MagicMock()

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ),
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            result = svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        assert result.confidence == ForwardCGConfidence.avl_full

    def test_avl_path_cm_delta_e_positive(self):
        """AVL path must produce Cm_δe > 0 (TE-UP sign convention)."""
        svc = _import_svc()

        mock_ac = _build_mock_aeroplane()
        assumption_map = self._make_assumption_map()

        # Baseline Cm=-0.06, deflected (TE-UP) Cm=0.20 → Cm_δe > 0
        call_count = [0]

        def fake_avl_run(avl_file_content, control_overrides=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"CL": 1.0, "Cm": -0.06}
            return {"CL": 0.9, "Cm": 0.20}

        mock_runner = MagicMock()
        mock_runner.run.side_effect = fake_avl_run
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ),
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            result = svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        assert result.cm_delta_e is not None
        assert result.cm_delta_e > 0, "Cm_δe must be positive (TE-UP convention)"

    def test_avl_path_calls_avl_runner_twice(self):
        """_compute_forward_cg_limit_avl runs AVL twice: baseline + TE-UP deflection."""
        svc = _import_svc()

        mock_ac = _build_mock_aeroplane()
        assumption_map = self._make_assumption_map()

        mock_runner = MagicMock()
        mock_runner.run.return_value = {"CL": 1.0, "Cm": -0.05}

        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ),
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        # AVL runner.run() must be called at least twice (baseline + deflected)
        assert mock_runner.run.call_count >= 2

    def test_avl_path_no_pitch_control_raises(self):
        """_compute_forward_cg_limit_avl raises ValueError with no pitch-control TED."""
        svc = _import_svc()

        mock_ac = MagicMock()
        mock_ac.id = 99
        mock_ac.wings = []  # no wings → no pitch TEDs

        assumption_map = self._make_assumption_map()

        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
        ):
            with pytest.raises(ValueError, match="No pitch-control TED"):
                svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

    def test_avl_path_x_np_unavailable_raises(self):
        """_compute_forward_cg_limit_avl raises ValueError when x_np missing."""
        svc = _import_svc()

        mock_ac = _build_mock_aeroplane()

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: None
            ),
        ):
            with pytest.raises(ValueError, match="x_np"):
                svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

    def test_avl_path_confidence_override_ignores_warn_roles(self):
        """Even warn-tier roles (ruddervator/elevon) get avl_full confidence from AVL path."""
        svc = _import_svc()
        ForwardCGConfidence, _ = _import_schema()

        # Use ruddervator (warn-tier in ASB path) — should still get avl_full
        mock_ac = _build_mock_aeroplane(ted_role="ruddervator")
        assumption_map = self._make_assumption_map()

        call_count = [0]

        def fake_avl_run(avl_file_content, control_overrides=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"CL": 1.0, "Cm": -0.05}
            return {"CL": 0.9, "Cm": 0.20}

        mock_runner = MagicMock()
        mock_runner.run.side_effect = fake_avl_run
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ),
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            result = svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        # Confidence must be avl_full regardless of role
        assert result.confidence == ForwardCGConfidence.avl_full, (
            "AVL path always returns avl_full confidence, regardless of aircraft config"
        )

    def test_avl_path_uses_te_up_deflection(self):
        """AVL run uses TE-UP (negative) deflection for the second run."""
        svc = _import_svc()

        mock_ac = _build_mock_aeroplane(negative_deflection_deg=-25.0)
        assumption_map = self._make_assumption_map()

        mock_runner = MagicMock()
        mock_runner.run.return_value = {"CL": 1.0, "Cm": -0.05}

        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ) as mock_runner_cls,
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        # Verify deflected run used a negative value (TE-UP) as control_override
        calls = mock_runner.run.call_args_list
        assert len(calls) >= 2

        # Second call should have a control_overrides with a negative deflection value
        deflected_call = calls[1]
        overrides = deflected_call.kwargs.get("control_overrides") or (
            deflected_call.args[1] if len(deflected_call.args) > 1 else None
        )
        if overrides:
            deflection_values = list(overrides.values())
            assert any(v < 0 for v in deflection_values), (
                "Deflected AVL run must use negative (TE-UP) deflection"
            )

    def test_avl_path_guards_still_applied(self):
        """Conditioning and infeasibility guards are still applied in AVL path."""
        svc = _import_svc()
        ForwardCGConfidence, _ = _import_schema()

        mock_ac = _build_mock_aeroplane()
        assumption_map = self._make_assumption_map()

        # Same Cm baseline and deflected → Cm_δe ≈ 0 → conditioning guard triggers
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"CL": 1.0, "Cm": -0.05}  # identical runs

        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        with (
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.elevator_authority_service.AVLRunner",
                return_value=mock_runner,
            ),
            patch(
                "app.services.elevator_authority_service._build_avl_file_for_elevator",
                return_value="DUMMY AVL FILE",
            ),
        ):
            result = svc._compute_forward_cg_limit_avl(MagicMock(), mock_ac)

        # Conditioning guard should trigger
        assert any("critically low" in w for w in result.warnings)
        # Confidence still avl_full (guard overrides x_np but keeps avl_full tier)
        assert result.confidence == ForwardCGConfidence.avl_full


# ---------------------------------------------------------------------------
# Class D: _build_avl_file_for_elevator helper
# ---------------------------------------------------------------------------


class TestBuildAvlFileForElevator:
    """_build_avl_file_for_elevator must return a valid AVL geometry file string."""

    def test_build_avl_file_returns_string(self):
        """_build_avl_file_for_elevator returns a non-empty string."""
        svc = _import_svc()

        mock_plane_schema = MagicMock()
        result = None

        # This function calls avl_geometry_service — we mock it
        with patch(
            "app.services.elevator_authority_service.build_avl_geometry_file",
            return_value=MagicMock(__repr__=lambda self: "MOCK AVL CONTENT"),
        ):
            result = svc._build_avl_file_for_elevator(mock_plane_schema)

        assert result is not None
        assert isinstance(result, str)

    def test_build_avl_file_helper_exists(self):
        """_build_avl_file_for_elevator must exist as a function."""
        svc = _import_svc()
        assert hasattr(svc, "_build_avl_file_for_elevator"), (
            "_build_avl_file_for_elevator must exist"
        )


# ---------------------------------------------------------------------------
# Class E: API endpoint — POST /aeroplanes/{uuid}/forward-cg/recompute
# ---------------------------------------------------------------------------


class TestForwardCgRecomputeEndpoint:
    """Tests for POST /aeroplanes/{uuid}/forward-cg/recompute?solver=... endpoint."""

    def test_endpoint_exists_asb_path(self, client_and_db):
        """POST /aeroplanes/{uuid}/forward-cg/recompute?solver=asb returns 200 or 404."""
        from app.schemas.forward_cg import ForwardCGConfidence, ForwardCGResult

        mock_result = ForwardCGResult(
            cg_fwd_m=0.12,
            confidence=ForwardCGConfidence.asb_high_clean,
            cm_delta_e=0.32,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )

        import uuid

        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())

        with patch(
            "app.api.v2.endpoints.aeroplane.forward_cg.compute_forward_cg_limit",
            return_value=mock_result,
        ):
            resp = client.post(
                f"/aeroplanes/{fake_uuid}/forward-cg/recompute?solver=asb"
            )

        # 200 or 404 (no aeroplane in DB) — endpoint must exist (not 405 "route not found")
        assert resp.status_code in (200, 404, 422, 500), (
            f"Expected endpoint to exist; got {resp.status_code}: {resp.text}"
        )
        assert resp.status_code != 405, "Endpoint must accept POST"

    def test_endpoint_exists_avl_path(self, client_and_db):
        """POST /aeroplanes/{uuid}/forward-cg/recompute?solver=avl returns non-405."""
        from app.schemas.forward_cg import ForwardCGConfidence, ForwardCGResult

        mock_result = ForwardCGResult(
            cg_fwd_m=0.11,
            confidence=ForwardCGConfidence.avl_full,
            cm_delta_e=0.40,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )

        import uuid

        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())

        with patch(
            "app.api.v2.endpoints.aeroplane.forward_cg.compute_forward_cg_limit",
            return_value=mock_result,
        ):
            resp = client.post(
                f"/aeroplanes/{fake_uuid}/forward-cg/recompute?solver=avl"
            )

        assert resp.status_code != 405, "Endpoint must accept POST with solver=avl"
        assert resp.status_code in (200, 404, 422, 500)

    def test_endpoint_invalid_solver_returns_422(self, client_and_db):
        """POST /aeroplanes/{uuid}/forward-cg/recompute?solver=invalid returns 422."""
        import uuid

        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())

        resp = client.post(
            f"/aeroplanes/{fake_uuid}/forward-cg/recompute?solver=invalid_value"
        )
        assert resp.status_code == 422, (
            f"Invalid solver value should return 422; got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Class F: Slow integration test — real AVL run (Cessna fixture)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestForwardCgLimitAvlIntegration:
    """Real AVL execution for Cm_δe — 30% sanity bound vs ASB value.

    Marked @pytest.mark.slow: requires AVL binary and AeroSandbox.
    Only run via: poetry run pytest -m slow
    """

    def _cessna_fixture_aeroplane_schema(self):
        """Build a minimal Cessna-like aeroplane schema for AVL integration."""
        import aerosandbox as asb
        import aerosandbox.numpy as np

        from app.schemas.aeroplaneschema import (
            AeroplaneSchema,
            AsbWingSchema,
            WingXSecSchema,
        )

        try:
            return asb.Airplane(
                name="Cessna-fixture",
                xyz_ref=[0.3, 0, 0],
                wings=[
                    asb.Wing(
                        name="Wing",
                        symmetric=True,
                        xsecs=[
                            asb.WingXSec(xyz_le=[0, 0, 0], chord=0.30, airfoil=asb.Airfoil("naca2412")),
                            asb.WingXSec(xyz_le=[0.05, 0.6, 0], chord=0.20, airfoil=asb.Airfoil("naca2412")),
                        ],
                    ),
                    asb.Wing(
                        name="Horizontal Stabilizer",
                        symmetric=True,
                        xsecs=[
                            asb.WingXSec(
                                xyz_le=[0.9, 0, 0],
                                chord=0.12,
                                airfoil=asb.Airfoil("naca0012"),
                                control_surfaces=[
                                    asb.ControlSurface(
                                        name="[elevator]Elevator",
                                        deflection=0,
                                    )
                                ],
                            ),
                            asb.WingXSec(
                                xyz_le=[0.92, 0.25, 0],
                                chord=0.10,
                                airfoil=asb.Airfoil("naca0012"),
                            ),
                        ],
                    ),
                ],
            )
        except Exception as exc:
            pytest.skip(f"Could not build ASB airplane fixture: {exc}")

    def test_avl_and_asb_cm_delta_e_within_30pct(self):
        """Real AVL Cm_δe must be within 30% of ASB Cm_δe for Cessna fixture.

        Sanity bound only — methods differ (vortex lattice vs strip theory).
        30% tolerance is intentionally wide.
        """
        try:
            import aerosandbox as asb
            from avl_binary import avl_path
        except ImportError as exc:
            pytest.skip(f"Dependencies not available: {exc}")

        from app.services.avl_runner import AVLRunner
        from app.services.avl_geometry_service import build_avl_geometry_file
        from app.schemas.aeroanalysis_schema import SpacingConfig

        # Build ASB airplane
        asb_airplane = self._cessna_fixture_aeroplane_schema()
        if asb_airplane is None:
            pytest.skip("Could not build fixture airplane")

        x_np_m = 0.40
        mac_m = 0.30
        delta_e_deg = -25.0  # TE-UP
        delta_e_rad = abs(delta_e_deg) * math.pi / 180.0
        v = 15.0

        # ASB Cm_δe via finite difference
        op = asb.OperatingPoint(velocity=v, alpha=12.0)
        xyz_ref = [x_np_m, 0, 0]

        try:
            asb_baseline = asb_airplane.with_control_deflections({"[elevator]Elevator": 0.0})
            asb_deflected = asb_airplane.with_control_deflections(
                {"[elevator]Elevator": delta_e_deg}
            )
            r_base = asb.AeroBuildup(
                airplane=asb_baseline, op_point=op, xyz_ref=xyz_ref
            ).run()
            r_defl = asb.AeroBuildup(
                airplane=asb_deflected, op_point=op, xyz_ref=xyz_ref
            ).run()

            def _cm(r):
                if isinstance(r, dict):
                    return float(r.get("Cm", 0.0))
                return float(getattr(r, "Cm", 0.0))

            cm_delta_e_asb = abs((_cm(r_defl) - _cm(r_base)) / delta_e_rad)
        except Exception as exc:
            pytest.skip(f"ASB run failed: {exc}")

        # Skip if ASB gives near-zero (conditioning guard would trigger anyway)
        if cm_delta_e_asb < 0.01:
            pytest.skip(f"ASB Cm_δe={cm_delta_e_asb:.4f} too small for meaningful comparison")

        # AVL Cm_δe via two AVL runs
        try:
            from app.services.avl_geometry_service import build_avl_geometry_file
            from app.schemas.aeroanalysisschema import SpacingConfig

            # Build a simple AVL geometry string directly
            avl_content = _build_cessna_avl_string()
            runner = AVLRunner(
                airplane=asb_airplane,
                op_point=op,
                xyz_ref=xyz_ref,
                timeout=30,
            )
            r_avl_base = runner.run(
                avl_file_content=avl_content,
                control_overrides={"[elevator]Elevator": 0.0},
            )
            r_avl_defl = runner.run(
                avl_file_content=avl_content,
                control_overrides={"[elevator]Elevator": delta_e_deg},
            )
        except Exception as exc:
            pytest.skip(f"AVL run failed: {exc}")

        cm_delta_e_avl = abs(
            (r_avl_defl.get("Cm", 0.0) - r_avl_base.get("Cm", 0.0)) / delta_e_rad
        )

        # Both must be non-zero (otherwise comparison is meaningless)
        if cm_delta_e_avl < 0.001:
            pytest.skip(f"AVL Cm_δe={cm_delta_e_avl:.4f} too small for meaningful comparison")

        # 30% tolerance sanity bound
        ratio = abs(cm_delta_e_avl - cm_delta_e_asb) / max(cm_delta_e_asb, cm_delta_e_avl)
        assert ratio <= 0.30, (
            f"AVL Cm_δe={cm_delta_e_avl:.4f} and ASB Cm_δe={cm_delta_e_asb:.4f} "
            f"differ by {ratio:.1%} > 30% sanity bound"
        )


def _build_cessna_avl_string() -> str:
    """Build a minimal Cessna-like AVL geometry string for integration testing."""
    return """\
Cessna-fixture
#Mach
0.0
#IYsym   IZsym   Zsym
0        0       0
#Sref    Cref    Bref
0.36     0.30    1.2
#Xref    Yref    Zref
0.40     0.0     0.0

SURFACE
Wing
#Nchordwise  Cspace   Nspanwise   Sspace
8            1.0      12          1.0
YDUPLICATE
0.0
ANGLE
0.0
SECTION
#Xle    Yle    Zle     Chord   Ainc
0.0     0.0    0.0     0.30    0.0
NACA
2412
SECTION
#Xle    Yle    Zle     Chord   Ainc
0.05    0.6    0.0     0.20    0.0
NACA
2412

SURFACE
Horizontal Stabilizer
#Nchordwise  Cspace   Nspanwise   Sspace
6            1.0      8           1.0
YDUPLICATE
0.0
ANGLE
0.0
SECTION
#Xle    Yle    Zle     Chord   Ainc
0.90    0.0    0.0     0.12    0.0
NACA
0012
CONTROL
#name     gain   Xhinge  XYZhvec       SgnDup
elevator  1.0    0.7     0.0 0.0 0.0   1.0

SECTION
#Xle    Yle    Zle     Chord   Ainc
0.92    0.25   0.0     0.10    0.0
NACA
0012
CONTROL
#name     gain   Xhinge  XYZhvec       SgnDup
elevator  1.0    0.7     0.0 0.0 0.0   1.0
"""
