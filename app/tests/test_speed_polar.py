"""Unit tests for the speed polar (Geschwindigkeitspolare) derivation.

The speed polar derives sink rate ``w`` over forward speed ``V`` from a drag
polar (CL/CD) for one or more masses. Aerodynamic coefficients are mass
independent; only the speed required to fly a given CL scales with mass, so
curves for different masses scale as ``V, w ∝ sqrt(m)``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.services.analysis_service import _compute_speed_polar

G = 9.81


def _v_of(mass: float, rho: float, s: float, cl: float) -> float:
    return math.sqrt(2.0 * mass * G / (rho * s * cl))


def test_single_base_curve_formula() -> None:
    cl = np.array([0.5, 1.0])
    cd = np.array([0.02, 0.05])
    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[], base_mass_kg=1.5, s_ref_m2=0.225, rho=1.225
    )
    assert len(sp.curves) == 1
    curve = sp.curves[0]
    assert curve.is_base is True
    assert curve.mass_kg == pytest.approx(1.5)
    # Arrays sorted ascending by V (higher CL -> lower V).
    assert curve.V == sorted(curve.V)
    # Spot-check the V and w formulas at CL = 1.0 (the lowest-V point).
    v_expected = _v_of(1.5, 1.225, 0.225, 1.0)
    idx = next(i for i, c in enumerate(curve.cl) if abs(c - 1.0) < 1e-9)
    assert curve.V[idx] == pytest.approx(v_expected, rel=1e-9)
    assert curve.w[idx] == pytest.approx(v_expected * (0.05 / 1.0), rel=1e-9)


def test_sqrt_m_scaling() -> None:
    """Quadrupling the mass scales V and w by exactly 2 (sqrt(4))."""
    cl = np.array([0.4, 0.8, 1.2])
    cd = np.array([0.018, 0.03, 0.06])
    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[1.0, 4.0], base_mass_kg=1.0, s_ref_m2=0.3, rho=1.225
    )
    by_mass = {c.mass_kg: c for c in sp.curves}
    light, heavy = by_mass[1.0], by_mass[4.0]
    for vl, vh in zip(light.V, heavy.V, strict=True):
        assert vh == pytest.approx(2.0 * vl, rel=1e-9)
    for wl, wh in zip(light.w, heavy.w, strict=True):
        assert wh == pytest.approx(2.0 * wl, rel=1e-9)


def test_filters_nonpositive_cl() -> None:
    cl = np.array([-0.3, 0.0, 0.5, 1.0])
    cd = np.array([0.04, 0.02, 0.02, 0.05])
    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[], base_mass_kg=2.0, s_ref_m2=0.225, rho=1.225
    )
    curve = sp.curves[0]
    # Only CL = 0.5 and CL = 1.0 survive.
    assert len(curve.V) == 2
    assert all(c > 0 for c in curve.cl)


def test_empty_masses_returns_base_only() -> None:
    cl = np.array([0.5, 1.0])
    cd = np.array([0.02, 0.05])
    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[], base_mass_kg=1.5, s_ref_m2=0.225, rho=1.225
    )
    assert [c.mass_kg for c in sp.curves] == [pytest.approx(1.5)]
    assert sp.base_mass_kg == pytest.approx(1.5)


def test_dedup_sort_and_base_flag() -> None:
    cl = np.array([0.5, 1.0])
    cd = np.array([0.02, 0.05])
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[2.5, 1.5, 2.5],  # duplicate 2.5, base 1.5 not in list explicitly
        base_mass_kg=1.5,
        s_ref_m2=0.225,
        rho=1.225,
    )
    masses = [c.mass_kg for c in sp.curves]
    # Deduplicated, base included, ascending.
    assert masses == [pytest.approx(1.5), pytest.approx(2.5)]
    base_curves = [c for c in sp.curves if c.is_base]
    assert len(base_curves) == 1
    assert base_curves[0].mass_kg == pytest.approx(1.5)


def test_characteristic_points_present() -> None:
    # Parabolic polar so min-sink and best-glide land on distinct CL points
    # (min-sink CL = sqrt(3) * best-glide CL for an ideal parabolic polar).
    cd0, e, ar = 0.012, 0.85, 14.4
    cl = np.linspace(0.1, 1.4, 200)
    cd = cd0 + cl**2 / (math.pi * e * ar)
    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[], base_mass_kg=1.5, s_ref_m2=0.225, rho=1.225
    )
    curve = sp.curves[0]
    assert curve.w_min is not None and curve.w_min > 0
    assert curve.v_min_sink is not None and curve.v_min_sink > 0
    assert curve.v_best_glide is not None and curve.v_best_glide > 0
    assert curve.ld_max is not None
    # Best glide L/D equals max(CL/CD) of the polar.
    assert curve.ld_max == pytest.approx(float(np.max(cl / cd)), rel=1e-9)
    # Min-sink speed is strictly below best-glide speed (classic glider ordering).
    assert curve.v_min_sink < curve.v_best_glide


def test_w_min_matches_closed_form() -> None:
    """w_min from the discrete polar matches the closed-form _min_sink_rate."""
    from app.services.assumption_compute_service import _min_sink_rate

    cd0, e, ar = 0.012, 0.85, 14.4
    mass, s_ref, rho = 1.5, 0.225, 1.225
    cl = np.linspace(0.05, 1.4, 600)
    cd = cd0 + cl**2 / (math.pi * e * ar)

    sp = _compute_speed_polar(
        cl=cl, cd=cd, masses_kg=[], base_mass_kg=mass, s_ref_m2=s_ref, rho=rho
    )
    w_min_discrete = sp.curves[0].w_min
    w_min_closed = _min_sink_rate(mass, s_ref, cd0, ar, rho=rho, oswald_e=e)
    assert w_min_closed is not None
    assert w_min_discrete == pytest.approx(w_min_closed, rel=0.03)


# ---------------------------------------------------------------------------
# Velocity-axis bounds (gh-799)
# ---------------------------------------------------------------------------


def _make_polar_with_stall() -> tuple:
    """Return (cl, cd, s_ref, rho) for a simple polar with a well-defined CL_max."""
    cl = np.linspace(0.2, 1.4, 50)
    cd0, e, ar = 0.012, 0.85, 12.0
    cd = cd0 + cl**2 / (math.pi * e * ar)
    return cl, cd, 0.225, 1.225


def test_bounds_with_v_dive() -> None:
    """With v_dive provided: v_axis_min=0.7*min(v_stall), v_axis_max=1.3*v_dive."""
    cl, cd, s_ref, rho = _make_polar_with_stall()
    v_dive = 40.0
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=v_dive,
    )
    assert len(sp.curves) == 1
    v_stall = sp.curves[0].v_stall
    assert v_stall is not None
    assert sp.v_axis_min == pytest.approx(0.7 * v_stall, rel=1e-9)
    assert sp.v_axis_max == pytest.approx(1.3 * v_dive, rel=1e-9)


def test_bounds_fallback_no_v_dive() -> None:
    """With v_dive=None the right bound falls back to max(V) over all curves."""
    cl, cd, s_ref, rho = _make_polar_with_stall()
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=None,
    )
    curve = sp.curves[0]
    expected_v_max = max(curve.V)
    assert sp.v_axis_max == pytest.approx(expected_v_max, rel=1e-9)
    # Left bound is still derived from v_stall (CL_max = 1.4 for this polar).
    assert curve.v_stall is not None
    assert sp.v_axis_min == pytest.approx(0.7 * curve.v_stall, rel=1e-9)


def test_bounds_multi_mass_v_axis_min_uses_lightest() -> None:
    """With multiple masses, v_axis_min is anchored to the lightest mass's v_stall."""
    cl, cd, s_ref, rho = _make_polar_with_stall()
    # Lighter mass → lower v_stall → lower left edge
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[3.0],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=50.0,
    )
    by_mass = {c.mass_kg: c for c in sp.curves}
    v_stall_light = by_mass[1.5].v_stall
    v_stall_heavy = by_mass[3.0].v_stall
    assert v_stall_light is not None
    assert v_stall_heavy is not None
    # Lightest mass gives smallest v_stall
    assert v_stall_light < v_stall_heavy
    assert sp.v_axis_min == pytest.approx(0.7 * v_stall_light, rel=1e-9)


