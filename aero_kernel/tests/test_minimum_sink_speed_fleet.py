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
    FUSELAGE_REJECTED,
    FleetMember,
    assert_rejected_for_the_fuselage,
    reference_document,
)

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
GOLDEN = {
    FleetMember.BRYAN: (6.1460437, 4.6544086, 0.9140074, 7.4468700),
    FleetMember.JAGUAR: (7.1115531, 5.5958411, 0.7834771, 9.0692794),
    FleetMember.BELEMNITOS: (4.9079007, 5.7739549, 0.9317612, 5.3792137),
    FleetMember.RV7: (8.0806222, 7.2014265, 0.8170156, 10.2315110),
}
OUTSIDE_RE_BAND = {FleetMember.BRYAN, FleetMember.JAGUAR, FleetMember.BELEMNITOS}
# Observed V_mp / V_md of these goldens: BRYAN 0.825, JAGUAR 0.784, BELEMNITOS 0.912, RV-7 0.790. A parabolic polar gives
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
    expected = {"reynolds_bubble_sensitive"}
    if member in OUTSIDE_RE_BAND:
        expected.add("reynolds_outside_band")  # ADR 0028: the tip chords are far below the band
    assert {w.code for w in result.quantities[0].warnings} >= expected


@pytest.mark.parametrize("member", list(FUSELAGE_REJECTED))
async def test_the_fuselage_aerosandbox_cannot_take_is_the_recorded_result(
    member: FleetMember,
) -> None:
    """CHEKKER's and WIESEL's fuselages carry a section with n_lower != n (README): the kernel
    declares it instead of computing, for every quantity that builds the AeroSandbox airplane."""
    assert_rejected_for_the_fuselage(member, (await sink(member)).quantities)


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
