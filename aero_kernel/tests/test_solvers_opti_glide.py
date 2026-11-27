"""The best-glide problem of the OPT adapter: min D s.t. L = n m g on the pre-stall branch."""

import importlib.metadata
import math
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import KernelWarning, Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import (
    BestGlideSolution,
    MinSinkSolution,
    OptiAdapter,
    StallRequest,
)
from aero_kernel.solvers.regime import regime_by_surface
from aero_kernel.tests.asb_fakes import RecordingBoundary
from aero_kernel.tests.formula_builders import OPT_SETTINGS
from aero_kernel.tests.planform_stand_in import canon_bands, stand_in_surface_sections
from aero_kernel.tests.solver_builders import (
    AIR,
    K_E_D0,
    InProcessRuntime,
    airplane,
    direct_aero_model,
    drag_notice,
)
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
    assert request.k_e_d0 == K_E_D0
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
    expected = regime_by_surface(
        stand_in_surface_sections(airplane()),
        6.0,
        AIR.speed_of_sound,
        AIR.kinematic_viscosity,
        canon_bands(),
    )
    assert [w.code for w in expected] == ["reynolds_bubble_sensitive"]
    assert result.warnings == (*expected, drag_notice())
    fast = canned(glide(18.0))
    monkeypatch.setattr(opti_module, "best_glide_worker", fast)
    assert (await adapter.best_glide(airplane(), MASS, GRAVITY, 1.0, AIR)).warnings == (
        drag_notice(),
    )


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


def flapped(root: float = 0.75, tip: float = 0.75) -> AirplaneGeometry:
    """The stand-in airplane with its flap 'flap-1' on Main at 10 deg, hinge at ``root`` / ``tip``."""
    document = airplane(device=("flap", 10.0), hinge=root).model_dump(
        mode="json", exclude_none=True
    )
    document["wings"]["Main"]["x_secs"][0]["trailing_edge_device"]["rel_chord_tip"] = tip
    return AirplaneGeometry.model_validate(document)


def assert_flap_caveats_lead(warnings: tuple[KernelWarning, ...], *, averaged: bool) -> None:
    """The warnings of a flapped result at 18 m/s (no regime warning there), in order.

    The averaged hinge (only where root and tip differ: (0.74 + 0.76) / 2 = 0.75), the flap model's
    unknown fit range naming the flap, and last the drag notice. ADR 0020: the flap model is a
    declared substitution.
    """
    expected = ["control_surface_fit_range_unknown", "induced_drag_viscous_factor_removed"]
    if averaged:
        expected.insert(0, "hinge_line_averaged")
    assert [w.code for w in warnings] == expected
    fit_range = warnings[-2]
    assert fit_range.severity == "notice"
    assert fit_range.detail == {
        "flaps": [{"wing": "Main", "device": "flap-1", "deflection_deg": 10.0}]
    }
    assert warnings[-1] == drag_notice()
    if averaged:
        hinge = warnings[0]
        assert hinge.severity == "notice"
        assert (hinge.detail["wing"], hinge.detail["device"]) == ("Main", "flap-1")
        used = hinge.detail["used"]
        assert isinstance(used, float)
        assert math.isclose(used, 0.75, rel_tol=1e-12)


@pytest.mark.parametrize(("root", "tip", "averaged"), [(0.75, 0.75, False), (0.74, 0.76, True)])
async def test_the_glide_of_a_flapped_configuration_declares_the_flap_model(
    monkeypatch: pytest.MonkeyPatch, root: float, tip: float, averaged: bool
) -> None:
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide(18.0)))
    result = await OptiAdapter(InProcessRuntime()).best_glide(
        flapped(root, tip), MASS, GRAVITY, 1.0, AIR
    )
    assert_flap_caveats_lead(result.warnings, averaged=averaged)


@pytest.mark.parametrize(("root", "tip", "averaged"), [(0.75, 0.75, False), (0.74, 0.76, True)])
async def test_the_minimum_sink_of_a_flapped_configuration_declares_the_flap_model(
    monkeypatch: pytest.MonkeyPatch, root: float, tip: float, averaged: bool
) -> None:
    """The same declaration on the minimum-sink entry point (an interior optimum at 18 m/s)."""

    def worker(_request: StallRequest) -> WorkerOutcome[MinSinkSolution]:
        found = MinSinkSolution(v_mp=18.0, alpha_mp=7.0, cl_mp=0.9)
        return WorkerOutcome(value=found, diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "min_sink_worker", worker)
    result = await OptiAdapter(InProcessRuntime()).min_sink(
        flapped(root, tip), MASS, GRAVITY, 1.0, AIR
    )
    assert_flap_caveats_lead(result.warnings, averaged=averaged)


