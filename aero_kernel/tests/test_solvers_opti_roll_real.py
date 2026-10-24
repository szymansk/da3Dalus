"""The steady roll against real AeroSandbox and IPOPT, in the process pool (aero tier).

Golden values of the reference fleet are in ``test_roll_rate_fleet.py``; this module tests the
physics of the problem on a small airplane (regression, not validation).
"""

import math
from typing import Any

import numpy as np
import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.solvers.opti import OptiAdapter, SteadyRoll
from aero_kernel.solvers.roll_math import body_rates, control_effectiveness
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

MASS_KG, GRAVITY, SPEED = 1.5, 9.81, 11.0


def aileron_trainer() -> AirplaneGeometry:
    """A 1.4 m span, 0.2 m chord wing with an aileron (hinge 0.75) on the outer panel."""
    sections: list[dict[str, Any]] = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for y in (0.0, 0.4, 0.7)
    ]
    sections[1]["trailing_edge_device"] = {
        "name": "aileron",
        "role": "aileron",
        "rel_chord_root": 0.75,
        "rel_chord_tip": 0.75,
    }
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate(
        {"name": "trainer", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Main": wing}}
    )


def sea_level() -> AirState:
    asb: Any = load_aerosandbox()
    atmosphere = asb.Atmosphere(altitude=0.0)
    return AirState(
        density=float(atmosphere.density()),
        dynamic_viscosity=float(atmosphere.dynamic_viscosity()),
        speed_of_sound=float(atmosphere.speed_of_sound()),
    )


async def roll(delta: float) -> SteadyRoll:
    async with SolverRuntime(max_workers=1) as runtime:
        return await OptiAdapter(runtime).steady_roll(
            aileron_trainer(), MASS_KG, GRAVITY, sea_level(), SPEED, delta
        )


def residuals(found: SteadyRoll, delta: float) -> tuple[float, float]:
    """Lift minus weight in N and the stability-axis rolling-moment coefficient at the solution."""
    asb: Any = load_aerosandbox()
    airplane = to_asb_airplane(aileron_trainer(), delta)
    p_body, r_body = body_rates(found.p_rad_s, found.alpha_deg, asb.numpy)
    result = asb.AeroBuildup(
        airplane,
        asb.OperatingPoint(
            atmosphere=FixedAtmosphere(sea_level()),
            velocity=SPEED,
            alpha=found.alpha_deg,
            p=p_body,
            r=r_body,
        ),
        model_size="xlarge",
    ).run()
    alpha = math.radians(found.alpha_deg)
    cl, cn, lift = (float(np.ravel(result[key])[0]) for key in ("Cl", "Cn", "L"))
    return lift - MASS_KG * GRAVITY, cl * math.cos(alpha) + cn * math.sin(alpha)


async def test_a_positive_command_rolls_right_and_the_solution_is_an_equilibrium() -> None:
    found = await roll(20.0)
    assert found.p_rad_s > 0.0
    lift_error, moment = residuals(found, 20.0)
    assert abs(lift_error) < 1e-6 * MASS_KG * GRAVITY
    assert abs(moment) < 1e-7
    codes = [w.code for w in found.warnings]
    assert "control_surface_fit_range_unknown" in codes
    (fit,) = [w for w in found.warnings if w.code == "control_surface_fit_range_unknown"]
    assert 0.0 < float(fit.detail["min_confidence"]) <= 1.0  # pyright: ignore[reportArgumentType]
    assert float(fit.detail["max_effective_alpha_deg"]) > found.alpha_deg  # pyright: ignore[reportArgumentType]


async def test_the_negative_command_gives_the_mirrored_roll() -> None:
    plus, minus = await roll(20.0), await roll(-20.0)
    assert math.isclose(minus.p_rad_s, -plus.p_rad_s, abs_tol=1e-6)
    assert math.isclose(minus.alpha_deg, plus.alpha_deg, abs_tol=1e-6)


async def test_steady_roll_zero_delta_gives_zero_p() -> None:
    found = await roll(0.0)
    assert math.isclose(found.p_rad_s, 0.0, abs_tol=1e-9)
    assert [w.code for w in found.warnings] == []


async def test_effective_alpha_shift_matches_asb() -> None:
    """NeuralFoil with a control surface equals NeuralFoil at alpha + tau * delta without one: the
    kernel's one copy of ASB's tau (``aero_buildup.py:784-806``) cannot drift unnoticed. The 360-deg
    blend is off: it uses the unshifted alpha for the post-stall weight, which is no part of tau."""
    asb: Any = load_aerosandbox()
    airfoil = asb.Airfoil("naca2412")
    hinge, delta, alpha = 0.7803, 15.0, 4.0
    surface = asb.ControlSurface(hinge_point=hinge, deflection=delta, symmetric=False)
    with_surface = airfoil.get_aero_from_neuralfoil(
        alpha=alpha,
        Re=1e5,
        model_size="xlarge",
        control_surfaces=[surface],
        include_360_deg_effects=False,
    )
    shifted = airfoil.get_aero_from_neuralfoil(
        alpha=alpha + control_effectiveness(hinge) * delta,
        Re=1e5,
        model_size="xlarge",
        include_360_deg_effects=False,
    )
    assert np.isclose(
        float(np.ravel(with_surface["CL"])[0]), float(np.ravel(shifted["CL"])[0]), rtol=1e-9
    )


async def test_bryan_at_the_approach_speed_and_twenty_degrees_converges_from_its_secant_start() -> (
    None
):
    """BRYAN at V_app 6.819 m/s, 20 deg: IPOPT, started from a fixed fraction (0.1) of the roll-rate
    window, ended in 'Infeasible_Problem_Detected' although the equilibrium exists (a fraction of 0.2
    to 0.5 reaches p = 8.5546 rad/s, p_hat 0.3424, alpha 3.93 deg). The start is the zero of the
    secant of the rolling moment at the weight-carrying alpha."""
    airplane = AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN))
    async with SolverRuntime(max_workers=1) as runtime:
        found = await OptiAdapter(runtime).steady_roll(
            airplane, FleetMember.BRYAN.mass_kg, 9.80665, sea_level(), 6.818986359246604, 20.0
        )
    assert math.isclose(found.p_rad_s, 8.5546408, abs_tol=1e-4)
    assert math.isclose(found.alpha_deg, 3.9310246, abs_tol=1e-3)


async def test_jaguar_at_forty_degrees_fails_loudly_and_never_returns_a_value() -> None:
    """JAGUAR at V_app 8.189 m/s and 40 deg has no solution the solver reaches (measured: the start
    is a secant, the problem stays infeasible): the answer is a declared not_converged error, never a
    value, and the roll-rate quantity becomes an error with the other world's value in the detail."""
    airplane = AirplaneGeometry.model_validate(reference_document(FleetMember.JAGUAR))
    async with SolverRuntime(max_workers=1) as runtime:
        with pytest.raises(FormulaError) as raised:
            await OptiAdapter(runtime).steady_roll(
                airplane, FleetMember.JAGUAR.mass_kg, 9.80665, sea_level(), 8.188976805083124, 40.0
            )
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
