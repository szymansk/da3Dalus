"""``sweep_polar`` and the fixed atmosphere against real AeroSandbox (aero tier)."""

import math
from typing import Any

import numpy as np
import pytest
from aero_kernel.solvers.aerobuildup import kernel_drag, sweep_lift, sweep_polar
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.tests.solver_builders import K_E_D0, airplane

pytestmark = pytest.mark.aero

ALPHAS = tuple(float(a) for a in range(-4, 17, 2))


def isa_air(altitude_m: float) -> tuple[Any, AirState]:
    """ASB's own atmosphere and the same state as an AirState."""
    asb = load_aerosandbox()
    atmosphere = asb.Atmosphere(altitude=altitude_m)
    return atmosphere, AirState(
        density=float(atmosphere.density()),
        dynamic_viscosity=float(atmosphere.dynamic_viscosity()),
        speed_of_sound=float(atmosphere.speed_of_sound()),
    )


@pytest.mark.parametrize("altitude", [0.0, 2000.0])
def test_the_sweep_equals_asbs_own_aerobuildup_in_the_same_air(altitude: float) -> None:
    """The fixed atmosphere object reproduces asb.Atmosphere in everything AeroBuildup asks; C_D is
    the kernel's drag of the same run over q S_ref (#1346)."""
    asb = load_aerosandbox()
    atmosphere, air = isa_air(altitude)
    converted = to_asb_airplane(airplane())
    polar = sweep_polar(converted, air, 12.0, ALPHAS, "small", K_E_D0)
    point = asb.OperatingPoint(
        atmosphere=atmosphere, velocity=np.full(len(ALPHAS), 12.0), alpha=np.array(ALPHAS)
    )
    reference: dict[str, Any] = asb.AeroBuildup(converted, point).run()
    expected_cd = np.asarray(kernel_drag(reference, K_E_D0)) / (
        np.asarray(point.dynamic_pressure()) * converted.s_ref
    )
    for ours, theirs, key in (
        (polar.cl, reference["CL"], "CL"),
        (polar.cd, expected_cd, "CD"),
    ):
        assert all(
            math.isclose(a, float(b), rel_tol=1e-9, abs_tol=1e-12)
            for a, b in zip(ours, theirs, strict=True)
        ), key
    assert polar.alpha_deg == ALPHAS
    assert sweep_lift(converted, air, 12.0, ALPHAS, "small").cl == polar.cl


def test_the_lift_curve_rises_with_alpha_for_a_cambered_wing() -> None:
    _, air = isa_air(0.0)
    polar = sweep_lift(to_asb_airplane(airplane()), air, 12.0, ALPHAS, "small")
    assert polar.cl[0] < polar.cl[len(ALPHAS) // 2] < polar.cl[-3]


def test_the_model_size_is_passed_to_aerobuildup() -> None:
    """A larger NeuralFoil model gives other coefficients: the size reaches AeroBuildup."""
    _, air = isa_air(0.0)
    converted = to_asb_airplane(airplane())
    small = sweep_lift(converted, air, 12.0, ALPHAS, "small")
    large = sweep_lift(converted, air, 12.0, ALPHAS, "xxxlarge")
    assert small.cl != large.cl
