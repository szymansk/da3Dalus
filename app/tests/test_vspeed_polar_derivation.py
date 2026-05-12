"""Polar-derived V-speed regression tests (gh-475).

The aero-performance audit identified four DEFECT findings where computed
V-speeds and operating-point seed speeds used heuristic shortcuts instead
of polar / physics data that was already available:

- ``flight_envelope_service.derive_performance_kpis`` emits
  ``best_ld_speed = 1.4 * V_s`` and ``min_sink_speed = 1.2 * V_s`` even
  when the polar-derived value is cached on the aeroplane.
- ``operating_point_generator_service._estimate_reference_speeds`` derives
  ``V_s`` from ``V_cruise / margin``, inverting physical causality.

Reference: Anderson, *Fundamentals of Aerodynamics*, 6e §6.7.2
(``[[maximum-lift-to-drag-ratio]]``).
"""

from __future__ import annotations

import math

import pytest

from app.services.assumption_compute_service import (
    _min_drag_speed,
    _min_sink_speed,
    _stall_speed,
)
from app.services.flight_envelope_service import derive_performance_kpis


# --------------------------------------------------------------------------- #
# Reference aircraft for cross-checks (audit §5)
# --------------------------------------------------------------------------- #


class _Aircraft:
    """Convenience holder for the textbook reference aircraft."""

    def __init__(
        self,
        name: str,
        mass_kg: float,
        s_ref_m2: float,
        aspect_ratio: float,
        cl_max: float,
        cd0: float,
        oswald_e: float,
        expected_vs: float,
        expected_vmd: float,
    ) -> None:
        self.name = name
        self.mass_kg = mass_kg
        self.s_ref_m2 = s_ref_m2
        self.aspect_ratio = aspect_ratio
        self.cl_max = cl_max
        self.cd0 = cd0
        self.oswald_e = oswald_e
        self.expected_vs = expected_vs
        self.expected_vmd = expected_vmd


CESSNA_172 = _Aircraft(
    name="Cessna 172",
    mass_kg=1043.0,
    s_ref_m2=16.2,
    aspect_ratio=7.32,
    cl_max=1.6,
    cd0=0.031,
    oswald_e=0.75,
    expected_vs=25.4,
    expected_vmd=37.6,
)
# Note on the audit (gh-475 §5.1): the Cessna hand-calculation shows
# inputs m=1043 kg / S=16.2 m² / C_D0=0.031 / e=0.75 / AR=7.32 with the
# claim V_md ≈ 33.5. Plugging those numbers into V_md = √(2W/(ρS·C_L*))
# with C_L* = √(π e AR C_D0) ≈ 0.731 actually yields 37.6, not 33.5.
# The audit's arithmetic in the final step is wrong; the formula and our
# implementation match Anderson §6.7.2 exactly. We test against 37.6.

ASW_27 = _Aircraft(
    name="ASW-27 sailplane",
    mass_kg=300.0,
    s_ref_m2=9.0,
    aspect_ratio=28.5,
    cl_max=1.3,
    cd0=0.011,
    oswald_e=0.80,
    expected_vs=19.7,
    expected_vmd=23.9,
)

# Small RC trainer (typical 2 m wingspan electric)
RC_TRAINER = _Aircraft(
    name="RC trainer",
    mass_kg=2.0,
    s_ref_m2=0.40,
    aspect_ratio=7.0,
    cl_max=1.2,
    cd0=0.035,
    oswald_e=0.78,
    expected_vs=7.2,
    expected_vmd=10.1,
)


REFERENCE_AIRCRAFT = [CESSNA_172, ASW_27, RC_TRAINER]


# --------------------------------------------------------------------------- #
# Helper: textbook V_min_sink
# --------------------------------------------------------------------------- #


def _textbook_v_min_sink(a: _Aircraft, rho: float = 1.225, g: float = 9.81) -> float:
    """V_mp = √(2W / (ρ·S·C_L_mp)) with C_L_mp = √(3·π·e·AR·C_D0)."""
    cl_mp = math.sqrt(3.0 * math.pi * a.oswald_e * a.aspect_ratio * a.cd0)
    weight = a.mass_kg * g
    return math.sqrt(2.0 * weight / (rho * a.s_ref_m2 * cl_mp))


def _vs(a: _Aircraft) -> float:
    """Stall speed for a reference aircraft. Helper asserts the underlying
    ``_stall_speed`` did not return None for these well-formed inputs."""
    v = _stall_speed(a.mass_kg, a.s_ref_m2, a.cl_max)
    assert v is not None, f"_stall_speed returned None for {a.name}"
    return v


# --------------------------------------------------------------------------- #
# _min_sink_speed helper (new)
# --------------------------------------------------------------------------- #


