"""A V-tail is the horizontal tail of the neutral point and the tail volumes (maintainer 2026-10-27, #1208).

S_h,eff = sum S_i cos^2(nu_i), the lift slope from the true panel aspect ratio; the fin share is
sum S_i sin^2(nu_i). The solver boundary (AeroSandbox, AVL) is stubbed.
"""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.formulas.horizontal_tail_arm import horizontal_tail_arm
from aero_kernel.formulas.horizontal_tail_volume import horizontal_tail_volume
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import SurfaceProperties
from aero_kernel.schema import AircraftInput, ComputeRequest, QuantityStatus
from aero_kernel.tests.asb_fakes import stand_in_horizontal_tail_area, stand_in_v_tail_surface
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    StubGeometry,
    close,
    context_with,
    solvers_with,
)
from aero_kernel.tests.np_builders import StubAvl, airplane_with
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_neutral_point import (
    MASS,
    RHO,
    X_NP_AVL,
    X_NP_PAPPAS,
    X_NP_TEXTBOOK,
    only,
    run,
)

pytestmark = pytest.mark.asyncio

HALF_SPAN, CHORD = 0.2, 0.1
# A 45 degree V-tail panel (y, z) = (0, 0) -> (0.2, 0.2): the half panel is 0.2 sqrt(2) m long.
SLANT = HALF_SPAN * math.sqrt(2.0)


def tilted(rise: float) -> dict[str, Any]:
    """A mirrored one-panel V-tail rising ``rise`` m over a half span of 0.2 m, constant chord."""
    sections = [
        {"xyz_le": [0.60, y, z], "chord": CHORD, "twist": 0.0, "airfoil": "naca0012"}
        for y, z in ((0.0, 0.0), (HALF_SPAN, rise))
    ]
    return {"name": "vee", "symmetric": True, "surface_type": "v_tail", "x_secs": sections}


def v_tail_airplane(rise: float) -> AirplaneGeometry:
    """The fixture main wing and a V-tail with the given rise."""
    wings: dict[str, Any] = airplane_with("main_wing").model_dump(mode="json")["wings"]
    wings["vee"] = tilted(rise)
    return AirplaneGeometry.model_validate({"name": "vee", "wings": wings})


async def test_the_stand_in_v_tail_has_the_effective_area_and_the_true_panel_aspect_ratio() -> None:
    wing = (v_tail_airplane(HALF_SPAN).wings or {})["vee"]
    found = stand_in_v_tail_surface(wing)
    true_area = 2.0 * CHORD * SLANT
    assert close(found.area, 0.5 * true_area, 1e-12)  # cos^2 45 degrees
    assert close(found.span, 2.0 * SLANT, 1e-12)
    assert close(found.aspect_ratio, (2.0 * SLANT) ** 2 / true_area, 1e-12)  # not projected
    assert close(stand_in_horizontal_tail_area(wing), found.area, 1e-12)
    assert close(found.c_mac, CHORD, 1e-12)


async def test_a_flat_v_tail_is_exactly_a_horizontal_tail_in_every_world() -> None:
    """With nu = 0 the share is 1 and the aspect ratio the planform's: the numbers of the fixture tail."""
    result, avl = await run("neutral-point", airplane=airplane_with("main_wing", "v_tail"))
    quantity = only(result)
    assert quantity.status is QuantityStatus.OK
    assert quantity.interval is not None
    worlds = quantity.interval.worlds
    assert close(worlds["neutral-point=textbook"], X_NP_TEXTBOOK, 1e-12)
    assert close(worlds["neutral-point=pappas"], X_NP_PAPPAS, 1e-12)
    assert worlds["neutral-point=avl"] == X_NP_AVL
    assert len(avl.calls) == 1


async def test_a_tilted_v_tail_enters_the_barycentre_with_its_effective_area_and_true_aspect_ratio() -> (
    None
):
    airplane = v_tail_airplane(HALF_SPAN)
    main_key, tail_key = list(airplane.wings or {})
    geometry = StubGeometry()
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}), opti=StubOpti(), avl=StubAvl(), geometry=geometry
    )
    aircraft = AircraftInput.model_validate(
        {"airplane": airplane, "values": {"aircraft-mass": MASS, "altitude": 0.0}}
    )
    result = await evaluate(
        shipped_build(), aircraft, ComputeRequest(quantities=("neutral-point",)), solvers=solvers
    )
    worlds = only(result).interval.worlds  # type: ignore[union-attr]
    main = await geometry.surface_reference(airplane, main_key)
    tail = await geometry.surface_reference(airplane, tail_key)
    assert close(tail.area, 0.5 * 2.0 * CHORD * SLANT, 1e-12)
    weight = 1.0 - 3.24 / main.aspect_ratio
    weight *= (tail.aspect_ratio / (tail.aspect_ratio + 2.0)) / (
        main.aspect_ratio / (main.aspect_ratio + 2.0)
    )
    x_tail = tail.x_le_mac + 0.25 * tail.c_mac
    x_main = main.x_le_mac + 0.25 * main.c_mac
    expected = (main.area * x_main + weight * tail.area * x_tail) / (main.area + weight * tail.area)
    assert close(worlds["neutral-point=pappas"], expected, 1e-12)


async def test_the_v_tail_volume_uses_the_effective_area_and_the_arm_to_its_own_mac() -> None:
    airplane = v_tail_airplane(HALF_SPAN)
    geometry = StubGeometry()
    context = context_with(StubAtmosphere({}), geometry=geometry)
    inputs = {"airplane": airplane, "s_ref": 0.28, "c_mac": 0.2, "l_h_cg": 0.4}
    volume = await horizontal_tail_volume(inputs, context)
    assert close(volume["v_h"], 0.5 * 2.0 * CHORD * SLANT * 0.4 / (0.28 * 0.2), 1e-12)
    assert geometry.horizontal_tail_keys == ["vee"]


async def test_the_v_tail_is_the_horizontal_surface_of_the_arm() -> None:
    airplane = v_tail_airplane(HALF_SPAN)
    arm = await horizontal_tail_arm(
        {"airplane": airplane, "x_cg": 0.15}, context_with(StubAtmosphere({}))
    )
    assert close(arm["l_h_cg"], 0.60 + 0.25 * CHORD - 0.15, 1e-12)


async def test_the_surface_properties_given_to_the_stub_win_over_the_stand_in() -> None:
    airplane = v_tail_airplane(HALF_SPAN)
    given = SurfaceProperties(area=0.03, span=0.6, aspect_ratio=12.0, c_mac=0.1, x_le_mac=0.6)
    found = await StubGeometry(surfaces={"vee": given}).surface_reference(airplane, "vee")
    assert found == given
