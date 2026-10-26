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

The one exception is a run that drives the roll devices (``drive_roll``) or holds deflected flaps
(``drive_flaps``): the ends of every driven device are stations then, because AVL controls a strip only if both bounding sections declare the
control (``amake.f:397-399``), and the uniform stations that would leave a sliver next to such an end
are dropped. The tail takes the wing's stations inside its span as always, so a break on the wing is
a station on the tail too and the wing's trailing vortex there never meets a tail control point.
"""

import math
from bisect import bisect_right
from collections.abc import Callable, Sequence
from itertools import pairwise

from aero_kernel.devices import FLAP_ROLES
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Airfoil, AirplaneGeometry, Wing
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.solvers.devices import (
    flap_segments,
    roll_deflection,
    roll_segments,
)
from aero_kernel.surface_chain import ChainPoint, oriented_chain
from pydantic import BaseModel, ConfigDict

__all__ = [
    "FLAP_CONTROL",
    "MESH_DECIMALS",
    "ROLL_CONTROL",
    "SLIVER_STEPS",
    "MeshControl",
    "MeshSection",
    "MeshSurface",
    "mesh_surfaces",
    "split_at_hinge",
]

# A tail station closer to the tail tip than this many wing strip widths would leave a sliver strip.
SLIVER_STEPS = 0.3
# A flap control is the deflection itself: the variable is the angle, the gain one.
FLAP_GAIN = 1.0
# Stations are merged when they agree to this many decimals (metres).
MESH_DECIMALS = 9


# The two control variables of a run. The roll control is one name for every device acting as
# aileron, driven antisymmetrically (SgnDup -1 makes the mirrored half deflect the other way,
# avl_doc.txt:755-757); the flap control is one name for every deflected flap, symmetric (SgnDup +1).
ROLL_CONTROL = "aileron"
FLAP_CONTROL = "flap"
ROLL_SGN_DUP = -1
FLAP_SGN_DUP = 1


class MeshControl(BaseModel):
    """A control declared on a station (AVL ``CONTROL``).

    Attributes:
        gain: Deflection per unit of the control variable, on the side as written (+y).
        x_hinge: Hinge position as a fraction of the local chord.
        name: The control variable's name: :data:`ROLL_CONTROL` or :data:`FLAP_CONTROL`.
        sgn_dup: The sign of the mirrored half's deflection relative to the written one.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    gain: float
    x_hinge: float
    name: str = ROLL_CONTROL
    sgn_dup: int = ROLL_SGN_DUP


class MeshSection(BaseModel):
    """One station of a surface: leading edge, chord, twist and the airfoil in force there.

    Attributes:
        x: x of the leading edge in m.
        y: y of the leading edge in m.
        z: z of the leading edge in m.
        chord: Chord in m.
        twist: Twist in degrees.
        airfoil: Index of the airfoil, as numbered by the caller's callback.
        control: The roll control declared here, if the station lies on a driven device.
        flap: The flap control declared here, if the station lies on a deflected flap.
        chord_range: The part of the airfoil this piece of a split surface carries, as fractions
            of the chord (AVL ``AFIL x_min x_max``); ``None`` for the whole contour.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float
    y: float
    z: float
    chord: float
    twist: float
    airfoil: int
    control: MeshControl | None = None
    flap: MeshControl | None = None
    chord_range: tuple[float, float] | None = None

    def controls(self) -> tuple[MeshControl, ...]:
        """The controls declared here, the roll control first (the order they are written in)."""
        return tuple(c for c in (self.control, self.flap) if c is not None)


class MeshSurface(BaseModel):
    """One surface of the mesh.

    Attributes:
        name: Surface name.
        symmetric: Whether AVL mirrors it about y = 0.
        sections: Stations, root first, one strip per neighbouring pair.
        n_chord: Chordwise vortices of this surface; ``None`` takes the run's count.
        component: AVL ``COMPONENT``: surfaces of one component share their wake and the strips
            of their stations (the pieces of a split surface); ``None`` for a surface of its own.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    symmetric: bool
    sections: tuple[MeshSection, ...]
    n_chord: int | None = None
    component: int | None = None


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
    return [round(start + k * (end - start) / count, MESH_DECIMALS) for k in range(count + 1)]


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


