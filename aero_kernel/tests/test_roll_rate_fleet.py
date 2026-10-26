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
from aero_kernel.tests.reference_fleet import (
    FleetMember,
    assert_rejected_for_the_fuselage,
    flap_values,
    reference_document,
)

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = ("roll-rate-approach", "roll-rate-nondimensional-approach")
AB, AVL = "roll-rate=aerobuildup", "roll-rate=avl"
# Regression goldens: (AeroBuildup world, AVL world) of p in deg/s and of p_hat = p b / 2 V.
GOLDEN_P = {
    FleetMember.BRYAN: (490.14462, 410.51230),
    FleetMember.JAGUAR: (346.50673, 419.59114),
    FleetMember.BELEMNITOS: (115.91897, 120.59319),
}
GOLDEN_P_HAT = {
    FleetMember.BRYAN: (0.3431387, 0.28739),
    FleetMember.JAGUAR: (0.2304946, 0.27911),
    FleetMember.BELEMNITOS: (0.2599288, 0.27041),
}
# V_app = 1.3 V_S (m/s) of the slice-3 stall golden path; the fleet has no flap, so V_S,landing = V_S.
V_APP = {
    FleetMember.BRYAN: 6.818986359246604,
    FleetMember.JAGUAR: 8.188976805083124,
    FleetMember.BELEMNITOS: 5.834674251667882,
}
HINGE_SEGMENTS = {FleetMember.BRYAN: 4, FleetMember.JAGUAR: 6, FleetMember.BELEMNITOS: 0}
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
                    **flap_values(member),
                },
            }
        )
        _CACHE[member, delta] = await compute(aircraft, request(*SLUGS))
    return _CACHE[member, delta]


def worlds(quantity: QuantityResult) -> dict[str, float]:
    assert quantity.status is QuantityStatus.OK, quantity
    assert quantity.interval is not None
    return quantity.interval.worlds


