"""The fuselages of an airplane as AVL bodies (ARCHITECTURE ch. 8.8; canon ``lateral-static-stability-*``).

AVL models a body as a source and doublet line on a straight axis, with a round cross-section whose
diameter is the difference of the upper and lower values of the body file (``avl_doc.txt:1018-1025``):
"bodies which are not round must be approximated with an equivalent round body which has roughly the
same cross-sectional areas". This module does exactly that and nothing else: each fuselage becomes one
round body of the area-equivalent radius at every section, on the axis through the area-weighted
centre of its sections. The substitution is declared by the adapter (ADR 0020).
"""

import math
from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, Fuselage, FuselageXSecSuperEllipse
from pydantic import BaseModel, ConfigDict

__all__ = ["MeshBody", "body_file_text", "equivalent_radius", "mesh_bodies"]


class MeshBody(BaseModel):
    """One fuselage as an AVL body.

    Attributes:
        name: The fuselage's name.
        origin: The nose point (x, y, z) in m: the first section's x and the body axis' y and z.
        stations: Pairs ``(distance from the nose, radius)`` in m, the distance strictly rising.
        axis_offset: The largest distance of a section centre from the straight axis in m, the
            size of the straightening.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    origin: tuple[float, float, float]
    stations: tuple[tuple[float, float], ...]
    axis_offset: float


def _half_area_factor(exponent: float) -> float:
    """``Gamma(1 + 1/n)^2 / Gamma(1 + 2/n)``: the area of a half super-ellipse is ``2 a b`` times it."""
    return math.gamma(1.0 + 1.0 / exponent) ** 2 / math.gamma(1.0 + 2.0 / exponent)


def section_area(section: FuselageXSecSuperEllipse) -> float:
    """The area of a super-ellipse section in m^2, upper and lower half with their own exponents.

    The outline is ``|y/a|^n + |z/b|^n = 1`` with ``n`` for ``z >= 0`` and ``n_lower`` below; a full
    super-ellipse has the area ``4 a b Gamma(1 + 1/n)^2 / Gamma(1 + 2/n)``, each half contributes half.
    """
    lower = section.n if section.n_lower is None else section.n_lower
    return 2.0 * section.a * section.b * (_half_area_factor(section.n) + _half_area_factor(lower))


def equivalent_radius(section: FuselageXSecSuperEllipse) -> float:
    """The radius in m of the round section of the same area as ``section``."""
    return math.sqrt(section_area(section) / math.pi)


def _body(fuselage: Fuselage) -> MeshBody:
    """One fuselage as a body: raises ``FormulaError`` for a mirrored one or sections at one x."""
    if fuselage.symmetric:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the fuselage {fuselage.name!r} is mirrored; the body of the vortex lattice is on the "
            "centre line",
            "give both halves as separate fuselages, or one body on the centreline",
            detail={"fuselage": fuselage.name},
            parameter="airplane",
        )
    sections = sorted(fuselage.x_secs, key=lambda s: s.xyz[0])
    if any(outer.xyz[0] <= inner.xyz[0] for inner, outer in pairwise(sections)):
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the fuselage {fuselage.name!r} has two sections at the same x",
            "give every section of a fuselage its own x",
            detail={"fuselage": fuselage.name},
            parameter="airplane",
        )
    areas = [section_area(s) for s in sections]
    total = sum(areas)
    if not total > 0.0:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the fuselage {fuselage.name!r} has no cross-section area",
            "give a fuselage sections with a non-zero width and height",
            detail={"fuselage": fuselage.name},
            parameter="airplane",
        )
    axis_y = sum(a * s.xyz[1] for a, s in zip(areas, sections, strict=True)) / total
    axis_z = sum(a * s.xyz[2] for a, s in zip(areas, sections, strict=True)) / total
    nose = sections[0].xyz[0]
    return MeshBody(
        name=fuselage.name,
        origin=(nose, axis_y, axis_z),
        stations=tuple((s.xyz[0] - nose, equivalent_radius(s)) for s in sections),
        axis_offset=max(math.hypot(s.xyz[1] - axis_y, s.xyz[2] - axis_z) for s in sections),
    )


def mesh_bodies(airplane: AirplaneGeometry) -> tuple[MeshBody, ...]:
    """Every fuselage of the airplane as an AVL body, in document order.

    Args:
        airplane: The validated geometry document.

    Returns:
        The bodies; empty for an airplane without fuselages.

    Raises:
        FormulaError: ``unsupported_configuration`` for a mirrored fuselage, one with two sections at
            the same x, or one without a cross-section area.
    """
    return tuple(_body(fuselage) for fuselage in (airplane.fuselages or {}).values())


def body_file_text(body: MeshBody) -> str:
    """The body file: the outline in the order of an airfoil file, tail to nose over the top and back.

    The upper values are the radius, the lower values its negative, so AVL's diameter (the difference
    of the two) is twice the radius (``avl_doc.txt:1018-1025``).

    Args:
        body: The body.

    Returns:
        The file text, one ``x y`` pair per line after the name line.
    """
    upper = [(x, r) for x, r in reversed(body.stations)]
    lower = [(x, -r) for x, r in body.stations[1:]]
    rows = "\n".join(f"{x:.8f} {y:.8f}" for x, y in [*upper, *lower])
    return f"{body.name}\n{rows}\n"
