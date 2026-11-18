"""aileron-deflection-required round trip with roll-rate on the fleet, real AeroSandbox, IPOPT and AVL.

Aero tier. The check is the inverse relation, not a golden value: the roll rate at a known command
is the target, the formula must return that command, and feeding the returned command back into
``roll-rate`` must reproduce the target (AeroBuildup world: within the formula's own tolerance,
``opt_roll_target_tolerance``; AVL world: linear, so to the print resolution of AVL).
"""

import math

import pytest
from aero_kernel import compute
from aero_kernel.reference_fleet import FleetMember
from aero_kernel.schema import AircraftInput, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import flap_values, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

AB, AVL = "roll-rate=aerobuildup", "roll-rate=avl"
REQ_AB, REQ_AVL = (
    "aileron-deflection-required=aerobuildup",
    "aileron-deflection-required=avl",
)
MEMBERS = (
    FleetMember.BRYAN,
    FleetMember.JAGUAR,
    FleetMember.BELEMNITOS,
    FleetMember.WIESEL,
    FleetMember.RV7,
)
DELTA_BIAS = 10.0  # the known command whose AeroBuildup roll rate is the target
DELTA_LINEAR = 5.0  # the known command whose AVL roll rate (inside AVL's range) is the target


async def _compute(member: FleetMember, slug: str, values: dict[str, float]) -> QuantityResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                **flap_values(member),
                **values,
            },
        }
    )
    (quantity,) = (await compute(aircraft, request(slug))).quantities
    assert quantity.status is QuantityStatus.OK, quantity
    return quantity


def _worlds(quantity: QuantityResult) -> dict[str, float]:
    assert quantity.interval is not None
    return quantity.interval.worlds


async def _roll(member: FleetMember, delta: float) -> dict[str, float]:
    quantity = await _compute(member, "roll-rate-approach", {"aileron-deflection": delta})
    found = _worlds(quantity)
    if AVL not in found:  # beyond AVL's range: the value is in the declaration
        (dropped,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
        found = {**found, AVL: float(dropped.detail["p_deg_s"])}  # pyright: ignore[reportArgumentType]
    return found


@pytest.mark.parametrize("member", MEMBERS, ids=lambda m: m.name)
async def test_the_aerobuildup_deflection_reproduces_the_target_through_roll_rate(
    member: FleetMember,
) -> None:
    target = (await _roll(member, DELTA_BIAS))[AB]
    required = await _compute(
        member, "aileron-deflection-required-approach", {"roll-rate-target-approach": target}
    )
    delta = _worlds(required)[REQ_AB]
    assert abs(delta - DELTA_BIAS) < 0.05, (member, delta)
    assert close((await _roll(member, delta))[AB], target, 5e-4), member


@pytest.mark.parametrize("member", MEMBERS, ids=lambda m: m.name)
async def test_the_avl_deflection_reproduces_the_target_through_roll_rate(
    member: FleetMember,
) -> None:
    target = (await _roll(member, DELTA_LINEAR))[AVL]
    required = await _compute(
        member, "aileron-deflection-required-approach", {"roll-rate-target-approach": target}
    )
    delta = _worlds(required)[REQ_AVL]
    assert abs(delta - DELTA_LINEAR) < 0.01, (member, delta)
    assert close((await _roll(member, delta))[AVL], target, 1e-3), member


async def test_the_cruise_application_inverts_the_cruise_roll_rate() -> None:
    member, speed = FleetMember.BRYAN, 15.0
    rolled = await _compute(
        member,
        "roll-rate-cruise",
        {"cruise-speed-target": speed, "aileron-deflection": DELTA_BIAS},
    )
    target = _worlds(rolled)["roll-rate-cruise-target=aerobuildup"]
    required = await _compute(
        member,
        "aileron-deflection-required-cruise",
        {"cruise-speed-target": speed, "roll-rate-target-cruise": target},
    )
    assert abs(_worlds(required)[REQ_AB] - DELTA_BIAS) < 0.05


async def test_a_negative_target_gives_the_mirrored_deflection() -> None:
    member = FleetMember.BRYAN
    target = (await _roll(member, DELTA_BIAS))[AB]
    found: list[float] = []
    for wanted in (target, -target):
        required = await _compute(
            member, "aileron-deflection-required-approach", {"roll-rate-target-approach": wanted}
        )
        found.append(_worlds(required)[REQ_AB])
    plus, minus = found
    assert math.isclose(plus, -minus, abs_tol=0.01)


async def test_a_target_above_the_maximum_is_target_above_method_maximum() -> None:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.BRYAN),
            "values": {
                "aircraft-mass": FleetMember.BRYAN.mass_kg,
                "altitude": 0.0,
                "roll-rate-target-approach": 5000.0,
            },
        }
    )
    (quantity,) = (
        await compute(aircraft, request("aileron-deflection-required-approach"))
    ).quantities
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code in {"target_above_method_maximum", "not_converged"}
    assert quantity.error.world == REQ_AB
