"""gh-672: α-resolution auto-recovery for the parabolic polar fit.

When the fit is rejected because the α-sweep was too coarse
(``insufficient_points`` / ``non_monotonic_polar``), the service re-runs a
*finer* sweep and refits — up to 2 times — instead of dropping straight to the
0.8 Oswald fallback. Only resolution is increased; no threshold is loosened
(memory ``feedback_aerobuildup_resolution``).

Pure logic with mocked solver/fit, so these run in the fast tier.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from app.schemas.polar_by_config import ParabolicPolar, PolarRejection
from app.services import assumption_compute_service as svc


def _config(step: float = 0.5, margin: float = 5.0):
    return SimpleNamespace(fine_alpha_step_deg=step, fine_alpha_margin_deg=margin)


def _reject(gate: str, category: str) -> PolarRejection:
    return PolarRejection(gate=gate, category=category, fitted_value=1.0, threshold="x", hint="h")


def _dummy_sweep():
    # (cl_max, cl_arr, cd_arr, v_arr, cdi_arr)
    cl = np.array([0.1, 0.5, 0.9])
    cd = np.array([0.01, 0.02, 0.05])
    return (1.2, cl, cd, np.array([14.0, 14.0, 14.0]), np.array([0.005, 0.01, 0.03]))


def _call(**overrides):
    kwargs = dict(
        asb_airplane=object(),
        stall_alpha_deg=8.0,
        v_cruise=14.0,
        v_max=20.0,
        config=_config(),
        aspect_ratio=8.0,
        cl_max_for_fit=1.2,
        cd0_stability=0.02,
        cl=np.array([0.1, 0.5, 0.9]),
        cd=np.array([0.01, 0.02, 0.05]),
    )
    kwargs.update(overrides)
    return svc._fit_parabolic_polar_with_refinement(**kwargs)


class TestAutoRecovery:
    def test_insufficient_points_retries_once_then_succeeds(self):
        rej = _reject("insufficient_points", "sweep")
        good = (0.02, 0.85, 0.98, None)
        with (
            patch.object(
                svc, "_fit_parabolic_polar", side_effect=[(None, None, None, rej), good]
            ) as m_fit,
            patch.object(svc, "_fine_sweep_cl_max", return_value=_dummy_sweep()) as m_sweep,
        ):
            cd0, e, r2, rejection, auto_refined = _call()

        assert (cd0, e, r2) == (0.02, 0.85, 0.98)
        assert rejection is None
        assert auto_refined is True
        assert m_sweep.call_count == 1  # exactly one refinement
        assert m_fit.call_count == 2
        # the retry halved the step and widened the margin (×1.5)
        kw = m_sweep.call_args.kwargs
        assert kw["alpha_step_override"] == 0.25  # 0.5 / 2
        assert kw["alpha_margin_override"] == 7.5  # 5.0 * 1.5

    def test_non_monotonic_retries_twice_then_passes_rejection_through(self):
        rej = _reject("non_monotonic_polar", "data")
        with (
            patch.object(
                svc,
                "_fit_parabolic_polar",
                side_effect=[(None, None, None, rej)] * 3,  # initial + 2 retries all reject
            ) as m_fit,
            patch.object(svc, "_fine_sweep_cl_max", return_value=_dummy_sweep()) as m_sweep,
        ):
            cd0, e, r2, rejection, auto_refined = _call()

        assert rejection is not None and rejection.gate == "non_monotonic_polar"
        assert auto_refined is False  # refinement didn't help → no banner
        assert m_sweep.call_count == 2  # capped at max_retries
        assert m_fit.call_count == 3

    def test_non_refinable_gate_does_not_retry(self):
        rej = _reject("negative_slope_k", "design")
        with (
            patch.object(
                svc, "_fit_parabolic_polar", return_value=(None, None, None, rej)
            ) as m_fit,
            patch.object(svc, "_fine_sweep_cl_max") as m_sweep,
        ):
            cd0, e, r2, rejection, auto_refined = _call()

        assert rejection is not None and rejection.gate == "negative_slope_k"
        assert auto_refined is False
        m_sweep.assert_not_called()  # design rejections are not a resolution problem
        assert m_fit.call_count == 1

    def test_clean_fit_on_first_try_does_not_refine(self):
        with (
            patch.object(svc, "_fit_parabolic_polar", return_value=(0.02, 0.85, 0.99, None)),
            patch.object(svc, "_fine_sweep_cl_max") as m_sweep,
        ):
            cd0, e, r2, rejection, auto_refined = _call()

        assert rejection is None
        assert auto_refined is False
        m_sweep.assert_not_called()

    def test_second_retry_step_quartered(self):
        """A gate that resolves only on the 2nd retry uses step/4, margin×2.25."""
        rej = _reject("insufficient_points", "sweep")
        good = (0.02, 0.8, 0.97, None)
        with (
            patch.object(
                svc,
                "_fit_parabolic_polar",
                side_effect=[(None, None, None, rej), (None, None, None, rej), good],
            ),
            patch.object(svc, "_fine_sweep_cl_max", return_value=_dummy_sweep()) as m_sweep,
        ):
            _cd0, _e, _r2, rejection, auto_refined = _call()

        assert rejection is None and auto_refined is True
        assert m_sweep.call_count == 2
        last = m_sweep.call_args_list[-1].kwargs
        assert last["alpha_step_override"] == 0.125  # 0.5 / 2**2
        assert last["alpha_margin_override"] == 11.25  # 5.0 * 1.5**2


class TestParabolicPolarSchema:
    def test_auto_refined_defaults_false(self):
        p = ParabolicPolar(cl_max=1.2)
        assert p.auto_refined is False

    def test_auto_refined_roundtrips(self):
        p = ParabolicPolar(cl_max=1.2, auto_refined=True)
        assert ParabolicPolar.model_validate(p.model_dump()).auto_refined is True
