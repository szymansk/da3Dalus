"""Tests for GET /airfoils/db/suitability endpoint (Task 8, gh-821).

Uses TestClient with mocked service.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client_no_svc():
    """TestClient with in-memory DB, service mocked via patch."""
    from app.db.base import Base
    import app.models  # noqa: F401
    from app.db.session import get_db
    from app.main import create_app

    app = create_app()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, class_=Session
    )

    from app.services.component_type_service import seed_default_types
    from app.services.mission_objective_service import seed_mission_presets

    _s = TestingSessionLocal()
    try:
        seed_default_types(_s)
        seed_mission_presets(_s)
        _s.commit()
    finally:
        _s.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _make_fake_response():
    """Build a minimal SuitabilityResponse for mocking (gh-825 contract)."""
    from app.schemas.airfoil import (
        SuitabilityResponse,
        SuitabilityQuery,
        SuitabilityCaveat,
        SuitabilityItem,
    )

    return SuitabilityResponse(
        query=SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            mission_type=None,
            target_cl_cruise=None,
            target_cl_best_glide=None,
            target_cl_min_sink=None,
            target_cl_provenance="estimated",
            active_lens="re_agnostic",
        ),
        caveat=SuitabilityCaveat(
            relative_ranking_only=True,
            no_hysteresis_modelling=True,
            ignores_tip_re_clmax_collapse=True,
            recommend_xfoil_validation=False,
            text="Nur relative Reihenfolge.",
        ),
        results=[
            SuitabilityItem(
                airfoil_name="sd7037",
                family="cambered",
                re_agnostic=0.85,
                mission=None,
                target_cl_cruise=None,
                target_cl_best_glide=None,
                target_cl_min_sink=None,
                stall_gentleness=-0.04,
                cl_max_margin=0.4,
                min_analysis_confidence=0.95,
                tip_re_flag=False,
                caveat="",
            )
        ],
    )


def test_endpoint_requires_chord_m(client_no_svc):
    resp = client_no_svc.get("/airfoils/db/suitability", params={"speed_ms": 15.0})
    assert resp.status_code == 422  # chord_m missing


def test_endpoint_requires_speed_ms(client_no_svc):
    resp = client_no_svc.get("/airfoils/db/suitability", params={"chord_m": 0.15})
    assert resp.status_code == 422  # speed_ms missing


def test_endpoint_returns_200_with_required_params(client_no_svc):
    fake_resp = _make_fake_response()
    with patch("app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp):
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={"chord_m": 0.15, "speed_ms": 15.0},
        )
    assert resp.status_code == 200


def test_endpoint_response_has_frozen_shape(client_no_svc):
    """Verify response shape matches gh-825 contract."""
    fake_resp = _make_fake_response()
    with patch("app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp):
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={"chord_m": 0.15, "speed_ms": 15.0},
        )
    data = resp.json()
    assert "query" in data
    assert "caveat" in data
    assert "results" in data
    q = data["query"]
    assert "chord_m" in q
    assert "speed_ms" in q
    assert "reynolds" in q
    assert "re_clamped" in q
    assert "active_lens" in q
    assert "target_cl_best_glide" in q
    assert "target_cl_min_sink" in q
    assert "target_cl_provenance" in q
    assert "target_cl_loiter" not in q
    c = data["caveat"]
    assert "relative_ranking_only" in c
    assert "no_hysteresis_modelling" in c
    assert "ignores_tip_re_clmax_collapse" in c
    assert "recommend_xfoil_validation" in c
    r = data["results"][0]
    assert "airfoil_name" in r
    assert "family" in r
    assert "re_agnostic" in r
    assert "mission" in r
    assert "target_cl_cruise" in r
    assert "target_cl_best_glide" in r
    assert "target_cl_min_sink" in r
    assert "stall_gentleness" in r
    assert "cl_max_margin" in r
    assert "min_analysis_confidence" in r
    assert "tip_re_flag" in r
    assert "caveat" in r
    assert "target_cl_loiter" not in r


def test_endpoint_passes_optional_params_to_service(client_no_svc):
    """Verify optional params are forwarded to the service."""
    fake_resp = _make_fake_response()
    with patch(
        "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
    ) as mock_svc:
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={
                "chord_m": 0.15,
                "speed_ms": 15.0,
                "mission_type": "glider",
                "target_cl_cruise": 0.7,
                "limit": 10,
            },
        )
    assert resp.status_code == 200
    call_kwargs = mock_svc.call_args[1]
    assert call_kwargs.get("mission_type") == "glider"
    assert call_kwargs.get("target_cl_cruise") == pytest.approx(0.7)
    assert call_kwargs.get("limit") == 10


def test_endpoint_aeroplane_id_forwarded(client_no_svc):
    """aeroplane_id UUID string is forwarded to the service."""
    import uuid

    fake_resp = _make_fake_response()
    ap_uuid = str(uuid.uuid4())
    with patch(
        "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
    ) as mock_svc:
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={
                "chord_m": 0.15,
                "speed_ms": 15.0,
                "aeroplane_id": ap_uuid,
            },
        )
    assert resp.status_code == 200
    call_kwargs = mock_svc.call_args[1]
    assert call_kwargs.get("aeroplane_id") == ap_uuid


# ---------------------------------------------------------------------------
# ITEM 5-BE (gh-825): `include` query param — endpoint-level tests
# ---------------------------------------------------------------------------


def test_endpoint_include_param_parsed_and_forwarded(client_no_svc):
    """include=s1223,ag35 is parsed and forwarded as list[str] to the service."""
    fake_resp = _make_fake_response()
    with patch(
        "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
    ) as mock_svc:
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={
                "chord_m": 0.15,
                "speed_ms": 15.0,
                "include": "s1223,ag35",
            },
        )
    assert resp.status_code == 200
    call_kwargs = mock_svc.call_args[1]
    include_param = call_kwargs.get("include")
    assert include_param is not None, "include must be forwarded to service"
    assert isinstance(include_param, list), (
        f"include must be parsed to list, got {type(include_param)}"
    )
    assert sorted(include_param) == sorted(["s1223", "ag35"]), (
        f"include must contain ['s1223', 'ag35'], got {include_param}"
    )


def test_endpoint_include_param_absent_gives_none(client_no_svc):
    """Old clients (no include param) must get include=None → identical behaviour."""
    fake_resp = _make_fake_response()
    with patch(
        "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
    ) as mock_svc:
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={"chord_m": 0.15, "speed_ms": 15.0},
        )
    assert resp.status_code == 200
    call_kwargs = mock_svc.call_args[1]
    # include should either be absent or None — either way, no include list
    include_param = call_kwargs.get("include")
    assert include_param is None, (
        f"Old clients (no include) must get include=None; got {include_param}"
    )


def test_endpoint_include_whitespace_stripped(client_no_svc):
    """include values are stripped of whitespace (e.g. 's1223 , ag35')."""
    fake_resp = _make_fake_response()
    with patch(
        "app.api.v2.endpoints.airfoils.search_suitability", return_value=fake_resp
    ) as mock_svc:
        resp = client_no_svc.get(
            "/airfoils/db/suitability",
            params={
                "chord_m": 0.15,
                "speed_ms": 15.0,
                "include": " s1223 , ag35 , ",
            },
        )
    assert resp.status_code == 200
    call_kwargs = mock_svc.call_args[1]
    include_param = call_kwargs.get("include")
    # Empty strings after split+strip must be dropped
    assert "" not in (include_param or []), (
        f"Empty strings must be dropped from include: {include_param}"
    )
    assert "s1223" in (include_param or []), "s1223 must be present after strip"
    assert "ag35" in (include_param or []), "ag35 must be present after strip"
