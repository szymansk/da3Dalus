"""The stall bracket is the main C_L maximum, not the first local one (gh-1423, maintainer 2026-11-27):
the local maximum above alpha = 0 with the largest fall behind it.

Faked sweeps with more than one local maximum (the solver boundary is the recording fake): the
bracket, the window of alpha and the start IPOPT receives are read off the problem the worker states.
Hand values: S_ref = 0.28 m^2, rho = 1.225 kg/m^3, weight 1.5 kg * 9.81 m/s^2 = 14.715 N, so the
speed at which a lift coefficient C_L carries the weight is sqrt(2 * 14.715 / (1.225 * 0.28 * C_L)).
"""

import math
from collections.abc import Callable, Sequence
from itertools import pairwise
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import StallRequest
from aero_kernel.tests.asb_fakes import RecordingBoundary
from aero_kernel.tests.solver_builders import AIR, K_E_D0, airplane, direct_aero_model

pytestmark = pytest.mark.asyncio

Knots = Sequence[tuple[float, float]]

# The Avistar shape: a shoulder at 8 deg (C_L 1.21, 0.01 deep), the main maximum 1.34 at 16.5 deg and
# a lower post-stall maximum 1.07 at 23 deg.
SHOULDER: Knots = (
    (-15.0, -0.6),
    (8.0, 1.21),
    (8.5, 1.20),
    (16.5, 1.34),
    (20.0, 0.9),
    (23.0, 1.07),
    (25.0, 0.95),
)
# Two maxima whose falls depend on the speed: at 8 deg and at 18 deg. LOW_FIRST: 1.25 at 8 deg falls
# 0.35 to the end (the climb back to 1.10 is 0.1, less than half of 0.25), 1.10 at 18 deg falls 0.2.
# HIGH_SECOND: 1.20 at 8 deg falls 0.2 before the curve recovers, 1.25 at 18 deg falls 0.35.
LOW_FIRST: Knots = ((-15.0, -0.6), (8.0, 1.25), (12.0, 1.0), (18.0, 1.10), (25.0, 0.9))
HIGH_SECOND: Knots = ((-15.0, -0.6), (8.0, 1.20), (12.0, 1.0), (18.0, 1.25), (25.0, 0.9))
# The WINDFREAK shape: the stall at 9.5 deg (0.860, falling to 0.744) and a higher flat plateau
# behind it (0.885 at 22 deg, 0.874 at the end of the sweep).
PLATEAU: Knots = ((-15.0, -0.6), (9.5, 0.860), (13.0, 0.744), (22.0, 0.885), (25.0, 0.874))
# The SNOOPY shape: a front hump 1.447 at 7.25 deg falling 0.12, then 1.420 at 13 deg falling 0.42.
HUMP: Knots = ((-15.0, -0.6), (7.25, 1.447), (10.0, 1.327), (13.0, 1.420), (25.0, 1.0))
# No interior maximum above alpha = 0: the curve rises to the end of the sweep.
RISING: Knots = ((-15.0, -0.6), (25.0, 1.4))
# The curve ends above its only interior maximum (1.1 at 10 deg): the low-Reynolds shape.
END_ABOVE: Knots = ((-15.0, -0.6), (10.0, 1.1), (14.0, 0.9), (25.0, 1.5))
# Inverted: a shoulder trough -0.5 at -6 deg and the main trough -0.7 at -11 deg.
INVERTED_SHOULDER: Knots = ((-15.0, -0.4), (-11.0, -0.7), (-6.5, -0.49), (-6.0, -0.5), (25.0, 1.5))


def curve(knots: Knots, alphas: Sequence[float]) -> Polar:
    """The piecewise-linear lift curve through ``knots`` sampled at ``alphas``."""

    def cl(alpha: float) -> float:
        for (a0, c0), (a1, c1) in pairwise(knots):
            if alpha <= a1:
                return c0 + (c1 - c0) * (alpha - a0) / (a1 - a0)
        return knots[-1][1]

    return Polar(alpha_deg=tuple(alphas), cl=tuple(cl(a) for a in alphas), cd=(0.05,) * len(alphas))


