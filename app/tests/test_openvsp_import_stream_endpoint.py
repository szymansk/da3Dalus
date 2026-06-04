"""Integration tests for the gh-737 SSE-streaming import endpoint
``POST /api/v2/import/openvsp/stream``.

Reuses the same fixture machinery as ``test_openvsp_import_endpoint``
— same up-front validation rules apply, so the four failure-mode
tests (no openvsp / not vsp3 / too large / mutex) are mirrored. The
new tests focus on the streaming contract:

* The response body parses as a sequence of SSE events
* The events arrive in the documented order (``progress`` … ``complete``)
* On a service-side error, an ``error`` event is emitted instead of
  ``complete`` (and the HTTP status is still 200 because the stream
  itself succeeded — error info travels in the payload)
"""

from __future__ import annotations

import json
from collections import OrderedDict
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest


# ---------------------------------------------------------------------------
# Helpers (mirror test_openvsp_import_endpoint)
# ---------------------------------------------------------------------------


def _make_fake_vsp(geoms: list[dict] | None = None) -> ModuleType:
    geoms = geoms or []
    fake = SimpleNamespace()
    fake.LEN_M = 2
    fake.SYM_XZ = 2
    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.SetLengthUnit = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: "VEH"
    fake.FindGeoms = lambda: [g["id"] for g in geoms]
    fake.GetGeomName = lambda gid: next((g["name"] for g in geoms if g["id"] == gid), "")
    fake.GetGeomTypeName = lambda gid: next(
        (g.get("type", "BLANK") for g in geoms if g["id"] == gid), ""
    )
    fake.FindParm = lambda *a, **k: ""
    fake.GetParmVal = lambda pid: 0.0
    return cast(ModuleType, fake)


@pytest.fixture
def client(client_and_db):
    cl, _session_factory = client_and_db
    return cl


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """Parse an SSE stream body into ``[(event_type, data_dict), …]``.

    Mirrors the parser the frontend uses (``frontend/lib/sseStream.ts``).
    """
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type = "message"
        data_str = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_str += line[len("data:") :].strip()
        if not data_str:
            continue
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {"raw": data_str}
        events.append((event_type, data))
    return events


def _stub_import_vsp3(monkeypatch):
    """Patch ``import_vsp3`` with a trivial 1-wing payload so the
    stream's progress events get something to iterate over."""
    from app.converters import openvsp_importer
    from app.schemas.aeroplaneschema import (
        AeroplaneSchema,
        AsbWingSchema,
        WingXSecSchema,
    )

    def _fake_import(path, **_kw):  # noqa: ARG001
        wing = AsbWingSchema(
            name="Main",
            symmetric=True,
            x_secs=[
                WingXSecSchema(xyz_le=[0, 0, 0], chord=0.5, twist=0, airfoil="naca0015"),
                WingXSecSchema(xyz_le=[0, 5, 0], chord=0.2, twist=0, airfoil="naca0015"),
            ],
        )
        ap = AeroplaneSchema(name="StreamTest")
        ap.wings = OrderedDict([("Main", wing)])
        return openvsp_importer.ImportResult(
            aeroplane=ap,
            warnings=[],
            lossy_components=[],
            weight_items=[],
        )

    monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_import)
    from app.services import openvsp_import_service

    monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_import)


# ---------------------------------------------------------------------------
# Validation: stream endpoint must reject same failure modes as JSON endpoint
# ---------------------------------------------------------------------------


class TestStreamValidation:
    def test_503_when_openvsp_missing(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: False)
        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 503

    def test_400_when_not_vsp3(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("notes.txt", b"hi", "text/plain")},
        )
        assert r.status_code == 400

    def test_400_when_both_scaling_params(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        r = client.post(
            "/api/v2/import/openvsp/stream?target_span_m=1.5&scale_factor=0.5",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Streaming contract
# ---------------------------------------------------------------------------


class TestStreamContract:
    def test_success_emits_progress_then_complete(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/event-stream")
        events = _parse_sse(r.text)
        assert events, "no SSE events emitted"
        event_types = [e[0] for e in events]
        # At least one progress event, and the final event is ``complete``.
        assert "progress" in event_types
        assert event_types[-1] == "complete"
        complete_payload = events[-1][1]
        assert "aeroplane_uuid" in complete_payload
        # The aeroplane name comes from the uploaded filename's stem
        # (resolver precedence — see _resolve_aeroplane_name). For
        # "x.vsp3" that's "x". The parsed name ("StreamTest") is only
        # used when no filename is available.
        assert complete_payload["aeroplane_name"] == "x"
        assert complete_payload["n_wings"] == 1

    def test_progress_events_have_pct_and_step(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        events = _parse_sse(r.text)
        progress_events = [e for e in events if e[0] == "progress"]
        assert progress_events, "no progress events"
        for _, payload in progress_events:
            assert "step" in payload
            assert "pct" in payload
            assert isinstance(payload["pct"], int)
            assert 0 <= payload["pct"] <= 100
            assert "detail" in payload
        # pct values should be monotonically non-decreasing.
        pcts = [p["pct"] for _, p in progress_events]
        assert pcts == sorted(pcts), f"progress pct not monotonic: {pcts}"

    def test_error_event_on_service_failure(self, client, monkeypatch):
        """A service-side exception during import → ``error`` event,
        no ``complete``. HTTP status is still 200 (the SSE stream itself
        succeeded; the failure travels in the payload)."""
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)

        def _boom(*_a, **_kw):
            raise RuntimeError("simulated parse failure")

        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _boom)

        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 200  # stream itself opens fine
        events = _parse_sse(r.text)
        event_types = [e[0] for e in events]
        assert "complete" not in event_types
        assert "error" in event_types
        error_payload = next(payload for et, payload in events if et == "error")
        assert "simulated parse failure" in error_payload.get("detail", "")
        assert error_payload.get("status") == 422

    def test_pct_reaches_100_via_complete(self, client, monkeypatch):
        """End-of-import contract: a ``complete`` event always means
        100 %. Frontend can latch on either ``progress.pct == 100`` OR
        ``complete`` to finish the bar."""
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp/stream",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        events = _parse_sse(r.text)
        assert events[-1][0] == "complete"
        # The frontend treats ``complete`` as 100 %. Last progress event
        # should be close to it (≥ 90 %) so the bar doesn't appear stuck.
        progress_events = [e for e in events if e[0] == "progress"]
        if progress_events:
            assert progress_events[-1][1]["pct"] >= 90
