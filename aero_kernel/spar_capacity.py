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

How the document is read (format ch. 5, version 3):

* **Bending axis.** The spar bends about the chordwise axis. ``height`` of a section is measured in
  the airfoil thickness direction, ``width`` across the chord; ``W = I / (h / 2)``. Rod and tube
  are symmetric. The capacity is the same upward and downward: one strength, no distinction
  between tension and compression.
* **Spanwise extent.** The spars of a segment (the ribs ``i`` and ``i + 1``) are consulted only at
  stations of that segment: a station belongs to the segment with ``y_i <= y < y_(i+1)`` of the
  ribs' leading-edge ``y`` (the last segment also owns its outer rib). So a spar that continues
  through several segments (``*_backward``, ``follow``) is counted once, by the entry of the
  segment that contains the station. Within a segment the spar exists over
  ``spare_start`` to ``spare_start + spare_length`` metres, ``None`` meaning to the end of the
  segment, measured along the straight line between the two leading-edge points of the segment
  and projected on ``y``. A length beyond the segment has no effect outside it.
* **Which spar bends the wing.** BR-W16: the front spar alone carries the bending, the rear one
  the torsion, so the capacities of several spars are **not added**. The front spar is the one
  present at the station with the smallest ``spare_position_factor``; if that cannot be told (a
  missing or equal position among several spars) the station fails. A front spar without
  ``section`` gives no capacity; the rear spar does not stand in for it.
"""

import math
from collections.abc import Mapping

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
from pydantic import JsonValue

# UNREACHABLE(gh-1429): no production module imports this one yet.
__all__ = ["bending_capacity", "section_modulus"]


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


def _segment_at(wing: Wing, y: float) -> int | None:
    """Index of the segment that owns station ``y``, or ``None`` outside the wing."""
    ribs = wing.x_secs
    last = len(ribs) - 2
    for index in range(last + 1):
        y_root, y_tip = ribs[index].xyz_le[1], ribs[index + 1].xyz_le[1]
        low, high = min(y_root, y_tip), max(y_root, y_tip)
        if low <= y < high or (index == last and y == high and low < high):
            return index
    return None


def _present_at(wing: Wing, index: int, spar: SpareDetail, y: float) -> bool:
    """Whether the spar of segment ``index`` exists at station ``y`` (already inside the segment)."""
    root, tip = wing.x_secs[index].xyz_le, wing.x_secs[index + 1].xyz_le
    line = math.dist(root, tip)  # > 0: a segment owns stations only if its ribs differ in y
    y_per_metre = (tip[1] - root[1]) / line
    end = line if spar.spare_length is None else spar.spare_start + spar.spare_length
    ends = (root[1] + y_per_metre * spar.spare_start, root[1] + y_per_metre * end)
    return min(ends) <= y <= max(ends)


def _where(wing: Wing, index: int, position: int) -> str:
    return f"wing {wing.name!r}, x_secs[{index}].spare_list[{position}]"


def _front_spar(
    wing: Wing, index: int, present: list[tuple[int, SpareDetail]]
) -> tuple[int, SpareDetail]:
    """The front spar of the spars present at a station: the smallest chordwise position."""
    if len(present) == 1:
        return present[0]
    factors = [spar.spare_position_factor for _, spar in present]
    known = [factor for factor in factors if factor is not None]
    if len(known) < len(factors) or known.count(min(known)) > 1:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "front_spar_not_determinable",
            f"The front spar of wing {wing.name!r}, x_secs[{index}] cannot be told: several spars "
            "are present at the station and their spare_position_factor is missing or not unique.",
            "Give every spar a distinct spare_position_factor; the front spar carries the "
            "bending alone (BR-W16).",
            detail={"wing": wing.name, "x_sec": index},
            parameter="airplane",
        )
    return min(present, key=lambda item: item[1].spare_position_factor or 0.0)


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
) -> float | None:
    """Bending capacity ``M_cap = W * sigma`` of the wing's front spar at station ``y``.

    Implements the capacity of the canon formula ``spar-break-load-factor`` (reader: gh-1429).

    Args:
        wing: The wing; its ribs' leading-edge ``y`` define the segments, metres.
        y: Spanwise station on the stored half of the wing, metres.
        materials: The pushed materials by key, or ``None`` if none are pushed.

    Returns:
        ``M_cap`` in N*m, or ``None`` if no spar with a section is the front spar at ``y`` (no
        spar there, or the front spar has no ``section``).

    Raises:
        FormulaError: ``spar_material_missing``, ``spar_material_unknown``,
            ``spar_material_without_strength`` for a front spar with a section whose material
            cannot be resolved; ``front_spar_not_determinable`` for several spars with no
            distinct chordwise positions.
    """
    index = _segment_at(wing, y)
    if index is None:
        return None
    present = [
        (position, spar)
        for position, spar in enumerate(wing.x_secs[index].spare_list or ())
        if _present_at(wing, index, spar, y)
    ]
    if not present:
        return None
    position, front = _front_spar(wing, index, present)
    if front.section is None:
        return None
    return section_modulus(front.section) * _strength(wing, index, position, front, materials)
