"""butterfly-approach: the crow sweep of the stall problem, on a stub optimiser (fast tier).

Direct calls of the formula for the curves (v1 carries scalars only), and the engine for the
conditions and the carried scalar ``butterfly-max-mix``.
"""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.devices import with_flaps_at
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.butterfly_approach import (
    approach_speed_positive,
    butterfly_approach,
    crow_aileron_not_negative,
    optimum_at_first_cl_peak,
)
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    Curve,
    KernelWarning,
    Polar,
    QuantityStatus,
    StallCurve,
)
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import (
    LevelFlightPoint,
    LevelPoint,
    Stall,
    StallSolution,
)
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import StubAtmosphere, close, near, solvers_with
from aero_kernel.tests.stall_stubs import StubOpti, flap_confidence, lift_curve
from aero_kernel.tests.test_stall_speed_engine import MASS, RHO

pytestmark = pytest.mark.asyncio

AIR = AirState(density=RHO, dynamic_viscosity=1.79e-5, speed_of_sound=340.0)
GRAVITY = 9.80665
CD = 0.05
ALPHA_S = 15.75


def document(*, with_flap: bool = True, with_aileron: bool = True) -> dict[str, Any]:
    """A 1.4 m span, 0.2 m chord wing with a flap on the first panel and an aileron on the second."""

    def rib(y: float, device: dict[str, Any] | None) -> dict[str, Any]:
        rib: dict[str, Any] = {
            "xyz_le": [0.0, y, 0.0],
            "chord": 0.2,
            "twist": 0.0,
            "airfoil": "naca2412",
        }
        if device is not None:
            rib["trailing_edge_device"] = {**device, "rel_chord_root": 0.75, "rel_chord_tip": 0.75}
        return rib

    ribs = [
        rib(0.0, {"role": "flap"} if with_flap else None),
        rib(0.3, {"role": "aileron"} if with_aileron else None),
        rib(0.7, None),
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": ribs}
    return {"name": "t", "wings": {"Main": wing}}


def device_angles(airplane: AirplaneGeometry) -> tuple[float, float]:
    """(flap, aileron) deflection in the stub's two device slots."""
    ribs = (airplane.wings or {})["Main"].x_secs
    angles = [
        0.0 if x.trailing_edge_device is None else (x.trailing_edge_device.deflection_deg or 0.0)
        for x in ribs
    ]
    return angles[0], angles[1]


def cl_max_of(airplane: AirplaneGeometry) -> float:
    """The stub's C_L,max: a flap raises it, a raised aileron (negative angle) lowers it."""
    flap, aileron = device_angles(airplane)
    return 1.19 + 0.002 * flap + 0.006 * aileron


def stall_of(
    airplane: AirplaneGeometry, mass: float, gravity: float, air: AirState
) -> StallSolution:
    cl_max = cl_max_of(airplane)
    area = stand_in_main_wing_properties(airplane).s_ref
    v_s = math.sqrt(2.0 * mass * gravity / (air.density * area * cl_max))
    return StallSolution(
        v_s=v_s,
        cl_max=cl_max,
        alpha_s=ALPHA_S,
        polar=lift_curve((ALPHA_S, cl_max), True),
    )


class CrowStub(StubOpti):
    """A stub whose stall depends on the flap and the raised aileron, and whose glide is parabolic."""

    def __init__(self) -> None:
        super().__init__()
        self.stall_airplanes: list[AirplaneGeometry] = []
        self.glide_speeds: list[float] = []
        self.n_loads: list[float] = []

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        self.stall_airplanes.append(airplane)
        self.n_loads.append(n_load)
        return Stall(solution=stall_of(airplane, mass_kg, gravity, air), warnings=())

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
        self.glide_speeds.append(v_ms)
        area = stand_in_main_wing_properties(airplane).s_ref
        cl = 2.0 * mass_kg * gravity / (air.density * v_ms**2 * area)
        point = LevelPoint(
            v_ms=v_ms,
            alpha_deg=4.0,
            cl=cl,
            cd=CD,
            lift_n=mass_kg * gravity,
            drag_n=CD * 0.5 * air.density * v_ms**2 * area,
        )
        return LevelFlightPoint(point=point, warnings=())


def inputs(**change: object) -> dict[str, object]:
    landing = 30.0
    airplane = AirplaneGeometry.model_validate(document())
    base: dict[str, object] = {
        "airplane": with_flaps_at(airplane, landing),
        "m": MASS,
        "g": GRAVITY,
        "n_load": 1.0,
        "rho": RHO,
        "mu": AIR.dynamic_viscosity,
        "a": AIR.speed_of_sound,
        "v_app": 1.05 * v_stall_landing(),
        "delta_f_ldg": landing,
        "delta_f_crow": 60.0,
        "delta_a_crow": 40.0,
    }
    return {**base, **change}


def v_stall_landing() -> float:
    flapped = AirplaneGeometry.model_validate(document())
    return stall_of(with_flaps_at(flapped, 30.0), MASS, GRAVITY, AIR).v_s


def context(stub: StubOpti) -> Context:
    return Context(origin="butterfly-max-mix", solvers=solvers_with(opti=stub))


async def run(stub: CrowStub, **change: object) -> dict[str, Any]:
    result = await butterfly_approach(inputs(**change), context(stub))  # type: ignore[arg-type]
    return dict(result)


# cl(s) = 1.19 + 0.002 (30 + 30 s) - 0.006 (40 s) = 1.25 - 0.18 s along the stub's crow path


async def test_the_mix_is_sampled_in_ten_equal_steps_from_landing_to_full_crow() -> None:
    stub = CrowStub()
    out = await run(stub)
    curve = out["v_s0_curve"]
    assert isinstance(curve, StallCurve)
    assert all(close(a, k / 10, 1e-12) for k, a in enumerate(curve.x))
    assert len(stub.stall_airplanes) == 11
    flaps = [device_angles(a)[0] for a in stub.stall_airplanes]
    ailerons = [device_angles(a)[1] for a in stub.stall_airplanes]
    assert all(close(a, 30.0 + 3.0 * k, 1e-12) for k, a in enumerate(flaps))
    assert all(abs(a + 4.0 * k) < 1e-9 for k, a in enumerate(ailerons))


async def test_the_stall_speed_curve_is_the_stall_problem_at_each_mix() -> None:
    out = await run(CrowStub())
    curve = out["v_s0_curve"]
    area = 0.28
    for s, v_s in zip(curve.x, curve.y, strict=True):
        cl = 1.25 - 0.18 * s
        assert close(v_s, math.sqrt(2 * MASS * GRAVITY / (RHO * area * cl)), 1e-9)


async def test_the_approach_speed_keeps_the_reserve_of_the_landing_configuration() -> None:
    out = await run(CrowStub())
    stall, approach = out["v_s0_curve"], out["v_app_curve"]
    assert isinstance(approach, Curve)
    v_app = 1.05 * v_stall_landing()
    assert close(approach.y[0], v_app, 1e-12)  # Q35: the curve starts at V_app
    for v_s, v in zip(stall.y, approach.y, strict=True):
        assert close(v / v_s, v_app / stall.y[0], 1e-9)


async def test_the_glide_angle_is_read_at_the_approach_speed_of_each_mix() -> None:
    stub = CrowStub()
    out = await run(stub)
    approach, gamma = out["v_app_curve"], out["gamma_curve"]
    assert stub.glide_speeds == list(approach.y)
    area = 0.28
    for v, g in zip(approach.y, gamma.y, strict=True):
        cl = 2 * MASS * GRAVITY / (RHO * v**2 * area)
        assert close(g, math.degrees(math.atan(CD / cl)), 1e-9)


async def test_the_largest_mix_is_where_the_stall_speed_reaches_the_approach_speed() -> None:
    out = await run(CrowStub())
    # 1.25 / 1.05^2 = 1.133787 = C_L at the crossing -> s = (1.25 - 1.133787) / 0.18
    exact = (1.25 - 1.25 / 1.05**2) / 0.18
    assert abs(out["s_max"] - exact) < 2e-3
    # V_S0(s) is convex here, so the chord between two samples lies above it and reaches the
    # approach speed earlier: the interpolated mix is a little below the root
    assert out["s_max"] <= exact


async def test_a_stall_speed_that_never_reaches_the_approach_speed_has_no_largest_mix() -> None:
    stub = CrowStub()
    with pytest.raises(FormulaError) as raised:
        await run(stub, v_app=1.3 * v_stall_landing())
    error = raised.value
    assert (error.category, error.code) == (
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
    )
    detail: dict[str, Any] = error.detail  # type: ignore[assignment]
    assert len(detail["mix"]) == 11
    assert detail["v_s0_m_s"][-1] < 1.3 * v_stall_landing()


async def test_an_approach_speed_at_or_below_the_landing_stall_speed_has_the_largest_mix_zero() -> (
    None
):
    stub = CrowStub()
    out = await run(stub, v_app=v_stall_landing())
    assert out["s_max"] == 0.0
    # exactly at the landing stall speed the formula takes the no-glide path: with '<=' instead of
    # '<' it would read eleven glides at the stall speed and still return s_max = 0
    assert out["gamma_curve"].x == ()
    assert stub.glide_speeds == []


async def test_the_preconditions_hold_for_a_crow_approach() -> None:
    x = inputs()
    assert approach_speed_positive(x).state == "held"
    assert crow_aileron_not_negative(x).state == "held"


@pytest.mark.parametrize("v_app", [0.0, -3.0])
async def test_an_approach_speed_not_above_zero_violates_its_precondition(v_app: float) -> None:
    assert approach_speed_positive(inputs(v_app=v_app)).state == "violated"


async def test_a_negative_crow_aileron_angle_violates_its_precondition() -> None:
    result = crow_aileron_not_negative(inputs(delta_a_crow=-5.0))
    assert result.state == "violated"
    assert "raised" in result.message


async def test_the_engine_refuses_a_negative_crow_aileron_angle_before_any_solve() -> None:
    stub = CrowStub()
    result = await engine({"crow-aileron-deflection": -5.0}, stub=stub)
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "precondition_violated"
    assert quantity.error.detail == {"precondition": "crow_aileron_not_negative"}
    assert not any(device_angles(a)[1] != 0.0 for a in stub.stall_airplanes)


async def test_the_stall_problem_is_the_level_one_bound_by_the_canon() -> None:
    stub = CrowStub()
    await engine({"approach-speed-margin-target": 1.05}, stub=stub)
    assert set(stub.n_loads) == {1.0}


async def test_a_mix_on_another_branch_is_named_even_when_the_stall_never_reaches_the_approach_speed() -> (
    None
):
    class OffPeak(CrowStub):
        async def stall(self, airplane: AirplaneGeometry, *args: Any) -> Stall:  # type: ignore[override]
            stall = await super().stall(airplane, *args)
            if abs(device_angles(airplane)[1] + 20.0) < 1e-9:
                flat = Polar(
                    alpha_deg=stall.solution.polar.alpha_deg,
                    cl=tuple(0.5 for _ in stall.solution.polar.cl),
                    cd=stall.solution.polar.cd,
                )
                return Stall(
                    solution=stall.solution.model_copy(update={"polar": flat}), warnings=()
                )
            return stall

    with pytest.raises(FormulaError) as raised:
        await run(OffPeak(), v_app=1.3 * v_stall_landing())
    error = raised.value
    assert error.code == "postcondition_violated"
    assert error.detail == {"postcondition": "optimum_at_first_cl_peak", "mix": 0.5}


async def test_an_approach_speed_below_the_landing_stall_gives_zero_without_reading_a_glide() -> (
    None
):
    class Refusing(CrowStub):
        async def level_flight_point(
            self,
            airplane: AirplaneGeometry,
            mass_kg: float,
            gravity: float,
            air: AirState,
            v_ms: float,
            n_load: float,
        ) -> LevelFlightPoint:
            self.glide_speeds.append(v_ms)
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "below the stall", "h")

    stub = Refusing()
    out = await run(stub, v_app=0.9 * v_stall_landing())
    assert out["s_max"] == 0.0
    assert stub.glide_speeds == []
    assert out["gamma_curve"].x == ()
    assert len(out["v_app_curve"].x) == 11


