"""The role of a body and the body it sits on (#1355, slice 1).

Every body under ``fuselages`` carries a ``role`` (``fuselage``, ``canopy``, ``nacelle``,
``fairing``, ``pod``, ``other``) and optionally ``attached_to``, the name of the body it sits on.
The role is stated by the writer, never inferred from a name (ADR 0020). The rules (canon rule
``body-attachment``):

1. ``attached_to``, when set, names another body of the same aircraft; the chain of
   ``attached_to`` has no cycle;
2. a canopy has ``attached_to``, and its parent is no canopy (slice 2: the merge folds every
   canopy into one parent);
3. a canopy's x range (the smallest to the largest ``xyz[0]`` of its sections) lies inside its
   parent's, ends included.

Rule 3 compares only bodies that have a loft, at least ``min_sections`` sections with finite
positions: a body with fewer is refused by ``too_few_sections``, a non-finite position by the walk
over the numbers. These functions are pure and know no thresholds; the caller passes the canon's.
The solvers see each canopy merged into its parent (:mod:`aero_kernel.solver_bodies`, slice 2).
"""

import math
from collections.abc import Mapping
from typing import Literal, NamedTuple

__all__ = ["AttachedBody", "AttachmentDefect", "attachment_defects"]

AttachmentCode = Literal["invalid_body_attachment", "canopy_outside_parent"]


class AttachedBody(NamedTuple):
    """What the attachment rules read of one body.

    Attributes:
        role: The body's role.
        attached_to: Name of the body it sits on, ``None`` if it sits on none.
        x: ``xyz[0]`` of every section in loft order, metres.
    """

    role: str
    attached_to: str | None
    x: tuple[float, ...]


class AttachmentDefect(NamedTuple):
    """Why a body's role or attachment is refused.

    Attributes:
        body: Name of the offending body.
        field: ``attached_to``, or ``x_secs`` for a canopy section outside its parent.
        section: Index of the offending section (``x_secs`` only), else ``None``.
        code: The kernel error code.
        message: The reason, naming the bodies involved.
    """

    body: str
    field: Literal["attached_to", "x_secs"]
    section: int | None
    code: AttachmentCode
    message: str


def _cycle(name: str, bodies: Mapping[str, AttachedBody]) -> list[str] | None:
    """Return the attachment chain from ``name`` back to itself, or ``None`` if it ends."""
    chain = [name]
    current = bodies[name].attached_to
    while current is not None and current in bodies and current not in chain:
        chain.append(current)
        current = bodies[current].attached_to
    if current == name and len(chain) > 1:
        return [*chain, name]
    return None


def _reference_defects(
    name: str, body: AttachedBody, bodies: Mapping[str, AttachedBody]
) -> list[AttachmentDefect]:
    """Rules 1 and 2: the parent exists, is another body and not in a cycle; a canopy has one.

    The parent of a canopy is no canopy.
    """
    parent = body.attached_to
    if parent is None:
        if body.role != "canopy":
            return []
        message = f"Body {name!r} is a canopy and needs attached_to: the body it sits on."
    elif parent == name:
        message = f"Body {name!r} is attached to itself."
    elif parent not in bodies:
        message = f"Body {name!r} is attached to {parent!r}, which is not a body of this aircraft."
    elif body.role == "canopy" and bodies[parent].role == "canopy":
        message = (
            f"Canopy {name!r} is attached to {parent!r}, itself a canopy; a canopy sits on a body "
            "that is no canopy."
        )
    else:
        cycle = _cycle(name, bodies)
        if cycle is None:
            return []
        message = f"Body {name!r} is part of the attachment cycle {' -> '.join(cycle)}."
    return [AttachmentDefect(name, "attached_to", None, "invalid_body_attachment", message)]


def _has_loft(body: AttachedBody, min_sections: int) -> bool:
    """Whether a body has an x range to compare: enough sections, all positions finite."""
    return len(body.x) >= min_sections and all(math.isfinite(x) for x in body.x)


def _range_defects(
    name: str, body: AttachedBody, bodies: Mapping[str, AttachedBody], min_sections: int
) -> list[AttachmentDefect]:
    """Rule 3: every section of a canopy lies within the x range of its parent."""
    parent_name = body.attached_to
    if body.role != "canopy" or parent_name is None or parent_name == name:
        return []
    parent = bodies.get(parent_name)
    if parent is None or not _has_loft(body, min_sections) or not _has_loft(parent, min_sections):
        return []
    start, end = min(parent.x), max(parent.x)
    defects: list[AttachmentDefect] = []
    for index in sorted({body.x.index(min(body.x)), body.x.index(max(body.x))}):
        x = body.x[index]
        if x < start:
            where = f"ahead of its parent {parent_name!r}, which starts at x = {start} m"
        elif x > end:
            where = f"behind its parent {parent_name!r}, which ends at x = {end} m"
        else:
            continue
        message = f"Section {index} of canopy {name!r} lies at x = {x} m, {where}."
        defects.append(AttachmentDefect(name, "x_secs", index, "canopy_outside_parent", message))
    return defects


def attachment_defects(
    bodies: Mapping[str, AttachedBody], min_sections: int
) -> list[AttachmentDefect]:
    """Check the roles and attachments of an aircraft's bodies (canon rule ``body-attachment``).

    Args:
        bodies: Every body of the aircraft by name, in document order.
        min_sections: The canon's ``minimum-sections.min_sections``: a body with fewer sections
            has no loft, so its x range is not compared.

    Returns:
        The defects in document order, the attachment before the range of each body.
    """
    defects: list[AttachmentDefect] = []
    for name, body in bodies.items():
        defects += _reference_defects(name, body, bodies)
        defects += _range_defects(name, body, bodies, min_sections)
    return defects
