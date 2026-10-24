"""The steady-roll problem of the Opti adapter: wiring, windows, caveats (fast tier, stubbed solver).

The solver boundary is faked as in the stall tests; the real AeroBuildup and IPOPT are in
``test_solvers_opti_roll_real.py``.
"""

import math
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import (
    DeflectionDiagnostics,
    OptiAdapter,
    RollRequest,
    RollSolution,
)
from aero_kernel.solvers.roll_math import control_effectiveness
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve
from aero_kernel.tests.test_solvers_roll_devices import aileron, wing_geometry
from aero_kernel.tests.test_solvers_roll_math import Degrees

pytestmark = pytest.mark.asyncio

MASS, GRAVITY, SPEED = 0.15, 9.81, 10.0


def rolling_airplane(root: float = 0.8, tip: float = 0.8) -> AirplaneGeometry:
    """A 0.4 m half-span wing with an aileron on its second panel."""
    return wing_geometry((0.0, 0.2, 0.4), 1, aileron(root, tip))


def diagnostics() -> DeflectionDiagnostics:
    return DeflectionDiagnostics(
        min_confidence=0.61,
        min_confidence_wing="Main",
        max_effective_alpha_deg=14.2,
        max_effective_alpha_wing="Main",
    )


def solution(p: float = 1.2, alpha: float = 4.0, with_diagnostics: bool = True) -> RollSolution:
    return RollSolution(
        p_rad_s=p, alpha_deg=alpha, diagnostics=diagnostics() if with_diagnostics else None
    )


def canned(result: RollSolution, seen: list[RollRequest] | None = None) -> object:
    def worker(request: RollRequest) -> WorkerOutcome[RollSolution]:
        if seen is not None:
            seen.append(request)
        return WorkerOutcome(value=result, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


async def test_steady_roll_end_to_end_with_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[RollRequest] = []
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution(), seen))
    plane = rolling_airplane()
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(plane, MASS, GRAVITY, AIR, SPEED, 20.0)
    (request,) = seen
    assert (request.mass_kg, request.gravity, request.air) == (MASS, GRAVITY, AIR)
    assert (request.v_ms, request.delta_deg) == (SPEED, 20.0)
    assert request.airplane == plane
    assert (roll.p_rad_s, roll.alpha_deg) == (1.2, 4.0)


async def test_steady_roll_reports_min_confidence_and_max_effective_alpha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M1: the values go into one declared practice warning; there is no threshold."""
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution()))
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        rolling_airplane(), MASS, GRAVITY, AIR, SPEED, 20.0
    )
    (warning,) = [w for w in roll.warnings if w.code == "control_surface_fit_range_unknown"]
    assert warning.severity == "practice"
    assert warning.detail == {
        "min_confidence": 0.61,
        "min_confidence_wing": "Main",
        "max_effective_alpha_deg": 14.2,
        "max_effective_alpha_wing": "Main",
    }
    assert "tau" in warning.message or "τ" in warning.message


async def test_steady_roll_zero_delta_gives_zero_p_without_deflection_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[RollRequest] = []
    monkeypatch.setattr(
        opti_module, "steady_roll_worker", canned(solution(0.0, with_diagnostics=False), seen)
    )
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        rolling_airplane(0.78, 0.8), MASS, GRAVITY, AIR, SPEED, 0.0
    )
    assert roll.p_rad_s == 0.0
    assert roll.warnings == ()  # no deflection evaluated: neither the fit range nor the hinge
    assert seen[0].delta_deg == 0.0


async def test_steady_roll_declares_the_averaged_hinge_per_driven_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution()))
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        rolling_airplane(0.78, 0.8), MASS, GRAVITY, AIR, SPEED, 20.0
    )
    codes = [w.code for w in roll.warnings]
    assert codes == ["hinge_line_averaged", "control_surface_fit_range_unknown"]


async def test_steady_roll_regime_warnings_at_v(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chord 0.2 m at 3 m/s: Re 4.1e4, bubble-sensitive (ADR 0028)."""
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution()))
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        rolling_airplane(), MASS, GRAVITY, AIR, 3.0, 20.0
    )
    (regime,) = [w for w in roll.warnings if w.code == "reynolds_bubble_sensitive"]
    assert regime.detail["wing"] == "Main"


