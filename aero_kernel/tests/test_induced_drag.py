"""The kernel's drag from AeroBuildup: the full-scale viscous factor k_e,D0 removed (#1346).

Fast tier, AeroSandbox faked at the solver boundary. AeroBuildup's induced drag uses the Nita-Scholz
Oswald factor, which holds the viscous factor k_e,D0; NeuralFoil's section polars already carry the
lift-dependent profile drag. The kernel uses ``D = D_profile + k_e,D0 * D_induced`` wherever it
takes drag from AeroBuildup, reads k_e,D0 from the canon rule ``aerobuildup-induced-drag`` and
declares every value that carries the correction with the notice
``induced_drag_viscous_factor_removed``.
"""

import math
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from aero_kernel.build import shipped_build
from aero_kernel.rules import Rules
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers import aerobuildup as aerobuildup_module
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.aero_model import MODEL_OUTPUTS
from aero_kernel.solvers.aerobuildup import (
    INDUCED_DRAG_RULE,
    VISCOUS_FACTOR_PARAMETER,
    evaluate_forces,
    kernel_drag,
    sweep_lift,
    sweep_polar,
)
from aero_kernel.solvers.opti import EvaluationRequest, Forces, OptiAdapter
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime, airplane

CODE = "induced_drag_viscous_factor_removed"
# The canon's value (rules.yaml): the mean of the four Nita-Scholz classes AeroSandbox uses.
CANON_K_E_D0 = (0.873 + 0.864 + 0.804 + 0.804) / 4.0


def canon_k_e_d0() -> float:
    rule = shipped_build().model.namespaces["calc"].rules[INDUCED_DRAG_RULE]
    return rule.parameters[VISCOUS_FACTOR_PARAMETER].value


def test_the_canon_holds_the_viscous_factor_as_an_adopted_sourced_rule_parameter() -> None:
    rule = shipped_build().model.namespaces["calc"].rules[INDUCED_DRAG_RULE]
    parameter = rule.parameters[VISCOUS_FACTOR_PARAMETER]
    assert math.isclose(parameter.value, CANON_K_E_D0, rel_tol=0.0, abs_tol=1e-12)
    assert (parameter.unit, parameter.basis, parameter.status) == ("1", "sourced", "adopted")
    assert rule.codes == [CODE]
    assert rule.applies_to.formula == "aerobuildup-evaluation"


def test_the_notice_is_a_notice() -> None:
    from aero_kernel.schema import WARNING_CATALOGUE

    assert WARNING_CATALOGUE[CODE] is WarningSeverity.NOTICE


# --- the one function ------------------------------------------------------------------------


def test_kernel_drag_is_profile_plus_the_factor_times_induced() -> None:
    """D = D_profile + k_e,D0 * D_induced: 0.6 + 0.83625 * 0.4 = 0.9345 N."""
    result = {"D": 1.0, "D_profile": 0.6, "D_induced": 0.4}
    assert math.isclose(kernel_drag(result, CANON_K_E_D0), 0.6 + CANON_K_E_D0 * 0.4)


def test_kernel_drag_with_a_factor_of_one_is_aerobuildups_drag() -> None:
    result = {"D_profile": np.array([0.6, 0.7]), "D_induced": np.array([0.4, 0.2])}
    assert np.allclose(kernel_drag(result, 1.0), [1.0, 0.9])


def test_kernel_drag_never_reads_aerobuildups_total_drag() -> None:
    """The total ``D`` holds the viscous factor; the kernel builds its drag from the parts only."""
    assert kernel_drag({"D_profile": 0.5, "D_induced": 0.5}, 0.5) == 0.75


def test_the_model_function_offers_the_drag_parts_and_no_total_drag() -> None:
    """A reader of the model function cannot take AeroBuildup's own D or C_D (ADR 0022)."""
    assert "D_profile" in MODEL_OUTPUTS
    assert "D_induced" in MODEL_OUTPUTS
    assert "D" not in MODEL_OUTPUTS
    assert "CD" not in MODEL_OUTPUTS


# --- the numeric runs --------------------------------------------------------------------------


def fake_aerobuildup(
    monkeypatch: pytest.MonkeyPatch, result: dict[str, Any], seen: list[Any] | None = None
) -> None:
    """Fake AeroSandbox whose AeroBuildup returns ``result``; the operating point knows its q."""

    def aerobuildup(_airplane: object, op_point: Any, **_: object) -> SimpleNamespace:
        if seen is not None:
            seen.append(op_point)
        return SimpleNamespace(run=lambda: result)

    def operating_point(**kwargs: Any) -> SimpleNamespace:
        point = SimpleNamespace(**kwargs)
        point.dynamic_pressure = lambda: 0.5 * kwargs["atmosphere"].density() * point.velocity**2
        return point

    fake = SimpleNamespace(AeroBuildup=aerobuildup, OperatingPoint=operating_point)
    monkeypatch.setattr(aerobuildup_module, "load_aerosandbox", lambda: fake)


