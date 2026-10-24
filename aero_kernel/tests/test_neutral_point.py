"""neutral-point (three worlds, A11) and static-margin through the engine; the AVL world is a stub."""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError, ToolRunTimeoutError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    KernelWarning,
    QuantityResult,
    QuantityStatus,
    WarningSeverity,
)
from aero_kernel.solvers.opti import BestGlide
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.np_builders import CONVENTIONAL, StubAvl, airplane_with
from aero_kernel.tests.stall_stubs import CD0, K, StubOpti

pytestmark = pytest.mark.asyncio

RHO, MASS, CG = 1.225, 1.5, 0.12
S_W, S_H, AR_W, AR_H = 0.28, 0.04, 7.0, 4.0
X_AC_W, X_AC_H, C_MAC = 0.10, 0.625, 0.2
WEIGHT_AT_G = MASS * 9.80665

# Hand values. Textbook (Sadraey Eq. 6.67, eta = 0.9): K = 0.9 (1 - 4/9) (4/6) / (7/9) = 3/7;
# x_NP = (0.28 * 0.10 + 3/7 * 0.04 * 0.625) / (0.28 + 3/7 * 0.04) = 0.0387142857 / 0.2971428571.
K_TEXTBOOK = 0.9 * (1 - 4 / (AR_W + 2)) * (AR_H / (AR_H + 2)) / (AR_W / (AR_W + 2))
X_NP_TEXTBOOK = (S_W * X_AC_W + K_TEXTBOOK * S_H * X_AC_H) / (S_W + K_TEXTBOOK * S_H)
# Pappas (10/2009): K = (1 - 3.24/7) (1/(1+2/4)) / (1/(1+2/7)) = 0.5371429 * 6/7.
K_PAPPAS = (1 - 3.24 / AR_W) * (1 / (1 + 2 / AR_H)) / (1 / (1 + 2 / AR_W))
X_NP_PAPPAS = (S_W * X_AC_W + K_PAPPAS * S_H * X_AC_H) / (S_W + K_PAPPAS * S_H)
X_NP_AVL = 0.14


async def run(
    *slugs: str,
    airplane: AirplaneGeometry | None = None,
    avl: StubAvl | None = None,
    opti: StubOpti | None = None,
    cg: float | None = None,
) -> tuple[ComputeResult, StubAvl]:
    stub = avl or StubAvl(X_NP_AVL)
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti or StubOpti(), avl=stub)
    values = {"aircraft-mass": MASS, "altitude": 0.0}
    if cg is not None:
        values["centre-of-gravity"] = cg
    aircraft = AircraftInput.model_validate(
        {"airplane": airplane or airplane_with(*CONVENTIONAL), "values": values}
    )
    result = await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=slugs), solvers=solvers
    )
    return result, stub


def only(result: ComputeResult) -> QuantityResult:
    (quantity,) = result.quantities
    return quantity


async def test_the_three_worlds_give_the_interval_with_the_hand_values() -> None:
    quantity = only((await run("neutral-point"))[0])
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    assert quantity.unit == "m"
    worlds = quantity.interval.worlds
    assert set(worlds) == {
        "neutral-point=textbook",
        "neutral-point=pappas",
        "neutral-point=avl",
    }
    assert close(worlds["neutral-point=textbook"], X_NP_TEXTBOOK, 1e-12)
    assert close(worlds["neutral-point=pappas"], X_NP_PAPPAS, 1e-12)
    assert worlds["neutral-point=avl"] == X_NP_AVL
    assert quantity.interval.min == min(worlds.values())
    assert quantity.interval.max == max(worlds.values())
    assert 0.13028 < X_NP_TEXTBOOK < 0.13029  # 0.0387142857 / 0.2971428571
    assert abs(K_TEXTBOOK - 3 / 7) < 1e-12


