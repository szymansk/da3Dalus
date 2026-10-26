"""The hand example the geometry figures share, and the textbook relations that read it.

One trapezoid half-wing with a fuselage gap at the centreline. Every number in a figure comes from
here, computed in pure Python from the stated inputs, never typed into a drawing. The aero tier
(`aero_kernel/tests/test_canon_figures_aero.py`) checks them against AeroSandbox 4.2.9.
"""

import math
from pathlib import Path

import yaml

# Inputs, in metres. The root section sits at y = 0.10 (half the fuselage width), not on the centreline.
Y_ROOT = 0.10
Y_TIP = 0.90
C_ROOT = 0.30
C_TIP = 0.15
X_LE_TIP = 0.12  # leading-edge offset of the tip behind the root leading edge

# Horizontal tail and fin of the same example (centroid quarter-chord stations, area).
S_TAIL = 0.07
B_TAIL = 0.53
X_AC_TAIL = 0.85
S_FIN = 0.035
X_AC_FIN = 0.87
ETA_TAIL = 0.65  # the canon default of tail-efficiency

CANON = Path(__file__).resolve().parent.parent


def canon_default(slug: str) -> float:
    """A default of the canon (``defaults.yaml``), so a figure shows the value the canon states."""
    table = yaml.safe_load((CANON / "defaults.yaml").read_text(encoding="utf-8"))
    return float(table[slug]["value"])


def panel_span() -> float:
    """Span of one panel, along y."""
    return Y_TIP - Y_ROOT


def taper() -> float:
    """Taper ratio of the panel."""
    return C_TIP / C_ROOT


def panel_area() -> float:
    """Planform area of one panel, without the gap."""
    return (C_ROOT + C_TIP) / 2 * panel_span()


def c_geo() -> float:
    """Geometric chord of the panel, area over span: the width AeroSandbox gives the gap strip."""
    return panel_area() / panel_span()


def gap_area() -> float:
    """Area of one strip from the centreline to the root: AeroSandbox extrudes the root section with the geometric chord as its width."""
    return c_geo() * Y_ROOT


def s_ref() -> float:
    """Reference area: both panels and both gaps (``include_centerline_distance=True``)."""
    return 2 * (panel_area() + gap_area())


def s_panels() -> float:
    """Area of both panels without the gaps."""
    return 2 * panel_area()


def b_ref() -> float:
    """Reference span, carried to the centreline."""
    return 2 * Y_TIP


def b_panels() -> float:
    """Span of the panels only, without the gap."""
    return 2 * panel_span()


def aspect_ratio() -> float:
    """``b_ref^2 / s_ref``."""
    return b_ref() ** 2 / s_ref()


def c_mac() -> float:
    """Mean aerodynamic chord of the trapezoid panel: ``(2/3) c_r (1 + t + t^2) / (1 + t)``."""
    t = taper()
    return 2 / 3 * C_ROOT * (1 + t + t * t) / (1 + t)


def y_mac() -> float:
    """Station of the mean aerodynamic chord: ``y_root + b_p (1 + 2t) / (3 (1 + t))``."""
    t = taper()
    return Y_ROOT + panel_span() * (1 + 2 * t) / (3 * (1 + t))


def x_le_at(y: float) -> float:
    """Leading-edge x at station y (straight leading edge, root leading edge at x = 0)."""
    return X_LE_TIP * (y - Y_ROOT) / panel_span()


def x_le_mac() -> float:
    """Leading edge of the mean aerodynamic chord."""
    return x_le_at(y_mac())


def x_ac_wing() -> float:
    """Aerodynamic centre of the wing: a quarter of the MAC behind its leading edge."""
    return x_le_mac() + 0.25 * c_mac()


def ar_tail() -> float:
    """Aspect ratio of the tail."""
    return B_TAIL**2 / S_TAIL


def np_textbook() -> float:
    """Neutral point, textbook world: the barycentre with ``K = eta (1 - 4/(AR+2)) ...``."""
    ar, ar_h = aspect_ratio(), ar_tail()
    k = ETA_TAIL * (1 - 4 / (ar + 2)) * (ar_h / (ar_h + 2)) / (ar / (ar + 2))
    return _barycentre(k)


def np_pappas() -> float:
    """Neutral point, Pappas world: the barycentre with ``K = (1 - 3.24/AR) ...``."""
    ar, ar_h = aspect_ratio(), ar_tail()
    k = (1 - 3.24 / ar) * (1 / (1 + 2 / ar_h)) / (1 / (1 + 2 / ar))
    return _barycentre(k)


def _barycentre(k: float) -> float:
    """``(S_w x_ac,w + K S_h x_ac,h) / (S_w + K S_h)``."""
    return (s_ref() * x_ac_wing() + k * S_TAIL * X_AC_TAIL) / (s_ref() + k * S_TAIL)


def percent_mac(x: float) -> float:
    """A position as a percentage of the MAC, 0 at its leading edge."""
    return (x - x_le_mac()) / c_mac() * 100


def sqrt_ellipse(s: float) -> float:
    """``sqrt(1 - s^2)``, the elliptic lift shape, for ``|s| <= 1``."""
    return math.sqrt(max(0.0, 1 - s * s))
