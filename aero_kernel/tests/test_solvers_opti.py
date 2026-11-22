"""The Opti adapter: the stall speed as an optimisation over AeroBuildup (ch. 8.8, canon K32)."""

import importlib.metadata
import math
from collections.abc import Sequence
from itertools import pairwise
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import DeviceSpan, OptiAdapter, StallRequest, StallSolution
from aero_kernel.solvers.regime import regime_by_surface
from aero_kernel.tests.asb_fakes import RecordingBoundary
from aero_kernel.tests.planform_stand_in import canon_bands, stand_in_surface_sections
from aero_kernel.tests.solver_builders import (
    AIR,
    K_E_D0,
    InProcessRuntime,
    airplane,
    direct_aero_model,
)
from aero_kernel.tests.stall_stubs import INVERTED_TROUGH, UPRIGHT_PEAK, lift_curve, lift_curve_at

pytestmark = pytest.mark.asyncio


def solution(v_s: float = 8.0, cl: float = 1.2, alpha_s: float = 14.0) -> StallSolution:
    alphas = (0.0, alpha_s, 20.0)
    polar = Polar(alpha_deg=alphas, cl=(0.3, cl, 1.0), cd=(0.01,) * 3)
    return StallSolution(v_s=v_s, cl_max=cl, alpha_s=alpha_s, polar=polar)


def canned(result: StallSolution) -> object:
    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_the_adapter_declares_its_tool_and_requirement() -> None:
    assert OptiAdapter.tool == "OPT"
    # NeuralFoil is the model AeroBuildup's sections come from: a tool of the result (ch. 8.4)
    assert OptiAdapter.requirements == {"aerosandbox": "aerosandbox", "neuralfoil": "neuralfoil"}


async def test_the_stall_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        seen.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    result = await OptiAdapter(InProcessRuntime()).stall(airplane(), 1.5, 9.81, 1.0, AIR)
    (request,) = seen
    assert (request.mass_kg, request.gravity, request.n_load, request.air) == (1.5, 9.81, 1.0, AIR)
    assert request.airplane == airplane()
    assert result.solution == solution()


async def test_the_stall_carries_the_regime_warnings_of_its_stall_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m, MAC 0.156 m: at 6 m/s Re 6.4e4 at the MAC (bubble-sensitive, in the
    band); at 2 m/s Re 2.1e4, below 3e4 (ADR 0028; per surface, #1342)."""
    adapter = OptiAdapter(InProcessRuntime())
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=6.0)))
    fast = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in fast.warnings] == [
        "reynolds_bubble_sensitive"
    ]  # no drag: no drag notice
    assert fast.warnings[0].detail["wing"] == "Main"
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=2.0)))
    slow = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in slow.warnings] == ["reynolds_outside_band"]
    assert all(w.origin is None for w in (*fast.warnings, *slow.warnings))


