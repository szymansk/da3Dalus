"""minimum-sink-speed-from-polar through the engine on the shipped canon, stub optimiser (fast tier)."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.solvers.opti import MinSinkSolution
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.stall_stubs import CD0, SINK_ALPHA, K, StubOpti
from aero_kernel.tests.test_stall_speed_engine import MASS, RHO, aircraft

pytestmark = pytest.mark.asyncio

SLUGS = (
    "minimum-sink-speed",
    "angle-of-attack-minimum-sink",
    "lift-coefficient-minimum-sink",
)
# Stub answers, plumbing only (the maths is verified in the _real aero test): parabolic polar,
# 1.4 m x 0.2 m wing, S_ref = 0.28 m^2, sea level, m = 1.5 kg:
# V_mp = sqrt(2 W / (rho S)) (k / (3 CD0))^(1/4); CL_mp = sqrt(3 CD0 / k).
V_MP = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28)) * (K / (3 * CD0)) ** 0.25


async def run(
    *slugs: str, stub: StubOpti | None = None, budget: float | None = None
) -> tuple[ComputeResult, StubOpti]:
    opti = stub or StubOpti()
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti)
    request = ComputeRequest(quantities=slugs, time_budget_s=budget)
    result = await evaluate(shipped_build(), aircraft(), request, solvers=solvers)
    return result, opti


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


async def test_level_flight_minimum_sink_from_the_shipped_canon() -> None:
    result, opti = await run(*SLUGS)
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert close(quantities["minimum-sink-speed"].value, V_MP, 1e-12)
    assert quantities["minimum-sink-speed"].unit == "m/s"
    assert quantities["angle-of-attack-minimum-sink"].value == SINK_ALPHA
    assert close(quantities["lift-coefficient-minimum-sink"].value, math.sqrt(3 * CD0 / K), 1e-12)
    assert all(q.tool == "OPT" and q.application == "level_flight" for q in quantities.values())
    assert len(opti.sink_calls) == 1  # three outputs of one application call the formula once
    assert (opti.calls, opti.glide_calls) == ([], [])
    _, mass, gravity, n_load, air = opti.sink_calls[0]
    assert (mass, gravity, n_load, air.density) == (MASS, 9.80665, 1.0, RHO)


async def test_the_minimum_sink_speed_is_the_minimum_drag_speed_over_the_fourth_root_of_three() -> (
    None
):
    """Plumbing: both stub answers are the closed forms of one parabolic polar, so V_mp = V_md / 3^(1/4).

    The maths of the optimum is verified against real IPOPT in test_solvers_opti_min_sink_real.py.
    """
    result, _ = await run("minimum-sink-speed", "minimum-drag-speed")
    quantities = by_slug(result)
    sink, drag = quantities["minimum-sink-speed"].value, quantities["minimum-drag-speed"].value
    assert sink is not None
    assert drag is not None
    assert close(sink, drag / 3**0.25, 1e-12)


async def test_an_optimiser_that_does_not_converge_gives_no_value() -> None:
    class Failing(StubOpti):
        async def min_sink(self, *args: object) -> object:  # type: ignore[override]
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "bound", "hint")

    result, _ = await run(*SLUGS, stub=Failing())
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        assert quantity.error is not None
        assert quantity.error.category is ErrorCategory.NOT_CONVERGED


async def test_an_expired_time_budget_cancels_the_solve_and_reports_timeout() -> None:
    result, opti = await run(
        "minimum-sink-speed", "weight", stub=StubOpti(delay_s=30.0), budget=0.2
    )
    quantities = by_slug(result)
    assert quantities["weight"].status is QuantityStatus.OK
    error = quantities["minimum-sink-speed"].error
    assert error is not None
    assert (error.category, error.code) == (ErrorCategory.TIMEOUT, "timeout")
    assert opti.cancelled


async def test_the_sink_solution_type_carries_the_three_outputs() -> None:
    assert set(MinSinkSolution.model_fields) == {"v_mp", "alpha_mp", "cl_mp"}
