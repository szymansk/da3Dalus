"""Integration tests for the OpenVSP import endpoint (gh-646).

Extended for gh-695 with scaling-parameter coverage:

* ``?target_span_m=<f>`` rescales the imported aeroplane to that span.
* ``?scale_factor=<f>`` directly scales all length-typed fields.
* Mutex (both supplied) → 400.
* Out-of-range numeric inputs → 422.
"""

from __future__ import annotations

from collections import OrderedDict
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_vsp(geoms: list[dict] | None = None, name: str = "Empty") -> ModuleType:
    """Tiny fake vsp module sufficient for the endpoint's smoke flow."""
    geoms = geoms or []
    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
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


# ---------------------------------------------------------------------------
# Scaling-parameter tests (gh-695)
# ---------------------------------------------------------------------------


def _stub_import_vsp3_with_wing(monkeypatch, *, span_m: float, root_chord: float = 0.5):
    """Patch ``import_vsp3`` to yield a deterministic ImportResult with one
    symmetric wing spanning ±``span_m`` (physical span = 2 * span_m).
    """
    from app.converters import openvsp_importer
    from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema, WingXSecSchema

    def _fake_import(path):  # noqa: ARG001 — path is read for fixture only
        wing = AsbWingSchema(
            name="Main",
            symmetric=True,
            x_secs=[
                WingXSecSchema(
                    xyz_le=[0.0, 0.0, 0.0],
                    chord=root_chord,
                    twist=0.0,
                    airfoil="naca0015",
                ),
                WingXSecSchema(
                    xyz_le=[0.0, span_m, 0.0],
                    chord=root_chord * 0.4,
                    twist=0.0,
                    airfoil="naca0015",
                ),
            ],
        )
        ap = AeroplaneSchema(name="ScaledTest")
        ap.wings = OrderedDict([("Main", wing)])
        return openvsp_importer.ImportResult(
            aeroplane=ap,
            warnings=[],
            lossy_components=[],
            weight_items=[],
        )

    # Patch both at the source module and at the alias used by the service.
    monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_import)
    from app.services import openvsp_import_service

    monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_import)


