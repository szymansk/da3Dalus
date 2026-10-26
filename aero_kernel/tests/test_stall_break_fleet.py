"""stall-break of BRYAN and JAGUAR through the public compute(), real AeroSandbox (aero tier).

The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this
build computes (NeuralFoil model size xlarge, the tool versions asserted below) so that a change of
code or of AeroSandbox is noticed; they are not measurements of the aircraft.
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

SLUGS = ("alpha-break", "stall-break-width", "angle-of-attack-stall")
GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
# Regression goldens at sea level, mass of the fleet member, ISA, f = 0.10, NeuralFoil model size
# xlarge: (alpha_break deg, width deg, alpha_S deg). width = alpha_break - alpha_S.
GOLDEN = {
    FleetMember.BRYAN: (14.7822439, 1.5835136, 13.1987303),
    FleetMember.JAGUAR: (11.0671515, 1.1418603, 9.9252912),
    FleetMember.BELEMNITOS: (11.0568417, 1.4866984, 9.5701434),
    FleetMember.RV7: (16.3483882, 1.2300212, 15.1183671),
}


async def stall_break(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    return await compute(aircraft, request(*SLUGS))


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_regression_goldens_with_the_xlarge_model(member: FleetMember) -> None:
    result = await stall_break(member)
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    assert result.provenance.tool_versions == GOLDEN_TOOL_VERSIONS
    assert result.provenance.solver_settings == OPT_SETTINGS
    for quantity, value in zip(result.quantities, GOLDEN[member], strict=True):
        assert close(quantity.value, value, 1e-5), quantity.slug
        assert quantity.tool == "OPT"
    used = {d.slug: d.value for d in result.provenance.defaults_used}
    assert used["stall-break-fraction"] == 0.10  # the convention, recorded with its source


@pytest.mark.parametrize("member", list(FUSELAGE_REJECTED))
async def test_the_fuselage_aerosandbox_cannot_take_is_the_recorded_result(
    member: FleetMember,
) -> None:
    """CHEKKER's and WIESEL's fuselages carry a section with n_lower != n (README): the stall angle
    is the declared error and the break, which waits for it, fails upstream."""
    assert_rejected_for_the_fuselage(member, (await stall_break(member)).quantities)


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_the_resolution_check_finds_both_sweeps_in_agreement(member: FleetMember) -> None:
    """Halving the sweep step moves the break by less than one published step (0.25 deg): no
    ``stall_break_resolution`` defect on either reference airplane."""
    result = await stall_break(member)
    codes = {w.code for q in result.quantities for w in q.warnings}
    assert "stall_break_resolution" not in codes


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_the_width_is_the_break_minus_the_stall_angle(member: FleetMember) -> None:
    result = await stall_break(member)
    values = {q.slug: q.value for q in result.quantities}
    alpha_break, width, alpha_s = (
        values["alpha-break"],
        values["stall-break-width"],
        values["angle-of-attack-stall"],
    )
    assert alpha_break is not None
    assert width is not None
    assert alpha_s is not None
    assert close(width, alpha_break - alpha_s, 1e-9)
