"""Endpoint tests for GET /aeroplanes/{id}/speed-polar (gh-841)."""

from __future__ import annotations

import math
import uuid

import pytest

from app.models.aeroplanemodel import AeroplaneModel
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_aeroplane_with_context(session, *, ctx: dict) -> AeroplaneModel:
    plane = make_aeroplane(session, name=f"speed-polar-test-{uuid.uuid4().hex[:8]}")
    plane.assumption_computation_context = ctx
    session.flush()
    session.commit()
    return plane


_FULL_CTX = {
    "mass_kg": 2.0,
    "s_ref_m2": 0.40,
    "aspect_ratio": 8.0,
    "e_oswald": 0.80,
    "cd0": 0.025,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpeedPolarEndpointHappyPath:
    def test_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{uid}/speed-polar")
        assert resp.status_code == 200, resp.text

    def test_response_has_required_fields(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        for field in ("v_mps", "sink_mps", "cl", "best_glide", "min_sink", "inputs"):
            assert field in data, f"Missing field: {field}"

    def test_best_glide_and_min_sink_have_point_fields(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        for key in ("best_glide", "min_sink"):
            pt = data[key]
            for f in ("v_mps", "sink_mps", "cl"):
                assert f in pt, f"{key} missing {f}"

    def test_min_sink_cl_is_sqrt3_times_best_glide_cl(self, client_and_db):
        """CL_ms = √3 · CL_bg (closed-form invariant)."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        cl_bg = data["best_glide"]["cl"]
        cl_ms = data["min_sink"]["cl"]
        assert abs(cl_ms / cl_bg - math.sqrt(3)) < 1e-3

    def test_v_ms_approx_076_v_bg(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        v_bg = data["best_glide"]["v_mps"]
        v_ms = data["min_sink"]["v_mps"]
        ratio = v_ms / v_bg
        assert abs(ratio - 0.76) < 0.01

    def test_min_sink_lower_than_best_glide_sink(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        assert data["min_sink"]["sink_mps"] < data["best_glide"]["sink_mps"]

    def test_curve_has_multiple_points(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        assert len(data["v_mps"]) > 10

    def test_inputs_echoed_in_response(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=_FULL_CTX)
            uid = str(plane.uuid)

        data = client.get(f"/aeroplanes/{uid}/speed-polar").json()
        assert data["inputs"]["mass_kg"] == _FULL_CTX["mass_kg"]
        assert data["inputs"]["cd0"] == _FULL_CTX["cd0"]


class TestSpeedPolarEndpointErrors:
    def test_404_for_unknown_aeroplane(self, client_and_db):
        client, _ = client_and_db
        uid = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{uid}/speed-polar")
        assert resp.status_code == 404

    def test_422_when_context_missing(self, client_and_db):
        """When aeroplane has no computation context, return 422."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx={})
            uid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{uid}/speed-polar")
        assert resp.status_code == 422

    def test_422_includes_missing_inputs_list(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            # Only mass_kg is present — all others missing
            plane = _make_aeroplane_with_context(db, ctx={"mass_kg": 2.0})
            uid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{uid}/speed-polar")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "missing_inputs" in detail
        assert len(detail["missing_inputs"]) > 0

    def test_422_when_cd0_zero(self, client_and_db):
        """cd0 = 0 is invalid (non-positive) → 422."""
        client, SessionLocal = client_and_db
        ctx = {**_FULL_CTX, "cd0": 0.0}
        with SessionLocal() as db:
            plane = _make_aeroplane_with_context(db, ctx=ctx)
            uid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{uid}/speed-polar")
        assert resp.status_code == 422
