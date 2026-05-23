"""Integration tests for the OpenVSP import endpoint (gh-646)."""

from __future__ import annotations

from types import ModuleType

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_vsp(geoms: list[dict] | None = None, name: str = "Empty") -> ModuleType:
    """Tiny fake vsp module sufficient for the endpoint's smoke flow."""
    geoms = geoms or []
    fake = ModuleType("openvsp")
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
    return fake


@pytest.fixture
def client(client_and_db):
    """Reuse the shared client_and_db fixture (in-memory SQLite + lifespan)."""
    cl, _session_factory = client_and_db
    return cl


# ---------------------------------------------------------------------------
# Endpoint contract tests
# ---------------------------------------------------------------------------


class TestImportEndpoint:
    def test_503_when_openvsp_missing(self, client, monkeypatch):
        """Endpoint reports 503 + actionable hint when openvsp isn't installed."""
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: False)
        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 503
        body = r.json()
        assert "openvsp" in body["detail"].lower()
        assert "setup" in body["detail"].lower()

    def test_400_when_not_vsp3(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert ".vsp3" in r.json()["detail"]

    def test_413_when_file_too_large(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        # 60 MB > 50 MB cap
        big = b"x" * (60 * 1024 * 1024)
        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("big.vsp3", big, "application/octet-stream")},
        )
        assert r.status_code == 413

    def test_success_returns_201_with_warnings(self, client, monkeypatch):
        from app.converters import openvsp_adapter
        from app.services import openvsp_import_service

        # Pretend openvsp is available, and inject a fake module with
        # one PROP geom (which produces a warning + lossy).
        fake = _make_fake_vsp(geoms=[{"id": "G1", "name": "Prop", "type": "PROP"}])
        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        # Reset handler registry to avoid leakage from previous tests.
        from app.converters import openvsp_importer

        openvsp_importer._HANDLERS.clear()
        openvsp_importer._POST_PASSES.clear()
        openvsp_importer._handlers_loaded = False

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("oneram6.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["aeroplane_uuid"]
        assert body["aeroplane_name"]
        # PROP is unsupported → at least one warning.
        assert body["warnings"]
        assert any(w["component_type"] == "PROP" for w in body["warnings"])
        assert "G1" in body["lossy_components"]