def speed_for(cl: float, n_load: float = 1.0) -> float:
    return math.sqrt(2.0 * abs(n_load) * 1.5 * 9.81 / (1.225 * 0.28 * abs(cl)))


def install(
    monkeypatch: pytest.MonkeyPatch,
    knots_at: Callable[[float], Knots],
    optimum: tuple[float, float],
    n_load: float = 1.0,
) -> tuple[StallRequest, RecordingBoundary, list[float]]:
    """Fake the solver boundary: the sweep at speed ``v`` answers ``knots_at(v)``, IPOPT ``optimum``.

    Returns:
        The request, the boundary recording the problem, and the speeds of the bracketing sweeps.
    """
    boundary = RecordingBoundary(
        ("speed", "alpha"), {"speed": optimum[0], "alpha": optimum[1]}, ("L",)
    )
    swept: list[float] = []

    def sweep(
        _plane: object, _air: object, speed: float, angles: Sequence[float], *_: object
    ) -> Polar:
        swept.append(speed)
        return curve(knots_at(speed), angles)

    def publish(
        _plane: object, _air: object, speed: float, angles: Sequence[float], *_: object
    ) -> Polar:
        return curve(knots_at(speed), angles)

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28)

    monkeypatch.setattr(opti_module, "sweep_lift", sweep)
    monkeypatch.setattr(opti_module, "sweep_polar", publish)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", boundary.namespace)
    monkeypatch.setattr(opti_module, "aero_model", direct_aero_model)
    request = StallRequest(
        airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=n_load, air=AIR, k_e_d0=K_E_D0
    )
    return request, boundary, swept


async def test_the_stall_is_bracketed_at_the_main_maximum_behind_a_shoulder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first local maximum (1.21 at 8 deg) is not the stall: the window of alpha ends one step
    past the main maximum (16.5 + 0.25 = 16.75 deg), IPOPT starts at 16.5 deg, and the second
    bracketing sweep runs at the speed the main maximum implies,
    sqrt(2 * 14.715 / (1.225 * 0.28 * 1.34)) = 8.0019 m/s (the shoulder would give 8.4209 m/s)."""
    v_main = speed_for(1.34)
    request, boundary, swept = install(monkeypatch, lambda _v: SHOULDER, (v_main, 16.5))
    outcome = opti_module.stall_worker(request)
    (problem,) = boundary.problems
    alpha = problem.variables["alpha"]
    assert (alpha["lower_bound"], alpha["upper_bound"], alpha["init_guess"]) == (-15.0, 16.75, 16.5)
    assert math.isclose(swept[1], 8.0019, abs_tol=5e-5)
    assert math.isclose(problem.variables["speed"]["init_guess"], v_main, rel_tol=1e-12)
    assert (outcome.value.alpha_s, outcome.value.cl_max) == (16.5, 1.34)
    assert math.isclose(outcome.value.v_s, 8.0019, abs_tol=5e-5)


async def test_the_bracket_follows_the_higher_of_two_maxima_at_the_speed_of_the_second_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The main maximum is read at the speed of each sweep. The first sweep (C_L 1 assumed: 9.26 m/s)
    sees the stall at 8 deg (1.25); the second runs at the speed 1.25 implies (8.28 m/s), where the
    maximum at 18 deg has the larger fall (1.25): the window ends at 18.25 deg, the start is 18 deg."""

    def knots_at(speed: float) -> Knots:
        return LOW_FIRST if speed > 9.0 else HIGH_SECOND

    request, boundary, swept = install(monkeypatch, knots_at, (speed_for(1.25), 18.0))
    opti_module.stall_worker(request)
    assert math.isclose(swept[0], speed_for(1.0), rel_tol=1e-12)
    assert math.isclose(swept[1], speed_for(1.25), rel_tol=1e-12)
    (problem,) = boundary.problems
    alpha = problem.variables["alpha"]
    assert (alpha["upper_bound"], alpha["init_guess"]) == (18.25, 18.0)


