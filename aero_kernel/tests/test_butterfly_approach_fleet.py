"""butterfly-approach on the RV-7 through the public engine, real AeroSandbox and IPOPT.

Aero tier. The RV-7 is the one aircraft of the reference fleet with a flap and an aileron on separate
surfaces and fleet flap values; it is **not a glider** and no crow measurement of it exists, so the
numbers are consistency checks of the machinery, never validation of a crow prediction
(aero_kernel/CLAUDE.md). The crow angles are test inputs, kept inside the range where the sweep
converges (the 60 / 20 deg crow of the exploration fails at one mix, see the evidence sheet).
"""

import math
from itertools import pairwise

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.devices import crow_configuration, flap_deflections, with_flaps_at
from aero_kernel.engine import evaluate
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import ComputeRequest, QuantityStatus
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import OptiAdapter, Stall
from aero_kernel.tests.formula_builders import close, solvers_with
from aero_kernel.tests.reference_fleet import FleetMember, aircraft_input, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

LANDING, FLAP_CROW, AILERON_UP = 30.0, 45.0, 15.0
MARGIN = 1.05
GRAVITY = 9.80665
SEA_LEVEL = AirState(
    density=1.2249991558877122,
    dynamic_viscosity=1.789380278077583e-05,
    speed_of_sound=340.2941077869353,
)


class Recording(OptiAdapter):
    """The real adapter, recording the airplane of every stall call and its answer."""

    def __init__(self) -> None:
        super().__init__(SolverRuntime())
        self.stalls: list[tuple[AirplaneGeometry, Stall]] = []

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        result = await super().stall(airplane, mass_kg, gravity, n_load, air)
        self.stalls.append((airplane, result))
        return result


def flap_angle(airplane: AirplaneGeometry) -> float:
    """The largest flap-like angle of the airplane: the flap of the crow configuration."""
    return max(angle for _, _, angle in flap_deflections(airplane))


async def crow() -> tuple[Recording, dict[str, float | None]]:
    recording = Recording()
    values = {
        "altitude": 0.0,
        "crow-flap-deflection": FLAP_CROW,
        "crow-aileron-deflection": AILERON_UP,
        "approach-speed-margin-target": MARGIN,
    }
    request = ComputeRequest(
        quantities=("butterfly-max-mix", "stall-speed-landing", "approach-speed")
    )
    result = await evaluate(
        shipped_build(),
        aircraft_input(FleetMember.RV7, values),
        request,
        solvers=solvers_with(opti=recording),
    )
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.OK, quantity
    return recording, {q.slug: q.value for q in result.quantities}


async def test_zero_mix_is_the_landing_stall_and_s_max_lands_on_the_approach_speed() -> None:
    recording, found = await crow()
    landing, approach, s_max = (
        found["stall-speed-landing"],
        found["approach-speed"],
        found["butterfly-max-mix"],
    )
    assert landing is not None
    assert approach is not None
    assert s_max is not None
    assert close(approach, MARGIN * landing, 1e-9)
    # eleven mixes plus the landing stall of `stall-speed-landing`; mix 0 is the landing airplane
    # itself (landing flap, level aileron), so it agrees with that stall (Q35)
    assert len(recording.stalls) == 12
    zero = min(recording.stalls, key=lambda call: flap_angle(call[0]))
    assert close(zero[1].solution.v_s, landing, 1e-4)
    # the stall speed rises with the mix, the approach speed is the landing one times the margin
    speeds = [
        call[1].solution.v_s for call in sorted(recording.stalls, key=lambda c: flap_angle(c[0]))
    ]
    assert 0.0 < s_max < 1.0
    # independent check of the interpolation: a real stall at the interpolated mix lands near V_app
    plane = AirplaneGeometry.model_validate(reference_document(FleetMember.RV7))
    cfg = crow_configuration(with_flaps_at(plane, LANDING), s_max, LANDING, FLAP_CROW, AILERON_UP)
    check = await OptiAdapter(SolverRuntime()).stall(
        cfg, FleetMember.RV7.mass_kg, GRAVITY, 1.0, SEA_LEVEL
    )
    assert math.isfinite(speeds[-1])
    assert all(b >= a - 1e-9 for a, b in pairwise(speeds))
    assert abs(check.solution.v_s - approach) / approach < 0.01
