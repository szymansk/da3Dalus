"""roll-rate through the engine on the shipped canon, with stub adapters (two worlds, A11)."""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
    WarningSeverity,
)
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import StubAtmosphere, close, solvers_with
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, StubOpti
from aero_kernel.tests.test_solvers_roll_devices import aileron, wing_geometry

pytestmark = pytest.mark.asyncio

RHO, MASS, GRAVITY = 1.225, 0.15, 9.80665
WORLDS = ("roll-rate=aerobuildup", "roll-rate=avl")


def plane(role: str = "aileron", **device: Any) -> AirplaneGeometry:
    """A 0.4 m half-span wing (S_ref 0.16 m^2, b_ref 0.8 m) with a roll device on its second panel."""
    return wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.78, 0.78, role=role, **device))


async def run(
    *slugs: str,
    airplane: AirplaneGeometry | None = None,
    delta: float | None = 20.0,
    opti: StubOpti | None = None,
    avl: StubAvl | None = None,
    extra: dict[str, float] | None = None,
) -> ComputeResult:
    given: dict[str, float] = {"aircraft-mass": MASS, "altitude": 0.0, **(extra or {})}
    if delta is not None:
        given["aileron-deflection"] = delta
    aircraft = AircraftInput.model_validate({"airplane": airplane or plane(), "values": given})
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}), opti=opti or StubOpti(), avl=avl or StubAvl()
    )
    return await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=slugs), solvers=solvers
    )


def only(result: ComputeResult) -> QuantityResult:
    (quantity,) = result.quantities
    return quantity


def v_app(model: AirplaneGeometry) -> float:
    """1.3 * V_S of the stub's lift curve: V_S = sqrt(2 m g / (rho S C_L,max))."""
    area = stand_in_main_wing_properties(model).s_ref
    return 1.3 * math.sqrt(2.0 * MASS * GRAVITY / (RHO * area * UPRIGHT_PEAK[1]))


async def test_roll_rate_not_applicable_without_aileron_role() -> None:
    """Q35: no device acting as aileron: the condition is not met, and no input is demanded."""
    quantity = only(await run("roll-rate-approach", airplane=plane("elevator"), delta=None))
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET
    assert quantity.error is None


@pytest.mark.parametrize("role", ["aileron", "flaperon", "elevon"])
async def test_roll_rate_flaperon_and_elevon_count(role: str) -> None:
    """A flaperon is also a flap: its landing configuration needs the landing flap deflection
    (Q33), given here at rest, so that the approach speed is the clean airplane's."""
    extra = {"flap-deflection-landing": 0.0} if role == "flaperon" else None
    quantity = only(await run("roll-rate-approach", airplane=plane(role), extra=extra))
    assert quantity.status is QuantityStatus.OK, quantity


async def test_roll_rate_missing_aileron_deflection_is_missing_input() -> None:
    quantity = only(await run("roll-rate-approach", delta=None))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "missing_input"
    assert quantity.error.input_path is not None


async def test_roll_rate_interval_two_worlds_end_to_end_with_stubs() -> None:
    """Hand values at V_app = 1.3 V_S (stub lift curve): AeroBuildup p = 3 rad/s -> 171.887 deg/s,
    p_hat = 3 * b / (2 V); AVL p_hat = 0.08 (inside its range) -> p = 0.08 * 2 V / b rad/s."""
    airplane = plane()
    result = await run("roll-rate-approach", "roll-rate-nondimensional-approach")
    p, p_hat = result.quantities
    assert (p.slug, p.unit, p.tool) == ("roll-rate-approach", "deg/s", "OPT")
    assert p.interval is not None
    assert set(p.interval.worlds) == set(WORLDS)
    speed, b_ref = v_app(airplane), 0.8
    assert close(p.interval.worlds["roll-rate=aerobuildup"], math.degrees(3.0), 1e-12)
    assert close(p.interval.worlds["roll-rate=avl"], math.degrees(0.08 * 2.0 * speed / b_ref), 1e-9)
    assert p_hat.interval is not None
    assert set(p_hat.interval.worlds) == set(WORLDS)
    assert close(p_hat.interval.worlds["roll-rate=aerobuildup"], 3.0 * b_ref / (2.0 * speed), 1e-9)
    assert close(p_hat.interval.worlds["roll-rate=avl"], 0.08, 1e-9)
    assert p_hat.unit == "1"


