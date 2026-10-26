"""stall-speed of BRYAN and JAGUAR through the public compute(), real AeroSandbox and IPOPT.

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they
pin what this build computes (recorded at the commit that introduced them) so that a change of
code or of AeroSandbox is noticed; they are not measurements of the aircraft.
"""

import importlib.metadata

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import StallRequest
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import OPT_SETTINGS, close
from aero_kernel.tests.reference_fleet import (
    FUSELAGE_REJECTED,
    FleetMember,
    assert_rejected_for_the_fuselage,
    flap_values,
    reference_document,
)

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = (
    "stall-speed",
    "max-lift-coefficient",
    "angle-of-attack-stall",
    "stall-speed-takeoff",
    "stall-speed-landing",
    "inverted-max-lift-coefficient",
)
# Regression goldens at sea level, mass of the fleet member, ISA, AeroSandbox's S_ref of the main wing
# (gh-1240; V_S and alpha_S did not move, the lift coefficients did), NeuralFoil model size xlarge.
BRYAN_V_S = 5.2453741  # m/s
BRYAN_CL_MAX, BRYAN_ALPHA_S = 1.2548391, 13.1987303
BRYAN_V_S_SMALL = 5.2894317  # m/s, the small model of the prototype
JAGUAR_V_S = 6.2992129  # m/s
JAGUAR_CL_MAX, JAGUAR_ALPHA_S = 0.9985795, 9.9252911
JAGUAR_CL_MIN = -0.7831582
# (V_S m/s, C_L,max, alpha_S deg, C_L,min) of the aircraft added by gh-1284; the takeoff and landing
# speeds equal V_S where the airplane has no flap (BELEMNITOS).
BELEMNITOS_GOLDEN = (4.4882110, 1.1141652, 9.5701434, -0.4784755)
RV7_GOLDEN = (6.6001580, 1.2246480, 15.1183671, -0.8329524)


def sea_level_air() -> AirState:
    """The ISA state at sea level, as the kernel's ATM adapter returns it."""
    return AirState(
        density=1.2249991558877122,
        dynamic_viscosity=1.789380278077583e-05,
        speed_of_sound=340.2941077869353,
    )


async def stall_result(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0, **flap_values(member)},
        }
    )
    return await compute(aircraft, request(*SLUGS))


async def stall(member: FleetMember) -> dict[str, QuantityResult]:
    return {q.slug: q for q in (await stall_result(member)).quantities}


def assert_goldens_are_pinned_to_their_tools(result: ComputeResult) -> None:
    """The goldens hold for these tool versions and this NeuralFoil model size only."""
    assert result.provenance.tool_versions == {
        "aerosandbox": importlib.metadata.version("aerosandbox"),
        "neuralfoil": importlib.metadata.version("neuralfoil"),
    }
    assert result.provenance.solver_settings == OPT_SETTINGS


