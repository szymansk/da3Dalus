"""maneuvering-speed through the engine on the shipped canon, stub optimiser (fast tier)."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityStatus
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_stall_speed_engine import MASS, RHO, aircraft

pytestmark = pytest.mark.asyncio


async def run(
    *slugs: str, stub: StubOpti | None = None, values: dict[str, float] | None = None
) -> tuple[ComputeResult, StubOpti]:
    opti = stub or StubOpti()
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti)
    request = ComputeRequest(quantities=slugs)
    result = await evaluate(
        shipped_build(), aircraft(False, **(values or {})), request, solvers=solvers
    )
    return result, opti


async def test_the_stall_problem_is_solved_at_the_default_limit_load_factor() -> None:
    result, opti = await run("maneuvering-speed", "stall-speed")
    v_a, v_s = result.quantities
    assert v_a.status is QuantityStatus.OK, result
    assert (v_a.unit, v_a.tool) == ("m/s", "OPT")
    # the stub's lift curve does not depend on the speed, so the corner is V_S * sqrt(n_lim)
    assert v_s.value is not None
    assert close(v_a.value, v_s.value * math.sqrt(10.0), 1e-12)
    loads = sorted(call[3] for call in opti.calls)
    assert loads == [1.0, 10.0]
    _, mass, gravity, _, air = opti.calls[0]
    assert (mass, gravity, air.density) == (MASS, 9.80665, RHO)


async def test_a_given_limit_load_factor_binds_the_problem() -> None:
    result, opti = await run("maneuvering-speed", values={"limit-load-factor": 4.0})
    assert result.quantities[0].status is QuantityStatus.OK, result
    assert [call[3] for call in opti.calls] == [4.0]
    default, _ = await run("maneuvering-speed")
    assert default.quantities[0].value is not None
    assert close(result.quantities[0].value, default.quantities[0].value * math.sqrt(0.4), 1e-12)


async def test_an_optimiser_that_does_not_converge_gives_no_value() -> None:
    class Failing(StubOpti):
        async def stall(self, *args: object) -> object:  # type: ignore[override]  # stub raises
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "bound", "hint")

    result, _ = await run("maneuvering-speed", stub=Failing())
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.value is None
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.NOT_CONVERGED
