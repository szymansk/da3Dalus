"""roll-rate of BRYAN and JAGUAR through the public compute(), real AeroSandbox, IPOPT and AVL.

Aero tier. The values are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this
build computes (NeuralFoil xlarge, AVL 3.40 from the avl-binary wheel, the declared AVL roll mesh of
ARCHITECTURE 8.8) so that a change of code or of a tool is noticed. The AVL world is independently
checked against a resampling of the same geometry by the expert (``test_solvers_avl_roll_real.py``,
0.1 %). The operating point is the canon's own: aileron deflection +20 deg, no flap, k_S 1.3 (the
default), ISA sea level.
"""

import math

import pytest
from aero_kernel import compute
from aero_kernel.errors import ErrorCategory
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import (
    AircraftInput,
    ComputeResult,
    KernelWarning,
    QuantityResult,
    QuantityStatus,
    WarningSeverity,
)
from aero_kernel.solvers.asb_airplane import main_wing_properties
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = ("roll-rate-approach", "roll-rate-nondimensional-approach")
AB, AVL = "roll-rate=aerobuildup", "roll-rate=avl"
# Regression goldens: (AeroBuildup world, AVL world) of p in deg/s and of p_hat = p b / 2 V.
GOLDEN_P = {
    FleetMember.BRYAN: (490.14462, 410.51230),
    FleetMember.JAGUAR: (346.50673, 419.59114),
}
GOLDEN_P_HAT = {
    FleetMember.BRYAN: (0.3431387, 0.28739),
    FleetMember.JAGUAR: (0.2304946, 0.27911),
}
# V_app = 1.3 V_S (m/s) of the slice-3 stall golden path; the fleet has no flap, so V_S,landing = V_S.
V_APP = {FleetMember.BRYAN: 6.818986359246604, FleetMember.JAGUAR: 8.188976805083124}
HINGE_SEGMENTS = {FleetMember.BRYAN: 4, FleetMember.JAGUAR: 6}
_CACHE: dict[tuple[FleetMember, float], ComputeResult] = {}


async def run(member: FleetMember, delta: float = 20.0) -> ComputeResult:
    if (member, delta) not in _CACHE:
        aircraft = AircraftInput.model_validate(
            {
                "airplane": reference_document(member),
                "values": {
                    "aircraft-mass": member.mass_kg,
                    "altitude": 0.0,
                    "aileron-deflection": delta,
                },
            }
        )
        _CACHE[member, delta] = await compute(aircraft, request(*SLUGS))
    return _CACHE[member, delta]


def worlds(quantity: QuantityResult) -> dict[str, float]:
    assert quantity.status is QuantityStatus.OK, quantity
    assert quantity.interval is not None
    return quantity.interval.worlds


def codes(quantity: QuantityResult, world: str | None = None) -> list[str]:
    return [w.code for w in quantity.warnings if world is None or w.world == world]