async def test_the_glide_uses_the_adapters_versions_and_settings() -> None:
    adapter = OptiAdapter(InProcessRuntime())
    assert adapter.tool_versions() == {
        "aerosandbox": importlib.metadata.version("aerosandbox"),
        "neuralfoil": importlib.metadata.version("neuralfoil"),
    }
    assert adapter.settings() == OPT_SETTINGS


# --- the worker, with the solver boundary faked ------------------------------------------------


def install_optimum(
    monkeypatch: pytest.MonkeyPatch,
    v: float,
    alpha: float,
    drag: tuple[float, float] = (0.3, 0.2),
    cl: float = 0.55,
    error: Exception | None = None,
    objective: list[object] | None = None,
    problems: list[RecordingBoundary] | None = None,
) -> StallRequest:
    """Fake AeroSandbox so that IPOPT 'returns' (v, alpha) with (profile, induced) drag and C_L there.

    ``problems`` receives the boundary that records what the worker states to the optimiser
    (variables with bounds, constraint, objective); ``objective`` receives every minimised
    expression.
    """
    polar = lift_curve(UPRIGHT_PEAK, upright=True)
    values: dict[str, float] = {
        "speed": v,
        "alpha": alpha,
        "D_profile": drag[0],
        "D_induced": drag[1],
        "CL": cl,
    }
    boundary = RecordingBoundary(
        ("speed", "alpha"),
        values,
        ("L", "D_profile", "D_induced", "CL"),
        error,
        None if objective is None else objective.append,
    )
    if problems is not None:
        problems.append(boundary)

    def sweep(*_: object) -> Polar:
        return polar

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28)

    monkeypatch.setattr(opti_module, "sweep_lift", sweep)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", boundary.namespace)
    monkeypatch.setattr(opti_module, "aero_model", direct_aero_model)
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS, gravity=GRAVITY, n_load=1.0, air=AIR, k_e_d0=K_E_D0
    )
    return request


async def test_the_worker_reads_the_optimum_drag_and_lift_coefficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """e_max = m g / D at the optimum, D the kernel's: 1.5 * 9.81 / (0.3 + k_e,D0 * 0.2) = 31.6."""
    request = install_optimum(monkeypatch, 12.0, 4.0, drag=(0.3, 0.2), cl=0.55)
    outcome = opti_module.best_glide_worker(request)
    solution = outcome.value
    assert (solution.v_md, solution.alpha_md, solution.cl_md) == (12.0, 4.0, 0.55)
    assert math.isclose(solution.e_max, MASS * GRAVITY / (0.3 + K_E_D0 * 0.2), rel_tol=1e-12)


async def test_the_worker_minimises_the_drag_not_the_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    objective: list[object] = []
    request = install_optimum(monkeypatch, 12.0, 4.0, objective=objective)
    opti_module.best_glide_worker(request)
    (minimised,) = objective
    assert minimised.name == f"(D_profile+{K_E_D0}*D_induced)"  # type: ignore[attr-defined]


def assert_the_one_constraint_is_the_lift_balance(boundary: RecordingBoundary) -> None:
    """``L = n m g``: the model's lift set to 1.5 kg * 9.81 m/s^2 * 1 = 14.715 N, and nothing else."""
    (problem,) = boundary.problems
    (constraint,) = problem.constraints
    assert (constraint.left.name, constraint.left.operator) == ("L", "")
    assert math.isclose(constraint.right, 14.715, rel_tol=1e-12)


async def test_the_glide_problem_is_constrained_by_the_lift_balance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    problems: list[RecordingBoundary] = []
    request = install_optimum(monkeypatch, 12.0, 4.0, problems=problems)
    opti_module.best_glide_worker(request)
    (boundary,) = problems
    assert_the_one_constraint_is_the_lift_balance(boundary)
    (minimised,) = boundary.problems[0].objectives
    assert minimised.name == f"(D_profile+{K_E_D0}*D_induced)"


async def test_the_minimum_sink_problem_is_constrained_by_the_lift_balance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The minimum sink shares the solve of the best glide: min D V subject to the same balance."""
    problems: list[RecordingBoundary] = []
    request = install_optimum(monkeypatch, 9.0, 7.0, problems=problems)
    opti_module.min_sink_worker(request)
    (boundary,) = problems
    assert_the_one_constraint_is_the_lift_balance(boundary)
    (minimised,) = boundary.problems[0].objectives
    assert minimised.name == f"(D_profile+{K_E_D0}*D_induced)*speed"


V_HIGH = opti_module.V_MAX_MACH * AIR.speed_of_sound
V_LOW = opti_module.V_MIN_MS


@pytest.mark.parametrize(
    ("v", "alpha", "variable"),
    [
        (V_HIGH, 4.0, "V"),
        (V_LOW, 4.0, "V"),
        (12.0, opti_module.ALPHA_MIN_DEG, "alpha"),
        (12.0, 16.0, "alpha"),  # the window's upper edge: the main peak (15.75) plus one step
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
