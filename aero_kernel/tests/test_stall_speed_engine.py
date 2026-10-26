"""stall-speed through the engine on the shipped canon, with a stub optimiser (fast tier).

Applications, configured airplanes, Q38, the postconditions and the time budget.
"""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.devices import FLAP_ROLES
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    FlowConditions,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import OptiAdapter, StallRequest, StallSolution
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import OPT_SETTINGS, StubAtmosphere, close, solvers_with
from aero_kernel.tests.solver_builders import InProcessRuntime
from aero_kernel.tests.stall_stubs import (
    INVERTED_TROUGH,
    UPRIGHT_PEAK,
    StubOpti,
    lift_curve,
)

pytestmark = pytest.mark.asyncio

RHO = 1.225
MASS = 1.5


def document(flap: bool = False) -> dict[str, Any]:
    """A 1.4 m span, 0.2 m chord main wing; with a flap device on its first panel if asked."""
    first: dict[str, Any] = {
        "xyz_le": [0.0, 0.0, 0.0],
        "chord": 0.2,
        "twist": 0.0,
        "airfoil": "naca2412",
    }
    if flap:
        first["trailing_edge_device"] = {
            "role": "flap",
            "rel_chord_root": 0.75,
            "rel_chord_tip": 0.75,
            "positive_deflection_deg": 30.0,
        }
    tip = {"xyz_le": [0.0, 0.7, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": [first, tip]}
    return {"name": "t", "wings": {"Main": wing}}


def aircraft(flap: bool = False, **extra: float) -> AircraftInput:
    given = {"aircraft-mass": MASS, "altitude": 0.0, **extra}
    return AircraftInput.model_validate({"airplane": document(flap), "values": given})


async def run(
    *slugs: str,
    stub: StubOpti | None = None,
    flap: bool = False,
    budget: float | None = None,
    values: dict[str, float] | None = None,
) -> tuple[ComputeResult, StubOpti]:
    opti = stub or StubOpti()
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti)
    request = ComputeRequest(quantities=slugs, time_budget_s=budget)
    result = await evaluate(
        shipped_build(), aircraft(flap, **(values or {})), request, solvers=solvers
    )
    return result, opti


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


def flap_deflections(airplane: AirplaneGeometry) -> list[float | None]:
    return [
        None
        if s.trailing_edge_device is None or s.trailing_edge_device.role not in FLAP_ROLES
        else s.trailing_edge_device.deflection_deg
        for s in (airplane.wings or {})["Main"].x_secs
    ]


V_CLEAN = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28 * UPRIGHT_PEAK[1]))


async def test_clean_stall_speed_from_the_shipped_canon() -> None:
    result, opti = await run("stall-speed", "max-lift-coefficient", "angle-of-attack-stall")
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert close(quantities["stall-speed"].value, V_CLEAN, 1e-9)
    assert (quantities["stall-speed"].unit, quantities["stall-speed"].tool) == ("m/s", "OPT")
    assert quantities["stall-speed"].application == "clean"
    assert quantities["max-lift-coefficient"].value == UPRIGHT_PEAK[1]
    assert quantities["angle-of-attack-stall"].value == UPRIGHT_PEAK[0]
    assert len(opti.calls) == 1  # three outputs of one application call the formula once
    _, mass, gravity, n_load, air = opti.calls[0]
    assert (mass, gravity, n_load) == (MASS, 9.80665, 1.0)
    assert air.density == RHO


async def test_the_provenance_names_the_optimiser_tool_versions_and_settings() -> None:
    result, _ = await run("stall-speed")
    assert set(result.provenance.tool_versions) == {"aerosandbox", "neuralfoil"}
    assert result.provenance.solver_settings == OPT_SETTINGS


async def test_a_request_that_runs_no_solver_has_no_solver_settings() -> None:
    result, _ = await run("weight")
    assert result.provenance.solver_settings == {}


async def test_takeoff_and_landing_without_flaps_are_the_clean_airplane_not_a_fallback() -> None:
    result, opti = await run("stall-speed", "stall-speed-takeoff", "stall-speed-landing")
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    values = {q.value for q in quantities.values()}
    assert len(values) == 1
    assert all(q.warnings == () for q in quantities.values())
    airplanes = [call[0] for call in opti.calls]
    assert len(airplanes) == 3
    assert airplanes[0] == airplanes[1] == airplanes[2]


async def test_a_flap_deflection_for_an_airplane_without_flaps_is_declared_and_not_used() -> None:
    result, opti = await run("stall-speed-takeoff", values={"flap-deflection-takeoff": 40.0})
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    assert [w.code for w in only.warnings] == ["deflection_without_flap"]
    assert opti.calls[0][0] == shipped_airplane_at_rest()


def shipped_airplane_at_rest() -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(document())


async def test_takeoff_and_landing_with_flaps_set_the_flaps_exactly_and_independently() -> None:
    values = {"flap-deflection-takeoff": 20.0, "flap-deflection-landing": 45.0}
    result, opti = await run(
        "stall-speed", "stall-speed-takeoff", "stall-speed-landing", flap=True, values=values
    )
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    seen = {tuple(flap_deflections(call[0])) for call in opti.calls}
    assert seen == {
        (0.0, None),
        (20.0, None),
        (45.0, None),
    }  # clean, takeoff, landing; 45 > stop 30


async def test_flaps_without_a_deflection_fail_the_configured_speed_but_not_the_clean_one() -> None:
    result, _ = await run("stall-speed", "stall-speed-landing", flap=True)
    quantities = by_slug(result)
    assert quantities["stall-speed"].status is QuantityStatus.OK
    landing = quantities["stall-speed-landing"]
    assert landing.status is QuantityStatus.ERROR
    assert landing.error is not None
    assert landing.error.category is ErrorCategory.UPSTREAM_FAILED
    assert landing.error.detail["causes"] == [
        {"quantity": "airplane-landing", "code": "missing_input"}
    ]


