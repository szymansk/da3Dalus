"""The AVL hinge moments against the real AVL binary (aero tier).

The checks are internal and independent of the implementation's own bookkeeping: the sign, the
linearity in the deflection, the scaling with the dynamic pressure, the antisymmetry of an aileron
pair, the vanishing of the moment at zero deflection and zero lift, a hand-written AVL file with
one duplicated flap control against the explicit halves, and thin-airfoil theory for a flap on a
wing of high aspect ratio. No published hinge moment of an RC aircraft exists to compare with.
"""

import math

import numpy as np
import pytest
from aero_kernel.devices import with_flaps_at
from aero_kernel.geometry import Airfoil, AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import main_wing_properties
from aero_kernel.solvers.avl import (
    CORE_RATIO,
    N_CHORD,
    N_SPAN,
    SPLIT_N_CHORD,
    AvlAdapter,
    AvlHinge,
)
from aero_kernel.solvers.avl_mesh import FLAP_CONTROL, split_at_hinge
from aero_kernel.solvers.avl_writer import (
    avl_hinge_commands,
    control_order,
    parse_hinge_output,
)
from aero_kernel.tests.hinge_builders import conventional, device, wing_document
from aero_kernel.tests.mesh_helpers import mesh_surfaces

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

AIR = AirState(density=1.225, dynamic_viscosity=1.81e-5, speed_of_sound=340.0)


async def hinge(
    airplane: AirplaneGeometry,
    role: str,
    delta: float,
    *,
    cl: float = 0.0,
    speed: float = 20.0,
) -> AvlHinge:
    async with SolverRuntime(max_workers=1) as runtime:
        return await AvlAdapter(runtime).hinge_moments(
            airplane, cl=cl, role=role, delta_deg=delta, speed_ms=speed, air=AIR
        )


async def test_an_elevator_deflected_trailing_edge_down_has_a_restoring_negative_moment() -> None:
    """The aerodynamic moment on a trailing-edge-down surface pushes it back up: negative in the
    sense of the positive deflection (avl-advisor: C_hinge < 0 for a restoring load)."""
    found = await hinge(conventional(), "elevator", 5.0)
    assert found.moments["Tail.elevator_right"] < 0.0
    assert found.moments["Tail.elevator_left"] < 0.0


async def test_the_moment_vanishes_at_zero_deflection_and_zero_lift_for_a_symmetric_section() -> (
    None
):
    """AVL prints ``Chinge`` with four significant digits and solves alpha iteratively, so zero means
    three orders of magnitude below the moment of a 5 degree deflection."""
    found = await hinge(conventional(), "elevator", 0.0, cl=0.0)
    reference = await hinge(conventional(), "elevator", 5.0, cl=0.0)
    for key, value in found.moments.items():
        assert abs(value) < 1e-3 * abs(reference.moments[key])


async def test_the_two_halves_of_an_elevator_carry_the_same_moment() -> None:
    found = await hinge(conventional(), "elevator", 5.0)
    assert math.isclose(
        found.moments["Tail.elevator_right"], found.moments["Tail.elevator_left"], rel_tol=3e-3
    )


async def test_an_aileron_pair_is_antisymmetric_at_zero_lift() -> None:
    """Right trailing edge up, left down: the moments in the trailing-edge-down sense are equal
    and opposite on the two halves of a symmetric wing at zero lift."""
    found = await hinge(conventional(), "aileron", 5.0)
    right, left = found.moments["Main wing.aileron_right"], found.moments["Main wing.aileron_left"]
    assert left < 0.0 < right
    assert math.isclose(right, -left, rel_tol=3e-3)


async def test_the_moment_is_linear_in_the_deflection() -> None:
    half, full = (
        await hinge(conventional(), "elevator", 5.0),
        await hinge(conventional(), "elevator", 10.0),
    )
    for key, value in full.moments.items():
        assert math.isclose(value, 2.0 * half.moments[key], rel_tol=3e-3)


async def test_a_deflected_surface_changes_the_hinge_moment_at_the_same_lift() -> None:
    """The deflection reaches AVL (issue 585 concerns the app, not the kernel): the elevator at 0
    and at 8 degrees differ, at a lift coefficient that gives both a non-zero moment."""
    plane = conventional()
    rest, deflected = (
        await hinge(plane, "elevator", 0.0, cl=0.5),
        await hinge(plane, "elevator", 8.0, cl=0.5),
    )
    key = "Tail.elevator_right"
    assert abs(deflected.moments[key] - rest.moments[key]) > 0.05 * abs(deflected.moments[key])


async def test_the_moment_scales_with_the_dynamic_pressure() -> None:
    slow, fast = (
        await hinge(conventional(), "elevator", 5.0, speed=10.0),
        await hinge(conventional(), "elevator", 5.0, speed=30.0),
    )
    for key, value in fast.moments.items():
        assert math.isclose(value, 9.0 * slow.moments[key], rel_tol=1e-6)