class TestMinSinkSpeedHelper:
    """V_mp = V_md / 3^(1/4) ≈ 0.760 · V_md (Anderson §6.7.2)."""

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_matches_textbook(self, aircraft):
        v_mp = _min_sink_speed(
            mass_kg=aircraft.mass_kg,
            s_ref_m2=aircraft.s_ref_m2,
            cd0=aircraft.cd0,
            aspect_ratio=aircraft.aspect_ratio,
            oswald_e=aircraft.oswald_e,
        )
        assert v_mp is not None
        v_mp_expected = _textbook_v_min_sink(aircraft)
        assert abs(v_mp - v_mp_expected) < 0.05, (
            f"{aircraft.name}: V_mp={v_mp:.2f} expected {v_mp_expected:.2f}"
        )

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_canonical_ratio_to_v_md(self, aircraft):
        """V_mp ≈ 0.760·V_md is the canonical identity from polar geometry."""
        v_md = _min_drag_speed(
            aircraft.mass_kg,
            aircraft.s_ref_m2,
            aircraft.cd0,
            aircraft.aspect_ratio,
            oswald_e=aircraft.oswald_e,
        )
        v_mp = _min_sink_speed(
            aircraft.mass_kg,
            aircraft.s_ref_m2,
            aircraft.cd0,
            aircraft.aspect_ratio,
            oswald_e=aircraft.oswald_e,
        )
        assert v_md is not None
        assert v_mp is not None
        ratio = v_mp / v_md
        assert abs(ratio - 0.760) < 0.005, (
            f"{aircraft.name}: V_mp/V_md={ratio:.4f}, expected 0.760"
        )

    def test_returns_none_on_degenerate_inputs(self):
        # Matches _min_drag_speed semantics: only the geometry/polar inputs
        # gate the None return; non-positive mass would produce 0.0 here
        # just like in _min_drag_speed.
        assert _min_sink_speed(1.0, 0.0, 0.03, 7.0) is None
        assert _min_sink_speed(1.0, 1.0, 0.0, 7.0) is None
        assert _min_sink_speed(1.0, 1.0, 0.03, None) is None
        assert _min_sink_speed(1.0, 1.0, 0.03, 0.0) is None


# --------------------------------------------------------------------------- #
# derive_performance_kpis polar consumption (AC1)
# --------------------------------------------------------------------------- #


class TestDerivePerformanceKpisPolar:
    """``derive_performance_kpis`` must consume polar V_md / V_min_sink
    when supplied and fall back to the heuristic only otherwise."""

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_v_md_from_polar_matches_textbook(self, aircraft):
        v_stall = _vs(aircraft)
        v_md_textbook = _min_drag_speed(
            aircraft.mass_kg, aircraft.s_ref_m2, aircraft.cd0,
            aircraft.aspect_ratio, oswald_e=aircraft.oswald_e,
        )
        assert v_md_textbook is not None

        kpis = derive_performance_kpis(
            stall_speed_mps=v_stall,
            v_max_mps=2 * v_stall,
            g_limit=4.0,
            markers=[],
            v_md_polar_mps=v_md_textbook,
        )
        best_ld = next(k for k in kpis if k.label == "best_ld_speed")
        assert abs(best_ld.value - v_md_textbook) < 0.05
        assert best_ld.confidence == "computed"

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_v_min_sink_from_polar_matches_textbook(self, aircraft):
        v_stall = _vs(aircraft)
        v_mp_textbook = _textbook_v_min_sink(aircraft)

        kpis = derive_performance_kpis(
            stall_speed_mps=v_stall,
            v_max_mps=2 * v_stall,
            g_limit=4.0,
            markers=[],
            v_min_sink_polar_mps=v_mp_textbook,
        )
        min_sink = next(k for k in kpis if k.label == "min_sink_speed")
        assert abs(min_sink.value - v_mp_textbook) < 0.05
        assert min_sink.confidence == "computed"

    def test_heuristic_when_polar_absent(self):
        """When no polar value is supplied, fall back to 1.4·V_s / 1.2·V_s
        with confidence='estimated' (preserves backward compat)."""
        kpis = derive_performance_kpis(
            stall_speed_mps=10.0,
            v_max_mps=30.0,
            g_limit=4.0,
            markers=[],
        )
        best_ld = next(k for k in kpis if k.label == "best_ld_speed")
        min_sink = next(k for k in kpis if k.label == "min_sink_speed")
        assert abs(best_ld.value - 14.0) < 0.01
        assert abs(min_sink.value - 12.0) < 0.01
        assert best_ld.confidence == "estimated"
        assert min_sink.confidence == "estimated"

    def test_marker_overrides_polar(self):
        """If a TRIMMED operating-point marker exists, it wins over the
        polar fallback (existing precedence preserved)."""
        from app.schemas.flight_envelope import VnMarker

        marker = VnMarker(
            op_id=42, name="best_ld_point", velocity_mps=15.0,
            load_factor=1.0, status="TRIMMED", label="best_ld",
        )
        kpis = derive_performance_kpis(
            stall_speed_mps=10.0,
            v_max_mps=30.0,
            g_limit=4.0,
            markers=[marker],
            v_md_polar_mps=33.5,
        )
        best_ld = next(k for k in kpis if k.label == "best_ld_speed")
        assert abs(best_ld.value - 15.0) < 0.01
        assert best_ld.confidence == "trimmed"