class TestImportEndpointScaling:
    def test_400_when_both_scale_params_supplied(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp?target_span_m=1.5&scale_factor=0.1",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 400
        assert "mutually exclusive" in r.json()["detail"].lower()

    def test_422_when_scale_factor_out_of_range(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        # 50.0 is well above the max of 10.0
        r = client.post(
            "/api/v2/import/openvsp?scale_factor=50.0",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 422
        assert "scale_factor" in r.json()["detail"].lower()

    def test_422_when_target_span_out_of_range(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp?target_span_m=100.0",  # > 50 cap
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 422
        assert "target_span_m" in r.json()["detail"].lower()

    def test_scale_factor_applied_and_warning_emitted(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0, root_chord=0.5)

        r = client.post(
            "/api/v2/import/openvsp?scale_factor=0.5",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        # SCALING warning should appear
        scaling = [w for w in body["warnings"] if w["component_type"] == "SCALING"]
        assert len(scaling) == 1
        assert "scaled" in scaling[0]["reason"].lower()
        assert "masses were not scaled" in scaling[0]["reason"].lower()

    def test_target_span_resolves_to_correct_factor(self, client, monkeypatch):
        """Roundtrip: span_m=10.0 sym → 20m physical; target_span=1.5 → factor 0.075."""
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0, root_chord=0.5)

        r = client.post(
            "/api/v2/import/openvsp?target_span_m=1.5",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        # Look up the persisted wing and verify the y_le of the tip xsec.
        # Tip y_le was 10.0; after factor 0.075 → 0.75. Sym wing → physical span 1.5.
        uuid = body["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/wings/Main")
        assert rs.status_code == 200, rs.text
        wing = rs.json()
        tip_y = wing["x_secs"][1]["xyz_le"][1]
        assert tip_y == pytest.approx(0.75, rel=0.01)

    def test_target_span_on_wingless_returns_422(self, client, monkeypatch):
        from app.converters import openvsp_importer
        from app.schemas.aeroplaneschema import AeroplaneSchema
        from app.services import openvsp_import_service

        def _fake_import(path):  # noqa: ARG001
            return openvsp_importer.ImportResult(
                aeroplane=AeroplaneSchema(name="Wingless"),
                warnings=[],
                lossy_components=[],
                weight_items=[],
            )

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_import)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_import)

        r = client.post(
            "/api/v2/import/openvsp?target_span_m=1.5",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 422
        assert "wing" in r.json()["detail"].lower() or "span" in r.json()["detail"].lower()

    def test_no_scaling_when_no_params(self, client, monkeypatch):
        """Without scale params the importer must NOT emit a SCALING warning."""
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        scaling = [w for w in body["warnings"] if w["component_type"] == "SCALING"]
        assert scaling == []


# ---------------------------------------------------------------------------
# Aeroplane-name tests (post-MVP UX fix)
# ---------------------------------------------------------------------------


class TestImportEndpointAeroplaneName:
    """The aeroplane name must come from (in order of precedence):

    1. Explicit ``?name=`` query param (user-typed in the import dialog).
    2. The original upload filename's stem (so ``cessna172.vsp3`` →
       ``cessna172``).
    3. The converter-supplied fallback (which uses ``path.stem`` —
       previously surfaced as ``tmpXXXX`` because the endpoint writes
       to a NamedTemporaryFile before parsing).
    """

    def test_explicit_name_query_param_overrides_filename(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp?name=My%20Custom%20Plane",
            files={"file": ("cessna172.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        assert r.json()["aeroplane_name"] == "My Custom Plane"

    def test_fallback_to_uploaded_filename_stem(self, client, monkeypatch):
        """No explicit name → use the uploaded filename's stem, NOT the
        tempfile stem the endpoint generates internally.
        """
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("cessna172.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["aeroplane_name"] == "cessna172"
        # Defensive: no `tmp` leaked-tempfile prefix.
        assert not body["aeroplane_name"].startswith("tmp")

    def test_blank_name_param_falls_back_to_filename(self, client, monkeypatch):
        """An explicit empty-or-whitespace ``?name=`` is treated as 'no
        override' so we still get a sane name from the upload filename.
        """
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp?name=%20%20",
            files={"file": ("rv7.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        assert r.json()["aeroplane_name"] == "rv7"

    def test_name_param_is_trimmed(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_wing(monkeypatch, span_m=10.0)

        r = client.post(
            "/api/v2/import/openvsp?name=%20%20Cessna%20172%20%20",
            files={"file": ("ignored.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        assert r.json()["aeroplane_name"] == "Cessna 172"


# ---------------------------------------------------------------------------
# gh-693: Phase 1.5 — Fuselage + WeightItem DB persistence
# ---------------------------------------------------------------------------


def _stub_import_vsp3_with_fuselage_and_weights(monkeypatch):
    """Patch ``import_vsp3`` to yield an ImportResult with one wing,
    one fuselage (3 super-ellipse xsecs), and 2 weight items.
    """
    from app.converters import openvsp_importer
    from app.schemas.aeroplaneschema import (
        AeroplaneSchema,
        AsbWingSchema,
        FuselageSchema,
        FuselageXSecSuperEllipseSchema,
        WingXSecSchema,
    )
    from app.schemas.weight_item import WeightItemWrite

    def _fake_import(path):  # noqa: ARG001 — fixture-only path
        wing = AsbWingSchema(
            name="Main",
            symmetric=True,
            x_secs=[
                WingXSecSchema(
                    xyz_le=[0.0, 0.0, 0.0],
                    chord=0.5,
                    twist=0.0,
                    airfoil="naca0015",
                ),
                WingXSecSchema(
                    xyz_le=[0.0, 5.0, 0.0],
                    chord=0.2,
                    twist=0.0,
                    airfoil="naca0015",
                ),
            ],
        )
        fuse = FuselageSchema(
            name="Fuselage",
            x_secs=[
                FuselageXSecSuperEllipseSchema(
                    xyz=[0.0, 0.0, 0.0], a=0.0, b=0.0, n=2.0
                ),
                FuselageXSecSuperEllipseSchema(
                    xyz=[1.0, 0.0, 0.0], a=0.4, b=0.3, n=2.0
                ),
                FuselageXSecSuperEllipseSchema(
                    xyz=[2.0, 0.0, 0.0], a=0.0, b=0.0, n=2.0
                ),
            ],
        )
        ap = AeroplaneSchema(name="WithFuse")
        ap.wings = OrderedDict([("Main", wing)])
        ap.fuselages = OrderedDict([("Fuselage", fuse)])

        return openvsp_importer.ImportResult(
            aeroplane=ap,
            warnings=[],
            lossy_components=[],
            weight_items=[
                WeightItemWrite(
                    name="Battery",
                    mass_kg=1.5,
                    x_m=0.3,
                    y_m=0.0,
                    z_m=0.05,
                    category="other",
                ),
                WeightItemWrite(
                    name="ESC",
                    mass_kg=0.08,
                    x_m=0.5,
                    y_m=0.1,
                    z_m=0.0,
                    category="other",
                ),
            ],
        )

    from app.services import openvsp_import_service

    monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_import)
    monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_import)


class TestImportEndpointPersistence:
    """After a successful import the DB must contain the parsed
    fuselages and weight items — not just the wing.

    Pre-gh-693 the importer counted them in the response envelope but
    silently dropped them on the way to the DB, leaving the user with
    a wing-only aeroplane that couldn't be scaled or analysed end-to-end.
    """

    def test_fuselage_persisted_after_import(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["n_fuselages"] == 1

        # Fuselage must be retrievable through the REST API.
        uuid = body["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        assert rs.status_code == 200, rs.text
        fuse = rs.json()
        assert fuse["name"] == "Fuselage"
        assert len(fuse["x_secs"]) == 3
        # Middle xsec carries the non-trivial geometry.
        mid = fuse["x_secs"][1]
        assert mid["a"] == pytest.approx(0.4)
        assert mid["b"] == pytest.approx(0.3)
        assert mid["xyz"] == [pytest.approx(1.0), pytest.approx(0.0), pytest.approx(0.0)]

    def test_weight_items_persisted_after_import(self, client, monkeypatch):
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["n_weight_items"] == 2

        # Weight items must be readable via the existing weight-items
        # endpoint. The list-endpoint returns a WeightSummary envelope
        # ``{items, total_mass_kg, cg_x_m, cg_y_m, cg_z_m}``.
        uuid = body["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/weight-items")
        assert rs.status_code == 200, rs.text
        summary = rs.json()
        items = summary["items"]
        assert len(items) == 2
        names = sorted(it["name"] for it in items)
        assert names == ["Battery", "ESC"]
        battery = next(it for it in items if it["name"] == "Battery")
        assert battery["mass_kg"] == pytest.approx(1.5)
        assert battery["x_m"] == pytest.approx(0.3)
        assert battery["category"] == "other"
        # CG of (1.5 kg @ x=0.3) + (0.08 kg @ x=0.5) ≈ 0.31013 m. The
        # endpoint rounds to 6 decimals — keep the tolerance loose.
        assert summary["total_mass_kg"] == pytest.approx(1.58)
        expected_cg = (1.5 * 0.3 + 0.08 * 0.5) / 1.58
        assert summary["cg_x_m"] == pytest.approx(expected_cg, abs=1e-5)

    def test_fuselage_failure_becomes_warning_not_crash(self, client, monkeypatch):
        """A broken fuselage write must not roll back the whole import —
        the wing should still land, and the failure must surface as an
        importer warning so the user sees what happened.
        """
        from app.services import fuselage_service, openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        def _boom(*_a, **_kw):
            raise RuntimeError("simulated DB failure on fuselage write")

        monkeypatch.setattr(fuselage_service, "create_fuselage", _boom)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        # Wing still landed.
        uuid = body["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/wings/Main")
        assert rs.status_code == 200, rs.text
        # Failure surfaced as a FUSELAGE-typed warning.
        fuse_warnings = [w for w in body["warnings"] if w["component_type"] == "FUSELAGE"]
        assert fuse_warnings, body["warnings"]
        assert "simulated DB failure" in fuse_warnings[0]["reason"]