def _sine_to_tip(start: float, end: float, count: int, breaks: Sequence[float]) -> list[float]:
    """The ``count + 1`` stations of a driven surface: one sine-to-tip distribution, breaks exact.

    ``y = start + (end - start) sin(pi/2 t)``, ``t`` in [0, 1]: a cosine distribution over the whole
    half span, AVL's ``Sspace`` -2 from root to tip, which Drela recommends for a wing without a
    chord break at the centreline (``avl_doc.txt:1043-1048``). Uniform strips have an O(1/N) error
    at the tip that shows in the roll damping (``Clp`` halves its error on every doubling). A break
    (a device end) is a station exactly: its ``t`` is rounded to the nearest strip count and ``t``
    runs evenly inside each piece between breaks, so the strip widths stay continuous
    (``avl_doc.txt:1100``). The distribution does not depend on the number of breaks inside a piece.

    Args:
        start: Y of the root station.
        end: Y of the tip station.
        count: Strips over the half span.
        breaks: Ys of the stations that must exist, between the ends.

    Returns:
        The stations, root first.
    """
    span = end - start
    inner = sorted({round(b, MESH_DECIMALS) for b in breaks if start < b < end})
    # t of the breaks, exact; the strips a piece gets are the rounded difference of their cumulative
    # counts, at least one
    t_edges = [0.0, *(2.0 / math.pi * math.asin((b - start) / span) for b in inner), 1.0]
    cuts = [0, *(round(count * t) for t in t_edges[1:-1]), count]
    stations = [round(start, MESH_DECIMALS)]
    for (low, high), (t_low, t_high) in zip(pairwise(cuts), pairwise(t_edges), strict=True):
        n = max(high - low, 1)
        for k in range(1, n + 1):
            t = t_low + (t_high - t_low) * k / n
            stations.append(round(start + span * math.sin(0.5 * math.pi * t), MESH_DECIMALS))
    return stations


