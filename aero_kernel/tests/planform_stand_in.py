"""A planform integration without AeroSandbox: the stand-in for the GEO adapter in the fast tier.

The production values are AeroSandbox's (``solvers.asb_airplane``, gh-1253); fast tests need
consistent numbers only, so the GEO stub answers with this deterministic integration of the sections
(projected onto the x-y plane, a mirrored surface carried to the centreline). It is not a second
producer in the kernel: it lives in the tests, and the aero tier compares the real adapter with ASB.
"""

from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Wing
from aero_kernel.geometry_properties import SurfaceProperties
from aero_kernel.surface_chain import oriented_chain

__all__ = ["stand_in_surface_properties"]

# A point of the planform chain: y, chord, x of the leading edge (all in m).
_Point = tuple[float, float, float]
# A panel: dy, chords c1 and c2, leading-edge x1 and x2.
_Panel = tuple[float, float, float, float, float]


def _unsupported(message: str, hint: str, wing: str) -> FormulaError:
    """The error of a surface whose planform cannot be integrated."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        message,
        hint,
        detail={"wing": wing},
        parameter="airplane",
    )


def _panels(chain: list[_Point], symmetric: bool) -> tuple[list[_Panel], float]:
    """The panels of the planform and its half span.

    A mirrored surface is carried to the centreline: a root off y = 0 is extended to it with the root
    chord and leading edge, and a side that crosses y = 0 is clipped there.

    Returns:
        The panels ``(dy, c1, c2, x1, x2)`` and the y extent of the half planform.
    """
    if not symmetric:
        panels = [(y2 - y1, c1, c2, x1, x2) for (y1, c1, x1), (y2, c2, x2) in pairwise(chain)]
        return panels, chain[-1][0] - chain[0][0]
    panels: list[_Panel] = []
    if chain[0][0] > 0.0:
        panels.append((chain[0][0], chain[0][1], chain[0][1], chain[0][2], chain[0][2]))
    for (y1, c1, x1), (y2, c2, x2) in pairwise(chain):
        low = max(y1, 0.0)
        if y2 > low:
            share = (low - y1) / (y2 - y1)
            panels.append((y2 - low, c1 + (c2 - c1) * share, c2, x1 + (x2 - x1) * share, x2))
    return panels, max(chain[-1][0], 0.0)


def stand_in_surface_properties(wing: Wing) -> SurfaceProperties:
    """Return the planform values of one surface, projected onto the x-y plane.

    The definition (maintainer, 2026-10-22): the sections' chords and leading edges as given,
    projected onto the x-y plane, panel by panel (so a polyhedral wing works); twist does not
    change it. A mirrored surface is carried to the centreline (team-lead, 2026-10-23): a root off
    the plane is extended to y = 0 with the root chord, and a stored side that crosses y = 0 is
    clipped there, so the span is ``2 max|y|``. A surface that is not mirrored keeps its stored
    extent ``max y - min y``, with no extension. The neutral point's wing and tail terms come from
    here (the reference values of the main wing are AeroSandbox's, not these).

    ``x_le_MAC`` has no AeroSandbox counterpart. Per panel, with ``dy`` its y extent, chords ``c1``,
    ``c2`` and leading edges ``x1``, ``x2``:

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
        The planform values in m^2, m, 1, m, m.

    Raises:
        FormulaError: ``unsupported_configuration`` if the sections fold back in y or the surface
            has no projected area (all its sections at one y).
    """
    chain = [(p.y, p.chord, p.x) for p in oriented_chain(wing, 1)]
    panels, half_span = _panels(chain, wing.symmetric)
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
    )
