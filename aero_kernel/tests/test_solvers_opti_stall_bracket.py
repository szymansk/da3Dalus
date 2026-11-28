"""The stall worker where the first C_L extremum changes with the speed (gh-1423, canon K32).

The first lift peak of an airplane depends on the Reynolds number, so on the speed of the sweep
that locates it. The fakes here give the lift curve a different first peak below and above a
transition speed and let "IPOPT" answer the optimum of that model inside the window it is given.
Weight 1.5 kg * 9.81 m/s^2 = 14.715 N, S_ref 0.28 m^2, rho 1.225 kg/m^3, so a peak of C_L carries
the weight at ``V = sqrt(2 * 14.715 / (1.225 * 0.28 * C_L)) = sqrt(85.80175 / C_L)``:

- C_L 1.00 at 9.2629 m/s (the speed of the first bracketing sweep, ``BRACKET_CL``),
- C_L 1.10 at 8.8318 m/s,
- C_L 1.25 at 8.2850 m/s,
- C_L 1.40 at 7.8286 m/s.
"""

import math
from collections.abc import Callable, Sequence
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import Polar
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import (
    BracketRelocation,
    OptiAdapter,
    StallRequest,
    StallSolution,
)
from aero_kernel.tests.solver_builders import (
    AIR,
    K_E_D0,
    InProcessRuntime,
    airplane,
    direct_aero_model,
)
from aero_kernel.tests.stall_stubs import lift_curve_at

pytestmark = pytest.mark.asyncio

S_REF = 0.28
MASS_KG, GRAVITY = 1.5, 9.81
NO_SOLUTION = "no_consistent_first_lift_extremum"

# The first extremum (alpha in deg, C_L) of the faked lift curve at a speed in m/s.
PeakOfSpeed = Callable[[float], tuple[float, float]]
# The optimum (V in m/s, alpha in deg) the faked IPOPT finds between two bounds of alpha in deg.
Solve = Callable[[float, float], tuple[float, float]]


def carrying_speed(cl: float) -> float:
    """The speed in m/s at which a lift coefficient carries the weight of the request."""
    return math.sqrt(2.0 * MASS_KG * GRAVITY / (AIR.density * S_REF * abs(cl)))


class ScriptedOpti:
    """A faked ``asb.Opti``: two variables (speed, alpha), an optimum from the test's script."""

    def __init__(self, solve: Solve, windows: list[tuple[float, float]]) -> None:
        self._solve, self._windows = solve, windows
        self._bounds: list[tuple[float, float]] = []

    def variable(self, *, init_guess: float, lower_bound: float, upper_bound: float) -> int:
        assert lower_bound <= init_guess <= upper_bound
        self._bounds.append((lower_bound, upper_bound))
        return len(self._bounds) - 1  # 0: the speed, 1: alpha

    def subject_to(self, _constraint: object) -> None:
        return None

    def minimize(self, _objective: object) -> None:
        return None

    def solve(self, **_options: object) -> Callable[[int], float]:
        window = self._bounds[1]
        self._windows.append(window)
        optimum = self._solve(*window)
        return lambda variable: optimum[variable]


class Scene:
    """The faked boundary of one test: what was swept and which windows IPOPT was given."""

    def __init__(self) -> None:
        self.bracketing_speeds: list[float] = []
        self.published_speeds: list[float] = []
        self.windows: list[tuple[float, float]] = []


def install(
    monkeypatch: pytest.MonkeyPatch, peak_of: PeakOfSpeed, solve: Solve, n_load: float = 1.0
) -> tuple[StallRequest, Scene]:
    """Fake the worker's solver boundary with a lift curve whose first extremum depends on the speed."""
    scene = Scene()
    upright = n_load > 0.0

    def sweep_lift(
        _plane: object, _air: object, speed: float, angles: Sequence[float], _size: str
    ) -> Polar:
        scene.bracketing_speeds.append(speed)
        return lift_curve_at(peak_of(speed), upright, angles)

    def sweep_polar(
        _plane: object, _air: object, speed: float, angles: Sequence[float], _size: str, _k: float
    ) -> Polar:
        scene.published_speeds.append(speed)
        return lift_curve_at(peak_of(speed), upright, angles)

    def opti() -> ScriptedOpti:
        return ScriptedOpti(solve, scene.windows)

    def operating_point(**_: object) -> None:
        return None

    def aerobuildup(*_: object, **__: object) -> SimpleNamespace:
        return SimpleNamespace(run=lambda: {"L": 0.0})

    def convert(_: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=S_REF)

    fake_asb = SimpleNamespace(Opti=opti, OperatingPoint=operating_point, AeroBuildup=aerobuildup)
    monkeypatch.setattr(opti_module, "sweep_lift", sweep_lift)
    monkeypatch.setattr(opti_module, "sweep_polar", sweep_polar)
    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "load_aerosandbox", lambda: fake_asb)
    monkeypatch.setattr(opti_module, "aero_model", direct_aero_model)
    request = StallRequest(
        airplane=airplane(), mass_kg=MASS_KG, gravity=GRAVITY, n_load=n_load, air=AIR, k_e_d0=K_E_D0
    )
    return request, scene


