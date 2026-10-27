"""static-margin-probe: SM = -C_m,alpha / C_L,alpha from AeroBuildup about the design CG (fast tier, OPT stubbed)."""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context, Value
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.static_margin_probe import static_margin_probe
from aero_kernel.schema import AircraftInput, ComputeRequest, QuantityStatus, WarningSeverity
from aero_kernel.solvers.air import AirState
from aero_kernel.tests.chain_builders import C_MAC, SM_TARGET, WORLD_X_NP, document, run_chain
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    all_near,
    close,
    context_with,
    solvers_with,
)
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import StubOpti, consistent_glide
from aero_kernel.tests.test_neutral_point import MASS, RHO

pytestmark = pytest.mark.asyncio

GRAVITY = 9.80665
AIR = AirState(density=RHO, dynamic_viscosity=STUB_VISCOSITY, speed_of_sound=STUB_SPEED_OF_SOUND)


async def test_the_probe_is_the_slope_ratio_about_the_design_cg_in_every_world() -> None:
    """A stub whose neutral point is the AVL world's: the AVL world's probe is the target exactly,
    the other worlds differ by their neutral point's offset in chords."""
    opti = StubOpti()
    opti.probe_x_np = WORLD_X_NP["neutral-point=avl"]
    run = await run_chain("static-margin-probe", "pitching-moment-slope", opti=opti)
    probe = run.quantity("static-margin-probe")
    assert probe.status is QuantityStatus.OK
    assert probe.interval is not None
    assert set(probe.interval.worlds) == set(WORLD_X_NP)
    for world, x_np in WORLD_X_NP.items():
        x_cg = x_np - SM_TARGET * C_MAC
        expected = (opti.probe_x_np - x_cg) / C_MAC
        assert close(probe.interval.worlds[world], expected, 1e-12), world
    assert close(probe.interval.worlds["neutral-point=avl"], SM_TARGET, 1e-12)


async def test_the_moment_slope_is_reported_with_its_unit() -> None:
    run = await run_chain("pitching-moment-slope")
    slope = run.quantity("pitching-moment-slope")
    assert slope.unit == "1/rad"
    assert slope.interval is not None
    assert all(value < 0.0 for value in slope.interval.worlds.values())


async def test_the_adapter_is_asked_at_v_md_with_the_design_cg_as_the_moment_reference() -> None:
    run = await run_chain("static-margin-probe")
    plane = run.opti.probe_calls[0][0]
    v_md = consistent_glide(plane, MASS, GRAVITY, 1.0, AIR).v_md
    reference_x = sorted(call[5] for call in run.opti.probe_calls)
    expected = sorted(x_np - SM_TARGET * C_MAC for x_np in WORLD_X_NP.values())
    assert all_near(reference_x, expected)
    for _, mass, gravity, air, speed, _ in run.opti.probe_calls:
        assert (mass, gravity, air) == (MASS, GRAVITY, AIR)
        assert close(speed, v_md, 1e-9)


def probe_inputs(x_cg: float = 0.12) -> dict[str, Value | None]:
    return {
        "airplane": document(),
        "m": MASS,
        "g": GRAVITY,
        "rho": RHO,
        "mu": STUB_VISCOSITY,
        "a": STUB_SPEED_OF_SOUND,
        "v_md": 12.0,
        "x_cg": x_cg,
        "sm_target": SM_TARGET,
    }


async def call_probe(x_np: float, x_cg: float = 0.12) -> tuple[dict[str, float], Context]:
    """The formula about ``x_cg`` with a stub whose neutral point is ``x_np``; hand value (x_np - x_cg) / c_MAC."""
    opti = StubOpti()
    opti.probe_x_np = x_np
    context = context_with(StubAtmosphere({}), opti=opti)
    return await static_margin_probe(probe_inputs(x_cg), context), context


async def test_a_probe_that_agrees_carries_only_the_declared_bias() -> None:
    """Target 0.08 at x_cg 0.12 m, c_MAC 0.2 m: x_NP 0.136 m gives exactly 0.08."""
    found, context = await call_probe(0.12 + SM_TARGET * C_MAC)
    assert close(found["sm_probe"], SM_TARGET, 1e-12)
    assert [w.code for w in context.warnings] == ["aerobuildup_no_downwash"]
    assert context.warnings[0].severity is WarningSeverity.PRACTICE


async def test_a_probe_beyond_the_tolerance_is_declared_and_the_value_stays() -> None:
    """x_NP 0.20 m ahead of the agreeing one: the probe reads 1.0 less margin, far beyond 0.05."""
    found, context = await call_probe(0.12 + SM_TARGET * C_MAC - 0.2)
    assert close(found["sm_probe"], SM_TARGET - 1.0, 1e-12)
    codes = [w.code for w in context.warnings]
    assert codes == ["aerobuildup_no_downwash", "static_margin_probe_disagrees"]
    disagreement = context.warnings[1]
    assert disagreement.severity is WarningSeverity.DEFECT
    assert disagreement.detail["agreement_tolerance"] == 0.05
    assert disagreement.detail["sm_target"] == SM_TARGET
    assert close(float(disagreement.detail["deviation"]), -1.0, 1e-9)  # pyright: ignore[reportArgumentType]


async def test_a_deviation_just_inside_the_tolerance_is_not_declared() -> None:
    """0.04 of the chord off: inside 0.05 (the boundary is `at most`)."""
    _, context = await call_probe(0.12 + SM_TARGET * C_MAC + 0.04 * C_MAC)
    assert [w.code for w in context.warnings] == ["aerobuildup_no_downwash"]


async def test_a_deviation_just_beyond_the_tolerance_is_declared() -> None:
    _, context = await call_probe(0.12 + SM_TARGET * C_MAC + 0.06 * C_MAC)
    assert "static_margin_probe_disagrees" in [w.code for w in context.warnings]


async def test_the_override_of_the_tolerance_is_used_and_declared_in_the_provenance() -> None:
    opti = StubOpti()
    opti.probe_x_np = WORLD_X_NP["neutral-point=avl"] + 0.005
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}),
        opti=opti,
        avl=StubAvl(WORLD_X_NP["neutral-point=avl"]),
    )
    aircraft = AircraftInput.model_validate(
        {
            "airplane": document(),
            "values": {"aircraft-mass": MASS, "altitude": 0.0, "static-margin-target": SM_TARGET},
            "rule_overrides": {"static-margin-probe-agreement.agreement_tolerance": 0.001},
        }
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        ComputeRequest(quantities=("static-margin-probe",)),
        solvers=solvers,
    )
    (probe,) = result.quantities
    assert [w.code for w in probe.warnings].count("static_margin_probe_disagrees") >= 1
    used = {(r.rule, r.parameter): r for r in result.provenance.rules_used}
    assert used["static-margin-probe-agreement", "agreement_tolerance"].overridden is True


async def test_an_adapter_failure_is_the_quantitys_error() -> None:
    opti = StubOpti()
    opti.probe_failure = FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "no lift balance", "x"
    )
    probe = (await run_chain("static-margin-probe", opti=opti)).quantity("static-margin-probe")
    assert probe.status is QuantityStatus.ERROR
    assert probe.error is not None
    assert probe.error.code == "not_converged"