async def test_a_sweep_that_still_rises_at_its_end_without_an_interior_maximum_has_no_stall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The end of the sweep is no maximum: no value, the 'no peak' failure as before."""
    request, _, _ = install(monkeypatch, lambda _v: RISING, (8.0, 25.0))
    with pytest.raises(FormulaError) as failure:
        opti_module.stall_worker(request)
    assert failure.value.category is ErrorCategory.NOT_CONVERGED
    assert "has no peak inside -15.0..25.0 deg" in failure.value.message


async def test_the_highest_interior_maximum_counts_where_the_sweep_ends_above_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The curve ends at 1.5, above its interior maximum 1.1 at 10 deg: the stall is bracketed at
    10 deg (window to 10.25 deg), at the speed 1.1 implies."""
    request, boundary, swept = install(monkeypatch, lambda _v: END_ABOVE, (speed_for(1.1), 10.0))
    outcome = opti_module.stall_worker(request)
    (problem,) = boundary.problems
    assert problem.variables["alpha"]["upper_bound"] == 10.25
    assert math.isclose(swept[1], speed_for(1.1), rel_tol=1e-12)
    assert outcome.value.cl_max == 1.1


async def test_the_inverted_stall_is_bracketed_at_the_main_trough_behind_a_shoulder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirror: scanning down from alpha = 0 the first trough is -0.5 at -6 deg, the main one -0.7 at
    -11 deg. The window runs from -11.25 deg to the end of the sweep, the start is -11 deg."""
    request, boundary, swept = install(
        monkeypatch, lambda _v: INVERTED_SHOULDER, (speed_for(0.7), -11.0), n_load=-1.0
    )
    outcome = opti_module.stall_worker(request)
    (problem,) = boundary.problems
    alpha = problem.variables["alpha"]
    assert (alpha["lower_bound"], alpha["upper_bound"], alpha["init_guess"]) == (
        -11.25,
        25.0,
        -11.0,
    )
    assert math.isclose(swept[1], speed_for(0.7), rel_tol=1e-12)
    assert math.isclose(outcome.value.cl_max, -0.7, abs_tol=1e-12)


async def test_the_stall_is_bracketed_before_a_higher_plateau_with_a_small_fall_behind_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The plateau maximum (0.885 at 22 deg) is higher than the stall (0.860 at 9.5 deg) but falls
    only 0.011 behind it, the stall 0.116: the window ends at 9.75 deg, the start is 9.5 deg and the
    second sweep runs at the speed 0.860 implies."""
    request, boundary, swept = install(monkeypatch, lambda _v: PLATEAU, (speed_for(0.86), 9.5))
    outcome = opti_module.stall_worker(request)
    (problem,) = boundary.problems
    alpha = problem.variables["alpha"]
    assert (alpha["upper_bound"], alpha["init_guess"]) == (9.75, 9.5)
    assert math.isclose(swept[1], speed_for(0.86), rel_tol=1e-12)
    assert math.isclose(outcome.value.cl_max, 0.86, abs_tol=1e-12)


async def test_the_stall_is_bracketed_at_the_lower_maximum_before_the_real_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The front hump (1.447 at 7.25 deg) is higher, but the curve recovers behind it; the stall is
    1.420 at 13 deg, where it falls 0.42: the window ends at 13.25 deg, the start is 13 deg and the
    second sweep runs at the speed 1.420 implies."""
    request, boundary, swept = install(monkeypatch, lambda _v: HUMP, (speed_for(1.42), 13.0))
    outcome = opti_module.stall_worker(request)
    (problem,) = boundary.problems
    alpha = problem.variables["alpha"]
    assert (alpha["upper_bound"], alpha["init_guess"]) == (13.25, 13.0)
    assert math.isclose(swept[1], speed_for(1.42), rel_tol=1e-12)
    assert math.isclose(outcome.value.cl_max, 1.42, abs_tol=1e-12)
