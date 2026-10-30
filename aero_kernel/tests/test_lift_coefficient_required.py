"""lift-coefficient-required: C_L,req = n m g / (q S_ref), as a formula and through the engine.

Fast tier: hand-computed values; the engine run uses the stub ATM and GEO adapters.
"""

import pytest
from aero_kernel import compute
from aero_kernel.build import shipped_build
from aero_kernel.context import Value
from aero_kernel.engine import evaluate
from aero_kernel.formulas.lift_coefficient_required import lift_coefficient_required
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeRequest, QuantityStatus
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
    solvers_with,
)
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_stall_speed_engine import document

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
SLUG = "lift-coefficient-required"
RHO = 1.225
MASS = 1.5
SPEED = 10.0


def inputs(n_load: float) -> dict[str, Value]:
    """The formula's ``x`` for m = 1.5 kg, q = 60 Pa, S_ref = 0.28 m^2 at load factor ``n_load``."""
    return inputs_from_model(
        MODEL,
        SLUG,
        {
            "aircraft-mass": MASS,
            "gravity": 9.80665,
            "load-factor": n_load,
            "dynamic-pressure": 60.0,
            "wing-reference-area": 0.28,
        },
    )


async def test_level_flight_lift_coefficient_is_weight_over_q_s() -> None:
    """Hand value: C_L = 1 * 1.5 * 9.80665 / (60 * 0.28) = 14.709975 / 16.8 = 0.87559375."""
    result = await lift_coefficient_required(inputs(1.0), context_with(StubAtmosphere({})))
    assert set(result) == {"cl_req"}
    assert close(result["cl_req"], 0.87559375, 1e-12)


async def test_the_load_factor_scales_the_demanded_lift_coefficient() -> None:
    """Hand value: at n = 2.5 the demand is 2.5 * 0.87559375 = 2.188984375."""
    result = await lift_coefficient_required(inputs(2.5), context_with(StubAtmosphere({})))
    assert close(result["cl_req"], 2.188984375, 1e-12)


async def test_the_lift_coefficient_through_the_engine_uses_the_default_load_factor() -> None:
    """q = 0.5 * 1.225 * 10^2 = 61.25 Pa; S_ref from the stand-in GEO adapter; n = 1 (default)."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": document(),
            "values": {"aircraft-mass": MASS, "altitude": 0.0, "flight-speed": SPEED},
        }
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}))
    request = ComputeRequest(quantities=("lift-coefficient",))
    result = await evaluate(shipped_build(), aircraft, request, solvers=solvers)
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK, result
    s_ref = stand_in_main_wing_properties(AirplaneGeometry.model_validate(document())).s_ref
    expected = MASS * 9.80665 / (0.5 * RHO * SPEED**2 * s_ref)
    assert close(only.value, expected, 1e-12)
    assert (only.unit, only.tool) == ("1", "APP")
    assert {d.slug for d in result.provenance.defaults_used} == {"gravity", "load-factor"}


@pytest.mark.aero
async def test_bryans_lift_coefficient_through_the_public_compute() -> None:
    """BRYAN at sea level, 8 m/s, real ATM and GEO: C_L = m g / (q S_ref) of the same result."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.BRYAN),
            "values": {
                "aircraft-mass": FleetMember.BRYAN.mass_kg,
                "altitude": 0.0,
                "flight-speed": 8.0,
            },
        }
    )
    slugs = ("lift-coefficient", "dynamic-pressure", "wing-reference-area", "weight")
    result = await compute(aircraft, ComputeRequest(quantities=slugs))
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    weight = quantities["weight"].value
    q = quantities["dynamic-pressure"].value
    s_ref = quantities["wing-reference-area"].value
    assert weight is not None
    assert q is not None
    assert s_ref is not None
    assert close(quantities["lift-coefficient"].value, weight / (q * s_ref), 1e-12)
