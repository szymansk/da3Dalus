"""Builders for the solver tests: an in-process runtime, a small airplane and an air state."""

from typing import Any

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime, WorkerOutcome, run_in_worker
from aero_kernel.solvers.air import AirState

AIR = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)


class InProcessRuntime(SolverRuntime):
    """Runs the worker in this process: the fast tier has no pool, the worker is a stub."""

    async def run_cpu(self, fn: Any, *args: object) -> Any:
        outcome = run_in_worker(fn, args)
        if isinstance(outcome, WorkerOutcome):
            return outcome.value
        raise outcome.to_formula_error()


def airplane(
    chords: tuple[float, ...] = (0.2, 0.1),
    device: tuple[str, float] | None = None,
    tail_chords: tuple[float, ...] | None = None,
    surface_deflection: float | None = None,
) -> AirplaneGeometry:
    """A main wing of the given chords; ``device`` is (role, deflection_deg) on the first panel."""
    sections: list[dict[str, Any]] = [
        {"xyz_le": [0.0, 0.3 * i, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for i, c in enumerate(chords)
    ]
    if device is not None:
        role, deflection = device
        sections[0]["trailing_edge_device"] = {
            "name": "flap-1",
            "role": role,
            "deflection_deg": deflection,
        }
    if surface_deflection is not None:
        sections[0]["control_surface"] = {"name": "cs-1", "deflection": surface_deflection}
    wings: dict[str, Any] = {
        "Main": {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    }
    if tail_chords is not None:
        tail_sections = [
            {"xyz_le": [0.5, 0.1 * i, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca0012"}
            for i, c in enumerate(tail_chords)
        ]
        wings["Tail"] = {
            "name": "Tail",
            "surface_type": "horizontal_tail",
            "x_secs": tail_sections,
        }
    return AirplaneGeometry.model_validate({"name": "t", "wings": wings})
