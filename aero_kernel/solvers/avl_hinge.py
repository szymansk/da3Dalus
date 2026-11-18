"""The AVL model of the hinge-moment procedure (canon ``control-surface-hinge-moments``, ch. 8.8).

One AVL run per role. Every surface acting in the role is its own AVL control at gain 1 under a short
internal name (``c01``, ``c02``, ...), because AVL's ``HM`` sums all surfaces that share a control
name (``aero.f:411-420``, ``amake.f:545-549``); the key of the surface (``<wing>.<device>[_left|_right]``)
is kept beside the name and the name never leaves this module's caller. Every half of a mirrored wing
is its own explicit ``SURFACE``, without ``YDUPLICATE``: the image of a duplicated surface keeps the
control index, so ``HM`` would sum both sides (``amake.f:812-822``). A left half runs tip to root
like every AVL surface (``avl_doc.txt:615-625``); its hinge vector is the mirror image of the right
half's, so a positive deflection means the same on both sides: trailing edge down on a surface that
spreads in y, the trailing edge towards +y on one that stands up. Every wing of the airplane is
meshed, so that the tail's downwash and the fin's sidewash act on the surface that is read.

A surface is a run of adjacent segments of one wing that carry a device of the same name and role. The
ends of a run are stations; the half is split at its hinge line into a front and an aft surface of
one component (Drela's rule, ``avl_doc.txt:1110-1119``), the aft one carrying the control, so that
the deflected part is whole panels.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from itertools import pairwise

from aero_kernel.devices import FLAP_ROLES
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Airfoil, AirplaneGeometry, Wing
from aero_kernel.graph import AILERON_ROLES
from aero_kernel.solvers.avl_mesh import (
    MESH_DECIMALS,
    SLIVER_STEPS,
    MeshControl,
    MeshSection,
    MeshSurface,
    root_station,
    section_at,
    sine_to_tip,
    split_at_hinge,
    uniform_stations,
    wing_axis,
)
from aero_kernel.surface_chain import ChainPoint, oriented_chain
from pydantic import BaseModel, ConfigDict

__all__ = [
    "COMMAND_SIGNS",
    "ROLE_CODES",
    "ROLE_DEVICE_ROLES",
    "HingeControl",
    "HingeMesh",
    "hinge_mesh",
    "surface_key",
]

# The device roles that act in each role of the canon entry ("Roles by function"): a dual-role
# surface is evaluated once per role.
ROLE_DEVICE_ROLES: Mapping[str, frozenset[str]] = {
    "aileron": AILERON_ROLES,
    "elevator": frozenset({"elevator", "elevon", "ruddervator"}),
    "rudder": frozenset({"rudder", "ruddervator"}),
    "flap": FLAP_ROLES,
}
# The role codes the canon applications bind (``role`` input of the entry): its own coding.
ROLE_CODES: Mapping[int, str] = {1: "aileron", 2: "elevator", 3: "rudder", 4: "flap"}
# The sign of the control value of a role on the right (or only) half and on the left half, in the
# sense of a positive deflection of that half. Aileron: right trailing edge up for a positive command
# (``aileron-deflection``), the left one down. Elevator and flap: both down. Rudder: yaw to the right
# for a positive command (trailing edge towards +y on a fin; right half down, left half up on a
# V-tail); the canon fixes no sense for the rudder, this is the one of the entry's remark on it.
COMMAND_SIGNS: Mapping[str, tuple[int, int]] = {
    "aileron": (-1, 1),
    "elevator": (1, 1),
    "rudder": (1, -1),
    "flap": (1, 1),
}
# The hinge vector of a half; zero puts it along the hinge line in the direction the sections run.
_MIRRORED_FIN_HINGE = (0.0, 0.0, -1.0)
# Every surface of the mesh declares its component, so that none takes AVL's default (the surface
# index), which could collide with a declared one.
_FIRST_COMPONENT = 1


class HingeControl(BaseModel):
    """One AVL control of the run: one half of one surface.

    Attributes:
        name: The internal control name written to the file (at most 16 characters).
        key: The surface key ``<wing>.<device>[_left|_right]``.
        sign: The sign of the control value for a positive command of the role.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    key: str
    sign: int


