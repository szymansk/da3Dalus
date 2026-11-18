"""The glide point of the OPT adapter: the steady glide at a given speed (canon butterfly-approach).

Fast tier: the adapter with a canned worker.
"""

import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import GlidePointSolution, GlideRequest, OptiAdapter
from aero_kernel.tests.solver_builders import AIR, K_E_D0, InProcessRuntime, airplane

pytestmark = pytest.mark.asyncio

SOLUTION = GlidePointSolution(alpha_deg=4.0, cl=0.8, cd=0.05, glide_angle_deg=3.58)


def canned(seen: list[GlideRequest]) -> object:
    def worker(request: GlideRequest) -> WorkerOutcome[GlidePointSolution]:
        seen.append(request)
        return WorkerOutcome(value=SOLUTION, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_hands_the_worker_the_point_and_declares_the_drag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[GlideRequest] = []
    monkeypatch.setattr(opti_module, "glide_point_worker", canned(seen))
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).glide_point(plane, 1.5, 9.81, AIR, 8.0)
    (request,) = seen
    assert (request.airplane, request.mass_kg, request.gravity, request.v_ms) == (
        plane,
        1.5,
        9.81,
        8.0,
    )
    assert request.k_e_d0 == K_E_D0
    assert result.solution == SOLUTION
    assert "induced_drag_viscous_factor_removed" in {w.code for w in result.warnings}


@pytest.mark.parametrize("v", [0.0, -1.0, math.nan, math.inf])
async def test_an_inadmissible_speed_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, v: float
) -> None:
    monkeypatch.setattr(opti_module, "glide_point_worker", canned([]))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).glide_point(airplane(), 1.5, 9.81, AIR, v)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == "v"


@pytest.mark.parametrize(("mass", "gravity", "name"), [(0.0, 9.81, "m"), (1.5, -1.0, "g")])
async def test_an_inadmissible_mass_or_gravity_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, name: str
) -> None:
    monkeypatch.setattr(opti_module, "glide_point_worker", canned([]))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).glide_point(airplane(), mass, gravity, AIR, 8.0)
    assert raised.value.parameter == name


async def test_a_deflected_flap_is_evaluated_and_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "glide_point_worker", canned([]))
    flapped = airplane(device=("flap", 10.0), hinge=0.75)
    result = await OptiAdapter(InProcessRuntime()).glide_point(flapped, 1.5, 9.81, AIR, 8.0)
    assert "control_surface_fit_range_unknown" in {w.code for w in result.warnings}
