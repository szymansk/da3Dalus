"""The masses that had no stall speed have one at the main C_L maximum (gh-1423, aero tier).

Real AeroSandbox and IPOPT through the public compute(), sea level. With the stall at the *first* C_L
peak a band of masses had no stall speed on AVISTAR_ELITE (8.50 to 9.44 kg), AERONCA_CHAMP (about
0.365 to 0.384 kg, and its nominal 0.39 kg did not converge) and CHEKKER (about 0.295 to 0.336 kg):
an early shoulder of the lift curve exists only in a range of Reynolds numbers, so the first peak
jumped with the speed. The stall is at the main maximum (maintainer 2026-11-27): the local maximum
above alpha = 0 with the largest fall behind it.

Each value is checked twice. Against an independent brute force made in this file (its own
AeroBuildup call and its own search for that maximum, no kernel function): the lift
balance closes at that maximum. And against pinned numbers, which are **regression, not validation**
(aero_kernel/CLAUDE.md): what this build computes (NeuralFoil xlarge, 0.25 deg sweep); they agree
to 2e-8 with a root search over the speed made for gh-1423 with the same brute force.
"""

from typing import Any

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import QuantityResult, QuantityStatus
from aero_kernel.solvers.asb_airplane import load_aerosandbox, to_asb_airplane
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, aircraft_input, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

REL = 2e-3  # the regression tolerance of the fleet tests
SLUGS = ("stall-speed", "max-lift-coefficient", "angle-of-attack-stall", "approach-speed")
GRAVITY = 9.80665  # the kernel's default
RHO_SEA_LEVEL = 1.2249991558877122  # the kernel's ISA density at 0 m
SWEEP_DEG = [-15.0 + 0.25 * k for k in range(161)]

# (member, mass in kg, V_S in m/s, C_L,max, alpha_S in deg). Under the first-peak rule: the Avistar
# masses 8.75 to 9.4 kg had no value and 8.5 kg stalled on the shoulder (17.28 m/s, C_L 1.211 at
# 8 deg); AERONCA_CHAMP 0.37 kg had no value, 0.39 kg (nominal) was `not_converged`; CHEKKER 0.30 and
# 0.32 kg had no value.
FORMER_BAND = [
    (FleetMember.AVISTAR_ELITE, 8.5, 16.39732, 1.34449, 16.435),
    (FleetMember.AVISTAR_ELITE, 9.0, 16.88023, 1.34329, 16.473),
    (FleetMember.AVISTAR_ELITE, 9.4, 17.25694, 1.34241, 16.498),
    (FleetMember.AVISTAR_ELITE, 9.6, 17.44226, 1.34199, 16.509),
    (FleetMember.AERONCA_CHAMP, 0.37, 5.87202, 1.32692, 18.326),
    (FleetMember.AERONCA_CHAMP, 0.39, 6.02620, 1.32799, 18.253),
    (FleetMember.CHEKKER, 0.30, 5.21088, 1.30128, 14.693),
    (FleetMember.CHEKKER, 0.32, 5.37373, 1.30518, 14.657),
    (FleetMember.CHEKKER, 0.345, 5.57032, 1.30958, 14.616),
]


async def stall(member: FleetMember, mass_kg: float) -> dict[str, QuantityResult]:
    """The stall quantities and the approach speed (which reads the landing stall speed) at a mass."""
    values = {"altitude": 0.0, "aircraft-mass": mass_kg}
    result = await compute(aircraft_input(member, values), request(*SLUGS))
    return {q.slug: q for q in result.quantities}


def number(quantity: QuantityResult) -> float:
    assert quantity.status is QuantityStatus.OK, (quantity.slug, quantity.error)
    assert quantity.value is not None
    return quantity.value


