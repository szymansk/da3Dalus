"""The straight body axis AeroBuildup sees (#1358, canon rule ``fuselage-axis-straightened``).

AeroBuildup (AeroSandbox 4.2.9, ``aero_buildup.py`` 1104-1176) takes the axis of each fuselage
segment from the centres of its two sections. A vertical step of the centre between two close
sections becomes a steeply inclined segment, and that segment gets Jorgensen crossflow drag even at
an angle of attack of 0 (measured: CHEKKER +0.0100 in C_D, SNACK +0.0098, BRYAN +0.0051).

For AeroBuildup only, every body's section centres are therefore placed in height on one straight
axis: ``z`` of each centre becomes the unweighted least-squares line ``z(x)`` through all centres
``(x, z)`` of that body (maintainer decision 2026-11-07, #1358). ``x``, ``y``, ``a``, ``b``, ``n``,
``n_lower`` and the measured ``contour`` stay, so the cross-sections, the wetted area and the volume
are unchanged; a real curvature of the axis (an upswept boom) is lost.

It applies to the bodies after the canopy merge (:func:`~aero_kernel.solver_bodies.merged_bodies`).
AVL keeps the true centres, and the stored document is never changed. :func:`aerobuildup_bodies`
is the one producer (ADR 0022): the AeroSandbox conversion and the validation's declarations read
it.
"""

import logging
from collections.abc import Iterable
from typing import NamedTuple

import numpy as np
from aero_kernel.config import config
from aero_kernel.geometry import AirplaneGeometry, Fuselage
from aero_kernel.solver_bodies import solver_bodies

logger = logging.getLogger(__name__)

__all__ = ["AeroBuildupBodies", "AxisStraightening", "aerobuildup_bodies", "straight_axis"]


class AxisStraightening(NamedTuple):
    """What straightening one body's axis did; the content of its declaration.

    Attributes:
        fuselage: Name of the body (a parent of canopies as its merged body).
        sections: Number of its sections.
        largest_shift: Largest ``|z_line - z|`` over its section centres, m.
        section_index: Index of the section with the largest shift, in the body handed to the
            solvers (a merged body counts its inserted stations).
        x: ``x`` of that section, m.
    """

    fuselage: str
    sections: int
    largest_shift: float
    section_index: int
    x: float


class AeroBuildupBodies(NamedTuple):
    """The bodies AeroBuildup sees and what straightening their axes did.

    Attributes:
        bodies: The solver bodies in document order, each on its straight axis.
        straightenings: One entry per changed body, in document order.
    """

    bodies: tuple[Fuselage, ...]
    straightenings: tuple[AxisStraightening, ...]


def straight_axis(body: Fuselage, tolerance: float) -> tuple[Fuselage, AxisStraightening | None]:
    """Place a body's section centres in z on the least-squares line through all of them.

    Args:
        body: One body as the solvers see it.
        tolerance: Largest shift, m, up to which the centres count as on a line already
            (``opt_body_axis_tolerance``).

    Returns:
        The body on its straight axis and what was done; the body itself and ``None`` if it has
        fewer than two sections, all sections at one x, or every centre within ``tolerance`` of
        the line.
    """
    if len(body.x_secs) < 2:
        return body, None
    x = np.array([float(s.xyz[0]) for s in body.x_secs])
    z = np.array([float(s.xyz[2]) for s in body.x_secs])
    dx = x - x.mean()
    spread = float(dx @ dx)
    if spread == 0.0:  # no line in x; validation refuses such a body before it gets here
        return body, None
    slope = float(dx @ (z - z.mean())) / spread
    line = z.mean() + slope * dx
    shifts = np.abs(line - z)
    index = int(np.argmax(shifts))
    largest = float(shifts[index])
    if largest <= tolerance:
        return body, None
    sections = tuple(
        s.model_copy(update={"xyz": (s.xyz[0], s.xyz[1], float(z_line))})
        for s, z_line in zip(body.x_secs, line, strict=True)
    )
    straightening = AxisStraightening(
        fuselage=body.name,
        sections=len(sections),
        largest_shift=largest,
        section_index=index,
        x=float(x[index]),
    )
    return body.model_copy(update={"x_secs": sections}), straightening


def _straightened(bodies: Iterable[Fuselage], tolerance: float) -> AeroBuildupBodies:
    found: list[Fuselage] = []
    straightenings: list[AxisStraightening] = []
    for body in bodies:
        if body.symmetric:  # AeroSandbox has no mirrored body; the conversion refuses it
            found.append(body)
            continue
        straight, straightening = straight_axis(body, tolerance)
        found.append(straight)
        if straightening is not None:
            straightenings.append(straightening)
    return AeroBuildupBodies(tuple(found), tuple(straightenings))


def aerobuildup_bodies(airplane: AirplaneGeometry) -> AeroBuildupBodies:
    """The bodies AeroBuildup sees: the solver bodies, each on its straight axis (#1358).

    Args:
        airplane: The validated geometry document.

    Returns:
        The solver bodies (:func:`~aero_kernel.solver_bodies.solver_bodies`) in document order,
        each straightened, and one :class:`AxisStraightening` per changed body. The kernel
        configuration is read only when some centre lies off its line at all, so an airplane of
        straight bodies needs none, as the canopy merge needs none without canopies.
    """
    bodies = solver_bodies(airplane)
    exact = _straightened(bodies, 0.0)
    if not exact.straightenings:  # every axis exactly straight: no tolerance to read
        return exact
    result = _straightened(bodies, config().opt_body_axis_tolerance.value)
    for found in result.straightenings:
        logger.debug(
            "straightened the axis of %s: largest shift %.6g m at section %d (x = %.6g m)",
            found.fuselage,
            found.largest_shift,
            found.section_index,
            found.x,
        )
    return result
