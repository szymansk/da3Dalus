"""maneuvering-speed through the engine on the shipped canon, stub optimiser (fast tier)."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.devices import with_flaps_at
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.maneuvering_speed import maneuvering_speed
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import ComputeRequest, ComputeResult, KernelWarning, QuantityStatus
from aero_kernel.solvers.opti import Stall
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    close,
    solvers_with,
)
from aero_kernel.tests.stall_stubs import StubOpti, flap_confidence
from aero_kernel.tests.test_stall_speed_engine import MASS, RHO, aircraft, document

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


async def test_the_regime_warnings_of_the_optimiser_arrive_on_the_manoeuvring_speed() -> None:
    class Warned(StubOpti):
        async def stall(self, *args: object) -> Stall:  # type: ignore[override]  # stub forwards
            stall = await super().stall(*args)  # type: ignore[arg-type]
            warning = KernelWarning.of("reynolds_bubble_sensitive", "Re is low", detail={"re": 6e4})
            return Stall(solution=stall.solution, warnings=(warning,))

    result, _ = await run("maneuvering-speed", stub=Warned())
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.OK, result
    # beside the notice that the default limit load factor was used
    assert ("reynolds_bubble_sensitive", "maneuvering-speed", {"re": 6e4}) in [
        (w.code, w.origin, w.detail) for w in quantity.warnings
    ]


async def test_a_manoeuvring_speed_on_a_deflected_flap_declares_its_validity() -> None:
    """The formula called directly with a flap at 45 deg (above the 30 deg limit of the rule
    flap-model-validity) and NeuralFoil's confidence 0.407 (below the floor 0.85) over the flap.

    The engine never hands the formula a deflected flap (its only application binds the airplane at
    rest), so the caveat is pinned on the formula itself: both declarations carry the origin.
    """

    class Diagnosed(StubOpti):
        async def stall(self, *args: object) -> Stall:  # type: ignore[override]  # stub forwards
            stalled = await super().stall(*args)  # type: ignore[arg-type]
            solution = stalled.solution.model_copy(update={"diagnostics": flap_confidence(0.407)})
            return Stall(solution=solution, warnings=())

    airplane = with_flaps_at(AirplaneGeometry.model_validate(document(True)), 45.0)
    x = {
        "airplane": airplane,
        "m": MASS,
        "g": 9.80665,
        "n_lim": 10.0,
        "rho": RHO,
        "mu": STUB_VISCOSITY,
        "a": STUB_SPEED_OF_SOUND,
    }
    ctx = Context(origin="maneuvering-speed", solvers=solvers_with(opti=Diagnosed()))
    await maneuvering_speed(x, ctx)
    (beyond,) = [w for w in ctx.warnings if w.code == "flap_deflection_beyond_validity"]
    assert beyond.origin == "maneuvering-speed"
    assert beyond.detail["limit_deg"] == 30.0
    assert beyond.detail["flaps"] == [
        {"wing": "Main", "device": "device 0", "deflection_deg": 45.0}
    ]
    (low,) = [w for w in ctx.warnings if w.code == "flap_confidence_low"]
    assert low.origin == "maneuvering-speed"
    assert low.detail["mean_confidence"] == 0.407
    assert low.detail["threshold"] == 0.85
