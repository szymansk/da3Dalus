"""The band of masses without a stall speed, on AVISTAR_ELITE and AERONCA_CHAMP (gh-1423, aero tier).

Real AeroSandbox and IPOPT through the public compute(), sea level. The first C_L peak of both
aircraft changes with the Reynolds number: below a transition speed it is an early shoulder of the
lift curve, from that speed on a later, higher peak. A weight between what the two peaks carry at the
transition speed has no speed at which a first peak balances it: no value, one declared failure. A
weight outside that gap has a stall speed, also where the two bracketing sweeps of the procedure see
the other peak (the bracket is located again, declared).

The numbers are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this build
computes (NeuralFoil xlarge, 0.25 deg sweep). Measured for gh-1423 on a 0.05 kg grid (AVISTAR_ELITE,
8.4 to 9.8 kg) and a 0.005 kg grid (AERONCA_CHAMP, 0.325 to 0.415 kg).
"""

import pytest
from aero_kernel import compute
from aero_kernel.errors import ErrorCategory
from aero_kernel.schema import QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, aircraft_input

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

NO_SOLUTION = "no_consistent_first_lift_extremum"
REL = 2e-3  # the regression tolerance of the fleet tests
SLUGS = ("stall-speed", "max-lift-coefficient", "angle-of-attack-stall", "approach-speed")


async def stall(member: FleetMember, mass_kg: float) -> dict[str, QuantityResult]:
    """The stall quantities and the approach speed (which reads the landing stall speed) at a mass."""
    values = {"altitude": 0.0, "aircraft-mass": mass_kg}
    result = await compute(aircraft_input(member, values), request(*SLUGS))
    return {q.slug: q for q in result.quantities}


def detail_number(quantity: QuantityResult, key: str) -> float:
    assert quantity.error is not None
    value = quantity.error.detail[key]
    assert isinstance(value, float)
    return value


@pytest.mark.parametrize("mass_kg", [8.8, 9.0, 9.4])
async def test_the_avistar_has_no_stall_speed_inside_the_band_and_says_why(mass_kg: float) -> None:
    """One failure for the whole band (before gh-1423: `not_converged`, "the optimum lies on the bound
    of alpha", from 8.8 to 9.3 kg and `postcondition_violated` at 9.4 kg). The first peak is the
    shoulder at 8 deg (C_L 1.2110) below 17.283 m/s and the peak at 16.5 deg (C_L 1.3423) from there
    on; at that speed they carry 8.505 and 9.428 kg."""
    got = await stall(FleetMember.AVISTAR_ELITE, mass_kg)
    for slug in ("stall-speed", "max-lift-coefficient", "angle-of-attack-stall"):
        quantity = got[slug]
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        error = quantity.error
        assert error is not None
        assert (error.category, error.code) == (
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            NO_SOLUTION,
        )
        assert (error.retryable, error.escalate) == (
            False,
            False,
        )  # the same input, the same answer
        assert f"no stall speed is defined at {mass_kg:g} kg" in error.message
        assert "not a failed solve" in error.hint
        assert close(detail_number(quantity, "transition_v_ms"), 17.2828, 1e-4)
        assert (error.detail["alpha_below_deg"], error.detail["alpha_above_deg"]) == (8.0, 16.5)
        assert close(detail_number(quantity, "cl_below"), 1.21102, REL)
        assert close(detail_number(quantity, "cl_above"), 1.34235, REL)
        assert close(detail_number(quantity, "mass_below_kg"), 8.5054, REL)
        assert close(detail_number(quantity, "mass_above_kg"), 9.4277, REL)
        assert (
            detail_number(quantity, "lift_below_n")
            < detail_number(quantity, "lift_required_n")
            < detail_number(quantity, "lift_above_n")
        )
        assert close(detail_number(quantity, "lift_required_n"), mass_kg * 9.80665, 1e-12)