def optimum_of(peak_of: PeakOfSpeed, candidates: Sequence[float]) -> Solve:
    """The faked IPOPT of a model whose self-consistent stall speeds are ``candidates``.

    A candidate speed whose own first peak lies inside the window is the optimum (the slowest one);
    without one the lift still rises at the upper bound of alpha, which is where IPOPT ends.
    """

    def solve(low: float, high: float) -> tuple[float, float]:
        for speed in sorted(candidates):
            alpha, _cl = peak_of(speed)
            if low < alpha < high:
                return speed, alpha
        return 8.5, high

    return solve


# --- a consistent first peak exists, the two bracketing sweeps miss it (AERONCA_CHAMP) -------------


def three_branches(speed: float) -> tuple[float, float]:
    """First peak at 6 deg (C_L 1.10) below 8.2 m/s, at 9 deg (1.25) up to 9 m/s, (9 deg, 1.40) above.

    The peak of 1.25 carries the weight at 8.2850 m/s, inside its own range: the stall speed. The
    two bracketing sweeps miss it: the first (9.2629 m/s) sees C_L 1.40, whose carrying speed
    7.8286 m/s lies below 8.2 m/s, where the first peak is the one at 6 deg.
    """
    if speed < 8.2:
        return 6.0, 1.10
    return (9.0, 1.25) if speed < 9.0 else (9.0, 1.40)


async def test_a_first_peak_that_moved_is_located_again_and_the_stall_speed_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v_s = carrying_speed(1.25)
    request, scene = install(monkeypatch, three_branches, optimum_of(three_branches, [v_s]))
    outcome = opti_module.stall_worker(request)
    solution = outcome.value
    assert (solution.v_s, solution.alpha_s, solution.cl_max) == (v_s, 9.0, 1.25)
    # the first window ends one step past the peak at 6 deg, the second one step past the one at 9 deg
    assert scene.windows == [(-15.0, 6.25), (-15.0, 9.25)]
    assert scene.published_speeds == [v_s]


async def test_the_relocation_is_recorded_with_both_brackets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sweep 2 runs at 7.8286 m/s (peak 6 deg); the bracket that holds lies at a speed at or above the
    transition (8.2 m/s) whose peak is the one at 9 deg."""
    v_s = carrying_speed(1.25)
    request, _ = install(monkeypatch, three_branches, optimum_of(three_branches, [v_s]))
    relocation = opti_module.stall_worker(request).value.relocation
    assert relocation is not None
    assert math.isclose(relocation.first_v_ms, carrying_speed(1.40), rel_tol=1e-12)
    assert relocation.first_alpha_deg == 6.0
    assert relocation.alpha_deg == 9.0
    assert 8.2 <= relocation.v_ms < 9.0


async def test_a_first_peak_that_drifted_one_sweep_step_is_located_again_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The peak lies at 9 deg below 8.3 m/s and at 9.25 deg from there on, with
    ``C_L = 0.32371 + 0.1 V`` (1.25 at the first sweep's 9.2629 m/s). Sweep 2 runs at 8.2850 m/s
    (peak 9 deg, C_L 1.1522, window to 9.25 deg); the lift balance closes at 8.5366 m/s
    (``V^2 (0.32371 + 0.1 V) = 85.80175``), where the peak lies at 9.25 deg: on the window's edge.
    The window is moved with the peak (to 9.5 deg) instead of refusing the optimum (AERONCA_CHAMP at
    0.36 kg)."""

    def drifting(speed: float) -> tuple[float, float]:
        return (9.0 if speed < 8.3 else 9.25), 0.32371 + 0.1 * speed

    v_s = 8.5366
    request, scene = install(monkeypatch, drifting, optimum_of(drifting, [v_s]))
    solution = opti_module.stall_worker(request).value
    assert (solution.v_s, solution.alpha_s) == (v_s, 9.25)
    assert scene.windows == [(-15.0, 9.25), (-15.0, 9.5)]
    assert solution.relocation is not None
    assert (solution.relocation.first_alpha_deg, solution.relocation.alpha_deg) == (9.0, 9.25)


