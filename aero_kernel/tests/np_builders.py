"""Builders for the neutral-point tests: a conventional airplane of known planform and a stub AVL."""

import math
from typing import Any

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.avl import AvlAdapter, AvlNeutralPoint, AvlRoll

# Hand fixture: main wing half span 0.7 m, chord 0.2 m, leading edge x = 0.05 m (S = 0.28 m^2,
# AR = 7, c_MAC = 0.2 m, x_ac = 0.10 m); tail half span 0.2 m, chord 0.1 m, leading edge x = 0.60 m
# (S_h = 0.04 m^2, AR_h = 4, x_ac = 0.625 m).
MAIN = {"half_span": 0.7, "chord": 0.2, "x_le": 0.05}
TAIL = {"half_span": 0.2, "chord": 0.1, "x_le": 0.60}


def surface(name: str, surface_type: str, half_span: float, chord: float, x_le: float) -> Any:
    """A mirrored rectangular surface from y = 0 to ``half_span``."""
    sections = [
        {"xyz_le": [x_le, y, 0.0], "chord": chord, "twist": 0.0, "airfoil": "naca0012"}
        for y in (0.0, half_span)
    ]
    return {"name": name, "symmetric": True, "surface_type": surface_type, "x_secs": sections}


def airplane_with(*types: str) -> AirplaneGeometry:
    """An airplane whose wings have the given surface types, the first being the main wing.

    The main wing and a ``horizontal_tail`` have the fixture planforms; any other type gets the tail's.
    """
    wings: dict[str, Any] = {}
    for index, surface_type in enumerate(types):
        geometry = MAIN if surface_type == "main_wing" else TAIL
        name = f"{surface_type}-{index}"
        wings[name] = surface(name, surface_type, **geometry)
    return AirplaneGeometry.model_validate({"name": "np", "wings": wings})


CONVENTIONAL = ("main_wing", "horizontal_tail")


class StubAvl(AvlAdapter):
    """An AVL adapter that records the lift coefficient it is asked for and answers a canned x_NP."""

    def __init__(self, x_np: float = 0.14, warnings: tuple[KernelWarning, ...] = ()) -> None:
        super().__init__(SolverRuntime())
        self.x_np = x_np
        self.canned_warnings = warnings
        self.calls: list[tuple[AirplaneGeometry, float]] = []
        self.failure: Exception | None = None
        self.p_hat = 0.25  # |p'b/2V| of the stub's steady roll, signed by the command
        self.roll_calls: list[tuple[AirplaneGeometry, float, float]] = []
        self.roll_failure: Exception | None = None

    async def neutral_point(self, airplane: AirplaneGeometry, cl: float) -> AvlNeutralPoint:
        """Answer without AVL."""
        self.calls.append((airplane, cl))
        if self.failure is not None:
            raise self.failure
        return AvlNeutralPoint(x_np=self.x_np, warnings=self.canned_warnings)

    async def steady_roll(
        self, airplane: AirplaneGeometry, cl: float, delta_a_deg: float
    ) -> AvlRoll:
        """Answer the steady roll without AVL: ``p_hat`` with the sign of the command."""
        self.roll_calls.append((airplane, cl, delta_a_deg))
        if self.roll_failure is not None:
            raise self.roll_failure
        return AvlRoll(p_hat=math.copysign(self.p_hat, delta_a_deg), warnings=self.canned_warnings)
