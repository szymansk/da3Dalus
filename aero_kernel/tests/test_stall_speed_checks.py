"""The postconditions of stall-speed, on hand-made polars (canon K32, Q25)."""

import math
from collections.abc import Mapping

import pytest
from aero_kernel.formulas.stall_speed import (
    alpha_range_past_inverted_stall,
    cl_max_at_stall_reynolds_number,
    optimum_at_first_cl_peak,
    optimum_at_first_cl_trough,
)
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import Polar

RHO, MASS, GRAVITY = 1.225, 1.5, 9.81
STEP = 0.25


def plane() -> AirplaneGeometry:
    """Reference area 2 * 0.7 m * 0.2 m = 0.28 m^2 (projected, mirrored)."""
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y in (0.0, 0.7)
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


def upright_polar(peak_at: float = 15.75, peak: float = 1.19) -> Polar:
    """A lift curve that rises to ``peak`` at ``peak_at`` deg, falls to a plateau and rises again."""
    alphas = [a * STEP for a in range(-20, 101)]  # -5 .. 25 deg

    def cl(alpha: float) -> float:
        if alpha <= peak_at:
            return peak - 0.1 * (peak_at - alpha) * 0.4
        return max(peak - 0.2 * (alpha - peak_at), 0.8) + (
            0.02 * (alpha - 22.0) if alpha > 22.0 else 0.0
        )

    return Polar(
        alpha_deg=tuple(alphas),
        cl=tuple(cl(a) for a in alphas),
        cd=(0.05,) * len(alphas),
        cm=(-0.02,) * len(alphas),
    )


def x_of(n: float = 1.0) -> Mapping[str, object]:
    return {"airplane": plane(), "m": MASS, "g": GRAVITY, "n_load": n, "rho": RHO}


def y_of(polar: Polar, alpha_s: float, n: float = 1.0) -> dict[str, object]:
    cl = polar.cl[polar.alpha_deg.index(alpha_s)]
    v_s = math.sqrt(2.0 * abs(n) * MASS * GRAVITY / (RHO * 0.28 * abs(cl)))
    return {"v_s": v_s, "cl_max": cl, "alpha_s": alpha_s, "polar": polar}


def test_the_probe_holds_when_the_lift_balance_closes_at_the_polar_sample() -> None:
    polar = upright_polar()
    assert cl_max_at_stall_reynolds_number(x_of(), y_of(polar, 15.75)).state == "held"


def test_the_probe_is_violated_when_v_s_does_not_close_the_lift_balance() -> None:
    polar = upright_polar()
    y = y_of(polar, 15.75)
    y["v_s"] = float(y["v_s"]) * 1.01  # type: ignore[arg-type]  # the value is a float
    result = cl_max_at_stall_reynolds_number(x_of(), y)
    assert result.state == "violated"
    assert "V_S" in result.message


def test_the_probe_is_violated_when_cl_max_is_not_the_polar_value_at_alpha_s() -> None:
    polar = upright_polar()
    y = y_of(polar, 15.75)
    y["cl_max"] = float(y["cl_max"]) + 0.01  # type: ignore[arg-type]
    assert cl_max_at_stall_reynolds_number(x_of(), y).state == "violated"


def test_the_probe_is_violated_when_alpha_s_is_not_a_sample_of_the_polar() -> None:
    polar = upright_polar()
    y = y_of(polar, 15.75)
    y["alpha_s"] = 15.8
    assert cl_max_at_stall_reynolds_number(x_of(), y).state == "violated"


def test_the_probe_of_inverted_flight_uses_the_magnitudes() -> None:
    alphas = [a * STEP for a in range(-60, 21)]  # -15 .. 5 deg
    cl = [-0.7 + 0.03 * (a + 10.0) ** 2 / 10.0 * (1 if a > -10 else 0.3) for a in alphas]
    polar = Polar(alpha_deg=tuple(alphas), cl=tuple(cl), cd=(0.05,) * len(cl), cm=(0.0,) * len(cl))
    y = y_of(polar, -10.0, n=-1.0)
    assert cl_max_at_stall_reynolds_number(x_of(-1.0), y).state == "held"


def test_the_first_peak_check_holds_when_alpha_s_is_at_the_first_sampled_peak() -> None:
    polar = upright_polar()
    assert optimum_at_first_cl_peak(x_of(), y_of(polar, 15.75)).state == "held"


def test_the_first_peak_check_is_violated_on_the_later_lower_branch() -> None:
    """The BRYAN failure: IPOPT found the second maximum (23 deg) instead of the first (12 deg)."""
    polar = upright_polar()
    result = optimum_at_first_cl_peak(x_of(), y_of(polar, 23.0))
    assert result.state == "violated"


def test_the_first_peak_check_is_violated_when_the_curve_never_turns() -> None:
    alphas = tuple(a * STEP for a in range(0, 41))
    polar = Polar(
        alpha_deg=alphas,
        cl=tuple(0.1 * i * STEP for i in range(41)),
        cd=(0.05,) * 41,
        cm=(0.0,) * 41,
    )
    assert optimum_at_first_cl_peak(x_of(), y_of(polar, 5.0)).state == "violated"


