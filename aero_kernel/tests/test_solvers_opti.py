"""The Opti adapter: the stall speed as an optimisation over AeroBuildup (ch. 8.8, canon K32)."""

import importlib.metadata
import math
from itertools import pairwise

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.base import regime_by_wing
from aero_kernel.solvers.opti import OptiAdapter, StallRequest, StallSolution
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane

pytestmark = pytest.mark.asyncio


def solution(v_s: float = 8.0, cl: float = 1.2, alpha_s: float = 14.0) -> StallSolution:
    alphas = (0.0, alpha_s, 20.0)
    polar = Polar(alpha_deg=alphas, cl=(0.3, cl, 1.0), cd=(0.01,) * 3, cm=(-0.01,) * 3)
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
    """Chords 0.2 and 0.1 m: at 8 m/s Re 9.1e4 and 4.6e4 (bubble-sensitive, in the band); at 2 m/s
    the smaller chord gives Re 1.1e4, below 3e4 (ADR 0028)."""
    adapter = OptiAdapter(InProcessRuntime())
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=8.0)))
    fast = await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in fast.warnings] == ["reynolds_bubble_sensitive"]
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
    assert warning.severity == "practice"
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
    """Main chords 0.2 / 0.1 m are in the band at 8 m/s (Re 9.1e4 / 4.6e4); a tail tip of 2 mm
    gives Re 1.0e3: only the tail is outside the band, and the warning says so."""
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=8.0)))
    adapter = OptiAdapter(InProcessRuntime())
    stall = await adapter.stall(airplane(tail_chords=(0.05, 0.002)), 1.5, 9.81, 1.0, AIR)
    outside = [w for w in stall.warnings if w.code == "reynolds_outside_band"]
    (warning,) = outside
    assert warning.detail["wing"] == "Tail"
    assert "Tail" in warning.message
    sensitive = [w for w in stall.warnings if w.code == "reynolds_bubble_sensitive"]
    assert [w.detail["wing"] for w in sensitive] == ["Main", "Tail"][: len(sensitive)]
    assert all(w.detail["wing"] != "Main" for w in outside)


async def test_a_mach_warning_is_raised_once_not_per_wing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=120.0)))
    adapter = OptiAdapter(InProcessRuntime())
    stall = await adapter.stall(airplane(tail_chords=(0.2, 0.1)), 1.5, 9.81, 1.0, AIR)
    assert [w.code for w in stall.warnings].count("mach_above_limit") == 1


def install_failing_solver(monkeypatch: pytest.MonkeyPatch, error: Exception) -> StallRequest:
    """Fake the AeroSandbox boundary of the worker so that `Opti.solve` raises ``error``."""
    from types import SimpleNamespace

    from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve

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
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake_asb)
    return StallRequest(airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=1.0, air=AIR)


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


def install_solution(monkeypatch: pytest.MonkeyPatch, v_s: float, alpha_s: float) -> StallRequest:
    """Fake the solver boundary so that IPOPT 'returns' (v_s, alpha_s); records the bounds."""
    from types import SimpleNamespace

    from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve

    polar = lift_curve(UPRIGHT_PEAK, upright=True)

    class Variable:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeOpti:
        def __init__(self) -> None:
            self.count = 0

        def variable(self, **_: object) -> Variable:
            self.count += 1
            return Variable("speed" if self.count == 1 else "alpha")

        def subject_to(self, _: object) -> None:
            return None

        def minimize(self, _: object) -> None:
            return None

        def solve(self, **_: object) -> object:
            values = {"speed": v_s, "alpha": alpha_s}

            def solved(variable: Variable) -> float:
                return values[variable.name]

            return solved

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
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake_asb)
    return StallRequest(airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=1.0, air=AIR)


V_HIGH = opti_module.V_MAX_MACH * AIR.speed_of_sound
V_LOW = opti_module.V_MIN_MS


async def test_an_interior_optimum_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    request = install_solution(monkeypatch, 8.0, 15.75)
    outcome = opti_module.stall_worker(request)
    assert (outcome.value.v_s, outcome.value.alpha_s) == (8.0, 15.75)


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
    expected = regime_by_wing(
        {"Main": [0.2, 0.1]}, 6.0, AIR.speed_of_sound, AIR.kinematic_viscosity
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

    def confidence_run(_asb: object, plane: object, keys: list[str], point: object) -> str:
        return f"{plane}:{keys}:{point}"

    monkeypatch.setattr(
        opti_module, "load_aerosandbox", lambda: SimpleNamespace(OperatingPoint=operating_point)
    )
    monkeypatch.setattr(opti_module, "_confidence_run", confidence_run)
    request = StallRequest(airplane=airplane(), mass_kg=1.5, gravity=9.81, n_load=1.0, air=AIR)
    found = opti_module._flap_diagnostics(request, "asb", 8.0, 15.0)  # pyright: ignore[reportPrivateUsage]
    assert found == "asb:['Main']:point"
    assert (points[0]["velocity"], points[0]["alpha"]) == (8.0, 15.0)
