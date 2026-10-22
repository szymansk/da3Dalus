"""A stub OPT adapter that answers the stall problem from a closed-form lift curve."""

import math

from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import Polar
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import OptiAdapter, Stall, StallSolution

STEP = 0.25
UPRIGHT_PEAK = (15.75, 1.19)  # alpha_S in deg, C_L,max
INVERTED_TROUGH = (-10.0, -0.70)


def lift_curve(peak: tuple[float, float], upright: bool) -> Polar:
    """A sweep -15..25 deg with a first extremum at ``peak`` and a second branch behind it."""
    alphas = [-15.0 + k * STEP for k in range(161)]
    at, top = peak

    def cl(alpha: float) -> float:
        if upright:
            return top - 0.04 * (at - alpha) if alpha <= at else max(top - 0.2 * (alpha - at), 0.8)
        return top + 0.04 * (alpha - at) if alpha >= at else min(top + 0.2 * (at - alpha), -0.4)

    return Polar(
        alpha_deg=tuple(alphas),
        cl=tuple(cl(a) for a in alphas),
        cd=(0.05,) * len(alphas),
        cm=(-0.02,) * len(alphas),
    )


def consistent_stall(
    airplane: AirplaneGeometry, mass: float, gravity: float, n_load: float, air: AirState
) -> StallSolution:
    """The self-consistent answer: V_S from the closed form with the lift curve's extremum."""
    upright = n_load > 0.0
    alpha_s, cl_max = UPRIGHT_PEAK if upright else INVERTED_TROUGH
    polar = lift_curve((alpha_s, cl_max), upright)
    area = main_wing_properties(airplane).s_ref
    v_s = math.sqrt(2.0 * abs(n_load) * mass * gravity / (air.density * area * abs(cl_max)))
    return StallSolution(v_s=v_s, cl_max=cl_max, alpha_s=alpha_s, polar=polar)


class StubOpti(OptiAdapter):
    """Records its calls and answers consistently, or with a given solution."""

    def __init__(self, answer: StallSolution | None = None, delay_s: float = 0.0) -> None:
        super().__init__(SolverRuntime())
        self.answer = answer
        self.delay_s = delay_s
        self.calls: list[tuple[AirplaneGeometry, float, float, float, AirState]] = []
        self.cancelled = False

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        """Answer without a solver."""
        import asyncio

        self.calls.append((airplane, mass_kg, gravity, n_load, air))
        try:
            await asyncio.sleep(self.delay_s)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        solution = self.answer or consistent_stall(airplane, mass_kg, gravity, n_load, air)
        return Stall(solution=solution, warnings=())
