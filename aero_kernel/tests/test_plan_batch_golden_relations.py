"""Relations between the recorded goldens of the reference fleet, checked without a solver.

Fast tier (#1458, P8-F01). The aero tier compares what the kernel computes with the recorded cells
(``test_plan_batch_fleet.py``, ``test_mvp_chain_fleet.py``, REL = 2e-3) and nothing else, so a
defect that was present at the recording, or was re-recorded, passes it. These tests state what
must hold between the recorded numbers whatever the build; together with the aero comparison they
bind the kernel's values to the relations. They are still **regression, not validation**: no
measurement is involved.
"""

import math

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.tests import test_mvp_chain_fleet as mvp_chain
from aero_kernel.tests.asb_fakes import stand_in_quarter_chord_x
from aero_kernel.tests.reference_fleet import (
    PLAN_BATCH,
    WITH_PITCH_TAIL,
    FleetMember,
    reference_document,
)
from aero_kernel.tests.test_plan_batch_fleet import GOLDEN, Golden

STANDARD_GRAVITY = 9.80665  # m/s^2, the canon default
SEA_LEVEL_DENSITY = 1.225  # kg/m^3, ISA at 0 m (the goldens were recorded at altitude 0)
POINTS = ("md", "mp", "app")


def number(member: FleetMember, slug: str) -> float | None:
    """The recorded scalar of ``slug``, or ``None`` where the golden is an error."""
    golden = GOLDEN[member][slug]
    return golden if isinstance(golden, float) else None


def worlds(golden: Golden | None) -> tuple[float, float, float] | None:
    """The three recorded neutral-point worlds, or ``None`` where the golden is no value."""
    return golden if isinstance(golden, tuple) else None


@pytest.mark.parametrize("member", PLAN_BATCH, ids=lambda m: m.name)
def test_the_recorded_speeds_are_ordered_stall_minimum_sink_minimum_drag(
    member: FleetMember,
) -> None:
    """V_S < V_mp < V_md: the minimum sink is flown at a higher C_L than the best glide
    (C_L,mp = sqrt(3) C_L,md on a parabolic polar) and below C_L,max. Every member of the batch has a
    recorded stall speed (AERONCA_CHAMP since gh-1423)."""
    v_s = number(member, "stall-speed")
    v_mp, v_md = number(member, "minimum-sink-speed"), number(member, "minimum-drag-speed")
    assert v_s is not None
    assert v_mp is not None
    assert v_md is not None
    assert v_s < v_mp < v_md


@pytest.mark.parametrize("member", PLAN_BATCH, ids=lambda m: m.name)
def test_the_recorded_stall_speed_closes_the_lift_balance(member: FleetMember) -> None:
    """V_S = sqrt(2 m g / (rho S_ref C_L,max)) with the README's mass, g = 9.80665 m/s^2,
    rho = 1.225 kg/m^3 and S_ref the frozen AeroSandbox area of the member (asb_reference[0]),
    which is independent of the recorded run. The tolerance 1e-5 covers the kernel's own Probe
    (1e-6) and the rounding of the ISA density."""
    v_s, cl_max = number(member, "stall-speed"), number(member, "max-lift-coefficient")
    assert v_s is not None
    assert cl_max is not None
    weight = member.mass_kg * STANDARD_GRAVITY
    hand = math.sqrt(2.0 * weight / (SEA_LEVEL_DENSITY * member.asb_reference[0] * cl_max))
    assert math.isclose(v_s, hand, rel_tol=1e-5)


def spiral_signs_disagree(cells: dict[str, Golden], point: str) -> bool:
    """Whether the criterion and the time of one point have opposite signs in every world."""
    criterion = worlds(cells.get(f"spiral-criterion-{point}"))
    time = worlds(cells.get(f"spiral-doubling-time-{point}"))
    if criterion is None or time is None:
        return criterion is None and time is None
    return all(e * t < 0.0 for e, t in zip(criterion, time, strict=True))


@pytest.mark.parametrize("member", PLAN_BATCH, ids=lambda m: m.name)
@pytest.mark.parametrize("point", POINTS)
def test_the_recorded_spiral_time_has_the_sign_opposite_to_the_criterion(
    member: FleetMember, point: str
) -> None:
    """E < 0 (unstable) goes with a positive doubling time, E > 0 with a negative halving time, per
    world. Not an identity: sign(t) = -sign(E) sign(C_l,beta C_n,p - C_n,beta C_l,p)
    (lateral_stability._spiral_time), so it holds while that roll-yaw denominator is positive, which
    it is for every aircraft of the fleet; an aircraft that breaks it needs a look, not a re-record.
    Where one of the two is an error, both are."""
    assert spiral_signs_disagree(GOLDEN[member], point)


@pytest.mark.parametrize("member", list(mvp_chain.GOLDEN), ids=lambda m: m.name)
@pytest.mark.parametrize("point", POINTS)
def test_the_spiral_signs_of_the_first_six_disagree_as_well(
    member: FleetMember, point: str
) -> None:
    """The same relation on the goldens of test_mvp_chain_fleet.py (RV-7 is the stable one). RV-7's
    approach point is recorded there as an error, so it has neither value."""
    cells: dict[str, Golden] = dict(mvp_chain.GOLDEN[member])
    assert spiral_signs_disagree(cells, point)


@pytest.mark.parametrize(
    "member", [m for m in PLAN_BATCH if m in WITH_PITCH_TAIL], ids=lambda m: m.name
)
def test_the_recorded_neutral_points_lie_between_the_wing_and_the_tail(
    member: FleetMember,
) -> None:
    """Every world's x_NP lies behind the quarter-chord MAC of the main wing and ahead of the
    quarter-chord MAC of the tail: a stabilising tail moves the neutral point aft of the wing's
    aerodynamic centre, and never past its own. The two positions are computed here from the
    document by AeroSandbox's panel formula (asb_fakes.stand_in_quarter_chord_x), not recorded."""
    neutral_point = worlds(GOLDEN[member]["neutral-point"])
    assert neutral_point is not None
    wings = AirplaneGeometry.model_validate(reference_document(member)).wings or {}
    x_wing = stand_in_quarter_chord_x(wings[member.main_wing_name])
    x_tail = stand_in_quarter_chord_x(wings[member.tail_name])
    for x_np in neutral_point:
        assert x_wing < x_np < x_tail
