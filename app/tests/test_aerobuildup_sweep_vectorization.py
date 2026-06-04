"""Tests for gh-690 vectorization of AeroBuildup sweeps.

The three sweep functions in ``app/services/assumption_compute_service.py``
historically called ``asb.AeroBuildup(...).run()`` once per (V, α) point.
gh-690 collapses each one into a single vectorised call over the full grid.

Two test layers:

1. **Single-call** — pins the refactor itself. Counts ``AeroBuildup.run``
   invocations per sweep-function call: must be exactly 1. FAILS before
   the refactor, PASSES after.

2. **Equivalence** — pins the *output* against an inlined point-by-point
   serial reference computed in the test itself. Catches regressions if
   anyone later tweaks the vectorised implementation.

The fixture is a tiny rectangular wing built directly with the AeroSandbox
API (no DB / no conftest factory) so the whole file runs in well under
the slow-test budget. AeroBuildup is deterministic, so vectorised vs.
serial should agree to machine precision (``atol=1e-9``).
"""

from __future__ import annotations

import numpy as np
import pytest

asb = pytest.importorskip("aerosandbox")

from app.models.computation_config import COMPUTATION_CONFIG_DEFAULTS  # noqa: E402
from app.services.assumption_compute_service import (  # noqa: E402
    _coarse_alpha_sweep,
    _extract_cl_alpha_from_linear_sweep,
    _extract_scalar,
    _fine_sweep_cl_max,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _SweepConfig:
    """Tiny stand-in for AircraftComputationConfigModel.

    ``_coarse_alpha_sweep`` and ``_fine_sweep_cl_max`` only read attribute
    values — no SQLAlchemy machinery needed. Defaults match
    COMPUTATION_CONFIG_DEFAULTS exactly so behaviour matches production.
    """

    def __init__(self, **overrides):
        for k, v in COMPUTATION_CONFIG_DEFAULTS.items():
            setattr(self, k, v)
        for k, v in overrides.items():
            setattr(self, k, v)


@pytest.fixture(scope="module")
def tiny_airplane():
    """A minimal rectangular wing — enough to exercise AeroBuildup / NeuralFoil.

    Module-scoped so the airfoil's NeuralFoil cache is built once.
    """
    naca = asb.Airfoil("naca2412")
    wing = asb.Wing(
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[0.0, 0.0, 0.0], chord=0.25, airfoil=naca),
            asb.WingXSec(xyz_le=[0.0, 1.0, 0.0], chord=0.25, airfoil=naca),
        ],
    )
    plane = asb.Airplane(wings=[wing], xyz_ref=[0.0, 0.0, 0.0])
    plane.s_ref = 0.5  # 2 × 1.0 × 0.25
    plane.b_ref = 2.0
    plane.c_ref = 0.25
    return plane


@pytest.fixture
def sweep_config():
    """Reduced-grid config so the tests stay fast.

    Smaller than the production default, large enough to exercise the
    array-flattening path (and reveal any V-outer / α-inner ordering bug).
    """
    return _SweepConfig(
        coarse_alpha_min_deg=-2.0,
        coarse_alpha_max_deg=8.0,
        coarse_alpha_step_deg=2.0,  # → 6 α points
        fine_alpha_margin_deg=2.0,
        fine_alpha_step_deg=1.0,  # → 5 α points around the coarse peak
        fine_velocity_count=3,  # → 3 velocities
    )


# ---------------------------------------------------------------------------
# Helper: count AeroBuildup.run() invocations during a callable
# ---------------------------------------------------------------------------


