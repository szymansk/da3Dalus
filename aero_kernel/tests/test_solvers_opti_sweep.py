"""The alpha sweep of the OPT adapter: AeroBuildup at a fixed speed over given angles (fast tier)."""

import math
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import OptiAdapter, SweepRequest
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve

pytestmark = pytest.mark.asyncio

ALPHAS = (14.0, 14.5, 15.0)


def canned(polar: Polar) -> object:
    def worker(request: SweepRequest) -> WorkerOutcome[Polar]:
        return WorkerOutcome(value=polar, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_sweep_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[SweepRequest] = []
    polar = lift_curve(UPRIGHT_PEAK, upright=True)

    def worker(request: SweepRequest) -> WorkerOutcome[Polar]:
        seen.append(request)
        return WorkerOutcome(value=polar, diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "sweep_worker", worker)
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).sweep(plane, AIR, 10.0, ALPHAS)
    (request,) = seen
    assert (request.airplane, request.air, request.v_ms, request.alphas_deg) == (
        plane,
        AIR,
        10.0,
        ALPHAS,
    )
    assert result == polar


@pytest.mark.parametrize(
    ("v_ms", "alphas"),
    [
        (0.0, ALPHAS),
        (-1.0, ALPHAS),
        (math.nan, ALPHAS),
        (10.0, ()),
        (10.0, (15.0, 14.0)),
        (10.0, (14.0, 14.0)),
        (10.0, (14.0, math.nan)),
    ],
)
async def test_an_inadmissible_speed_or_angle_series_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, v_ms: float, alphas: tuple[float, ...]
) -> None:
    monkeypatch.setattr(opti_module, "sweep_worker", canned(lift_curve(UPRIGHT_PEAK, upright=True)))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).sweep(airplane(), AIR, v_ms, alphas)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_deflected_control_surface_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "sweep_worker", canned(lift_curve(UPRIGHT_PEAK, upright=True)))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).sweep(
            airplane(device=("aileron", 4.0)), AIR, 10.0, ALPHAS
        )
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).sweep(airplane(), AIR, 10.0, ALPHAS)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_worker_sweeps_the_converted_airplane_with_the_adapters_model_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []
    polar = lift_curve(UPRIGHT_PEAK, upright=True)

    def sweep(*args: object) -> Polar:
        calls.append(args)
        return polar

    converted = SimpleNamespace(s_ref=0.28)

    def convert(_: object) -> SimpleNamespace:
        return converted

    monkeypatch.setattr(opti_module, "sweep_polar", sweep)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    request = SweepRequest(airplane=airplane(), air=AIR, v_ms=10.0, alphas_deg=ALPHAS)
    outcome = opti_module.sweep_worker(request)
    assert outcome.value == polar
    assert calls == [(converted, AIR, 10.0, ALPHAS, opti_module.NEURALFOIL_MODEL_SIZE)]