@pytest.mark.parametrize("field", ["device", "surface"])
async def test_deflected_geometry_state_still_refused(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    called: list[RollRequest] = []
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution(), called))
    plane = (
        wing_geometry((0.0, 0.2, 0.4), 1, aileron(deflection_deg=3.0))
        if field == "device"
        else wing_geometry((0.0, 0.2, 0.4), 1, surface_deflection=2.0)
    )
    adapter = OptiAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.steady_roll(plane, MASS, GRAVITY, AIR, SPEED, 20.0)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert called == []


async def test_roll_device_on_unmirrored_surface_is_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution()))
    plane = wing_geometry((0.0, 0.2, 0.4), 1, symmetric=False)
    adapter = OptiAdapter(InProcessRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.steady_roll(plane, MASS, GRAVITY, AIR, SPEED, 20.0)
    assert raised.value.code == "roll_device_on_unmirrored_surface"


@pytest.mark.parametrize(
    ("mass", "gravity", "speed", "delta"),
    [
        (0.0, 9.81, 10.0, 20.0),
        (0.15, 0.0, 10.0, 20.0),
        (0.15, 9.81, 0.0, 20.0),
        (0.15, 9.81, math.nan, 20.0),
        (0.15, 9.81, 10.0, math.nan),
        (0.15, 9.81, 10.0, math.inf),
    ],
)
async def test_an_inadmissible_input_is_invalid_input(
    monkeypatch: pytest.MonkeyPatch, mass: float, gravity: float, speed: float, delta: float
) -> None:
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution()))
    adapter = OptiAdapter(InProcessRuntime())
    airplane = rolling_airplane()
    with pytest.raises(FormulaError) as raised:
        await adapter.steady_roll(airplane, mass, gravity, AIR, speed, delta)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


# --- the worker against a faked solver boundary --------------------------------------------------


class Variable(float):
    """A decision variable that behaves as its initial guess in arithmetic."""

    name: str

    def __new__(cls, name: str, value: float) -> "Variable":
        instance = super().__new__(cls, value)
        instance.name = name
        return instance


class FakeAirfoil:
    """The base class of the recording airfoil: answers NeuralFoil with a fixed confidence."""

    confidence_by_name: ClassVar[dict[str, float]] = {}

    def __init__(self, name: str = "", coordinates: object = None) -> None:
        self.name = name
        self.coordinates = coordinates

    def get_aero_from_neuralfoil(self, **kwargs: Any) -> dict[str, float]:
        return {"analysis_confidence": self.confidence_by_name.get(self.name, 0.95), "CL": 0.5}


class Boundary:
    """The faked AeroSandbox of the worker; records what the worker asked of it."""

    def __init__(self, p_opt: float, alpha_opt: float) -> None:
        self.values = {"alpha": alpha_opt, "p": p_opt}
        self.operating_points: list[dict[str, Any]] = []
        self.variables: list[dict[str, Any]] = []
        self.error: Exception | None = None
        self.numeric_runs = 0
        # (alpha, p_body) -> (Cl, Cn) of the fake airplane, for the secant start
        self.moments: Callable[[float, float], tuple[float, float]] = lambda _a, _p: (0.0, 0.0)

    def namespace(self) -> SimpleNamespace:
        boundary = self

        class FakeOpti:
            def variable(self, **kwargs: Any) -> Variable:
                boundary.variables.append(kwargs)
                name = "alpha" if len(boundary.variables) == 1 else "p"
                return Variable(name, kwargs["init_guess"])

            def subject_to(self, _: object) -> None:
                return None

            def minimize(self, _: object) -> None:
                return None

            def solve(self, **_: object) -> object:
                if boundary.error is not None:
                    raise boundary.error

                def solved(variable: Variable) -> float:
                    return boundary.values[variable.name]

                return solved

        def operating_point(**kwargs: Any) -> SimpleNamespace:
            boundary.operating_points.append(kwargs)
            return SimpleNamespace(**kwargs)

        def aero_buildup(airplane: Any, op_point: Any, model_size: str) -> SimpleNamespace:
            def run() -> dict[str, float]:
                if isinstance(op_point.alpha, float) and not isinstance(op_point.alpha, Variable):
                    boundary.numeric_runs += 1
                for wing in getattr(airplane, "wings", []):
                    for xsec in wing.xsecs:
                        xsec.airfoil.get_aero_from_neuralfoil(
                            alpha=5.0, Re=1e5, control_surfaces=xsec.control_surfaces
                        )
                cl, cn = (
                    boundary.moments(op_point.alpha, op_point.p)
                    if isinstance(op_point.alpha, float)
                    and not isinstance(op_point.alpha, Variable)
                    else (0.0, 0.0)
                )
                return {"L": 0.0, "Cl": cl, "Cn": cn}

            return SimpleNamespace(run=run)

        return SimpleNamespace(
            Opti=FakeOpti,
            OperatingPoint=operating_point,
            AeroBuildup=aero_buildup,
            Airfoil=FakeAirfoil,
            numpy=Degrees(),
        )


