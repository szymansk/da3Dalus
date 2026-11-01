"""The AeroBuildup evaluation of the OPT adapter: L and D at the caller's (V, alpha) and air state.

Fast tier: the adapter with a canned worker, the worker and ``evaluate_forces`` with AeroSandbox
faked at the solver boundary.
"""

import math
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import aerobuildup as aerobuildup_module
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.aerobuildup import evaluate_forces
from aero_kernel.solvers.base import regime_by_wing
from aero_kernel.solvers.opti import EvaluationRequest, Forces, OptiAdapter
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane

pytestmark = pytest.mark.asyncio

FORCES = Forces(lift_n=14.7, drag_n=0.98)


def canned(seen: list[EvaluationRequest] | None = None) -> object:
    def worker(request: EvaluationRequest) -> WorkerOutcome[Forces]:
        if seen is not None:
            seen.append(request)
        return WorkerOutcome(value=FORCES, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_hands_the_worker_the_operating_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[EvaluationRequest] = []
    monkeypatch.setattr(opti_module, "evaluation_worker", canned(seen))
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).evaluate(plane, AIR, 10.0, 4.0)
    (request,) = seen
    assert (request.airplane, request.air, request.v_ms, request.alpha_deg) == (
        plane,
        AIR,
        10.0,
        4.0,
    )
    assert result.forces == FORCES


async def test_the_regime_warnings_are_those_of_the_callers_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "evaluation_worker", canned())
    result = await OptiAdapter(InProcessRuntime()).evaluate(airplane(), AIR, 6.0, 2.0)
    expected = regime_by_wing(
        {"Main": [0.2, 0.1]}, 6.0, AIR.speed_of_sound, AIR.kinematic_viscosity
    )
    assert result.warnings == tuple(expected)


@pytest.mark.parametrize(
    ("v", "alpha", "parameter"),
    [
        (0.0, 4.0, "v"),
        (-3.0, 4.0, "v"),
        (math.nan, 4.0, "v"),
        (10.0, math.nan, "alpha"),
        (10.0, math.inf, "alpha"),
    ],
)
async def test_an_inadmissible_operating_point_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, v: float, alpha: float, parameter: str
) -> None:
    """A negative angle of attack is admissible; only a non-finite one is not."""
    monkeypatch.setattr(opti_module, "evaluation_worker", canned())
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.evaluate(plane, AIR, v, alpha)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == parameter


async def test_a_negative_angle_of_attack_is_evaluated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "evaluation_worker", canned())
    result = await OptiAdapter(InProcessRuntime()).evaluate(airplane(), AIR, 10.0, -6.0)
    assert result.forces == FORCES


async def test_a_deflected_aileron_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "evaluation_worker", canned())
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await adapter.evaluate(plane, AIR, 10.0, 4.0)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_deflected_flap_is_evaluated_and_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "evaluation_worker", canned())
    flapped = airplane(device=("flap", 10.0), hinge=0.75)
    result = await OptiAdapter(InProcessRuntime()).evaluate(flapped, AIR, 10.0, 4.0)
    (declared,) = [w for w in result.warnings if w.code == "control_surface_fit_range_unknown"]
    assert declared.detail["flaps"] == [
        {"wing": "Main", "device": "flap-1", "deflection_deg": 10.0}
    ]


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.evaluate(plane, AIR, 10.0, 4.0)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_worker_evaluates_the_converted_airplane(monkeypatch: pytest.MonkeyPatch) -> None:
    converted = SimpleNamespace(s_ref=0.28)
    seen: list[tuple[object, ...]] = []

    def forces(*args: object) -> tuple[float, float]:
        seen.append(args)
        return 14.7, 0.98

    def convert(_airplane: object) -> SimpleNamespace:
        return converted

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "evaluate_forces", forces)
    request = EvaluationRequest(airplane=airplane(), air=AIR, v_ms=10.0, alpha_deg=4.0)
    outcome = opti_module.evaluation_worker(request)
    assert outcome.value == FORCES
    assert seen == [(converted, AIR, 10.0, 4.0, opti_module.NEURALFOIL_MODEL_SIZE)]


async def test_evaluate_forces_reads_lift_and_drag_of_one_aerobuildup_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AeroBuildup's own L and D in newtons, at the given point; nothing derived from coefficients."""
    runs: list[dict[str, Any]] = []

    def aerobuildup(airplane: object, op_point: Any, **kwargs: object) -> SimpleNamespace:
        runs.append({"airplane": airplane, "op": op_point, **kwargs})
        return SimpleNamespace(run=lambda: {"L": np.array([14.7]), "D": 0.98, "CL": 0.5})

    def operating_point(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    fake = SimpleNamespace(AeroBuildup=aerobuildup, OperatingPoint=operating_point)
    monkeypatch.setattr(aerobuildup_module, "load_aerosandbox", lambda: fake)
    plane = object()
    lift, drag = evaluate_forces(plane, AIR, 10.0, 4.0, "xlarge")
    assert (lift, drag) == (14.7, 0.98)
    (run,) = runs
    assert (run["airplane"], run["model_size"]) == (plane, "xlarge")
    assert (run["op"].velocity, run["op"].alpha) == (10.0, 4.0)
    assert run["op"].atmosphere.density() == AIR.density


async def test_sweep_polar_runs_aerobuildup_over_the_angles_at_one_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sweep next to the evaluation: one vectorised run, the speed repeated per angle."""
    seen: list[Any] = []

    def aerobuildup(_airplane: object, op_point: Any, **_: object) -> SimpleNamespace:
        seen.append(op_point)
        result = {"CL": np.array([0.1, 0.5]), "CD": np.array([0.02, 0.03]), "Cm": np.zeros(2)}
        return SimpleNamespace(run=lambda: result)

    def operating_point(**kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    fake = SimpleNamespace(AeroBuildup=aerobuildup, OperatingPoint=operating_point)
    monkeypatch.setattr(aerobuildup_module, "load_aerosandbox", lambda: fake)
    polar = aerobuildup_module.sweep_polar(object(), AIR, 9.0, [0.0, 4.0], "xlarge")
    assert (polar.alpha_deg, polar.cl, polar.cd, polar.cm) == (
        (0.0, 4.0),
        (0.1, 0.5),
        (0.02, 0.03),
        (0.0, 0.0),
    )
    assert polar.conditions is not None
    assert polar.conditions.v_ms == 9.0
    (point,) = seen
    assert list(point.velocity) == [9.0, 9.0]
