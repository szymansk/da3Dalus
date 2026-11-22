"""The reference fleet through the whole chain with fake solvers: the fast counterpart of the aero tier.

The aero tier runs the fleet through ``compute()`` with the real AeroSandbox and the real AVL and
pins the values (``test_*_fleet.py``). This module runs the same documents, the same request and the
same caller values through the same engine and the shipped canon, with the stub adapters of the
per-formula tests at the solver boundary (#1458, P8-F04). What the solvers would answer is fake, so
no value of such a run is an aircraft's value; what is real is everything the engine decides from
the document and the canon: which application binds, what is ``not_applicable``, which error a
layout gets and what fails upstream of it, the worlds of an interval, and the arithmetic of the
nodes that only combine their inputs.
"""

from dataclasses import dataclass
from typing import Any, cast

from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, solvers_with
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.reference_fleet import FleetMember, fleet_values, reference_document
from aero_kernel.tests.stall_stubs import StubOpti

__all__ = [
    "CHAIN_VALUES",
    "FAKE_DENSITY",
    "FAKE_X_NP_AVL",
    "NEUTRAL_POINT_WORLDS",
    "OK",
    "ROLL_RATE_WORLDS",
    "SM_TARGET",
    "FleetChainRun",
    "Outcome",
    "outcome_of",
    "run_fleet_chain",
]

FAKE_DENSITY = 1.225  # kg/m^3, the stub atmosphere's answer at the altitude 0 m
FAKE_X_NP_AVL = 0.14  # m, the stub AVL's neutral point, the same for every aircraft
SM_TARGET = 0.10  # the static-margin target of the fleet tests
# The caller values of test_plan_batch_fleet.run(): sea level, SM_target and the aileron command.
CHAIN_VALUES: dict[str, float] = {
    "altitude": 0.0,
    "static-margin-target": SM_TARGET,
    "aileron-deflection": 20.0,
}
NEUTRAL_POINT_WORLDS = frozenset(
    {"neutral-point=textbook", "neutral-point=pappas", "neutral-point=avl"}
)
ROLL_RATE_WORLDS = frozenset({"roll-rate=aerobuildup", "roll-rate=avl"})
OK = "ok"


@dataclass(frozen=True)
class Outcome:
    """What the kernel answers for one quantity, without the value.

    Attributes:
        status: ``ok``, ``not_applicable``, or the code of the error.
        causes: ``(quantity, code)`` per cause of an ``upstream_failed`` error, in the kernel's order.
    """

    status: str
    causes: tuple[tuple[str, str], ...] = ()


def outcome_of(quantity: QuantityResult) -> Outcome:
    """The outcome of a quantity result: its status, or its error code with the causes upstream."""
    if quantity.status is not QuantityStatus.ERROR:
        return Outcome(quantity.status.value)
    assert quantity.error is not None, quantity.slug
    causes = cast("list[dict[str, Any]]", quantity.error.detail.get("causes", []))
    return Outcome(quantity.error.code, tuple((c["quantity"], c["code"]) for c in causes))


class FleetChainRun:
    """The result of one engine run on a fleet document and the stubs that answered it."""

    def __init__(
        self, result: ComputeResult, geometry: StubGeometry, opti: StubOpti, avl: StubAvl
    ) -> None:
        self.result = result
        self.geometry = geometry
        self.opti = opti
        self.avl = avl

    def quantity(self, slug: str) -> QuantityResult:
        """The result of the requested quantity ``slug``."""
        (found,) = [q for q in self.result.quantities if q.slug == slug]
        return found

    def outcome(self, slug: str) -> Outcome:
        """The outcome of the requested quantity ``slug``."""
        return outcome_of(self.quantity(slug))

    def value(self, slug: str) -> float:
        """The value of a scalar quantity that computed."""
        value = self.quantity(slug).value
        assert value is not None, (slug, self.quantity(slug).error)
        return value

    def worlds(self, slug: str) -> dict[str, float]:
        """The value per world assignment of an uncertain quantity that computed."""
        interval = self.quantity(slug).interval
        assert interval is not None, (slug, self.quantity(slug).error)
        return interval.worlds


async def run_fleet_chain(
    member: FleetMember,
    *slugs: str,
    values: dict[str, float] | None = None,
    document: dict[str, Any] | None = None,
    flaps: bool = True,
) -> FleetChainRun:
    """Evaluate ``slugs`` for a fleet aircraft on the shipped canon with stub adapters.

    Args:
        member: The aircraft; its mass and flap deflections are the fleet's (``fleet_values``).
        slugs: The requested quantities.
        values: Caller values on top of the fleet's and of ``CHAIN_VALUES``.
        document: A changed copy of the member's document; by default the reference document.
        flaps: Whether the fleet's flap deflections are passed; without them only the mass is.

    Returns:
        The result and the stubs, which recorded what they were asked.
    """
    geometry, opti, avl = StubGeometry(), StubOpti(), StubAvl(FAKE_X_NP_AVL)
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: FAKE_DENSITY}), opti=opti, avl=avl, geometry=geometry
    )
    own = fleet_values(member) if flaps else {"aircraft-mass": member.mass_kg}
    aircraft = AircraftInput.model_validate(
        {
            "airplane": document if document is not None else reference_document(member),
            "values": {**own, **CHAIN_VALUES, **(values or {})},
        }
    )
    result = await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=slugs), solvers=solvers
    )
    return FleetChainRun(result, geometry, opti, avl)
