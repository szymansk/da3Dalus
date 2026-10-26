"""The steady roll of the Opti adapter on a configuration with flaps (fast tier, stubbed solver, #1212)."""

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import OptiAdapter, RollRequest
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime
from aero_kernel.tests.test_solvers_opti_roll import GRAVITY, MASS, SPEED, canned, solution
from aero_kernel.tests.test_solvers_roll_devices import wing_geometry

pytestmark = pytest.mark.asyncio


def flaperon(
    deflection: float | None, root: float | None = 0.78, tip: float | None = 0.80
) -> AirplaneGeometry:
    return wing_geometry(
        (0.0, 0.2, 0.4),
        1,
        {
            "name": "Klappe",
            "role": "flaperon",
            "rel_chord_root": root,
            "rel_chord_tip": tip,
            "deflection_deg": deflection,
        },
    )


async def test_a_flaperon_with_a_bias_reaches_the_worker_and_declares_hinge_and_model_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flaperon is both a roll device and a flap: one averaged-hinge warning for it, and the
    model-range warning carries the flap with the diagnostics of the deflected run."""
    seen: list[RollRequest] = []
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution(), seen))
    plane = flaperon(25.0)
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(plane, MASS, GRAVITY, AIR, SPEED, 10.0)
    assert seen[0].airplane == plane
    assert [w.code for w in roll.warnings if not w.code.startswith("reynolds")] == [
        "hinge_line_averaged",
        "control_surface_fit_range_unknown",
    ]
    (fit,) = [w for w in roll.warnings if w.code == "control_surface_fit_range_unknown"]
    assert fit.detail["flaps"] == [{"wing": "Main", "device": "Klappe", "deflection_deg": 25.0}]
    assert fit.detail["min_confidence"] == 0.61


async def test_a_flap_bias_without_a_command_declares_the_model_range_without_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        opti_module, "steady_roll_worker", canned(solution(0.0, with_diagnostics=False))
    )
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        flaperon(25.0), MASS, GRAVITY, AIR, SPEED, 0.0
    )
    (fit,) = [w for w in roll.warnings if w.code == "control_surface_fit_range_unknown"]
    assert set(fit.detail) == {"flaps"}


async def test_a_flaperon_at_rest_without_a_command_declares_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        opti_module, "steady_roll_worker", canned(solution(0.0, with_diagnostics=False))
    )
    roll = await OptiAdapter(InProcessRuntime()).steady_roll(
        flaperon(0.0), MASS, GRAVITY, AIR, SPEED, 0.0
    )
    assert roll.warnings == ()


async def test_a_flap_without_a_hinge_is_invalid_input_before_any_solve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[RollRequest] = []
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution(), seen))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).steady_roll(
            flaperon(25.0, root=None, tip=None), MASS, GRAVITY, AIR, SPEED, 0.0
        )
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert seen == []