@pytest.mark.parametrize(
    ("mass", "gravity", "n_load"),
    [(0.0, 9.81, 1.0), (-1.0, 9.81, 1.0), (1.5, 0.0, 1.0), (1.5, 9.81, 0.0), (1.5, 9.81, math.nan)],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, n_load: float
) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(plane, mass, gravity, n_load, AIR)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_negative_load_factor_is_the_inverted_stall_not_an_inadmissible_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stall takes a signed load factor (only 0 is refused): n = -1 reaches the worker as given."""
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        seen.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    result = await OptiAdapter(InProcessRuntime()).stall(airplane(), 1.5, 9.81, -1.0, AIR)
    (request,) = seen
    assert request.n_load == -1.0
    assert result.solution == solution()


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    adapter = OptiAdapter(InProcessRuntime())
    plane = airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(plane, 1.5, 9.81, 1.0, AIR)
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_tool_versions_are_aerosandboxs_and_neuralfoils() -> None:
    assert OptiAdapter(InProcessRuntime()).tool_versions() == {
        "aerosandbox": importlib.metadata.version("aerosandbox"),
        "neuralfoil": importlib.metadata.version("neuralfoil"),
    }


async def test_the_adapter_declares_the_neuralfoil_model_size_it_passes() -> None:
    """xlarge: the author's default, at the knee of speed versus accuracy (Sharpe 2024, PhD thesis
    ch. 7, Table 7.1; maintainer decision 2026-10-22). The airfoil scoring (#821) uses xxxlarge,
    precomputed, on purpose."""
    adapter = OptiAdapter(InProcessRuntime())
    assert adapter.settings()["neuralfoil_model_size"] == opti_module.NEURALFOIL_MODEL_SIZE
    assert opti_module.NEURALFOIL_MODEL_SIZE == "xlarge"


@pytest.mark.parametrize(("role", "deflection"), [("aileron", -5.0), ("elevator", 2.0)])
async def test_a_deflected_control_surface_is_refused_not_computed_as_clean(
    monkeypatch: pytest.MonkeyPatch, role: str, deflection: float
) -> None:
    """Only flaps are passed to AeroBuildup (a configuration); any other deflected device would
    silently be computed as at rest, so it is refused."""
    called: list[object] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        called.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    adapter = OptiAdapter(InProcessRuntime())
    deflected = airplane(device=(role, deflection))
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(deflected, 1.5, 9.81, 1.0, AIR)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "deflected control surfaces are not yet passed to AeroBuildup" in raised.value.message
    assert "flap-1" in raised.value.message
    assert role in raised.value.message
    assert called == []


async def test_a_deflected_flap_reaches_the_worker_and_is_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The landing configuration: the worker is given the flap, never the clean airplane, and the
    result carries the averaged-hinge-free model caveat with the flap in its detail."""
    seen: list[StallRequest] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        seen.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    flapped = airplane(device=("flap", 30.0), hinge=0.8)
    result = await OptiAdapter(InProcessRuntime()).stall(flapped, 1.5, 9.81, 1.0, AIR)
    assert seen[0].airplane == flapped
    (warning,) = [w for w in result.warnings if w.code == "control_surface_fit_range_unknown"]
    assert warning.severity == "notice"
    assert warning.detail == {
        "flaps": [{"wing": "Main", "device": "flap-1", "deflection_deg": 30.0}]
    }
    assert "analysis_confidence" in warning.message
    assert "single-element" in warning.message


async def test_a_flap_without_a_hinge_is_invalid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    hingeless = airplane(device=("flap", 30.0))
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(hingeless, 1.5, 9.81, 1.0, AIR)
    assert (raised.value.category, raised.value.code) == (
        ErrorCategory.INVALID_INPUT,
        "missing_hinge",
    )


async def test_a_clean_stall_has_no_flap_caveat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    result = await OptiAdapter(InProcessRuntime()).stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert all(w.code != "control_surface_fit_range_unknown" for w in result.warnings)


async def test_a_device_at_rest_is_no_obstacle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.stall(airplane(device=("flap", 0.0)), 1.5, 9.81, 1.0, AIR)
    assert result.solution == solution()


async def test_a_regime_warning_names_the_wing_that_is_out_of_band(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At 8 m/s the stand-in MAC of Main (chords 0.2 / 0.1 m: 0.1556 m) gives Re = 8 * 0.1556 /
    1.4607e-5 = 8.5e4, above the bubble-sensitive limit 7e4: no warning for Main. The tail (chords
    0.05 m / 2 mm, MAC 0.033 m) gives Re 1.8e4, below the band's 3e4: the one warning, and it names
    the tail."""
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=8.0)))
    adapter = OptiAdapter(InProcessRuntime())
    stall = await adapter.stall(airplane(tail_chords=(0.05, 0.002)), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in stall.warnings] == ["reynolds_outside_band"]
    (warning,) = stall.warnings
    assert warning.severity == "warning"
    assert warning.detail["wing"] == "Tail"
    assert "Tail" in warning.message
    sensitive = [w for w in stall.warnings if w.code == "reynolds_bubble_sensitive"]
    assert sensitive == []


async def test_a_mach_warning_is_raised_once_not_per_wing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=120.0)))
    adapter = OptiAdapter(InProcessRuntime())
    stall = await adapter.stall(airplane(tail_chords=(0.2, 0.1)), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in stall.warnings].count("mach_above_limit") == 1


def install_failing_solver(monkeypatch: pytest.MonkeyPatch, error: Exception) -> StallRequest:
    """Fake the AeroSandbox boundary of the worker so that `Opti.solve` raises ``error``."""
    polar = lift_curve(UPRIGHT_PEAK, upright=True)

    class FakeOpti:
        def variable(self, **_: object) -> float:
            return 1.0

        def subject_to(self, _: object) -> None:
            return None

        def minimize(self, _: object) -> None:
            return None

        def solve(self, **_: object) -> object:
            raise error

    def operating_point(**_: object) -> None:
        return None

    def aerobuildup(*_: object, **__: object) -> SimpleNamespace:
        return SimpleNamespace(run=lambda: {"L": 0.0})

    def sweep(*_: object) -> Polar:
        return polar

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28)

    fake_asb = SimpleNamespace(
        Opti=FakeOpti, OperatingPoint=operating_point, AeroBuildup=aerobuildup
    )
    monkeypatch.setattr(opti_module, "sweep_polar", sweep)
    monkeypatch.setattr(opti_module, "sweep_lift", sweep)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake_asb)
    monkeypatch.setattr(opti_module, "aero_model", direct_aero_model)
    return StallRequest(
        airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=1.0, air=AIR, k_e_d0=K_E_D0
    )


async def test_an_ipopt_failure_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    """CasADi reports a failed solve as a RuntimeError."""
    request = install_failing_solver(monkeypatch, RuntimeError("Infeasible_Problem_Detected"))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "Infeasible_Problem_Detected" in raised.value.message


async def test_any_other_exception_of_the_solve_is_a_defect_and_stays_an_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = install_failing_solver(monkeypatch, ValueError("a bug"))
    with pytest.raises(ValueError, match="a bug"):
        opti_module.stall_worker(request)


async def test_the_sweep_grid_spans_minus_15_to_25_deg_in_quarter_degree_steps() -> None:
    grid = opti_module._grid()  # pyright: ignore[reportPrivateUsage]  # the grid is the contract
    assert len(grid) == 161
    assert (grid[0], grid[-1]) == (-15.0, 25.0)
    assert all(math.isclose(b - a, 0.25, abs_tol=1e-12) for a, b in pairwise(grid))
    assert (opti_module.ALPHA_MIN_DEG, opti_module.ALPHA_MAX_DEG) == (-15.0, 25.0)
    assert opti_module.ALPHA_STEP_DEG == 0.25


# The arguments of one ``sweep_polar`` call: airplane, air, speed in m/s, angles in deg, NeuralFoil
# model size, viscous factor.
PublishedSweep = tuple[object, object, float, tuple[float, ...], str, float]


def install_recording_solution(
    monkeypatch: pytest.MonkeyPatch, v_s: float, alpha_s: float, n_load: float = 1.0
) -> tuple[StallRequest, RecordingBoundary, list[PublishedSweep]]:
    """Fake the solver boundary so that IPOPT 'returns' (v_s, alpha_s), and record the problem.

    The lift sweeps answer the stub's curve of the branch (first peak at 15.75 deg upright, first
    trough at -10 deg inverted); the converted airplane has S_ref = 0.28 m^2.

    Returns:
        The request, the boundary that records every problem the worker states (variables with
        bounds, constraint, objective), and the arguments of every call of ``sweep_polar`` (the
        published polar).
    """
    upright = n_load > 0.0
    peak = UPRIGHT_PEAK if upright else INVERTED_TROUGH
    polar = lift_curve(peak, upright=upright)
    boundary = RecordingBoundary(("speed", "alpha"), {"speed": v_s, "alpha": alpha_s}, ("L",))
    published: list[PublishedSweep] = []
    converted = SimpleNamespace(s_ref=0.28)

    def publish(
        plane: object, air: object, speed: float, angles: Sequence[float], size: str, k: float
    ) -> Polar:
        published.append((plane, air, speed, tuple(angles), size, k))
        return lift_curve_at(peak, upright, angles)

    def sweep(*_: object) -> Polar:
        return polar

    def convert(_: object) -> SimpleNamespace:
        return converted

    monkeypatch.setattr(opti_module, "sweep_polar", publish)
    monkeypatch.setattr(opti_module, "sweep_lift", sweep)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", boundary.namespace)
    monkeypatch.setattr(opti_module, "aero_model", direct_aero_model)
    request = StallRequest(
        airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=n_load, air=AIR, k_e_d0=K_E_D0
    )
    return request, boundary, published


def install_solution(monkeypatch: pytest.MonkeyPatch, v_s: float, alpha_s: float) -> StallRequest:
    """Fake the solver boundary so that IPOPT 'returns' (v_s, alpha_s) for the upright stall."""
    return install_recording_solution(monkeypatch, v_s, alpha_s)[0]


V_HIGH = opti_module.V_MAX_MACH * AIR.speed_of_sound
V_LOW = opti_module.V_MIN_MS


async def test_an_interior_optimum_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_solution(monkeypatch, 8.0, 15.75)
    outcome = opti_module.stall_worker(request)
    assert (outcome.value.v_s, outcome.value.alpha_s) == (8.0, 15.75)


@pytest.mark.parametrize(
    ("n_load", "alpha_s", "lift"), [(1.0, 15.75, 14.715), (-1.0, -5.0, -14.715)]
)
async def test_the_stall_problem_minimises_the_speed_subject_to_the_lift_balance(
    monkeypatch: pytest.MonkeyPatch, n_load: float, alpha_s: float, lift: float
) -> None:
    """min V s.t. L = n m g (canon K32): the objective is the speed variable itself, the one
    constraint sets the model's lift to 1.5 kg * 9.81 m/s^2 = 14.715 N (negative when inverted)."""
    request, boundary, _ = install_recording_solution(monkeypatch, 8.0, alpha_s, n_load)
    opti_module.stall_worker(request)
    (problem,) = boundary.problems
    (objective,) = problem.objectives
    assert (objective.name, objective.operator) == ("speed", "")
    (constraint,) = problem.constraints
    assert (constraint.left.name, constraint.left.operator) == ("L", "")
    assert math.isclose(constraint.right, lift, rel_tol=1e-12)


@pytest.mark.parametrize(
    ("n_load", "alpha_s", "window"),
    [(1.0, 15.75, (-15.0, 16.0)), (-1.0, -5.0, (-10.25, 25.0))],
)
async def test_the_window_of_alpha_ends_one_step_past_the_first_extremum_of_the_branch(
    monkeypatch: pytest.MonkeyPatch, n_load: float, alpha_s: float, window: tuple[float, float]
) -> None:
    """Upright the window runs from the sweep's start (-15 deg) to the first peak plus one step
    (15.75 + 0.25 = 16 deg); inverted from the first trough minus one step (-10 - 0.25 = -10.25 deg)
    to the sweep's end (25 deg). The speed lies between 1 m/s and Mach 0.6 (0.6 * 340.294 =
    204.1764 m/s) on both branches."""
    request, boundary, _ = install_recording_solution(monkeypatch, 8.0, alpha_s, n_load)
    opti_module.stall_worker(request)
    (problem,) = boundary.problems
    alpha, speed = problem.variables["alpha"], problem.variables["speed"]
    assert (alpha["lower_bound"], alpha["upper_bound"]) == window
    assert speed["lower_bound"] == 1.0
    assert math.isclose(speed["upper_bound"], 204.1764, rel_tol=1e-12)


async def test_the_published_polar_is_swept_at_the_stall_speed_with_the_stall_angle_among_its_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The polar C_L,max is read from is swept once, at the optimum V_S = 8 m/s, not at the
    bracketing speed sqrt(2 * 14.715 / (1.225 * 0.28 * 1.19)) = 8.49 m/s, over the grid plus alpha_S
    (15.6 deg lies between two grid points), with the kernel's viscous factor."""
    request, _, published = install_recording_solution(monkeypatch, 8.0, 15.6)
    outcome = opti_module.stall_worker(request)
    (call,) = published
    _converted, air, speed, angles, model_size, viscous_factor = call
    assert (air, speed) == (AIR, 8.0)
    assert 15.6 in angles
    assert len(angles) == 162  # the 161 grid points and alpha_S
    assert (model_size, viscous_factor) == ("xlarge", K_E_D0)
    assert outcome.value.alpha_s == 15.6


@pytest.mark.parametrize(
    ("v_s", "alpha_s", "variable"),
    [
        (V_HIGH, 15.75, "V"),
        (V_HIGH - 1e-9, 15.75, "V"),
        (V_LOW, 15.75, "V"),
        (V_LOW + 1e-9, 15.75, "V"),
        (8.0, opti_module.ALPHA_MIN_DEG, "alpha"),
        (8.0, opti_module.ALPHA_MIN_DEG + 1e-9, "alpha"),
        (8.0, 16.0, "alpha"),  # the window's upper edge: peak (15.75) + one step
    ],
)
async def test_an_optimum_on_a_bound_is_not_converged_and_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, v_s: float, alpha_s: float, variable: str
) -> None:
    request = install_solution(monkeypatch, v_s, alpha_s)
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["variable"] == variable