class _Span(BaseModel):
    """One driven segment of the oriented main-wing chain, with its hinge line."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    y_start: float
    y_end: float
    x_start: float
    x_end: float


def _driven_spans(
    wing_key: str,
    chain: Sequence[ChainPoint],
    join_tolerance_m: float,
    roles: frozenset[str],
    *,
    deflected_only: bool = False,
) -> list[_Span]:
    """The driven segments of the oriented chain with the absolute hinge line of each.

    The hinge line of a segment runs straight from ``x_le + h c`` at its start to the same at its
    end (AVL interpolates the same line between sections, ``amake.f:415-419``). Two positions closer
    than ``join_tolerance_m`` (canon rule ``hinge-line-continuity``) are the same rib.

    Args:
        wing_key: Key of the wing, for the message.
        chain: The oriented chain of the main wing.
        join_tolerance_m: The canon rule's join tolerance.
        roles: The roles of the devices that make a span.
        deflected_only: Only devices off their rest position make a span (the flaps).

    Raises:
        FormulaError: ``unsupported_configuration`` (``hinge_line_discontinuous``) if two driven
            segments meet at a rib with different hinge lines: AVL holds one value per section.
    """
    spans: list[_Span] = []
    for start, end in pairwise(chain):
        device = start.device
        if device is None or device.role not in roles:
            continue
        if deflected_only and not device.deflection_deg:
            continue
        if device.hinge_start is None or device.hinge_end is None:
            msg = "a driven device without a hinge: roll_segments must have refused it"
            raise ValueError(msg)
        spans.append(
            _Span(
                y_start=start.y,
                y_end=end.y,
                x_start=start.x + device.hinge_start * start.chord,
                x_end=end.x + device.hinge_end * end.chord,
            )
        )
    for before, after in pairwise(spans):
        joined = math.isclose(before.y_end, after.y_start, abs_tol=join_tolerance_m)
        if joined and not math.isclose(before.x_end, after.x_start, abs_tol=join_tolerance_m):
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "hinge_line_discontinuous",
                f"the driven device of the wing {wing_key!r} has a hinge line with a jump at "
                f"y = {before.y_end:.6g} m",
                "AVL holds one hinge position per section: make the hinge line continuous",
                detail={"wing": wing_key, "y_m": before.y_end},
                parameter="airplane",
            )
    return spans


def _device_ends(spans: Sequence[_Span], join_tolerance_m: float) -> list[float]:
    """The spanwise ends of the devices: the two ends of every run of joined driven segments.

    The ribs inside a device are not breaks; like all ribs they are interpolated between stations.
    """
    ends: list[float] = []
    for index, span in enumerate(spans):
        previous = spans[index - 1] if index else None
        if previous is None or not math.isclose(
            previous.y_end, span.y_start, abs_tol=join_tolerance_m
        ):
            ends.append(span.y_start)
        following = spans[index + 1] if index + 1 < len(spans) else None
        if following is None or not math.isclose(
            span.y_end, following.y_start, abs_tol=join_tolerance_m
        ):
            ends.append(span.y_end)
    return ends


def _control_at(
    y: float,
    spans: Sequence[_Span],
    section: MeshSection,
    join_tolerance_m: float,
    control: tuple[str, int],
) -> MeshControl | None:
    """The control of a station: on a driven span (ends inclusive), hinge from its line.

    Args:
        y: The station.
        spans: The driven spans of the control.
        section: The mesh section at the station.
        join_tolerance_m: The canon rule's join tolerance.
        control: The control's name and the sign of its mirrored half.
    """
    name, sgn_dup = control
    for span in spans:
        if span.y_start - join_tolerance_m <= y <= span.y_end + join_tolerance_m:
            fraction = (y - span.y_start) / (span.y_end - span.y_start)
            x_line = span.x_start + min(max(fraction, 0.0), 1.0) * (span.x_end - span.x_start)
            return MeshControl(
                gain=roll_deflection(1, 1.0) if name == ROLL_CONTROL else FLAP_GAIN,
                x_hinge=(x_line - section.x) / section.chord,
                name=name,
                sgn_dup=sgn_dup,
            )
    return None


def _refuse_driven_device_off(
    wings: dict[str, Wing], main_key: str, roles: frozenset[str], *, deflected_only: bool = False
) -> None:
    """Refuse a driven device outside the main wing: nothing would drive it in the AVL file."""
    for key, wing in wings.items():
        if key == main_key:
            continue
        for index, section in enumerate(wing.x_secs):
            device = section.trailing_edge_device
            if device is None or device.role not in roles:
                continue
            if deflected_only and not device.deflection_deg:
                continue
            label = device.name or f"device {index}"
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "unsupported_layout",
                f"the driven device {label!r} (role {device.role}) sits on {key!r}, not on the "
                "main wing",
                "the steady roll is driven, and flaps are deflected, on the main wing only",
                detail={"wing": key, "device": label, "role": device.role},
                parameter="airplane",
            )


def split_at_hinge(
    surface: MeshSurface, n_chord: tuple[int, int]
) -> tuple[MeshSurface, MeshSurface]:
    """Split a driven surface at its hinge line into a front and an aft surface (Drela's rule 3).

    Both pieces have the same stations, so the strips agree (``avl_doc.txt:1110-1117``: same
    component, same spanwise spacing). The split fraction of a station is the hinge position of its
    control (the most forward one where a roll control and a flap meet; the other is then measured
    from the cut); a station off the devices takes the one of the nearest controlled station, a cut that
    is continuous and otherwise immaterial. The aft piece starts at the hinge with the leading-edge
    z unchanged (AVL tilts the normals by the incidence, it does not rotate the lattice,
    ``amake.f:497-511``) and carries the control with its hinge at its own leading edge, so the
    deflected part is the whole aft strip (``amake.f:418-423``).

    Args:
        surface: The driven surface with controls on its device stations.
        n_chord: Chordwise vortices of the front and the aft surface.

    Returns:
        The front and the aft surface.
    """

    def cut_of(section: MeshSection) -> float | None:
        """The split fraction a controlled station asks for: its most forward hinge."""
        return min((c.x_hinge for c in section.controls()), default=None)

    controlled = [(s.y, cut) for s in surface.sections if (cut := cut_of(s)) is not None]

    def split_of(section: MeshSection) -> float:
        own = cut_of(section)
        if own is not None:
            return own
        return min(controlled, key=lambda c: abs(c[0] - section.y))[1]

    def moved(control: MeshControl | None, cut: float) -> MeshControl | None:
        """The control on the aft piece: its hinge measured from the cut (0 where the cut is it)."""
        if control is None:
            return None
        return control.model_copy(update={"x_hinge": (control.x_hinge - cut) / (1.0 - cut)})

    front: list[MeshSection] = []
    aft: list[MeshSection] = []
    for section in surface.sections:
        cut = split_of(section)
        front.append(
            section.model_copy(
                update={
                    "chord": cut * section.chord,
                    "control": None,
                    "flap": None,
                    "chord_range": (0.0, cut),
                }
            )
        )
        aft.append(
            section.model_copy(
                update={
                    "x": section.x + cut * section.chord,
                    "chord": (1.0 - cut) * section.chord,
                    "control": moved(section.control, cut),
                    "flap": moved(section.flap, cut),
                    "chord_range": (cut, 1.0),
                }
            )
        )
    return (
        MeshSurface(
            name=f"{surface.name} front",
            symmetric=surface.symmetric,
            sections=tuple(front),
            n_chord=n_chord[0],
            component=1,
        ),
        MeshSurface(
            name=f"{surface.name} aft",
            symmetric=surface.symmetric,
            sections=tuple(aft),
            n_chord=n_chord[1],
            component=1,
        ),
    )


def _refuse_undrivable(
    airplane: AirplaneGeometry, main_key: str, *, drive_roll: bool, drive_flaps: bool
) -> None:
    """Apply the shared device rules of a driven run and refuse a driven device off the main wing."""
    if drive_roll:
        roll_segments(airplane)  # the shared rules: mirrored surface, hinge given
        _refuse_driven_device_off(airplane.wings or {}, main_key, AILERON_ROLES)
    if drive_flaps:
        flap_segments(airplane)  # the same rules for a deflected flap
        _refuse_driven_device_off(airplane.wings or {}, main_key, FLAP_ROLES, deflected_only=True)


def _main_spans(
    main_key: str,
    chain: Sequence[ChainPoint],
    join_tolerance_m: float,
    *,
    drive_roll: bool,
    drive_flaps: bool,
) -> tuple[list[_Span], list[_Span]]:
    """The roll spans and the flap spans of the main wing's chain (empty where not driven)."""
    roll = _driven_spans(main_key, chain, join_tolerance_m, AILERON_ROLES) if drive_roll else []
    flap = (
        _driven_spans(main_key, chain, join_tolerance_m, FLAP_ROLES, deflected_only=True)
        if drive_flaps
        else []
    )
    return roll, flap


def mesh_surfaces(
    airplane: AirplaneGeometry,
    n_wing: int,
    airfoil_index: Callable[[Airfoil], int],
    *,
    join_tolerance_m: float,
    drive_roll: bool = False,
    drive_flaps: bool = False,
) -> tuple[MeshSurface, ...]:
    """The aligned mesh: main wing, horizontal tail, then the other surfaces by name.

    Args:
        airplane: A geometry of a supported layout (one main wing).
        n_wing: Strips over the main wing's span.
        airfoil_index: Numbers an airfoil for the adapter's coordinate files.
        join_tolerance_m: Two positions closer than this (m) are the same rib: the station of a
            device end and the rib it was read from agree to rounding (canon rule
            ``hinge-line-continuity``).
        drive_roll: Whether the devices acting as aileron are driven in this run: their ends
            become stations of the main wing (and, inside its span, of the tail) and every station
            on a device carries a control. ``False`` is the clean mesh. The main wing is the first
            surface; :func:`split_at_hinge` splits it for the run.
        drive_flaps: Whether the deflected flaps are held in this run: like ``drive_roll`` for the
            devices of role ``flap`` or ``flaperon`` that are off their rest position, with the
            symmetric control :data:`FLAP_CONTROL`. A flaperon carries both controls.

    Returns:
        The surfaces with their stations.

    Raises:
        ValueError: If there is no ``main_wing``.
        FormulaError: ``unsupported_configuration`` for a driven device off the main wing or with
            a discontinuous hinge line (``drive_roll`` or ``drive_flaps`` only); the errors of
            :func:`aero_kernel.solvers.devices.roll_segments` and
            :func:`aero_kernel.solvers.devices.flap_segments`.
    """
    wings = list((airplane.wings or {}).values())
    mains = [w for w in wings if w.surface_type == "main_wing"]
    if not mains:
        msg = "the aligned mesh needs a main_wing"
        raise ValueError(msg)
    main = mains[0]
    main_key = next(key for key, wing in (airplane.wings or {}).items() if wing is main)
    _refuse_undrivable(airplane, main_key, drive_roll=drive_roll, drive_flaps=drive_flaps)
    tails = [w for w in wings if w.surface_type == "horizontal_tail"]
    rest = sorted((w for w in wings if w is not main and w not in tails), key=lambda w: w.name)

    main_chain = oriented_chain(main, 1)
    y_root, y_tip = _root(main, main_chain), main_chain[-1].y
    step = (y_tip - y_root) / n_wing
    main_stations = _uniform(y_root, y_tip, n_wing)
    roll_spans, flap_spans = _main_spans(
        main_key, main_chain, join_tolerance_m, drive_roll=drive_roll, drive_flaps=drive_flaps
    )
    if drive_roll or drive_flaps:
        breaks = [
            *_device_ends(roll_spans, join_tolerance_m),
            *_device_ends(flap_spans, join_tolerance_m),
        ]
        main_stations = _sine_to_tip(y_root, y_tip, n_wing, breaks)

    def main_section(y: float) -> MeshSection:
        section = _section_at(main_chain, 1, y, airfoil_index)
        control = _control_at(
            y, roll_spans, section, join_tolerance_m, (ROLL_CONTROL, ROLL_SGN_DUP)
        )
        flap = _control_at(y, flap_spans, section, join_tolerance_m, (FLAP_CONTROL, FLAP_SGN_DUP))
        return section.model_copy(update={"control": control, "flap": flap})

    surfaces = [
        MeshSurface(
            name=main.name,
            symmetric=bool(main.symmetric),
            sections=tuple(main_section(y) for y in main_stations),
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
