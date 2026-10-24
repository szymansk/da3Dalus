"""The oriented section chain of a lifting surface: the one place that decides which way a surface runs.

A geometry document may store a surface root first or tip first, and a mirrored surface on either
side of the plane. The planform values (:mod:`geometry_properties`) and the AVL mesh
(:mod:`solvers.avl_mesh`) both read the surface through :func:`oriented_chain`, so they cannot
disagree on it (ADR 0022).
"""

from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Airfoil, Wing
from pydantic import BaseModel, ConfigDict

__all__ = ["ChainDevice", "ChainPoint", "oriented_chain"]


class ChainDevice(BaseModel):
    """The control device of the segment that starts at a chain point, in oriented order.

    Attributes:
        name: The device's name.
        role: Its standardised role.
        hinge_start: Hinge position (fraction of chord) at the start of the oriented segment.
        hinge_end: Hinge position at the end of the oriented segment; the root hinge's where the
            format gives no tip hinge (ch. 6).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None
    role: str
    hinge_start: float | None
    hinge_end: float | None


class ChainPoint(BaseModel):
    """One section of an oriented chain.

    Attributes:
        x: x of the leading edge in m.
        y: y of the leading edge in m (mirrored to y >= 0 for a surface stored on the other side).
        z: z of the leading edge in m.
        chord: Chord in m.
        twist: Twist in degrees.
        airfoil: The section's airfoil.
        device: The device of the segment that starts here in oriented order, if any.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float
    y: float
    z: float
    chord: float
    twist: float
    airfoil: Airfoil
    device: ChainDevice | None = None


def _unsupported(wing: Wing, axis_name: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        f"the sections of the wing {wing.name!r} fold back in {axis_name}",
        f"order the sections from the root outwards without doubling back in {axis_name}",
        detail={"wing": wing.name},
        parameter="airplane",
    )


def oriented_chain(wing: Wing, axis: int) -> list[ChainPoint]:
    """The sections of a surface, root first, with the spreading coordinate never decreasing.

    ``axis`` 1 (y) is the spanwise coordinate of a wing or tail, 2 (z) that of a fin. The chain is
    reversed if it is stored tip first, and a mirrored surface stored on the negative side is
    mirrored to y >= 0 (a mirrored surface keeps its other coordinates). A fin is oriented upward.

    Args:
        wing: One surface of a validated geometry document.
        axis: 1 for a surface that spreads in y, 2 for one that stands up in z.

    Returns:
        The chain, root first.

    Raises:
        FormulaError: ``unsupported_configuration`` if the chain folds back along its axis.
    """
    points = [
        ChainPoint(
            x=s.xyz_le[0],
            y=s.xyz_le[1],
            z=s.xyz_le[2],
            chord=s.chord,
            twist=s.twist,
            airfoil=s.airfoil,
        )
        for s in wing.x_secs
    ]
    stored = list(range(len(points)))

    def along(point: ChainPoint) -> float:
        return point.y if axis == 1 else point.z

    if along(points[-1]) < along(points[0]):
        points, stored = points[::-1], stored[::-1]
    if axis == 1 and wing.symmetric and max(map(along, points), key=abs) < 0.0:
        points = [p.model_copy(update={"y": -p.y}) for p in points][::-1]
        stored = stored[::-1]
    if any(along(outer) < along(inner) for inner, outer in pairwise(points)):
        raise _unsupported(wing, "y" if axis == 1 else "z")
    return [
        point.model_copy(update={"device": _device(wing, stored[k], stored[k + 1])})
        if k + 1 < len(points)
        else point
        for k, point in enumerate(points)
    ]


def _device(wing: Wing, first: int, second: int) -> ChainDevice | None:
    """The device of the segment between two stored ribs, hinges in the order of travel.

    The format puts a device on the rib the segment starts at (stored order); a chain that runs
    against the stored order meets the segment's tip end first, so its hinges swap.
    """
    device = wing.x_secs[min(first, second)].trailing_edge_device
    if device is None:
        return None
    root = device.rel_chord_root
    tip = root if device.rel_chord_tip is None and root is not None else device.rel_chord_tip
    reversed_ = first > second
    return ChainDevice(
        name=device.name,
        role=device.role,
        hinge_start=tip if reversed_ else root,
        hinge_end=root if reversed_ else tip,
    )
