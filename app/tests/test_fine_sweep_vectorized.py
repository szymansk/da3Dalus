"""Regression test for _fine_sweep_cl_max vectorisation (gh-670).

The refactor must be bit-identical to the naive double-loop reference
implementation in CL, CD, V and CDi per grid point — see issue #670.

The test contains its own reference loop so that the assertion is
self-contained: after refactor, the real function still has to produce
exactly what the reference loop produces. The test is therefore a
characterisation test for the function's numerical contract.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest

from app.core.platform import aerosandbox_available
from app.models.computation_config import AircraftComputationConfigModel

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="aerosandbox excluded on this platform (linux/aarch64)",
)


def _build_minimal_airplane():
    """Tiny but valid trapezoidal wing — enough for AeroBuildup to converge."""
    import aerosandbox as asb

    return asb.Airplane(
        name="gh-670-test",
        wings=[
            asb.Wing(
                name="MainWing",
                symmetric=True,
                xsecs=[
                    asb.WingXSec(
                        xyz_le=[0.0, 0.0, 0.0], chord=0.20, airfoil=asb.Airfoil("naca0012")
                    ),
                    asb.WingXSec(
                        xyz_le=[0.05, 0.6, 0.0], chord=0.15, airfoil=asb.Airfoil("naca0012")
                    ),
                ],
            )
        ],
    )


def _reference_loop_output(airplane, stall_alpha_deg, v_cruise, v_max, config):
    """Naive double-loop reference (mirror of the pre-gh-670 implementation).

    This is the spec the vectorised version must match exactly.
    """
    import aerosandbox as asb

    from app.services.assumption_compute_service import _extract_scalar

    alpha_min = stall_alpha_deg - config.fine_alpha_margin_deg
    alpha_max = stall_alpha_deg + config.fine_alpha_margin_deg
    alphas = np.arange(alpha_min, alpha_max + 0.01, config.fine_alpha_step_deg)

    v_stall_approx = max(v_cruise * 0.5, 3.0)
    velocities = np.linspace(v_stall_approx, v_max, config.fine_velocity_count)

    xyz_ref = list(airplane.xyz_ref) if airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    s_ref = float(airplane.s_ref)

    cl_list: list[float] = []
    cd_list: list[float] = []
    v_list: list[float] = []
    cdi_list: list[float] = []
    cl_max = -float("inf")

    for v in velocities:
        for a in alphas:
            op = asb.OperatingPoint(velocity=float(v), alpha=float(a))
            r = asb.AeroBuildup(airplane=airplane, op_point=op, xyz_ref=xyz_ref).run()
            cl = _extract_scalar(r, "CL", default=0.0)
            cd = _extract_scalar(r, "CD", default=0.0)
            d_induced = _extract_scalar(r, "D_induced", default=float("nan"))
            q = 0.5 * 1.225 * float(v) ** 2
            cdi = (
                d_induced / (q * s_ref) if (s_ref > 0 and np.isfinite(d_induced)) else float("nan")
            )
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


@pytest.mark.slow
def test_fine_sweep_cl_max_matches_reference_loop():
    """Vectorised _fine_sweep_cl_max must match the naive loop bit-for-bit.

    Grid: 3 velocities × 5 alphas = 15 AeroBuildup evaluations.
    Tolerances are tight (rtol=1e-10) because the only legitimate
    difference is float-summation order, which AeroBuildup avoids when
    given arrays vs. scalars (NumPy elementwise ops are bit-stable).
    """
    from app.services.assumption_compute_service import _fine_sweep_cl_max

    airplane = _build_minimal_airplane()
    config = SimpleNamespace(
        fine_alpha_margin_deg=2.0,
        fine_alpha_step_deg=1.0,
        fine_velocity_count=3,
    )
    stall_alpha_deg = 12.0
    v_cruise = 15.0
    v_max = 25.0

    cfg = cast(AircraftComputationConfigModel, config)
    expected = _reference_loop_output(airplane, stall_alpha_deg, v_cruise, v_max, cfg)
    actual = _fine_sweep_cl_max(airplane, stall_alpha_deg, v_cruise, v_max, cfg)

    expected_cl_max, e_cl, e_cd, e_v, e_cdi = expected
    actual_cl_max, a_cl, a_cd, a_v, a_cdi = actual

    # Length must match: outer V × inner alpha = (count V) × (count alpha)
    assert len(a_cl) == len(e_cl)
    assert len(a_cd) == len(e_cd)
    assert len(a_v) == len(e_v)
    assert len(a_cdi) == len(e_cdi)

    np.testing.assert_allclose(a_cl, e_cl, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(a_cd, e_cd, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(a_v, e_v, rtol=1e-12, atol=1e-12)

    # CDi may carry NaN if D_induced is missing — equal_nan to compare structure.
    np.testing.assert_array_equal(np.isnan(a_cdi), np.isnan(e_cdi))
    finite_mask = ~np.isnan(a_cdi)
    np.testing.assert_allclose(a_cdi[finite_mask], e_cdi[finite_mask], rtol=1e-10, atol=1e-12)

    # cl_max must come from the very same array
    assert actual_cl_max == pytest.approx(expected_cl_max, rel=1e-12)
    assert actual_cl_max == pytest.approx(float(np.max(a_cl)), rel=1e-12)


@pytest.mark.slow
def test_fine_sweep_cl_max_grid_order_outer_v_inner_alpha():
    """Document and lock the array ordering convention: outer velocity, inner alpha.

    The flat array index i corresponds to (v_index = i // n_alpha, a_index = i % n_alpha).
    Downstream consumers (parabolic polar fit, polar_re_table_service) rely on
    this layout — changing it silently would break them.
    """
    from app.services.assumption_compute_service import _fine_sweep_cl_max

    airplane = _build_minimal_airplane()
    config = SimpleNamespace(
        fine_alpha_margin_deg=2.0,
        fine_alpha_step_deg=1.0,
        fine_velocity_count=3,
    )

    _, _, _, v_arr, _ = _fine_sweep_cl_max(
        airplane,
        stall_alpha_deg=12.0,
        v_cruise=15.0,
        v_max=25.0,
        config=cast(AircraftComputationConfigModel, config),
    )

    # 5 alphas per velocity (margin 2°, step 1° → -2,-1,0,1,2 around stall = 5)
    # 3 velocities → 15 total samples
    n_alpha = 5
    n_v = 3
    assert len(v_arr) == n_v * n_alpha

    # Each block of n_alpha consecutive entries must carry the same velocity.
    for v_idx in range(n_v):
        block = v_arr[v_idx * n_alpha : (v_idx + 1) * n_alpha]
        assert np.all(block == block[0]), (
            f"velocity block {v_idx} is not constant — array order is not "
            "(outer V, inner alpha) as required by gh-670 contract"
        )
