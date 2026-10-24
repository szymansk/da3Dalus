"""The best-glide problem of the OPT adapter: min D s.t. L = n m g on the pre-stall branch."""

import importlib.metadata
import math
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.base import regime_by_wing
from aero_kernel.solvers.opti import (
    BestGlideSolution,
    OptiAdapter,
    StallRequest,
)
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve

pytestmark = pytest.mark.asyncio

MASS, GRAVITY = 1.5, 9.81


def glide(v_md: float = 12.0) -> BestGlideSolution:
    return BestGlideSolution(v_md=v_md, e_max=20.0, alpha_md=4.0, cl_md=0.55)


def canned(result: BestGlideSolution) -> object:
    def worker(request: StallRequest) -> WorkerOutcome[BestGlideSolution]:
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_glide_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[BestGlideSolution]:
        seen.append(request)
        return WorkerOutcome(value=glide(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "best_glide_worker", worker)
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).best_glide(plane, MASS, GRAVITY, 1.0, AIR)
    (request,) = seen
    assert (request.mass_kg, request.gravity, request.n_load, request.air) == (
        MASS,
        GRAVITY,
        1.0,
        AIR,
    )
    assert request.airplane == plane
    assert result.solution == glide()


async def test_the_glide_carries_the_regime_warnings_of_its_speed_per_wing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At 12 m/s the main chords (0.2 / 0.1 m) give Re 1.4e5 / 6.9e4 (bubble-sensitive), a 2 mm tail
    tip gives Re 1.4e3: only the tail is outside the band, and the warning names it."""
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide(12.0)))
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane(tail_chords=(0.05, 0.002))
    result = await adapter.best_glide(plane, MASS, GRAVITY, 1.0, AIR)
    outside = [w for w in result.warnings if w.code == "reynolds_outside_band"]
    (warning,) = outside
    assert warning.detail["wing"] == "Tail"
    assert all(w.origin is None for w in result.warnings)


async def test_the_regime_warnings_are_those_of_the_optimum_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m at 6 m/s: Re 8.2e4 and 4.1e4, so the smaller chord is bubble-sensitive.
    Evaluated at three times the speed (18 m/s, Re > 1.2e5) there would be no warning at all."""
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide(6.0)))
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.best_glide(airplane(), MASS, GRAVITY, 1.0, AIR)
    expected = regime_by_wing(
        {"Main": [0.2, 0.1]}, 6.0, AIR.speed_of_sound, AIR.kinematic_viscosity
    )
    assert [w.code for w in expected] == ["reynolds_bubble_sensitive"]
    assert result.warnings == tuple(expected)
    fast = canned(glide(18.0))
    monkeypatch.setattr(opti_module, "best_glide_worker", fast)
    assert (await adapter.best_glide(airplane(), MASS, GRAVITY, 1.0, AIR)).warnings == ()


@pytest.mark.parametrize(
    ("mass", "gravity", "n_load"),
    [
        (0.0, 9.81, 1.0),
        (1.5, -1.0, 1.0),
        (1.5, 9.81, 0.0),
        (1.5, 9.81, -1.0),
        (1.5, 9.81, math.nan),
    ],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, n_load: float
) -> None:
    """Best glide lives on the upright branch: a negative load factor is no input of it."""
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide()))
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.best_glide(plane, mass, gravity, n_load, AIR)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_deflected_control_surface_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide()))
    adapter = OptiAdapter(InProcessRuntime())
    deflected = airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await adapter.best_glide(deflected, MASS, GRAVITY, 1.0, AIR)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "deflected control surfaces are not yet passed to AeroBuildup" in raised.value.message


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.best_glide(plane, MASS, GRAVITY, 1.0, AIR)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_glide_uses_the_adapters_versions_and_settings() -> None:
    adapter = OptiAdapter(InProcessRuntime())
    assert adapter.tool_versions() == {
        "aerosandbox": importlib.metadata.version("aerosandbox"),
        "neuralfoil": importlib.metadata.version("neuralfoil"),
    }
    assert adapter.settings() == {"neuralfoil_model_size": "xlarge"}


# --- the worker, with the solver boundary faked ------------------------------------------------


