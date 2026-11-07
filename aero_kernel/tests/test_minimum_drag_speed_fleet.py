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
    FleetMember,
    bryan_as_the_prototype,
    convert_with_the_true_body_axes,
    reference_document,
)
from aero_kernel.tests.test_regime_fleet import assert_regime_per_surface

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

SLUGS = (
    "minimum-drag-speed",
    "max-lift-to-drag-ratio",
    "angle-of-attack-best-glide",
    "lift-coefficient-best-glide",
)
# k_e,D0 = 1: the kernel's drag D_profile + k_e,D0 * D_induced is then AeroBuildup's own (#1346), the
# drag the prototype used.
AEROBUILDUP_AS_IS = 1.0
# The tool versions the goldens hold for. A different version may move them; this is then noticed
# here (and the goldens are re-recorded deliberately), not discovered later.
GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
# Regression goldens at sea level, mass of the fleet member, ISA, AeroSandbox's S_ref of the main wing (gh-1240),
# NeuralFoil model size xlarge: (V_md m/s, (L/D)max, alpha_md deg, C_L,md). Re-recorded with the kernel's drag
# (#1346: AeroBuildup's viscous factor k_e,D0 removed from its induced drag); before, V_md / (L/D)max were BRYAN
# 7.4468700 / 7.7276780, JAGUAR 9.0692794 / 10.4719556, BELEMNITOS 5.3792137 / 13.8824812, RV-7 10.2315110 /
# 9.5383095, CHEKKER 9.1449363 / 9.2766026, WIESEL 12.5389487 / 11.8938174.
# BRYAN re-recorded for #1355 slice 2 (its canopy merged into the fuselage, only the visible part counts);
# before: (7.2306630, 8.3568527, 1.7236595, 0.6603661).
GOLDEN = {
    FleetMember.BRYAN: (
        7.7115090,
        9.7448970,
        0.9138034,
        0.5805802,
    ),  # #1358: was 7.6649267, 9.6087249, 0.9810230, 0.5876584
    FleetMember.JAGUAR: (
        8.9849874,
        11.4240420,
        2.2086100,
        0.4908178,
    ),  # #1358: was 8.8849618, 11.0911866, 2.3196645, 0.5019311
    FleetMember.BELEMNITOS: (
        5.2599903,
        14.8435692,
        4.4637211,
        0.8111968,
    ),  # #1358: was 14.8391368, 4.4632809
    FleetMember.RV7: (
        9.9524821,
        10.3440635,
        3.2120554,
        0.5385886,
    ),  # #1358: was 9.9423059, 10.2825158, 3.2198890, 0.5396917
    FleetMember.CHEKKER: (
        9.7394293,
        11.9131723,
        0.0388367,
        0.5450933,
    ),  # #1358: was 8.8958176, 9.9654926, 1.3233626, 0.6533805
    FleetMember.WIESEL: (
        12.0893466,
        12.8538066,
        3.4526886,
        0.4874568,
    ),  # #1358: was 11.9855865, 12.6842314, 3.5502794, 0.4959332
}


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
    # ADR 0028 amended (#1342): per surface at its MAC and per device, the surface named
    assert_regime_per_surface(result.quantities[0].warnings, member.main_wing_name)


async def test_bryan_best_glide_where_the_prototype_found_it_with_the_small_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prototype (CRRCSim branch, ERGEBNISSE_STABILITAET.md, 151 g): V_md = 7.82 m/s, C_L = 0.5656.

    The prototype used AeroSandbox's default NeuralFoil model, "small", and AeroBuildup's drag as it
    is, so the worker is run in this process with that size and with k_e,D0 = 1 (the kernel's drag
    is then AeroBuildup's own, #1346): 7.818 m/s (0.02 % from the prototype), C_L 0.5662 (0.1 %),
    (L/D)max 7.78. With the kernel's "xlarge" and AeroBuildup as is the same airplane gives
    7.447 m/s, 4.8 % lower: the model size, not the procedure, is the difference. The prototype
    had no canopy merge, so its geometry is BRYAN with the canopy a body of its own (#1355).
    """
    installed = {name: importlib.metadata.version(name) for name in GOLDEN_TOOL_VERSIONS}
    assert installed == GOLDEN_TOOL_VERSIONS  # the 7.8181 below holds for these versions only
    monkeypatch.setattr(opti_module, "NEURALFOIL_MODEL_SIZE", "small")
    convert_with_the_true_body_axes(monkeypatch)  # nor did it straighten the body axes (#1358)
    request_ = StallRequest(
        airplane=AirplaneGeometry.model_validate(bryan_as_the_prototype()),
        mass_kg=FleetMember.BRYAN.mass_kg,
        gravity=9.80665,
        n_load=1.0,
        air=AirState(
            density=1.2249991558877122,
            dynamic_viscosity=1.789380278077583e-05,
            speed_of_sound=340.2941077869353,
        ),
        k_e_d0=AEROBUILDUP_AS_IS,
    )
    solution = opti_module.best_glide_worker(request_).value
    assert close(solution.v_md, 7.82, 2e-3)
    assert close(solution.cl_md, 0.5656, 2e-3)
    assert close(solution.v_md, 7.8181, 1e-4)  # regression of the small model