@pytest.mark.parametrize("member", list(FleetMember))
async def test_roll_rate_goldens_per_world(member: FleetMember) -> None:
    p, p_hat = (await run(member)).quantities
    assert p.slug == SLUGS[0]
    assert p_hat.slug == SLUGS[1]
    assert p.unit == "deg/s"
    assert p_hat.unit == "1"
    assert p.tool == "OPT"
    for quantity, golden, rel, absolute in (
        (p, GOLDEN_P[member], 1e-4, None),
        (p_hat, GOLDEN_P_HAT[member], None, 1e-4),
    ):
        found = worlds(quantity)
        assert set(found) == {AB, AVL}
        for world, value in zip((AB, AVL), golden, strict=True):
            if rel is not None:
                assert close(found[world], value, rel), (quantity.slug, world, found[world])
            else:
                assert abs(found[world] - value) < (absolute or 0.0), (quantity.slug, world)
        assert quantity.interval is not None
        assert quantity.interval.min == min(found.values())
        assert quantity.interval.max == max(found.values())


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_nondimensional_rate_is_p_b_over_two_v_in_both_worlds(
    member: FleetMember,
) -> None:
    """p_hat = radians(p) b_ref / (2 V_app) with the kernel's b_ref, hand-computed from the geometry."""
    b_ref = main_wing_properties(AirplaneGeometry.model_validate(reference_document(member))).b_ref
    p, p_hat = (await run(member)).quantities
    for world in (AB, AVL):
        expected = math.radians(worlds(p)[world]) * b_ref / (2.0 * V_APP[member])
        assert close(worlds(p_hat)[world], expected, 1e-9), world


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_approach_speed_is_1p3_stall_speed_of_the_clean_airplane(
    member: FleetMember,
) -> None:
    """No flap: the landing configuration is the clean airplane (Q33), V_app = 1.3 V_S exactly."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    approach, landing, clean = (
        await compute(aircraft, request("approach-speed", "stall-speed-landing", "stall-speed"))
    ).quantities
    assert landing.value == clean.value
    assert approach.value is not None
    assert clean.value is not None
    assert close(approach.value, 1.3 * clean.value, 1e-12)
    assert close(approach.value, V_APP[member], 1e-9)


@pytest.mark.parametrize("member", list(FleetMember))
async def test_a_negative_command_gives_the_mirrored_roll_in_both_worlds(
    member: FleetMember,
) -> None:
    """Sign and antisymmetry (M2): +20 deg rolls to the right in each world, -20 deg exactly the
    other way, within the AVL print and the IPOPT tolerance."""
    plus, minus = (await run(member, 20.0)).quantities[1], (await run(member, -20.0)).quantities[1]
    for world in (AB, AVL):
        assert worlds(plus)[world] > 0.0
        assert abs(worlds(minus)[world] + worlds(plus)[world]) < 1e-4, world


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_warnings_of_the_roll(member: FleetMember) -> None:
    p, p_hat = (await run(member)).quantities
    for quantity in (p, p_hat):
        found = codes(quantity)
        assert "aileron_deflection_beyond_reference" not in found  # 20 deg <= 25 deg
        assert "default_target_used" in found
        for refused in (
            "avl_mesh_not_converged",
            "avl_refinement_unchecked",
            "avl_roll_branch_inconsistent",
        ):
            assert refused not in found
        # the AVL world carries AVL's primer range (|p'b/2V| > 0.10) as the adapter's defect
        (beyond,) = [w for w in quantity.warnings if w.code == "avl_roll_rate_beyond_range"]
        assert beyond.world == AVL
        assert beyond.severity is WarningSeverity.DEFECT
        assert beyond.detail == {"p_hat": GOLDEN_P_HAT[member][1], "limit": 0.1}
        # the averaged hinge line: one declaration per driven segment, AeroBuildup world only
        averaged = [w for w in quantity.warnings if w.code == "hinge_line_averaged"]
        assert len(averaged) == HINGE_SEGMENTS[member]
        assert {w.world for w in averaged} == {AB}
        # NeuralFoil's confidence and the angle the net saw, a regression of the deflected strips
        (fit,) = [w for w in quantity.warnings if w.code == "control_surface_fit_range_unknown"]
        assert fit.world == AB
        assert 0.0 < float(_detail(fit, "min_confidence")) < 1.0
        assert float(_detail(fit, "max_effective_alpha_deg")) > 10.0


def _detail(warning: KernelWarning, key: str) -> float:
    value = warning.detail[key]
    assert isinstance(value, float)
    return value


async def test_the_regression_values_of_the_fit_range_warning() -> None:
    expected = {
        FleetMember.BRYAN: (0.6547296, "Hoehenleitwerk", 18.692106, "Tragflaeche"),
        FleetMember.JAGUAR: (0.4667034, "Tragflaeche", 14.617064, "Tragflaeche"),
    }
    for member, (confidence, low_wing, alpha, high_wing) in expected.items():
        (fit,) = [
            w
            for w in (await run(member)).quantities[0].warnings
            if w.code == "control_surface_fit_range_unknown"
        ]
        assert close(_detail(fit, "min_confidence"), confidence, 1e-5)
        assert fit.detail["min_confidence_wing"] == low_wing
        assert close(_detail(fit, "max_effective_alpha_deg"), alpha, 1e-5)
        assert fit.detail["max_effective_alpha_wing"] == high_wing


async def test_a_world_that_does_not_converge_is_an_error_with_the_other_value_in_the_detail() -> (
    None
):
    """JAGUAR at 40 deg: the AeroBuildup world has no solution the solver reaches (a declared
    not_converged error, never a value), the AVL world computes. The quantity is an error, its value
    and interval are None, the failing world is named and the AVL value is only in detail.worlds_ok
    (A11: a failed world is never dropped from the interval, never narrowed). An error carries no
    warnings: ARCHITECTURE 8.1 ("An error means no value") and Engine._result_under, which lists the
    warnings of an ok quantity only, so aileron_deflection_beyond_reference (40 > 25 deg) is not
    on it."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.JAGUAR),
            "values": {
                "aircraft-mass": FleetMember.JAGUAR.mass_kg,
                "altitude": 0.0,
                "aileron-deflection": 40.0,
            },
        }
    )
    for quantity in (await compute(aircraft, request(*SLUGS))).quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        assert quantity.interval is None
        assert quantity.warnings == ()
        error = quantity.error
        assert error is not None
        assert error.category is ErrorCategory.NOT_CONVERGED
        assert error.world == AB
        worlds_ok = error.detail["worlds_ok"]
        assert isinstance(worlds_ok, dict)
        assert list(worlds_ok) == [AVL]
