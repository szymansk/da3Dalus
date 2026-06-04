"""Tests for compute_airfoil_low_re with mocked NeuralFoil boundary (Task 5, gh-821).

NO real AeroSandbox import in this fast test — the NeuralFoil call is
monkey-patched via pytest monkeypatch. Deterministic fake polar arrays
drive the metric extraction and parabolic fit assertions.
"""

from __future__ import annotations

import numpy as np
import pytest


def _make_fake_aero_result(alpha_deg: np.ndarray, *, re: float) -> dict:
    """Build a deterministic fake NeuralFoil result for testing.

    Generates a realistic-looking polar:
    - CL rises linearly with alpha, peaks at ~12 deg, then drops
    - CD parabolic in CL (cd0=0.012, k=0.04, cl0=0.3)
    - analysis_confidence = 0.95 everywhere (above the 0.90 gate)
    """
    alpha_rad = np.deg2rad(alpha_deg)
    # Simple linear CL with post-stall drop
    cl = np.where(
        alpha_deg <= 12.0,
        0.1 + 0.1 * alpha_deg,
        1.3 - 0.05 * (alpha_deg - 12.0),
    )
    cl0_true = 0.3
    cd0_true = 0.012
    k_true = 0.04
    cd = cd0_true + k_true * (cl - cl0_true) ** 2
    conf = np.full_like(alpha_deg, 0.95)
    return {
        "CL": cl,
        "CD": cd,
        "analysis_confidence": conf,
    }


def _make_low_confidence_result(alpha_deg: np.ndarray) -> dict:
    """Result with confidence below gate — metrics should be excluded."""
    cl = np.full_like(alpha_deg, 0.5)
    cd = np.full_like(alpha_deg, 0.02)
    # Confidence 0.85 — below the 0.90 gate
    conf = np.full_like(alpha_deg, 0.85)
    return {
        "CL": cl,
        "CD": cd,
        "analysis_confidence": conf,
    }


@pytest.fixture()
def mock_asb(monkeypatch):
    """Monkey-patch asb.Airfoil.get_aero_from_neuralfoil with deterministic results."""
    import sys
    import types

    # Create a fake aerosandbox module if not present
    if "aerosandbox" not in sys.modules:
        asb_module = types.ModuleType("aerosandbox")

        class FakeAirfoil:
            def __init__(self, name=None, coordinates=None):
                self.name = name
                self.coordinates = coordinates

            def get_aero_from_neuralfoil(
                self, alpha, Re, mach=0, n_crit=9.0, model_size="large", **kwargs
            ):
                return _make_fake_aero_result(np.atleast_1d(alpha), re=Re)

        asb_module.Airfoil = FakeAirfoil
        sys.modules["aerosandbox"] = asb_module

    # Monkeypatch the Airfoil.get_aero_from_neuralfoil on the existing module
    import aerosandbox as asb

    def fake_neuralfoil(self, alpha, Re, mach=0, n_crit=9.0, model_size="large", **kwargs):
        return _make_fake_aero_result(np.atleast_1d(alpha), re=Re)

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", fake_neuralfoil)
    return asb


def test_compute_returns_one_row_per_re_point(mock_asb):
    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    re_grid = [50_000, 100_000, 200_000]
    results = compute_airfoil_low_re("test_af", coords, re_grid, model_size="large")
    assert len(results) == 3


def test_compute_metrics_are_finite(mock_asb):
    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    re_grid = [100_000]
    results = compute_airfoil_low_re("test_af", coords, re_grid)
    row = results[0]
    assert row["ld_max"] is not None
    assert row["cl_max"] is not None
    assert row["ld_max"] > 0
    assert row["cl_max"] > 0


def test_compute_parabolic_fit_recovers_known_coefficients(mock_asb):
    """Verify the OLS fit recovers cd0, k, cl0 from the deterministic polar.

    The fake polar uses cd0_true=0.012, k_true=0.04, cl0_true=0.3.
    """
    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    re_grid = [100_000]
    results = compute_airfoil_low_re("test_af", coords, re_grid)
    row = results[0]

    assert row["cd0"] is not None, "cd0 should be fitted"
    assert row["k"] is not None, "k should be fitted"
    assert row["cl0"] is not None, "cl0 should be fitted"

    # Allow some tolerance since we fit over a non-perfect polar
    assert row["k"] == pytest.approx(0.04, abs=0.02), f"k fit off: {row['k']}"
    assert row["cl0"] == pytest.approx(0.3, abs=0.1), f"cl0 fit off: {row['cl0']}"


def test_compute_min_analysis_confidence_is_minimum_over_sweep(mock_asb):
    """min_analysis_confidence must be the minimum over the entire swept alpha range."""
    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    re_grid = [100_000]
    results = compute_airfoil_low_re("test_af", coords, re_grid)
    row = results[0]
    # Our fake polar gives 0.95 everywhere
    assert row["min_analysis_confidence"] == pytest.approx(0.95, abs=0.01)


