"""The equivalent dihedral of a polyhedral wing, canon ``spiral-parameter`` (ARCHITECTURE ch. 8.5).

The canon derives it by strip theory (maintainer 2026-10-26, #1309): every strip of the semi-span
contributes to the dihedral effect in proportion to its chord and its distance from the centre line,
so ``Gamma_eq = int Gamma(y) c(y) y dy / int c(y) y dy`` over the semi-span of the main wing. The
weights are integrals of a quadratic, closed in each panel; nothing is integrated numerically.
"""

import math
from itertools import pairwise

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, Wing
from aero_kernel.surface_chain import ChainPoint, oriented_chain

__all__ = ["equivalent_dihedral_deg", "main_wing_dihedral_deg"]


def _panel_weight(inner: ChainPoint, outer: ChainPoint) -> float:
    """``int c(y) y dy`` over one panel, the chord linear in y between the two ribs, in m^3.

    With ``c = c1 + s (y - y1)``: ``c1 (y2^2 - y1^2) / 2 + s ((y2^3 - y1^3) / 3 - y1 (y2^2 - y1^2) / 2)``.
    """
    span = outer.y - inner.y
    if span <= 0.0:
        return 0.0
    slope = (outer.chord - inner.chord) / span
    square = (outer.y**2 - inner.y**2) / 2.0
    cube = (outer.y**3 - inner.y**3) / 3.0
    return inner.chord * square + slope * (cube - inner.y * square)


def equivalent_dihedral_deg(wing: Wing) -> float:
    """The strip-theory equivalent dihedral of a mirrored wing in degrees, positive tips up.

    The panel dihedral is the angle of the panel's leading-edge line to the horizontal in the y-z
    plane, ``atan2(dz, dy)``. The weighting starts at the root rib: a gap at the centre line has no
    wing and so no weight. Sweep and the coupling between strips are neglected, as the canon states.

    Args:
        wing: The main wing, a mirrored surface.

    Returns:
        ``Gamma_eq`` in degrees.

    Raises:
        FormulaError: ``unsupported_configuration`` (``unsupported_layout``) for a wing that is not
            mirrored, which has no semi-span to weigh; (``unsupported_configuration``) for a wing
            without a span, or whose sections fold back along y.
    """
    if not wing.symmetric:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_layout",
            f"the equivalent dihedral weighs the semi-span of a mirrored main wing; {wing.name!r} "
            "is not mirrored",
            "give the main wing as one half with the mirrored flag set",
            detail={"wing": wing.name},
            parameter="airplane",
        )
    chain = oriented_chain(wing, 1)
    weighted = total = 0.0
    for inner, outer in pairwise(chain):
        weight = _panel_weight(inner, outer)
        dihedral = math.degrees(math.atan2(outer.z - inner.z, outer.y - inner.y))
        weighted += weight * dihedral
        total += weight
    if total <= 0.0:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the wing {wing.name!r} has no span to weigh: its sections all lie at one y",
            "a wing needs sections at different y",
            detail={"wing": wing.name},
            parameter="airplane",
        )
    return weighted / total


def main_wing_dihedral_deg(airplane: AirplaneGeometry) -> float:
    """The equivalent dihedral of the one wing with ``surface_type`` ``main_wing``, in degrees.

    The wing is chosen by type, never by list position.

    Args:
        airplane: The validated geometry document.

    Returns:
        ``Gamma_eq`` as :func:`equivalent_dihedral_deg`.

    Raises:
        ValueError: If the document does not have exactly one main wing (a defect of the caller:
            validation reports ``main_wing_count`` as the user-facing error).
        FormulaError: As :func:`equivalent_dihedral_deg`.
    """
    wings = [w for w in (airplane.wings or {}).values() if w.surface_type == "main_wing"]
    if len(wings) != 1:
        msg = f"validated input has exactly one main wing, got {len(wings)}"
        raise ValueError(msg)
    return equivalent_dihedral_deg(wings[0])
