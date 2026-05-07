"""Tests for stability service pure computation functions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.stability_service import classify_stability, compute_cg_range, compute_geometry_hash


class TestClassifyStability:

    def test_stable_high_margin(self):
        assert classify_stability(20.0) == "stable"

    def test_stable_boundary(self):
        assert classify_stability(5.01) == "stable"

    def test_neutral_at_five(self):
        assert classify_stability(5.0) == "neutral"

    def test_neutral_at_zero(self):
        assert classify_stability(0.0) == "neutral"

    def test_neutral_mid(self):
        assert classify_stability(2.5) == "neutral"

    def test_unstable_negative(self):
        assert classify_stability(-1.0) == "unstable"

    def test_unstable_very_negative(self):
        assert classify_stability(-50.0) == "unstable"

    def test_none_returns_none(self):
        assert classify_stability(None) is None


class TestComputeCGRange:

    def test_default_margins(self):
        forward, aft = compute_cg_range(0.10, 0.25)
        assert forward == pytest.approx(0.10 - 0.25 * 0.25)
        assert aft == pytest.approx(0.10 - 0.05 * 0.25)

    def test_custom_margins(self):
        forward, aft = compute_cg_range(0.10, 0.25, min_margin=10.0, max_margin=30.0)
        assert forward == pytest.approx(0.10 - 0.30 * 0.25)
        assert aft == pytest.approx(0.10 - 0.10 * 0.25)

    def test_forward_is_ahead_of_aft(self):
        result = compute_cg_range(0.10, 0.25, min_margin=5.0, max_margin=25.0)
        forward, aft = result
        assert forward < aft

    def test_zero_mac_returns_none(self):
        assert compute_cg_range(0.10, 0.0) is None

    def test_negative_mac_returns_none(self):
        assert compute_cg_range(0.10, -0.1) is None

    def test_none_mac_returns_none(self):
        assert compute_cg_range(0.10, None) is None


class TestComputeGeometryHash:

    def test_deterministic(self):
        schema = SimpleNamespace(
            wings=[SimpleNamespace(
                name="main",
                symmetric=True,
                x_secs=[SimpleNamespace(x_le=0, y_le=0, z_le=0, chord=0.3, twist=0)],
            )],
            fuselages=[],
        )
        h1 = compute_geometry_hash(schema)
        h2 = compute_geometry_hash(schema)
        assert h1 == h2
        assert len(h1) == 16

    def test_changes_with_geometry(self):
        s1 = SimpleNamespace(
            wings=[SimpleNamespace(
                name="main",
                symmetric=True,
                x_secs=[SimpleNamespace(x_le=0, y_le=0, z_le=0, chord=0.3, twist=0)],
            )],
            fuselages=[],
        )
        s2 = SimpleNamespace(
            wings=[SimpleNamespace(
                name="main",
                symmetric=True,
                x_secs=[SimpleNamespace(x_le=0, y_le=0, z_le=0, chord=0.5, twist=0)],
            )],
            fuselages=[],
        )
        assert compute_geometry_hash(s1) != compute_geometry_hash(s2)

    def test_empty_schema(self):
        schema = SimpleNamespace(wings=[], fuselages=[])
        h = compute_geometry_hash(schema)
        assert isinstance(h, str)
        assert len(h) == 16

    def test_no_wings_attribute(self):
        schema = SimpleNamespace()
        h = compute_geometry_hash(schema)
        assert isinstance(h, str)
