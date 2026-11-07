"""minimum-sink-speed of BRYAN and JAGUAR through the public compute(), real AeroSandbox and IPOPT.

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they pin
what this build computes (NeuralFoil model size xlarge, the tool versions asserted below) so that a
change of code or of AeroSandbox is noticed; they are not measurements of the aircraft.
"""

import pytest
from aero_kernel import compute
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import OPT_SETTINGS, close
from aero_kernel.tests.reference_fleet import (
    FleetMember,
    reference_document,
)
from aero_kernel.tests.test_regime_fleet import assert_regime_per_surface

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = (
    "minimum-sink-speed",
    "angle-of-attack-minimum-sink",
    "lift-coefficient-minimum-sink",
    "minimum-drag-speed",
)
# The tool versions the goldens hold for. A different version may move them; this is then noticed
# here (and the goldens are re-recorded deliberately), not discovered later.
GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
# Regression goldens at sea level, mass of the fleet member, ISA, AeroSandbox's S_ref of the main wing (gh-1240),
# NeuralFoil model size xlarge: (V_mp m/s, alpha_mp deg, C_L,mp, V_md m/s). V_md is the golden of
# test_minimum_drag_speed_fleet.py, recomputed here as the reference of the ratio.
# BRYAN re-recorded for #1355 slice 2 (canopy merged); before: (6.0225190, 5.1468365, 0.9518853, 7.2306630).
GOLDEN = {
    FleetMember.BRYAN: (
        6.4546825,
        3.6050250,
        0.8286883,
        7.7115090,
    ),  # #1358: was 6.4126247, 3.7242834, 0.8395940, 7.6649267
    FleetMember.JAGUAR: (
        7.1085573,
        5.6116187,
        0.7841376,
        8.9849874,
    ),  # #1358: was 7.1019810, 5.6291430, 0.7855905, 8.8849618
    FleetMember.BELEMNITOS: (
        4.8934801,
        5.8417751,
        0.9372608,
        5.2599903,
    ),  # #1358: was 4.8933654, 0.9373048
    FleetMember.RV7: (
        7.9388254,
        7.6737171,
        0.8464620,
        9.9524821,
    ),  # #1358: was 7.9411907, 7.6357058, 0.8459578, 9.9423059
    FleetMember.CHEKKER: (
        7.7966254,
        3.6754048,
        0.8505984,
        9.7394293,
    ),  # #1358: was 7.3310603, 5.0096420, 0.9620648, 8.8958176
    FleetMember.WIESEL: (
        9.7641003,
        6.4824095,
        0.7472696,
        12.0893466,
    ),  # #1358: was 9.7532022, 6.4971152, 0.7489405, 11.9855865
}
# Re-recorded with the kernel's drag (#1346: AeroBuildup's viscous factor k_e,D0 removed from its induced drag),
# from BRYAN 6.1460437, JAGUAR 7.1115531, BELEMNITOS 4.9079007, RV-7 8.0806222, CHEKKER 7.4625361, WIESEL 9.8057437 m/s.
# Observed V_mp / V_md of these goldens: BRYAN 0.833, JAGUAR 0.799, BELEMNITOS 0.930, RV-7 0.799, CHEKKER 0.824, WIESEL 0.814. A parabolic polar gives
# 3^(-1/4) = 0.760; the real polar at Re 1e5 is not parabolic (canon entry, "Observed"). The ratio is
# reported, not asserted as a tolerance: no source gives one for a computed polar.


async def sink(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    return await compute(aircraft, request(*SLUGS))


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_regression_goldens_with_the_xlarge_model(member: FleetMember) -> None:
    result = await sink(member)
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    assert result.provenance.tool_versions == GOLDEN_TOOL_VERSIONS
    assert result.provenance.solver_settings == OPT_SETTINGS
    for quantity, value in zip(result.quantities, GOLDEN[member], strict=True):
        assert close(quantity.value, value, 1e-5), quantity.slug
        assert quantity.tool == "OPT"
    # ADR 0028 amended (#1342): per surface at its MAC and per device, the surface named
    assert_regime_per_surface(result.quantities[0].warnings, member.main_wing_name)


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_the_minimum_sink_speed_lies_below_the_minimum_drag_speed(
    member: FleetMember,
) -> None:
    """The sink power D V is least at a lower speed than the drag D: physics, not a tolerance."""
    result = await sink(member)
    values = {q.slug: q.value for q in result.quantities}
    v_mp, v_md = values["minimum-sink-speed"], values["minimum-drag-speed"]
    assert v_mp is not None
    assert v_md is not None
    assert v_mp < v_md
