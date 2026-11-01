"""aerobuildup-evaluation: L, D := AeroBuildup(airplane, OperatingPoint(V, alpha, atmosphere)).

Fast tier: the formula against a stub optimiser, and through the engine on the shipped canon.
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Value
from aero_kernel.formulas.aerobuildup_evaluation import aerobuildup_evaluation
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning, QuantityStatus
from aero_kernel.solvers.opti import Evaluation, Forces
from aero_kernel.tests.formula_builders import (
    OPT_SETTINGS,
    StubAtmosphere,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.stall_stubs import DRAG_N, LIFT_N, StubOpti
from aero_kernel.tests.test_stall_speed_engine import RHO, by_slug, run
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
POINT = {"flight-speed": 10.0, "angle-of-attack": 4.0}


def inputs() -> dict[str, Value]:
    return inputs_from_model(
        MODEL,
        "aerobuildup-evaluation",
        {
            "airplane": AirplaneGeometry.model_validate(airplane_document()),
            "flight-speed": 10.0,
            "angle-of-attack": 4.0,
            "air-density": 1.2,
            "dynamic-viscosity": 1.8e-5,
            "speed-of-sound": 340.0,
        },
    )


async def test_the_formula_returns_the_adapters_forces_and_names_them() -> None:
    stub = StubOpti()
    result = await aerobuildup_evaluation(inputs(), context_with(StubAtmosphere({}), opti=stub))
    assert result == {"l": LIFT_N, "d": DRAG_N}
    ((_, air, v, alpha),) = stub.evaluate_calls
    assert (v, alpha) == (10.0, 4.0)
    assert (air.density, air.dynamic_viscosity, air.speed_of_sound) == (1.2, 1.8e-5, 340.0)


async def test_the_adapters_caveats_become_the_formulas_warnings() -> None:
    class Caveated(StubOpti):
        async def evaluate(
            self, airplane: AirplaneGeometry, air: object, v_ms: float, alpha_deg: float
        ) -> Evaluation:
            warning = KernelWarning.of("reynolds_bubble_sensitive", "low Re", detail={"re": 5e4})
            return Evaluation(forces=Forces(lift_n=1.0, drag_n=0.1), warnings=(warning,))

    context = context_with(StubAtmosphere({}), opti=Caveated(), origin="lift-force")
    await aerobuildup_evaluation(inputs(), context)
    (warning,) = context.warnings
    assert (warning.code, warning.origin) == ("reynolds_bubble_sensitive", "lift-force")


async def test_lift_and_drag_force_through_the_engine_at_the_callers_point() -> None:
    result, opti = await run("lift-force", "drag-force", values=POINT)
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert quantities["lift-force"].value == LIFT_N
    assert quantities["drag-force"].value == DRAG_N
    assert {q.unit for q in quantities.values()} == {"N"}
    assert {q.tool for q in quantities.values()} == {"AB"}
    assert len(opti.evaluate_calls) == 1  # two outputs, one evaluation
    (_, air, v, alpha) = opti.evaluate_calls[0]
    assert (v, alpha, air.density) == (10.0, 4.0, RHO)


async def test_the_provenance_names_the_optimiser_that_runs_aerobuildup() -> None:
    """Tool AB is run by the OPT adapter (ADR 0022): its versions and settings are declared."""
    result, _ = await run("lift-force", values=POINT)
    assert set(result.provenance.tool_versions) == {"aerosandbox", "neuralfoil"}
    assert result.provenance.solver_settings == OPT_SETTINGS


async def test_without_an_angle_of_attack_there_is_no_value() -> None:
    result, opti = await run("lift-force", values={"flight-speed": 10.0})
    (quantity,) = result.quantities
    assert quantity.status is not QuantityStatus.OK
    assert quantity.value is None
    assert opti.evaluate_calls == []
