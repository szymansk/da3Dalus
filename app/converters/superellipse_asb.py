"""The one conversion from a super-ellipse section to an AeroSandbox section (gh-1146, Q-FD-3).

``FuselageXSecSuperEllipseSchema`` stores the **half-axes** ``a`` (Y, lateral) and ``b``
(Z, vertical) of ``|y/a|^n + |z/b|^n = 1`` (BR-F1). AeroSandbox's ``FuselageXSec`` takes
the **full** ``width`` and ``height`` and evaluates ``width / 2`` and ``height / 2`` itself
(``aerosandbox/geometry/fuselage.py``, ASB 4.2.9). The factor two is geometry, not a unit
conversion, and it lives here only: every app path that hands a super-ellipse section to
AeroSandbox goes through :func:`superellipse_to_asb_xsec`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aerosandbox import FuselageXSec

# Full dimension over half-axis: a super-ellipse spans -a..+a laterally and -b..+b vertically.
FULL_OVER_HALF_AXIS = 2.0

# Every super-ellipse section lies in the Y-Z plane, normal to the fuselage axis X.
_SECTION_NORMAL = (1.0, 0.0, 0.0)


def superellipse_to_asb_xsec(
    *,
    xyz: Sequence[float],
    a: float,
    b: float,
    n: float,
    n_lower: Optional[float] = None,
) -> FuselageXSec:
    """Build the ASB section of one super-ellipse: ``width = 2a``, ``height = 2b``.

    A section whose ``n_lower`` differs from ``n`` becomes a split super-ellipse (gh-1157)
    with the same full width and height.
    """
    # Imported here so that the constant above stays importable without AeroSandbox
    # (platform guard; the plausibility service reuses it).
    from aerosandbox import FuselageXSec

    from app.converters.split_superellipse import SplitSuperEllipseFuselageXSec

    common = {
        "xyz_c": [float(value) for value in xyz],
        "xyz_normal": list(_SECTION_NORMAL),
        "radius": None,
        "width": FULL_OVER_HALF_AXIS * float(a),
        "height": FULL_OVER_HALF_AXIS * float(b),
    }
    if n_lower is None or float(n_lower) == float(n):
        return FuselageXSec(shape=float(n), **common)
    return SplitSuperEllipseFuselageXSec(shape_upper=float(n), shape_lower=float(n_lower), **common)