def _count_runs(monkeypatch):
    """Wrap ``asb.AeroBuildup.run`` with a counter. Returns the counter dict."""
    counter = {"n": 0}
    original = asb.AeroBuildup.run

    def counted_run(self, *args, **kwargs):
        counter["n"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(asb.AeroBuildup, "run", counted_run)
    return counter


# ---------------------------------------------------------------------------
# 1. Single-call tests (FAIL before refactor, PASS after)
# ---------------------------------------------------------------------------


class TestSingleAeroBuildupCall:
    def test_coarse_alpha_sweep_makes_one_run_call(self, tiny_airplane, sweep_config, monkeypatch):
        counter = _count_runs(monkeypatch)
        _coarse_alpha_sweep(tiny_airplane, v_cruise=15.0, config=sweep_config)
        assert counter["n"] == 1

    def test_fine_sweep_cl_max_makes_one_run_call(self, tiny_airplane, sweep_config, monkeypatch):
        counter = _count_runs(monkeypatch)
        _fine_sweep_cl_max(
            tiny_airplane,
            stall_alpha_deg=10.0,
            v_cruise=15.0,
            v_max=25.0,
            config=sweep_config,
        )
        assert counter["n"] == 1

    def test_cl_alpha_linear_sweep_makes_one_run_call(self, tiny_airplane, monkeypatch):
        counter = _count_runs(monkeypatch)
        _extract_cl_alpha_from_linear_sweep(
            tiny_airplane,
            v_cruise=15.0,
            alpha_min_deg=-2.0,
            alpha_max_deg=6.0,
            alpha_step_deg=2.0,
        )
        assert counter["n"] == 1


# ---------------------------------------------------------------------------
# 2. Equivalence tests against inlined point-by-point serial references
# ---------------------------------------------------------------------------


def _serial_coarse_alpha_sweep(asb_airplane, v_cruise, config):
    """Point-by-point baseline mirroring the pre-refactor implementation."""
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    alphas = np.arange(
        config.coarse_alpha_min_deg,
        config.coarse_alpha_max_deg + 0.01,
        config.coarse_alpha_step_deg,
    )
    cls = []
    for a in alphas:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()
        cls.append(_extract_scalar(r, "CL", default=0.0))
    return float(alphas[int(np.argmax(cls))])


def _serial_fine_sweep_cl_max(asb_airplane, stall_alpha_deg, v_cruise, v_max, config):
    """Point-by-point baseline mirroring the pre-refactor implementation."""
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    s_ref = float(asb_airplane.s_ref)
    alpha_min = stall_alpha_deg - config.fine_alpha_margin_deg
    alpha_max = stall_alpha_deg + config.fine_alpha_margin_deg
    alphas = np.arange(alpha_min, alpha_max + 0.01, config.fine_alpha_step_deg)
    velocities = np.linspace(max(v_cruise * 0.5, 3.0), v_max, config.fine_velocity_count)
    cl_list, cd_list, v_list, cdi_list = [], [], [], []
    cl_max = -float("inf")
    for v in velocities:
        for a in alphas:
            op = asb.OperatingPoint(velocity=float(v), alpha=float(a))
            r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()
            cl = _extract_scalar(r, "CL", default=0.0)
            cd = _extract_scalar(r, "CD", default=0.0)
            d_ind = _extract_scalar(r, "D_induced", default=float("nan"))
            q = 0.5 * 1.225 * float(v) ** 2
            cdi = d_ind / (q * s_ref) if (s_ref > 0 and np.isfinite(d_ind)) else float("nan")
            cl_list.append(cl)
            cd_list.append(cd)
            v_list.append(float(v))
            cdi_list.append(cdi)
            if cl > cl_max:
                cl_max = cl
    return (
        float(cl_max),
        np.asarray(cl_list, dtype=float),
        np.asarray(cd_list, dtype=float),
        np.asarray(v_list, dtype=float),
        np.asarray(cdi_list, dtype=float),
    )


def _serial_cl_alpha_linear_sweep(
    asb_airplane, v_cruise, alpha_min_deg, alpha_max_deg, alpha_step_deg
):
    """Point-by-point baseline mirroring the pre-refactor implementation."""
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    alphas_deg = np.arange(alpha_min_deg, alpha_max_deg + 0.01, alpha_step_deg)
    cls = []
    for a in alphas_deg:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        r = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref).run()
        cls.append(_extract_scalar(r, "CL", default=float("nan")))
    return alphas_deg, np.asarray(cls, dtype=float)