def fit_warning(flap: float, aileron: float, confidence: float) -> KernelWarning:
    return KernelWarning.of(
        "control_surface_fit_range_unknown",
        "fit range unknown",
        detail={
            "flaps": [
                {"wing": "Main", "device": "F", "deflection_deg": flap},
                {"wing": "Main", "device": "A", "deflection_deg": aileron},
            ],
            "devices": [{"wing": "Main", "device": "F", "mean_confidence": confidence}],
            "min_confidence": confidence,
        },
    )


class Noisy(CrowStub):
    """Regime messages that embed the Reynolds number of each speed, fit-range caveats per mix."""

    async def stall(self, airplane: AirplaneGeometry, *args: Any) -> Stall:  # type: ignore[override]
        stall = await super().stall(airplane, *args)
        flap, aileron = device_angles(airplane)
        warnings = (
            KernelWarning.of(
                "reynolds_bubble_sensitive", f"Re {stall.solution.v_s * 1e4:.0f}", detail={}
            ),
            fit_warning(flap, aileron, 1.0 - flap / 100.0),
        )
        return Stall(solution=stall.solution, warnings=warnings)


def v_s0(mix: float) -> float:
    """V_S0(s) = sqrt(2 m g / (rho S C_L(s))) with S = 0.28 m^2 and C_L(s) = 1.25 - 0.18 s."""
    return math.sqrt(2.0 * MASS * GRAVITY / (RHO * 0.28 * (1.25 - 0.18 * mix)))