def inverted_polar(trough_at: float = -10.0) -> Polar:
    alphas = [a * STEP for a in range(-60, 21)]  # -15 .. 5 deg
    cl = [-0.7 + 0.02 * abs(a - trough_at) for a in alphas]
    return Polar(alpha_deg=tuple(alphas), cl=tuple(cl), cd=(0.05,) * 81, cm=(0.0,) * 81)


def test_the_first_trough_check_holds_at_the_first_sampled_trough() -> None:
    polar = inverted_polar()
    assert optimum_at_first_cl_trough(x_of(-1.0), y_of(polar, -10.0, n=-1.0)).state == "held"


def test_the_first_trough_check_is_violated_away_from_the_trough() -> None:
    polar = inverted_polar()
    assert optimum_at_first_cl_trough(x_of(-1.0), y_of(polar, -5.0, n=-1.0)).state == "violated"


def test_the_inverted_range_check_holds_when_the_trough_is_inside_the_sweep() -> None:
    assert (
        alpha_range_past_inverted_stall(x_of(-1.0), y_of(inverted_polar(), -10.0, -1.0)).state
        == "held"
    )


def test_the_inverted_range_check_is_violated_when_the_trough_is_on_the_boundary() -> None:
    """A boundary sample is never passed off as C_L,min (ADR 0020)."""
    polar = inverted_polar(trough_at=-15.0)  # the curve still falls at the first sample
    result = alpha_range_past_inverted_stall(x_of(-1.0), y_of(polar, -15.0, n=-1.0))
    assert result.state == "violated"


@pytest.mark.parametrize("check", [optimum_at_first_cl_peak, optimum_at_first_cl_trough])
def test_the_extremum_checks_are_unchecked_without_a_polar(check: object) -> None:
    y: dict[str, object] = {"v_s": 8.0, "cl_max": 1.2, "alpha_s": 15.0, "polar": None}
    assert check(x_of(), y).state == "unchecked"  # type: ignore[operator]


def peak_y(alpha_s: float, cl_max: float) -> dict[str, object]:
    """A result whose polar peaks at 15.75 deg (C_L 1.19), with a chosen optimum."""
    polar = upright_polar()
    return {"v_s": 8.0, "cl_max": cl_max, "alpha_s": alpha_s, "polar": polar}


def trough_y(alpha_s: float, cl_max: float) -> dict[str, object]:
    return {"v_s": 8.0, "cl_max": cl_max, "alpha_s": alpha_s, "polar": inverted_polar()}


def test_the_peak_check_is_violated_when_cl_max_falls_short_of_the_sampled_peak() -> None:
    sampled = upright_polar()
    peak = sampled.cl[sampled.alpha_deg.index(15.75)]
    result = optimum_at_first_cl_peak(x_of(), peak_y(15.75, peak - 1e-3))
    assert result.state == "violated"
    assert "short of the first sampled peak" in result.message


def test_the_peak_check_tolerates_numerical_noise_below_the_sampled_peak() -> None:
    sampled = upright_polar()
    peak = sampled.cl[sampled.alpha_deg.index(15.75)]
    assert optimum_at_first_cl_peak(x_of(), peak_y(15.75, peak - 1e-7)).state == "held"
    assert optimum_at_first_cl_peak(x_of(), peak_y(15.75, peak + 1e-3)).state == "held"


def test_the_trough_check_is_violated_when_cl_max_lies_above_the_sampled_trough() -> None:
    sampled = inverted_polar()
    trough = sampled.cl[sampled.alpha_deg.index(-10.0)]
    result = optimum_at_first_cl_trough(x_of(-1.0), trough_y(-10.0, trough + 1e-3))
    assert result.state == "violated"
    assert "short of the first sampled trough" in result.message


def test_the_trough_check_tolerates_numerical_noise_above_the_sampled_trough() -> None:
    sampled = inverted_polar()
    trough = sampled.cl[sampled.alpha_deg.index(-10.0)]
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-10.0, trough + 1e-7)).state == "held"
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-10.0, trough - 1e-3)).state == "held"


def test_the_peak_window_is_one_sweep_step() -> None:
    """alpha_S 0.25 deg from the sampled peak is held, 0.5 deg is another branch."""
    sampled = upright_polar()
    peak = sampled.cl[sampled.alpha_deg.index(15.75)]
    assert optimum_at_first_cl_peak(x_of(), peak_y(16.0, peak)).state == "held"
    assert optimum_at_first_cl_peak(x_of(), peak_y(15.5, peak)).state == "held"
    assert optimum_at_first_cl_peak(x_of(), peak_y(16.25, peak)).state == "violated"
    assert optimum_at_first_cl_peak(x_of(), peak_y(15.25, peak)).state == "violated"


def test_the_trough_window_is_one_sweep_step() -> None:
    sampled = inverted_polar()
    trough = sampled.cl[sampled.alpha_deg.index(-10.0)]
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-9.75, trough)).state == "held"
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-10.25, trough)).state == "held"
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-9.5, trough)).state == "violated"
    assert optimum_at_first_cl_trough(x_of(-1.0), trough_y(-10.5, trough)).state == "violated"
