"""The AeroBuildup adapter: an alpha sweep of the whole airplane (ARCHITECTURE ch. 8.8)."""

import importlib.metadata
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime, WorkerDiagnostics, WorkerOutcome, run_in_worker
from aero_kernel.schema import Polar
from aero_kernel.solvers import aerobuildup as aerobuildup_module
from aero_kernel.solvers.aerobuildup import AeroBuildupAdapter, SweepRequest
from aero_kernel.solvers.air import AirState

pytestmark = pytest.mark.asyncio

AIR = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)


class InProcessRuntime(SolverRuntime):
    """Runs the worker in this process: the fast tier has no pool, the worker is a stub."""

    async def run_cpu(self, fn: Any, *args: object) -> Any:
        outcome = run_in_worker(fn, args)
        if isinstance(outcome, WorkerOutcome):
            return outcome.value
        raise outcome.to_formula_error()


def airplane(chords: tuple[float, ...] = (0.2, 0.1)) -> AirplaneGeometry:
    sections = [
        {"xyz_le": [0.0, 0.3 * i, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for i, c in enumerate(chords)
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})


def canned(request: SweepRequest) -> WorkerOutcome[Polar]:
    n = len(request.alphas_deg)
    polar = Polar(
        alpha_deg=request.alphas_deg,
        cl=tuple(0.1 * i for i in range(n)),
        cd=(0.01,) * n,
        cm=(-0.01,) * n,
    )
    return WorkerOutcome(value=polar, diagnostics=WorkerDiagnostics(duration_s=0.0))


async def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert AeroBuildupAdapter.tool == "AB"
    assert AeroBuildupAdapter.requirements == {"aerosandbox": "aerosandbox"}


async def test_the_sweep_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[SweepRequest] = []

    def worker(request: SweepRequest) -> WorkerOutcome[Polar]:
        seen.append(request)
        return canned(request)

    monkeypatch.setattr(aerobuildup_module, "sweep_worker", worker)
    adapter = AeroBuildupAdapter(InProcessRuntime())
    sweep = await adapter.sweep(airplane(), 12.0, (0.0, 2.0, 4.0), AIR)
    (request,) = seen
    assert (request.velocity_ms, request.alphas_deg, request.air) == (12.0, (0.0, 2.0, 4.0), AIR)
    assert request.airplane == airplane()
    assert sweep.polar.alpha_deg == (0.0, 2.0, 4.0)


async def test_the_sweep_carries_the_regime_warnings_of_its_operating_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m at 12 m/s: Re 1.6e5 and 8e4 inside the band, no warning; at 2 m/s the
    smallest chord gives Re 1.3e4, below 3e4 (ADR 0028)."""
    monkeypatch.setattr(aerobuildup_module, "sweep_worker", canned)
    adapter = AeroBuildupAdapter(InProcessRuntime())
    quiet = await adapter.sweep(airplane(), 12.0, (0.0, 2.0), AIR)
    assert quiet.warnings == ()
    slow = await adapter.sweep(airplane(), 2.0, (0.0, 2.0), AIR)
    assert [w.code for w in slow.warnings] == ["reynolds_outside_band"]
    assert slow.warnings[0].origin is None  # the engine sets the origin


@pytest.mark.parametrize("velocity", [0.0, -1.0, float("nan")])
async def test_an_inadmissible_velocity_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, velocity: float
) -> None:
    monkeypatch.setattr(aerobuildup_module, "sweep_worker", canned)
    adapter = AeroBuildupAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.sweep(airplane(), velocity, (0.0, 2.0), AIR)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AeroBuildupAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = AeroBuildupAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.sweep(airplane(), 12.0, (0.0, 2.0), AIR)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_tool_versions_are_aerosandboxs() -> None:
    versions = AeroBuildupAdapter(InProcessRuntime()).tool_versions()
    assert versions == {"aerosandbox": importlib.metadata.version("aerosandbox")}
