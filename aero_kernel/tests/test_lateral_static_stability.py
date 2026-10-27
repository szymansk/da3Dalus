"""lateral-static-stability-md/-app/-mp: AVL derivatives, spiral criterion and time at three speeds (fast tier)."""

import math
from typing import Any

import pytest
from aero_kernel.context import Context, Value
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.lateral_static_stability_md import lateral_static_stability_md
from aero_kernel.schema import KernelWarning, QuantityStatus, WarningSeverity
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.avl import AvlLateral
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.chain_builders import C_MAC, SM_TARGET, WORLD_X_NP, document, run_chain
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    StubGeometry,
    all_near,
    close,
    solvers_with,
)
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, consistent_glide, consistent_min_sink
from aero_kernel.tests.test_neutral_point import MASS, RHO, X_NP_AVL

pytestmark = pytest.mark.asyncio

GRAVITY = 9.80665
AIR = AirState(density=RHO, dynamic_viscosity=STUB_VISCOSITY, speed_of_sound=STUB_SPEED_OF_SOUND)
S_REF = 0.28
# The stub's derivatives (StubAvl.lateral): E = (-0.05)(-0.06) - (0.07)(0.11) = -0.0047 (unstable),
# D = (-0.05)(-0.04) - (0.07)(-0.55) = 0.0405, lambda_s = -(g/V) E / D.
E_UNSTABLE = -0.05 * -0.06 - 0.07 * 0.11
DENOMINATOR = -0.05 * -0.04 - 0.07 * -0.55
OUTPUTS = {
    "md": (
        "dihedral-effect-md",
        "weathercock-stability-md",
        "spiral-criterion-md",
        "spiral-doubling-time-md",
    ),
    "app": (
        "dihedral-effect-app",
        "weathercock-stability-app",
        "spiral-criterion-app",
        "spiral-doubling-time-app",
    ),
    "mp": (
        "dihedral-effect-mp",
        "weathercock-stability-mp",
        "spiral-criterion-mp",
        "spiral-doubling-time-mp",
    ),
}


def time_unstable(speed: float) -> float:
    return math.log(2.0) / (-(GRAVITY / speed) * E_UNSTABLE / DENOMINATOR)


def speeds() -> dict[str, float]:
    plane = document()
    area = stand_in_main_wing_properties(plane).s_ref
    v_s = math.sqrt(2.0 * MASS * GRAVITY / (RHO * area * UPRIGHT_PEAK[1]))
    return {
        "md": consistent_glide(plane, MASS, GRAVITY, 1.0, AIR).v_md,
        "mp": consistent_min_sink(plane, MASS, GRAVITY, 1.0, AIR).v_mp,
        "app": 1.3 * v_s,
    }


@pytest.mark.parametrize("point", ["md", "app", "mp"])
async def test_the_outputs_at_each_point_are_the_hand_values_in_every_world(point: str) -> None:
    speed = speeds()[point]
    run = await run_chain(*OUTPUTS[point])
    beta, weathercock, criterion, time = (run.quantity(slug) for slug in OUTPUTS[point])
    for quantity in (beta, weathercock, criterion, time):
        assert quantity.status is QuantityStatus.OK, quantity
        assert quantity.interval is not None
        assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    assert beta.unit == "1/rad"
    assert time.unit == "s"
    for world in WORLD_X_NP:
        assert beta.interval.worlds[world] == -0.05  # type: ignore[union-attr]
        assert weathercock.interval.worlds[world] == 0.07  # type: ignore[union-attr]
        assert close(criterion.interval.worlds[world], E_UNSTABLE, 1e-12)  # type: ignore[union-attr]
        assert close(time.interval.worlds[world], time_unstable(speed), 1e-12)  # type: ignore[union-attr]


@pytest.mark.parametrize("point", ["md", "app", "mp"])
async def test_avl_runs_at_the_lift_balance_of_its_speed_about_each_worlds_design_cg(
    point: str,
) -> None:
    speed = speeds()[point]
    run = await run_chain(OUTPUTS[point][0])
    expected_cl = MASS * GRAVITY / (0.5 * RHO * speed**2 * S_REF)
    expected_x = sorted(x_np - SM_TARGET * C_MAC for x_np in WORLD_X_NP.values())
    assert len(run.avl.lateral_calls) >= len(WORLD_X_NP)
    lateral = run.avl.lateral_calls
    assert all_near(sorted({round(x, 12) for _, _, x in lateral}), expected_x, 1e-9)
    for _, cl, _ in lateral:
        assert close(cl, expected_cl, 1e-9)