async def test_the_avl_world_is_asked_for_the_lift_coefficient_at_the_minimum_drag_speed() -> None:
    """C_L = m g / (1/2 rho V_md^2 S_ref) with the kernel's S_ref: on the stub's parabolic polar
    V_md = sqrt(2 W / (rho S)) (k / CD0)^(1/4), so C_L = sqrt(CD0 / k)."""
    _, avl = await run("neutral-point")
    ((airplane, cl),) = avl.calls
    assert close(cl, math.sqrt(CD0 / K), 1e-12)
    assert isinstance(airplane, AirplaneGeometry)


async def test_the_avl_world_adds_no_regime_warning_of_its_own() -> None:
    """The regime warnings come with V_md and are inherited; the AVL adapter's list is empty here."""
    regime = KernelWarning.of("reynolds_bubble_sensitive", "low Re", detail={"wing": "W"})

    class Warned(StubOpti):
        async def best_glide(self, *args: Any) -> BestGlide:  # type: ignore[override]
            glide = await super().best_glide(*args)
            return BestGlide(solution=glide.solution, warnings=(regime,))

    opti = Warned()
    quantity = only((await run("neutral-point", opti=opti))[0])
    codes = [w.code for w in quantity.warnings]
    assert codes.count("reynolds_bubble_sensitive") == 1  # inherited once, not per world
    assert "avl_mesh_not_converged" not in codes


async def test_every_world_carries_the_fuselage_warning_and_so_does_the_static_margin() -> None:
    quantity = only((await run("neutral-point"))[0])
    fuselage = [w for w in quantity.warnings if w.code == "fuselage_not_modelled"]
    assert sorted(str(w.world) for w in fuselage) == [
        "neutral-point=avl",
        "neutral-point=pappas",
        "neutral-point=textbook",
    ]
    assert all(
        w.severity is WarningSeverity.DEFECT and w.origin == "neutral-point" for w in fuselage
    )
    assert all(not w.detail for w in fuselage)
    margin = only((await run("static-margin", cg=CG))[0])
    assert len([w for w in margin.warnings if w.code == "fuselage_not_modelled"]) == 3


async def test_the_static_margin_is_an_interval_per_world() -> None:
    quantity = only((await run("static-margin", cg=CG))[0])
    assert quantity.interval is not None
    assert quantity.unit == "1"
    expected = {
        "neutral-point=textbook": (X_NP_TEXTBOOK - CG) / C_MAC,
        "neutral-point=pappas": (X_NP_PAPPAS - CG) / C_MAC,
        "neutral-point=avl": (X_NP_AVL - CG) / C_MAC,
    }
    for key, value in expected.items():
        assert close(quantity.interval.worlds[key], value, 1e-12), key


async def test_a_missing_centre_of_gravity_is_a_missing_input() -> None:
    quantity = only((await run("static-margin"))[0])
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "missing_input"
    assert quantity.error.input_path == "values.centre-of-gravity"


@pytest.mark.parametrize(
    ("layout", "found"),
    [
        (("main_wing",), ["main_wing"]),  # tailless
        (("main_wing", "canard"), ["canard", "main_wing"]),
        (("main_wing", "tandem_wing"), ["main_wing", "tandem_wing"]),
        (("main_wing", "v_tail"), ["main_wing", "v_tail"]),
        (("main_wing", "horizontal_tail", "canard"), ["canard", "horizontal_tail", "main_wing"]),
        (("main_wing", "horizontal_tail", "v_tail"), ["horizontal_tail", "main_wing", "v_tail"]),
        (
            ("main_wing", "horizontal_tail", "horizontal_tail"),
            ["horizontal_tail", "horizontal_tail", "main_wing"],
        ),
    ],
)
async def test_a_layout_outside_one_main_wing_and_one_horizontal_tail_is_refused(
    layout: tuple[str, ...], found: list[str]
) -> None:
    result, avl = await run("neutral-point", airplane=airplane_with(*layout))
    quantity = only(result)
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert (quantity.error.category, quantity.error.code) == (
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_layout",
    )
    assert quantity.error.detail["surface_types"] == found
    assert avl.calls == []  # AVL is never started for a refused layout
    assert quantity.error.detail["worlds_ok"] == {}


