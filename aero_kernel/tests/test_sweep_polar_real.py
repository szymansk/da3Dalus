"""``sweep_polar`` and the fixed atmosphere against real AeroSandbox (aero tier)."""

import math
from typing import Any

import numpy as np
import pytest
from aero_kernel.solvers.aerobuildup import sweep_polar
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.tests.solver_builders import airplane

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
    """The fixed atmosphere object reproduces asb.Atmosphere in everything AeroBuildup asks."""
    asb = load_aerosandbox()
    atmosphere, air = isa_air(altitude)
    converted = to_asb_airplane(airplane())
    polar = sweep_polar(converted, air, 12.0, ALPHAS)
    reference: dict[str, Any] = asb.AeroBuildup(
        converted,
        asb.OperatingPoint(
            atmosphere=atmosphere, velocity=np.full(len(ALPHAS), 12.0), alpha=np.array(ALPHAS)
        ),
    ).run()
    for ours, key in ((polar.cl, "CL"), (polar.cd, "CD"), (polar.cm, "Cm")):
        assert all(
            math.isclose(a, float(b), rel_tol=1e-9, abs_tol=1e-12)
            for a, b in zip(ours, reference[key], strict=True)
        ), key
    assert polar.alpha_deg == ALPHAS


def test_the_lift_curve_rises_with_alpha_for_a_cambered_wing() -> None:
    _, air = isa_air(0.0)
    polar = sweep_polar(to_asb_airplane(airplane()), air, 12.0, ALPHAS)
    assert polar.cl[0] < polar.cl[len(ALPHAS) // 2] < polar.cl[-3]