async def test_p_hat_from_p_with_bound_b_ref() -> None:
    """p_hat = radians(p) * b_ref / (2 V_app) with the bound wing-span, in both worlds."""
    result = await run("roll-rate-approach", "roll-rate-nondimensional-approach")
    p, p_hat = result.quantities
    assert p.interval is not None
    assert p_hat.interval is not None
    speed = v_app(plane())
    for world in WORLDS:
        expected = math.radians(p.interval.worlds[world]) * 0.8 / (2.0 * speed)
        assert close(p_hat.interval.worlds[world], expected, 1e-12)


async def test_avl_world_cl_from_kernel_sref() -> None:
    """C_L = m g / (1/2 rho V_app^2 S_ref) with the kernel's S_ref, the command passed on."""
    avl = StubAvl()
    await run("roll-rate-approach", avl=avl)
    ((airplane, cl, delta),) = avl.roll_calls
    speed = v_app(airplane)
    assert close(
        cl,
        MASS * GRAVITY / (0.5 * RHO * speed**2 * stand_in_main_wing_properties(airplane).s_ref),
        1e-12,
    )
    assert delta == 20.0


async def test_the_aerobuildup_world_gets_mass_gravity_air_speed_and_command() -> None:
    opti = StubOpti()
    await run("roll-rate-approach", opti=opti)
    ((airplane, mass, gravity, air, speed, delta),) = opti.roll_calls
    assert (mass, gravity, air.density, delta) == (MASS, GRAVITY, RHO, 20.0)
    assert close(speed, v_app(airplane), 1e-12)


async def test_a_negative_command_gives_the_mirrored_roll_in_both_worlds() -> None:
    plus = only(await run("roll-rate-approach", delta=20.0))
    minus = only(await run("roll-rate-approach", delta=-20.0))
    assert plus.interval is not None
    assert minus.interval is not None
    for world in WORLDS:
        assert close(minus.interval.worlds[world], -plus.interval.worlds[world], 1e-12)


async def test_aerobuildup_failure_error_with_avl_in_worlds_ok() -> None:
    """A failed world is never dropped from the interval (A11): the quantity is an error and the
    value that did compute is in the detail."""
    opti = StubOpti()
    opti.roll_failure = FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "no roll", "check the speed"
    )
    quantity = only(await run("roll-rate-approach", opti=opti))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.value is None
    assert quantity.interval is None
    assert quantity.error is not None
    assert quantity.error.code == "not_converged"
    worlds_ok = quantity.error.detail["worlds_ok"]
    assert isinstance(worlds_ok, dict)
    assert list(worlds_ok) == ["roll-rate=avl"]


@pytest.mark.parametrize(
    ("delta", "expected"), [(20.0, False), (25.0, False), (30.0, True), (-30.0, True)]
)
async def test_deflection_beyond_25_is_practice_warning_in_both_worlds(
    delta: float, expected: bool
) -> None:
    quantity = only(await run("roll-rate-approach", delta=delta))
    beyond = [w for w in quantity.warnings if w.code == "aileron_deflection_beyond_reference"]
    if not expected:
        assert beyond == []
        return
    assert sorted(str(w.world) for w in beyond) == sorted(WORLDS)
    for warning in beyond:
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.origin == "roll-rate-approach"
        assert warning.detail == {"deflection_deg": delta, "reference_deg": 25.0}
        assert "Sadraey" in warning.message


