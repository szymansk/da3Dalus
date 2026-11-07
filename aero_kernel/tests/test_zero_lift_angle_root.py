"""zero-lift-angle: the root of C_L(V, alpha) and dC_L/dalpha there, at V_md and V_mp.

Fast tier: the formula against a stub optimiser, and both applications through the engine on the
shipped canon (each binds the speed of its optimum).
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Value
from aero_kernel.formulas.zero_lift_angle import zero_lift_angle
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning, QuantityStatus
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import ZeroLift, ZeroLiftSolution
from aero_kernel.tests.formula_builders import (
    OPT_SETTINGS,
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.stall_stubs import StubOpti, stub_zero_lift
from aero_kernel.tests.test_minimum_drag_speed_engine import V_MD
from aero_kernel.tests.test_stall_speed_engine import RHO, by_slug, run
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
V_MP = V_MD / 3.0**0.25  # the stub's parabolic polar: V_mp = V_md / 3^(1/4)


def inputs(application: str) -> dict[str, Value]:
    speed = "minimum-drag-speed" if application == "best_glide" else "minimum-sink-speed"
    return inputs_from_model(
        MODEL,
        "zero-lift-angle",
        {
            "airplane": AirplaneGeometry.model_validate(airplane_document()),
            speed: 9.0,
            "air-density": 1.2,
            "dynamic-viscosity": 1.8e-5,
            "speed-of-sound": 340.0,
        },
        application=application,
    )


@pytest.mark.parametrize("application", ["best_glide", "minimum_sink"])
async def test_the_formula_returns_the_root_and_the_slope_at_the_bound_speed(
    application: str,
) -> None:
    stub = StubOpti()
    context = context_with(StubAtmosphere({}), opti=stub)
    result = await zero_lift_angle(inputs(application), context)
    expected = stub_zero_lift(9.0)
    assert result == {"alpha_0": expected.alpha_0_deg, "cl_alpha": expected.cl_alpha_per_rad}
    ((_, air, v),) = stub.zero_lift_calls
    assert v == 9.0
    assert (air.density, air.dynamic_viscosity, air.speed_of_sound) == (1.2, 1.8e-5, 340.0)


async def test_the_adapters_caveats_become_the_formulas_warnings() -> None:
    class Caveated(StubOpti):
        async def zero_lift(
            self, airplane: AirplaneGeometry, air: AirState, v_ms: float
        ) -> ZeroLift:
            warning = KernelWarning.of("reynolds_outside_band", "low Re", detail={"re": 2e4})
            solution = ZeroLiftSolution(alpha_0_deg=-3.0, cl_alpha_per_rad=5.0)
            return ZeroLift(solution=solution, warnings=(warning,))

    context = context_with(StubAtmosphere({}), opti=Caveated(), origin="zero-lift-angle-best-glide")
    await zero_lift_angle(inputs("best_glide"), context)
    (warning,) = context.warnings
    assert (warning.code, warning.origin) == ("reynolds_outside_band", "zero-lift-angle-best-glide")


async def test_both_applications_through_the_engine_each_at_the_speed_of_its_optimum() -> None:
    slugs = (
        "zero-lift-angle-best-glide",
        "lift-curve-slope-best-glide",
        "zero-lift-angle-minimum-sink",
        "lift-curve-slope-minimum-sink",
    )
    result, opti = await run(*slugs)
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    at_md, at_mp = stub_zero_lift(V_MD), stub_zero_lift(V_MP)
    assert close(quantities["zero-lift-angle-best-glide"].value, at_md.alpha_0_deg, 1e-12)
    assert close(quantities["lift-curve-slope-best-glide"].value, at_md.cl_alpha_per_rad, 1e-12)
    assert close(quantities["zero-lift-angle-minimum-sink"].value, at_mp.alpha_0_deg, 1e-12)
    assert close(quantities["lift-curve-slope-minimum-sink"].value, at_mp.cl_alpha_per_rad, 1e-12)
    assert quantities["zero-lift-angle-best-glide"].unit == "deg"
    assert quantities["lift-curve-slope-best-glide"].unit == "1/rad"
    assert quantities["zero-lift-angle-best-glide"].application == "best_glide"
    assert quantities["zero-lift-angle-minimum-sink"].application == "minimum_sink"
    assert sorted(round(v, 9) for _, _, v in opti.zero_lift_calls) == sorted(
        round(v, 9) for v in (V_MD, V_MP)
    )  # one solve per application, two outputs each
    assert all(air.density == RHO for _, air, _ in opti.zero_lift_calls)


async def test_the_provenance_names_the_optimiser() -> None:
    result, _ = await run("zero-lift-angle-best-glide")
    assert set(result.provenance.tool_versions) == {"aerosandbox", "neuralfoil"}
    assert result.provenance.solver_settings == OPT_SETTINGS