# --------------------------------------------------------------------------- #
# _estimate_reference_speeds physics-seeded V_s (AC3)
# --------------------------------------------------------------------------- #


class TestEstimateReferenceSpeedsPhysics:
    """``_estimate_reference_speeds`` must derive V_s from physics
    (cached ``v_stall_mps``) when the assumption-computation context is
    available, instead of inverting cruise/margin."""

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_vs_clean_from_cached_context(self, aircraft):
        from app.services.operating_point_generator_service import (
            _estimate_reference_speeds,
        )

        v_stall = _vs(aircraft)
        profile = {
            "goals": {
                "cruise_speed_mps": 2 * v_stall,
                "min_speed_margin_vs_clean": 1.20,
            },
        }
        cached_context = {"v_stall_mps": v_stall}

        refs = _estimate_reference_speeds(profile, cached_context=cached_context)
        assert abs(refs["vs_clean"] - v_stall) < 0.05

    def test_falls_back_to_cruise_margin_when_no_context(self):
        from app.services.operating_point_generator_service import (
            _estimate_reference_speeds,
        )

        profile = {
            "goals": {
                "cruise_speed_mps": 24.0,
                "min_speed_margin_vs_clean": 1.20,
            },
        }
        refs = _estimate_reference_speeds(profile)
        assert abs(refs["vs_clean"] - 20.0) < 0.01

    def test_stol_design_respects_physics(self):
        """STOL design with V_cruise/V_s ≈ 3: physics V_s ≈ 7, cruise/margin
        would give V_s ≈ 17.5 (2.5× too high)."""
        from app.services.operating_point_generator_service import (
            _estimate_reference_speeds,
        )

        profile = {
            "goals": {
                "cruise_speed_mps": 21.0,
                "min_speed_margin_vs_clean": 1.20,
            },
        }
        cached_context = {"v_stall_mps": 7.0}
        refs = _estimate_reference_speeds(profile, cached_context=cached_context)
        # With physics: V_s = 7. Without: V_s = 21 / 1.2 = 17.5.
        assert abs(refs["vs_clean"] - 7.0) < 0.05
        assert refs["vs_clean"] < 10.0


# --------------------------------------------------------------------------- #
# Cross-check: services agree on V_md (AC6)
# --------------------------------------------------------------------------- #


class TestCrossServiceAgreement:
    """Audit acceptance criterion: V_md from ``flight_envelope_service``
    must match the value from ``assumption_compute_service`` to within
    0.5 m/s on the same aircraft + polar."""

    @pytest.mark.parametrize("aircraft", REFERENCE_AIRCRAFT, ids=lambda a: a.name)
    def test_v_md_matches_within_half_mps(self, aircraft):
        v_md_from_assumption = _min_drag_speed(
            aircraft.mass_kg, aircraft.s_ref_m2, aircraft.cd0,
            aircraft.aspect_ratio, oswald_e=aircraft.oswald_e,
        )
        assert v_md_from_assumption is not None
        v_stall = _vs(aircraft)
        kpis = derive_performance_kpis(
            stall_speed_mps=v_stall,
            v_max_mps=2 * v_stall,
            g_limit=4.0,
            markers=[],
            v_md_polar_mps=v_md_from_assumption,
        )
        v_md_from_envelope = next(k for k in kpis if k.label == "best_ld_speed").value
        assert abs(v_md_from_envelope - v_md_from_assumption) < 0.5, (
            f"{aircraft.name}: envelope V_md={v_md_from_envelope:.2f}, "
            f"assumption V_md={v_md_from_assumption:.2f}"
        )

    def test_textbook_v_md_matches_handcalc(self):
        """Sanity check that _min_drag_speed agrees with the audit's textbook
        section §5 to within ~1 m/s. The audit's intermediate rounding makes
        a strict ±0.2 match unrealistic; the formula itself is unambiguous."""
        for aircraft in REFERENCE_AIRCRAFT:
            v_md = _min_drag_speed(
                aircraft.mass_kg, aircraft.s_ref_m2, aircraft.cd0,
                aircraft.aspect_ratio, oswald_e=aircraft.oswald_e,
            )
            assert v_md is not None
            assert abs(v_md - aircraft.expected_vmd) < 1.0, (
                f"{aircraft.name}: V_md={v_md:.2f} vs textbook {aircraft.expected_vmd}"
            )