async def test_a_deflected_control_surface_view_is_refused_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The conversion drops control_surface.deflection as well as the device's, so the guard
    refuses what the conversion would drop."""
    called: list[object] = []

    def worker(request: StallRequest) -> WorkerOutcome[StallSolution]:
        called.append(request)
        return WorkerOutcome(value=solution(), diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    adapter = OptiAdapter(InProcessRuntime())
    deflected = airplane(surface_deflection=12.0)
    with pytest.raises(FormulaError) as raised:
        await adapter.stall(deflected, 1.5, 9.81, 1.0, AIR)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "deflected control surfaces are not yet passed to AeroBuildup" in raised.value.message
    assert "cs-1" in raised.value.message
    assert called == []


async def test_a_control_surface_view_at_rest_is_no_obstacle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    result = await adapter.stall(airplane(surface_deflection=0.0), 1.5, 9.81, 1.0, AIR)
    assert result.solution == solution()


async def test_the_stall_regime_warnings_are_those_of_the_stall_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m at 6 m/s: only the smaller chord is bubble-sensitive (Re 4.1e4). At
    three times the speed (18 m/s) there would be no warning at all."""
    adapter = OptiAdapter(InProcessRuntime())
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=6.0)))
    result = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    expected = regime_by_surface(
        stand_in_surface_sections(airplane()),
        6.0,
        AIR.speed_of_sound,
        AIR.kinematic_viscosity,
        canon_bands(),
    )
    assert [w.code for w in expected] == ["reynolds_bubble_sensitive"]
    assert result.warnings == tuple(expected)
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=18.0)))
    assert (await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)).warnings == ()


