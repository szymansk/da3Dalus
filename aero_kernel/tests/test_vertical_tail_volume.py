"""vertical-tail-volume: V_V = S_V l_V,CG / (S_ref b_ref), one value per neutral-point world (fast tier)."""

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.vertical_tail_volume import vertical_tail_volume
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.schema import QuantityStatus
from aero_kernel.tests.chain_builders import C_MAC, SM_TARGET, WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, close, context_with
from aero_kernel.tests.test_tail_arms import X_FIN_QC

pytestmark = pytest.mark.asyncio

# The fixture fin (test_tail_arms.fin): chord 0.12 -> 0.06 m over 0.15 m of height, one-sided:
# S_V = (0.12 + 0.06) / 2 * 0.15 = 0.0135 m^2. The fixture main wing: S_ref = 0.28 m^2, b_ref = 1.4 m.
S_FIN = (0.12 + 0.06) / 2.0 * 0.15
S_REF, B_REF = 0.28, 1.4


async def test_the_volume_is_the_fin_area_times_the_arm_over_wing_area_and_span_per_world() -> None:
    quantity = (await run_chain("vertical-tail-volume")).quantity("vertical-tail-volume")
    assert quantity.status is QuantityStatus.OK
    assert quantity.unit == "1"
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    for world, x_np in WORLD_X_NP.items():
        arm = X_FIN_QC - (x_np - SM_TARGET * C_MAC)
        assert close(quantity.interval.worlds[world], S_FIN * arm / (S_REF * B_REF), 1e-9), world
    assert quantity.interval.min == min(quantity.interval.worlds.values())


async def test_the_fin_area_is_asked_of_the_geometry_adapter_for_the_one_vertical_surface() -> None:
    run = await run_chain("vertical-tail-volume")
    assert set(run.geometry.fin_keys) == {"fin"}


async def test_s_ref_and_b_ref_are_the_reference_values_of_the_main_wing_not_recomputed() -> None:
    """ADR 0022: the quantities of airplane-geometry, whatever the main wing's sections say."""
    custom = MainWingProperties(s_ref=0.5, b_ref=2.0, c_mac=C_MAC)
    run = await run_chain("vertical-tail-volume", reference=custom)
    quantity = run.quantity("vertical-tail-volume")
    assert quantity.interval is not None
    arm = X_FIN_QC - (WORLD_X_NP["neutral-point=avl"] - SM_TARGET * C_MAC)
    assert close(quantity.interval.worlds["neutral-point=avl"], S_FIN * arm / (0.5 * 2.0), 1e-9)


async def test_a_v_tail_counts_its_fin_share_sin_squared_of_the_panel_angle() -> None:
    """A mirrored V-tail panel from (y, z) = (0.05, 0) to (0.25, 0.2): 45 deg, sin^2 = 1/2."""
    sections = [
        {"xyz_le": [0.62, 0.05, 0.0], "chord": 0.12, "twist": 0.0, "airfoil": "naca0012"},
        {"xyz_le": [0.66, 0.25, 0.2], "chord": 0.06, "twist": 0.0, "airfoil": "naca0012"},
    ]
    vee = {"name": "vee", "symmetric": True, "surface_type": "v_tail", "x_secs": sections}
    airplane = document(vee, tail=False)
    arm = 0.4
    context = context_with(StubAtmosphere({}), geometry=StubGeometry())
    found = await vertical_tail_volume(
        {"airplane": airplane, "s_ref": S_REF, "b_ref": B_REF, "l_v_cg": arm}, context
    )
    panel = (0.12 + 0.06) / 2.0 * (0.2**2 + 0.2**2) ** 0.5
    assert close(found["v_v"], 2.0 * panel * 0.5 * arm / (S_REF * B_REF), 1e-12)


async def test_without_a_vertical_tail_the_volume_does_not_apply() -> None:
    quantity = (await run_chain("vertical-tail-volume", airplane=document())).quantity(
        "vertical-tail-volume"
    )
    assert quantity.status is not QuantityStatus.OK
    assert quantity.interval is None


@pytest.mark.parametrize("surface_types", [("vertical_tail", "vertical_tail"), ("winglet",)])
async def test_the_volume_needs_exactly_one_vertical_surface(
    surface_types: tuple[str, ...],
) -> None:
    extra = [fin(kind, f"fin-{index}") for index, kind in enumerate(surface_types)]
    airplane: AirplaneGeometry = document(*extra)
    context = context_with(StubAtmosphere({}), geometry=StubGeometry())
    with pytest.raises(FormulaError) as raised:
        await vertical_tail_volume(
            {"airplane": airplane, "s_ref": S_REF, "b_ref": B_REF, "l_v_cg": 0.4}, context
        )
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "unsupported_layout"
