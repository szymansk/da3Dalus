"""speed-from-stall-margin through the engine on the shipped canon, with a stub optimiser."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.devices import FLAP_ROLES
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import ComputeRequest, QuantityStatus
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import OptiAdapter, Stall, StallRequest, StallSolution
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.solver_builders import InProcessRuntime
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, StubOpti, lift_curve
from aero_kernel.tests.test_stall_speed_engine import (
    RHO,
    V_CLEAN,
    aircraft,
    by_slug,
    flap_aware_stall,
    run,
)

pytestmark = pytest.mark.asyncio


def flap_deflection(airplane: AirplaneGeometry) -> float:
    """The deflection of the first flap device of the main wing."""
    for section in (airplane.wings or {})["Main"].x_secs:
        device = section.trailing_edge_device
        if device is not None and device.role in FLAP_ROLES:
            return device.deflection_deg or 0.0
    return 0.0


class FlapAwareOpti(StubOpti):
    """A stub whose C_L,max rises with the flap deflection so that V_S falls by 1 % per degree:
    the configuration of each call shows in the value, and the answer stays self-consistent."""

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        factor = 1.0 - flap_deflection(airplane) / 100.0
        alpha_s, cl_clean = UPRIGHT_PEAK
        cl_max = cl_clean / factor**2
        area = stand_in_main_wing_properties(airplane).s_ref
        v_s = math.sqrt(2.0 * n_load * mass_kg * gravity / (air.density * area * cl_max))
        polar = lift_curve((alpha_s, cl_max), upright=True)
        solution = StallSolution(v_s=v_s, cl_max=cl_max, alpha_s=alpha_s, polar=polar)
        return Stall(solution=solution, warnings=())


async def test_approach_speed_is_margin_times_landing_stall_speed() -> None:
    """Hand value: V_app = 1.3 * V_S,landing; no flaps, so V_S,landing is the clean V_S."""
    result, _ = await run("approach-speed", values={"approach-speed-margin-target": 1.3})
    (approach,) = result.quantities
    assert approach.status is QuantityStatus.OK
    assert close(approach.value, 1.3 * V_CLEAN, 1e-12)
    assert (approach.unit, approach.tool, approach.application) == ("m/s", "APP", "approach")


async def test_touchdown_and_takeoff_bind_their_own_margin_and_configuration() -> None:
    values = {
        "flap-deflection-landing": 30.0,
        "flap-deflection-takeoff": 10.0,
        "touchdown-speed-margin-target": 1.2,
        "takeoff-speed-margin-target": 1.15,
        "approach-speed-margin-target": 1.3,
    }
    result, _ = await run(
        "approach-speed",
        "touchdown-speed",
        "takeoff-speed",
        stub=FlapAwareOpti(),
        flap=True,
        values=values,
    )
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert close(quantities["approach-speed"].value, 1.3 * 0.70 * V_CLEAN, 1e-12)
    assert close(quantities["touchdown-speed"].value, 1.2 * 0.70 * V_CLEAN, 1e-12)
    assert close(quantities["takeoff-speed"].value, 1.15 * 0.90 * V_CLEAN, 1e-12)
    assert quantities["touchdown-speed"].application == "touchdown"
    assert quantities["takeoff-speed"].application == "takeoff"


async def test_default_margin_is_declared_default_target_used() -> None:
    """Q31: the 1.3 comes from defaults.yaml and is declared on the result."""
    result, _ = await run("approach-speed")
    (approach,) = result.quantities
    assert approach.status is QuantityStatus.OK
    assert close(approach.value, 1.3 * V_CLEAN, 1e-12)
    (warning,) = [w for w in approach.warnings if w.code == "default_target_used"]
    assert warning.origin == "approach-speed-margin-target"
    assert "approach-speed-margin-target" in [d.slug for d in result.provenance.defaults_used]


async def test_flapped_aircraft_without_a_landing_deflection_is_upstream_failed() -> None:
    """Q33: with flaps and no flap-deflection-landing the landing stall speed is missing input,
    and the approach speed inherits it as upstream_failed."""
    result, _ = await run("approach-speed", flap=True)
    (approach,) = result.quantities
    assert approach.status is QuantityStatus.ERROR
    assert approach.error is not None
    assert approach.error.category is ErrorCategory.UPSTREAM_FAILED


async def test_flapped_aircraft_approach_speed_is_computed_with_the_landing_flap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real adapter is given the flapped landing airplane: the approach speed is the margin
    times the flapped landing stall speed, never the clean speed times the margin."""
    adapter = OptiAdapter(InProcessRuntime())
    seen: list[AirplaneGeometry] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        seen.append(request.airplane)
        return WorkerOutcome(
            value=flap_aware_stall(request), diagnostics=WorkerDiagnostics(duration_s=0.0)
        )

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=adapter)
    result = await evaluate(
        shipped_build(),
        aircraft(True, **{"flap-deflection-landing": 30.0, "approach-speed-margin-target": 1.3}),
        ComputeRequest(quantities=("approach-speed",)),
        solvers=solvers,
    )
    (approach,) = result.quantities
    assert approach.status is QuantityStatus.OK
    assert [flap_deflection(a) for a in seen] == [30.0]
    assert close(approach.value, 1.3 * V_CLEAN / math.sqrt(1.3), 1e-9)
    assert not close(approach.value, 1.3 * V_CLEAN, 1e-3)