async def test_a_stall_with_a_deflected_flap_records_the_confidence_at_the_optimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aero_kernel.solvers.opti import DeflectionDiagnostics

    request = install_solution(monkeypatch, 8.0, 15.75)
    found = DeflectionDiagnostics(
        min_confidence=0.53,
        min_confidence_wing="Main",
        max_effective_alpha_deg=15.75,
        max_effective_alpha_wing="Main",
        devices=(),
    )
    calls: list[tuple[float, float]] = []

    def fake_diagnostics(_request: object, _airplane: object, speed: float, alpha: float) -> object:
        calls.append((speed, alpha))
        return found

    monkeypatch.setattr(opti_module, "_flap_diagnostics", fake_diagnostics)
    flapped = request.model_copy(update={"airplane": airplane(device=("flap", 30.0), hinge=0.8)})
    assert opti_module.stall_worker(flapped).value.diagnostics == found
    assert calls == [(8.0, 15.75)]
    assert opti_module.stall_worker(request).value.diagnostics is None  # a clean airplane: no run
    assert calls == [(8.0, 15.75)]


async def test_the_confidence_of_a_flapped_stall_reaches_the_declared_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aero_kernel.solvers.opti import DeflectionDiagnostics

    found = DeflectionDiagnostics(
        min_confidence=0.53,
        min_confidence_wing="Main",
        max_effective_alpha_deg=15.0,
        max_effective_alpha_wing="Main",
        devices=(),
    )
    flapped = solution().model_copy(update={"diagnostics": found})
    monkeypatch.setattr(opti_module, "stall_worker", canned(flapped))
    result = await OptiAdapter(InProcessRuntime()).stall(
        airplane(device=("flap", 30.0), hinge=0.8), 1.5, 9.81, 1.0, AIR
    )
    (warning,) = [w for w in result.warnings if w.code == "control_surface_fit_range_unknown"]
    assert warning.detail["min_confidence"] == 0.53
    assert warning.detail["min_confidence_wing"] == "Main"


