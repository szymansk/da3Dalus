"""stall-wing-loading-limit: (W/S)_max = 1/2 rho V_S,target^2 C_L,max, as a formula and through the
engine (application ``at_stall_speed_target``, given ``stall-speed-target``).

Fast tier: hand-computed values; the engine run uses the stub ATM adapter and the stub optimiser.
"""

import pytest
from aero_kernel import compute
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.formulas.stall_wing_loading_limit import stall_wing_loading_limit
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityStatus,
    ReasonCode,
)
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
    solvers_with,
)
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, StubOpti
from aero_kernel.tests.test_stall_speed_engine import document

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
QUANTITY = "wing-loading-limit-stall"
ALTITUDE_M = 500.0
RHO_500 = 1.167268  # ISA at 500 m (hand value of test_formulas_end_to_end)
TARGET = 9.0


async def test_the_limit_is_half_rho_v_squared_cl_max() -> None:
    """Hand value: 0.5 * 1.2 kg/m^3 * (8 m/s)^2 * 1.1 = 42.24 N/m^2."""
    x = inputs_from_model(
        MODEL,
        "stall-wing-loading-limit",
        {"air-density": 1.2, "stall-speed-target": 8.0, "max-lift-coefficient": 1.1},
        application="at_stall_speed_target",
    )
    result = await stall_wing_loading_limit(x, context_with(StubAtmosphere({})))
    assert set(result) == {"ws_max_stall"}
    assert close(result["ws_max_stall"], 42.24, 1e-12)


async def run(values: dict[str, float]) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": document(),
            "values": {"aircraft-mass": 1.5, "altitude": ALTITUDE_M, **values},
        }
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({ALTITUDE_M: RHO_500}), opti=StubOpti())
    request = ComputeRequest(quantities=(QUANTITY,))
    return await evaluate(shipped_build(), aircraft, request, solvers=solvers)


async def test_with_a_stall_speed_target_the_limit_uses_the_density_at_the_set_altitude() -> None:
    """rho is air-density-isa at 500 m, never sea level; C_L,max is the stall optimum's."""
    result = await run({"stall-speed-target": TARGET})
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK, result
    assert close(only.value, 0.5 * RHO_500 * TARGET**2 * UPRIGHT_PEAK[1], 1e-12)
    assert (only.unit, only.tool, only.application) == ("N/m^2", "APP", "at_stall_speed_target")


async def test_without_a_stall_speed_target_the_limit_is_not_given() -> None:
    result = await run({})
    (only,) = result.quantities
    assert only.status is QuantityStatus.NOT_APPLICABLE
    assert only.reason is not None
    assert only.reason.code is ReasonCode.NOT_GIVEN


@pytest.mark.aero
async def test_bryans_limit_through_the_public_compute_closes_on_its_own_inputs() -> None:
    """BRYAN at 500 m with V_S,target = 6 m/s, real ATM and stall optimum: the limit equals
    1/2 rho V^2 C_L,max of the density and C_L,max of the same result (one producer each)."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.BRYAN),
            "values": {
                "aircraft-mass": FleetMember.BRYAN.mass_kg,
                "altitude": ALTITUDE_M,
                "stall-speed-target": 6.0,
            },
        }
    )
    slugs = (QUANTITY, "air-density", "max-lift-coefficient")
    result = await compute(aircraft, ComputeRequest(quantities=slugs))
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    rho = quantities["air-density"].value
    cl_max = quantities["max-lift-coefficient"].value
    assert rho is not None
    assert cl_max is not None
    assert close(rho, RHO_500, 5e-4)
    assert close(quantities[QUANTITY].value, 0.5 * rho * 6.0**2 * cl_max, 1e-12)
