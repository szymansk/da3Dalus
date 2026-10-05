"""Fuselage cross-section with its own exponent below the centre line (gh-1157).

A ``FuselageXSecSuperEllipseSchema`` with ``n_lower`` set describes two
half super-ellipses that share the half-axes ``a`` and ``b``::

    z >= 0:  |y/a|^n       + |z/b|^n       = 1
    z <  0:  |y/a|^n_lower + |z/b|^n_lower = 1

Both halves meet at ``(±a, 0)``, so the outline stays closed. This is how
a body that is boxy underneath and rounded on top is written down (the
OpenVSP super-ellipse with ``Super_TopBotSym = false``).

AeroSandbox only knows one exponent per section. ``SplitSuperEllipseFuselageXSec``
subclasses ``asb.FuselageXSec`` and overrides the two methods that read the
exponent and depend on the half: ``get_3D_coordinates`` (outline, mesh) and
``xsec_perimeter`` (wetted area). ``shape`` carries the **area-equivalent**
exponent, so ASB's own ``xsec_area`` - and every consumer that only reads
``shape`` (ASB section interpolation in ``subdivide_sections``/``add_loft``,
the frozen ``FuselageConfiguration`` serialiser) - keeps the section area,
which is what the drag build-up depends on. Only the outline detail of such
a consumer is lost, never the size.
"""

from __future__ import annotations

import aerosandbox.numpy as np
from aerosandbox import FuselageXSec

# ASB's closed-form area approximation: area = w * h / (s**-K + 1),
# exact at s = 1, s = 2 and s -> inf (``FuselageXSec.xsec_area``).
_ASB_AREA_K = 1.8717618013591173


def _area_fraction(shape: float) -> float:
    return 1.0 / (shape**-_ASB_AREA_K + 1.0)


def area_equivalent_exponent(n_upper: float, n_lower: float) -> float:
    """Single exponent whose super-ellipse has the same area as the split one.

    Each half contributes half of the area of its full super-ellipse, so the
    area fraction of the split section is the mean of both fractions; ASB's
    area law then inverts in closed form.
    """
    if n_upper == n_lower:
        return float(n_upper)
    mean_fraction = 0.5 * (_area_fraction(n_upper) + _area_fraction(n_lower))
    return float((1.0 / mean_fraction - 1.0) ** (-1.0 / _ASB_AREA_K))


class SplitSuperEllipseFuselageXSec(FuselageXSec):
    """``asb.FuselageXSec`` with separate exponents above and below the centre."""

    def __init__(self, *, shape_upper: float, shape_lower: float, **kwargs):
        kwargs.pop("shape", None)
        super().__init__(
            shape=area_equivalent_exponent(shape_upper, shape_lower),
            **kwargs,
        )
        self.shape_upper = float(shape_upper)
        self.shape_lower = float(shape_lower)

    def __repr__(self) -> str:
        return (
            f"SplitSuperEllipseFuselageXSec (xyz_c: {self.xyz_c}, width: {self.width}, "
            f"height: {self.height}, shape_upper: {self.shape_upper}, "
            f"shape_lower: {self.shape_lower})"
        )

    def _half(self, shape: float) -> FuselageXSec:
        return FuselageXSec(
            xyz_c=self.xyz_c,
            xyz_normal=self.xyz_normal,
            width=self.width,
            height=self.height,
            shape=shape,
        )

    def xsec_perimeter(self):
        # Each half is exactly half the perimeter of its own full super-ellipse.
        return 0.5 * (
            self._half(self.shape_upper).xsec_perimeter()
            + self._half(self.shape_lower).xsec_perimeter()
        )

    def get_3D_coordinates(self, theta=None):
        if theta is None:
            theta = np.linspace(0, 2 * np.pi, 60 + 1)[:-1]
        upper = self._half(self.shape_upper).get_3D_coordinates(theta)
        lower = self._half(self.shape_lower).get_3D_coordinates(theta)
        is_upper = np.sin(np.mod(theta, 2 * np.pi)) >= 0
        return tuple(
            np.where(is_upper, top, bottom) for top, bottom in zip(upper, lower, strict=True)
        )