async def test_the_adapter_declares_a_relocated_bracket(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR 0020: a second bracket is a declared step, a ``notice`` with both brackets in its detail."""
    polar = Polar(alpha_deg=(0.0, 9.0, 20.0), cl=(0.3, 1.25, 1.0), cd=(0.01,) * 3)
    relocation = BracketRelocation(first_v_ms=7.83, first_alpha_deg=6.0, v_ms=8.3, alpha_deg=9.0)
    found = StallSolution(v_s=8.285, cl_max=1.25, alpha_s=9.0, polar=polar, relocation=relocation)

    def worker(_request: StallRequest) -> WorkerOutcome[StallSolution]:
        return WorkerOutcome(value=found, diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "stall_worker", worker)
    stall = await OptiAdapter(InProcessRuntime()).stall(airplane(), MASS_KG, GRAVITY, 1.0, AIR)
    (notice,) = [w for w in stall.warnings if w.code == "stall_bracket_relocated"]
    assert notice.severity == "notice"
    assert notice.detail == {
        "first_v_ms": 7.83,
        "first_alpha_deg": 6.0,
        "v_ms": 8.3,
        "alpha_deg": 9.0,
    }
    assert "6 deg" in notice.message
    assert "9 deg" in notice.message


async def test_a_bracket_that_holds_takes_two_bracketing_sweeps_and_no_relocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The procedure of the canon entry is unchanged where it works: two bracketing sweeps (at the
    speed of C_L = 1, then at the speed its peak implies), one IPOPT run, one published sweep."""

    def one_branch(_speed: float) -> tuple[float, float]:
        return 12.0, 1.25

    v_s = carrying_speed(1.25)
    request, scene = install(monkeypatch, one_branch, optimum_of(one_branch, [v_s]))
    outcome = opti_module.stall_worker(request)
    assert outcome.value.relocation is None
    assert scene.windows == [(-15.0, 12.25)]
    assert len(scene.bracketing_speeds) == 2
    assert math.isclose(scene.bracketing_speeds[0], carrying_speed(1.0), rel_tol=1e-12)
    assert math.isclose(scene.bracketing_speeds[1], v_s, rel_tol=1e-12)


async def test_an_optimum_on_the_edge_of_a_bracket_that_holds_is_still_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The peak does not move with the speed, and still IPOPT ends on the window's edge: that is a
    failed solve, not a missing stall speed."""

    def one_branch(_speed: float) -> tuple[float, float]:
        return 12.0, 1.25

    request, _ = install(monkeypatch, one_branch, lambda _low, high: (8.5, high))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.code == "not_converged"
    assert raised.value.detail["variable"] == "alpha"


# --- no speed closes the lift balance at a first peak (AVISTAR_ELITE, 8.8 to 9.4 kg) ---------------


def two_branches(speed: float) -> tuple[float, float]:
    """First peak at 8 deg (C_L 1.10) below 8.6 m/s, at 16 deg (C_L 1.25) from 8.6 m/s on.

    The peak of 1.10 carries the weight at 8.8318 m/s, where it is no longer the first peak; the peak
    of 1.25 carries it at 8.2850 m/s, where it is not the first peak yet. At 8.6 m/s the first peak
    carries 0.5 * 1.225 * 8.6^2 * 0.28 * 1.10 = 13.9538 N (1.4224 kg) just below and
    0.5 * 1.225 * 8.6^2 * 0.28 * 1.25 = 15.8566 N (1.6164 kg) from there on; 14.715 N lies between.
    """
    return (8.0, 1.10) if speed < 8.6 else (16.0, 1.25)


async def test_a_weight_between_two_branches_of_the_first_peak_has_no_stall_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _ = install(monkeypatch, two_branches, optimum_of(two_branches, []))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    error = raised.value
    assert error.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert error.code == NO_SOLUTION
    detail = error.detail
    assert math.isclose(float(str(detail["transition_v_ms"])), 8.6, abs_tol=1e-3)
    assert (detail["alpha_below_deg"], detail["cl_below"]) == (8.0, 1.10)
    assert (detail["alpha_above_deg"], detail["cl_above"]) == (16.0, 1.25)
    assert math.isclose(float(str(detail["lift_below_n"])), 13.9538, abs_tol=5e-3)
    assert math.isclose(float(str(detail["lift_above_n"])), 15.8566, abs_tol=5e-3)
    assert math.isclose(float(str(detail["lift_required_n"])), 14.715, rel_tol=1e-12)
    assert math.isclose(float(str(detail["mass_below_kg"])), 1.4224, abs_tol=5e-4)
    assert math.isclose(float(str(detail["mass_above_kg"])), 1.6164, abs_tol=5e-4)


async def test_the_failure_says_why_in_words(monkeypatch: pytest.MonkeyPatch) -> None:
    request, _ = install(monkeypatch, two_branches, optimum_of(two_branches, []))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    message = raised.value.message
    assert "no stall speed" in message
    assert "8.6 m/s" in message
    assert "8 deg" in message
    assert "16 deg" in message
    assert "1.422 kg" in message
    assert "1.616 kg" in message
    assert "not a failed solve" in raised.value.hint


def drifting_two_branches(speed: float) -> tuple[float, float]:
    """As :func:`two_branches` from 8.3 m/s on, with a C_L of the upper peak that falls with the speed.

    ``C_L = 1.25 - 0.02 (V - 8.3)``: the first bracketing sweep (9.2629 m/s) sees 1.2307, whose
    carrying speed 8.3496 m/s lies above the transition at 8.3 m/s, so the bracket is the peak at
    16 deg; the optimum on that branch (8.2863 m/s) lies below the transition, where the first peak
    is the one at 8 deg (the mass of the issue at which the old kernel answered
    ``postcondition_violated``).
    """
    return (8.0, 1.10) if speed < 8.3 else (16.0, 1.25 - 0.02 * (speed - 8.3))


async def test_an_optimum_below_the_transition_is_the_same_failure_as_one_above_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One failure for the whole band: here IPOPT finds an interior optimum on the bracket's branch,
    and the sweep at that speed shows another first peak."""
    request, scene = install(monkeypatch, drifting_two_branches, lambda _low, _high: (8.2863, 16.0))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.code == NO_SOLUTION
    assert math.isclose(float(str(raised.value.detail["transition_v_ms"])), 8.3, abs_tol=1e-3)
    assert raised.value.detail["alpha_below_deg"] == 8.0
    assert raised.value.detail["alpha_above_deg"] == 16.0
    assert scene.windows == [(-15.0, 16.25)]  # one IPOPT run, no second attempt


async def test_the_inverted_stall_has_the_same_failure_for_its_first_trough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrored: the first trough at -8 deg (C_L -1.10) below 8.6 m/s, at -12 deg (-1.25) above."""

    def troughs(speed: float) -> tuple[float, float]:
        return (-8.0, -1.10) if speed < 8.6 else (-12.0, -1.25)

    request, scene = install(monkeypatch, troughs, lambda low, _high: (8.5, low), n_load=-1.0)
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.code == NO_SOLUTION
    assert scene.windows == [(-8.25, 25.0)]
    assert (raised.value.detail["alpha_below_deg"], raised.value.detail["cl_below"]) == (
        -8.0,
        -1.10,
    )
    assert (raised.value.detail["alpha_above_deg"], raised.value.detail["cl_above"]) == (
        -12.0,
        -1.25,
    )
    assert "trough" in raised.value.message


async def test_a_first_peak_that_keeps_moving_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A peak that always needs 0.05 m/s more than the speed it was found at, and lies 2 deg away at
    that speed (6, 8, 10 deg in turn): the search ends at its step limit and says so; it neither
    returns a value nor claims that none exists."""
    balance = 2.0 * MASS_KG * GRAVITY / (AIR.density * S_REF)  # C_L V^2 of the weight

    def runaway(speed: float) -> tuple[float, float]:
        return 6.0 + 2.0 * (round(20.0 * speed) % 3), balance / (speed + 0.05) ** 2

    request, _ = install(monkeypatch, runaway, lambda _low, high: (8.5, high))
    with pytest.raises(FormulaError) as raised:
        opti_module.stall_worker(request)
    assert raised.value.code == "not_converged"
    assert "first C_L peak" in raised.value.message
    assert raised.value.detail["sweeps"] == opti_module.BRACKET_RELOCATION_SWEEPS
