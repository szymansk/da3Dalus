"""horizontal-tail-arm and vertical-tail-arm: l_H,CG and l_V,CG from the design CG, per method world (gh-1272)."""

from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.horizontal_tail_arm import horizontal_tail_arm
from aero_kernel.formulas.vertical_tail_arm import vertical_tail_arm
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeRequest, ComputeResult, QuantityStatus
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    StubGeometry,
    close,
    context_with,
    solvers_with,
)
from aero_kernel.tests.np_builders import StubAvl, surface
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_neutral_point import (
    C_MAC,
    MASS,
    RHO,
    X_NP_AVL,
    X_NP_PAPPAS,
    X_NP_TEXTBOOK,
    only,
)

SM_TARGET = 0.08
# The fixture tail (np_builders.TAIL): chord 0.1 m at x = 0.60 m, so its quarter-chord MAC is at 0.625 m.
X_TAIL_QC = 0.625
# A tapered, swept, unmirrored fin from z = 0 to 0.15 m at y = 0: chord 0.12 -> 0.06 m, leading edge
# x 0.62 -> 0.66 m. One panel, taper ratio 1/2: the MAC leading edge sits at
# 0.62 + 0.04 (1 + 2/2) / (3 + 3/2) = 0.6377778 m, c_MAC = (2/3) 0.12 (1 + 1/2 + 1/4) / (1 + 1/2) =
# 0.0933333 m, so the quarter-chord MAC is at 0.6377778 + 0.0233333 = 0.6611111 m.
X_FIN_QC = 0.62 + 0.04 * (2.0 / 4.5) + 0.25 * (2.0 / 3.0) * 0.12 * (1.75 / 1.5)
WORLD_X_NP = {
    "neutral-point=textbook": X_NP_TEXTBOOK,
    "neutral-point=pappas": X_NP_PAPPAS,
    "neutral-point=avl": X_NP_AVL,
}


def fin(surface_type: str = "vertical_tail", name: str = "fin") -> dict[str, Any]:
    """The unmirrored, tapered, swept fin of the hand value."""
    sections = [
        {"xyz_le": [0.62, 0.0, 0.0], "chord": 0.12, "twist": 0.0, "airfoil": "naca0012"},
        {"xyz_le": [0.66, 0.0, 0.15], "chord": 0.06, "twist": 0.0, "airfoil": "naca0012"},
    ]
    return {"name": name, "symmetric": False, "surface_type": surface_type, "x_secs": sections}


def document(*extra: dict[str, Any], tail: bool = True) -> AirplaneGeometry:
    """Main wing, optionally the fixture horizontal tail, and the given extra surfaces."""
    wings: dict[str, Any] = {"main": surface("main", "main_wing", 0.7, 0.2, 0.05)}
    if tail:
        wings["htail"] = surface("htail", "horizontal_tail", 0.2, 0.1, 0.60)
    for wing in extra:
        wings[wing["name"]] = wing
    return AirplaneGeometry.model_validate({"name": "arms", "wings": wings})


async def run(
    *slugs: str, airplane: AirplaneGeometry, target: float | None = SM_TARGET
) -> ComputeResult:
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}),
        opti=StubOpti(),
        avl=StubAvl(X_NP_AVL),
        geometry=StubGeometry(),
    )
    values: dict[str, float] = {"aircraft-mass": MASS, "altitude": 0.0}
    if target is not None:
        values["static-margin-target"] = target
    aircraft = AircraftInput.model_validate({"airplane": airplane, "values": values})
    return await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=slugs), solvers=solvers
    )


@pytest.mark.asyncio
async def test_the_horizontal_arm_is_the_tail_quarter_chord_less_the_design_cg_per_world() -> None:
    quantity = only(await run("horizontal-tail-arm", airplane=document(fin())))
    assert quantity.status is QuantityStatus.OK
    assert quantity.unit == "m"
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    for world, x_np in WORLD_X_NP.items():
        x_cg = x_np - SM_TARGET * C_MAC
        assert close(quantity.interval.worlds[world], X_TAIL_QC - x_cg, 1e-12), world
    assert quantity.interval.min == min(quantity.interval.worlds.values())
    assert quantity.interval.max == max(quantity.interval.worlds.values())


@pytest.mark.asyncio
async def test_the_vertical_arm_is_the_fin_quarter_chord_less_the_design_cg_per_world() -> None:
    quantity = only(await run("vertical-tail-arm", airplane=document(fin())))
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    for world, x_np in WORLD_X_NP.items():
        x_cg = x_np - SM_TARGET * C_MAC
        assert close(quantity.interval.worlds[world], X_FIN_QC - x_cg, 1e-9), world


@pytest.mark.asyncio
async def test_a_v_tail_is_the_vertical_surface_of_the_arm() -> None:
    """The arm is to the V-tail's own quarter-chord MAC (ASB's); what a V-tail counts as is #1208.

    The neutral point refuses a V-tail layout (#1208), so the formula is called with the CG given.
    """
    airplane = document(fin("v_tail", "vee"), tail=False)
    arm = await vertical_tail_arm(
        {"airplane": airplane, "x_cg": 0.15}, context_with(StubAtmosphere({}))
    )
    assert close(arm["l_v_cg"], X_FIN_QC - 0.15, 1e-9)