def regime_messages(context_: Context) -> list[str]:
    return [w.message for w in context_.warnings if w.code == "reynolds_bubble_sensitive"]


async def test_the_forwarded_caveats_are_the_reference_solves_and_the_worst_case_of_the_sweep() -> (
    None
):
    stub = Noisy()
    context_ = context(stub)
    await butterfly_approach(inputs(), context_)  # type: ignore[arg-type]
    # V_app = 1.05 V_S0(0): V_S0(s) = V_S0(0) sqrt(1.25 / (1.25 - 0.18 s)) reaches 1.05 where
    # 1.25 - 0.18 s = 1.25 / 1.1025 = 1.13379, s = 0.6456: the closing sample is the mix 0.7.
    # The reference solves are the landing stall (s = 0) and that sample; the stub's message is
    # 'Re <v_s 1e4>' of the mix's own stall speed, so each mix has a message of its own.
    assert sorted(regime_messages(context_)) == sorted(
        [f"Re {v_s0(0.0) * 1e4:.0f}", f"Re {v_s0(0.7) * 1e4:.0f}"]
    )
    (fit,) = [w for w in context_.warnings if w.code == "control_surface_fit_range_unknown"]
    flaps = {f["device"]: f["deflection_deg"] for f in fit.detail["flaps"]}  # type: ignore[index, union-attr]
    assert flaps == {"F": 60.0, "A": -40.0}  # the largest deflection of each device
    assert near(float(str(fit.detail["min_confidence"])), 0.4, 1e-12)
    # the lowest mean confidence of device F over the sweep: the stub gives 1 - flap / 100 and the
    # flap peaks at 60 deg (full crow), so 0.4; the highest would be 0.7 (flap 30 deg at s = 0)
    (record,) = fit.detail["devices"]  # type: ignore[misc]
    assert (record["wing"], record["device"]) == ("Main", "F")  # type: ignore[index]
    assert near(float(str(record["mean_confidence"])), 0.4, 1e-12)  # type: ignore[index]