async def test_what_reads_the_stall_speed_leads_back_to_the_reason() -> None:
    """`upstream_failed` names the root quantity and the code that says why (ch. 8.1)."""
    got = await stall(FleetMember.AVISTAR_ELITE, 9.0)
    error = got["approach-speed"].error
    assert error is not None
    assert error.code == "upstream_failed"
    assert error.detail == {"causes": [{"quantity": "stall-speed-landing", "code": NO_SOLUTION}]}
    assert (error.retryable, error.escalate) == (False, False)


@pytest.mark.parametrize(
    ("mass_kg", "v_s", "cl_max", "alpha_s"),
    [(8.7, 17.479654, 1.2109824, 7.9743725), (9.5, 17.349843, 1.3421984, 16.5037435)],
)
async def test_on_both_sides_of_the_band_the_avistar_stalls_as_before(
    mass_kg: float, v_s: float, cl_max: float, alpha_s: float
) -> None:
    """Unchanged by gh-1423 and not relocated: at 8.7 kg the optimum is the shoulder, at 9.5 kg the
    later peak. The stall speed is lower at the higher mass: C_L,max jumps between the two."""
    got = await stall(FleetMember.AVISTAR_ELITE, mass_kg)
    assert close(got["stall-speed"].value, v_s, REL)
    assert close(got["max-lift-coefficient"].value, cl_max, REL)
    assert close(got["angle-of-attack-stall"].value, alpha_s, REL)
    assert "stall_bracket_relocated" not in {w.code for w in got["stall-speed"].warnings}


@pytest.mark.parametrize(
    ("mass_kg", "v_s", "cl_max", "alpha_s", "first_alpha", "alpha"),
    [
        (0.36, 6.1023832, 1.1954209, 4.7578442, 4.5, 4.75),  # the peak drifted one sweep step
        (0.39, 6.1820995, 1.2618564, 7.0221546, 4.75, 7.0),  # the nominal mass: another peak
    ],
)
async def test_the_aeronca_stalls_where_its_first_peak_lies_at_the_stall_speed(
    mass_kg: float, v_s: float, cl_max: float, alpha_s: float, first_alpha: float, alpha: float
) -> None:
    """Before gh-1423 both masses were `not_converged`: the bracketing sweep runs at a speed at which
    the first peak lies elsewhere than at the stall speed. The bracket is located again and the
    value carries the notice with both brackets (ADR 0020)."""
    got = await stall(FleetMember.AERONCA_CHAMP, mass_kg)
    assert close(got["stall-speed"].value, v_s, REL)
    assert close(got["max-lift-coefficient"].value, cl_max, REL)
    assert close(got["angle-of-attack-stall"].value, alpha_s, REL)
    assert got["approach-speed"].status is QuantityStatus.OK
    (notice,) = [w for w in got["stall-speed"].warnings if w.code == "stall_bracket_relocated"]
    assert notice.severity == "notice"
    assert (notice.detail["first_alpha_deg"], notice.detail["alpha_deg"]) == (first_alpha, alpha)


async def test_the_aeronca_has_no_stall_speed_between_its_two_first_peaks() -> None:
    """At 0.37 kg: the first peak lies at 4.75 deg (C_L 1.1973) below 6.1394 m/s and at 7 deg
    (C_L 1.2605) from there on; they carry 0.3650 and 0.3842 kg at that speed."""
    got = await stall(FleetMember.AERONCA_CHAMP, 0.37)
    quantity = got["stall-speed"]
    error = quantity.error
    assert error is not None
    assert (error.category, error.code) == (ErrorCategory.UNSUPPORTED_CONFIGURATION, NO_SOLUTION)
    assert close(detail_number(quantity, "transition_v_ms"), 6.13940, 1e-4)
    assert (error.detail["alpha_below_deg"], error.detail["alpha_above_deg"]) == (4.75, 7.0)
    assert close(detail_number(quantity, "mass_below_kg"), 0.36495, REL)
    assert close(detail_number(quantity, "mass_above_kg"), 0.38420, REL)
    causes = got["approach-speed"].error
    assert causes is not None
    assert causes.detail == {"causes": [{"quantity": "stall-speed-landing", "code": NO_SOLUTION}]}