class HingeMesh(BaseModel):
    """The AVL surfaces of a hinge-moment run and the controls they declare.

    Attributes:
        surfaces: The surfaces in file order.
        controls: The controls in the order they are created (not AVL's numbering: use
            :func:`aero_kernel.solvers.avl_writer.control_order`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    surfaces: tuple[MeshSurface, ...]
    controls: tuple[HingeControl, ...]


class _Span(BaseModel):
    """One segment of a run along the surface's spreading coordinate, with its hinge line."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: float
    end: float
    x_start: float
    x_end: float


class _Run(BaseModel):
    """A surface: adjacent segments of one wing with a device of one name and role."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    spans: tuple[_Span, ...]


def surface_key(wing_name: str, device_name: str, side: str | None) -> str:
    """The key of a control surface: ``<wing>.<device>`` and ``_left`` / ``_right`` if mirrored."""
    return f"{wing_name}.{device_name}" + ("" if side is None else f"_{side}")


def _device_name(point: ChainPoint) -> str:
    """The name of the device of the segment that starts at a chain point: name, label or role."""
    device = point.device
    assert device is not None  # callers pass a point with a device
    return device.name or device.label or device.role


def _along(point: ChainPoint, axis: int) -> float:
    """The spreading coordinate of a chain point."""
    return point.y if axis == 1 else point.z


def _runs(wing: Wing, chain: Sequence[ChainPoint], axis: int, roles: frozenset[str]) -> list[_Run]:
    """The runs of the chain's segments whose device acts in ``roles``, in oriented order.

    Raises:
        FormulaError: ``invalid_input`` (``missing_hinge``) for a device without a hinge position;
            ``unsupported_configuration`` (``hinge_device_on_unmirrored_surface``) for a device on
            an unmirrored surface that spreads in y.
    """
    runs: list[_Run] = []
    last: tuple[str, str] | None = None
    for start, end in pairwise(chain):
        device = start.device
        if device is None or device.role not in roles:
            last = None
            continue
        if device.hinge_start is None or device.hinge_end is None:
            raise FormulaError(
                ErrorCategory.INVALID_INPUT,
                "missing_hinge",
                f"the device {_device_name(start)!r} of the wing {wing.name!r} has no hinge position",
                "give rel_chord_root; the tool's default hinge is never used",
                detail={"wing": wing.name, "device": _device_name(start)},
                parameter="airplane",
            )
        if axis == 1 and not wing.symmetric:
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION,
                "hinge_device_on_unmirrored_surface",
                f"the device {_device_name(start)!r} (role {device.role}) sits on the unmirrored "
                f"wing {wing.name!r}",
                "a control surface on a surface that spreads sideways is supported on a mirrored one only",
                detail={"wing": wing.name, "device": _device_name(start), "role": device.role},
                parameter="airplane",
            )
        span = _Span(
            start=_along(start, axis),
            end=_along(end, axis),
            x_start=start.x + device.hinge_start * start.chord,
            x_end=end.x + device.hinge_end * end.chord,
        )
        identity = (_device_name(start), device.role)
        if last == identity:
            runs[-1] = runs[-1].model_copy(update={"spans": (*runs[-1].spans, span)})
        else:
            runs.append(_Run(name=identity[0], spans=(span,)))
        last = identity
    return runs


def _check_joints(wing: Wing, runs: Sequence[_Run], join_tolerance_m: float) -> None:
    """Refuse a run whose hinge line jumps at a rib: AVL holds one hinge position per section."""
    for run in runs:
        for before, after in pairwise(run.spans):
            if not math.isclose(before.x_end, after.x_start, abs_tol=join_tolerance_m):
                raise FormulaError(
                    ErrorCategory.UNSUPPORTED_CONFIGURATION,
                    "hinge_line_discontinuous",
                    f"the device {run.name!r} of the wing {wing.name!r} has a hinge line with a "
                    f"jump at {before.end:.6g} m",
                    "AVL holds one hinge position per section: make the hinge line continuous",
                    detail={"wing": wing.name, "device": run.name, "at_m": before.end},
                    parameter="airplane",
                )


def _ends(runs: Sequence[_Run]) -> list[float]:
    """The two ends of every run: the stations that must exist."""
    return [end for run in runs for end in (run.spans[0].start, run.spans[-1].end)]


def _with_breaks(stations: Sequence[float], breaks: Sequence[float], sliver: float) -> list[float]:
    """The stations with the breaks added and every station within ``sliver`` of one dropped."""
    first, last = stations[0], stations[-1]
    inner = sorted({round(b, MESH_DECIMALS) for b in breaks if first < b < last})
    kept = [s for s in stations if s in (first, last) or all(abs(s - b) >= sliver for b in inner)]
    return sorted({*kept, *inner})


def _control_for(
    at: float,
    run: _Run,
    section: MeshSection,
    control: tuple[str, tuple[float, float, float]],
    join_tolerance_m: float,
) -> MeshControl | None:
    """The control of a run at a station, if the station lies on the run (ends inclusive)."""
    name, hinge_vector = control
    for span in run.spans:
        if span.start - join_tolerance_m <= at <= span.end + join_tolerance_m:
            fraction = min(max((at - span.start) / (span.end - span.start), 0.0), 1.0)
            x_line = span.x_start + fraction * (span.x_end - span.x_start)
            return MeshControl(
                gain=1.0,
                x_hinge=(x_line - section.x) / section.chord,
                name=name,
                sgn_dup=1,
                hinge_vector=hinge_vector,
            )
    return None


class _Half(BaseModel):
    """One written half of a wing: its controls by run index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    suffix: str | None
    names: tuple[str, ...]
    hinge_vector: tuple[float, float, float]
    mirrored: bool


