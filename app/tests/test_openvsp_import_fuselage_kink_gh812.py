"""gh-812: the fuselage xsec slicer must read the faithful **surface**
STEP, not the sewn **solid** STEP.

Root cause (proven against the Romo ``FuselageGeom`` DB record): the
importer sliced ``rel_solid or rel_step`` — i.e. it preferred the gh-731
sewn solid. At a sharply-curved loft region (Romo's nose-body fillet,
x ≈ 3.377 m) the sewn solid carries internal seam faces; a section cut
there fragments into dozens of contours that ``select_outer_contour``
cannot resolve, so ``fit_shape_area_superellipse`` places the section
centre at the weighted-mean y of an asymmetric point set (+0.70 m) — the
visible lateral kink. The surface STEP is the faithful VSP geometry and
slices into a single clean outline at the same station.

The fix prefers the surface STEP for xsec geometry; the solid stays a
fallback (and is still used for the construction download + volume
metric).
"""

from __future__ import annotations

import pytest


# --------------------------------------------------------------------------- #
# Fast unit test — the source-selection decision (drives the fix).
# --------------------------------------------------------------------------- #


def test_xsec_slice_source_prefers_surface_over_solid():
    """gh-812: with both STEPs present, slice the surface, not the solid."""
    from app.services.openvsp_import_service import _select_xsec_slice_source

    chosen = _select_xsec_slice_source("FuselageGeom.stp", "FuselageGeom_solid.stp")
    assert chosen == "FuselageGeom.stp"


def test_xsec_slice_source_falls_back_to_solid_when_surface_missing():
    """If the surface export is somehow absent, the solid is the fallback."""
    from app.services.openvsp_import_service import _select_xsec_slice_source

    assert _select_xsec_slice_source(None, "FuselageGeom_solid.stp") == "FuselageGeom_solid.stp"


def test_xsec_slice_source_none_when_neither_present():
    from app.services.openvsp_import_service import _select_xsec_slice_source

    assert _select_xsec_slice_source(None, None) is None


# --------------------------------------------------------------------------- #
# Slow end-to-end guard — real OpenVSP + CadQuery import of romo.vsp3.
#
# Drives the full persist wiring (export → sew → slice → refine → persist)
# for Romo's ``FuselageGeom`` and asserts no section drifts laterally. This
# catches a regression that bypasses ``_select_xsec_slice_source`` and slices
# the sewn solid again (which fragments at the nose-body fillet → y ≈ +0.70 m).
# --------------------------------------------------------------------------- #

ROMO_VSP3 = "components/aircraft/vsp/romo.vsp3"


@pytest.mark.slow
def test_romo_fuselage_geom_has_no_lateral_kink(client_and_db, tmp_path, monkeypatch):
    pytest.importorskip("openvsp")
    pytest.importorskip("cadquery")

    from collections import OrderedDict
    from pathlib import Path

    if not Path(ROMO_VSP3).exists():
        pytest.skip(f"{ROMO_VSP3} not fetched in this checkout (see fetch_models.sh)")

    from app.core.config import settings
    from app.converters import openvsp_importer
    from app.models.aeroplanemodel import (
        AeroplaneModel,
        FuselageModel,
        FuselageXSecSuperEllipseModel,
    )
    from app.services.openvsp_import_service import _persist_aeroplane

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))

    # Parse (loads the VSP model into the live session) and trim to just
    # FuselageGeom to bound the wall-clock — the kink is geom-local.
    result = openvsp_importer.import_vsp3(Path(ROMO_VSP3))
    fuselages = result.aeroplane.fuselages or {}
    assert "FuselageGeom" in fuselages
    result.aeroplane.fuselages = OrderedDict(FuselageGeom=fuselages["FuselageGeom"])
    result.aeroplane.wings = OrderedDict()
    result.fuselage_geom_ids = {
        g: n for g, n in (result.fuselage_geom_ids or {}).items() if n == "FuselageGeom"
    }

    _, session_factory = client_and_db
    db = session_factory()
    try:
        uuid_str, _ = _persist_aeroplane(db, result, name="romo-gh812")
        db.commit()

        ap = db.query(AeroplaneModel).filter_by(uuid=uuid_str).one()
        fuse = db.query(FuselageModel).filter_by(aeroplane_id=ap.id, name="FuselageGeom").one()
        xsecs = db.query(FuselageXSecSuperEllipseModel).filter_by(fuselage_id=fuse.id).all()
    finally:
        db.close()

    assert len(xsecs) >= 2
    # The handler frame is centred on y=0; no refined section may drift more
    # than 5 cm laterally. Pre-fix (solid slice) the fillet section sat at
    # y ≈ +0.70 m.
    max_abs_y = max(abs(xs.xyz[1]) for xs in xsecs)
    assert max_abs_y < 0.05, (
        f"lateral kink: a FuselageGeom section is off-centre by {max_abs_y:.3f} m "
        f"(centres y = {[round(xs.xyz[1], 3) for xs in xsecs]})"
    )