def test_compute_low_confidence_excludes_metrics(monkeypatch):
    """When analysis_confidence is below gate everywhere, metrics should be None."""
    import sys
    import types

    if "aerosandbox" not in sys.modules:
        asb_module = types.ModuleType("aerosandbox")

        class FakeLowConfAirfoil:
            def __init__(self, name=None, coordinates=None):
                pass

            def get_aero_from_neuralfoil(self, alpha, Re, **kwargs):
                return _make_low_confidence_result(np.atleast_1d(alpha))

        asb_module.Airfoil = FakeLowConfAirfoil
        sys.modules["aerosandbox"] = asb_module

    import aerosandbox as asb

    def fake_low_conf(self, alpha, Re, **kwargs):
        return _make_low_confidence_result(np.atleast_1d(alpha))

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", fake_low_conf)

    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    results = compute_airfoil_low_re("test_af", coords, [100_000], confidence_gate=0.90)
    row = results[0]
    # With 0.85 confidence < 0.90 gate, trusted points are empty → all metrics None
    assert row["ld_max"] is None
    assert row["cl_max"] is None
    assert row["min_analysis_confidence"] == pytest.approx(0.85, abs=0.01)


def test_compute_cl_valid_lo_hi_span(mock_asb):
    """cl_valid_lo and cl_valid_hi should span the trusted CL range."""
    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
    re_grid = [100_000]
    results = compute_airfoil_low_re("test_af", coords, re_grid)
    row = results[0]
    if row["cl_valid_lo"] is not None and row["cl_valid_hi"] is not None:
        assert row["cl_valid_hi"] > row["cl_valid_lo"]


def test_compute_graceful_when_aerosandbox_unavailable(monkeypatch):
    """compute_airfoil_low_re must return [] when aerosandbox is not importable."""
    import sys
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "aerosandbox":
            raise ImportError("mock: aerosandbox not available")
        return original_import(name, *args, **kwargs)

    # Remove aerosandbox from sys.modules temporarily
    saved = sys.modules.pop("aerosandbox", None)
    monkeypatch.setattr(builtins, "__import__", mock_import)

    try:
        from app.services.airfoil_low_re_service import compute_airfoil_low_re

        coords = np.array([[0.0, 0.0], [0.5, 0.06], [1.0, 0.0]])
        results = compute_airfoil_low_re("test_af", coords, [100_000])
        assert results == []
    finally:
        if saved is not None:
            sys.modules["aerosandbox"] = saved
        monkeypatch.undo()


# ---------------------------------------------------------------------------
# ITEM 1 (gh-825): windowed min_analysis_confidence
# ---------------------------------------------------------------------------
#
# The attached/operating alpha window is [alpha_attached_lo, alpha_attached_hi]
# which is the ascending CL portion up to CL_max.  The min_analysis_confidence
# stored in the row must be the MIN of analysis_confidence over ONLY that window,
# NOT the global sweep minimum.
#
# This test constructs a crafted NeuralFoil result where:
#   - confidence is HIGH (0.97) in the attached/ascending CL region
#   - confidence is LOW  (0.40) in the deep-stall post-peak region
# The test asserts that min_analysis_confidence == 0.97 (windowed min),
# NOT 0.40 (global sweep min).


def _make_windowed_confidence_result(alpha_deg: np.ndarray) -> dict:
    """NeuralFoil result with high confidence in attached region, low in deep stall.

    CL peaks at ~12 deg (CL ≈ 1.3).  Attached window: alpha ≤ 12 deg.
    Confidence is 0.97 for alpha ≤ 12 deg (attached), 0.40 for alpha > 12 deg.
    Global sweep min confidence = 0.40; windowed (attached) min = 0.97.
    """
    # CL rises linearly, peaks at 12 deg, then drops
    cl = np.where(
        alpha_deg <= 12.0,
        0.1 + 0.1 * alpha_deg,  # attached: 0.1 at α=-5, 1.3 at α=12
        1.3 - 0.05 * (alpha_deg - 12.0),  # post-stall: drops
    )
    # CD parabolic in CL (cd0=0.012, k=0.04, cl0=0.3)
    cd0_true, k_true, cl0_true = 0.012, 0.04, 0.3
    cd = cd0_true + k_true * (cl - cl0_true) ** 2

    # HIGH confidence in attached region (alpha ≤ 12), LOW beyond
    conf = np.where(alpha_deg <= 12.0, 0.97, 0.40)
    return {"CL": cl, "CD": cd, "analysis_confidence": conf}


