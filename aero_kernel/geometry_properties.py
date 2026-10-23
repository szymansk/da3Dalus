"""Reference values of a lifting surface, integrated from the geometry (ARCHITECTURE ch. 8.5, 8.8).

GEO is a plain read of the geometry; nothing here calls a tool. Implements the procedure of the
canon formula ``airplane-geometry`` and the surface terms of ``neutral-point``. One function
(:func:`surface_properties`) serves the main wing and the tail, so there is one authority for the
mean aerodynamic chord (ADR 0022).
"""

from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, Wing
from pydantic import BaseModel, ConfigDict

__all__ = ["MainWingProperties", "SurfaceProperties", "main_wing_properties", "surface_properties"]


class MainWingProperties(BaseModel):
    """The reference values of the main wing, projected onto the x-y plane.

    Attributes:
        s_ref: Reference area in m^2 (canon quantity ``wing-reference-area``).
        b_ref: Reference span in m (``wing-span``).
        c_mac: Mean aerodynamic chord in m (``mean-aerodynamic-chord``).
        extended_m: Length in m by which the root was extended to y = 0 with the root chord.
        clipped_m: Length in m of the stored side that was clipped away at y = 0.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    s_ref: float
    b_ref: float
    c_mac: float
    extended_m: float = 0.0
    clipped_m: float = 0.0


class SurfaceProperties(BaseModel):
    """Area, span, aspect ratio and mean aerodynamic chord of one surface, projected onto x-y.

    Attributes:
        area: Planform area in m^2 (both halves of a mirrored surface).
        span: Span in m (``2 max|y|`` for a mirrored surface).
        aspect_ratio: ``span^2 / area``.
        c_mac: Mean aerodynamic chord in m.
        x_le_mac: x of the leading edge of the mean aerodynamic chord in m (the chord-weighted
            leading edge), in the geometry frame, aft positive.
        extended_m: Length in m by which the root was extended to y = 0 with the root chord.
        clipped_m: Length in m of the stored side that was clipped away at y = 0.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    area: float
    span: float
    aspect_ratio: float
    c_mac: float
    x_le_mac: float
    extended_m: float = 0.0
    clipped_m: float = 0.0


# A point of the planform chain: y, chord, x of the leading edge (all in m).
_Point = tuple[float, float, float]
# A panel: dy, chords c1 and c2, leading-edge x1 and x2.
_Panel = tuple[float, float, float, float, float]