async def test_the_inverted_application_solves_at_minus_one_g() -> None:
    result, opti = await run("inverted-max-lift-coefficient")
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    assert only.value == INVERTED_TROUGH[1]
    assert opti.calls[0][3] == -1.0


async def test_requesting_the_polar_is_not_implemented_and_the_formula_runs_once() -> None:
    result, opti = await run("polar-stall", "stall-speed")
    quantities = by_slug(result)
    polar = quantities["polar-stall"]
    assert polar.status is QuantityStatus.ERROR
    assert polar.error is not None
    assert (polar.error.category, polar.error.code) == (
        ErrorCategory.NOT_IMPLEMENTED,
        "non_scalar_result",
    )
    assert quantities["stall-speed"].status is QuantityStatus.OK
    assert len(opti.calls) == 1


async def test_an_inconsistent_optimum_is_a_postcondition_error_and_no_value() -> None:
    wrong = StallSolution(
        v_s=V_CLEAN * 1.05,  # does not close the lift balance at the sweep's C_L
        cl_max=UPRIGHT_PEAK[1],
        alpha_s=UPRIGHT_PEAK[0],
        polar=lift_curve(UPRIGHT_PEAK, upright=True),
    )
    result, _ = await run("stall-speed", "max-lift-coefficient", stub=StubOpti(answer=wrong))
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        assert quantity.error is not None
        assert quantity.error.code == "postcondition_violated"
        assert quantity.error.detail == {"postcondition": "cl_max_at_stall_reynolds_number"}


async def test_the_wrong_branch_is_a_postcondition_error() -> None:
    """The BRYAN failure: the optimum on the lower second maximum instead of the first peak."""
    polar = lift_curve(UPRIGHT_PEAK, upright=True)
    index = polar.alpha_deg.index(23.0)
    area = 0.28
    cl = polar.cl[index]
    wrong = StallSolution(
        v_s=math.sqrt(2 * MASS * 9.80665 / (RHO * area * cl)),
        cl_max=cl,
        alpha_s=23.0,
        polar=polar,
    )
    result, _ = await run("stall-speed", stub=StubOpti(answer=wrong))
    (only,) = result.quantities
    assert only.error is not None
    assert (only.error.code, only.error.detail) == (
        "postcondition_violated",
        {"postcondition": "optimum_at_first_cl_peak"},
    )


async def test_an_expired_time_budget_cancels_the_solve_and_reports_timeout() -> None:
    result, opti = await run("stall-speed", "weight", stub=StubOpti(delay_s=30.0), budget=0.2)
    quantities = by_slug(result)
    assert quantities["weight"].status is QuantityStatus.OK
    error = quantities["stall-speed"].error
    assert error is not None
    assert (error.category, error.code) == (ErrorCategory.TIMEOUT, "timeout")
    assert opti.cancelled


def flap_aware_stall(request: StallRequest) -> StallSolution:
    """A self-consistent stall whose C_L,max rises by 1 % per degree of flap: the configuration the
    solver was given shows in the value."""
    deflection = flap_deflections(request.airplane)[0] or 0.0
    alpha_s, cl_clean = UPRIGHT_PEAK
    cl_max = cl_clean * (1.0 + deflection / 100.0)
    area = stand_in_main_wing_properties(request.airplane).s_ref
    v_s = math.sqrt(2.0 * request.mass_kg * request.gravity / (request.air.density * area * cl_max))
    flow = FlowConditions(
        v_ms=v_s,
        density=request.air.density,
        dynamic_viscosity=request.air.dynamic_viscosity,
        speed_of_sound=request.air.speed_of_sound,
    )
    polar = lift_curve((alpha_s, cl_max), upright=True).model_copy(update={"conditions": flow})
    return StallSolution(v_s=v_s, cl_max=cl_max, alpha_s=alpha_s, polar=polar)


async def test_a_flapped_landing_reaches_the_solver_with_its_flap_and_never_as_the_clean_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reviewer's reproduction (a flap and flap-deflection-landing = 30 deg), now computed: the
    real adapter hands the worker the flapped airplane, the landing value is the flapped one (it
    differs from the clean speed) and the result declares the model range of the flap. The clean
    speed is never returned for a flapped request."""
    adapter = OptiAdapter(InProcessRuntime())
    calls: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        calls.append(request)
        return WorkerOutcome(
            value=flap_aware_stall(request), diagnostics=WorkerDiagnostics(duration_s=0.0)
        )

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=adapter)
    request = ComputeRequest(quantities=("stall-speed", "stall-speed-landing"))
    result = await evaluate(
        shipped_build(),
        aircraft(True, **{"flap-deflection-landing": 30.0}),
        request,
        solvers=solvers,
    )
    quantities = by_slug(result)
    assert quantities["stall-speed"].status is QuantityStatus.OK
    landing = quantities["stall-speed-landing"]
    assert landing.status is QuantityStatus.OK
    assert landing.error is None
    assert close(quantities["stall-speed"].value, V_CLEAN, 1e-9)
    assert landing.value is not None
    assert close(landing.value, V_CLEAN / math.sqrt(1.3), 1e-9)
    assert sorted(flap_deflections(c.airplane)[0] or 0.0 for c in calls) == [0.0, 30.0]
    (caveat,) = [w for w in landing.warnings if w.code == "control_surface_fit_range_unknown"]
    assert caveat.detail["flaps"] == [
        {"wing": "Main", "device": "device 0", "deflection_deg": 30.0}
    ]
    assert all(
        w.code != "control_surface_fit_range_unknown" for w in quantities["stall-speed"].warnings
    )
