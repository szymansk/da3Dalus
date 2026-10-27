"""The moment slope at the lift balance of the OPT adapter (canon ``static-margin-probe``), fast tier.

The adapter hands a worker everything it needs; the worker is tested with AeroSandbox faked at its
boundary, so its sweep, interpolation and error paths are covered without the real solver.
"""

import math
from types import SimpleNamespace

import numpy as np
import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import (
    MomentSlopeRequest,
    MomentSlopeSolution,
    OptiAdapter,
    moment_slope_worker,
)
from aero_kernel.tests.formula_builders import near
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve

pytestmark = pytest.mark.asyncio

MASS, GRAVITY, SPEED, X_CG = 1.5, 9.81, 12.0, 0.11
S_REF = 0.28
SLOPES = MomentSlopeSolution(alpha_deg=4.0, cl=0.55, cl_alpha=5.2, cm_alpha=-0.5)


def canned(result: MomentSlopeSolution) -> object:
    def worker(request: MomentSlopeRequest) -> WorkerOutcome[MomentSlopeSolution]:
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[MomentSlopeRequest] = []

    def worker(request: MomentSlopeRequest) -> WorkerOutcome[MomentSlopeSolution]:
        seen.append(request)
        return WorkerOutcome(value=SLOPES, diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "moment_slope_worker", worker)
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).moment_slope(
        plane, MASS, GRAVITY, AIR, SPEED, X_CG
    )
    (request,) = seen
    assert request.airplane == plane
    assert (request.mass_kg, request.gravity, request.air, request.v_ms, request.x_cg) == (
        MASS,
        GRAVITY,
        AIR,
        SPEED,
        X_CG,
    )
    assert result.solution == SLOPES


async def test_the_regime_at_the_speed_is_declared_by_the_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chord 0.2 m at 12 m/s is Re ~ 1.6e5, in the band: no Reynolds warning; at 3 m/s it is below."""
    monkeypatch.setattr(opti_module, "moment_slope_worker", canned(SLOPES))
    adapter = OptiAdapter(InProcessRuntime())
    fast = await adapter.moment_slope(airplane(), MASS, GRAVITY, AIR, SPEED, X_CG)
    slow = await adapter.moment_slope(airplane(), MASS, GRAVITY, AIR, 0.6, X_CG)
    assert fast.warnings == ()
    assert [w.code for w in slow.warnings] == ["reynolds_outside_band"]


@pytest.mark.parametrize(
    ("mass", "gravity", "speed", "x_cg", "parameter"),
    [
        (0.0, GRAVITY, SPEED, X_CG, "m"),
        (MASS, math.nan, SPEED, X_CG, "g"),
        (MASS, GRAVITY, -1.0, X_CG, "v"),
        (MASS, GRAVITY, SPEED, math.inf, "x_cg"),
    ],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
    mass: float,
    gravity: float,
    speed: float,
    x_cg: float,
    parameter: str,
) -> None:
    monkeypatch.setattr(opti_module, "moment_slope_worker", canned(SLOPES))
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).moment_slope(plane, mass, gravity, AIR, speed, x_cg)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == parameter


async def test_a_deflected_control_surface_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "moment_slope_worker", canned(SLOPES))
    deflected = airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).moment_slope(
            deflected, MASS, GRAVITY, AIR, SPEED, X_CG
        )
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).moment_slope(plane, MASS, GRAVITY, AIR, SPEED, X_CG)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


# --- the worker, with the solver boundary faked ------------------------------------------------


def install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cl_alpha: float = 5.2,
    cm_alpha: float = -0.5,
    polar: Polar | None = None,
) -> list[dict[str, object]]:
    """Fake AeroSandbox: the sweep is the stub lift curve, AeroBuildup returns the given slopes.

    Returns:
        The keyword arguments of every AeroBuildup constructor and stability call, in order.
    """
    asked: list[dict[str, object]] = []
    curve = polar or lift_curve(UPRIGHT_PEAK, upright=True)

    class AeroBuildup:
        def __init__(self, airplane_: object, op_point: object, **kwargs: object) -> None:
            asked.append({"op_point": op_point, **kwargs})

        def run_with_stability_derivatives(self, **flags: object) -> dict[str, object]:
            asked.append(dict(flags))
            return {
                "CL": np.array([0.55]),
                "CLa": np.array([cl_alpha]),
                "Cma": np.array([cm_alpha]),
            }

    def operating_point(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    fake = SimpleNamespace(AeroBuildup=AeroBuildup, OperatingPoint=operating_point)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake)

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=S_REF)

    def sweep(*_: object) -> Polar:
        return curve

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "sweep_polar", sweep)
    return asked


def request() -> MomentSlopeRequest:
    return MomentSlopeRequest(
        airplane=airplane(), mass_kg=MASS, gravity=GRAVITY, air=AIR, v_ms=SPEED, x_cg=X_CG
    )


async def test_the_worker_runs_aerobuildup_at_the_lift_balance_about_the_cg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stub curve is CL = 1.19 - 0.04 (15.75 - alpha) below the peak, so the wanted CL maps to alpha."""
    asked = install(monkeypatch)
    wanted = MASS * GRAVITY / (0.5 * AIR.density * SPEED**2 * S_REF)
    alpha = 15.75 - (1.19 - wanted) / 0.04
    solution = moment_slope_worker(request()).value
    assert near(solution.alpha_deg, alpha)
    assert (solution.cl_alpha, solution.cm_alpha) == (5.2, -0.5)
    constructor, stability = asked
    assert near(constructor["op_point"].alpha, alpha)  # type: ignore[attr-defined]
    assert constructor["op_point"].velocity == SPEED  # type: ignore[attr-defined]
    reference = request().airplane.xyz_ref
    assert constructor["xyz_ref"] == [X_CG, reference[1], reference[2]]
    assert constructor["model_size"] == opti_module.NEURALFOIL_MODEL_SIZE
    assert constructor["include_wave_drag"] is True
    assert stability == {"alpha": True, "beta": False, "p": False, "q": False, "r": False}


async def test_a_curve_that_never_reaches_the_wanted_lift_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    low = Polar(
        alpha_deg=(-1.0, 0.0, 1.0, 2.0, 3.0),
        cl=(0.1, 0.2, 0.3, 0.2, 0.1),
        cd=(0.05,) * 5,
        cm=(0.0,) * 5,
    )
    install(monkeypatch, polar=low)
    with pytest.raises(FormulaError) as raised:
        moment_slope_worker(request())
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "lift balance" in raised.value.message


async def test_a_sweep_without_a_peak_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    rising = Polar(alpha_deg=(0.0, 1.0, 2.0), cl=(0.1, 0.2, 0.3), cd=(0.05,) * 3, cm=(0.0,) * 3)
    install(monkeypatch, polar=rising)
    with pytest.raises(FormulaError) as raised:
        moment_slope_worker(request())
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


@pytest.mark.parametrize("cl_alpha", [0.0, -1.0, math.nan])
async def test_a_lift_slope_that_is_not_positive_and_finite_is_not_converged(
    monkeypatch: pytest.MonkeyPatch, cl_alpha: float
) -> None:
    install(monkeypatch, cl_alpha=cl_alpha)
    with pytest.raises(FormulaError) as raised:
        moment_slope_worker(request())
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "lift slope" in raised.value.message


async def test_a_moment_slope_that_is_not_finite_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, cm_alpha=math.nan)
    with pytest.raises(FormulaError) as raised:
        moment_slope_worker(request())
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "moment slope" in raised.value.message