def _unsupported(message: str, hint: str, wing: str) -> FormulaError:
    """The error of a surface whose planform the reference values cannot be taken from."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        message,
        hint,
        detail={"wing": wing},
        parameter="airplane",
    )


def _outboard_chain(points: list[_Point], symmetric: bool, name: str) -> list[_Point]:
    """Orient the (y, chord, x_le) chain so y never decreases from the root outwards.

    The chain is reversed if it runs from the tip inwards, and a mirrored wing stored on the
    negative side is mirrored to y >= 0 (outermost section at y > 0).

    Raises:
        FormulaError: ``unsupported_configuration`` if the chain folds back in y.
    """
    oriented = points[::-1] if points[-1][0] < points[0][0] else points
    if symmetric and max(oriented, key=lambda point: abs(point[0]))[0] < 0.0:
        oriented = [(-y, c, x) for y, c, x in oriented][::-1]
    if any(outer[0] < inner[0] for inner, outer in pairwise(oriented)):
        raise _unsupported(
            f"the sections of the wing {name!r} fold back in y",
            "order the sections from the root outwards without doubling back in y",
            name,
        )
    return oriented


def _panels(chain: list[_Point], symmetric: bool) -> tuple[list[_Panel], float, float, float]:
    """The panels of the reference planform, its half span, and what the centreline convention did.

    A mirrored surface is carried to the centreline: a root off y = 0 is extended to it with the root
    chord and leading edge, and a side that crosses y = 0 is clipped there.

    Returns:
        The panels ``(dy, c1, c2, x1, x2)``, the y extent of the half planform, the length by which
        the root was extended and the length of the stored side that was clipped away.
    """
    if not symmetric:
        panels = [(y2 - y1, c1, c2, x1, x2) for (y1, c1, x1), (y2, c2, x2) in pairwise(chain)]
        return panels, chain[-1][0] - chain[0][0], 0.0, 0.0
    panels: list[_Panel] = []
    extended = 0.0
    if chain[0][0] > 0.0:
        extended = chain[0][0]
        panels.append((extended, chain[0][1], chain[0][1], chain[0][2], chain[0][2]))
    for (y1, c1, x1), (y2, c2, x2) in pairwise(chain):
        low = max(y1, 0.0)
        if y2 > low:
            share = (low - y1) / (y2 - y1)
            panels.append((y2 - low, c1 + (c2 - c1) * share, c2, x1 + (x2 - x1) * share, x2))
    return panels, max(chain[-1][0], 0.0), extended, max(-chain[0][0], 0.0)


def surface_properties(wing: Wing) -> SurfaceProperties:
    """Return the planform values of one surface, projected onto the x-y plane.

    The definition (maintainer, 2026-10-22): the sections' chords and leading edges as given,
    projected onto the x-y plane, panel by panel (so a polyhedral wing works); twist does not
    change it. A mirrored surface is carried to the centreline (team-lead, 2026-10-23): a root off
    the plane is extended to y = 0 with the root chord, and a stored side that crosses y = 0 is
    clipped there, so the span is ``2 max|y|``. A surface that is not mirrored keeps its stored
    extent ``max y - min y``, with no extension. The main wing's S_ref, b_ref and c_MAC and the
    neutral point's tail terms come from here.

    AeroSandbox's ``Wing.area("projected")`` and ``Wing.span("y")`` are not used: they measure
    along the quarter-chord line, whose y depends on twist (BRYAN: S_ref -0.05 %), and
    ``Wing.mean_aerodynamic_chord()`` weights panels by their slant area. Per panel, with ``dy`` its
    y extent, chords ``c1``, ``c2`` and leading edges ``x1``, ``x2``:

    - area ``dy (c1 + c2) / 2``, ``integral c^2 dy = dy (c1^2 + c1 c2 + c2^2) / 3``,
      ``integral c x_le dy = dy (c1 x1 / 3 + (c1 x2 + c2 x1) / 6 + c2 x2 / 3)``;
    - ``c_MAC = integral(c^2 dy) / integral(c dy)`` over the half planform, which is
      ``(2/S) integral(c^2 dy)`` over the half wing;
    - ``x_le_MAC = integral(c x_le dy) / integral(c dy)``, the chord-weighted leading edge: the
      leading edge at the spanwise station of the MAC.

    No external tool is called, so this needs no AeroSandbox.

    Args:
        wing: One surface of a validated geometry document.

    Returns:
        The planform values in m^2, m, 1, m, m, with the lengths the centreline convention changed.

    Raises:
        FormulaError: ``unsupported_configuration`` if the sections fold back in y or the surface
            has no projected area (all its sections at one y).
    """
    chain = _outboard_chain(
        [(s.xyz_le[1], s.chord, s.xyz_le[0]) for s in wing.x_secs], wing.symmetric, wing.name
    )
    panels, half_span, extended, clipped = _panels(chain, wing.symmetric)
    area = sum(dy * (c1 + c2) / 2.0 for dy, c1, c2, _x1, _x2 in panels)
    squares = sum(dy * (c1 * c1 + c1 * c2 + c2 * c2) / 3.0 for dy, c1, c2, _x1, _x2 in panels)
    moment = sum(
        dy * (c1 * x1 / 3.0 + (c1 * x2 + c2 * x1) / 6.0 + c2 * x2 / 3.0)
        for dy, c1, c2, x1, x2 in panels
    )
    if area <= 0.0:
        raise _unsupported(
            f"the wing {wing.name!r} has no area projected onto the x-y plane",
            "a surface needs sections at different y; a vertical surface has no projected planform",
            wing.name,
        )
    mirrored = 2.0 if wing.symmetric else 1.0
    return SurfaceProperties(
        area=mirrored * area,
        span=mirrored * half_span,
        aspect_ratio=(mirrored * half_span) ** 2 / (mirrored * area),
        c_mac=squares / area,
        x_le_mac=moment / area,
        extended_m=extended,
        clipped_m=clipped,
    )


def main_wing_properties(airplane: AirplaneGeometry) -> MainWingProperties:
    """Return ``S_ref``, ``b_ref`` and ``c_MAC`` of the one wing with ``surface_type`` ``main_wing``.

    The values are those of :func:`surface_properties` for that wing (the definition is stated
    there); ``extended_m`` and ``clipped_m`` report the length by which the centreline convention
    changed the planform, so the caller can declare it (ADR 0020).

    Args:
        airplane: The validated geometry document, which has exactly one main wing.

    Returns:
        The three reference values in m^2, m and m.

    Raises:
        ValueError: If the document does not have exactly one main wing (a defect: validation
            reports ``main_wing_count`` as the user-facing error).
        FormulaError: As :func:`surface_properties`.
    """
    main = [wing for wing in (airplane.wings or {}).values() if wing.surface_type == "main_wing"]
    if len(main) != 1:
        msg = f"validated input has exactly one main wing, got {len(main)}"
        raise ValueError(msg)
    surface = surface_properties(main[0])
    return MainWingProperties(
        s_ref=surface.area,
        b_ref=surface.span,
        c_mac=surface.c_mac,
        extended_m=surface.extended_m,
        clipped_m=surface.clipped_m,
    )