async def test_bryan_stalls_where_the_prototype_found_it_with_the_small_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prototype (bryan/ERGEBNISSE_STABILITAET.md, 151 g): V_S = 5.29 m/s.

    The prototype used AeroSandbox's default NeuralFoil model, "small", so the worker is run in this
    process with that size: 5.2894 m/s, 0.01 % from the prototype. The prototype took S from
    AeroSandbox's own planform area (7.0 dm2); the kernel passes AeroSandbox's S_ref of the main
    wing (6.9985 dm2) to AeroBuildup, so C_L,max differs a little while V_S, which fixes S * C_L,
    agrees.
    """
    monkeypatch.setattr(opti_module, "NEURALFOIL_MODEL_SIZE", "small")
    request = StallRequest(
        airplane=AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN)),
        mass_kg=FleetMember.BRYAN.mass_kg,
        gravity=9.80665,
        n_load=1.0,
        air=sea_level_air(),
    )
    solution = opti_module.stall_worker(request).value
    assert close(solution.v_s, 5.29, 2e-3)  # the prototype's two decimals
    assert close(solution.v_s, BRYAN_V_S_SMALL, 1e-5)  # regression of the small model


async def test_bryan_regression_goldens_with_the_xlarge_model() -> None:
    """xlarge, the size the kernel uses (maintainer 2026-10-22): 5.2454 m/s, 0.85 % below the
    prototype, which the small model reproduces (test above). C_L,max 1.256 at 13.2 deg."""
    result = await stall_result(FleetMember.BRYAN)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    clean = quantities["stall-speed"]
    assert clean.status is QuantityStatus.OK
    assert close(clean.value, BRYAN_V_S, 1e-5)  # regression
    assert close(quantities["max-lift-coefficient"].value, BRYAN_CL_MAX, 1e-5)
    assert close(quantities["angle-of-attack-stall"].value, BRYAN_ALPHA_S, 1e-5)
    assert {"reynolds_outside_band", "reynolds_bubble_sensitive"} <= {
        w.code for w in clean.warnings
    }  # ADR 0028: the tip chord of 1 cm and the root chord of 15 cm span the band
    outside = {str(w.detail["wing"]) for w in clean.warnings if w.code == "reynolds_outside_band"}
    assert {"Seitenleitwerk", "Hoehenleitwerk"} <= outside  # the surface that is out is named
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == clean.value  # no flaps: the same airplane, not a fallback


async def test_bryans_inverted_stall_gives_no_value_because_the_trough_vanishes_with_the_speed() -> (
    None
):
    """At the first estimate's speed (5.88 m/s) the sweep has a trough at -10.5 deg; at the speed
    the second sweep uses (8.32 m/s, higher Re) it has none: C_L falls monotonically down to the
    sweep's lower end (-15 deg, C_L -0.55). The trough is present at the lower Reynolds number of
    the first sweep, so the bracket finds no extremum and the kernel returns no value (ADR 0020)
    instead of a boundary sample. (Speeds and the -10.5 deg trough are those of the "small" model,
    measured in the next test; with the "xlarge" model the kernel uses, the result is the same: no value.)"""
    inverted = (await stall(FleetMember.BRYAN))["inverted-max-lift-coefficient"]
    assert inverted.status is QuantityStatus.ERROR
    assert inverted.value is None
    assert inverted.error is not None
    assert inverted.error.code == "not_converged"
    assert "no trough" in inverted.error.message


async def test_bryans_inverted_trough_exists_only_at_the_low_speed_of_the_first_sweep() -> None:
    from aero_kernel.geometry import AirplaneGeometry
    from aero_kernel.solvers.aerobuildup import sweep_polar
    from aero_kernel.solvers.air import AirState
    from aero_kernel.solvers.asb_airplane import to_asb_airplane
    from aero_kernel.solvers.opti import ALPHA_MAX_DEG, ALPHA_MIN_DEG, ALPHA_STEP_DEG
    from aero_kernel.solvers.stall_math import first_extremum_from_zero

    air = AirState(
        density=1.2249991559, dynamic_viscosity=1.789380278e-05, speed_of_sound=340.2941078
    )
    airplane = to_asb_airplane(
        AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN))
    )
    count = round((ALPHA_MAX_DEG - ALPHA_MIN_DEG) / ALPHA_STEP_DEG)
    grid = [ALPHA_MIN_DEG + k * ALPHA_STEP_DEG for k in range(count + 1)]
    slow = sweep_polar(airplane, air, 5.88, grid, "small")
    fast = sweep_polar(airplane, air, 8.32, grid, "small")
    index = first_extremum_from_zero(slow.alpha_deg, slow.cl, upright=False)
    assert index is not None
    assert slow.alpha_deg[index] == -10.5
    assert first_extremum_from_zero(fast.alpha_deg, fast.cl, upright=False) is None


async def test_jaguar_regression_goldens() -> None:
    result = await stall_result(FleetMember.JAGUAR)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), quantities
    assert close(quantities["stall-speed"].value, JAGUAR_V_S, 1e-5)
    assert close(quantities["max-lift-coefficient"].value, JAGUAR_CL_MAX, 1e-5)
    assert close(quantities["angle-of-attack-stall"].value, JAGUAR_ALPHA_S, 1e-5)
    assert close(quantities["inverted-max-lift-coefficient"].value, JAGUAR_CL_MIN, 1e-5)
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == quantities["stall-speed"].value


async def test_belemnitos_regression_goldens() -> None:
    """No flap: take-off and landing are the clean airplane. The passed 0.28 kg equals the source's
    total_mass_kg (estimated, maintainer 2026-10-26), so no conflicting_mass is declared."""
    result = await stall_result(FleetMember.BELEMNITOS)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), quantities
    for slug, golden in zip(
        (
            "stall-speed",
            "max-lift-coefficient",
            "angle-of-attack-stall",
            "inverted-max-lift-coefficient",
        ),
        BELEMNITOS_GOLDEN,
        strict=True,
    ):
        assert close(quantities[slug].value, golden, 1e-5), slug
    for slug in ("stall-speed-takeoff", "stall-speed-landing"):
        assert quantities[slug].value == quantities["stall-speed"].value
    for quantity in quantities.values():
        assert "conflicting_mass" not in {w.code for w in quantity.warnings}


# RV-7 with the maintainer's guessed flaps (take-off 15 deg, landing 30 deg), regression of this build
# (#1212, route A: the flap is the rotated contour behind the hinge, evaluated by NeuralFoil):
# (V_S m/s, C_L,max, NeuralFoil's lowest analysis_confidence at the stall optimum).
RV7_TAKEOFF = (6.3137959, 1.3382550, 0.8771531)
RV7_LANDING = (6.2445456, 1.3681013, 0.4069260)


async def rv7_values(*slugs: str) -> dict[str, float | None]:
    """The values of the given quantities of RV-7 with the maintainer's guessed flaps."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(FleetMember.RV7),
            "values": {
                "aircraft-mass": FleetMember.RV7.mass_kg,
                "altitude": 0.0,
                **flap_values(FleetMember.RV7),
            },
        }
    )
    result = await compute(aircraft, request(*slugs))
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    return {q.slug: q.value for q in result.quantities}


