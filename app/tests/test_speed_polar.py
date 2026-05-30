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