def plain_wing() -> SimpleNamespace:
    """One wing with one plain section, so that the recording pass has something to record."""
    xsec = SimpleNamespace(airfoil=FakeAirfoil(name="plain"), control_surfaces=[])
    return SimpleNamespace(name="Main", xsecs=[xsec])


def install(
    monkeypatch: pytest.MonkeyPatch,
    boundary: Boundary,
    polar: Polar | None = None,
    wings: list[Any] | None = None,
) -> RollRequest:
    """Fake the boundary the worker uses and return a request on the rolling airplane."""
    sweep = polar or lift_curve(UPRIGHT_PEAK, upright=True)

    def convert(_airplane: object, _roll: float = 0.0) -> SimpleNamespace:
        return SimpleNamespace(s_ref=0.28, b_ref=1.4, wings=wings or [plain_wing()])

    def sweep_stub(*_: object) -> Polar:
        return sweep

    monkeypatch.setattr(opti_module, "sweep_polar", sweep_stub)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", boundary.namespace)
    return RollRequest(
        airplane=rolling_airplane(),
        mass_kg=MASS,
        gravity=GRAVITY,
        air=AIR,
        v_ms=SPEED,
        delta_deg=20.0,
    )


P_LIMIT = 2.0 * SPEED / 1.4  # |p_hat| <= 1


async def test_the_worker_rotates_about_the_stability_axis(monkeypatch: pytest.MonkeyPatch) -> None:
    """p_b = p_s cos(alpha) and r_b = p_s sin(alpha) go into the operating point, V and alpha as
    variables; the stability-axis rate is a variable inside the |p_hat| <= 1 window."""
    boundary = Boundary(p_opt=2.0, alpha_opt=4.0)
    request = install(monkeypatch, boundary)
    outcome = opti_module.steady_roll_worker(request)
    alpha_variable, p_variable = boundary.variables
    assert (p_variable["lower_bound"], p_variable["upper_bound"]) == (-P_LIMIT, P_LIMIT)
    assert (alpha_variable["lower_bound"], alpha_variable["upper_bound"]) == (
        opti_module.ALPHA_MIN_DEG,
        UPRIGHT_PEAK[0] + opti_module.ALPHA_STEP_DEG,
    )
    first = next(op for op in boundary.operating_points if isinstance(op["alpha"], Variable))
    alpha, p_s = alpha_variable["init_guess"], p_variable["init_guess"]
    assert first["velocity"] == SPEED
    assert first["alpha"] == alpha
    assert close_to(first["p"], p_s * math.cos(math.radians(alpha)))
    assert close_to(first["r"], p_s * math.sin(math.radians(alpha)))
    assert (outcome.value.p_rad_s, outcome.value.alpha_deg) == (2.0, 4.0)


def close_to(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12)


async def test_the_start_value_of_alpha_carries_the_weight_on_the_rising_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lift curve of the stub rises 0.04 per degree to C_L 1.19 at 15.75 deg, so
    C_L = m g / (q S) at 10 m/s, 0.28 m^2 (0.15 * 9.81 / (0.5 * 1.225 * 100 * 0.28) = 0.08581) is
    reached at 15.75 - (1.19 - 0.08581) / 0.04 = -11.86 deg on the stub's branch."""
    boundary = Boundary(p_opt=2.0, alpha_opt=4.0)
    install(monkeypatch, boundary)
    cl_needed = MASS * GRAVITY / (0.5 * AIR.density * SPEED**2 * 0.28)
    request = install(monkeypatch, boundary)
    opti_module.steady_roll_worker(request)
    alpha_init = boundary.variables[0]["init_guess"]
    expected = UPRIGHT_PEAK[0] - (UPRIGHT_PEAK[1] - cl_needed) / 0.04
    assert math.isclose(alpha_init, expected, abs_tol=0.25)


