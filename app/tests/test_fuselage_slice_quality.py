"""Slow tests for superellipse fit quality with real STEP files (GH#59 AC-5).

These tests load actual fuselage STEP files and validate that the slicing
pipeline produces geometrically faithful results.

Marked @pytest.mark.slow — skipped in the fast CI job.
"""

import pytest

# Platform guard: skip entire module if CadQuery is not available
try:
    from cad_designer.aerosandbox.slicing import slice_step_to_fuselage
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not HAS_CADQUERY, reason="CadQuery not available on this platform"),
]

EHAWK_STEP = "components/aircraft/eHawk/e-Hawk Rumpf v29.step"
PUNISHER_STEP = "components/aircraft/punisher/fuselage.step"


class TestEHawkFuselage:
    """Fit quality tests against the eHawk fuselage (primary test case)."""

    @pytest.fixture(scope="class")
    def ehawk_result(self):
        xsecs, metrics = slice_step_to_fuselage(
            EHAWK_STEP, number_of_slices=50, points_per_slice=30
        )
        return xsecs, metrics

    def test_volume_fidelity_above_90_percent(self, ehawk_result):
        _, metrics = ehawk_result
        assert metrics["volume_ratio"] >= 0.90, (
            f"Volume fidelity too low: {metrics['volume_ratio']:.3f} (need ≥ 0.90)"
        )

    def test_area_fidelity_above_85_percent(self, ehawk_result):
        _, metrics = ehawk_result
        assert metrics["area_ratio"] >= 0.85, (
            f"Area fidelity too low: {metrics['area_ratio']:.3f} (need ≥ 0.85)"
        )

    def test_all_exponents_in_valid_range(self, ehawk_result):
        xsecs, _ = ehawk_result
        for i, xsec in enumerate(xsecs):
            assert 0.5 <= xsec["n"] <= 10.0, (
                f"Section {i}: exponent n={xsec['n']:.2f} out of range [0.5, 10.0]"
            )

    def test_no_degenerate_cross_sections(self, ehawk_result):
        xsecs, _ = ehawk_result
        for i, xsec in enumerate(xsecs):
            assert xsec["a"] > 0.001, f"Section {i}: a={xsec['a']:.6f} is degenerate"
            assert xsec["b"] > 0.001, f"Section {i}: b={xsec['b']:.6f} is degenerate"

    def test_slice_count_matches_request(self, ehawk_result):
        xsecs, _ = ehawk_result
        # Allow ±2 tolerance for rounding at boundaries
        assert abs(len(xsecs) - 50) <= 2, (
            f"Expected ~50 slices, got {len(xsecs)}"
        )

    def test_xsecs_ordered_along_x(self, ehawk_result):
        xsecs, _ = ehawk_result
        x_coords = [xs["xyz"][0] for xs in xsecs]
        for i in range(1, len(x_coords)):
            assert x_coords[i] >= x_coords[i - 1], (
                f"Section {i}: x={x_coords[i]:.4f} < previous x={x_coords[i-1]:.4f}"
            )


class TestPunisherFuselage:
    """Secondary test case with simpler geometry."""

    @pytest.fixture(scope="class")
    def punisher_result(self):
        xsecs, metrics = slice_step_to_fuselage(
            PUNISHER_STEP, number_of_slices=30, points_per_slice=30
        )
        return xsecs, metrics

    def test_produces_valid_output(self, punisher_result):
        xsecs, metrics = punisher_result
        assert len(xsecs) > 0
        assert metrics["volume_ratio"] > 0
        assert metrics["area_ratio"] > 0

    def test_no_degenerate_sections(self, punisher_result):
        xsecs, _ = punisher_result
        for i, xsec in enumerate(xsecs):
            assert xsec["a"] > 0.001, f"Section {i}: a degenerate"
            assert xsec["b"] > 0.001, f"Section {i}: b degenerate"


class TestAxisAutoDetection:
    """Test that auto-detection picks the correct axis."""

    def test_ehawk_auto_detects_x(self):
        """eHawk fuselage is longest along X — auto should pick X."""
        from cad_designer.aerosandbox.slicing import load_step_model, detect_longest_axis
        model = load_step_model(EHAWK_STEP)
        axis = detect_longest_axis(model.val())
        assert axis == "x", f"Expected auto-detect 'x', got '{axis}'"