def _mirrored(section: MeshSection) -> MeshSection:
    """The section of the other side of the plane y = 0."""
    return section.model_copy(update={"y": -section.y})


def _half_surface(
    wing: Wing,
    half: _Half,
    sections: Sequence[MeshSection],
    runs: Sequence[_Run],
    axis: int,
    join_tolerance_m: float,
) -> MeshSurface:
    """One half as a surface, controls on the stations of its runs; the left half runs tip to root."""
    stations: list[MeshSection] = []
    for section in sections:
        at = section.y if axis == 1 else section.z
        controls = tuple(
            c
            for run, name in zip(runs, half.names, strict=True)
            if (c := _control_for(at, run, section, (name, half.hinge_vector), join_tolerance_m))
            is not None
        )
        stations.append(section.model_copy(update={"others": controls}))
    if half.mirrored:
        image = [_mirrored(s) for s in stations]
        stations = image[::-1] if axis == 1 else image
    return MeshSurface(
        name=wing.name if half.suffix is None else f"{wing.name} {half.suffix}",
        symmetric=False,
        sections=tuple(stations),
    )


def _main_stations(
    wing: Wing, chain: Sequence[ChainPoint], n_wing: int, breaks: Sequence[float]
) -> list[float]:
    """The stations of the main wing: sine-to-tip with the breaks exact if driven, else uniform."""
    start, end = root_station(wing, chain), chain[-1].y
    return (
        sine_to_tip(start, end, n_wing, breaks) if breaks else uniform_stations(start, end, n_wing)
    )


def _tail_stations(
    wing: Wing,
    chain: Sequence[ChainPoint],
    main_stations: Sequence[float],
    step: float,
    breaks: Sequence[float],
) -> list[float]:
    """The stations of a horizontal tail: the main wing's inside its span, and its own breaks."""
    root, tip = root_station(wing, chain), chain[-1].y
    inside = [y for y in main_stations if root < y < tip - SLIVER_STEPS * abs(step)]
    return _with_breaks([root, *inside, tip], breaks, SLIVER_STEPS * abs(step))


def _rest_stations(
    chain: Sequence[ChainPoint], axis: int, step: float, breaks: Sequence[float]
) -> list[float]:
    """The stations of any other surface: the main wing's strip width, and its own breaks."""
    start, end = _along(chain[0], axis), _along(chain[-1], axis)
    count = max(2, round(abs(end - start) / abs(step)))
    return _with_breaks(uniform_stations(start, end, count), breaks, SLIVER_STEPS * abs(step))