def test_bounds_v_dive_mass_independent() -> None:
    """Right edge is identical regardless of extra comparison masses added."""
    cl, cd, s_ref, rho = _make_polar_with_stall()
    v_dive = 35.0
    sp_single = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=v_dive,
    )
    sp_multi = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[2.5, 4.0],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=v_dive,
    )
    assert sp_single.v_axis_max == pytest.approx(sp_multi.v_axis_max, rel=1e-9)
    assert sp_single.v_axis_max == pytest.approx(1.3 * v_dive, rel=1e-9)


def test_bounds_degenerate_no_positive_cl() -> None:
    """When no positive-CL points exist, both bounds are None — no exception raised."""
    cl = np.array([-0.5, -0.1, 0.0])
    cd = np.array([0.04, 0.02, 0.015])
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[],
        base_mass_kg=1.5,
        s_ref_m2=0.225,
        rho=1.225,
        v_dive=30.0,
    )
    assert sp.v_axis_min is None
    assert sp.v_axis_max is None


def test_bounds_inverted_guard() -> None:
    """When v_axis_min >= v_axis_max both bounds collapse to None (autorange).

    Scenario: very low v_dive (5 m/s) so that 1.3*v_dive < 0.7*v_stall.
    With CL_max ≈ 1.4, s_ref=0.225, mass=1.5 kg, rho=1.225:
      v_stall = sqrt(2*1.5*9.81 / (1.225*0.225*1.4)) ≈ 8.76 m/s
      0.7*v_stall ≈ 6.13  >  1.3*5 = 6.5  — barely above, so use a clearly
      inverted case with v_dive=2.0:
      1.3*2 = 2.6  <  0.7*8.76 ≈ 6.13  → inverted, both None.
    """
    cl, cd, s_ref, rho = _make_polar_with_stall()
    sp = _compute_speed_polar(
        cl=cl,
        cd=cd,
        masses_kg=[],
        base_mass_kg=1.5,
        s_ref_m2=s_ref,
        rho=rho,
        v_dive=2.0,  # extremely low — 1.3*2=2.6 < 0.7*v_stall≈6.1
    )
    assert sp.v_axis_min is None, "inverted bounds should collapse to None"
    assert sp.v_axis_max is None, "inverted bounds should collapse to None"
