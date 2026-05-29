"""Regression tests for fuselage slicer refinement under scaling (gh-765).

Bug: importing a ``.vsp3`` with a custom wing span scaled the Python
schema (wings + fuselage xsecs) correctly, but the fuselage slicer
refinement (gh-732) re-derived xsecs from a STEP exported from the
**unscaled** OpenVSP model and overwrote the scaled schema with
full-size cross-sections — producing a giant out-of-scale fuselage.

These tests pin down that ``_try_slicer_refinement``:
  * slices the (full-size) STEP in the full-size frame — the x-stations
    handed to the slicer are recovered from the scaled handler schema by
    dividing out ``factor``;
  * scales the slicer's full-size output back down by ``factor`` so the
    refined xsecs match the rest of the scaled aeroplane.

The CAD slicer is mocked so the test runs without OpenVSP / CadQuery.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from app.schemas.aeroplaneschema import (
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
)


def _scaled_handler_fuse(factor: float) -> FuselageSchema:
    """A handler-built fuselage already scaled by ``factor``.

    Full-size body: length 10 m, half-axes a=1.0 m / b=0.5 m. After the
    schema-level scaling that runs before persistence, every length is
    multiplied by ``factor``.
    """
    return FuselageSchema(
        name="Body",
        symmetric=False,
        x_secs=[
            FuselageXSecSuperEllipseSchema(
                xyz=[0.0 * factor, 0.0, 0.0], a=0.2 * factor, b=0.1 * factor, n=2.0
            ),
            FuselageXSecSuperEllipseSchema(
                xyz=[5.0 * factor, 0.0, 0.0], a=1.0 * factor, b=0.5 * factor, n=2.0
            ),
            FuselageXSecSuperEllipseSchema(
                xyz=[10.0 * factor, 0.0, 0.0], a=0.2 * factor, b=0.1 * factor, n=2.0
            ),
        ],
    )


@pytest.fixture
def mock_slicer(monkeypatch, tmp_path):
    """Patch the CAD slicer module + artifacts dir.

    ``slice_step_at_stations`` returns FULL-SIZE output (mm) — simulating
    a slice of the unscaled STEP. The real ``vsp_anchored_x_stations`` is
    replaced by a spy that just records the handler dicts it was given so
    we can assert the frame they were computed in.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", str(tmp_path))
    (tmp_path / "body.stp").write_text("dummy step")

    # Full-size slicer output (mm): body half-axes 1000 mm / 500 mm at
    # the mid station, tapering to 200 mm / 100 mm at the ends. Length
    # 10 m == 10000 mm.
    full_size_xsecs = [
        {"xyz": [0.0, 0.0, 0.0], "a": 200.0, "b": 100.0, "n": 2.0},
        {"xyz": [5000.0, 0.0, 0.0], "a": 1000.0, "b": 500.0, "n": 2.0},
        {"xyz": [10000.0, 0.0, 0.0], "a": 200.0, "b": 100.0, "n": 2.0},
    ]

    slice_at_stations = MagicMock(return_value=(full_size_xsecs, {"area_ratio": 1.0}))
    anchored_stations = MagicMock(return_value=[0.0, 5000.0, 10000.0])
    slice_to_fuselage = MagicMock(return_value=(full_size_xsecs, {}))

    fake_mod = types.ModuleType("cad_designer.aerosandbox.slicing")
    fake_mod.slice_step_at_stations = slice_at_stations
    fake_mod.slice_step_to_fuselage = slice_to_fuselage
    fake_mod.vsp_anchored_x_stations = anchored_stations
    monkeypatch.setitem(sys.modules, "cad_designer.aerosandbox.slicing", fake_mod)

    return types.SimpleNamespace(
        slice_at_stations=slice_at_stations,
        anchored_stations=anchored_stations,
    )


def test_slicer_refinement_scales_output_by_factor(mock_slicer):
    """Refined xsecs from a full-size STEP must be scaled by ``factor``.

    With factor=0.1 the slicer returns a full-size body (a_mid = 1.0 m).
    The refined schema must come back at the scaled size (a_mid = 0.1 m),
    matching the scaled wings — NOT the full 1.0 m that caused the giant
    fuselage in gh-765.
    """
    from app.services.openvsp_import_service import _try_slicer_refinement

    factor = 0.1
    refined = _try_slicer_refinement("body.stp", _scaled_handler_fuse(factor), "Body", factor)

    assert refined is not None
    a_values = sorted(xs.a for xs in refined)
    # Mid-section half-width: full-size 1.0 m → scaled 0.1 m.
    assert a_values[-1] == pytest.approx(1.0 * factor)
    # Length: full-size 10 m → scaled 1.0 m.
    x_span = max(xs.xyz[0] for xs in refined) - min(xs.xyz[0] for xs in refined)
    assert x_span == pytest.approx(10.0 * factor)


def test_slicer_refinement_slices_step_in_full_size_frame(mock_slicer):
    """The slicer must operate in the unscaled STEP's frame.

    The x-stations handed to ``slice_step_at_stations`` must be full-size
    (≈10000 mm span), recovered from the scaled handler schema. Slicing a
    full-size STEP at scaled (tiny) stations was the gh-765 defect.
    """
    from app.services.openvsp_import_service import _try_slicer_refinement

    factor = 0.1
    _try_slicer_refinement("body.stp", _scaled_handler_fuse(factor), "Body", factor)

    # The handler dicts used to compute anchored stations must be in the
    # full-size frame (mid xsec a ≈ 1.0 m), not the scaled 0.1 m frame.
    args, kwargs = mock_slicer.anchored_stations.call_args
    handler_dicts = args[0]
    max_a = max(d["a"] for d in handler_dicts)
    assert max_a == pytest.approx(1.0)


def test_slicer_refinement_factor_one_is_identity(mock_slicer):
    """factor=1.0 preserves the pre-gh-765 behaviour (plain mm→m)."""
    from app.services.openvsp_import_service import _try_slicer_refinement

    refined = _try_slicer_refinement("body.stp", _scaled_handler_fuse(1.0), "Body", 1.0)

    assert refined is not None
    a_values = sorted(xs.a for xs in refined)
    assert a_values[-1] == pytest.approx(1.0)
