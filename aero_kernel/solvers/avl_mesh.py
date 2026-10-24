"""The aligned AVL strip mesh of an airplane (ARCHITECTURE ch. 8.8; AVL_CONVERGENCE.md).

Every surface is resampled at explicit stations, one strip per station pair. The horizontal tail's
strip boundaries lie on the main wing's stations over the tail span, and a fin uses the wing's strip
width along z. Unaligned strips between wing and tail make AVL's neutral point mesh-dependent by
several percent of the mean chord; aligned ones converge (BRYAN: NP 38.1 / 38.1 / 37.8 % MAC for
5/12, 10/24, 20/48 strips). No control surface is meshed: the devices are at rest.

The stations are uniform: the section positions of the airplane are not stations, the geometry is
interpolated linearly between them. Meshing a surface at its own section breaks gives strips of very
different widths, and AVL's neutral point then depends on them (BRYAN: a root section stored 0.25 mm
off the centreline gave a strip across its own mirror image and moved the neutral point by 3 % MAC).
"""

from bisect import bisect_right
from collections.abc import Callable, Sequence

from aero_kernel.geometry import Airfoil, AirplaneGeometry, Wing
from aero_kernel.surface_chain import ChainPoint, oriented_chain
from pydantic import BaseModel, ConfigDict

__all__ = ["MeshSection", "MeshSurface", "mesh_surfaces"]

# A tail station closer to the tail tip than this many wing strip widths would leave a sliver strip.
SLIVER_STEPS = 0.3
# Stations are merged when they agree to this many decimals (metres).
_DECIMALS = 9


class MeshSection(BaseModel):
    """One station of a surface: leading edge, chord, twist and the airfoil in force there.

    Attributes:
        x: x of the leading edge in m.
        y: y of the leading edge in m.
        z: z of the leading edge in m.
        chord: Chord in m.
        twist: Twist in degrees.
        airfoil: Index of the airfoil, as numbered by the caller's callback.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float
    y: float
    z: float
    chord: float
    twist: float
    airfoil: int


class MeshSurface(BaseModel):
    """One surface of the mesh.

    Attributes:
        name: Surface name.
        symmetric: Whether AVL mirrors it about y = 0.
        sections: Stations, root first, one strip per neighbouring pair.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    symmetric: bool
    sections: tuple[MeshSection, ...]


def _interp(position: Sequence[float], values: Sequence[float], at: float) -> float:
    """Linear interpolation of ``values`` over increasing ``position``, held at the ends."""
    if at <= position[0]:
        return values[0]
    if at >= position[-1]:
        return values[-1]
    upper = bisect_right(position, at)
    lower = upper - 1
    fraction = (at - position[lower]) / (position[upper] - position[lower])
    return values[lower] + fraction * (values[upper] - values[lower])


def _axis(wing: Wing) -> int:
    """1 (y) for a surface that spreads sideways, 2 (z) for one that stands up."""
    secs = wing.x_secs
    y_extent = abs(secs[-1].xyz_le[1] - secs[0].xyz_le[1])
    z_extent = abs(secs[-1].xyz_le[2] - secs[0].xyz_le[2])
    return 1 if y_extent >= z_extent else 2


def _root(wing: Wing, chain: Sequence[ChainPoint]) -> float:
    """Y of the first station: the centreline for a mirrored surface (centreline convention).

    A root section stored slightly off the centreline would give a strip that crosses its own
    mirror image (BRYAN, -0.25 mm: 3 % MAC), or a slit between the halves (JAGUAR, +1.1 mm: a neutral
    point that drifts with every span doubling); the section values at y = 0 are interpolated, or held
    if the root lies beyond it.
    """
    return 0.0 if wing.symmetric else chain[0].y


def _uniform(start: float, end: float, count: int) -> list[float]:
    """``count`` equal strips from ``start`` to ``end``: the ``count + 1`` stations."""
    return [round(start + k * (end - start) / count, _DECIMALS) for k in range(count + 1)]


def _section_at(
    chain: Sequence[ChainPoint], axis: int, at: float, airfoil_index: Callable[[Airfoil], int]
) -> MeshSection:
    """The section of an oriented chain at the station ``at`` along ``axis``."""
    position = [p.y if axis == 1 else p.z for p in chain]
    inside = min(max(bisect_right(position, at) - 1, 0), len(chain) - 2)
    return MeshSection(
        x=_interp(position, [p.x for p in chain], at),
        y=at if axis == 1 else _interp(position, [p.y for p in chain], at),
        z=at if axis == 2 else _interp(position, [p.z for p in chain], at),
        chord=_interp(position, [p.chord for p in chain], at),
        twist=_interp(position, [p.twist for p in chain], at),
        airfoil=airfoil_index(chain[inside].airfoil),
    )


def mesh_surfaces(
    airplane: AirplaneGeometry, n_wing: int, airfoil_index: Callable[[Airfoil], int]
) -> tuple[MeshSurface, ...]:
    """The aligned mesh: main wing, horizontal tail, then the other surfaces by name.

    Args:
        airplane: A geometry of a supported layout (one main wing).
        n_wing: Strips over the main wing's span.
        airfoil_index: Numbers an airfoil for the adapter's coordinate files.

    Returns:
        The surfaces with their stations.

    Raises:
        ValueError: If there is no ``main_wing``.
    """
    wings = list((airplane.wings or {}).values())
    mains = [w for w in wings if w.surface_type == "main_wing"]
    if not mains:
        msg = "the aligned mesh needs a main_wing"
        raise ValueError(msg)
    main = mains[0]
    tails = [w for w in wings if w.surface_type == "horizontal_tail"]
    rest = sorted((w for w in wings if w is not main and w not in tails), key=lambda w: w.name)

    main_chain = oriented_chain(main, 1)
    y_root, y_tip = _root(main, main_chain), main_chain[-1].y
    step = (y_tip - y_root) / n_wing
    main_stations = _uniform(y_root, y_tip, n_wing)

    surfaces = [
        MeshSurface(
            name=main.name,
            symmetric=bool(main.symmetric),
            sections=tuple(_section_at(main_chain, 1, y, airfoil_index) for y in main_stations),
        )
    ]
    for tail in tails:
        chain = oriented_chain(tail, 1)
        root, tip = _root(tail, chain), chain[-1].y
        inside = [y for y in main_stations if root < y < tip - SLIVER_STEPS * step]
        stations = [root, *inside, tip]
        surfaces.append(
            MeshSurface(
                name=tail.name,
                symmetric=bool(tail.symmetric),
                sections=tuple(_section_at(chain, 1, y, airfoil_index) for y in stations),
            )
        )
    for wing in rest:
        axis = _axis(wing)
        chain = oriented_chain(wing, axis)
        along = [p.y if axis == 1 else p.z for p in chain]
        start, end = along[0], along[-1]
        count = max(2, round(abs(end - start) / abs(step)))
        stations = _uniform(start, end, count)
        surfaces.append(
            MeshSurface(
                name=wing.name,
                symmetric=bool(wing.symmetric),
                sections=tuple(_section_at(chain, axis, t, airfoil_index) for t in stations),
            )
        )
    return tuple(surfaces)
