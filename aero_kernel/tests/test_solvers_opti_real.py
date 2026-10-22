"""The stall problem against real AeroSandbox and IPOPT, in the process pool (aero tier).

Golden values are regression, not validation (aero_kernel/CLAUDE.md).
"""

import math
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from aero_kernel.solvers.opti import ALPHA_STEP_DEG, OptiAdapter, StallRequest, StallSolution
from aero_kernel.solvers.stall_math import first_extremum

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

MASS_KG, GRAVITY = 1.5, 9.81


def trainer() -> AirplaneGeometry:
    """The 1.5 kg trainer of the canon entry: NACA 2412, 0.2 m chord, 1.4 m span, no fuselage."""
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y in (0.0, 0.7)
    ]
    wing = {"name": "Main Wing", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate(
        {"name": "rc-trainer", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Main Wing": wing}}
    )


def sea_level() -> AirState:
    asb: Any = load_aerosandbox()
    atmosphere = asb.Atmosphere(altitude=0.0)
    return AirState(
        density=float(atmosphere.density()),
        dynamic_viscosity=float(atmosphere.dynamic_viscosity()),
        speed_of_sound=float(atmosphere.speed_of_sound()),
    )


async def solve(n_load: float, mass: float = MASS_KG) -> StallSolution:
    async with SolverRuntime(max_workers=1) as runtime:
        stall = await OptiAdapter(runtime).stall(trainer(), mass, GRAVITY, n_load, sea_level())
    return stall.solution


async def test_the_trainer_stalls_where_the_canon_entry_verified_it_with_the_small_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canon entry: optimiser 8.4888 m/s at alpha 15.8 deg, C_L 1.191 (1.5 kg, NACA 2412, 1.4 m
    span). That was computed with AeroSandbox's default NeuralFoil model, "small", so the worker is
    run in this process with that size. Regression golden, relative tolerance 2e-3 (the entry
    quotes 4-5 digits)."""
    monkeypatch.setattr(opti_module, "NEURALFOIL_MODEL_SIZE", "small")
    request = StallRequest(
        airplane=trainer(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=1.0, air=sea_level()
    )
    solution = opti_module.stall_worker(request).value
    assert math.isclose(solution.v_s, 8.4888, rel_tol=2e-3)
    assert math.isclose(solution.alpha_s, 15.8, abs_tol=0.3)
    assert math.isclose(solution.cl_max, 1.191, rel_tol=2e-3)


async def test_the_trainer_with_the_xlarge_model_regression() -> None:
    """The size the kernel uses (maintainer 2026-10-22): 8.3855 m/s at 15.3 deg, C_L 1.220, 2.1 %
    below the small model's value that the canon entry quotes. Regression, not validation."""
    solution = await solve(1.0)
    assert math.isclose(solution.v_s, 8.38546, rel_tol=1e-4)
    assert math.isclose(solution.alpha_s, 15.3226, abs_tol=0.01)
    assert math.isclose(solution.cl_max, 1.22023, rel_tol=1e-4)


async def test_the_lift_balance_holds_at_the_optimum() -> None:
    """V_S = sqrt(2 n m g / (rho S C_L)) with the C_L of the polar at alpha_S (the Probe)."""
    solution = await solve(1.0)
    air = sea_level()
    reference_area = 0.28  # 2 * 0.7 m * 0.2 m, projected
    probe = math.sqrt(2.0 * MASS_KG * GRAVITY / (air.density * reference_area * solution.cl_max))
    assert math.isclose(solution.v_s, probe, rel_tol=1e-6)


async def test_the_polar_contains_alpha_s_and_the_optimum_is_the_first_peak() -> None:
    solution = await solve(1.0)
    polar = solution.polar
    assert solution.alpha_s in polar.alpha_deg
    assert polar.cl[polar.alpha_deg.index(solution.alpha_s)] == solution.cl_max
    peak = first_extremum(list(polar.cl[polar.alpha_deg.index(0.0) :]), maximum=True)
    assert peak is not None
    sampled_peak_alpha = polar.alpha_deg[polar.alpha_deg.index(0.0) + peak]
    assert abs(sampled_peak_alpha - solution.alpha_s) <= ALPHA_STEP_DEG + 1e-9
    assert polar.alpha_deg[-1] - solution.alpha_s > 3.0  # the sweep runs past the peak
    assert (polar.alpha_deg[0], polar.alpha_deg[-1]) == (-15.0, 25.0)
    steps = {round(b - a, 9) for a, b in pairwise(polar.alpha_deg)}
    assert max(steps) == ALPHA_STEP_DEG  # alpha_S splits one step, never widens one
    assert len(polar.alpha_deg) in (161, 162)


async def test_two_g_stalls_faster_by_sqrt_two() -> None:
    one, two = await solve(1.0), await solve(2.0)
    assert math.isclose(
        two.v_s / one.v_s, math.sqrt(2.0), rel_tol=0.03
    )  # Re changes C_L,max a little


async def test_inverted_flight_finds_the_negative_lift_coefficient() -> None:
    solution = await solve(-1.0)
    assert solution.cl_max < 0.0
    assert solution.alpha_s < 0.0
    assert solution.v_s > 0.0
    polar = solution.polar
    assert polar.alpha_deg[0] < solution.alpha_s < polar.alpha_deg[-1]


async def test_an_airplane_too_heavy_for_the_speed_range_is_not_converged() -> None:
    with pytest.raises(FormulaError) as raised:
        await solve(1.0, mass=5000.0)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
