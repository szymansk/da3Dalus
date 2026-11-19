"""Builders for the endurance and range tests: a speed-dependent AeroBuildup stand-in and bound inputs.

The aerodynamic boundary is a stub with a closed-form drag, ``D(V) = a V^2 + b / V^2`` N (the lift
balance is not what these tests are about); everything behind it, the drive train, is checked against
the separately written plain-Python model of ``powertrain_reference`` (published APC 13x8E table,
T-Motor AT2814 KV900 on 14.8 V, rho = 1.225 kg/m^3).
"""

from typing import Any

from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.errors import ErrorCategory, FormulaError, display_slug
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import LevelFlightPoint, LevelPoint
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.formula_builders import inputs_from_model, solvers_with
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.wing_builders import airplane_document

RHO, D_PROP, U_BAT, MASS, G = 1.225, 13 * 0.0254, 14.8, 3.4, 9.80665
KV, I0, RM = 900.0, 1.2, 0.082
E_BAT_WH = 74.0  # 5 Ah on the 4S pack: the rated energy of the tests (marked test value)
SPEED_OF_SOUND = 340.0


class SpeedOpti(StubOpti):
    """AeroBuildup stand-in for the level-flight solve with ``D(V) = a V^2 + b / V^2`` N.

    Below ``min_speed`` the lift cannot reach the weight: the adapter's declared ``not_converged``.
    """

    def __init__(
        self,
        a: float = 0.01,
        b: float = 200.0,
        min_speed: float = 0.0,
        warnings: tuple[KernelWarning, ...] = (),
    ) -> None:
        super().__init__()
        self.a, self.b, self.min_speed, self.warnings = a, b, min_speed, warnings
        self.speeds: list[float] = []

    def drag(self, v: float) -> float:
        """The stub's drag in N at the speed."""
        return self.a * v**2 + self.b / v**2

    async def level_flight_point(
        self, airplane: AirplaneGeometry, mass_kg: float, gravity: float, air: AirState, v_ms: float
    ) -> LevelFlightPoint:
        self.speeds.append(v_ms)
        if v_ms < self.min_speed:
            raise FormulaError(
                ErrorCategory.NOT_CONVERGED,
                "not_converged",
                "the airplane does not reach the level lift below its first C_L peak",
                "check mass and speed",
                detail={"v_ms": v_ms},
            )
        point = LevelPoint(
            v_ms=v_ms,
            alpha_deg=3.0,
            cl=0.5,
            cd=0.05,
            lift_n=mass_kg * gravity,
            drag_n=self.drag(v_ms),
        )
        return LevelFlightPoint(point=point, warnings=self.warnings)


def context_of(slug: str, opti: StubOpti) -> Context:
    """The context the engine builds for a formula: the relations of its embeds closure."""
    formula = shipped_build().model.formula(slug)
    assert formula is not None
    relations = {
        item: DEFAULT_REGISTRY.relation_of(item.split(".")[0]) for item in formula.embeds_closure
    }
    return Context(
        origin="t",
        solvers=solvers_with(opti=opti),
        relations={k: v for k, v in relations.items() if v is not None},
    )


def bound(
    slug: str, extra: dict[str, Any] | None = None, application: str = "default"
) -> dict[str, Any]:
    """``x`` of the formula from the model, on the AT2814 / APC 13x8E drive train of the tests."""
    by_quantity: dict[str, Any] = {
        "airplane": AirplaneGeometry.model_validate(airplane_document()),
        "aircraft-mass": MASS,
        "gravity": G,
        "air-density": RHO,
        "dynamic-viscosity": 1.8e-5,
        "speed-of-sound": SPEED_OF_SOUND,
        "components": complete_components_with_table(),
        "battery-capacity": E_BAT_WH,
        "motor-voltage-constant": KV,
        "motor-no-load-current": I0,
        "motor-circuit-resistance": RM,
        "battery-voltage": U_BAT,
        "motor-max-power": 650.0,
        "propeller-diameter": D_PROP,
        "motor-efficiency": 0.8,
    }
    model = shipped_build().model
    formula = model.formula(slug)
    assert formula is not None
    wanted = {
        display_slug(q)
        for q in formula.application(application).bind.values()
        if isinstance(q, str)
    }
    given = {k: v for k, v in by_quantity.items() if display_slug(k) in wanted}
    given.update(extra or {})
    return inputs_from_model(model, slug, given, application)
