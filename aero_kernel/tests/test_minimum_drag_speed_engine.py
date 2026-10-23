"""minimum-drag-speed-from-polar through the engine on the shipped canon, stub optimiser (fast tier)."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.solvers.opti import BestGlideSolution
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.stall_stubs import CD0, GLIDE_ALPHA, K, StubOpti
from aero_kernel.tests.test_stall_speed_engine import MASS, RHO, aircraft

pytestmark = pytest.mark.asyncio

SLUGS = (
    "minimum-drag-speed",
    "max-lift-to-drag-ratio",
    "angle-of-attack-best-glide",
    "lift-coefficient-best-glide",
)
# Hand values (parabolic polar, 1.4 m x 0.2 m wing, S_ref = 0.28 m^2, sea level, m = 1.5 kg):
# V_md = sqrt(2 W / (rho S)) (k / CD0)^(1/4) = 9.2666 * 1.13622 = 10.529 m/s; CL_md = sqrt(CD0 / k).
V_MD = math.sqrt(2 * MASS * 9.80665 / (RHO * 0.28)) * (K / CD0) ** 0.25


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


async def test_level_flight_best_glide_from_the_shipped_canon() -> None:
    result, opti = await run(*SLUGS)
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert close(quantities["minimum-drag-speed"].value, V_MD, 1e-12)
    assert quantities["minimum-drag-speed"].unit == "m/s"
    assert close(quantities["max-lift-to-drag-ratio"].value, 1 / (2 * math.sqrt(CD0 * K)), 1e-12)
    assert quantities["angle-of-attack-best-glide"].value == GLIDE_ALPHA
    assert close(quantities["lift-coefficient-best-glide"].value, math.sqrt(CD0 / K), 1e-12)
    assert all(q.tool == "OPT" and q.application == "level_flight" for q in quantities.values())
    assert len(opti.glide_calls) == 1  # four outputs of one application call the formula once
    assert opti.calls == []
    _, mass, gravity, n_load, air = opti.glide_calls[0]
    assert (mass, gravity, n_load, air.density) == (MASS, 9.80665, 1.0, RHO)


async def test_the_provenance_names_the_optimiser_tool_versions_and_settings() -> None:
    result, _ = await run("minimum-drag-speed")
    assert set(result.provenance.tool_versions) == {"aerosandbox", "neuralfoil"}
    assert result.provenance.solver_settings == {"neuralfoil_model_size": "xlarge"}


async def test_a_heavier_airplane_flies_the_best_glide_faster_by_the_square_root() -> None:
    light, _ = await run("minimum-drag-speed")
    heavy_input = aircraft()  # the same airplane, 4 times the mass
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=StubOpti())
    heavy_values = heavy_input.model_copy(
        update={"values": {**heavy_input.values, "aircraft-mass": 4 * MASS}}
    )
    request = ComputeRequest(quantities=("minimum-drag-speed",))
    heavy = await evaluate(shipped_build(), heavy_values, request, solvers=solvers)
    light_speed, heavy_speed = light.quantities[0].value, heavy.quantities[0].value
    assert light_speed is not None
    assert close(heavy_speed, 2 * light_speed, 1e-12)


async def test_an_optimiser_that_does_not_converge_gives_no_value() -> None:
    from aero_kernel.errors import FormulaError

    class Failing(StubOpti):
        async def best_glide(self, *args: object) -> object:  # type: ignore[override]
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "bound", "hint")

    result, _ = await run(*SLUGS, stub=Failing())
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        assert quantity.error is not None
        assert quantity.error.category is ErrorCategory.NOT_CONVERGED


async def test_an_expired_time_budget_cancels_the_solve_and_reports_timeout() -> None:
    result, opti = await run(
        "minimum-drag-speed", "weight", stub=StubOpti(delay_s=30.0), budget=0.2
    )
    quantities = by_slug(result)
    assert quantities["weight"].status is QuantityStatus.OK
    error = quantities["minimum-drag-speed"].error
    assert error is not None
    assert (error.category, error.code) == (ErrorCategory.TIMEOUT, "timeout")
    assert opti.cancelled


async def test_the_glide_solution_type_carries_the_four_outputs() -> None:
    assert set(BestGlideSolution.model_fields) == {"v_md", "e_max", "alpha_md", "cl_md"}