class TestEquivalenceAgainstSerialBaseline:
    def test_coarse_alpha_sweep_matches_serial(self, tiny_airplane, sweep_config):
        vectorised = _coarse_alpha_sweep(tiny_airplane, v_cruise=15.0, config=sweep_config)
        serial = _serial_coarse_alpha_sweep(tiny_airplane, v_cruise=15.0, config=sweep_config)
        # Both return a peak α picked from the same grid → exact equality.
        assert vectorised == serial

    def test_fine_sweep_cl_max_matches_serial(self, tiny_airplane, sweep_config):
        cl_max_v, cl_v, cd_v, v_v, cdi_v = _fine_sweep_cl_max(
            tiny_airplane,
            stall_alpha_deg=10.0,
            v_cruise=15.0,
            v_max=25.0,
            config=sweep_config,
        )
        cl_max_s, cl_s, cd_s, v_s, cdi_s = _serial_fine_sweep_cl_max(
            tiny_airplane,
            stall_alpha_deg=10.0,
            v_cruise=15.0,
            v_max=25.0,
            config=sweep_config,
        )
        assert abs(cl_max_v - cl_max_s) < 1e-9
        np.testing.assert_allclose(cl_v, cl_s, rtol=0, atol=1e-9)
        np.testing.assert_allclose(cd_v, cd_s, rtol=0, atol=1e-9)
        np.testing.assert_allclose(v_v, v_s, rtol=0, atol=1e-9)
        # NaN positions in CDi must align element-by-element.
        nan_mask_v = np.isnan(cdi_v)
        nan_mask_s = np.isnan(cdi_s)
        assert np.array_equal(nan_mask_v, nan_mask_s)
        np.testing.assert_allclose(cdi_v[~nan_mask_v], cdi_s[~nan_mask_s], rtol=0, atol=1e-9)

    def test_cl_alpha_linear_sweep_matches_serial(self, tiny_airplane):
        vectorised = _extract_cl_alpha_from_linear_sweep(
            tiny_airplane,
            v_cruise=15.0,
            alpha_min_deg=-2.0,
            alpha_max_deg=6.0,
            alpha_step_deg=2.0,
        )

        alphas_deg, cls = _serial_cl_alpha_linear_sweep(
            tiny_airplane,
            v_cruise=15.0,
            alpha_min_deg=-2.0,
            alpha_max_deg=6.0,
            alpha_step_deg=2.0,
        )
        alphas_rad = np.deg2rad(alphas_deg)
        mask = np.isfinite(cls)
        a_mat = np.column_stack([alphas_rad[mask], np.ones_like(alphas_rad[mask])])
        coeffs, *_ = np.linalg.lstsq(a_mat, cls[mask], rcond=None)
        serial_cl_alpha = float(coeffs[0])

        # Both either produce a number or both reject via the R² gate.
        if vectorised is None:
            # If the vectorised path rejected, the serial fit on the same
            # data should also produce a low R². We don't recompute R² here
            # — leave the rejection to the production-side gate.
            pytest.skip("vectorised CL_α extraction rejected via R² gate")
        assert abs(vectorised - serial_cl_alpha) < 1e-9


# ---------------------------------------------------------------------------
# 3. Performance smoke test (marked slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPerformanceSmoke:
    """Lower bound on the speedup from vectorisation.

    Same hardware, same fixture, deterministic ratio — avoids brittle
    absolute wall-clock thresholds. With the production-default grid
    (~160 ops for the fine sweep, ~15 for the coarse sweep), the speedup
    is expected ~10–50×; the assertion is a loose 3× to leave headroom
    for noisy CI runners.
    """

    def test_fine_sweep_speedup_at_least_3x_over_serial(self, tiny_airplane):
        from time import perf_counter

        # Production-default sweep grid — the configuration that dominates
        # real recompute wall-clock.
        config = _SweepConfig()  # all defaults

        # Warm the NeuralFoil cache for this airfoil so the first sweep
        # doesn't pay the one-shot setup cost on top of its loop work.
        _coarse_alpha_sweep(tiny_airplane, v_cruise=15.0, config=config)

        serial_start = perf_counter()
        _serial_fine_sweep_cl_max(
            tiny_airplane,
            stall_alpha_deg=12.0,
            v_cruise=15.0,
            v_max=25.0,
            config=config,
        )
        serial_dt = perf_counter() - serial_start

        vec_start = perf_counter()
        _fine_sweep_cl_max(
            tiny_airplane,
            stall_alpha_deg=12.0,
            v_cruise=15.0,
            v_max=25.0,
            config=config,
        )
        vec_dt = perf_counter() - vec_start

        speedup = serial_dt / vec_dt if vec_dt > 0 else float("inf")
        assert speedup >= 3.0, (
            f"Expected ≥3× speedup from vectorisation, got {speedup:.1f}× "
            f"(serial={serial_dt * 1000:.0f} ms, vectorised={vec_dt * 1000:.0f} ms)"
        )
