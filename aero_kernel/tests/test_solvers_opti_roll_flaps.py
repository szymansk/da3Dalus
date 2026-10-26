"""The steady roll of the Opti adapter on a configuration with flaps (fast tier, stubbed solver, #1212)."""

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import OptiAdapter, RollRequest
from aero_kernel.tests.solver_builders import AIR, InProcessRuntime
from aero_kernel.tests.test_solvers_opti_roll import GRAVITY, MASS, SPEED, canned, solution
from aero_kernel.tests.test_solvers_roll_devices import wing_geometry


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_a_flap_without_a_hinge_is_invalid_input_before_any_solve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[RollRequest] = []
    monkeypatch.setattr(opti_module, "steady_roll_worker", canned(solution(), seen))
    adapter = OptiAdapter(InProcessRuntime())
    hingeless = flaperon(25.0, root=None, tip=None)
    with pytest.raises(FormulaError) as raised:
        await adapter.steady_roll(hingeless, MASS, GRAVITY, AIR, SPEED, 0.0)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert seen == []


def test_the_confidence_run_reports_the_lowest_confidence_and_its_wing() -> None:
    """The recording pass (M1) over a fake AeroSandbox: every section call is seen, the lowest
    NeuralFoil confidence and the highest angle win."""
    import numpy as np

    class Airfoil:
        def __init__(self, name: str, coordinates: object) -> None:
            self.name, self.coordinates = name, coordinates

        def get_aero_from_neuralfoil(self, **kwargs: object) -> dict[str, object]:
            confidence = 0.4 if self.name == "weak" else 0.9
            return {"analysis_confidence": np.array([confidence, 0.95])}

    class Xsec:
        def __init__(self, name: str) -> None:
            self.airfoil = Airfoil(name, None)

    class Wing:
        def __init__(self, *names: str) -> None:
            self.xsecs = [Xsec(n) for n in names]

    class Airplane:
        def __init__(self) -> None:
            self.wings = [Wing("fine", "fine"), Wing("fine", "weak")]

    class AeroBuildup:
        def __init__(self, airplane: Airplane, point: object, model_size: str) -> None:
            self.airplane = airplane

        def run(self) -> None:
            for wing in self.airplane.wings:
                for xsec in wing.xsecs:
                    xsec.airfoil.get_aero_from_neuralfoil(alpha=np.array([5.0, 7.0]))

    asb = type("Asb", (), {"Airfoil": Airfoil, "AeroBuildup": AeroBuildup})
    found = opti_module._confidence_run(  # pyright: ignore[reportPrivateUsage]
        asb, Airplane(), ["Main", "Tail"], object()
    )
    assert (found.min_confidence, found.min_confidence_wing) == (0.4, "Tail")
    assert found.max_effective_alpha_deg == 7.0
