"""The zero-lift problem of the OPT adapter: alpha_0 := root of C_L(V, alpha), C_Lalpha by AD there.

Fast tier: the adapter with a canned worker, and the worker with AeroSandbox and CasADi faked at the
solver boundary (the model function, IPOPT and the Jacobian).
"""

import math
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import RoutedRequest, WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.aero_model import model_key
from aero_kernel.solvers.opti import OptiAdapter, ZeroLiftRequest, ZeroLiftSolution
from aero_kernel.solvers.regime import regime_by_surface
from aero_kernel.tests.planform_stand_in import stand_in_surface_sections
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane

pytestmark = pytest.mark.asyncio

V_MS = 8.0
SOLUTION = ZeroLiftSolution(alpha_0_deg=-3.6, cl_alpha_per_rad=5.29)


def canned(seen: list[ZeroLiftRequest] | None = None) -> object:
    def worker(request: ZeroLiftRequest) -> WorkerOutcome[ZeroLiftSolution]:
        if seen is not None:
            seen.append(request)
        return WorkerOutcome(value=SOLUTION, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_hands_the_worker_the_point_and_the_airplanes_model_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The key is the one best glide and minimum sink use for the same airplane, so the solve is
    routed to the worker that already holds the model function (ch. 8.10)."""
    seen: list[ZeroLiftRequest] = []
    monkeypatch.setattr(opti_module, "zero_lift_worker", canned(seen))
    plane = airplane()
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.zero_lift(plane, AIR, V_MS)
    (request,) = seen
    assert (request.airplane, request.air, request.v_ms) == (plane, AIR, V_MS)
    expected_key = model_key(
        plane,
        roll_deg=0.0,
        model_size=opti_module.NEURALFOIL_MODEL_SIZE,
        tool_versions=adapter.tool_versions(),
    )
    assert request.model_key == expected_key
    assert result.solution == SOLUTION


async def test_the_regime_warnings_are_those_of_the_bound_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "zero_lift_worker", canned())
    result = await OptiAdapter(InProcessRuntime()).zero_lift(airplane(), AIR, 6.0)
    expected = regime_by_surface(
        stand_in_surface_sections(airplane()), 6.0, AIR.speed_of_sound, AIR.kinematic_viscosity
    )
    assert result.warnings == tuple(expected)


@pytest.mark.parametrize("v", [0.0, -1.0, math.nan, math.inf])
async def test_an_inadmissible_speed_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, v: float
) -> None:
    monkeypatch.setattr(opti_module, "zero_lift_worker", canned())
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.zero_lift(plane, AIR, v)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == "v"


async def test_a_deflected_aileron_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "zero_lift_worker", canned())
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await adapter.zero_lift(plane, AIR, V_MS)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_deflected_flap_is_evaluated_and_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    """The airplane as the geometry states it: a flap is evaluated, with its declared caveats."""
    monkeypatch.setattr(opti_module, "zero_lift_worker", canned())
    flapped = airplane(device=("flap", 10.0), hinge=0.75)
    result = await OptiAdapter(InProcessRuntime()).zero_lift(flapped, AIR, V_MS)
    (declared,) = [w for w in result.warnings if w.code == "control_surface_fit_range_unknown"]
    assert declared.detail["flaps"] == [
        {"wing": "Main", "device": "flap-1", "deflection_deg": 10.0}
    ]


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter, plane = OptiAdapter(InProcessRuntime()), airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.zero_lift(plane, AIR, V_MS)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


# --- the worker, with the solver boundary faked ------------------------------------------------


@dataclass
class Boundary:
    """What the faked AeroSandbox and CasADi saw and answer."""

    values: dict[str, float]
    error: Exception | None = None
    iterations: int = 3
    variables: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    constraints: list[tuple[str, object]] = field(default_factory=list[tuple[str, object]])
    solve_options: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    keys: list[str | None] = field(default_factory=list[str | None])
    minimised: list[object] = field(default_factory=list[object])


class Expr:
    """A symbolic stand-in: a name; comparing it records the constraint it builds."""

    def __init__(self, name: str, boundary: Boundary) -> None:
        self.name, self.boundary = name, boundary

    def __eq__(self, other: object) -> bool:  # `cl == 0` builds the constraint
        self.boundary.constraints.append((self.name, other))
        return True

    __hash__ = object.__hash__


class Solved:
    def __init__(self, values: dict[str, float], iterations: int) -> None:
        self.values, self.iterations = values, iterations

    def __call__(self, expression: Expr) -> float:
        return self.values[expression.name]

    def stats(self) -> dict[str, object]:
        return {"iter_count": self.iterations, "return_status": "Solve_Succeeded"}


def install(
    monkeypatch: pytest.MonkeyPatch,
    alpha: float = -3.6,
    slope_per_deg: float = 0.0923,
    error: Exception | None = None,
) -> tuple[Boundary, ZeroLiftRequest]:
    boundary = Boundary(
        values={"alpha": alpha, "CL": 1e-9, "dCL/dalpha": slope_per_deg}, error=error
    )

    class FakeOpti:
        def variable(self, **kwargs: object) -> Expr:
            boundary.variables.append(kwargs)
            return Expr("alpha", boundary)

        def subject_to(self, _: object) -> None:
            return None

        def minimize(self, expression: object) -> None:
            boundary.minimised.append(expression)

        def solve(self, **kwargs: object) -> Solved:
            boundary.solve_options.append(kwargs)
            if boundary.error is not None:
                raise boundary.error
            return Solved(boundary.values, boundary.iterations)

    def model(v: object, alpha_: Expr, air: object) -> dict[str, Expr]:
        assert (v, air) == (V_MS, AIR)
        return {"CL": Expr("CL", boundary), "L": Expr("L", boundary)}

    def aero_model(key: str | None, _airplane: object, _size: str) -> tuple[object, str]:
        boundary.keys.append(key)
        return model, "aero model reused from the worker's cache"

    def jacobian(expression: Expr, variable: Expr) -> Expr:
        return Expr(f"d{expression.name}/d{variable.name}", boundary)

    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: SimpleNamespace(Opti=FakeOpti))
    monkeypatch.setattr(opti_module, "load_casadi", lambda: SimpleNamespace(jacobian=jacobian))
    monkeypatch.setattr(opti_module, "aero_model", aero_model)

    def convert(_airplane: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28)

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    request = ZeroLiftRequest(airplane=airplane(), air=AIR, v_ms=V_MS, model_key="sha256:abc")
    return boundary, request


async def test_the_worker_returns_the_root_and_the_slope_per_radian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model's alpha is in degrees: dC_L/dalpha_rad = dC_L/dalpha_deg * 180/pi.
    Hand value: 0.0923 per deg * 57.29578 deg/rad = 5.28840 per rad."""
    _, request = install(monkeypatch, alpha=-3.6, slope_per_deg=0.0923)
    outcome = opti_module.zero_lift_worker(request)
    assert outcome.value.alpha_0_deg == -3.6
    assert math.isclose(outcome.value.cl_alpha_per_rad, 5.288400, rel_tol=1e-6)


async def test_the_worker_starts_at_zero_with_no_angle_range_and_solves_c_l_equal_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, request = install(monkeypatch)
    opti_module.zero_lift_worker(request)
    assert boundary.variables == [{"init_guess": 0.0}]  # no lower_bound, no upper_bound
    assert boundary.constraints == [("CL", 0.0)]
    assert boundary.minimised == []  # a root, not an optimum


async def test_the_worker_uses_the_iteration_limit_and_tolerance_of_the_opti_problems(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, request = install(monkeypatch)
    opti_module.zero_lift_worker(request)
    (options,) = boundary.solve_options
    assert options["max_iter"] == opti_module.MAX_ITERATIONS
    assert options["options"] == {"ipopt.tol": opti_module.IPOPT_TOLERANCE}
    assert opti_module.IPOPT_TOLERANCE == 1e-8


async def test_the_worker_reuses_the_model_function_of_the_requests_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, request = install(monkeypatch)
    outcome = opti_module.zero_lift_worker(request)
    assert boundary.keys == ["sha256:abc"]
    assert outcome.diagnostics.iterations == 3
    assert outcome.diagnostics.solver_status == "Solve_Succeeded"
    assert "aero model reused from the worker's cache" in outcome.diagnostics.notes


async def test_an_ipopt_failure_is_not_converged_with_the_solver_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = RuntimeError("Solver failed. return_status is 'Maximum_Iterations_Exceeded'")
    _, request = install(monkeypatch, error=failure)
    with pytest.raises(FormulaError) as raised:
        opti_module.zero_lift_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "Maximum_Iterations_Exceeded" in raised.value.message
    assert "zero-lift" in raised.value.message


@pytest.mark.parametrize(("alpha", "slope"), [(math.nan, 0.09), (-3.6, math.nan), (-3.6, math.inf)])
async def test_a_non_finite_root_or_slope_is_not_converged_never_a_value(
    monkeypatch: pytest.MonkeyPatch, alpha: float, slope: float
) -> None:
    _, request = install(monkeypatch, alpha=alpha, slope_per_deg=slope)
    with pytest.raises(FormulaError) as raised:
        opti_module.zero_lift_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_the_worker_runs_in_the_pool_routed_by_its_model_key() -> None:
    """The request is a ``RoutedRequest``: the runtime routes it by ``model_key`` (ch. 8.10)."""
    request = ZeroLiftRequest(airplane=airplane(), air=AIR, v_ms=V_MS, model_key="sha256:abc")
    assert isinstance(request, RoutedRequest)