@pytest.mark.asyncio
async def test_the_arm_moves_with_the_target_margin_because_the_cg_does() -> None:
    near = only(await run("horizontal-tail-arm", airplane=document(fin()), target=0.05))
    far = only(await run("horizontal-tail-arm", airplane=document(fin()), target=0.15))
    assert near.interval is not None
    assert far.interval is not None
    # A larger margin puts the CG further forward, so the arm grows by dSM * c_MAC.
    for world in WORLD_X_NP:
        assert close(far.interval.worlds[world] - near.interval.worlds[world], 0.10 * C_MAC, 1e-9)


@pytest.mark.asyncio
async def test_a_missing_target_takes_the_starting_value_and_declares_it() -> None:
    result = await run("horizontal-tail-arm", airplane=document(fin()), target=None)
    used = {d.slug: d for d in result.provenance.defaults_used}
    assert used["static-margin-target"].value == 0.10
    quantity = only(result)
    assert quantity.interval is not None
    assert close(
        quantity.interval.worlds["neutral-point=avl"],
        X_TAIL_QC - (X_NP_AVL - 0.10 * C_MAC),
        1e-12,
    )


@pytest.mark.asyncio
async def test_the_missing_fuselage_is_inherited_in_every_world() -> None:
    quantity = only(await run("vertical-tail-arm", airplane=document(fin())))
    fuselage = [w for w in quantity.warnings if w.code == "fuselage_not_modelled"]
    assert len(fuselage) == len(WORLD_X_NP)


@pytest.mark.asyncio
async def test_without_a_vertical_tail_the_vertical_arm_does_not_apply() -> None:
    quantity = only(await run("vertical-tail-arm", airplane=document()))
    assert quantity.status is not QuantityStatus.OK
    assert quantity.interval is None


@pytest.mark.asyncio
async def test_a_vertical_arm_needs_exactly_one_vertical_surface() -> None:
    twin = document(fin(name="fin-a"), fin(name="fin-b"))
    quantity = only(await run("vertical-tail-arm", airplane=twin))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert (quantity.error.category, quantity.error.code) == (
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_layout",
    )
    assert quantity.error.detail["surface_types"] == [
        "horizontal_tail",
        "main_wing",
        "vertical_tail",
        "vertical_tail",
    ]


@pytest.mark.asyncio
async def test_a_vertical_arm_does_not_take_a_fin_typed_as_a_winglet() -> None:
    """A fin-shaped surface typed winglet makes has_vertical_tail hold, but it is no tail arm."""
    quantity = only(await run("vertical-tail-arm", airplane=document(fin("winglet", "w"))))
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "unsupported_layout"


@pytest.mark.parametrize("tail", [False, True])
@pytest.mark.asyncio
async def test_a_horizontal_arm_needs_exactly_one_horizontal_tail(tail: bool) -> None:
    """None or two: the formula refuses by itself (the neutral point refuses first in the engine)."""
    airplane = document(fin(), tail=tail)
    if tail:
        wings = {k: w.model_dump() for k, w in (airplane.wings or {}).items()}
        wings["second"] = {**wings["htail"], "name": "second"}
        airplane = AirplaneGeometry.model_validate({"name": "two", "wings": wings})
    context = context_with(StubAtmosphere({}))
    with pytest.raises(FormulaError) as raised:
        await horizontal_tail_arm({"airplane": airplane, "x_cg": 0.1}, context)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "unsupported_layout"


@pytest.mark.asyncio
async def test_the_tail_position_is_asked_of_the_geometry_adapter_not_integrated() -> None:
    """ADR 0022: the quarter-chord MAC is ASB's (``Wing.aerodynamic_center``), via the GEO adapter."""

    class Recording(StubGeometry):
        def __init__(self) -> None:
            super().__init__()
            self.keys: list[str] = []

        async def quarter_chord_mac_x(self, airplane: AirplaneGeometry, key: str) -> float:
            self.keys.append(key)
            return 0.7

    geometry = Recording()
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}),
        opti=StubOpti(),
        avl=StubAvl(X_NP_AVL),
        geometry=geometry,
    )
    aircraft = AircraftInput.model_validate(
        {"airplane": document(fin()), "values": {"aircraft-mass": MASS, "altitude": 0.0}}
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        ComputeRequest(quantities=("horizontal-tail-arm",)),
        solvers=solvers,
    )
    quantity = only(result)
    assert quantity.interval is not None
    assert geometry.keys
    assert set(geometry.keys) == {"htail"}
    assert close(
        quantity.interval.worlds["neutral-point=avl"], 0.7 - (X_NP_AVL - 0.10 * C_MAC), 1e-12
    )


def test_the_vertical_tail_volume_and_spiral_parameter_are_bound_to_the_arm_from_the_cg() -> None:
    """l_V,25 is gone: the Drela quantities take the arm from the design CG (maintainer, 2026-10-25)."""
    model = shipped_build().model
    for slug in ("vertical-tail-volume", "spiral-parameter"):
        formula = model.formula(slug)
        assert formula is not None, slug
        bound = {str(q) for q in formula.application("with_vertical_tail").bind.values()}
        assert "vertical-tail-arm" in {b.split(":")[-1] for b in bound}, slug
