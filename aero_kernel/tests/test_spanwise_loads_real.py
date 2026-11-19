"""spanwise-loads against the real AVL binary and an independent second method (aero tier).

The independent method is AeroSandbox's vortex lattice at the same total lift coefficient: the half
wing's normal force and its moment about the root from the panel forces. The two meshes and
formulations are different, so agreement is a check of the reading (Y, normalisation, integration
direction), not of the tool.
"""

import asyncio
import importlib
import math
from typing import Any

import pytest
from aero_kernel.context import Context
from aero_kernel.formulas.spanwise_loads import spanwise_loads
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import Curve
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.formula_builders import solvers_with
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_solvers_opti_roll_real import aileron_trainer

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

MASS, GRAVITY, RHO, SPEED = 1.5, 9.80665, 1.225, 12.0
Q = 0.5 * RHO * SPEED**2


def trapezoid(y: tuple[float, ...], x: tuple[float, ...]) -> float:
    return float(sum((x[i + 1] - x[i]) * (y[i + 1] + y[i]) / 2.0 for i in range(len(x) - 1)))


async def loads(airplane: AirplaneGeometry, n_load: float) -> dict[str, Curve]:
    async with SolverRuntime(max_workers=1) as runtime:
        ctx = Context(
            origin="t",
            solvers=solvers_with(avl=AvlAdapter(runtime), geometry=GeometryAdapter(runtime)),
        )
        return dict(
            await spanwise_loads(
                {
                    "airplane": airplane,
                    "m": MASS,
                    "g": GRAVITY,
                    "n_load": n_load,
                    "rho": RHO,
                    "v": SPEED,
                },
                ctx,
            )
        )


async def test_the_load_of_the_half_wing_is_half_the_weight_and_the_curves_agree_with_each_other() -> (
    None
):
    """A wing alone carries n m g: V(root) = n m g / 2; l integrates to V; l y integrates to M."""
    out = await loads(aileron_trainer(), 1.0)
    l_y, v_y, m_y = out["l_y"], out["v_y"], out["m_y"]
    assert math.isclose(v_y.y[0], MASS * GRAVITY / 2.0, rel_tol=0.01)
    assert v_y.y[-1] == 0.0
    assert m_y.y[-1] == 0.0
    strips_lift = trapezoid(l_y.y, l_y.x) + l_y.y[0] * l_y.x[0]
    assert math.isclose(strips_lift, v_y.y[0], rel_tol=0.01)
    moment = trapezoid(tuple(a * b for a, b in zip(l_y.y, l_y.x, strict=True)), l_y.x)
    assert math.isclose(moment, m_y.y[0], rel_tol=0.02)
    assert all(a > b for a, b in zip(v_y.y, v_y.y[1:], strict=False))  # shear falls to the tip


