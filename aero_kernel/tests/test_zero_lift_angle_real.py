"""zero-lift-angle and aerobuildup-evaluation against the real AeroBuildup (aero tier).

The BRYAN reference of the canon entry (8 m/s, sea level): root -3.6 deg, C_Lalpha 5.29 /rad, three
IPOPT iterations, residual |C_L| about 1e-9. The slope is the automatic derivative; a central finite
difference of the same model function at the root checks it (the production code stays AD). Values
are regression, not validation (aero_kernel/CLAUDE.md).
"""

import math

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.solvers import aero_model as aero_model_module
from aero_kernel.solvers.aero_model import AeroModel, install_model_cache, installed_model_cache
from aero_kernel.solvers.aerobuildup import sweep_polar
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.opti import NEURALFOIL_MODEL_SIZE, ZeroLiftRequest, zero_lift_worker
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.solver_builders import K_E_D0
from aero_kernel.tests.test_aero_model_real import key
from aero_kernel.tests.test_stall_speed_fleet import sea_level_air

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

MEMBER = FleetMember.BRYAN
V_REFERENCE = 8.0
# The step of the finite-difference check, in degrees: small against the curvature of the lift
# curve, large against the rounding of C_L (about 1e-16).
FD_STEP_DEG = 1e-3


# The tool versions the goldens hold for (as in the other fleet tests).
GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
# Regression goldens, BRYAN at sea level and its mass, NeuralFoil xlarge (measured 2026-11-01; re-recorded
# 2026-11-03 for #1346: the kernel's drag moves V_md and V_mp, and with them the root and the slope).
# Re-recorded for #1355 slice 2 (BRYAN's canopy merged); before: 7.230662994492074,
# -3.515387311381626, 4.980706259404333, 6.02251899624491, -3.421853220357826, 4.4124252804453326.
GOLDEN = {
    "minimum-drag-speed": 7.711509030755531,  # #1358: was 7.664926694158355
    "zero-lift-angle-best-glide": -3.6314904698490476,  # #1358: was -3.6132002046649974
    "lift-curve-slope-best-glide": 5.044253788657642,  # #1358: was 5.0559843432476805
    "minimum-sink-speed": 6.454682494804102,  # #1358: was 6.412624702401902
    "zero-lift-angle-minimum-sink": -3.4967447439236956,  # #1358: was -3.481523436882498
    "lift-curve-slope-minimum-sink": 4.498426577323154,  # #1358: was 4.501778851784002
}


def bryan() -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(reference_document(MEMBER))


@pytest.fixture
def worker_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a model cache in this process as the runtime does in a worker; removed afterwards."""
    monkeypatch.setattr(aero_model_module._INSTALLED, "cache", None)  # pyright: ignore[reportPrivateUsage]  # the process-local holder under test
    install_model_cache(1)


@pytest.mark.usefixtures("worker_cache")
async def test_bryan_at_8_m_s_the_root_and_the_ad_slope_match_a_finite_difference() -> None:
    airplane, air = bryan(), sea_level_air()
    the_key = key(airplane, 0.0)
    outcome = zero_lift_worker(
        ZeroLiftRequest(airplane=airplane, air=air, v_ms=V_REFERENCE, model_key=the_key)
    )
    solution = outcome.value
    # #1355 slice 2 (canopy merged): before -3.624 deg and 5.284 /rad
    assert math.isclose(solution.alpha_0_deg, -3.674637, abs_tol=0.01), (
        solution
    )  # #1358: was -3.663
    assert math.isclose(solution.cl_alpha_per_rad, 5.142801, rel_tol=1e-3), (
        solution
    )  # #1358: was 5.173
    assert outcome.diagnostics.solver_status == "Solve_Succeeded"
    assert outcome.diagnostics.iterations is not None
    assert outcome.diagnostics.iterations <= 10

    cache = installed_model_cache()
    assert cache is not None

    def unexpected_build() -> AeroModel:
        raise AssertionError("the worker's model function must be held")

    model, held = cache.get(the_key, unexpected_build)
    assert held

    def cl(alpha_deg: float) -> float:
        return float(model(V_REFERENCE, alpha_deg, air)["CL"])

    assert abs(cl(solution.alpha_0_deg)) < 1e-7  # IPOPT tol 1e-8 on the scaled constraint
    per_deg = (cl(solution.alpha_0_deg + FD_STEP_DEG) - cl(solution.alpha_0_deg - FD_STEP_DEG)) / (
        2.0 * FD_STEP_DEG
    )
    assert math.isclose(solution.cl_alpha_per_rad, math.degrees(per_deg), rel_tol=1e-6)


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


async def test_bryan_zero_lift_angle_and_slope_at_both_optima_through_compute() -> None:
    """Regression goldens at V_md and V_mp (sea level, BRYAN's mass). The root moves with the
    Reynolds number: at the lower V_mp it lies above that at V_md (canon entry: -3.6 deg at 8 m/s,
    -4.3 deg at 12 m/s), and the slope there is lower."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(MEMBER),
            "values": {"aircraft-mass": MEMBER.mass_kg, "altitude": 0.0},
        }
    )
    result = await compute(aircraft, request(*GOLDEN))
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert result.provenance.tool_versions == GOLDEN_TOOL_VERSIONS
    for slug, golden in GOLDEN.items():
        assert close(quantities[slug].value, golden, 1e-6), (slug, quantities[slug].value)
    assert quantities["zero-lift-angle-best-glide"].unit == "deg"
    assert quantities["lift-curve-slope-minimum-sink"].unit == "1/rad"
    assert GOLDEN["minimum-sink-speed"] < GOLDEN["minimum-drag-speed"]
    assert GOLDEN["zero-lift-angle-best-glide"] < GOLDEN["zero-lift-angle-minimum-sink"]


async def test_bryan_forces_and_glide_ratio_agree_with_the_sweep_at_the_same_point() -> None:
    """L = C_L q S_ref and L/D = C_L/C_D of a one-point sweep: both are AeroBuildup at (V, alpha)."""
    v, alpha = 8.0, 4.0
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(MEMBER),
            "values": {
                "aircraft-mass": MEMBER.mass_kg,
                "altitude": 0.0,
                "flight-speed": v,
                "angle-of-attack": alpha,
            },
        }
    )
    result = await compute(aircraft, request("lift-force", "drag-force", "lift-to-drag-ratio"))
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    lift, drag = quantities["lift-force"].value, quantities["drag-force"].value
    ratio = quantities["lift-to-drag-ratio"].value
    assert lift is not None
    assert drag is not None
    assert ratio is not None
    assert drag > 0.0
    assert math.isclose(ratio, lift / drag, rel_tol=1e-12)
    air = sea_level_air()
    converted = to_asb_airplane(bryan())
    polar = sweep_polar(converted, air, v, [alpha, alpha + 1.0], NEURALFOIL_MODEL_SIZE, K_E_D0)
    q_s = 0.5 * air.density * v**2 * float(converted.s_ref)
    assert math.isclose(lift, polar.cl[0] * q_s, rel_tol=1e-9)
    assert math.isclose(ratio, polar.cl[0] / polar.cd[0], rel_tol=1e-9)