async def test_an_approach_speed_below_the_landing_stall_forwards_the_landing_stall_caveats() -> (
    None
):
    """The early-return path (s_max = 0) forwards the regime caveat of the landing stall once."""
    stub = Noisy()
    context_ = context(stub)
    out = await butterfly_approach(inputs(v_app=0.9 * v_stall_landing()), context_)  # type: ignore[arg-type]
    assert out["s_max"] == 0.0
    # one regime warning, that of the landing stall (reference solves 0 and 0 are the same)
    assert regime_messages(context_) == [f"Re {v_s0(0.0) * 1e4:.0f}"]
    (fit,) = [w for w in context_.warnings if w.code == "control_surface_fit_range_unknown"]
    assert near(float(str(fit.detail["min_confidence"])), 0.4, 1e-12)


async def test_the_validity_follows_the_largest_deflection_not_full_crow() -> None:
    """A crow flap below the landing flap: the landing flap, at s = 0, is the one declared."""
    stub = CrowStub()
    context_ = context(stub)
    await butterfly_approach(
        inputs(
            airplane=with_flaps_at(AirplaneGeometry.model_validate(document()), 60.0),
            delta_f_ldg=60.0,
            delta_f_crow=20.0,
        ),  # type: ignore[arg-type]
        context_,
    )  # type: ignore[arg-type]
    assert "flap_deflection_beyond_validity" in {w.code for w in context_.warnings}


