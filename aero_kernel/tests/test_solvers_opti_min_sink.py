"""The minimum-sink problem of the OPT adapter: min D V s.t. L = n m g on the pre-stall branch."""

import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.base import regime_by_wing
from aero_kernel.solvers.opti import MinSinkSolution, OptiAdapter, StallRequest
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane
from aero_kernel.tests.test_solvers_opti_glide import (
    GRAVITY,
    MASS,
    V_HIGH,
    V_LOW,
    install_optimum,
)

pytestmark = pytest.mark.asyncio


def sink(v_mp: float = 9.0) -> MinSinkSolution:
    return MinSinkSolution(v_mp=v_mp, alpha_mp=7.0, cl_mp=0.9)


def canned(result: MinSinkSolution) -> object:
    def worker(request: StallRequest) -> WorkerOutcome[MinSinkSolution]:
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_sink_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[MinSinkSolution]:
        seen.append(request)
        return WorkerOutcome(value=sink(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "min_sink_worker", worker)
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).min_sink(plane, MASS, GRAVITY, 1.0, AIR)
    (request,) = seen
    assert (request.mass_kg, request.gravity, request.n_load, request.air) == (
        MASS,
        GRAVITY,
        1.0,
        AIR,
    )
    assert request.airplane == plane
    assert result.solution == sink()


async def test_the_regime_warnings_are_those_of_the_optimum_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m at 6 m/s: Re 8.2e4 and 4.1e4, so the smaller chord is bubble-sensitive;
    at 18 m/s there is no warning at all."""
    monkeypatch.setattr(opti_module, "min_sink_worker", canned(sink(6.0)))
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.min_sink(airplane(), MASS, GRAVITY, 1.0, AIR)
    expected = regime_by_wing(
        {"Main": [0.2, 0.1]}, 6.0, AIR.speed_of_sound, AIR.kinematic_viscosity
    )
    assert [w.code for w in expected] == ["reynolds_bubble_sensitive"]
    assert result.warnings == tuple(expected)
    monkeypatch.setattr(opti_module, "min_sink_worker", canned(sink(18.0)))
    assert (await adapter.min_sink(airplane(), MASS, GRAVITY, 1.0, AIR)).warnings == ()


@pytest.mark.parametrize(
    ("mass", "gravity", "n_load"),
    [
        (0.0, 9.81, 1.0),
        (1.5, -1.0, 1.0),
        (1.5, 9.81, 0.0),
        (1.5, 9.81, -1.0),
        (1.5, 9.81, math.nan),
    ],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, n_load: float
) -> None:
    monkeypatch.setattr(opti_module, "min_sink_worker", canned(sink()))
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.min_sink(plane, mass, gravity, n_load, AIR)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_deflected_control_surface_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "min_sink_worker", canned(sink()))
    adapter = OptiAdapter(InProcessRuntime())
    deflected = airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await adapter.min_sink(deflected, MASS, GRAVITY, 1.0, AIR)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.min_sink(plane, MASS, GRAVITY, 1.0, AIR)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


# --- the worker, with the solver boundary faked ------------------------------------------------


async def test_the_worker_reads_the_optimum_speed_angle_and_lift_coefficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = install_optimum(monkeypatch, 9.0, 7.0, cl=0.9)
    solution = opti_module.min_sink_worker(request).value
    assert (solution.v_mp, solution.alpha_mp, solution.cl_mp) == (9.0, 7.0, 0.9)


async def test_the_worker_minimises_the_sink_power_drag_times_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D V is the power the glide loses; at fixed weight it is proportional to the sink rate."""
    objective: list[object] = []
    request = install_optimum(monkeypatch, 9.0, 7.0, objective=objective)
    opti_module.min_sink_worker(request)
    (minimised,) = objective
    assert minimised.name == "D*speed"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("v", "alpha", "variable"),
    [
        (V_HIGH, 7.0, "V"),
        (V_LOW, 7.0, "V"),
        (9.0, opti_module.ALPHA_MIN_DEG, "alpha"),
        (9.0, 15.75, "alpha"),  # the window's upper edge: the first peak itself
    ],
)
async def test_an_optimum_on_a_bound_is_not_converged_and_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, v: float, alpha: float, variable: str
) -> None:
    request = install_optimum(monkeypatch, v, alpha)
    with pytest.raises(FormulaError) as raised:
        opti_module.min_sink_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["variable"] == variable
    assert "minimum-sink" in raised.value.message


async def test_an_ipopt_failure_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_optimum(monkeypatch, 9.0, 7.0, error=RuntimeError("Infeasible_Problem"))
    with pytest.raises(FormulaError) as raised:
        opti_module.min_sink_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_any_other_exception_stays_an_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_optimum(monkeypatch, 9.0, 7.0, error=ValueError("a bug"))
    with pytest.raises(ValueError, match="a bug"):
        opti_module.min_sink_worker(request)
