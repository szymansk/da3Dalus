"""Bending capacity of the wing's spar: section modulus and ``M_cap`` at a spanwise station.

The reader of this module is the canon formula ``spar-break-load-factor`` (and
``max-mass-structure``), which follows in gh-1429. Until then nothing but the tests calls it
(ADR 0021, rule 2: scaffolding for planned work with a live ticket, marked ``UNREACHABLE(gh-1429)``
below, with a test that asserts it stays unreachable). The ticket that wires the formula removes
the marker and that test.

Pure functions over the parsed geometry and the pushed materials; no I/O, no solver. Strength only
(BR-W18): no buckling, no stiffness, no modulus of elasticity; attachments are ignored. The
strength is the material's published breaking strength in bending, and **no safety, resistance or
knock-down factor** is applied anywhere (maintainer, 2026-11-19, gh-1427): the canon computes, it
does not judge. Units: SI, so ``W`` in m^3, strength in Pa, capacity in N*m.

The result is **typed**, so that a caller cannot treat "unknown" as "skip": a station yields a
:class:`BendingCapacity` (a value), :class:`NoSparAtStation` (no spar is present there) or
:class:`CapacityUnknown` (the front spar is present but has no section). A station outside the
half span, or not a number, is an error.

How the document is read (format ch. 5.1, version 3):

* **Bending axis.** The spar bends about the chordwise axis. ``height`` of a section is measured in
  the airfoil thickness direction, ``width`` across the chord; ``W = I / (h / 2)``. Rod and tube
  are symmetric. The capacity is the same upward and downward: one strength, no distinction
  between tension and compression.
* **One section per segment: the smallest one.** A segment's ``section`` is the *smallest*
  section the spar has within that segment (the producer of the document is responsible); the
  kernel holds it constant over the segment and never interpolates.
* **Segment ownership.** The spars of a segment (the ribs ``i`` and ``i + 1``) are consulted only
  at stations of that segment: a station belongs to the segment with ``y_i <= y < y_(i+1)`` of the
  ribs' leading-edge ``y`` (the last segment also owns its outer rib). So a spar that continues
  through several segments (``*_backward``, ``follow``) is counted once, by the entry of the
  segment that contains the station.
* **Spanwise extent, as the creator builds it.** ``VaseModeWingCreator._create_spare_shape``
  (``cad_designer/airplane/creator/wing/VaseModeWingCreator.py:807-819``) puts a plane at
  ``spare_origin`` with the normal ``spare_vector``, moves it by ``spare_start`` along the normal,
  extrudes ``spare_length`` (``None``: far beyond the segment), in **both** directions when
  ``spare_start`` is 0 (``:813``), and intersects the result with the segment. So the spar exists
  over the axis coordinates ``[start, start + length]`` (``[-length, length]`` when ``start`` is 0;
  open ended when ``length`` is ``None``), inside the segment. A spar with ``start`` 0 and no
  length is the whole segment, and needs no axis. Otherwise the axis is read like the
  construction reads it (``cad_designer/.../wing/WingConfiguration.py``):

  - a given ``spare_vector`` is the direction, normalised (``:339``, ``:367-368``);
  - ``standard`` without a vector: the line from the chord position ``spare_position_factor`` on the
    root rib to the same position on the tip rib (``_get_standard_spare_origin_and_vector``,
    ``:157-177``), taken here from the ribs' leading-edge points and chords; the twist and the
    camber of the two points are ignored (second order);
  - ``normal`` without a vector: the segment plane's y axis (``:334-335``), whose spanwise component
    is that of the leading-edge line projected on the yz plane (dihedral, no sweep);
  - origin: ``normal`` takes ``spare_origin`` as an offset from the segment root (``:345``),
    ``standard`` as an absolute point (``:369-372``); absent, the root rib.
  - ``follow``, ``standard_backward`` and ``orthogonal_backward`` chain the axis over several
    segments (``:303-327``, ``:348-352``): with ``spare_start`` or ``spare_length`` given their
    extent cannot be placed without guessing, and fail with ``spar_extent_not_determinable``
    naming the mode.
* **Ignored: the spar's angle to the y axis.** Sweep, dihedral and the modes' vectors enter only
  the placement of the extent. The capacity ``W * strength`` itself does not depend on them. When
  a station's capacity is compared with the bending moment about the y direction, a spar inclined
  by an angle ``a`` to the y axis carries a local moment of only ``cos(a)`` times it, so ignoring
  the angle makes the ratio ``M_cap / M`` too small by ``cos(a)``: conservative.
* **Which spar bends the wing (BR-W16).** The front spar alone carries the bending, the rear one
  the torsion, so capacities are **not added**. The front spar at a station is the spar with the
  smallest ``spare_position_factor`` among those **present at that station** (a spar that has
  ended by ``spare_start`` / ``spare_length`` is not present; the remaining one is then the front
  spar). A present front spar without ``section`` means the capacity is unknown
  (:class:`CapacityUnknown`): the rear spar never stands in for a present front spar. Several
  spars present need distinct, finite positions, or the station fails with
  ``front_spar_not_determinable`` naming them.
"""