def untwisted_wing(foil: str) -> AirplaneGeometry:
    """The 1.4 m span, 0.2 m chord test wing of the trainer, without a device, with a given section."""
    sections = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": foil}
        for y in (0.0, 0.4, 0.7)
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate(
        {"name": "wing", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Main": wing}}
    )


async def test_a_downward_load_mirrors_the_upward_one_on_a_symmetric_section() -> None:
    """Measured 0.043310 (m^3) per unit C_L at C_L = +0.7 and -0.7: identical."""
    wing = untwisted_wing("naca0012")
    up, down = await asyncio.gather(loads(wing, 1.0), loads(wing, -1.0))
    assert math.isclose(down["m_y"].y[0], -up["m_y"].y[0], rel_tol=1e-3)
    assert math.isclose(down["l_y"].y[5], -up["l_y"].y[5], rel_tol=1e-3)


async def test_the_load_scales_with_the_load_factor_only_approximately_as_the_entry_declares() -> (
    None
):
    """The spanload shape of AVL changes with the angle of attack: on this wing the root moment per
    unit C_L falls by 3.6 % from C_L 0.60 (n = 1) to 1.79 (n = 3) (a symmetric section: 6.5 % from
    0.7 to 2.1). The entry declares linear scaling an approximation; this pins its size here. C_L 1.8
    is beyond a real section's C_L,max and only shows the trend."""
    one, three = await asyncio.gather(loads(aileron_trainer(), 1.0), loads(aileron_trainer(), 3.0))
    ratio = three["m_y"].y[0] / (3.0 * one["m_y"].y[0])
    assert 0.93 < ratio < 0.97


def vlm_half_wing(airplane: AirplaneGeometry, cl_total: float) -> tuple[float, float]:
    """ASB's vortex lattice at the angle of attack that gives ``cl_total``: the half wing's normal
    force and its moment about the root, per dynamic pressure."""
    asb: Any = importlib.import_module("aerosandbox")
    np: Any = importlib.import_module("numpy")
    asb_airplane = to_asb_airplane(airplane)

    def run(alpha: float) -> tuple[Any, float]:
        vlm: Any = asb.VortexLatticeMethod(
            airplane=asb_airplane,
            op_point=asb.OperatingPoint(velocity=SPEED, alpha=alpha),
            spanwise_resolution=12,
            chordwise_resolution=8,
        )
        return vlm, float(vlm.run()["CL"])

    (_, c0), (_, c1) = run(2.0), run(6.0)
    vlm, _ = run(2.0 + (cl_total - c0) * 4.0 / (c1 - c0))
    main = next(w for w in (airplane.wings or {}).values() if w.surface_type == "main_wing")
    x_lo = min(s.xyz_le[0] for s in main.x_secs)
    x_hi = max(s.xyz_le[0] + s.chord for s in main.x_secs)
    centres, forces = np.array(vlm.vortex_centers), np.array(vlm.forces_geometry)
    on_half = (centres[:, 1] > 0) & (centres[:, 0] >= x_lo - 1e-6) & (centres[:, 0] <= x_hi + 1e-6)
    z = forces[on_half, 2]
    return float(z.sum() / Q), float((z * centres[on_half, 1]).sum() / Q)


# Measured on the real binaries (CL 0.7): AVL against ASB VLM, root shear / root moment:
# trainer -0.1 % / -1.1 %, ULTRA_STICK_120 +1.1 % / +0.2 %, AVISTAR_ELITE -1.8 % / -4.1 %.
# The tolerances are twice the largest measured deviation, fixed after the measurement.
@pytest.mark.parametrize(
    ("member", "shear_tol", "moment_tol"),
    [
        (None, 0.02, 0.03),
        (FleetMember.ULTRA_STICK_120, 0.025, 0.02),
        (FleetMember.AVISTAR_ELITE, 0.04, 0.09),
    ],
)
async def test_the_root_shear_and_moment_agree_with_the_independent_vortex_lattice(
    member: FleetMember | None, shear_tol: float, moment_tol: float
) -> None:
    airplane = (
        aileron_trainer()
        if member is None
        else AirplaneGeometry.model_validate(reference_document(member))
    )
    async with SolverRuntime(max_workers=1) as runtime:
        found = await AvlAdapter(runtime).spanwise_loads(airplane, 0.7)
    shear, moment = vlm_half_wing(airplane, 0.7)
    assert math.isclose(found.shear[0], shear, rel_tol=shear_tol)
    assert math.isclose(found.moment[0], moment, rel_tol=moment_tol)


def elliptic_wing(semi_span: float, root_chord: float, foil: str) -> AirplaneGeometry:
    """An untwisted wing of elliptic planform, ``c(y) = c_0 sqrt(1 - (y / s)^2)``, on 13 sections.

    The quarter-chord line is straight. The last section is at 0.99 of the semi-span (the chord is
    0.14 c_0 there, not zero).
    """
    stations = [k / 12.0 * 0.99 for k in range(13)]
    sections = [
        {
            "xyz_le": [0.25 * root_chord * (1.0 - math.sqrt(1.0 - t * t)), t * semi_span, 0.0],
            "chord": root_chord * math.sqrt(1.0 - t * t),
            "twist": 0.0,
            "airfoil": foil,
        }
        for t in stations
    ]
    wing = {"name": "Main", "surface_type": "main_wing", "x_secs": sections}
    return AirplaneGeometry.model_validate(
        {"name": "elliptic", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Main": wing}}
    )


async def test_the_elliptic_wing_has_the_closed_form_root_load() -> None:
    """Closed form of an elliptic distribution (Anderson 5.3.1; Scholz Wing Design 7.3):
    l(y) = 4 L / (pi b) sqrt(1 - (2y/b)^2), so V(0) = L / 2 and M(0) = L b / (3 pi), with
    L = n m g and b the span. The planform is elliptic and untwisted, so the lifting-line loading is
    elliptic; AVL is a vortex lattice, so the two agree to the stated tolerance only. Measured on
    this wing (AVL against the closed form): root shear -0.7 %, root moment -2.2 %, peak lift per
    metre +1.0 %; the tolerances are twice the largest measured deviation, rounded up."""
    semi_span, chord = 0.7, 0.25
    out = await loads(elliptic_wing(semi_span, chord, "naca0012"), 1.0)
    lift = MASS * GRAVITY
    span = 2.0 * semi_span
    assert math.isclose(out["v_y"].y[0], lift / 2.0, rel_tol=0.02)
    assert math.isclose(out["m_y"].y[0], lift * span / (3.0 * math.pi), rel_tol=0.045)
    peak = 4.0 * lift / (math.pi * span)
    assert math.isclose(out["l_y"].y[0], peak, rel_tol=0.02)


async def test_the_main_wing_is_read_whatever_its_place_in_the_document() -> None:
    """The loads are the main wing's, chosen by surface type: a tail listed before the main wing
    changes nothing for the loads of the main wing (same C_L for the airplane, same mesh order)."""
    wing = untwisted_wing("naca0012")
    tail_sections = [
        {"xyz_le": [0.7, y, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
        for y in (0.0, 0.25)
    ]
    tail = {"name": "Tail", "surface_type": "horizontal_tail", "x_secs": tail_sections}
    main = (wing.wings or {})["Main"].model_dump(mode="json")
    first = AirplaneGeometry.model_validate(
        {"name": "a", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Main": main, "Tail": tail}}
    )
    second = AirplaneGeometry.model_validate(
        {"name": "b", "xyz_ref": [0.05, 0.0, 0.0], "wings": {"Tail": tail, "Main": main}}
    )
    one, two = await asyncio.gather(loads(first, 1.0), loads(second, 1.0))
    assert one["m_y"].x[-1] == two["m_y"].x[-1] == 0.7  # the main wing's semi-span, not the tail's
    assert math.isclose(one["m_y"].y[0], two["m_y"].y[0], rel_tol=1e-9)
