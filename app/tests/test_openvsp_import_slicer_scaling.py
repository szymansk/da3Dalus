"""Frame-pure fuselage refinement + post-refinement scaling (gh-765/769).

Clean architecture (supersedes the gh-766 ``factor``-in-slicer workaround):

* ``_try_slicer_refinement`` runs entirely in the **unscaled** STEP frame
  — it takes no scale factor and just converts the slicer's mm output to
  metres.
* The import scale is applied **once, after refinement**, by
  ``_scale_fuselage_xsecs`` (xsec geometry) and ``scale_geom_step`` (the
  stored STEP download files), so xsecs and STEP both land at model scale.

The CAD slicer is mocked so these tests run without OpenVSP / CadQuery.
"""

from __future__ import annotations

import sys
import types
from collections import OrderedDict
from unittest.mock import MagicMock

import pytest

from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
)


def _fuse() -> FuselageSchema:
    """A handler-built (unscaled) fuselage: length 10 m, a=1.0/b=0.5 m mid."""
    return FuselageSchema(
        name="Body",
        symmetric=False,
        x_secs=[
            FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.0, 0.0], a=0.2, b=0.1, n=2.0),
            FuselageXSecSuperEllipseSchema(xyz=[5.0, 0.0, 0.0], a=1.0, b=0.5, n=2.0),
            FuselageXSecSuperEllipseSchema(xyz=[10.0, 0.0, 0.0], a=0.2, b=0.1, n=2.0),
        ],
    )


# --------------------------------------------------------------------------- #
# _try_slicer_refinement — frame-pure (no scale factor)
#
# (``_scale_fuselage_xsecs`` and ``_scale_aeroplane_lengths`` are covered in
# test_openvsp_import_scaling.py, the canonical scaling-helpers suite.)
# --------------------------------------------------------------------------- #


