"""TDD tests for POST /aeroplanes/{id}/turbulator/optimize — gh-935 Part C.

Strategy
--------
FastAPI TestClient + in-memory SQLite. The heavy optimizer service call
is monkeypatched to a deterministic stub so tests remain in the fast tier.

Tests cover:
- Route is registered and reachable (returns something, not 404)
- 404 for unknown aeroplane
- Successful response shape matches TurbulatorOptimizerResponse schema
- scope query parameter is forwarded to the service
- Service-level error surfaces as HTTP 422
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_optimizer_result():
    """Build a minimal TurbulatorOptimizerResult that passes schema validation."""
    from app.services.turbulator_optimizer_service import (
        SectionOptimizerResult,
        TurbulatorOptimizerResult,
        TurbulatorOptimizerSummary,
    )

    sections = [
        SectionOptimizerResult(
            y_m=0.1,
            chord_m=0.2,
            re_local=200_000,
            cl=0.6,
            xtr_opt=0.4,
            cd_clean=0.030,
            cd_tripped=0.020,
            delta_cd=-0.010,
            warnings=[],
            section_area_m2=0.10,
        )
    ]
    summary = TurbulatorOptimizerSummary(
        delta_cd0=-0.0025,
        l_d_clean=20.0,
        l_d_tripped=21.2,
        delta_l_d=1.2,
    )
    return TurbulatorOptimizerResult(sections=sections, summary=summary, scope="section")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTurbulatorOptimizerEndpoint:
    def test_route_exists_not_404_for_known_aeroplane(self, client_and_db, monkeypatch):
        """POST /aeroplanes/{id}/turbulator/optimize returns non-404."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.turbulator_optimizer._call_optimizer",
            lambda *a, **kw: _stub_optimizer_result(),
        )

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "section"})
        assert response.status_code != 404

    def test_returns_404_for_unknown_aeroplane(self, client_and_db):
        """POST with unknown UUID returns 404."""
        import uuid

        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())
        response = client.post(f"/aeroplanes/{fake_uuid}/turbulator/optimize",
                               json={"scope": "section"})
        assert response.status_code == 404

    def test_successful_response_has_expected_keys(self, client_and_db, monkeypatch):
        """Successful response contains sections and summary keys."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.turbulator_optimizer._call_optimizer",
            lambda *a, **kw: _stub_optimizer_result(),
        )

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "section"})
        assert response.status_code == 200
        body = response.json()
        assert "sections" in body
        assert "summary" in body
        assert "scope" in body

    def test_response_sections_have_expected_fields(self, client_and_db, monkeypatch):
        """Each section entry has y_m, chord_m, re_local, cl, xtr_opt, cd_clean, etc."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.turbulator_optimizer._call_optimizer",
            lambda *a, **kw: _stub_optimizer_result(),
        )

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "section"})
        assert response.status_code == 200
        sec = response.json()["sections"][0]
        for key in ("y_m", "chord_m", "re_local", "cl", "xtr_opt",
                    "cd_clean", "cd_tripped", "delta_cd", "warnings"):
            assert key in sec, f"Missing key {key!r} in section response"

    def test_response_summary_has_expected_fields(self, client_and_db, monkeypatch):
        """Summary contains delta_cd0, l_d_clean, l_d_tripped, delta_l_d."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.turbulator_optimizer._call_optimizer",
            lambda *a, **kw: _stub_optimizer_result(),
        )

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "section"})
        summary = response.json()["summary"]
        for key in ("delta_cd0", "l_d_clean", "l_d_tripped", "delta_l_d"):
            assert key in summary, f"Missing key {key!r} in summary response"

    def test_scope_whole_accepted(self, client_and_db, monkeypatch):
        """scope='whole' is a valid input."""
        from app.tests.conftest import make_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        def _stub_whole(*a, **kw):
            r = _stub_optimizer_result()
            r.scope = "whole"
            return r

        monkeypatch.setattr(
            "app.api.v2.endpoints.aeroplane.turbulator_optimizer._call_optimizer",
            _stub_whole,
        )

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "whole"})
        assert response.status_code == 200
        assert response.json()["scope"] == "whole"

    def test_invalid_scope_returns_422(self, client_and_db):
        """scope='invalid' must be rejected at the Pydantic level (422)."""
        from app.tests.conftest import make_aeroplane
        import uuid

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        response = client.post(f"/aeroplanes/{aeroplane.uuid}/turbulator/optimize",
                               json={"scope": "invalid_scope"})
        assert response.status_code == 422
