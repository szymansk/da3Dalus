"""The Opti adapter: the stall speed as an optimisation over AeroBuildup (ch. 8.8, canon K32)."""

import importlib.metadata
import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import OptiAdapter, StallRequest, StallSolution
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane

pytestmark = pytest.mark.asyncio


def solution(v_s: float = 8.0, cl: float = 1.2, alpha_s: float = 14.0) -> StallSolution:
    alphas = (0.0, alpha_s, 20.0)
    polar = Polar(alpha_deg=alphas, cl=(0.3, cl, 1.0), cd=(0.01,) * 3, cm=(-0.01,) * 3)
    return StallSolution(v_s=v_s, cl_max=cl, alpha_s=alpha_s, polar=polar)


def canned(result: StallSolution) -> object:
    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert OptiAdapter.tool == "OPT"
    assert OptiAdapter.requirements == {"aerosandbox": "aerosandbox"}


async def test_the_stall_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        seen.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    result = await OptiAdapter(InProcessRuntime()).stall(airplane(), 1.5, 9.81, 1.0, AIR)
    (request,) = seen
    assert (request.mass_kg, request.gravity, request.n_load, request.air) == (1.5, 9.81, 1.0, AIR)
    assert request.airplane == airplane()
    assert result.solution == solution()


async def test_the_stall_carries_the_regime_warnings_of_its_stall_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m: at 8 m/s Re 9.1e4 and 4.6e4 (bubble-sensitive, in the band); at 2 m/s
    the smaller chord gives Re 1.1e4, below 3e4 (ADR 0028)."""
    adapter = OptiAdapter(InProcessRuntime())
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=8.0)))
    fast = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in fast.warnings] == ["reynolds_bubble_sensitive"]
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=2.0)))
    slow = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in slow.warnings] == ["reynolds_outside_band"]
    assert all(w.origin is None for w in (*fast.warnings, *slow.warnings))


@pytest.mark.parametrize(
    ("mass", "gravity", "n_load"),
    [(0.0, 9.81, 1.0), (-1.0, 9.81, 1.0), (1.5, 0.0, 1.0), (1.5, 9.81, 0.0), (1.5, 9.81, math.nan)],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, n_load: float
) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(airplane(), mass, gravity, n_load, AIR)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = OptiAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_tool_versions_are_aerosandboxs() -> None:
    assert OptiAdapter(InProcessRuntime()).tool_versions() == {
        "aerosandbox": importlib.metadata.version("aerosandbox")
    }


@pytest.mark.parametrize(
    ("role", "deflection"), [("flap", 30.0), ("aileron", -5.0), ("flaperon", 0.5)]
)
async def test_a_deflected_control_surface_is_refused_not_computed_as_clean(
    monkeypatch: pytest.MonkeyPatch, role: str, deflection: float
) -> None:
    """The conversion does not pass devices to AeroBuildup yet (it comes with the roll-rate step);
    a deflected airplane would silently be computed as the clean one."""
    called: list[object] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        called.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    adapter = OptiAdapter(InProcessRuntime())
    deflected = airplane(device=(role, deflection))
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(deflected, 1.5, 9.81, 1.0, AIR)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "deflected control surfaces are not yet passed to AeroBuildup" in raised.value.message
    assert "flap-1" in raised.value.message
    assert role in raised.value.message
    assert called == []


async def test_a_device_at_rest_is_no_obstacle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.stall(airplane(device=("flap", 0.0)), 1.5, 9.81, 1.0, AIR)
    assert result.solution == solution()