def landing_flap_above_crow_flap(**change: object) -> dict[str, object]:
    """Landing flap 60 deg, full crow flap 20 deg with the aileron raised 10 deg.

    C_L(s) = 1.19 + 0.002 (60 - 40 s) + 0.006 (-10 s) = 1.31 - 0.14 s. The approach speed is 2 %
    above the landing stall speed V_S0(0) = sqrt(2 m g / (rho 0.28 1.31)); V_S0(1) is
    sqrt(1.31 / 1.17) = 1.058 times V_S0(0), so the crossing exists and the call returns. At
    s = 1 the flap (20 deg) and the aileron (10 deg) are both below the 30 deg limit: only the
    landing flap at s = 0 is above it.
    """
    landing = 60.0
    return inputs(
        airplane=with_flaps_at(AirplaneGeometry.model_validate(document()), landing),
        delta_f_ldg=landing,
        delta_f_crow=20.0,
        delta_a_crow=10.0,
        v_app=1.02 * math.sqrt(2.0 * MASS * GRAVITY / (RHO * 0.28 * 1.31)),
        **change,
    )


async def test_the_declared_flap_is_the_landing_flap_where_it_is_the_largest_deflection() -> None:
    context_ = context(CrowStub())
    out = await butterfly_approach(landing_flap_above_crow_flap(), context_)  # type: ignore[arg-type]
    s_max = out["s_max"]
    assert isinstance(s_max, float)
    assert 0.0 < s_max < 1.0
    (beyond,) = [w for w in context_.warnings if w.code == "flap_deflection_beyond_validity"]
    assert beyond.detail["limit_deg"] == 30.0
    # the landing flap (s = 0) is the only deflection above the limit; full crow is not judged
    assert beyond.detail["flaps"] == [
        {"wing": "Main", "device": "device 0", "deflection_deg": 60.0}
    ]


class ConfidencePerFlap(CrowStub):
    """A stub whose NeuralFoil confidence is low (0.3) only where the flap is at 60 deg."""

    async def stall(self, airplane: AirplaneGeometry, *args: Any) -> Stall:  # type: ignore[override]
        stall = await super().stall(airplane, *args)
        confidence = 0.3 if abs(device_angles(airplane)[0] - 60.0) < 1e-9 else 0.95
        solution = stall.solution.model_copy(update={"diagnostics": flap_confidence(confidence)})
        return Stall(solution=solution, warnings=())


async def test_the_confidence_declared_is_that_of_the_mix_with_the_largest_deflection() -> None:
    context_ = context(ConfidencePerFlap())
    await butterfly_approach(landing_flap_above_crow_flap(), context_)  # type: ignore[arg-type]
    # mix 0 (flap 60 deg) has confidence 0.3 and is the mix with the largest deflection; every
    # other mix has 0.95, above the floor, so a declaration can only come from mix 0
    (low,) = [w for w in context_.warnings if w.code == "flap_confidence_low"]
    assert near(float(str(low.detail["mean_confidence"])), 0.3, 1e-12)


async def test_the_flap_validity_is_declared_above_the_limit() -> None:
    """A crow flap above the flap-validity limit gives the declaration, the value is still computed."""
    stub = CrowStub()
    context_ = context(stub)
    await butterfly_approach(inputs(), context_)  # type: ignore[arg-type]
    assert "flap_deflection_beyond_validity" in {w.code for w in context_.warnings}


# --- the postcondition ------------------------------------------------------------------------


def stall_curve(peak_at: float = ALPHA_S) -> StallCurve:
    polars = [lift_curve((ALPHA_S, 1.19), True)] * 3
    return StallCurve(
        x=(0.0, 0.5, 1.0),
        y=(8.0, 8.5, 9.0),
        alpha_s=(peak_at, ALPHA_S, ALPHA_S),
        cl_max=(1.19, 1.19, 1.19),
        polars=tuple(polars),
    )


async def test_the_postcondition_holds_when_every_mix_is_at_its_first_peak() -> None:
    assert optimum_at_first_cl_peak({}, {"v_s0_curve": stall_curve()}).state == "held"