async def test_a_rudder_on_an_unmirrored_fin_has_its_own_key_and_a_value() -> None:
    found = await hinge(conventional(), "rudder", 5.0)
    assert set(found.moments) == {"Fin.rudder"}
    assert found.moments["Fin.rudder"] != 0.0


async def test_the_explicit_halves_sum_to_the_duplicated_control_of_a_hand_written_file() -> None:
    """One flap control on a YDUPLICATE wing sums both sides (``HM`` of the roll's mesh, written by
    the existing writer): the two explicit halves of the hinge-moment mesh add up to it."""
    delta, cl = 6.0, 0.4
    plane = conventional(main={0: device("flap", "flap", 0.7)})
    explicit = await hinge(plane, "flap", delta, cl=cl)
    numbers: dict[Airfoil, int] = {}

    def number(airfoil: Airfoil) -> int:
        return numbers.setdefault(airfoil, len(numbers))

    main, *others = mesh_surfaces(with_flaps_at(plane, delta), N_SPAN, number, drive_flaps=True)
    surfaces = (*split_at_hinge(main, SPLIT_N_CHORD), *others)
    reference = main_wing_properties(plane)
    async with SolverRuntime(max_workers=1) as runtime:
        adapter = AvlAdapter(runtime)
        contours = await adapter._contours(tuple(numbers))  # pyright: ignore[reportPrivateUsage]
        order = control_order(surfaces)
        stdout = await adapter._execute(  # pyright: ignore[reportPrivateUsage]
            surfaces,
            contours,
            (N_CHORD, N_SPAN),
            avl_hinge_commands(cl, CORE_RATIO, {FLAP_CONTROL: delta}, order=order),
            reference,
            plane.xyz_ref,
        )
    output = parse_hinge_output(stdout, order)
    assert output is not None
    scale = 0.5 * AIR.density * 20.0**2 * reference.s_ref * reference.c_mac
    assert math.isclose(
        sum(explicit.moments.values()), scale * output.moments[FLAP_CONTROL], rel_tol=0.02
    )


def thin_airfoil_flap_coefficient(flap_chord_ratio: float) -> float:
    """``C_h,delta`` per radian of a plain flap, from thin-airfoil theory, referred to ``c^2``.

    Glauert's loading of a flat plate with a flap of ``E = c_f / c`` deflected trailing edge down
    by ``delta``: with ``x = c/2 (1 - cos(theta))``, ``A_0 = delta (pi - theta_h) / pi`` and
    ``A_n = -(2 delta / (n pi)) (sin(n pi) - sin(n theta_h))``, the pressure difference is
    ``4 [A_0 (1 + cos theta) / sin theta + sum A_n sin(n theta)]`` times ``q``. The moment of the
    pressure on the flap about the hinge, positive trailing edge down, is
    ``-q int_{x_h}^{c} Delta C_p (x - x_h) dx``; the coefficient is that over ``q c^2``.
    """
    theta_h = math.acos(1.0 - 2.0 * (1.0 - flap_chord_ratio))
    theta = np.linspace(theta_h, math.pi, 20001)[1:-1]
    a0 = (math.pi - theta_h) / math.pi
    loading = a0 * (1.0 + np.cos(theta)) / np.sin(theta)
    for n in range(1, 60):
        a_n = -2.0 / (n * math.pi) * (math.sin(n * math.pi) - math.sin(n * theta_h))
        loading = loading + a_n * np.sin(n * theta)
    delta_cp = 4.0 * loading
    x = 0.5 * (1.0 - np.cos(theta))
    x_hinge = 0.5 * (1.0 - math.cos(theta_h))
    integrand = delta_cp * (x - x_hinge) * 0.5 * np.sin(theta)
    return -float(np.trapezoid(integrand, theta))


async def test_a_flap_on_a_wing_of_high_aspect_ratio_agrees_with_thin_airfoil_theory() -> None:
    """A full-span flap (E = 0.3) on a wing of aspect ratio 40 is nearly two-dimensional: AVL's
    C_hinge per degree must be thin-airfoil theory's within 15 % (the vortex lattice's chordwise
    resolution of the hinge singularity and the remaining finite-span effect)."""
    chord, half_span, hinge_at = 0.1, 2.0, 0.7
    wing = wing_document(
        "Main wing",
        "main_wing",
        [(0.0, 0.0, 0.0, chord), (0.0, half_span / 2, 0.0, chord), (0.0, half_span, 0.0, chord)],
        {0: device("flap", "flap", hinge_at), 1: device("flap", "flap", hinge_at)},
    )
    plane = AirplaneGeometry.model_validate({"name": "plank", "wings": {"Main": wing}})
    speed, delta = 20.0, 2.0
    found = await hinge(plane, "flap", delta, speed=speed)
    q = 0.5 * AIR.density * speed**2
    # both halves, per unit span: H_total = C_h2D * q * c^2 * b
    span = 2.0 * half_span
    measured = sum(found.moments.values()) / (q * chord**2 * span) / math.radians(delta)
    expected = thin_airfoil_flap_coefficient(1.0 - hinge_at)
    assert expected < 0.0
    assert math.isclose(measured, expected, rel_tol=0.15), (measured, expected)
