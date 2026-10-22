"""stall-speed of BRYAN and JAGUAR through the public compute(), real AeroSandbox and IPOPT.

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they
pin what this build computes (recorded at the commit that introduced them) so that a change of
code or of AeroSandbox is noticed; they are not measurements of the aircraft.
"""

import importlib.metadata

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


async def stall_result(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    return await compute(aircraft, request(*SLUGS))


async def stall(member: FleetMember) -> dict[str, QuantityResult]:
    return {q.slug: q for q in (await stall_result(member)).quantities}


def assert_goldens_are_pinned_to_their_tools(result: ComputeResult) -> None:
    """The goldens hold for these tool versions and this NeuralFoil model size only."""
    assert result.provenance.tool_versions == {
        "aerosandbox": importlib.metadata.version("aerosandbox"),
        "neuralfoil": importlib.metadata.version("neuralfoil"),
    }
    assert result.provenance.solver_settings == {"neuralfoil_model_size": "small"}


async def test_bryan_stalls_where_the_prototype_found_it() -> None:
    """Prototype (bryan/ERGEBNISSE_STABILITAET.md, 151 g): V_S = 5.29 m/s.

    Computed 5.2894 m/s, 0.01 % below the table's two decimals. The prototype took S from AeroSandbox's
    own planform area (7.0 dm2); the kernel passes its projected S_ref (6.99 dm2) to AeroBuildup, so
    C_L,max differs a little (1.237 at 11.2 deg here) while V_S, which fixes S * C_L, agrees.
    """
    result = await stall_result(FleetMember.BRYAN)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    clean = quantities["stall-speed"]
    assert clean.status is QuantityStatus.OK
    assert close(clean.value, BRYAN_V_S, 1e-5)  # regression
    assert close(clean.value, 5.29, 2e-3)  # the prototype's two decimals
    assert {"reynolds_outside_band", "reynolds_bubble_sensitive"} <= {
        w.code for w in clean.warnings
    }  # ADR 0028: the tip chord of 1 cm and the root chord of 15 cm span the band
    outside = {str(w.detail["wing"]) for w in clean.warnings if w.code == "reynolds_outside_band"}
    assert {"Seitenleitwerk", "Hoehenleitwerk"} <= outside  # the surface that is out is named
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == clean.value  # no flaps: the same airplane, not a fallback


async def test_bryans_inverted_stall_gives_no_value_because_the_trough_vanishes_with_the_speed() -> (
    None
):
    """At the first estimate's speed (5.88 m/s) the sweep has a trough at -10.5 deg; at the speed
    the second sweep uses (8.32 m/s, higher Re) it has none: C_L falls monotonically down to the
    sweep's lower end (-15 deg, C_L -0.55). The trough is present at the lower Reynolds number of
    the first sweep, so the bracket finds no extremum and the kernel returns no value (ADR 0020)
    instead of a boundary sample."""
    inverted = (await stall(FleetMember.BRYAN))["inverted-max-lift-coefficient"]
    assert inverted.status is QuantityStatus.ERROR
    assert inverted.value is None
    assert inverted.error is not None
    assert inverted.error.code == "not_converged"
    assert "no trough" in inverted.error.message


async def test_bryans_inverted_trough_exists_only_at_the_low_speed_of_the_first_sweep() -> None:
    from aero_kernel.geometry import AirplaneGeometry
    from aero_kernel.solvers.aerobuildup import sweep_polar
    from aero_kernel.solvers.air import AirState
    from aero_kernel.solvers.asb_airplane import to_asb_airplane
    from aero_kernel.solvers.opti import ALPHA_MAX_DEG, ALPHA_MIN_DEG, ALPHA_STEP_DEG
    from aero_kernel.solvers.stall_math import first_extremum_from_zero

    air = AirState(
        density=1.2249991559, dynamic_viscosity=1.789380278e-05, speed_of_sound=340.2941078
    )
    airplane = to_asb_airplane(
        AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN))
    )
    count = round((ALPHA_MAX_DEG - ALPHA_MIN_DEG) / ALPHA_STEP_DEG)
    grid = [ALPHA_MIN_DEG + k * ALPHA_STEP_DEG for k in range(count + 1)]
    slow = sweep_polar(airplane, air, 5.88, grid, "small")
    fast = sweep_polar(airplane, air, 8.32, grid, "small")
    index = first_extremum_from_zero(slow.alpha_deg, slow.cl, upright=False)
    assert index is not None
    assert slow.alpha_deg[index] == -10.5
    assert first_extremum_from_zero(fast.alpha_deg, fast.cl, upright=False) is None


async def test_jaguar_regression_goldens() -> None:
    result = await stall_result(FleetMember.JAGUAR)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), quantities
    assert close(quantities["stall-speed"].value, JAGUAR_V_S, 1e-5)
    assert close(quantities["max-lift-coefficient"].value, JAGUAR_CL_MAX, 1e-5)
    assert close(quantities["angle-of-attack-stall"].value, JAGUAR_ALPHA_S, 1e-5)
    assert close(quantities["inverted-max-lift-coefficient"].value, JAGUAR_CL_MIN, 1e-5)
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == quantities["stall-speed"].value
