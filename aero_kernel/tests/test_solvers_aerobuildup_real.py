"""The AeroBuildup adapter against real AeroSandbox, in the process pool (aero tier)."""

import math
from typing import Any

import pytest
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.aerobuildup import AeroBuildupAdapter
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.tests.test_solvers_aerobuildup import airplane

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

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
async def test_the_sweep_equals_asbs_own_aerobuildup_in_the_same_air(altitude: float) -> None:
    """The fixed atmosphere object reproduces asb.Atmosphere in everything AeroBuildup asks."""
    import numpy as np

    asb = load_aerosandbox()
    atmosphere, air = isa_air(altitude)
    async with SolverRuntime(max_workers=1) as runtime:
        sweep = await AeroBuildupAdapter(runtime).sweep(airplane(), 12.0, ALPHAS, air)
    reference: dict[str, Any] = asb.AeroBuildup(
        to_asb_airplane(airplane()),
        asb.OperatingPoint(
            atmosphere=atmosphere,
            velocity=np.full(len(ALPHAS), 12.0),
            alpha=np.array(ALPHAS),
        ),
    ).run()
    for ours, key in ((sweep.polar.cl, "CL"), (sweep.polar.cd, "CD"), (sweep.polar.cm, "Cm")):
        assert all(
            math.isclose(a, float(b), rel_tol=1e-9, abs_tol=1e-12)
            for a, b in zip(ours, reference[key], strict=True)
        ), key
    assert sweep.polar.alpha_deg == ALPHAS


async def test_the_lift_curve_rises_with_alpha_for_a_cambered_wing() -> None:
    _, air = isa_air(0.0)
    async with SolverRuntime(max_workers=1) as runtime:
        sweep = await AeroBuildupAdapter(runtime).sweep(airplane(), 12.0, ALPHAS, air)
    assert sweep.polar.cl[0] < sweep.polar.cl[len(ALPHAS) // 2] < sweep.polar.cl[-3]
