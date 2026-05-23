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