async def test_fins_and_winglets_are_allowed_beside_the_main_wing_and_the_tail() -> None:
    airplane = airplane_with("main_wing", "horizontal_tail", "vertical_tail", "winglet")
    quantity = only((await run("neutral-point", airplane=airplane))[0])
    assert quantity.status is QuantityStatus.OK


async def test_the_layout_is_decided_by_surface_type_not_by_planform() -> None:
    """A tail-shaped wing typed main_wing and a wing-shaped one typed horizontal_tail: the types
    decide, so the small surface is the 'main wing' of the barycentre."""
    swapped = AirplaneGeometry.model_validate(
        {
            "name": "swapped",
            "wings": {
                "big": {
                    "name": "big",
                    "symmetric": True,
                    "surface_type": "horizontal_tail",
                    "x_secs": [
                        {
                            "xyz_le": [0.05, y, 0.0],
                            "chord": 0.2,
                            "twist": 0.0,
                            "airfoil": "naca0012",
                        }
                        for y in (0.0, 0.7)
                    ],
                },
                "small": {
                    "name": "small",
                    "symmetric": True,
                    "surface_type": "main_wing",
                    "x_secs": [
                        {"xyz_le": [0.6, y, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
                        for y in (0.0, 0.2)
                    ],
                },
            },
        }
    )
    quantity = only((await run("neutral-point", airplane=swapped))[0])
    assert quantity.interval is not None
    # main = the small surface (AR 4, x_ac 0.625), tail = the big one (AR 7, x_ac 0.10)
    k = 0.9 * (1 - 4 / (4 + 2)) * (7 / (7 + 2)) / (4 / (4 + 2))
    expected = (0.04 * 0.625 + k * 0.28 * 0.10) / (0.04 + k * 0.28)
    assert close(quantity.interval.worlds["neutral-point=textbook"], expected, 1e-12)


async def test_a_failing_avl_world_is_an_error_with_the_values_that_computed() -> None:
    avl = StubAvl(X_NP_AVL)
    avl.failure = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "avl failed", "retry")
    quantity = only((await run("neutral-point", avl=avl))[0])
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.interval is None
    assert quantity.error is not None
    assert (quantity.error.code, quantity.error.world) == ("not_converged", "neutral-point=avl")
    worlds_ok = quantity.error.detail["worlds_ok"]
    assert isinstance(worlds_ok, dict)
    assert set(worlds_ok) == {"neutral-point=textbook", "neutral-point=pappas"}
    textbook = worlds_ok["neutral-point=textbook"]
    assert isinstance(textbook, float)
    assert close(textbook, X_NP_TEXTBOOK, 1e-12)


async def test_the_avl_adapter_warnings_are_forwarded_in_the_avl_world_only() -> None:
    mesh = KernelWarning.of("avl_mesh_not_converged", "mesh", detail={"delta_mac": 0.01})
    quantity = only((await run("neutral-point", avl=StubAvl(X_NP_AVL, warnings=(mesh,))))[0])
    forwarded = [w for w in quantity.warnings if w.code == "avl_mesh_not_converged"]
    assert [w.world for w in forwarded] == ["neutral-point=avl"]


async def test_an_avl_run_that_exceeds_its_limit_is_a_timeout_error_with_the_values_that_computed() -> (
    None
):
    avl = StubAvl(X_NP_AVL)
    avl.failure = ToolRunTimeoutError("the vortex lattice run", 120.0)
    quantity = only((await run("neutral-point", avl=avl))[0])
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert (quantity.error.category, quantity.error.code) == (ErrorCategory.TIMEOUT, "timeout")
    assert quantity.error.world == "neutral-point=avl"
    assert quantity.error.detail["run_limit_s"] == 120.0
    assert set(quantity.error.detail["worlds_ok"]) == {  # type: ignore[arg-type]
        "neutral-point=textbook",
        "neutral-point=pappas",
    }
