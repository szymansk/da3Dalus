"""``motor-propeller-part-load``: battery power and current of level flight (route B).

The AeroBuildup boundary is a stub with a closed-form lift and drag (the solver itself is not what is
tested here): ``L(alpha) = 10 + 5 alpha`` N and ``D(alpha) = 2 + 0.05 alpha^2`` N. At m = 3.4 kg
(W = 33.3426 N) the lift balance gives ``alpha = 4.66852 deg`` and ``D = 3.0898 N``. The rest is
computed by a separately written plain-Python model and the published APC 13x8E table (T-Motor AT2814 KV900, 14.8 V,
rho = 1.225 kg/m^3, V = 10 m/s):

- thrust = drag: ``n_pl`` by bisection between the rpm blocks
- ``Q = C_P rho n^2 D^5 / 2 pi``, ``I = I_0 + Q K_v'``, ``U_m = I R_m + 2 pi n / K_v'``, ``P = U_m I``
"""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.context import Context
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_part_load import (
    demand_within_full_throttle,
    motor_propeller_part_load,
)
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import AircraftInput, KernelWarning, QuantityStatus
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import LevelFlightPoint, LevelPoint
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import (
    complete_components_with_table,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, inputs_from_model, solvers_with
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.wing_builders import airplane_document

RHO, D_PROP, U_BAT, V, MASS, G = 1.225, 13 * 0.0254, 14.8, 10.0, 3.4, 9.80665
KV, I0, RM = 900.0, 1.2, 0.082


class LinearOpti(StubOpti):
    """AeroBuildup stand-in for the level-flight solve: ``L = lift_0 + 5 alpha`` N, ``D = drag_0 + 0.05 alpha^2`` N.

    ``level_flight_point`` answers like the adapter: the angle where the lift equals the weight, or the
    adapter's declared ``not_converged`` if the lift cannot reach it (``lift_slope <= 0``).
    """

    def __init__(
        self,
        lift_0: float = 10.0,
        lift_slope: float = 5.0,
        drag_0: float = 2.0,
        warnings: tuple[KernelWarning, ...] = (),
    ) -> None:
        super().__init__()
        self.lift_0, self.lift_slope, self.drag_0, self.warnings = (
            lift_0,
            lift_slope,
            drag_0,
            warnings,
        )
        self.points: list[tuple[float, float, float, float]] = []

    async def level_flight_point(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        air: AirState,
        v_ms: float,
        n_load: float,
    ) -> LevelFlightPoint:
        assert math.isclose(n_load, 1.0)  # level flight
        weight = mass_kg * gravity
        self.points.append((mass_kg, gravity, air.density, v_ms))
        if self.lift_slope <= 0.0:
            raise FormulaError(
                ErrorCategory.NOT_CONVERGED,
                "not_converged",
                "the airplane does not reach the level lift below its main C_L peak",
                "check mass and speed",
                detail={"v_ms": v_ms},
            )
        alpha = (weight - self.lift_0) / self.lift_slope
        drag = self.drag_0 + 0.05 * alpha**2
        point = LevelPoint(v_ms=v_ms, alpha_deg=alpha, cl=0.5, cd=0.05, lift_n=weight, drag_n=drag)
        return LevelFlightPoint(point=point, warnings=self.warnings)


def context(opti: StubOpti) -> Context:
    formula = shipped_build().model.formula("motor-propeller-part-load")
    assert formula is not None
    relations = {item: DEFAULT_REGISTRY.relation_of(item.split(".")[0]) for item in formula.embeds}
    return Context(
        origin="t",
        solvers=solvers_with(opti=opti),
        relations={k: v for k, v in relations.items() if v is not None},
    )


def bound_inputs(**extra: Any) -> dict[str, Any]:
    by_quantity: dict[str, Any] = {
        "airplane": AirplaneGeometry.model_validate(airplane_document()),
        "aircraft-mass": MASS,
        "gravity": G,
        "air-density": RHO,
        "dynamic-viscosity": 1.8e-5,
        "speed-of-sound": 340.0,
        "components": complete_components_with_table(),
        "flight-speed": V,
        "motor-voltage-constant": KV,
        "motor-no-load-current": I0,
        "motor-circuit-resistance": RM,
        "battery-voltage": U_BAT,
        "motor-max-power": 650.0,
        "propeller-diameter": D_PROP,
        "motor-efficiency": 0.8,
    }
    by_quantity.update(extra)
    return inputs_from_model(shipped_build().model, "motor-propeller-part-load", by_quantity)


def independent(drag: float) -> tuple[float, float, float, float]:
    """``n_pl`` (1/s), ``I_bat``, ``P_bat`` and ``r_T`` from the independent computation."""
    point = reference.part_load(V, drag)
    return point.n_pl, point.i_bat, point.p_bat, point.r_t


@pytest.mark.asyncio
async def test_the_part_load_point_matches_the_independent_computation() -> None:
    opti = LinearOpti()
    ctx = context(opti)
    got = await motor_propeller_part_load(bound_inputs(), ctx)
    alpha = (MASS * G - 10.0) / 5.0
    drag = 2.0 + 0.05 * alpha**2
    n, i_bat, p_bat, r_t = independent(drag)
    assert close(got["n_pl"], n, 1e-7)
    assert close(got["p_bat"], p_bat, 1e-6)
    assert close(got["i_bat"], i_bat, 1e-6)
    assert close(got["r_t"], r_t, 1e-6)
    assert got["r_t"] < 1.0
    assert opti.points == [(MASS, G, RHO, V)]  # one level-flight solve at the speed
    assert [w.code for w in ctx.warnings] == ["powertrain_route_winding_resistance"]


@pytest.mark.asyncio
async def test_the_embedded_relations_are_the_ones_the_canon_lists() -> None:
    ctx = context(LinearOpti())
    await motor_propeller_part_load(bound_inputs(), ctx)
    formula = shipped_build().model.formula("motor-propeller-part-load")
    assert formula is not None
    assert set(ctx.embedded_requests) == set(formula.embeds)


@pytest.mark.asyncio
async def test_a_wing_that_cannot_carry_the_weight_is_not_converged() -> None:
    opti = LinearOpti(
        lift_slope=0.0
    )  # the adapter cannot reach the weight: its declared failure passes
    with pytest.raises(FormulaError) as caught:
        await motor_propeller_part_load(bound_inputs(), context(opti))
    assert caught.value.code == "not_converged"
    assert caught.value.detail["v_ms"] == V


@pytest.mark.asyncio
async def test_a_drag_beyond_the_table_is_a_declared_failure() -> None:
    with pytest.raises(FormulaError) as caught:
        await motor_propeller_part_load(bound_inputs(), context(LinearOpti(drag_0=1000.0)))
    assert caught.value.code == "outside_propeller_table"


@pytest.mark.asyncio
async def test_a_drag_above_the_full_throttle_thrust_is_computed_and_demand_is_above_one() -> None:
    ctx = context(LinearOpti(drag_0=26.5))
    got = await motor_propeller_part_load(bound_inputs(), ctx)
    assert got["r_t"] > 1.0
    verdict = demand_within_full_throttle({}, got)
    assert verdict.state == "violated"
    assert "cannot be held" in verdict.message


def test_a_demand_within_the_full_throttle_thrust_holds() -> None:
    assert demand_within_full_throttle({}, {"r_t": 0.4}).state == "held"
    assert demand_within_full_throttle({}, {"r_t": 1.0}).state == "held"


@pytest.mark.asyncio
async def test_an_absent_winding_resistance_is_missing_input_not_route_a() -> None:
    x = bound_inputs()
    x["r_m"] = None
    with pytest.raises(FormulaError) as caught:
        await motor_propeller_part_load(x, context(LinearOpti()))
    assert (caught.value.code, caught.value.parameter) == ("missing_input", "r_m")


@pytest.mark.asyncio
async def test_a_motor_whose_free_run_speed_is_below_the_table_has_no_balance() -> None:
    # a 40 V/rpm motor on 14.8 V turns 592 rpm: below the table, so the balance has no solution
    x = bound_inputs(**{"motor-voltage-constant": 40.0})
    with pytest.raises(FormulaError) as caught:
        await motor_propeller_part_load(x, context(LinearOpti()))
    assert caught.value.code == "outside_propeller_table"


@pytest.mark.asyncio
async def test_through_the_engine_the_four_quantities_and_the_route_notice() -> None:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "components": complete_components_with_table().model_dump(),
            "values": {"aircraft-mass": MASS, "altitude": 0.0, "flight-speed": V},
        }
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        request(
            "propeller-speed-part-load", "battery-current", "battery-power", "thrust-demand-ratio"
        ),
        solvers=solvers_with(opti=LinearOpti()),
    )
    got = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in got.values()), got
    assert got["battery-power"].unit == "W"
    assert got["battery-current"].unit == "A"
    assert got["thrust-demand-ratio"].unit == "1"
    assert got["propeller-speed-part-load"].unit == "1/s"
    for quantity in got.values():
        assert "powertrain_route_winding_resistance" in [w.code for w in quantity.warnings]
        assert "postcondition_violated" not in [w.code for w in quantity.warnings]
    assert close(got["battery-power"].value, independent(2.0 + 0.05 * 4.66852**2)[2], 1e-4)
    power = got["battery-power"].value
    assert power is not None
    assert close(got["battery-current"].value, power / U_BAT, 1e-12)