def test_evaluate_forces_returns_the_kernel_drag(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_aerobuildup(
        monkeypatch,
        {"L": np.array([14.7]), "D": 1.0, "D_profile": np.array([0.6]), "D_induced": 0.4},
    )
    lift, drag = evaluate_forces(object(), AIR, 10.0, 4.0, "xlarge", 0.8)
    assert lift == 14.7
    assert math.isclose(drag, 0.6 + 0.8 * 0.4)


def test_the_sweep_drag_coefficient_is_the_kernel_drag_over_q_s_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C_D = (D_profile + k D_induced) / (q S_ref), q from AeroSandbox's operating point."""
    result = {
        "CL": np.array([0.1, 0.5]),
        "CD": np.array([9.0, 9.0]),  # AeroBuildup's own C_D: never read
        "Cm": np.zeros(2),
        "D_profile": np.array([1.0, 1.5]),
        "D_induced": np.array([0.1, 2.0]),
    }
    fake_aerobuildup(monkeypatch, result)
    plane = SimpleNamespace(s_ref=0.25)
    polar = sweep_polar(plane, AIR, 9.0, [0.0, 4.0], "xlarge", 0.5)
    q_s = 0.5 * AIR.density * 9.0**2 * 0.25
    assert np.allclose(polar.cd, [(1.0 + 0.05) / q_s, (1.5 + 1.0) / q_s])
    assert polar.cl == (0.1, 0.5)


def test_the_lift_sweep_reads_no_drag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bracketing sweeps need C_L only, so they never read a drag."""
    seen: list[Any] = []
    fake_aerobuildup(monkeypatch, {"CL": np.array([0.1, 0.5])}, seen)
    curve = sweep_lift(object(), AIR, 9.0, [0.0, 4.0], "xlarge")
    assert (curve.alpha_deg, curve.cl) == ((0.0, 4.0), (0.1, 0.5))
    (point,) = seen
    assert list(point.velocity) == [9.0, 9.0]


# --- the adapter reads the factor from the rule and declares it --------------------------------


def canned_forces(seen: list[EvaluationRequest]) -> object:
    def worker(request: EvaluationRequest) -> WorkerOutcome[Forces]:
        seen.append(request)
        return WorkerOutcome(
            value=Forces(lift_n=14.7, drag_n=0.9), diagnostics=WorkerDiagnostics(duration_s=0.0)
        )

    return worker


@pytest.mark.asyncio
async def test_the_evaluation_takes_the_factor_from_the_rule_and_declares_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[EvaluationRequest] = []
    monkeypatch.setattr(opti_module, "evaluation_worker", canned_forces(seen))
    rules = Rules(shipped_build().model)
    result = await OptiAdapter(InProcessRuntime(), rules).evaluate(airplane(), AIR, 10.0, 4.0)
    (request,) = seen
    assert request.k_e_d0 == canon_k_e_d0()
    (notice,) = [w for w in result.warnings if w.code == CODE]
    assert notice.severity is WarningSeverity.NOTICE
    assert notice.detail == {
        "k_e_d0": canon_k_e_d0(),
        "induced_drag_share_removed": 1.0 - canon_k_e_d0(),
    }
    (used,) = [u for u in rules.used() if u.rule == INDUCED_DRAG_RULE]
    assert (used.parameter, used.value, used.basis, used.overridden) == (
        VISCOUS_FACTOR_PARAMETER,
        canon_k_e_d0(),
        "sourced",
        False,
    )


@pytest.mark.asyncio
async def test_an_override_of_the_factor_reaches_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[EvaluationRequest] = []
    monkeypatch.setattr(opti_module, "evaluation_worker", canned_forces(seen))
    key = f"{INDUCED_DRAG_RULE}.{VISCOUS_FACTOR_PARAMETER}"
    rules = Rules(shipped_build().model, {key: 1.0})
    result = await OptiAdapter(InProcessRuntime(), rules).evaluate(airplane(), AIR, 10.0, 4.0)
    assert seen[0].k_e_d0 == 1.0
    (notice,) = [w for w in result.warnings if w.code == CODE]
    assert notice.detail["induced_drag_share_removed"] == 0.0


@pytest.mark.asyncio
async def test_the_stall_glide_and_sink_problems_carry_the_factor_and_the_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aero_kernel.tests.test_solvers_opti import solution

    requests: list[Any] = []

    def canned(value: object) -> object:
        def worker(request: Any) -> WorkerOutcome[Any]:
            requests.append(request)
            return WorkerOutcome(value=value, diagnostics=WorkerDiagnostics(duration_s=0.0))

        return worker

    glide = opti_module.BestGlideSolution(v_md=9.0, e_max=10.0, alpha_md=3.0, cl_md=0.6)
    sink = opti_module.MinSinkSolution(v_mp=7.0, alpha_mp=6.0, cl_mp=0.9)
    monkeypatch.setattr(opti_module, "stall_worker", canned(solution(v_s=6.0)))
    monkeypatch.setattr(opti_module, "best_glide_worker", canned(glide))
    monkeypatch.setattr(opti_module, "min_sink_worker", canned(sink))
    adapter = OptiAdapter(InProcessRuntime())
    found = [
        (await adapter.stall(airplane(), 1.5, 9.81, 1.0, AIR)).warnings,
        (await adapter.best_glide(airplane(), 1.5, 9.81, 1.0, AIR)).warnings,
        (await adapter.min_sink(airplane(), 1.5, 9.81, 1.0, AIR)).warnings,
    ]
    assert [r.k_e_d0 for r in requests] == [canon_k_e_d0()] * 3
    assert [[w.code for w in warnings].count(CODE) for warnings in found] == [1, 1, 1]
