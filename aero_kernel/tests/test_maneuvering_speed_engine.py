"""maneuvering-speed through the engine on the shipped canon, stub optimiser (fast tier)."""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.devices import devices_at_rest, with_flaps_at
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.maneuvering_speed import maneuvering_speed
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    KernelWarning,
    QuantityStatus,
)
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


async def test_the_formula_declares_nothing_about_flaps() -> None:
    """V_A is the value of the clean configuration (canon entry, FAR 23.335(c); maintainer
    2026-11-27, #1477): the flap-model validity is no concern of this formula. Even called past the
    engine with a flap at 45 deg and NeuralFoil's confidence 0.407 over it, it declares nothing
    about flaps."""

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
    assert [w.code for w in ctx.warnings] == []


async def test_a_flap_deflected_in_the_document_does_not_reach_the_manoeuvring_speed() -> None:
    """Through the engine the optimiser gets the airplane at rest: a 45 deg flap in the document
    changes neither the problem nor the value, and the result says the deflection was ignored."""
    deflected = document(True)
    deflected["wings"]["Main"]["x_secs"][0]["trailing_edge_device"]["deflection_deg"] = 45.0
    given = AircraftInput.model_validate(
        {"airplane": deflected, "values": {"aircraft-mass": MASS, "altitude": 0.0}}
    )
    flapped = AirplaneGeometry.model_validate(deflected)
    opti = StubOpti()
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti)
    request = ComputeRequest(quantities=("maneuvering-speed",))
    result = await evaluate(shipped_build(), given, request, solvers=solvers)
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.OK, result
    (call,) = opti.calls
    assert call[0] == devices_at_rest(flapped)
    assert call[0] != flapped
    clean, _ = await run("maneuvering-speed")
    assert quantity.value == clean.quantities[0].value
    codes = {w.code for w in quantity.warnings}
    assert "geometry_deflection_ignored" in codes
    assert not {code for code in codes if code.startswith("flap_")}
