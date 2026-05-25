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

    def _fake_import(path, **_kw):  # noqa: ARG001 — path/kwargs are read for fixture only
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

        def _fake_import(path, **_kw):  # noqa: ARG001
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

    def _fake_import(path, **_kw):  # noqa: ARG001 — fixture-only path
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

    def test_fuselage_step_path_persisted_on_import(self, client, monkeypatch, tmp_path):
        """gh-729: a real OpenVSP STEP export should land on disk and
        the relative path should be recorded on ``FuselageModel.step_path``.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        # Fake VSP exporter — write a small file with the geom-id baked
        # in so we can verify the per-geom isolation logic ran.
        from app.services import openvsp_step_export_service

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text(f"FAKE STEP for {geom_name} ({gid})")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        monkeypatch.setattr(
            openvsp_step_export_service, "export_geom_step", _fake_export
        )
        # ``import_openvsp_file`` looks up vsp via openvsp_adapter — give
        # it a stub so the ``is_available`` gate passes.
        from app.converters import openvsp_adapter

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        # Make the stub import_vsp3 record the geom-id → fuselage-name
        # mapping that ``_persist_aeroplane`` needs.
        from app.converters import openvsp_importer

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        # GET the fuselage and check step_path is populated.
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        assert rs.status_code == 200, rs.text
        body = rs.json()
        assert body["step_path"] is not None
        # File exists on disk.
        from pathlib import Path
        full_path = Path(tmp_path) / body["step_path"]
        assert full_path.exists()
        assert "FAKE STEP" in full_path.read_text()

        # GET the STEP-download endpoint serves the file.
        rs_step = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage/step")
        assert rs_step.status_code == 200, rs_step.text
        assert rs_step.headers["content-type"] == "model/step"
        assert b"FAKE STEP" in rs_step.content

    def test_step_endpoint_404_when_no_step_path(self, client, monkeypatch):
        """A CAD-created fuselage (no STEP export) → 404 with a
        helpful message, not a 500.
        """
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        uuid = r.json()["aeroplane_uuid"]
        # No real STEP export ran — step_path stays None.
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage/step")
        assert rs.status_code == 404
        assert "STEP" in rs.json()["detail"]

    def test_fuselage_solid_step_path_persisted_on_import(
        self, client, monkeypatch, tmp_path
    ):
        """gh-731: when the surface STEP export succeeds, the sewing
        service should run and the resulting Solid-STEP relative path
        must land on ``FuselageModel.solid_step_path``.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        # Fake gh-729 exporter — must run so gh-731 has source input.
        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text(f"FAKE SURFACE STEP for {geom_name} ({gid})")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        monkeypatch.setattr(
            openvsp_step_export_service, "export_geom_step", _fake_export
        )

        # Fake sewing service — write a small file marked as solid so we
        # can verify it's served back through the endpoint.
        def _fake_sew(source_rel_step, aeroplane_uuid, geom_name):
            out_dir = openvsp_solid_sewing_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_solid_sewing_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}_solid.stp"
            target.write_text(f"FAKE SOLID STEP for {geom_name}")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        monkeypatch.setattr(
            openvsp_solid_sewing_service, "sew_imported_geom_to_solid", _fake_sew
        )

        # Stub VSP adapter so the gh-729 codepath runs.
        from app.converters import openvsp_adapter

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        # Provide a geom-id → fuselage-name mapping the import service expects.
        from app.converters import openvsp_importer

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        assert rs.status_code == 200, rs.text
        body = rs.json()
        assert body["step_path"] is not None  # gh-729
        assert body["solid_step_path"] is not None  # gh-731
        assert body["solid_step_path"].endswith("_solid.stp")
        from pathlib import Path
        full_path = Path(tmp_path) / body["solid_step_path"]
        assert full_path.exists()
        assert "FAKE SOLID STEP" in full_path.read_text()

        # The /solid_step endpoint must serve the file.
        rs_solid = client.get(
            f"/aeroplanes/{uuid}/fuselages/Fuselage/solid_step"
        )
        assert rs_solid.status_code == 200, rs_solid.text
        assert rs_solid.headers["content-type"] == "model/step"
        assert b"FAKE SOLID STEP" in rs_solid.content
        assert "_solid.stp" in rs_solid.headers.get("content-disposition", "")

    def test_solid_step_endpoint_404_when_no_solid_step_path(
        self, client, monkeypatch
    ):
        """A fuselage without a sewed solid (CAD-created or sewing
        failed) → 404 with the actionable "use /step and sew
        manually" hint.
        """
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage/solid_step")
        assert rs.status_code == 404
        assert "Solid STEP" in rs.json()["detail"]
        assert "/step" in rs.json()["detail"]

    def test_solid_step_skipped_when_sewing_fails(self, client, monkeypatch, tmp_path):
        """Sewing failures must not abort the import — the import
        succeeds, ``step_path`` still lands, and ``solid_step_path``
        stays null.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text("FAKE")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        monkeypatch.setattr(
            openvsp_step_export_service, "export_geom_step", _fake_export
        )
        # Sewing returns None → solid_step_path stays null.
        monkeypatch.setattr(
            openvsp_solid_sewing_service,
            "sew_imported_geom_to_solid",
            lambda **kw: None,
        )

        from app.converters import openvsp_adapter, openvsp_importer

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        body = rs.json()
        assert body["step_path"] is not None
        assert body["solid_step_path"] is None

    def test_slicer_refines_xsecs_when_step_present(self, client, monkeypatch, tmp_path):
        """gh-732: a successful slicer run on the gh-729 STEP must
        REPLACE the handler-built 3-xsec schema with a finer
        slicer-derived xsec list, while keeping the gh-729 surface
        STEP and gh-731 solid STEP paths intact.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        # Stub gh-729 STEP export.
        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text("FAKE SURFACE STEP")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        def _fake_sew(source_rel_step, aeroplane_uuid, geom_name):
            out_dir = openvsp_solid_sewing_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_solid_sewing_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}_solid.stp"
            target.write_text("FAKE SOLID STEP")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        # Stub the slicer to emulate a 30-xsec refinement. Values are
        # in cadquery's mm convention; the service must scale them to
        # metres before storing.
        from cad_designer.aerosandbox import slicing as _slicing

        def _fake_slicer(step_path, **_kw):
            xsecs = [
                {
                    "xyz": [100.0 * i, 0.0, 50.0],
                    "a": 150.0,
                    "b": 120.0,
                    "n": 2.5,
                }
                for i in range(30)
            ]
            metrics = {
                "original_volume": 0.001,
                "original_area": 0.01,
                "reconstructed_volume": 0.001,
                "reconstructed_area": 0.01,
                "volume_ratio": 0.9,
                "area_ratio": 0.95,
            }
            return xsecs, metrics

        monkeypatch.setattr(openvsp_step_export_service, "export_geom_step", _fake_export)
        monkeypatch.setattr(
            openvsp_solid_sewing_service, "sew_imported_geom_to_solid", _fake_sew
        )
        monkeypatch.setattr(_slicing, "slice_step_to_fuselage", _fake_slicer)
        # Bypass the world-frame X-dominance gate — the stub STEP file
        # is plain text, not cadquery-readable, so the real gate would
        # always say "skip". The gate itself is unit-tested in
        # test_openvsp_solid_sewing.py-style direct tests of the helper.
        monkeypatch.setattr(
            openvsp_import_service, "_is_x_dominant_fuselage", lambda _p: True
        )

        from app.converters import openvsp_adapter, openvsp_importer

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        assert rs.status_code == 200, rs.text
        body = rs.json()
        # 30 xsecs from the slicer, NOT the 3 from the handler stub.
        assert len(body["x_secs"]) == 30, (
            f"slicer refinement didn't replace handler xsecs "
            f"(got {len(body['x_secs'])})"
        )
        # Values must have been scaled from mm to metres.
        mid = body["x_secs"][15]
        assert mid["a"] == pytest.approx(0.150)  # 150 mm → 0.15 m
        assert mid["b"] == pytest.approx(0.120)  # 120 mm → 0.12 m
        assert mid["xyz"][0] == pytest.approx(1.500)  # 1500 mm → 1.5 m
        assert mid["n"] == pytest.approx(2.5)
        # gh-729 + gh-731 paths still intact after refinement.
        assert body["step_path"] is not None
        assert body["solid_step_path"] is not None

    def test_slicer_skipped_for_non_x_dominant_fuselage(self, client, monkeypatch, tmp_path):
        """gh-732: Cessna sub-fuselages (Struts oriented along Z,
        MainStrut diagonal) are rotated 90° in OpenVSP. Slicing them
        along X would either cut perpendicular to the long axis
        (garbage xsecs) or rotate the model and put xyz in the wrong
        frame. Both are visually degenerate. The handler schema must
        win when the world-frame X-dominance gate fires.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )
        from cad_designer.aerosandbox import slicing as _slicing

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text("FAKE")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        # Force the X-dominance gate to refuse refinement.
        monkeypatch.setattr(
            openvsp_import_service, "_is_x_dominant_fuselage", lambda _p: False
        )

        # Slicer must not be called at all — make it crash if it is.
        def _slicer_must_not_run(*_a, **_kw):
            raise AssertionError("slicer must not run when gate refuses")

        monkeypatch.setattr(openvsp_step_export_service, "export_geom_step", _fake_export)
        monkeypatch.setattr(
            openvsp_solid_sewing_service,
            "sew_imported_geom_to_solid",
            lambda **kw: None,
        )
        monkeypatch.setattr(_slicing, "slice_step_to_fuselage", _slicer_must_not_run)

        from app.converters import openvsp_adapter, openvsp_importer

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        body = rs.json()
        # Gate refused → handler schema (3 xsecs) preserved.
        assert len(body["x_secs"]) == 3
        # Handler values unchanged (gh-693 stub: a=0.4 at xsec[1]).
        assert body["x_secs"][1]["a"] == pytest.approx(0.4)

    def test_slicer_failure_keeps_handler_schema(self, client, monkeypatch, tmp_path):
        """gh-732: when the slicer raises or returns <2 xsecs, the
        handler-built schema must remain untouched and the import
        must still succeed.
        """
        from app.core import config as core_config
        from app.services import openvsp_import_service

        monkeypatch.setattr(openvsp_import_service, "is_importer_available", lambda: True)
        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _stub_import_vsp3_with_fuselage_and_weights(monkeypatch)

        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )
        from cad_designer.aerosandbox import slicing as _slicing

        def _fake_export(vsp, gid, geom_name, aeroplane_uuid):
            out_dir = openvsp_step_export_service.step_storage_dir(aeroplane_uuid)
            stem = openvsp_step_export_service.sanitize_geom_filename(geom_name)
            target = out_dir / f"{stem}.stp"
            target.write_text("FAKE SURFACE STEP")
            from pathlib import Path
            return str(target.relative_to(Path(tmp_path)))

        def _boom_slicer(*_a, **_kw):
            raise RuntimeError("simulated OCC failure inside slicer")

        monkeypatch.setattr(openvsp_step_export_service, "export_geom_step", _fake_export)
        # No solid available — slicer falls back to surface STEP.
        monkeypatch.setattr(
            openvsp_solid_sewing_service,
            "sew_imported_geom_to_solid",
            lambda **kw: None,
        )
        monkeypatch.setattr(_slicing, "slice_step_to_fuselage", _boom_slicer)

        from app.converters import openvsp_adapter, openvsp_importer

        class _StubVsp:
            pass

        monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: _StubVsp())

        orig_fake = openvsp_importer.import_vsp3

        def _fake_with_gids(path, **kw):
            r = orig_fake(path, **kw)
            r.fuselage_geom_ids = {"FAKE_GID_FUSE": "Fuselage"}
            return r

        monkeypatch.setattr(openvsp_importer, "import_vsp3", _fake_with_gids)
        monkeypatch.setattr(openvsp_import_service, "import_vsp3", _fake_with_gids)

        r = client.post(
            "/api/v2/import/openvsp",
            files={"file": ("x.vsp3", b"<vsp3/>", "application/octet-stream")},
        )
        assert r.status_code == 201, r.text
        uuid = r.json()["aeroplane_uuid"]
        rs = client.get(f"/aeroplanes/{uuid}/fuselages/Fuselage")
        assert rs.status_code == 200, rs.text
        body = rs.json()
        # Slicer raised → handler's 3-xsec schema preserved.
        assert len(body["x_secs"]) == 3
        # Original handler values intact (gh-693 stub uses a=0.4 at xsec[1]).
        assert body["x_secs"][1]["a"] == pytest.approx(0.4)

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