def excluded_avl(quantity: QuantityResult) -> KernelWarning:
    """The declaration that dropped the AVL world (|p b / 2V| > 0.10, decision (b) of #1243)."""
    (warning,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
    assert warning.world == AVL
    return warning


def codes(quantity: QuantityResult, world: str | None = None) -> list[str]:
    return [w.code for w in quantity.warnings if world is None or w.world == world]


@pytest.mark.parametrize("member", list(GOLDEN_P))
async def test_roll_rate_goldens_per_world(member: FleetMember) -> None:
    p, p_hat = (await run(member)).quantities
    assert p.slug == SLUGS[0]
    assert p_hat.slug == SLUGS[1]
    assert p.unit == "deg/s"
    assert p_hat.unit == "1"
    assert p.tool == "OPT"
    for quantity, golden, rel, absolute, key in (
        (p, GOLDEN_P[member], 1e-4, None, "p_deg_s"),
        (p_hat, GOLDEN_P_HAT[member], None, 1e-4, "p_hat"),
    ):
        # both fleet members roll beyond AVL's stated range: the interval is AeroBuildup alone
        found = worlds(quantity)
        assert set(found) == {AB}
        assert quantity.interval is not None
        assert quantity.interval.min == quantity.interval.max == found[AB]
        # the excluded AVL value stays visible, in the declaration
        shown = {AB: found[AB], AVL: _detail(excluded_avl(quantity), key)}
        for world, value in zip((AB, AVL), golden, strict=True):
            if rel is not None:
                assert close(shown[world], value, rel), (quantity.slug, world, shown[world])
            else:
                assert abs(shown[world] - value) < (absolute or 0.0), (quantity.slug, world)


@pytest.mark.parametrize("member", list(GOLDEN_P))
async def test_the_nondimensional_rate_is_p_b_over_two_v_in_both_worlds(
    member: FleetMember,
) -> None:
    """p_hat = radians(p) b_ref / (2 V_app) with the kernel's b_ref, hand-computed from the geometry."""
    b_ref = main_wing_properties(AirplaneGeometry.model_validate(reference_document(member))).b_ref
    p, p_hat = (await run(member)).quantities
    seen = {AB: (worlds(p)[AB], worlds(p_hat)[AB])}
    seen[AVL] = (
        _detail(excluded_avl(p), "p_deg_s"),
        _detail(excluded_avl(p_hat), "p_hat"),
    )
    for world, (rate, rate_hat) in seen.items():
        expected = math.radians(rate) * b_ref / (2.0 * V_APP[member])
        assert close(rate_hat, expected, 1e-9), world


@pytest.mark.parametrize("member", list(GOLDEN_P))
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
    assert approach.value is not None
    assert landing.value is not None
    assert clean.value is not None
    assert landing.value == clean.value
    assert close(approach.value, 1.3 * clean.value, 1e-12)
    assert close(approach.value, V_APP[member], 1e-9)


@pytest.mark.parametrize("member", list(GOLDEN_P))
async def test_a_negative_command_gives_the_mirrored_roll_in_both_worlds(
    member: FleetMember,
) -> None:
    """Sign and antisymmetry (M2): +20 deg rolls to the right in each world, -20 deg exactly the
    other way, within the AVL print and the IPOPT tolerance."""
    plus, minus = (await run(member, 20.0)).quantities[1], (await run(member, -20.0)).quantities[1]
    assert worlds(plus)[AB] > 0.0
    assert abs(worlds(minus)[AB] + worlds(plus)[AB]) < 1e-4
    # AVL's value is not in the interval (beyond its range) but is in the declaration, mirrored
    avl_plus, avl_minus = excluded_avl(plus).detail["p_hat"], excluded_avl(minus).detail["p_hat"]
    assert isinstance(avl_plus, float)
    assert isinstance(avl_minus, float)
    assert avl_plus > 0.0
    assert abs(avl_minus + avl_plus) < 1e-4


@pytest.mark.parametrize("member", list(GOLDEN_P))
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
        # decision (b): the same range drops the AVL world from the interval, declared with its value
        dropped = excluded_avl(quantity)
        assert dropped.severity is WarningSeverity.PRACTICE
        assert dropped.detail["limit"] == 0.1
        # the averaged hinge line: one declaration per driven segment, AeroBuildup world only
        averaged = [w for w in quantity.warnings if w.code == "hinge_line_averaged"]
        assert len(averaged) == HINGE_SEGMENTS[member]
        assert {w.world for w in averaged} == ({AB} if HINGE_SEGMENTS[member] else set())
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
        FleetMember.BELEMNITOS: (0.8018459, "V-Leitwerk", 16.349829, "Tragflaeche"),
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


async def test_chekker_has_no_aileron_so_the_roll_rate_is_not_applicable() -> None:
    """CHEKKER has no aileron (its main wing carries no device): not an error, a stated reason."""
    for quantity in (await run(FleetMember.CHEKKER)).quantities:
        assert quantity.status is QuantityStatus.NOT_APPLICABLE, quantity.slug
        assert quantity.value is None
        assert quantity.reason is not None
        assert quantity.reason.message == "The aircraft does not satisfy `has_aileron`."


async def test_wiesel_roll_rate_waits_for_the_stall_speed_the_fuselage_blocks() -> None:
    """The approach speed needs the landing stall speed, which needs the AeroSandbox airplane."""
    quantities = (await run(FleetMember.WIESEL)).quantities
    assert_rejected_for_the_fuselage(FleetMember.WIESEL, quantities, rooted=False)
    for quantity in quantities:
        assert quantity.error is not None
        assert quantity.error.code == "upstream_failed"
        assert "because `stall-speed-landing` failed" in quantity.error.message


# RV-7 on approach (#1212): the landing configuration, flaps at 30 deg (route A: the rotated contour),
# V_app = 1.3 * 6.2445 m/s. Regression values of the AeroBuildup world; the AVL world (p_hat 0.2213,
# beyond its range) is dropped from the interval and shown in its declaration.
RV7_AB_P_DEG_S, RV7_AB_P_HAT = 226.38745, 0.1995581
RV7_AVL_P_DEG_S, RV7_AVL_P_HAT = 251.05240, 0.2213
RV7_ROLL_CONFIDENCE = 0.3927175


async def test_rv7_roll_on_approach_is_evaluated_on_the_landing_configuration() -> None:
    """Maintainer decision 2026-10-26: the approach roll uses the landing configuration. With the
    flap as geometry the flapped C_L(alpha) curve has no spurious low peak any more, so the
    AeroBuildup world converges (it failed with the tau * delta flap: C_L 0.681 needed, first peak
    0.651). The AVL world is beyond its range and leaves the interval (decision (b) of #1243)."""
    p, p_hat = (await run(FleetMember.RV7)).quantities
    for quantity, golden, rel in ((p, RV7_AB_P_DEG_S, 1e-4), (p_hat, RV7_AB_P_HAT, 1e-4)):
        found = worlds(quantity)
        assert set(found) == {AB}, quantity.slug
        assert close(found[AB], golden, rel), quantity.slug
    shown = _detail(excluded_avl(p), "p_deg_s")
    assert close(shown, RV7_AVL_P_DEG_S, 1e-4)
    assert close(_detail(excluded_avl(p_hat), "p_hat"), RV7_AVL_P_HAT, 1e-3)
    for world, code in ((AB, "control_surface_fit_range_unknown"), (AVL, "avl_flap_linearised")):
        assert code in codes(p, world), (world, code)
    (roll_caveat,) = [
        w for w in p.warnings if w.code == "control_surface_fit_range_unknown" and w.world == AB
    ]
    assert "flap_confidence_low" in codes(p, AB)  # 0.393 is below the 0.85 floor
    assert "flap_confidence_low" not in codes(p, AVL)
    assert "flap_deflection_beyond_validity" not in codes(p)
    assert close(float(roll_caveat.detail["min_confidence"]), RV7_ROLL_CONFIDENCE, 1e-4)  # pyright: ignore[reportArgumentType]
