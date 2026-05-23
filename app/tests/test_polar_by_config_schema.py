"""Schema tests for the gh-630 PolarRejection extension."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.polar_by_config import ParabolicPolar, PolarRejection


class TestPolarRejection:
    def test_minimal_construction(self):
        r = PolarRejection(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.0123,
            threshold="k > 0",
            hint="Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
        )
        assert r.gate == "negative_slope_k"
        assert r.category == "design"
        assert r.fitted_value == pytest.approx(-0.0123)
        assert r.threshold == "k > 0"
        assert r.hint.startswith("Polare")

    def test_fitted_value_may_be_none(self):
        r = PolarRejection(
            gate="insufficient_points",
            category="sweep",
            fitted_value=None,
            threshold=">= 6 points",
            hint="Zu wenig Punkte.",
        )
        assert r.fitted_value is None

    def test_rejects_unknown_gate(self):
        with pytest.raises(ValidationError):
            PolarRejection(
                gate="bogus_gate",  # type: ignore[arg-type]
                category="design",
                fitted_value=None,
                threshold="-",
                hint="-",
            )

    def test_rejects_unknown_category(self):
        with pytest.raises(ValidationError):
            PolarRejection(
                gate="negative_slope_k",
                category="weather",  # type: ignore[arg-type]
                fitted_value=None,
                threshold="-",
                hint="-",
            )

    def test_rejects_non_canonical_gate_category_pair(self):
        """gh-630 type-hardening: gate=design but category=sweep must raise."""
        with pytest.raises(ValidationError):
            PolarRejection(
                gate="negative_slope_k",   # canonical: design
                category="sweep",           # nonsensical pair
                fitted_value=-0.001,
                threshold="k > 0",
                hint="hint",
            )

    def test_accepts_all_six_canonical_pairs(self):
        """All 6 canonical (gate, category) pairs from _GATE_CATEGORY validate."""
        canonical = [
            ("insufficient_points", "sweep"),
            ("non_monotonic_polar", "data"),
            ("negative_slope_k", "design"),
            ("non_positive_cd0", "consistency"),
            ("unphysical_e_oswald", "design"),
            ("cd0_stability_mismatch", "consistency"),
        ]
        for gate, category in canonical:
            r = PolarRejection(
                gate=gate,
                category=category,
                fitted_value=None,
                threshold="-",
                hint="-",
            )
            assert r.gate == gate and r.category == category

    def test_serialises_to_dict(self):
        r = PolarRejection(
            gate="unphysical_e_oswald",
            category="design",
            fitted_value=1.42,
            threshold="(0.4, 1.0]",
            hint="e = 1.42 außerhalb (0.4, 1.0].",
        )
        d = r.model_dump()
        assert d == {
            "gate": "unphysical_e_oswald",
            "category": "design",
            "fitted_value": 1.42,
            "threshold": "(0.4, 1.0]",
            "hint": "e = 1.42 außerhalb (0.4, 1.0].",
        }


class TestParabolicPolarRejectionField:
    def test_rejection_defaults_to_none(self):
        p = ParabolicPolar(cl_max=1.2)
        assert p.rejection is None

    def test_rejection_can_be_attached(self):
        rej = PolarRejection(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.001,
            threshold="k > 0",
            hint="hint",
        )
        p = ParabolicPolar(cl_max=1.2, rejection=rej)
        assert p.rejection is rej

    def test_rejection_survives_json_roundtrip(self):
        rej = PolarRejection(
            gate="unphysical_e_oswald",
            category="design",
            fitted_value=1.1,
            threshold="(0.4, 1.0]",
            hint="e=1.1 außerhalb (0.4, 1.0].",
        )
        p = ParabolicPolar(cl_max=1.2, rejection=rej)
        as_dict = p.model_dump()
        roundtripped = ParabolicPolar.model_validate(as_dict)
        assert roundtripped.rejection == rej


# ---------------------------------------------------------------------------
# gh-636: empirical (L/D)max + e from AeroBuildup D_induced sweep
# ---------------------------------------------------------------------------

import math

import numpy as np

from app.services.assumption_compute_service import (
    _e_oswald_from_sweep,
    _ld_max_from_sweep,
)


class TestLdMaxFromSweep:
    def test_finds_max_and_index(self):
        cl = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        cd = np.array([0.020, 0.022, 0.026, 0.034, 0.050])
        ld, cl_at, idx = _ld_max_from_sweep(cl, cd)
        # max(CL/CD): 0.1/0.02=5, 0.3/0.022=13.6, 0.5/0.026=19.2,
        # 0.7/0.034=20.6, 0.9/0.050=18 → max at index 3
        assert idx == 3
        assert cl_at == pytest.approx(0.7)
        assert ld == pytest.approx(0.7 / 0.034, rel=1e-3)

    def test_returns_none_when_all_invalid(self):
        cl = np.array([np.nan, np.nan])
        cd = np.array([0.020, 0.022])
        assert _ld_max_from_sweep(cl, cd) == (None, None, None)

    def test_returns_none_when_cd_all_zero(self):
        cl = np.array([0.1, 0.3, 0.5])
        cd = np.array([0.0, 0.0, 0.0])
        assert _ld_max_from_sweep(cl, cd) == (None, None, None)

    def test_skips_negative_cl(self):
        cl = np.array([-0.1, 0.3, 0.5])
        cd = np.array([0.020, 0.022, 0.026])
        ld, cl_at, idx = _ld_max_from_sweep(cl, cd)
        # negative CL is masked out → max picked from {1, 2}
        assert idx in (1, 2)
        assert cl_at > 0


class TestEOswaldFromSweep:
    def test_computes_e_at_ld_max_index(self):
        # Construct a clean test case: at index 1, e = CL²/(π·AR·CDi)
        cl = np.array([0.1, 0.5, 0.9])
        cdi = np.array([0.001, 0.006, 0.020])
        ar = 10.0
        # e at idx=1 = 0.5² / (π · 10 · 0.006) = 0.25 / 0.1885 ≈ 1.326 → CLIPPED to None
        # Pick more realistic numbers:
        cl = np.array([0.1, 0.5, 0.9])
        cdi = np.array([0.001, 0.0099, 0.025])  # at idx 1: e = 0.5²/(π·10·0.0099) ≈ 0.804
        e = _e_oswald_from_sweep(cl, cdi, ar=ar, ld_max_index=1)
        assert e is not None
        assert abs(e - 0.804) < 0.005

    def test_returns_none_when_index_none(self):
        cl = np.array([0.5])
        cdi = np.array([0.01])
        assert _e_oswald_from_sweep(cl, cdi, ar=10.0, ld_max_index=None) is None

    def test_returns_none_when_ar_invalid(self):
        cl = np.array([0.5])
        cdi = np.array([0.01])
        assert _e_oswald_from_sweep(cl, cdi, ar=0.0, ld_max_index=0) is None
        assert _e_oswald_from_sweep(cl, cdi, ar=None, ld_max_index=0) is None

    def test_returns_none_when_cdi_nonpositive(self):
        cl = np.array([0.5])
        cdi = np.array([0.0])
        assert _e_oswald_from_sweep(cl, cdi, ar=10.0, ld_max_index=0) is None

    def test_clips_unphysical_e_above_threshold(self):
        # CDi too low → e > 1.10 → clip to None
        cl = np.array([1.0])
        cdi = np.array([0.001])  # e = 1²/(π·10·0.001) ≈ 31.83 → out of range
        assert _e_oswald_from_sweep(cl, cdi, ar=10.0, ld_max_index=0) is None

    def test_returns_none_when_cl_nan(self):
        cl = np.array([float("nan")])
        cdi = np.array([0.01])
        assert _e_oswald_from_sweep(cl, cdi, ar=10.0, ld_max_index=0) is None