async def test_deflection_beyond_stop_computes_without_stop_warning() -> None:
    """Q34: stops are never read; 30 deg on a device with a 10 deg stop computes."""
    quantity = only(
        await run("roll-rate-approach", airplane=plane(positive_deflection_deg=10.0), delta=30.0)
    )
    assert quantity.status is QuantityStatus.OK
    assert not [w for w in quantity.warnings if "stop" in w.code or "stop" in w.message.lower()]


async def test_geometry_deflection_ignored_still_reported() -> None:
    """Ch. 8.11: the geometry's own deflection is an editor's state; the adapters get the airplane
    at rest, and the quantity says the supplied deflection was ignored."""
    opti, avl = StubOpti(), StubAvl()
    quantity = only(
        await run("roll-rate-approach", airplane=plane(deflection_deg=5.0), opti=opti, avl=avl)
    )
    assert "geometry_deflection_ignored" in [w.code for w in quantity.warnings]
    for airplane in (opti.roll_calls[0][0], avl.roll_calls[0][0]):
        device = (airplane.wings or {})["Main"].x_secs[1].trailing_edge_device
        assert device is not None
        assert device.deflection_deg == 0.0


async def test_approach_speed_default_target_used_inherited() -> None:
    quantity = only(await run("roll-rate-approach"))
    (warning,) = [w for w in quantity.warnings if w.code == "default_target_used"]
    assert warning.origin == "approach-speed-margin-target"


AB_WORLD, AVL_WORLD = WORLDS


def avl_roll(p_hat: float) -> StubAvl:
    avl = StubAvl()
    avl.p_hat = p_hat
    return avl


@pytest.mark.parametrize("p_hat", [0.08, 0.10])
async def test_the_avl_world_stays_in_the_interval_up_to_and_at_the_limit(p_hat: float) -> None:
    """Decision (b): |p b / 2V| <= 0.10 is inside AVL's stated range, both worlds form the interval."""
    quantity = only(await run("roll-rate-nondimensional-approach", avl=avl_roll(p_hat)))
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == set(WORLDS)
    assert "world_outside_validity" not in [w.code for w in quantity.warnings]


@pytest.mark.parametrize("p_hat", [0.1001, 0.25, -0.25])
async def test_the_avl_world_beyond_the_limit_is_dropped_and_declared(p_hat: float) -> None:
    """Decision (b), maintainer 2026-10-25: outside |p b / 2V| <= 0.10 the interval is AeroBuildup alone."""
    delta = -20.0 if p_hat < 0 else 20.0
    avl = avl_roll(abs(p_hat))
    result = await run(
        "roll-rate-approach", "roll-rate-nondimensional-approach", avl=avl, delta=delta
    )
    for quantity in result.quantities:
        assert quantity.interval is not None
        assert set(quantity.interval.worlds) == {AB_WORLD}
        assert quantity.interval.min == quantity.interval.max
        (warning,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
        assert warning.world == AVL_WORLD
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.detail["limit"] == 0.1
        assert warning.detail["p_hat"] == p_hat
        assert "AVL" in warning.message


async def test_the_excluded_avl_value_of_p_is_in_the_warning_not_in_the_interval() -> None:
    quantity = only(await run("roll-rate-approach", avl=avl_roll(0.25)))
    assert quantity.interval is not None
    (warning,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
    excluded = warning.detail["p_deg_s"]
    assert isinstance(excluded, float)
    assert close(excluded, math.degrees(0.25 * 2.0 * v_app(plane()) / 0.8), 1e-9)
    assert excluded not in quantity.interval.worlds.values()


async def test_a_failing_aerobuildup_world_stays_an_error_beside_an_excluded_avl_world() -> None:
    opti = StubOpti()
    opti.roll_failure = FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "no roll", "check the speed"
    )
    quantity = only(await run("roll-rate-approach", opti=opti, avl=avl_roll(0.25)))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "not_converged"