import math
from collections.abc import Mapping
from typing import Literal

from aero_kernel.components import Material
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import (
    RectangularSection,
    RodSection,
    SpareDetail,
    SparSection,
    TubeSection,
    Wing,
)
from pydantic import BaseModel, ConfigDict, JsonValue

# UNREACHABLE(gh-1429): no production module imports this one yet.
__all__ = [
    "BendingCapacity",
    "CapacityUnknown",
    "NoSparAtStation",
    "SparCapacity",
    "bending_capacity",
    "section_modulus",
]

_CONTINUED_MODES = ("follow", "standard_backward", "orthogonal_backward")


class BendingCapacity(BaseModel):
    """The front spar's bending capacity at a station: a value.

    Attributes:
        moment_nm: ``M_cap = W * strength`` in N*m, the same upward and downward.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    moment_nm: float


class NoSparAtStation(BaseModel):
    """No spar is present at the station (none in its segment, or all have ended there).

    Attributes:
        wing: Name of the wing.
        y: The station, metres.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wing: str
    y: float


class CapacityUnknown(BaseModel):
    """The front spar is present at the station but the document gives no section for it.

    The capacity there is **unknown**, not absent: a caller must not skip such a station.

    Attributes:
        wing: Name of the wing.
        x_sec: Index of the rib that starts the segment.
        spar: Index of the spar in that rib's ``spare_list``.
        reason: Why: the front spar has no ``section``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wing: str
    x_sec: int
    spar: int
    reason: Literal["front_spar_without_section"]


SparCapacity = BendingCapacity | NoSparAtStation | CapacityUnknown
"""The outcome at a station; a caller handles each type explicitly."""


def section_modulus(section: SparSection) -> float:
    """Section modulus ``W = I / (h / 2)`` of a spar section about the chordwise axis.

    Rod ``pi d^3 / 32``; tube ``pi (D^4 - d^4) / (32 D)`` with ``d = D - 2 t``; rectangular
    ``b h^2 / 6``; capped (two flanges, no web) ``b (H^3 - h^3) / (6 H)`` with ``h = H - 2 t``.
    The dimensions are assumed admissible (``validate.py``, rule ``spar-section-admissible``).

    Args:
        section: The parsed section, dimensions in metres.

    Returns:
        ``W`` in m^3.
    """
    if isinstance(section, RodSection):
        return math.pi * section.diameter**3 / 32.0
    if isinstance(section, TubeSection):
        outer = section.outer_diameter
        inner = outer - 2.0 * section.wall_thickness
        return math.pi * (outer**4 - inner**4) / (32.0 * outer)
    if isinstance(section, RectangularSection):
        return section.width * section.height**2 / 6.0
    gap = section.height - 2.0 * section.flange_thickness
    return section.width * (section.height**3 - gap**3) / (6.0 * section.height)


def _outside(wing: Wing, y: float) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT,
        "station_outside_wing",
        f"The station y = {y} is not on the stored half of wing {wing.name!r} "
        "(outside its first and last rib, or not a number).",
        "Ask for stations between the root and the tip rib, in metres.",
        detail={"wing": wing.name},
    )


def _segment_at(wing: Wing, y: float) -> int:
    """Index of the segment that owns station ``y``; raises ``station_outside_wing`` if none."""
    ribs = wing.x_secs
    last = len(ribs) - 2
    for index in range(last + 1):
        y_root, y_tip = ribs[index].xyz_le[1], ribs[index + 1].xyz_le[1]
        low, high = min(y_root, y_tip), max(y_root, y_tip)
        if low <= y < high or (index == last and y == high and low < high):
            return index
    raise _outside(wing, y)


def _not_determinable(wing: Wing, index: int, position: int, why: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "spar_extent_not_determinable",
        f"The spanwise extent of spar {position} of wing {wing.name!r}, x_secs[{index}] cannot "
        f"be placed: {why}.",
        "Give the spar the full segment (spare_start 0 and no spare_length), or a mode whose "
        "axis the kernel can place (standard or normal).",
        detail={"wing": wing.name, "x_sec": index, "spar": position},
        parameter="airplane",
    )


def _axis(wing: Wing, index: int, position: int, spar: SpareDetail) -> tuple[float, float]:
    """``(y at axis coordinate 0, y per metre along the axis)`` of a spar with a partial extent."""
    mode = spar.spare_mode or "standard"
    if mode in _CONTINUED_MODES:
        raise _not_determinable(
            wing, index, position, f"mode {mode!r} chains the axis over several segments"
        )
    root, tip = wing.x_secs[index], wing.x_secs[index + 1]
    d_y, d_z = tip.xyz_le[1] - root.xyz_le[1], tip.xyz_le[2] - root.xyz_le[2]
    if spar.spare_vector is not None:
        vector = spar.spare_vector
        run = math.sqrt(sum(c * c for c in vector))
        if not run > 0.0:
            raise _not_determinable(wing, index, position, "spare_vector is the zero vector")
        slope = vector[1] / run
    elif mode == "standard":
        factor = spar.spare_position_factor
        if factor is None:
            raise _not_determinable(
                wing, index, position, "mode 'standard' needs spare_position_factor to place it"
            )
        d_x = (tip.xyz_le[0] + factor * tip.chord) - (root.xyz_le[0] + factor * root.chord)
        slope = d_y / math.sqrt(d_x * d_x + d_y * d_y + d_z * d_z)
    else:
        slope = d_y / math.hypot(d_y, d_z)
    if not abs(slope) > 0.0:
        raise _not_determinable(wing, index, position, f"mode {mode!r}: the axis is not spanwise")
    offset = 0.0 if spar.spare_origin is None else spar.spare_origin[1]
    if mode == "normal" or spar.spare_origin is None:
        return root.xyz_le[1] + offset, slope
    return offset, slope


def _present_at(wing: Wing, index: int, position: int, spar: SpareDetail, y: float) -> bool:
    """Whether the spar of segment ``index`` exists at station ``y`` (already inside the segment)."""
    start, length = spar.spare_start, spar.spare_length
    if start <= 0.0 and length is None:
        return True
    y_origin, slope = _axis(wing, index, position, spar)
    if start <= 0.0:
        low = -math.inf if length is None else -length
        high = math.inf if length is None else length
    else:
        low = start
        high = math.inf if length is None else start + length
    ends = (y_origin + slope * low, y_origin + slope * high)
    return min(ends) <= y <= max(ends)


def _where(wing: Wing, index: int, position: int) -> str:
    return f"wing {wing.name!r}, x_secs[{index}].spare_list[{position}]"


def _front_spar(
    wing: Wing, index: int, present: list[tuple[int, SpareDetail]]
) -> tuple[int, SpareDetail]:
    """The front spar of the spars present at a station: the smallest chordwise position."""
    if len(present) == 1:
        return present[0]
    ranked = [
        (spar.spare_position_factor, position)
        for position, spar in present
        if spar.spare_position_factor is not None and math.isfinite(spar.spare_position_factor)
    ]
    if len(ranked) < len(present) or len({factor for factor, _ in ranked}) < len(ranked):
        listed = ", ".join(
            f"spar {position} (position {spar.spare_position_factor})" for position, spar in present
        )
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "front_spar_not_determinable",
            f"The front spar of wing {wing.name!r}, x_secs[{index}] cannot be told: {listed} are "
            "present at the station and their spare_position_factor is missing, not a number or "
            "not distinct.",
            "Give every spar a distinct spare_position_factor; the front spar carries the "
            "bending alone (BR-W16).",
            detail={
                "wing": wing.name,
                "x_sec": index,
                "spars": [position for position, _ in present],
            },
            parameter="airplane",
        )
    front_position = min(ranked)[1]
    return next(item for item in present if item[0] == front_position)


def _strength(
    wing: Wing,
    index: int,
    position: int,
    spar: SpareDetail,
    materials: Mapping[str, Material] | None,
) -> float:
    """The breaking strength in bending of the spar's material, or a declared failure."""
    where = _where(wing, index, position)
    detail: dict[str, JsonValue] = {"wing": wing.name, "x_sec": index, "spar": position}
    if spar.material is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "spar_material_missing",
            f"The spar at {where} has a section but no material.",
            "Name the spar's material (`material`), whose strength the components carry.",
            detail=detail,
            parameter="airplane",
        )
    material = None if materials is None else materials.get(spar.material)
    if material is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "spar_material_unknown",
            f"The spar at {where} names the material {spar.material!r}, which the pushed "
            "components do not hold.",
            "Push the material in components.materials under this key, or correct the key.",
            detail=detail | {"material": spar.material},
            parameter="components",
        )
    if material.bending_strength_pa is None:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "spar_material_without_strength",
            f"The material {spar.material!r} of the spar at {where} has no bending strength.",
            "Push its published breaking strength in bending (bending_strength_pa); "
            "the kernel does not estimate it.",
            detail=detail | {"material": spar.material},
            parameter="components",
        )
    return material.bending_strength_pa