async def test_the_postcondition_names_the_mix_that_is_on_another_branch() -> None:
    result = optimum_at_first_cl_peak({}, {"v_s0_curve": stall_curve(peak_at=22.0)})
    assert result.state == "violated"
    assert "mix s = 0" in result.message
    assert result.detail == {"mix": 0.0}
    assert "another branch" in result.message


async def test_the_postcondition_is_unchecked_without_the_curve() -> None:
    assert optimum_at_first_cl_peak({}, {"v_s0_curve": 1.0}).state == "unchecked"


# --- the engine -------------------------------------------------------------------------------


def aircraft(**values: float) -> AircraftInput:
    given = {
        "aircraft-mass": MASS,
        "altitude": 0.0,
        "flap-deflection-landing": 30.0,
        "crow-flap-deflection": 60.0,
        "crow-aileron-deflection": 40.0,
        **values,
    }
    return AircraftInput.model_validate({"airplane": document(), "values": given})


async def engine(
    values: dict[str, float],
    stub: StubOpti | None = None,
    quantities: tuple[str, ...] = ("butterfly-max-mix",),
    **doc: bool,
) -> Any:
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=stub or CrowStub())
    given = aircraft(**values)
    if doc:
        given = AircraftInput.model_validate({"airplane": document(**doc), "values": given.values})
    request = ComputeRequest(quantities=quantities)
    return await evaluate(shipped_build(), given, request, solvers=solvers)


async def test_the_engine_carries_the_largest_mix_from_the_approach_margin() -> None:
    result = await engine({"approach-speed-margin-target": 1.05})
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.OK, result
    assert (quantity.unit, quantity.tool, quantity.application) == ("1", "OPT", "crow")
    assert quantity.value is not None
    assert abs(quantity.value - (1.25 - 1.25 / 1.05**2) / 0.18) < 2e-3


async def test_the_engine_hands_out_the_three_curves_over_the_mix() -> None:
    curves = ("butterfly-stall-speed-curve", "butterfly-approach-speed-curve")
    result = await engine(
        {"approach-speed-margin-target": 1.05}, quantities=(*curves, "butterfly-glide-angle-curve")
    )
    stall, approach, glide = result.quantities
    assert [q.status for q in result.quantities] == [QuantityStatus.OK] * 3, result
    assert (stall.unit, approach.unit, glide.unit) == ("m/s", "m/s", "deg")
    for quantity in (stall, approach, glide):
        assert quantity.curve is not None
        assert (quantity.value, quantity.interval, quantity.application) == (None, None, "crow")
        assert quantity.curve.x == tuple(i / 10 for i in range(11))
        assert (quantity.curve.x_quantity, quantity.curve.x_unit) == ("crow-mix", "1")
    assert stall.curve is not None
    assert not isinstance(stall.curve, StallCurve)  # the sweep's extra fields stay in the formula


async def test_the_engine_reports_a_fully_mixable_airplane_with_the_curve_in_the_detail() -> None:
    result = await engine({})  # the default margin 1.3: the stall never reaches it
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "unsupported_configuration"
    assert "fully mixable" in quantity.error.message


async def test_a_wing_without_an_aileron_has_no_butterfly() -> None:
    result = await engine({}, with_aileron=False)
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code.value == "condition_not_met"


async def test_a_wing_without_a_flap_has_no_butterfly() -> None:
    result = await engine({}, with_flap=False)
    assert result.quantities[0].status is QuantityStatus.NOT_APPLICABLE


async def test_the_postcondition_error_discards_all_butterfly_outputs() -> None:
    class OffPeak(CrowStub):
        async def stall(self, airplane: AirplaneGeometry, *args: Any) -> Stall:  # type: ignore[override]
            stall = await super().stall(airplane, *args)
            if abs(device_angles(airplane)[1] + 20.0) < 1e-9:
                polar = Polar(
                    alpha_deg=stall.solution.polar.alpha_deg,
                    cl=tuple(0.5 for _ in stall.solution.polar.cl),
                    cd=stall.solution.polar.cd,
                )
                return Stall(
                    solution=stall.solution.model_copy(update={"polar": polar}), warnings=()
                )
            return stall

    result = await engine({"approach-speed-margin-target": 1.05}, stub=OffPeak())
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "postcondition_violated"
    assert "mix s = 0.5" in quantity.error.message
    assert quantity.error.detail == {"postcondition": "optimum_at_first_cl_peak", "mix": 0.5}
