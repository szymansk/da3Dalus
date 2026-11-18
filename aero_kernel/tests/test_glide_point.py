"""The glide point: the steady glide at a given speed, read off one sweep (canon butterfly-approach)."""

import math

import numpy as np
import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as glide_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import GlideRequest, glide_point_worker
from aero_kernel.solvers.stall_math import crossing_below_peak
from aero_kernel.tests.formula_builders import close

ALPHAS = (-2.0, 0.0, 2.0, 4.0, 6.0, 8.0)
CL = (0.0, 0.2, 0.4, 0.6, 0.8, 0.7)  # the peak is at 6 deg
AIR = AirState(density=1.2, dynamic_viscosity=1.8e-5, speed_of_sound=340.0)


def test_the_crossing_is_interpolated_between_the_samples_below_the_peak() -> None:
    assert crossing_below_peak(ALPHAS, CL, 4, 0.5) == (2, 0.5)


def test_a_level_above_the_peak_has_no_crossing() -> None:
    assert crossing_below_peak(ALPHAS, CL, 4, 0.9) is None


def test_a_level_on_a_sample_is_that_sample() -> None:
    assert crossing_below_peak(ALPHAS, CL, 4, 0.4) == (2, 0.0)


def test_a_level_below_the_whole_branch_has_no_crossing() -> None:
    assert crossing_below_peak(ALPHAS, CL, 4, -0.5) is None


def request(v_ms: float) -> GlideRequest:
    return GlideRequest(
        airplane=AirplaneGeometry.model_validate({"name": "t"}),
        mass_kg=1.0,
        gravity=9.81,
        air=AIR,
        v_ms=v_ms,
        k_e_d0=1.0,
    )


class Airplane:
    s_ref = 0.2


def install(monkeypatch: pytest.MonkeyPatch, cl: tuple[float, ...], cd: float = 0.05) -> None:
    def sweep(
        _airplane: object,
        _air: AirState,
        velocity_ms: float,
        alphas_deg: list[float],
        _size: str,
        _factor: float,
    ) -> Polar:
        values = [float(np.interp(a, ALPHAS, cl)) for a in alphas_deg]
        return Polar(alpha_deg=tuple(alphas_deg), cl=tuple(values), cd=(cd,) * len(alphas_deg))

    monkeypatch.setattr(glide_module, "sweep_polar", sweep)

    def convert(_airplane: AirplaneGeometry) -> Airplane:
        return Airplane()

    monkeypatch.setattr(glide_module, "to_asb_airplane", convert)


def test_the_glide_angle_is_the_arctangent_of_drag_over_lift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, CL)
    # at 12 m/s: C_L = m g / (q S) = 9.81 / (0.5 * 1.2 * 144 * 0.2) = 0.5677083
    solution = glide_point_worker(request(12.0)).value
    assert close(solution.cl, 0.5677083, 1e-6)
    assert close(solution.alpha_deg, 2.0 + 2.0 * (0.5677083 - 0.4) / 0.2, 1e-3)
    assert close(solution.glide_angle_deg, math.degrees(math.atan(0.05 / 0.5677083)), 1e-6)


def test_a_speed_below_the_stall_speed_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, CL)
    # at 10 m/s the C_L needed, 0.8175, is above the peak 0.8
    with pytest.raises(FormulaError) as raised:
        glide_point_worker(request(10.0))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


def test_a_sweep_without_a_peak_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, (0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    with pytest.raises(FormulaError) as raised:
        glide_point_worker(request(12.0))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
