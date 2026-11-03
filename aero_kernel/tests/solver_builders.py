"""Builders for the solver tests: an in-process runtime, a small airplane and an air state."""

from typing import Any

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime, WorkerOutcome, run_in_worker
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.air import AirState

AIR = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)


def canon_k_e_d0() -> float:
    """The viscous factor k_e,D0 of the shipped canon (rule ``aerobuildup-induced-drag``, #1346)."""
    from aero_kernel.build import shipped_build
    from aero_kernel.solvers.aerobuildup import INDUCED_DRAG_RULE, VISCOUS_FACTOR_PARAMETER

    rule = shipped_build().model.namespaces["calc"].rules[INDUCED_DRAG_RULE]
    return rule.parameters[VISCOUS_FACTOR_PARAMETER].value


# The factor the worker requests of the fast tier carry: the canon's, as the adapter reads it.
K_E_D0 = canon_k_e_d0()


def drag_notice() -> KernelWarning:
    """The notice the adapter puts on every value that carries the kernel's drag (#1346)."""
    from aero_kernel.solvers.opti import induced_drag_notice

    return induced_drag_notice(K_E_D0)


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
    hinge: float | None = None,
) -> AirplaneGeometry:
    """A main wing of the given chords; ``device`` is (role, deflection_deg) on the first panel.

    ``hinge`` gives the device its hinge position (fraction of chord), which a flap needs.
    """
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
            "rel_chord_root": hinge,
            "rel_chord_tip": hinge,
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


def direct_aero_model(_key: str | None, airplane: Any, model_size: str) -> tuple[Any, str]:
    """Test seam for ``opti.aero_model``: evaluate the faked AeroSandbox at every call.

    The fast tier has no CasADi, so a test that fakes ``opti.load_aerosandbox`` cannot build a
    model function. This stand-in evaluates the faked ``AeroBuildup`` at the arguments the
    problem passes (Opti variables or numbers), so the fake sees the same operating points as
    the real function's inputs.
    """
    from aero_kernel.solvers import opti as opti_module
    from aero_kernel.solvers.air import FixedAtmosphere

    asb = opti_module.load_aerosandbox()

    def model(
        v: Any, alpha: Any, air: AirState, *, p: Any = 0.0, q: Any = 0.0, r: Any = 0.0
    ) -> Any:
        point = asb.OperatingPoint(
            atmosphere=FixedAtmosphere(air), velocity=v, alpha=alpha, p=p, q=q, r=r
        )
        return asb.AeroBuildup(airplane, point, model_size=model_size).run()

    return model, "aero model evaluated directly (test seam)"