@pytest.mark.asyncio
async def test_a_motor_that_cannot_turn_the_propeller_to_positive_thrust_is_refused() -> None:
    # a flat table whose C_T is negative at 1000 rpm and positive at 20000 rpm; a 100 rpm/V motor on
    # 14.8 V stops at 1480 rpm, where the interpolated C_T is -0.0072: no thrust at full throttle
    document = complete_components_with_table().model_dump()
    point = {"j": [0.0, 1.0], "cp": [0.04, 0.04]}
    document["propeller"]["table"] = {
        "blocks": [
            {"rpm": 1000.0, "ct": [-0.01, -0.01], **point},
            {"rpm": 20000.0, "ct": [0.1, 0.1], **point},
        ]
    }
    x = bound_inputs(
        components=Components.model_validate(document),
        **{"motor-voltage-constant": 100.0, "flight-speed": 0.0},
    )
    with pytest.raises(FormulaError) as caught:
        await motor_propeller_part_load(x, context(LinearOpti(drag_0=0.05)))
    assert caught.value.code == "no_thrust_at_full_throttle"


def test_with_two_thrust_drag_crossings_the_part_load_speed_is_the_lowest() -> None:
    """Blocks 1200/2400/3600/4800 rpm, flat over J, C_T 0.05, 0.1, 0.02, 0.1, at V = 0.

    With the drag 100 rho D^4 the thrust minus the drag changes sign downward (thrust passes the
    drag) between 1200 and 2400 rpm and again between 3600 and 4800 rpm. The lowest crossing is
    the part-load speed (the lower throttle). In the unit rho D^4 the thrust is C_T n^2 with n in 1/s
    (blocks at 20, 40, 60, 80 1/s: 20, 160, 72, 640). Between the first two blocks
    C_T = 0.05 + 0.05 (n - 20) / 20 = 0.0025 n, so 0.0025 n^3 = 100, n = 40000^(1/3) = 34.1995 1/s
    = 2051.97 rpm.
    """
    from aero_kernel.formulas.motor_propeller_part_load import solve_part_load_speed
    from aero_kernel.tests.test_powertrain_chain import context_for
    from aero_kernel.tests.test_powertrain_edges import flat_table

    components = flat_table(
        (1200.0, 2400.0, 3600.0, 4800.0), (0.05, 0.1, 0.02, 0.1), (0.04, 0.04, 0.04, 0.04)
    )
    drag = 100.0 * RHO * D_PROP**4
    got = solve_part_load_speed(
        context_for("motor-propeller-part-load"), components, 0.0, RHO, D_PROP, drag
    )
    assert math.isclose(got, 40000.0 ** (1.0 / 3.0), rel_tol=1e-6)
    assert math.isclose(got * 60.0, 2051.97, rel_tol=1e-5)
