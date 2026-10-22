"""stall-speed of BRYAN and JAGUAR through the public compute(), real AeroSandbox and IPOPT.

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they
pin what this build computes (recorded at the commit that introduced them) so that a change of
code or of AeroSandbox is noticed; they are not measurements of the aircraft.
"""

import pytest
from aero_kernel import compute
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = (
    "stall-speed",
    "max-lift-coefficient",
    "angle-of-attack-stall",
    "stall-speed-takeoff",
    "stall-speed-landing",
    "inverted-max-lift-coefficient",
)
# Regression goldens at sea level, mass of the fleet member, ISA, the kernel's projected S_ref.
BRYAN_V_S = 5.2894317  # m/s
JAGUAR_V_S = 6.1679285  # m/s
JAGUAR_CL_MAX, JAGUAR_ALPHA_S = 1.0410012, 9.5515985
JAGUAR_CL_MIN = -0.7870643


async def stall(member: FleetMember) -> dict[str, QuantityResult]:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    result: ComputeResult = await compute(aircraft, request(*SLUGS))
    return {q.slug: q for q in result.quantities}


async def test_bryan_stalls_where_the_prototype_found_it() -> None:
    """Prototype (bryan/ERGEBNISSE_STABILITAET.md, 151 g): V_S = 5.29 m/s.

    Computed 5.2894 m/s, 0.01 % below the table's two decimals. The prototype took S from AeroSandbox's
    own planform area (7.0 dm2); the kernel passes its projected S_ref (6.99 dm2) to AeroBuildup, so
    C_L,max differs a little (1.237 at 11.2 deg here) while V_S, which fixes S * C_L, agrees.
    """
    quantities = await stall(FleetMember.BRYAN)
    clean = quantities["stall-speed"]
    assert clean.status is QuantityStatus.OK
    assert close(clean.value, BRYAN_V_S, 1e-5)  # regression
    assert close(clean.value, 5.29, 2e-3)  # the prototype's two decimals
    assert {"reynolds_outside_band", "reynolds_bubble_sensitive"} <= {
        w.code for w in clean.warnings
    }  # ADR 0028: the tip chord of 1 cm and the root chord of 15 cm span the band
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == clean.value  # no flaps: the same airplane, not a fallback


async def test_bryans_inverted_stall_is_outside_the_sweep_and_gives_no_value() -> None:
    """The cambered section stalls inverted beyond -15 deg: the trough would be a boundary sample."""
    inverted = (await stall(FleetMember.BRYAN))["inverted-max-lift-coefficient"]
    assert inverted.status is QuantityStatus.ERROR
    assert inverted.value is None
    assert inverted.error is not None
    assert inverted.error.code == "not_converged"


async def test_jaguar_regression_goldens() -> None:
    quantities = await stall(FleetMember.JAGUAR)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), quantities
    assert close(quantities["stall-speed"].value, JAGUAR_V_S, 1e-5)
    assert close(quantities["max-lift-coefficient"].value, JAGUAR_CL_MAX, 1e-5)
    assert close(quantities["angle-of-attack-stall"].value, JAGUAR_ALPHA_S, 1e-5)
    assert close(quantities["inverted-max-lift-coefficient"].value, JAGUAR_CL_MIN, 1e-5)
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == quantities["stall-speed"].value