def _halves(
    wing: Wing,
    role: str,
    runs: Sequence[_Run],
    axis: int,
    controls: list[HingeControl],
    keys: set[str],
) -> list[_Half]:
    """The halves a wing is written as, creating the controls of its runs (right half first).

    Raises:
        FormulaError: ``invalid_input`` (``duplicate_surface_key``) if a surface key repeats.
    """
    sides: list[str | None] = ["right", "left"] if wing.symmetric else [None]
    halves: list[_Half] = []
    for index, side in enumerate(sides):
        names: list[str] = []
        for run in runs:
            key = surface_key(wing.name, run.name, side)
            if key in keys:
                raise FormulaError(
                    ErrorCategory.INVALID_INPUT,
                    "duplicate_surface_key",
                    f"two control surfaces have the key {key!r}",
                    "give the devices of one wing different names",
                    detail={"key": key},
                    parameter="airplane",
                )
            keys.add(key)
            name = f"c{len(controls) + 1:02d}"
            names.append(name)
            controls.append(HingeControl(name=name, key=key, sign=COMMAND_SIGNS[role][index]))
        halves.append(
            _Half(
                suffix=side,
                names=tuple(names),
                hinge_vector=_MIRRORED_FIN_HINGE if (index == 1 and axis == 2) else (0.0, 0.0, 0.0),
                mirrored=index == 1,
            )
        )
    return halves


def hinge_mesh(
    airplane: AirplaneGeometry,
    role: str,
    n_wing: int,
    airfoil_index: Callable[[Airfoil], int],
    *,
    join_tolerance_m: float,
    split_n_chord: tuple[int, int],
) -> HingeMesh:
    """The mesh of one hinge-moment run: every wing, every half explicit, every role surface a control.

    Args:
        airplane: A geometry with one main wing and its devices at rest.
        role: ``aileron``, ``elevator``, ``rudder`` or ``flap``.
        n_wing: Strips over the main wing's half span.
        airfoil_index: Numbers an airfoil for the adapter's coordinate files.
        join_tolerance_m: Two positions closer than this (m) are the same rib (canon rule
            ``hinge-line-continuity``).
        split_n_chord: Chordwise vortices of the front and the aft surface of a split half.

    Returns:
        The surfaces and their controls; the controls are empty if no device acts in the role.

    Raises:
        ValueError: If there is no ``main_wing`` or the role is unknown.
        FormulaError: ``missing_hinge``, ``hinge_device_on_unmirrored_surface``,
            ``hinge_line_discontinuous`` and ``duplicate_surface_key`` (see :func:`_runs`,
            :func:`_check_joints`, :func:`_halves`).
    """
    roles = ROLE_DEVICE_ROLES[role]
    wings = list((airplane.wings or {}).values())
    mains = [w for w in wings if w.surface_type == "main_wing"]
    if not mains:
        msg = "the hinge-moment mesh needs a main_wing"
        raise ValueError(msg)
    main = mains[0]
    tails = [w for w in wings if w.surface_type == "horizontal_tail"]
    others = sorted((w for w in wings if w is not main and w not in tails), key=lambda w: w.name)
    main_chain = oriented_chain(main, 1)
    step = (main_chain[-1].y - root_station(main, main_chain)) / n_wing
    surfaces: list[MeshSurface] = []
    controls: list[HingeControl] = []
    keys: set[str] = set()
    main_stations: list[float] = []
    for component, wing in enumerate([main, *tails, *others], start=_FIRST_COMPONENT):
        axis = 1 if (wing is main or wing in tails) else wing_axis(wing)
        chain = main_chain if wing is main else oriented_chain(wing, axis)
        runs = _runs(wing, chain, axis, roles)
        _check_joints(wing, runs, join_tolerance_m)
        if wing is main:
            main_stations = _main_stations(wing, chain, n_wing, _ends(runs))
            stations = main_stations
        elif wing in tails:
            stations = _tail_stations(wing, chain, main_stations, step, _ends(runs))
        else:
            stations = _rest_stations(chain, axis, step, _ends(runs))
        sections = [section_at(chain, axis, at, airfoil_index) for at in stations]
        for half in _halves(wing, role, runs, axis, controls, keys):
            piece = _half_surface(wing, half, sections, runs, axis, join_tolerance_m)
            pieces = split_at_hinge(piece, split_n_chord) if runs else (piece,)
            surfaces += [p.model_copy(update={"component": component}) for p in pieces]
    return HingeMesh(surfaces=tuple(surfaces), controls=tuple(controls))
