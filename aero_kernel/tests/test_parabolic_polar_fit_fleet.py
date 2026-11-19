"""The parabola fit and its closed forms through the public compute(), real AeroSandbox (#1401).

Aero tier. The golden values are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what
this build computes (NeuralFoil model size xlarge, 48 level-flight points, sea level, the fleet member's
mass). The relations between the quantities (probe against optimisation, sink rate against the solver's
drag) are what the tests check beyond that.
"""

import importlib.metadata
import math

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, QuantityStatus
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.aerobuildup import evaluate_forces
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

GOLDEN_TOOL_VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}
SLUGS = (
    "zero-lift-drag-coefficient",
    "oswald-efficiency",
    "induced-drag-factor",
    "max-lift-to-drag-probe",
    "max-lift-to-drag-ratio",
    "minimum-drag-speed-probe",
    "minimum-drag-speed",
)
# C_D0, e, k, E_max probe, E_max of the optimisation, V_md probe, V_md (m/s): measured at 48 points.
GOLDEN = {
    FleetMember.BRYAN: (
        0.026976493288633007,
        0.7644839211165677,
        0.09743091104631407,
        9.752790053510006,
        9.744896983773835,
        8.100247890783676,
        7.711509030755531,
    ),
    FleetMember.ULTRA_STICK_120: (
        0.010000999207749304,
        0.7340878695491866,
        0.09113005204646399,
        16.56217994059028,
        15.86144202309478,
        23.499792225702507,
        22.148596166112437,
    ),
}


async def run(member: FleetMember) -> dict[str, float]:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0},
        }
    )
    result = await compute(aircraft, request(*SLUGS))
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    assert result.provenance.tool_versions == GOLDEN_TOOL_VERSIONS
    assert all(q.value is not None for q in result.quantities)
    fit_warnings = {w.code for q in result.quantities for w in q.warnings}
    assert "polar_fit_residual" in fit_warnings
    assert "polar_fit_nonphysical" not in fit_warnings
    return {q.slug: q.value for q in result.quantities if q.value is not None}


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_the_fit_and_its_probes_against_the_goldens(member: FleetMember) -> None:
    assert {n: importlib.metadata.version(n) for n in GOLDEN_TOOL_VERSIONS} == GOLDEN_TOOL_VERSIONS
    found = await run(member)
    for slug, expected in zip(SLUGS, GOLDEN[member], strict=True):
        assert close(found[slug], expected, 1e-5), slug


@pytest.mark.parametrize("member", list(GOLDEN))
async def test_the_closed_forms_are_consistent_with_the_fit(member: FleetMember) -> None:
    """k = 1 / (pi e AR) is the fitted slope; the probe E_max is 1 / (2 sqrt(C_D0 k)) of the same parabola."""
    found = await run(member)
    cd0, k = found["zero-lift-drag-coefficient"], found["induced-drag-factor"]
    assert close(found["max-lift-to-drag-probe"], 1.0 / (2.0 * math.sqrt(cd0 * k)), 1e-12)


async def test_every_level_flight_point_carries_the_weight_at_its_own_speed() -> None:
    """The level-flight polar, point by point: a fresh AeroBuildup run at (V, alpha) gives L = m g."""
    member = FleetMember.BRYAN
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    air = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)
    levels = (0.2, 0.5, 0.8, 1.0)
    weight = member.mass_kg * 9.80665
    request = opti_module.LevelPolarRequest(
        airplane=airplane,
        mass_kg=member.mass_kg,
        gravity=9.80665,
        air=air,
        cl_levels=levels,
        k_e_d0=0.83625,
        lift_tolerance=1e-6,
    )
    polar = opti_module.level_polar_worker(request).value
    converted = to_asb_airplane(airplane)
    area = float(converted.s_ref)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    for level, speed, alpha, cl, cd in zip(
        levels, polar.v_ms, polar.alpha_deg, polar.cl, polar.cd, strict=True
    ):
        lift, drag = evaluate_forces(
            converted, air, speed, alpha, opti_module.NEURALFOIL_MODEL_SIZE, 0.83625
        )
        assert close(lift, weight, 2e-6)
        assert close(speed, math.sqrt(2.0 * weight / (air.density * area * level)), 1e-12)
        assert close(cl, level, 2e-6)
        assert close(cd, drag / (0.5 * air.density * speed**2 * area), 1e-12)
    assert list(polar.v_ms) == sorted(polar.v_ms, reverse=True)
