"""Builders for the MVP-chain tests (vertical tail volume, spiral parameter, probe, lateral stability)."""

from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.schema import AircraftInput, ComputeRequest, ComputeResult, QuantityResult
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, solvers_with
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_neutral_point import MASS, RHO, X_NP_AVL
from aero_kernel.tests.test_tail_arms import WORLD_X_NP, document, fin

SM_TARGET = 0.08
C_MAC = 0.2
__all__ = ["C_MAC", "SM_TARGET", "WORLD_X_NP", "ChainRun", "document", "fin", "run_chain"]


class ChainRun:
    """The result of one engine run and the stubs that answered it."""

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


async def run_chain(
    *slugs: str,
    airplane: AirplaneGeometry | None = None,
    target: float | None = SM_TARGET,
    reference: MainWingProperties | None = None,
    opti: StubOpti | None = None,
    avl: StubAvl | None = None,
) -> ChainRun:
    """Evaluate quantities of the chain on the shipped canon with stub adapters (three NP worlds)."""
    geometry = StubGeometry(reference=reference)
    stub_opti, stub_avl = opti or StubOpti(), avl or StubAvl(X_NP_AVL)
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}), opti=stub_opti, avl=stub_avl, geometry=geometry
    )
    values: dict[str, float] = {"aircraft-mass": MASS, "altitude": 0.0}
    if target is not None:
        values["static-margin-target"] = target
    aircraft = AircraftInput.model_validate(
        {"airplane": airplane or document(fin()), "values": values}
    )
    result = await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=slugs), solvers=solvers
    )
    return ChainRun(result, geometry, stub_opti, stub_avl)