def main_maximum(member: FleetMember, speed: float) -> tuple[float, float, float]:
    """Brute force, independent of the kernel's search: ``(alpha, C_L, S_ref)`` at ``speed``.

    One AeroBuildup run over the 0.25 deg sweep at sea level (AeroSandbox's own ISA atmosphere, not
    the kernel's air state). Above alpha = 0 (index 60) every sample not lower than its predecessor
    and higher than its successor is a local maximum. Its fall is its C_L minus the lowest C_L
    behind it before the curve has climbed back by more than half of the fall so far (or up to the
    end of the sweep). The local maximum with the largest fall is the main maximum.
    """
    asb: Any = load_aerosandbox()
    airplane = to_asb_airplane(AirplaneGeometry.model_validate(reference_document(member)))
    point = asb.OperatingPoint(
        atmosphere=asb.Atmosphere(altitude=0.0), velocity=speed, alpha=asb.numpy.array(SWEEP_DEG)
    )
    cl = [float(v) for v in asb.AeroBuildup(airplane, point, model_size="xlarge").run()["CL"]]
    falls: dict[int, float] = {}
    for k in range(61, 160):
        if not (cl[k] >= cl[k - 1] and cl[k] > cl[k + 1]):
            continue
        low = cl[k]
        for j in range(k + 1, 161):
            low = min(low, cl[j])
            if cl[j] - low > 0.5 * (cl[k] - low):
                break
        falls[k] = cl[k] - low
    assert falls
    best = max(falls, key=lambda k: (falls[k], -k))
    return SWEEP_DEG[best], cl[best], float(airplane.s_ref)


@pytest.mark.parametrize(
    ("member", "mass_kg", "v_s", "cl_max", "alpha_s"),
    FORMER_BAND,
    ids=lambda v: getattr(v, "name", str(v)),
)
async def test_a_mass_of_the_former_band_stalls_at_the_main_maximum(
    member: FleetMember, mass_kg: float, v_s: float, cl_max: float, alpha_s: float
) -> None:
    """The kernel's C_L,max is the main maximum of the brute-force sweep at the kernel's V_S
    (the optimum is refined between the 0.25 deg samples, so it may exceed the highest sample by a
    little, never fall short of it), its angle lies within one sweep step of that sample, and the
    lift balance closes there: 0.5 rho V_S^2 S_ref C_L,max = m g."""
    got = await stall(member, mass_kg)
    speed, lift_coefficient = number(got["stall-speed"]), number(got["max-lift-coefficient"])
    angle = number(got["angle-of-attack-stall"])
    assert got["approach-speed"].status is QuantityStatus.OK
    peak_alpha, peak_cl, area = main_maximum(member, speed)
    assert -1e-6 <= lift_coefficient - peak_cl <= 1e-3
    assert abs(angle - peak_alpha) <= 0.25
    lift = 0.5 * RHO_SEA_LEVEL * speed * speed * area * lift_coefficient
    assert close(lift, mass_kg * GRAVITY, 1e-6)
    assert close(speed, v_s, REL)
    assert close(lift_coefficient, cl_max, REL)
    assert close(angle, alpha_s, REL)


async def test_the_stall_speed_rises_with_the_mass_across_the_former_band_of_the_avistar() -> None:
    """One stall speed per mass, rising with it, and no jump of C_L,max: 16.397, 16.880, 17.257 and
    17.442 m/s at 8.5, 9.0, 9.4 and 9.6 kg, C_L,max between 1.3420 and 1.3445. (Under the first-peak
    rule 8.7 kg gave 17.48 m/s and 9.5 kg gave 17.35 m/s: a higher mass, a lower stall speed.)"""
    masses = (8.5, 9.0, 9.4, 9.6)
    results = [await stall(FleetMember.AVISTAR_ELITE, mass) for mass in masses]
    speeds = [number(r["stall-speed"]) for r in results]
    coefficients = [number(r["max-lift-coefficient"]) for r in results]
    assert speeds == sorted(speeds)
    assert len(set(speeds)) == len(speeds)
    assert max(coefficients) - min(coefficients) < 5e-3