async def test_only_the_minimum_sink_point_outputs_the_roll_derivative_with_yaw_rate() -> None:
    """Maintainer decision 2026-10-27 (#1275): C_l,r at V_mp for the turn sideslip, from the same AVL run."""
    run = await run_chain("roll-due-to-yaw-rate-mp")
    quantity = run.quantity("roll-due-to-yaw-rate-mp")
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    assert all(value == 0.11 for value in quantity.interval.worlds.values())
    md = await lateral_static_stability_md(inputs(), context(StubAvl(X_NP_AVL)))
    assert set(md) == {"c_l_beta", "c_n_beta", "e_spiral", "t2_spiral"}


async def test_a_stable_spiral_reports_the_halving_time_negative_and_declares_it() -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral = AvlLateral(
        c_l_beta=-0.05, c_n_beta=0.07, c_l_p=-0.55, c_n_p=-0.04, c_l_r=0.11, c_n_r=-0.3
    )
    run = await run_chain("spiral-criterion-md", "spiral-doubling-time-md", avl=avl)
    criterion, time = run.quantity("spiral-criterion-md"), run.quantity("spiral-doubling-time-md")
    e_stable = -0.05 * -0.3 - 0.07 * 0.11
    assert e_stable > 0.0
    speed = speeds()["md"]
    root = -(GRAVITY / speed) * e_stable / DENOMINATOR
    assert root < 0.0
    assert criterion.interval is not None
    assert time.interval is not None
    for world in WORLD_X_NP:
        assert close(criterion.interval.worlds[world], e_stable, 1e-12)
        assert close(time.interval.worlds[world], -math.log(2.0) / abs(root), 1e-12)
    halving = [w for w in time.warnings if w.code == "spiral_halving_time_reported"]
    assert halving
    assert halving[0].severity is WarningSeverity.PRACTICE
    assert close(float(halving[0].detail["lambda_s"]), root, 1e-12)  # pyright: ignore[reportArgumentType]


async def test_an_unstable_spiral_has_no_halving_declaration() -> None:
    run = await run_chain("spiral-doubling-time-md")
    time = run.quantity("spiral-doubling-time-md")
    assert time.interval is not None
    assert time.interval.min > 0.0
    assert "spiral_halving_time_reported" not in [w.code for w in time.warnings]


async def test_the_avl_caveats_are_forwarded() -> None:
    caveat = KernelWarning.of("avl_body_equivalent_round", "round body", detail={"bodies": []})
    avl = StubAvl(X_NP_AVL, warnings=(caveat,))
    run = await run_chain("dihedral-effect-md", avl=avl)
    assert "avl_body_equivalent_round" in [
        w.code for w in run.quantity("dihedral-effect-md").warnings
    ]


def inputs(**overrides: float) -> dict[str, Value | None]:
    given: dict[str, Value | None] = {
        "airplane": document(),
        "m": MASS,
        "g": GRAVITY,
        "rho": RHO,
        "x_cg": 0.12,
        "v": 12.0,
    }
    given.update(overrides)
    return given


def context(avl: StubAvl) -> Context:
    return Context(
        origin="t",
        solvers=solvers_with(atmosphere=StubAtmosphere({}), avl=avl, geometry=StubGeometry()),
    )


@pytest.mark.parametrize(
    ("derivatives", "match"),
    [
        (
            {
                "c_l_beta": -0.05,
                "c_n_beta": 0.0,
                "c_l_p": -0.55,
                "c_n_p": -0.04,
                "c_l_r": 0.11,
                "c_n_r": 0.0,
            },
            "criterion is zero",
        ),
        (
            {
                "c_l_beta": 0.0,
                "c_n_beta": 0.0,
                "c_l_p": -0.55,
                "c_n_p": -0.04,
                "c_l_r": 0.11,
                "c_n_r": -0.06,
            },
            "is zero",
        ),
    ],
)
async def test_a_spiral_without_a_finite_time_is_refused(
    derivatives: dict[str, Any], match: str
) -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral = AvlLateral(**derivatives)
    with pytest.raises(FormulaError, match=match) as raised:
        await lateral_static_stability_md(inputs(), context(avl))
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_zero_denominator_with_a_non_zero_criterion_is_refused() -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral = AvlLateral(
        c_l_beta=-0.05, c_n_beta=0.0, c_l_p=-0.55, c_n_p=0.0, c_l_r=0.11, c_n_r=-0.06
    )
    with pytest.raises(FormulaError, match="C_l,beta C_n,p") as raised:
        await lateral_static_stability_md(inputs(), context(avl))
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_lift_coefficient_that_is_not_positive_is_invalid_input() -> None:
    with pytest.raises(FormulaError) as raised:
        await lateral_static_stability_md(inputs(m=0.0), context(StubAvl(X_NP_AVL)))
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_an_adapter_failure_is_the_quantitys_error() -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral_failure = FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "avl_array_limit", "too fine", "coarser"
    )
    quantity = (await run_chain("dihedral-effect-md", avl=avl)).quantity("dihedral-effect-md")
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "avl_array_limit"
