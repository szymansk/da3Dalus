"""horizontal-tail-volume: V_H = S_H l_H,CG / (S_ref c_MAC), one value per neutral-point world (fast tier)."""

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.horizontal_tail_volume import horizontal_tail_volume
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.schema import QuantityStatus
from aero_kernel.tests.chain_builders import C_MAC, SM_TARGET, WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, close, context_with
from aero_kernel.tests.np_builders import surface
from aero_kernel.tests.test_tail_arms import X_TAIL_QC

pytestmark = pytest.mark.asyncio

# The fixture tail (np_builders.TAIL): chord 0.1 m over a half span of 0.2 m, mirrored: S_H = 0.04 m^2.
# The fixture main wing: S_ref = 0.28 m^2, c_MAC = 0.2 m.
S_TAIL = 0.1 * 2.0 * 0.2
S_REF = 0.28


async def test_the_volume_is_the_tail_area_times_the_arm_over_wing_area_and_chord_per_world() -> (
    None
):
    quantity = (await run_chain("horizontal-tail-volume")).quantity("horizontal-tail-volume")
    assert quantity.status is QuantityStatus.OK
    assert quantity.unit == "1"
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    for world, x_np in WORLD_X_NP.items():
        arm = X_TAIL_QC - (x_np - SM_TARGET * C_MAC)
        assert close(quantity.interval.worlds[world], S_TAIL * arm / (S_REF * C_MAC), 1e-9), world
    assert close(quantity.interval.min, min(quantity.interval.worlds.values()), 1e-12)
    assert close(quantity.interval.max, max(quantity.interval.worlds.values()), 1e-12)


async def test_the_tail_area_is_asked_of_the_geometry_adapter_for_the_one_horizontal_surface() -> (
    None
):
    run = await run_chain("horizontal-tail-volume")
    assert set(run.geometry.horizontal_tail_keys) == {"htail"}


async def test_s_ref_and_c_mac_are_the_reference_values_of_the_main_wing_not_recomputed() -> None:
    """ADR 0022: the quantities of airplane-geometry, whatever the main wing's sections say."""
    custom = MainWingProperties(s_ref=0.5, b_ref=2.0, c_mac=0.25)
    run = await run_chain("horizontal-tail-volume", reference=custom)
    quantity = run.quantity("horizontal-tail-volume")
    assert quantity.interval is not None
    # the design CG is x_NP - SM_target c_MAC of the same reference chord, so the arm moves with it
    arm = X_TAIL_QC - (WORLD_X_NP["neutral-point=avl"] - SM_TARGET * 0.25)
    assert close(quantity.interval.worlds["neutral-point=avl"], S_TAIL * arm / (0.5 * 0.25), 1e-9)


async def test_without_a_horizontal_tail_the_volume_does_not_apply() -> None:
    wings = {"main": surface("main", "main_wing", 0.7, 0.2, 0.05)}
    tailless = AirplaneGeometry.model_validate({"name": "flat", "wings": wings})
    quantity = (await run_chain("horizontal-tail-volume", airplane=tailless)).quantity(
        "horizontal-tail-volume"
    )
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.interval is None


@pytest.mark.parametrize(
    ("surface_types", "tail"),
    [(("horizontal_tail",), True), (("v_tail",), True)],
    ids=["two-horizontal-tails", "v-tail-and-horizontal-tail"],
)
async def test_the_volume_needs_exactly_one_horizontal_surface(
    surface_types: tuple[str, ...], tail: bool
) -> None:
    """A V-tail is the horizontal surface (#1208); a second pitch surface beside it or beside a tail is refused."""
    extra = [
        {**fin(kind, f"extra-{index}"), "symmetric": True}
        for index, kind in enumerate(surface_types)
    ]
    airplane: AirplaneGeometry = document(*extra, tail=tail)
    context = context_with(StubAtmosphere({}), geometry=StubGeometry())
    inputs = {"airplane": airplane, "s_ref": S_REF, "c_mac": C_MAC, "l_h_cg": 0.4}
    with pytest.raises(FormulaError) as raised:
        await horizontal_tail_volume(inputs, context)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "unsupported_layout"