async def test_the_flap_diagnostics_run_at_the_optimum_of_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    points: list[dict[str, object]] = []

    def operating_point(**kwargs: object) -> str:
        points.append(kwargs)
        return "point"

    def confidence_run(
        _asb: object, plane: object, keys: list[str], point: object, spans: list[DeviceSpan]
    ) -> str:
        found_spans = [(span.wing, span.intervals) for span in spans]
        return f"{plane}:{keys}:{point}:{found_spans}"

    monkeypatch.setattr(
        opti_module, "load_aerosandbox", lambda: SimpleNamespace(OperatingPoint=operating_point)
    )
    monkeypatch.setattr(opti_module, "_confidence_run", confidence_run)
    flapped = airplane(device=("flap", 30.0), hinge=0.8)
    request = StallRequest(
        airplane=flapped, mass_kg=1.5, gravity=9.81, n_load=1.0, air=AIR, k_e_d0=K_E_D0
    )
    found = opti_module._flap_diagnostics(request, "asb", 8.0, 15.0)  # pyright: ignore[reportPrivateUsage]
    # the flap's span: the first panel, |y| 0 to 0.3 m
    assert found == "asb:['Main']:point:[('Main', ((0.0, 0.3),))]"
    assert (points[0]["velocity"], points[0]["alpha"]) == (8.0, 15.0)


async def test_the_regime_bands_are_the_call_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """At 6 m/s Re 6.4e4 at the MAC is bubble-sensitive under the canon's 7e4; an override of the
    rule to 5e4 moves it inside the band, and the read is declared in the rules used."""
    from aero_kernel.build import shipped_build
    from aero_kernel.rules import Rules

    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=6.0)))
    rules = Rules(shipped_build().model, {"reynolds-mach-regime.re_bubble_max": 5e4})
    result = await OptiAdapter(InProcessRuntime(), rules).stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert result.warnings == ()
    assert ("reynolds-mach-regime", "re_bubble_max", True) in {
        (u.rule, u.parameter, u.overridden) for u in rules.used()
    }
