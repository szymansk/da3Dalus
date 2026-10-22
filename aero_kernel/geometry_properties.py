"""Reference values of the main wing, integrated from the geometry (ARCHITECTURE ch. 8.5, 8.8).

GEO is a plain read of the geometry; nothing here calls a tool. Implements the procedure of the
canon formula ``airplane-geometry``.
"""

from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from pydantic import BaseModel, ConfigDict

__all__ = ["MainWingProperties", "main_wing_properties"]


class MainWingProperties(BaseModel):
    """The reference values of the main wing, projected onto the x-y plane.

    Attributes:
        s_ref: Reference area in m^2 (canon quantity ``wing-reference-area``).
        b_ref: Reference span in m (``wing-span``).
        c_mac: Mean aerodynamic chord in m (``mean-aerodynamic-chord``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    s_ref: float
    b_ref: float
    c_mac: float


def _unsupported(message: str, hint: str, wing: str) -> FormulaError:
    """The error of a main wing whose planform the reference values cannot be taken from."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        message,
        hint,
        detail={"wing": wing},
        parameter="airplane",
    )


def _outboard_chain(
    points: list[tuple[float, float]], symmetric: bool, name: str
) -> list[tuple[float, float]]:
    """Orient the (y, chord) chain so y never decreases from the root outwards.

    A mirrored wing is flipped so that its outermost section lies at y > 0; any other wing so that
    its last section has the larger y.

    Raises:
        FormulaError: ``unsupported_configuration`` if the chain folds back in y.
    """
    if symmetric:
        flip = max(points, key=lambda point: abs(point[0]))[0] < 0.0
    else:
        flip = points[-1][0] < points[0][0]
    oriented = [(-y, c) for y, c in points] if flip else points
    if any(outer[0] < inner[0] for inner, outer in pairwise(oriented)):
        raise _unsupported(
            f"the sections of the main wing {name!r} fold back in y",
            "order the sections from the root outwards without doubling back in y",
            name,
        )
    return oriented


def main_wing_properties(airplane: AirplaneGeometry) -> MainWingProperties:
    """Return ``S_ref``, ``b_ref`` and ``c_MAC`` of the one wing with ``surface_type`` ``main_wing``.

    This is the single place that fixes the definition (maintainer, 2026-10-22): the reference
    planform is the sections' chords and leading edges as given, **projected onto the x-y
    plane**, panel by panel (so a polyhedral wing works). Twist does not change it.

    A mirrored wing is carried to the centreline (team-lead, 2026-10-23): a root off the plane
    is extended to y = 0 with the root chord, and a stored side that crosses y = 0 is clipped
    there. So ``b_ref = 2 max|y|`` (tip to tip), and ``S_ref`` and ``c_MAC`` are integrated over
    0 ... max|y|. A wing that is not mirrored keeps its stored extent ``max y - min y``, with no
    extension.

    AeroSandbox's ``Wing.area("projected")`` and ``Wing.span("y")`` are not used: they measure
    along the quarter-chord line, whose y depends on twist (BRYAN: S_ref -0.05 %), and
    ``Wing.mean_aerodynamic_chord()`` weights panels by their slant area. The kernel integrates
    the sections itself. Per panel of the planform, with ``dy`` its y extent and ``c1``, ``c2``
    its chords:

    - area ``dy (c1 + c2) / 2``, ``integral c^2 dy = dy (c1^2 + c1 c2 + c2^2) / 3``;
    - ``S_ref`` and ``b_ref`` are the sums, doubled if the wing is mirrored;
    - ``c_MAC = (2/S_ref) * integral(c^2 dy)`` over the half wing, which is the integral over
      the stored side divided by the stored side's area (mirrored or not).

    No external tool is called, so this needs no AeroSandbox.

    Args:
        airplane: The validated geometry document, which has exactly one main wing.

    Returns:
        The three reference values in m^2, m and m.

    Raises:
        ValueError: If the document does not have exactly one main wing (a defect: validation
            reports ``main_wing_count`` as the user-facing error).
        FormulaError: ``unsupported_configuration`` if the sections fold back in y or the main
            wing has no projected area (all its sections at one y).
    """
    main = [wing for wing in (airplane.wings or {}).values() if wing.surface_type == "main_wing"]
    if len(main) != 1:
        msg = f"validated input has exactly one main wing, got {len(main)}"
        raise ValueError(msg)
    wing = main[0]
    chain = _outboard_chain(
        [(s.xyz_le[1], s.chord) for s in wing.x_secs], wing.symmetric, wing.name
    )
    panels: list[tuple[float, float, float]] = []  # (dy, c1, c2)
    if wing.symmetric:
        if chain[0][0] > 0.0:
            panels.append((chain[0][0], chain[0][1], chain[0][1]))
        for (y1, c1), (y2, c2) in pairwise(chain):
            low = max(y1, 0.0)
            if y2 > low:
                panels.append((y2 - low, c1 + (c2 - c1) * (low - y1) / (y2 - y1), c2))
        span = max(chain[-1][0], 0.0)
    else:
        panels = [(y2 - y1, c1, c2) for (y1, c1), (y2, c2) in pairwise(chain)]
        span = chain[-1][0] - chain[0][0]
    area = sum(dy * (c1 + c2) / 2.0 for dy, c1, c2 in panels)
    squares = sum(dy * (c1 * c1 + c1 * c2 + c2 * c2) / 3.0 for dy, c1, c2 in panels)
    if not area > 0.0:
        raise _unsupported(
            f"the main wing {wing.name!r} has no area projected onto the x-y plane",
            "a main wing needs sections at different y; a vertical surface is no main wing",
            wing.name,
        )
    mirrored = 2.0 if wing.symmetric else 1.0
    return MainWingProperties(s_ref=mirrored * area, b_ref=mirrored * span, c_mac=squares / area)