@pytest.fixture
def mock_slicer(monkeypatch, tmp_path):
    """Patch the CAD slicer; ``slice_step_at_stations`` returns mm output."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    (tmp_path / "body.stp").write_text("dummy step")

    mm_xsecs = [
        {"xyz": [0.0, 0.0, 0.0], "a": 200.0, "b": 100.0, "n": 2.0},
        {"xyz": [5000.0, 0.0, 0.0], "a": 1000.0, "b": 500.0, "n": 2.0},
        {"xyz": [10000.0, 0.0, 0.0], "a": 200.0, "b": 100.0, "n": 2.0},
    ]
    fake = types.ModuleType("cad_designer.aerosandbox.slicing")
    fake.slice_step_at_stations = MagicMock(return_value=(mm_xsecs, {"area_ratio": 1.0}))
    fake.slice_step_to_fuselage = MagicMock(return_value=(mm_xsecs, {}))
    fake.vsp_anchored_x_stations = MagicMock(return_value=[0.0, 5000.0, 10000.0])
    monkeypatch.setitem(sys.modules, "cad_designer.aerosandbox.slicing", fake)
    return fake


def test_slicer_refinement_is_frame_pure_mm_to_m(mock_slicer):
    """Refinement converts mm→m only — no scale factor, no parameter."""
    from app.services.openvsp_import_service import _try_slicer_refinement

    refined = _try_slicer_refinement("body.stp", _fuse(), "Body")

    assert refined is not None
    # Mid-section: 1000 mm → 1.0 m (NOT scaled by any import factor here).
    assert max(xs.a for xs in refined) == pytest.approx(1.0)
    x_span = max(xs.xyz[0] for xs in refined) - min(xs.xyz[0] for xs in refined)
    assert x_span == pytest.approx(10.0)


def test_slicer_refinement_takes_no_factor_argument():
    """The gh-766 ``factor`` parameter is gone (frame-pure by construction)."""
    import inspect

    from app.services.openvsp_import_service import _try_slicer_refinement

    params = inspect.signature(_try_slicer_refinement).parameters
    assert "factor" not in params
    assert "scale_factor" not in params


# --------------------------------------------------------------------------- #
# _scale_aeroplane_lengths — no longer touches fuselages (gh-765)
# --------------------------------------------------------------------------- #


def test_scale_aeroplane_lengths_leaves_fuselages_untouched():
    """Fuselage scaling moved to the persist path; this helper must not
    double-scale fuselages."""
    from app.schemas.aeroplaneschema import AeroplaneSchema
    from app.services.openvsp_import_service import _scale_aeroplane_lengths

    ap = AeroplaneSchema(name="t")
    ap.fuselages = {"Body": _fuse()}
    _scale_aeroplane_lengths(ap, 0.1)

    body = ap.fuselages["Body"]
    assert body.x_secs[1].a == pytest.approx(1.0)  # unchanged
    assert body.x_secs[-1].xyz[0] == pytest.approx(10.0)  # unchanged


# --------------------------------------------------------------------------- #
# scale_geom_step — scale the stored STEP download to model scale (gh-769)
# --------------------------------------------------------------------------- #


def test_scale_geom_step_scales_bounding_box(monkeypatch, tmp_path):
    """A stored STEP is rewritten at model scale; its bbox shrinks by factor.

    Uses real CadQuery (gated by ``importorskip`` — installed in the fast CI
    tier, like the existing solid-sewing / step-export tests), so the
    ``scale_geom_step`` body is exercised for coverage rather than mocked.
    """
    cq = pytest.importorskip("cadquery")
    from cadquery import exporters

    from app.core.config import settings
    from app.services import openvsp_step_export_service as step_svc

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    rel = "openvsp_imports/uuid/body.stp"
    src = tmp_path / rel
    src.parent.mkdir(parents=True, exist_ok=True)
    exporters.export(
        cq.Workplane("XY").box(10, 4, 2), str(src), exporters.ExportTypes.STEP
    )

    new_rel = step_svc.scale_geom_step(rel, 0.1, "uuid")
    assert new_rel is not None

    scaled = cq.importers.importStep(str(tmp_path / new_rel)).val()
    bb = scaled.BoundingBox()
    assert bb.xlen == pytest.approx(1.0, abs=1e-3)
    assert bb.ylen == pytest.approx(0.4, abs=1e-3)
    assert bb.zlen == pytest.approx(0.2, abs=1e-3)


def test_scale_geom_step_factor_one_returns_same_path(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import openvsp_step_export_service as step_svc

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    assert step_svc.scale_geom_step("x/y.stp", 1.0, "x") == "x/y.stp"


def test_scale_geom_step_missing_file_returns_none(tmp_path, monkeypatch):
    pytest.importorskip("cadquery")
    from app.core.config import settings
    from app.services import openvsp_step_export_service as step_svc

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    assert step_svc.scale_geom_step("does/not/exist.stp", 0.5, "u") is None


def test_scale_geom_step_invalid_step_returns_none(tmp_path, monkeypatch):
    """A corrupt/unreadable STEP fails gracefully (best-effort): None, no raise."""
    pytest.importorskip("cadquery")
    from app.core.config import settings
    from app.services import openvsp_step_export_service as step_svc

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    (tmp_path / "bad.stp").write_text("this is not a STEP file")
    assert step_svc.scale_geom_step("bad.stp", 0.5, "u") is None


# --------------------------------------------------------------------------- #
# _persist_aeroplane — fuselage scaling applied once, after refinement (gh-765)
#
# CAD-free: OpenVSP / CadQuery are mocked so these run in the `fast` CI job
# (which excludes requires_cadquery/openvsp) and exercise the persist branches.
# --------------------------------------------------------------------------- #


def _import_result_with_fuselage(**geom_ids):
    from app.converters.openvsp_importer import ImportResult

    ap = AeroplaneSchema(name="F")
    ap.fuselages = OrderedDict([("Body", _fuse())])
    return ImportResult(aeroplane=ap, fuselage_geom_ids=dict(geom_ids))


def _read_fuselage(db, uuid):
    from app.models.aeroplanemodel import AeroplaneModel, FuselageModel

    ap = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == uuid).first()
    return db.query(FuselageModel).filter(FuselageModel.aeroplane_id == ap.id).first()


def test_persist_scales_fuselage_xsecs_when_vsp_unavailable(client_and_db, monkeypatch):
    """vsp unavailable → no STEP path; the handler xsecs are scaled once."""
    _client, SessionLocal = client_and_db
    from app.converters import openvsp_adapter
    from app.services import openvsp_import_service as svc

    monkeypatch.setattr(openvsp_adapter, "is_available", lambda: False)

    db = SessionLocal()
    uuid, _name = svc._persist_aeroplane(
        db, _import_result_with_fuselage(), scale_factor=0.5
    )
    db.commit()

    f = _read_fuselage(db, uuid)
    # _fuse() mid-section a=1.0 → scaled 0.5; length 10 m → 5 m.
    assert max(s.a for s in f.x_secs) == pytest.approx(0.5)
    xs = [s.xyz[0] for s in f.x_secs]
    assert max(xs) - min(xs) == pytest.approx(5.0)
    db.close()


def test_persist_scales_refined_xsecs_and_step_with_vsp(client_and_db, monkeypatch):
    """vsp present → STEP export/sew/slice (mocked); the refined xsecs and
    the stored STEP files are both scaled by the import factor."""
    _client, SessionLocal = client_and_db
    from app.converters import openvsp_adapter
    from app.services import openvsp_import_service as svc
    from app.services import (
        openvsp_solid_sewing_service as sew_svc,
    )
    from app.services import (
        openvsp_step_export_service as step_svc,
    )

    monkeypatch.setattr(openvsp_adapter, "is_available", lambda: True)
    monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: object())
    monkeypatch.setattr(step_svc, "export_geom_step", lambda **kw: "imp/u/body.stp")
    monkeypatch.setattr(
        sew_svc, "sew_imported_geom_to_solid", lambda **kw: "imp/u/body_solid.stp"
    )
    scale_calls: list[tuple[str, float]] = []
    monkeypatch.setattr(
        step_svc,
        "scale_geom_step",
        lambda rel, factor, uuid: (scale_calls.append((rel, factor)) or rel),
    )
    # Slicer returns an UNSCALED refined list (mid a=2.0); persist scales it.
    refined = [
        FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.0, 0.0], a=0.0, b=0.0, n=2.0),
        FuselageXSecSuperEllipseSchema(xyz=[10.0, 0.0, 0.0], a=2.0, b=1.0, n=2.0),
    ]
    monkeypatch.setattr(svc, "_try_slicer_refinement", lambda *a, **k: refined)

    db = SessionLocal()
    uuid, _name = svc._persist_aeroplane(
        db, _import_result_with_fuselage(GID1="Body"), scale_factor=0.5
    )
    db.commit()

    f = _read_fuselage(db, uuid)
    # refined mid a=2.0 → scaled 1.0 (proves slicer output, not handler, won).
    assert max(s.a for s in f.x_secs) == pytest.approx(1.0)
    # both stored STEP files were scaled by the same factor.
    assert ("imp/u/body.stp", 0.5) in scale_calls
    assert ("imp/u/body_solid.stp", 0.5) in scale_calls
    db.close()