def install_optimum(
    monkeypatch: pytest.MonkeyPatch,
    v: float,
    alpha: float,
    drag: float = 0.5,
    cl: float = 0.55,
    error: Exception | None = None,
    objective: list[object] | None = None,
) -> StallRequest:
    """Fake AeroSandbox so that IPOPT 'returns' (v, alpha) with drag and C_L there."""
    polar = lift_curve(UPRIGHT_PEAK, upright=True)
    values: dict[str, float] = {"speed": v, "alpha": alpha, "D": drag, "CL": cl}
    recorded: list[object] = [] if objective is None else objective

    class Expr:
        def __init__(self, name: str) -> None:
            self.name = name

        def __eq__(self, other: object) -> bool:  # `aero["L"] == lift` builds a constraint
            return True

        __hash__ = object.__hash__

        def __mul__(self, other: object) -> "Expr":  # a product records the names of its factors
            return Expr(f"{self.name}*{getattr(other, 'name', other)}")

    class FakeOpti:
        def __init__(self) -> None:
            self.count = 0

        def variable(self, **_: object) -> Expr:
            self.count += 1
            return Expr("speed" if self.count == 1 else "alpha")

        def subject_to(self, _: object) -> None:
            return None

        def minimize(self, expression: object) -> None:
            recorded.append(expression)

        def solve(self, **_: object) -> object:
            if error is not None:
                raise error

            def solved(expression: Expr) -> float:
                return values[expression.name]

            return solved

    def operating_point(**_: object) -> None:
        return None

    def aerobuildup(*_: object, **__: object) -> SimpleNamespace:
        aero = {"L": Expr("L"), "D": Expr("D"), "CL": Expr("CL")}
        return SimpleNamespace(run=lambda: aero)

    def sweep(*_: object) -> Polar:
        return polar

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28)

    fake = SimpleNamespace(Opti=FakeOpti, OperatingPoint=operating_point, AeroBuildup=aerobuildup)
    monkeypatch.setattr(opti_module, "sweep_polar", sweep)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake)
    request = StallRequest(airplane=airplane(), mass_kg=MASS, gravity=GRAVITY, n_load=1.0, air=AIR)
    return request


async def test_the_worker_reads_the_optimum_drag_and_lift_coefficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """e_max = m g / D at the optimum: 1.5 * 9.81 / 0.5 = 29.43."""
    request = install_optimum(monkeypatch, 12.0, 4.0, drag=0.5, cl=0.55)
    outcome = opti_module.best_glide_worker(request)
    solution = outcome.value
    assert (solution.v_md, solution.alpha_md, solution.cl_md) == (12.0, 4.0, 0.55)
    assert math.isclose(solution.e_max, MASS * GRAVITY / 0.5, rel_tol=1e-12)


async def test_the_worker_minimises_the_drag_not_the_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    objective: list[object] = []
    request = install_optimum(monkeypatch, 12.0, 4.0, objective=objective)
    opti_module.best_glide_worker(request)
    (minimised,) = objective
    assert minimised.name == "D"  # type: ignore[attr-defined]


V_HIGH = opti_module.V_MAX_MACH * AIR.speed_of_sound
V_LOW = opti_module.V_MIN_MS


@pytest.mark.parametrize(
    ("v", "alpha", "variable"),
    [
        (V_HIGH, 4.0, "V"),
        (V_LOW, 4.0, "V"),
        (12.0, opti_module.ALPHA_MIN_DEG, "alpha"),
        (12.0, 16.0, "alpha"),  # the window's upper edge: the first peak (15.75) plus one step
    ],
)
async def test_an_optimum_on_a_bound_is_not_converged_and_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, v: float, alpha: float, variable: str
) -> None:
    request = install_optimum(monkeypatch, v, alpha)
    with pytest.raises(FormulaError) as raised:
        opti_module.best_glide_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["variable"] == variable
    assert "best-glide" in raised.value.message


async def test_an_ipopt_failure_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_optimum(monkeypatch, 12.0, 4.0, error=RuntimeError("Infeasible_Problem"))
    with pytest.raises(FormulaError) as raised:
        opti_module.best_glide_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_any_other_exception_stays_an_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_optimum(monkeypatch, 12.0, 4.0, error=ValueError("a bug"))
    with pytest.raises(ValueError, match="a bug"):
        opti_module.best_glide_worker(request)
