"""turn-sideslip: beta_turn = kappa r_hat_max, kappa = -C_l,r / C_l,beta, per neutral-point world (fast tier)."""

import math
from typing import Any

import pytest
from aero_kernel.context import Context
from aero_kernel.errors import ErrorCategory
from aero_kernel.formulas.turn_sideslip import dihedral_effect_stabilising, turn_sideslip
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import QuantityStatus
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.avl import AvlLateral
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.chain_builders import WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    StubGeometry,
    close,
    solvers_with,
)
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import consistent_min_sink
from aero_kernel.tests.test_neutral_point import MASS, RHO, X_NP_AVL

pytestmark = pytest.mark.asyncio

GRAVITY = 9.80665
AIR = AirState(density=RHO, dynamic_viscosity=STUB_VISCOSITY, speed_of_sound=STUB_SPEED_OF_SOUND)
# The stub's derivatives (StubAvl.lateral): C_l,beta = -0.05, C_l,r = 0.11, so kappa = 0.11 / 0.05 = 2.2.
KAPPA = 0.11 / 0.05


def hand_values() -> tuple[float, float]:
    """r_hat_max = rho g b C_L,mp / (8 W/S) and beta_turn in degrees, from the stubs' fixed numbers."""
    plane = document(fin())
    reference = stand_in_main_wing_properties(plane)
    cl_mp = consistent_min_sink(plane, MASS, GRAVITY, 1.0, AIR).cl_mp
    wing_loading = MASS * GRAVITY / reference.s_ref
    r_hat = RHO * GRAVITY * reference.b_ref * cl_mp / (8.0 * wing_loading)
    return r_hat, math.degrees(KAPPA * r_hat)


async def test_the_turn_sideslip_is_kappa_times_the_worst_turn_yaw_rate_in_degrees_per_world() -> (
    None
):
    run = await run_chain("turn-sideslip", "turn-sideslip-gain")
    beta, kappa = run.quantity("turn-sideslip"), run.quantity("turn-sideslip-gain")
    _, expected_beta = hand_values()
    for quantity in (beta, kappa):
        assert quantity.status is QuantityStatus.OK, quantity
        assert quantity.interval is not None
        assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    assert beta.unit == "deg"
    assert kappa.unit == "1"
    for world in WORLD_X_NP:
        assert close(beta.interval.worlds[world], expected_beta, 1e-12), world  # type: ignore[union-attr]
        assert close(kappa.interval.worlds[world], KAPPA, 1e-12), world  # type: ignore[union-attr]


async def test_the_derivatives_are_the_canon_quantities_of_one_avl_run_not_recomputed() -> None:
    """ADR 0022: C_l,beta and C_l,r are dihedral-effect-mp and roll-due-to-yaw-rate-mp, no AVL run of its own."""
    run = await run_chain("turn-sideslip", "dihedral-effect-mp", "roll-due-to-yaw-rate-mp")
    beta_calls = len(run.avl.lateral_calls)
    alone = await run_chain("dihedral-effect-mp", "roll-due-to-yaw-rate-mp")
    assert beta_calls == len(alone.avl.lateral_calls)


async def test_a_derivative_of_the_other_sign_follows_the_stub_into_kappa() -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral = AvlLateral(
        c_l_beta=-0.1, c_n_beta=0.07, c_l_p=-0.55, c_n_p=-0.04, c_l_r=0.05, c_n_r=-0.06
    )
    run = await run_chain("turn-sideslip-gain", avl=avl)
    quantity = run.quantity("turn-sideslip-gain")
    assert quantity.interval is not None
    assert all(close(value, 0.5, 1e-12) for value in quantity.interval.worlds.values())


@pytest.mark.parametrize("c_l_beta", [0.0, 0.02], ids=["zero", "positive"])
async def test_a_dihedral_effect_that_is_not_stabilising_is_the_declared_error(
    c_l_beta: float,
) -> None:
    avl = StubAvl(X_NP_AVL)
    avl.lateral = AvlLateral(
        c_l_beta=c_l_beta, c_n_beta=0.07, c_l_p=-0.55, c_n_p=-0.04, c_l_r=0.11, c_n_r=-0.06
    )
    run = await run_chain("turn-sideslip", avl=avl)
    quantity = run.quantity("turn-sideslip")
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "precondition_violated"
    assert quantity.error.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert quantity.error.detail["precondition"] == "dihedral_effect_stabilising"


def with_aileron() -> AirplaneGeometry:
    plane: Any = document(fin()).model_dump(mode="json", exclude_none=True)
    plane["wings"]["main"]["x_secs"][0]["trailing_edge_device"] = {"role": "aileron"}
    return AirplaneGeometry.model_validate(plane)


async def test_with_ailerons_the_sideslip_is_not_needed_and_does_not_apply() -> None:
    run = await run_chain("turn-sideslip", airplane=with_aileron())
    quantity = run.quantity("turn-sideslip")
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.interval is None
    assert quantity.reason is not None
    assert "has_no_aileron" in quantity.reason.message


@pytest.mark.parametrize(
    ("c_l_beta", "state"),
    [
        (-0.05, "held"),
        (-1e-9, "held"),
        (0.0, "violated"),
        (0.04, "violated"),
        (math.nan, "violated"),
    ],
)
async def test_the_precondition_holds_only_for_a_negative_dihedral_effect(
    c_l_beta: float, state: str
) -> None:
    result = dihedral_effect_stabilising({"c_l_beta": c_l_beta})
    assert result.state == state
    assert "C_l,beta" in result.message


async def test_the_formula_applies_the_worst_turn_to_the_given_derivatives() -> None:
    context = Context(
        origin="t",
        solvers=solvers_with(atmosphere=StubAtmosphere({}), geometry=StubGeometry()),
    )
    found = await turn_sideslip(
        {
            "rho": 1.0,
            "g": 10.0,
            "b_ref": 2.0,
            "w_s": 40.0,
            "c_l_mp": 1.0,
            "c_l_beta": -0.1,
            "c_l_r": 0.1,
        },
        context,
    )
    r_hat_max = 1.0 * 10.0 * 2.0 * 1.0 / (8.0 * 40.0)  # 0.0625
    assert close(found["kappa"], 1.0, 1e-12)
    assert close(found["beta_turn"], math.degrees(r_hat_max), 1e-12)