@pytest.mark.parametrize(
    ("p_opt", "alpha_opt", "variable"),
    [
        (P_LIMIT, 4.0, "p"),
        (-P_LIMIT, 4.0, "p"),
        (P_LIMIT - 1e-9, 4.0, "p"),
        (2.0, opti_module.ALPHA_MIN_DEG, "alpha"),
        (2.0, UPRIGHT_PEAK[0] + opti_module.ALPHA_STEP_DEG, "alpha"),
    ],
)
async def test_steady_roll_active_bound_is_not_converged(
    monkeypatch: pytest.MonkeyPatch, p_opt: float, alpha_opt: float, variable: str
) -> None:
    request = install(monkeypatch, Boundary(p_opt, alpha_opt))
    with pytest.raises(FormulaError) as raised:
        opti_module.steady_roll_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["variable"] == variable
    assert "steady-roll" in raised.value.message


async def test_steady_roll_no_cl_peak_in_sweep_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alphas = tuple(-15.0 + 0.25 * k for k in range(161))
    rising = Polar(
        alpha_deg=alphas,
        cl=tuple(0.1 * (a + 20.0) for a in alphas),
        cd=(0.05,) * 161,
        cm=(-0.02,) * 161,
    )
    request = install(monkeypatch, Boundary(2.0, 4.0), polar=rising)
    with pytest.raises(FormulaError) as raised:
        opti_module.steady_roll_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_an_ipopt_failure_is_not_converged(monkeypatch: pytest.MonkeyPatch) -> None:
    boundary = Boundary(2.0, 4.0)
    boundary.error = RuntimeError("Infeasible_Problem_Detected")
    request = install(monkeypatch, boundary)
    with pytest.raises(FormulaError) as raised:
        opti_module.steady_roll_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "Infeasible_Problem_Detected" in raised.value.message
    assert raised.value.hint == opti_module.ROLL_HINT
    assert "sampled angles of attack" not in raised.value.hint  # the stall problem's hint


async def test_the_weight_cannot_be_carried_before_the_stall_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At this mass and speed the needed C_L (3.4) lies above the sweep's peak (1.19)."""
    request = install(monkeypatch, Boundary(2.0, 4.0)).model_copy(update={"mass_kg": 6.0})
    with pytest.raises(FormulaError) as raised:
        opti_module.steady_roll_worker(request)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


def wings_with_confidence() -> list[Any]:
    """Two wings; the control surfaces of the first carry hinge 0.78 at -20 and +20 deg."""
    FakeAirfoil.confidence_by_name = {"main-a": 0.9, "main-b": 0.6, "tail": 0.8}

    def xsec(name: str, surfaces: list[Any]) -> SimpleNamespace:
        return SimpleNamespace(airfoil=FakeAirfoil(name=name), control_surfaces=surfaces)

    down = SimpleNamespace(hinge_point=0.78, deflection=20.0)
    up = SimpleNamespace(hinge_point=0.78, deflection=-20.0)
    return [
        SimpleNamespace(name="Main", xsecs=[xsec("main-a", [down]), xsec("main-b", [up])]),
        SimpleNamespace(name="Tail", xsecs=[xsec("tail", [])]),
    ]


