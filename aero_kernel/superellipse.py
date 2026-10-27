"""The equivalent symmetric super-ellipse of a fuselage section with two shape exponents (gh-1307).

The geometry format lets the upper and the lower half of a section carry their own exponent, both
halves sharing the semi-axes ``a`` and ``b`` (geometry format 7.1a). AeroSandbox's ``FuselageXSec``
has one exponent. The kernel replaces such a section by a symmetric one with the same semi-axes, so
the same width, height and centre, and the one exponent that keeps the **cross-section area**.

The exponent is the one of AeroSandbox's ``shape``: ``|y/a|^n + |z/b|^n = 1``, ``n = 2`` the ellipse,
``n = 1`` the diamond, ``n -> infinity`` the rectangle. Its quadrant area is
``a b f(n)`` with ``f(n) = Gamma(1 + 1/n)^2 / Gamma(1 + 2/n)`` (AeroSandbox's ``xsec_area`` is a
closed-form approximation of exactly this, error below 0.6 %).
"""

import math

from aero_kernel.config import config

__all__ = ["equivalent_exponent", "quadrant_area_fraction"]


def quadrant_area_fraction(n: float) -> float:
    """Return the area of one quadrant of the super-ellipse of exponent ``n`` in units of ``a b``.

    ``Gamma(1 + 1/n)^2 / Gamma(1 + 2/n)``, evaluated through the logarithm of the gamma function so
    that a small exponent does not overflow.

    Args:
        n: The exponent, > 0.

    Returns:
        The fraction of the bounding-box quadrant the outline encloses, in (0, 1); 1/2 for the
        diamond, pi/4 for the ellipse, rising to 1 for the rectangle.
    """
    return math.exp(2.0 * math.lgamma(1.0 + 1.0 / n) - math.lgamma(1.0 + 2.0 / n))


def equivalent_exponent(n_upper: float, n_lower: float) -> float:
    """Return the one exponent whose symmetric section has the area of the two different halves.

    With the shared semi-axes the area of the section with two halves is
    ``2 a b (f(n_upper) + f(n_lower))`` and that of the symmetric one ``4 a b f(n)``, so the
    equivalent exponent solves ``f(n) = (f(n_upper) + f(n_lower)) / 2`` independently of ``a`` and
    ``b``. ``f`` rises strictly with ``n``, so the root lies between the two exponents; it is found
    by bisection to the relative area tolerance of the kernel configuration.

    Args:
        n_upper: Exponent of the upper half, > 0.
        n_lower: Exponent of the lower half, > 0.

    Returns:
        The equivalent exponent; ``n_upper`` itself if both are equal.
    """
    if n_upper == n_lower:
        return n_upper
    tolerance = config().opt_fuselage_area_tolerance.value
    low, high = sorted((n_upper, n_lower))
    target = (quadrant_area_fraction(n_upper) + quadrant_area_fraction(n_lower)) / 2.0
    while True:
        middle = (low + high) / 2.0
        error = quadrant_area_fraction(middle) / target - 1.0
        # the bracket is exhausted when the midpoint no longer lies strictly inside it
        if abs(error) <= tolerance or not low < middle < high:
            return middle
        if error < 0.0:
            low = middle
        else:
            high = middle
