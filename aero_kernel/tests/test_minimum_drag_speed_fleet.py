"""minimum-drag-speed of BRYAN and JAGUAR through the public compute(), real AeroSandbox and IPOPT.

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they pin
what this build computes (NeuralFoil model size xlarge, the tool versions asserted below) so that a
change of code or of AeroSandbox is noticed; they are not measurements of the aircraft.
"""

import importlib.metadata

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import StallRequest
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
    "minimum-drag-speed",
    "max-lift-to-drag-ratio",
    "angle-of-attack-best-glide",
    "lift-coefficient-best-glide",
)
# The tool versions the goldens hold for. A different version may move them; this is then noticed
# here (and the goldens are re-recorded deliberately), not discovered later.
GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
# Regression goldens at sea level, mass of the fleet member, ISA, AeroSandbox's S_ref of the main wing (gh-1240),
# NeuralFoil model size xlarge: (V_md m/s, (L/D)max, alpha_md deg, C_L,md).
GOLDEN = {
    FleetMember.BRYAN: (7.4468700, 7.7276780, 1.3379343, 0.6225775),
    FleetMember.JAGUAR: (9.0692794, 10.4719556, 2.1200951, 0.4817366),
    FleetMember.BELEMNITOS: (5.3792137, 13.8824812, 4.1222829, 0.7756370),
    FleetMember.RV7: (10.2315110, 9.5383095, 2.7798438, 0.5096129),
}
# The aircraft whose tip chords fall below the Re band at 10 m/s as well as into the bubble-sensitive
# range (README: RV-7's chords keep it inside the band).
OUTSIDE_RE_BAND = {FleetMember.BRYAN, FleetMember.JAGUAR, FleetMember.BELEMNITOS}


async def glide(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    return await compute(aircraft, request(*SLUGS))


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_regression_goldens_with_the_xlarge_model(member: FleetMember) -> None:
    result = await glide(member)
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
    named = {
        str(w.detail["wing"])
        for w in result.quantities[0].warnings
        if w.code.startswith("reynolds_")
    }
    # the surface that is out is named: the main wing, or for RV-7 (inside the band) its tails
    assert named >= (
        {member.main_wing_name} if member in OUTSIDE_RE_BAND else {"elevator", "rudder"}
    )


@pytest.mark.parametrize("member", list(FUSELAGE_REJECTED))
async def test_the_fuselage_aerosandbox_cannot_take_is_the_recorded_result(
    member: FleetMember,
) -> None:
    """CHEKKER's and WIESEL's fuselages carry a section with n_lower != n (README): the kernel
    declares it instead of computing, for every quantity that builds the AeroSandbox airplane."""
    assert_rejected_for_the_fuselage(member, (await glide(member)).quantities)


async def test_bryan_best_glide_where_the_prototype_found_it_with_the_small_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prototype (CRRCSim branch, ERGEBNISSE_STABILITAET.md, 151 g): V_md = 7.82 m/s, C_L = 0.5656.

    The prototype used AeroSandbox's default NeuralFoil model, "small", so the worker is run in this
    process with that size: 7.818 m/s (0.02 % from the prototype), C_L 0.5662 (0.1 %), (L/D)max 7.78.
    With the kernel's "xlarge" the same airplane gives 7.447 m/s, 4.8 % lower: the model size, not
    the procedure, is the difference.
    """
    installed = {name: importlib.metadata.version(name) for name in GOLDEN_TOOL_VERSIONS}
    assert installed == GOLDEN_TOOL_VERSIONS  # the 7.8181 below holds for these versions only
    monkeypatch.setattr(opti_module, "NEURALFOIL_MODEL_SIZE", "small")
    request_ = StallRequest(
        airplane=AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN)),
        mass_kg=FleetMember.BRYAN.mass_kg,
        gravity=9.80665,
        n_load=1.0,
        air=AirState(
            density=1.2249991558877122,
            dynamic_viscosity=1.789380278077583e-05,
            speed_of_sound=340.2941077869353,
        ),
    )
    solution = opti_module.best_glide_worker(request_).value
    assert close(solution.v_md, 7.82, 2e-3)
    assert close(solution.cl_md, 0.5656, 2e-3)
    assert close(solution.v_md, 7.8181, 1e-4)  # regression of the small model