async def test_rv7_regression_goldens_and_the_flaps_computed_never_the_clean_airplane() -> None:
    """RV-7 has flaps and the DB gives no deflection; the maintainer's guess (2026-10-26) is passed
    as caller parameters: take-off 15 deg, landing 30 deg. Since #1212 AeroBuildup is given the
    flaps, so the two configured stall speeds are computed with them: they differ from the clean
    speed and carry the declared model range of the flap.

    Regression, not validation. The flap raises C_L,max (1.22 clean, 1.34 and 1.37) and lowers the
    stall speed (6.60 clean, 6.31 and 6.24 m/s), the right direction for a flap. NeuralFoil's
    confidence at the stall optimum falls with the deflection (0.88 at 15 deg, 0.41 at 30 deg) and is
    reported as a value in control_surface_fit_range_unknown (the threshold is a pending rule)."""
    result = await stall_result(FleetMember.RV7)
    assert_goldens_are_pinned_to_their_tools(result)
    quantities = {q.slug: q for q in result.quantities}
    for slug, golden in zip(
        (
            "stall-speed",
            "max-lift-coefficient",
            "angle-of-attack-stall",
            "inverted-max-lift-coefficient",
        ),
        RV7_GOLDEN,
        strict=True,
    ):
        assert quantities[slug].status is QuantityStatus.OK, slug
        assert close(quantities[slug].value, golden, 1e-5), slug
    assert "control_surface_fit_range_unknown" not in {
        w.code for w in quantities["stall-speed"].warnings
    }
    for slug, golden, deflection in (
        ("stall-speed-takeoff", RV7_TAKEOFF[0], 15.0),
        ("stall-speed-landing", RV7_LANDING[0], 30.0),
    ):
        quantity = quantities[slug]
        assert quantity.status is QuantityStatus.OK, slug
        assert close(quantity.value, golden, 1e-5), slug
        clean_speed = quantities["stall-speed"].value
        assert clean_speed is not None
        assert quantity.value < clean_speed, slug  # a flap lowers the stall speed
        assert not close(quantity.value, clean_speed, 1e-3), slug  # never the clean airplane's
        (caveat,) = [w for w in quantity.warnings if w.code == "control_surface_fit_range_unknown"]
        confidence = RV7_TAKEOFF[2] if slug.endswith("takeoff") else RV7_LANDING[2]
        assert close(float(caveat.detail["min_confidence"]), confidence, 1e-5), slug  # pyright: ignore[reportArgumentType]
        assert caveat.detail["flaps"] == [
            {"wing": "main_wing", "device": "flaps", "deflection_deg": deflection}
        ], slug
    found = await rv7_values("max-lift-coefficient-takeoff", "max-lift-coefficient-landing")
    assert close(found["max-lift-coefficient-takeoff"], RV7_TAKEOFF[1], 1e-5)
    assert close(found["max-lift-coefficient-landing"], RV7_LANDING[1], 1e-5)


async def test_rv7_speeds_from_the_configured_stall_speeds() -> None:
    """The margins bind the configured stall speeds: V_app = 1.3 V_S,LDG, V_td = 1.1 V_S,LDG and
    V_TO = 1.1 V_S,TO (default margins), so the flapped values enter and not the clean ones."""
    found = await rv7_values("approach-speed", "touchdown-speed", "takeoff-speed")
    assert close(found["approach-speed"], 1.3 * RV7_LANDING[0], 1e-6)
    assert close(found["touchdown-speed"], 1.1 * RV7_LANDING[0], 1e-6)
    assert close(found["takeoff-speed"], 1.1 * RV7_TAKEOFF[0], 1e-6)


@pytest.mark.parametrize("member", list(FUSELAGE_REJECTED))
async def test_the_fuselage_aerosandbox_cannot_take_is_the_recorded_result(
    member: FleetMember,
) -> None:
    """CHEKKER's and WIESEL's fuselages carry a section with n_lower != n (README): the kernel
    declares it instead of computing, for every stall quantity."""
    assert_rejected_for_the_fuselage(member, (await stall_result(member)).quantities)
