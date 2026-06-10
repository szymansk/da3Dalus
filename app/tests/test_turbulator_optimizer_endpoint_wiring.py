"""Coverage-completion tests for the turbulator optimizer endpoint — gh-935.

These tests exercise the INTERNAL wiring of _call_optimizer and _result_to_response
that the existing endpoint tests bypass (they monkeypatch _call_optimizer wholesale).

Strategy
--------
Each test mocks its collaborators one level down so the wiring code runs for real:
  - db.query(AeroplaneModel) → monkeypatched to return a stub aircraft row
  - get_effective_assumption → monkeypatched to return design_speed
  - get_aeroplane_schema_or_raise → stub schema
  - aeroplane_schema_to_asb_airplane_async → stub ASB airplane
  - compute_section_aoa → stub section entries
  - build_wing_section_data → stub WingSectionData list
  - run_turbulator_optimizer → returns a deterministic TurbulatorOptimizerResult

The _result_to_response function is tested by calling it directly with
a constructed TurbulatorOptimizerResult.

Error paths tested:
  - Aircraft not found → NotFoundError → 404
  - No wings on aircraft → ValidationDomainError → 422
  - Section AoA computation raises → ValidationDomainError → 422
  - No section entries → ValidationDomainError → 422
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stub_optimizer_result():
    from app.services.turbulator_optimizer_service import (
        SectionOptimizerResult,
        TurbulatorOptimizerResult,
        TurbulatorOptimizerSummary,
    )

    sections = [
        SectionOptimizerResult(
            y_m=0.1, chord_m=0.2, re_local=200_000, cl=0.6,
            xtr_opt=0.4, cd_clean=0.030, cd_tripped=0.020, delta_cd=-0.010,
            warnings=[], section_area_m2=0.10,
        )
    ]
    summary = TurbulatorOptimizerSummary(
        delta_cd0=-0.0025, l_d_clean=20.0, l_d_tripped=21.2, delta_l_d=1.2
    )
    return TurbulatorOptimizerResult(sections=sections, summary=summary, scope="section")


def _make_stub_wsd():
    from app.services.turbulator_optimizer_service import WingSectionData

    return [
        WingSectionData(
            y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
            airfoil_name="naca0012", section_area_m2=0.10,
        )
    ]


# ---------------------------------------------------------------------------
# Tests: _result_to_response (direct unit test)
# ---------------------------------------------------------------------------


class TestResultToResponse:
    """_result_to_response converts TurbulatorOptimizerResult → Pydantic response."""

    def test_maps_sections_correctly(self):
        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _result_to_response

        result = _make_stub_optimizer_result()
        response = _result_to_response(result)
        assert len(response.sections) == 1
        sec = response.sections[0]
        assert sec.y_m == pytest.approx(0.1, abs=1e-9)
        assert sec.xtr_opt == pytest.approx(0.4, abs=1e-9)
        assert sec.cd_clean == pytest.approx(0.030, abs=1e-9)
        assert sec.cd_tripped == pytest.approx(0.020, abs=1e-9)
        assert sec.delta_cd == pytest.approx(-0.010, abs=1e-9)
        assert sec.warnings == []

    def test_maps_summary_correctly(self):
        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _result_to_response

        result = _make_stub_optimizer_result()
        response = _result_to_response(result)
        assert response.summary.delta_cd0 == pytest.approx(-0.0025, abs=1e-9)
        assert response.summary.l_d_clean == pytest.approx(20.0, abs=1e-9)
        assert response.summary.l_d_tripped == pytest.approx(21.2, abs=1e-9)
        assert response.summary.delta_l_d == pytest.approx(1.2, abs=1e-9)

    def test_maps_scope_correctly(self):
        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _result_to_response

        result = _make_stub_optimizer_result()
        response = _result_to_response(result)
        assert response.scope == "section"

    def test_empty_sections_list(self):
        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _result_to_response
        from app.services.turbulator_optimizer_service import (
            TurbulatorOptimizerResult,
            TurbulatorOptimizerSummary,
        )

        summary = TurbulatorOptimizerSummary(
            delta_cd0=0.0, l_d_clean=15.0, l_d_tripped=15.0, delta_l_d=0.0
        )
        result = TurbulatorOptimizerResult(sections=[], summary=summary, scope="whole")
        response = _result_to_response(result)
        assert response.sections == []
        assert response.scope == "whole"


# ---------------------------------------------------------------------------
# Tests: _raise_http — maps ServiceException subclasses to HTTP status codes
# ---------------------------------------------------------------------------


class TestRaiseHttp:
    """_raise_http(exc) must raise HTTPException with the right status code."""

    def test_not_found_error_raises_404(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _raise_http
        from app.core.exceptions import NotFoundError

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(NotFoundError(entity="Aeroplane", resource_id="abc"))
        assert exc_info.value.status_code == 404

    def test_validation_domain_error_raises_422(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _raise_http
        from app.core.exceptions import ValidationDomainError

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(ValidationDomainError(message="bad input"))
        assert exc_info.value.status_code == 422

    def test_generic_service_exception_raises_500(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _raise_http
        from app.core.exceptions import ServiceException

        with pytest.raises(HTTPException) as exc_info:
            _raise_http(ServiceException(message="unexpected failure"))
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Tests: _call — wraps errors into HTTPException
# ---------------------------------------------------------------------------


class TestCallWrapper:
    """_call(func, ...) re-raises ServiceException → HTTPException."""

    def test_service_exception_becomes_404(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _call
        from app.core.exceptions import NotFoundError

        def _raise():
            raise NotFoundError(entity="Aeroplane", resource_id="xyz")

        with pytest.raises(HTTPException) as exc_info:
            _call(_raise)
        assert exc_info.value.status_code == 404

    def test_unexpected_exception_becomes_500(self):
        from fastapi import HTTPException

        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _call

        def _raise():
            raise RuntimeError("completely unexpected")

        with pytest.raises(HTTPException) as exc_info:
            _call(_raise)
        assert exc_info.value.status_code == 500

    def test_success_returns_value(self):
        from app.api.v2.endpoints.aeroplane.turbulator_optimizer import _call

        result = _call(lambda: 42)
        assert result == 42


# ---------------------------------------------------------------------------
# Tests: _call_optimizer wiring via endpoint (through TestClient)
# ---------------------------------------------------------------------------


class TestCallOptimizerWiring:
    """Exercise _call_optimizer with collaborators mocked one level down."""

    def _make_stub_asb_airplane(self):
        """ASB airplane stub with one wing + two xsecs + symmetric flag."""
        xsec_root = SimpleNamespace(
            xyz_le=[0.0, 0.0, 0.0],
            airfoil=SimpleNamespace(name="naca0012"),
        )
        xsec_tip = SimpleNamespace(
            xyz_le=[0.0, 0.5, 0.0],
            airfoil=SimpleNamespace(name="naca0012"),
        )
        wing = SimpleNamespace(
            area=lambda: 0.30,
            xsecs=[xsec_root, xsec_tip],
            name="main_wing",
            symmetric=True,
        )
        return SimpleNamespace(wings=[wing], xyz_ref=[0.08, 0.0, 0.0])

    def test_optimizer_wiring_returns_result(self, client_and_db, monkeypatch):
        """_call_optimizer wired end-to-end with all collaborators mocked."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        stub_airplane = self._make_stub_asb_airplane()
        stub_wsd = _make_stub_wsd()
        stub_result = _make_stub_optimizer_result()

        stub_section_entry = SimpleNamespace(y_m=0.1, chord_m=0.2, cl=0.6)

        with (
            patch("app.services.analysis_service.get_aeroplane_schema_or_raise",
                  return_value=SimpleNamespace()),
            patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                  return_value=stub_airplane),
            patch("app.services.design_assumptions_service.get_effective_assumption",
                  return_value=18.0),
            patch("app.services.section_aoa_service.compute_section_aoa",
                  return_value=[stub_section_entry]),
            patch("app.services.turbulator_optimizer_service.build_wing_section_data",
                  return_value=stub_wsd),
            patch("app.services.turbulator_optimizer_service.run_turbulator_optimizer",
                  return_value=stub_result),
        ):
            # Also need to patch aerosandbox.OperatingPoint
            import sys
            import types as _types

            if "aerosandbox" not in sys.modules:
                asb_mod = _types.ModuleType("aerosandbox")
                asb_mod.OperatingPoint = lambda **kw: SimpleNamespace(**kw)
                sys.modules["aerosandbox"] = asb_mod
            else:
                original_op = sys.modules["aerosandbox"].__dict__.get("OperatingPoint")
                sys.modules["aerosandbox"].OperatingPoint = lambda **kw: SimpleNamespace(**kw)

            response = client.post(
                f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                json={"scope": "section"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "sections" in body
        assert "summary" in body

    def test_no_wings_returns_422(self, client_and_db, monkeypatch):
        """When aircraft has no wings, _call_optimizer raises ValidationDomainError → 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        empty_airplane = SimpleNamespace(wings=[])

        with (
            patch("app.services.analysis_service.get_aeroplane_schema_or_raise",
                  return_value=SimpleNamespace()),
            patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                  return_value=empty_airplane),
            patch("app.services.design_assumptions_service.get_effective_assumption",
                  return_value=15.0),
        ):
            import sys
            import types as _types

            if "aerosandbox" not in sys.modules:
                asb_mod = _types.ModuleType("aerosandbox")
                asb_mod.OperatingPoint = lambda **kw: SimpleNamespace(**kw)
                sys.modules["aerosandbox"] = asb_mod

            response = client.post(
                f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                json={"scope": "section"},
            )

        assert response.status_code == 422

    def test_section_aoa_raises_returns_422(self, client_and_db, monkeypatch):
        """When compute_section_aoa raises, ValidationDomainError → 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        stub_airplane = self._make_stub_asb_airplane()

        with (
            patch("app.services.analysis_service.get_aeroplane_schema_or_raise",
                  return_value=SimpleNamespace()),
            patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                  return_value=stub_airplane),
            patch("app.services.design_assumptions_service.get_effective_assumption",
                  return_value=15.0),
            patch("app.services.section_aoa_service.compute_section_aoa",
                  side_effect=RuntimeError("AoA computation failed")),
        ):
            import sys
            import types as _types

            if "aerosandbox" not in sys.modules:
                asb_mod = _types.ModuleType("aerosandbox")
                asb_mod.OperatingPoint = lambda **kw: SimpleNamespace(**kw)
                sys.modules["aerosandbox"] = asb_mod
            else:
                sys.modules["aerosandbox"].OperatingPoint = lambda **kw: SimpleNamespace(**kw)

            response = client.post(
                f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                json={"scope": "section"},
            )

        assert response.status_code == 422

    def test_empty_section_entries_returns_422(self, client_and_db, monkeypatch):
        """When compute_section_aoa returns empty list, ValidationDomainError → 422."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        stub_airplane = self._make_stub_asb_airplane()

        with (
            patch("app.services.analysis_service.get_aeroplane_schema_or_raise",
                  return_value=SimpleNamespace()),
            patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                  return_value=stub_airplane),
            patch("app.services.design_assumptions_service.get_effective_assumption",
                  return_value=15.0),
            patch("app.services.section_aoa_service.compute_section_aoa",
                  return_value=[]),  # empty → ValidationDomainError
        ):
            import sys
            import types as _types

            if "aerosandbox" not in sys.modules:
                asb_mod = _types.ModuleType("aerosandbox")
                asb_mod.OperatingPoint = lambda **kw: SimpleNamespace(**kw)
                sys.modules["aerosandbox"] = asb_mod
            else:
                sys.modules["aerosandbox"].OperatingPoint = lambda **kw: SimpleNamespace(**kw)

            response = client.post(
                f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                json={"scope": "section"},
            )

        assert response.status_code == 422

    def test_design_speed_fallback_to_15(self, client_and_db, monkeypatch):
        """When get_effective_assumption returns None, design_speed defaults to 15."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        stub_airplane = self._make_stub_asb_airplane()
        stub_wsd = _make_stub_wsd()
        stub_result = _make_stub_optimizer_result()

        captured_speeds = []

        def _capture_build_wsd(asb_airplane, section_entries, velocity, s_ref):
            captured_speeds.append(velocity)
            return stub_wsd

        stub_section_entry = SimpleNamespace(y_m=0.1, chord_m=0.2, cl=0.6)

        with (
            patch("app.services.analysis_service.get_aeroplane_schema_or_raise",
                  return_value=SimpleNamespace()),
            patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                  return_value=stub_airplane),
            patch("app.services.design_assumptions_service.get_effective_assumption",
                  return_value=None),  # None → fallback to 15.0
            patch("app.services.section_aoa_service.compute_section_aoa",
                  return_value=[stub_section_entry]),
            patch("app.services.turbulator_optimizer_service.build_wing_section_data",
                  side_effect=_capture_build_wsd),
            patch("app.services.turbulator_optimizer_service.run_turbulator_optimizer",
                  return_value=stub_result),
        ):
            import sys
            import types as _types

            if "aerosandbox" not in sys.modules:
                asb_mod = _types.ModuleType("aerosandbox")
                asb_mod.OperatingPoint = lambda **kw: SimpleNamespace(**kw)
                sys.modules["aerosandbox"] = asb_mod
            else:
                sys.modules["aerosandbox"].OperatingPoint = lambda **kw: SimpleNamespace(**kw)

            response = client.post(
                f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                json={"scope": "section"},
            )

        assert response.status_code == 200
        # design_speed should default to 15.0 when get_effective_assumption returned None
        assert captured_speeds == [15.0]