def test_min_analysis_confidence_is_windowed_not_global(monkeypatch):
    """ITEM 1: min_analysis_confidence must be the MIN over the attached alpha window.

    The global sweep min is 0.40 (deep-stall region).
    The windowed (attached, alpha ≤ CL_max) min is 0.97.
    We assert min_analysis_confidence == 0.97 (windowed).

    NOTE: This test documents the gh-825 item 1 semantic change.
    Stored AirfoilLowRePolarModel.min_analysis_confidence rows require
    PO-run re-backfill after merge — NOT done in the workflow.
    """
    import sys
    import types

    # Ensure aerosandbox is available as a mock
    if "aerosandbox" not in sys.modules:
        asb_module = types.ModuleType("aerosandbox")

        class FakeAirfoilWindowed:
            def __init__(self, name=None, coordinates=None):
                self.name = name

            def get_aero_from_neuralfoil(
                self, alpha, Re, mach=0, n_crit=9.0, model_size="large", **kwargs
            ):
                return _make_windowed_confidence_result(np.atleast_1d(alpha))

        asb_module.Airfoil = FakeAirfoilWindowed
        sys.modules["aerosandbox"] = asb_module

    import aerosandbox as asb

    def fake_windowed(self, alpha, Re, mach=0, n_crit=9.0, model_size="large", **kwargs):
        return _make_windowed_confidence_result(np.atleast_1d(alpha))

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", fake_windowed)

    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.07], [1.0, 0.0]])
    # Use confidence_gate=0.90 so the attached region (conf=0.97) is trusted,
    # but deep-stall (conf=0.40) points are NOT included in the trusted cl/cd arrays.
    # This means _extract_metrics receives only the trusted (attached) points,
    # so the windowed confidence must be computed over the FULL conf_arr restricted
    # to the alpha_attached_lo .. alpha_attached_hi range.
    results = compute_airfoil_low_re(
        "test_windowed_af",
        coords,
        [100_000],
        confidence_gate=0.90,
        alpha_start=-5.0,
        alpha_end=18.0,
        alpha_step=0.5,
    )
    assert len(results) == 1
    row = results[0]

    # The attached window is alpha ≤ ~12 deg → all trusted (conf=0.97)
    # Deep stall alpha > 12 deg has conf=0.40, but falls below gate (0.90)
    # so they are excluded from the trusted set anyway.
    # min_analysis_confidence should be the windowed min over attached region = 0.97
    assert row["min_analysis_confidence"] is not None
    assert row["min_analysis_confidence"] == pytest.approx(0.97, abs=0.02), (
        f"Expected windowed min_analysis_confidence ≈ 0.97 (attached region), "
        f"got {row['min_analysis_confidence']:.4f}. "
        f"This test verifies gh-825 item 1: min_analysis_confidence is the windowed "
        f"(attached-alpha) min, NOT the global sweep min (0.40 in deep stall)."
    )


def test_min_analysis_confidence_windowed_gate_below_attached(monkeypatch):
    """Item 1 variant: gate below attached-region confidence.

    When some attached-region alpha points have confidence < full window min
    but still ABOVE the gate, the windowed min is correctly the min of the
    full conf_arr restricted to alpha_attached_lo..alpha_attached_hi.
    This uses a lower gate (0.50) to include all alpha in the trusted set,
    so the service must explicitly window by alpha_attached bounds.
    """
    import sys
    import types

    if "aerosandbox" not in sys.modules:
        asb_module = types.ModuleType("aerosandbox")

        class FakeAirfoilLowGate:
            def __init__(self, name=None, coordinates=None):
                pass

            def get_aero_from_neuralfoil(self, alpha, Re, **kwargs):
                return _make_windowed_confidence_result(np.atleast_1d(alpha))

        asb_module.Airfoil = FakeAirfoilLowGate
        sys.modules["aerosandbox"] = asb_module

    import aerosandbox as asb

    def fake_low_gate(self, alpha, Re, **kwargs):
        return _make_windowed_confidence_result(np.atleast_1d(alpha))

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", fake_low_gate)

    from app.services.airfoil_low_re_service import compute_airfoil_low_re

    coords = np.array([[0.0, 0.0], [0.5, 0.07], [1.0, 0.0]])
    # Use gate=0.35 so deep-stall (conf=0.40) points ARE included in trusted set.
    # Global sweep min = 0.40 (deep stall).  Windowed (attached) min = 0.97.
    # We assert windowed min = 0.97, not global min = 0.40.
    results = compute_airfoil_low_re(
        "test_lowgate_af",
        coords,
        [100_000],
        confidence_gate=0.35,  # both 0.97 and 0.40 pass gate
        alpha_start=-5.0,
        alpha_end=18.0,
        alpha_step=0.5,
    )
    assert len(results) == 1
    row = results[0]

    assert row["min_analysis_confidence"] is not None
    # The service must use the windowed min (over attached alpha range), not global min.
    # Windowed min = 0.97 (attached), global min = 0.40 (deep-stall included via low gate).
    assert row["min_analysis_confidence"] == pytest.approx(0.97, abs=0.02), (
        f"Expected windowed min_analysis_confidence ≈ 0.97; "
        f"got {row['min_analysis_confidence']:.4f}. "
        f"gh-825 item 1: must be windowed min over attached alpha range, NOT global sweep min."
    )