def bending_capacity(
    wing: Wing, y: float, materials: Mapping[str, Material] | None
) -> SparCapacity:
    """Bending capacity ``M_cap = W * sigma`` of the wing's front spar at station ``y``.

    Implements the capacity of the canon formula ``spar-break-load-factor`` (reader: gh-1429).

    Args:
        wing: The wing; its ribs' leading-edge ``y`` define the segments, metres.
        y: Spanwise station on the stored half of the wing, metres.
        materials: The pushed materials by key, or ``None`` if none are pushed.

    Returns:
        :class:`BendingCapacity` (``M_cap`` in N*m), :class:`NoSparAtStation` if no spar is
        present at ``y``, or :class:`CapacityUnknown` if the front spar present there has no
        ``section``.

    Raises:
        FormulaError: ``station_outside_wing`` for a station outside the first and last rib or not
            a number; ``spar_material_missing``, ``spar_material_unknown``,
            ``spar_material_without_strength`` for a front spar with a section whose material
            cannot be resolved; ``front_spar_not_determinable`` for several spars present with
            no distinct positions; ``spar_extent_not_determinable`` for a partial extent that
            cannot be placed.
    """
    index = _segment_at(wing, y)
    present = [
        (position, spar)
        for position, spar in enumerate(wing.x_secs[index].spare_list or ())
        if _present_at(wing, index, position, spar, y)
    ]
    if not present:
        return NoSparAtStation(wing=wing.name, y=y)
    position, front = _front_spar(wing, index, present)
    if front.section is None:
        return CapacityUnknown(
            wing=wing.name,
            x_sec=index,
            spar=position,
            reason="front_spar_without_section",
        )
    strength = _strength(wing, index, position, front, materials)
    return BendingCapacity(moment_nm=section_modulus(front.section) * strength)