def main_and_tail() -> AirplaneGeometry:
    """The rolling wing plus a horizontal tail, so that the wing keys are Main and Tail."""
    document = rolling_airplane().model_dump(mode="json", exclude_none=True)
    tail = [
        {"xyz_le": [0.5, y, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
        for y in (0.0, 0.1)
    ]
    document["wings"]["Tail"] = {"name": "Tail", "surface_type": "horizontal_tail", "x_secs": tail}
    return AirplaneGeometry.model_validate(document)


async def test_the_worker_records_min_confidence_and_max_effective_alpha_over_all_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fake AeroBuildup asks every section at alpha 5 deg: the effective angle is
    5 + tau(0.78) * 20 = 14.89 on the down-going section and 5 - 9.89 on the other; the lowest
    confidence is Main's second section (0.6). Recorded over all sections, not just the aileron's."""
    boundary = Boundary(2.0, 4.0)
    request = install(monkeypatch, boundary, wings=wings_with_confidence())
    request = request.model_copy(update={"airplane": main_and_tail()})
    outcome = opti_module.steady_roll_worker(request)
    recorded = outcome.value.diagnostics
    assert recorded is not None
    assert recorded.min_confidence == 0.6
    assert recorded.min_confidence_wing == "Main"
    tau = control_effectiveness(0.78)
    assert math.isclose(recorded.max_effective_alpha_deg, 5.0 + tau * 20.0, rel_tol=1e-12)
    assert recorded.max_effective_alpha_wing == "Main"
    assert boundary.numeric_runs == 3  # two for the start of the roll rate, one recording pass


async def test_a_zero_deflection_runs_no_recording_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    boundary = Boundary(0.0, 4.0)
    request = install(monkeypatch, boundary, wings=wings_with_confidence())
    request = request.model_copy(update={"airplane": main_and_tail(), "delta_deg": 0.0})
    outcome = opti_module.steady_roll_worker(request)
    assert outcome.value.diagnostics is None
    assert boundary.numeric_runs == 0


async def test_the_window_of_alpha_comes_from_the_clean_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D9: the sweep that brackets the first C_L peak and sets the start is made on the clean
    airplane. With the deflection the curve has kinks and its first local maximum lies far below the
    stall, so a sweep on the rolled airplane would bracket nothing (trainer: C_L 0.364 at 1 deg
    against a clean peak of 1.233 at 16 deg)."""
    boundary = Boundary(p_opt=2.0, alpha_opt=4.0)
    request = install(monkeypatch, boundary)
    swept: list[object] = []
    built: list[float] = []

    def convert(_airplane: object, roll: float = 0.0) -> SimpleNamespace:
        built.append(roll)
        return SimpleNamespace(s_ref=0.28, b_ref=1.4, wings=[plain_wing()], roll=roll)

    def sweep_stub(airplane: SimpleNamespace, *_: object) -> Polar:
        swept.append(airplane.roll)
        return lift_curve(UPRIGHT_PEAK, upright=True)

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "sweep_polar", sweep_stub)
    opti_module.steady_roll_worker(request)
    assert swept == [0.0]
    assert 20.0 in built  # the optimised and the recorded evaluation use the rolled airplane


def start_of_p(boundary: Boundary) -> float:
    return boundary.variables[1]["init_guess"]


async def test_the_start_of_the_roll_rate_is_the_zero_of_the_rolling_moment_at_the_start_alpha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two numeric runs at the start angle of attack (no roll and a probe at a quarter of the window)
    give the secant through the stability-axis rolling moment; its zero is the start. The fake
    airplane has Cl = 0.01 - 0.002 p_body and no Cn, so the moment is
    (0.01 - 0.002 p cos(alpha)) cos(alpha) and vanishes at p = 5 / cos(alpha)."""
    boundary = Boundary(2.0, 4.0)
    boundary.moments = lambda _alpha, p_body: (0.01 - 0.002 * p_body, 0.0)
    request = install(monkeypatch, boundary)
    opti_module.steady_roll_worker(request)
    alpha = boundary.variables[0]["init_guess"]
    assert math.isclose(start_of_p(boundary), 5.0 / math.cos(math.radians(alpha)), rel_tol=1e-9)
    probes = [op["p"] for op in boundary.operating_points[:2]]
    p_limit = 2.0 * SPEED / 1.4
    assert probes[0] == 0.0
    assert math.isclose(probes[1], 0.25 * p_limit * math.cos(math.radians(alpha)), rel_tol=1e-12)


async def test_the_start_is_negative_for_a_negative_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = Boundary(-2.0, 4.0)
    boundary.moments = lambda _alpha, p_body: (-0.01 - 0.002 * p_body, 0.0)
    request = install(monkeypatch, boundary).model_copy(update={"delta_deg": -20.0})
    opti_module.steady_roll_worker(request)
    assert start_of_p(boundary) < 0.0


async def test_the_start_stays_inside_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """A zero beyond 90 % of the window is cut to it: the start is no bound hit."""
    boundary = Boundary(2.0, 4.0)
    boundary.moments = lambda _alpha, p_body: (10.0 - 0.002 * p_body, 0.0)
    request = install(monkeypatch, boundary)
    opti_module.steady_roll_worker(request)
    assert math.isclose(start_of_p(boundary), 0.9 * P_LIMIT, rel_tol=1e-12)


async def test_a_roll_without_damping_starts_from_the_fixed_fraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No slope (or the wrong sign): the secant says nothing, the fixed fraction is the start."""
    boundary = Boundary(2.0, 4.0)
    request = install(monkeypatch, boundary)
    opti_module.steady_roll_worker(request)
    assert math.isclose(
        start_of_p(boundary), opti_module.ROLL_START_FRACTION * P_LIMIT, rel_tol=1e-12
    )
