"""Lift per span l(y), shear force V(y) and bending moment M(y) along one half-wing."""

from _example import b_ref, sqrt_ellipse
from _svg import Svg

CAPTION = (
    "Spanwise loads of one half-wing, y from the centreline outward: l(y) is the lift per metre, "
    "V(y) its integral from the tip to y, M(y) the integral of V. Elliptic l(y) as a hand example "
    "(the kernel takes l(y) from one AVL solution); L = n m g with n = 1, m = 1.5 kg."
)

MASS = 1.5
GRAVITY = 9.81
LOAD_FACTOR = 1.0
POINTS = 200


def loads() -> tuple[list[float], list[float], list[float], list[float]]:
    """Stations y, lift per span, shear force and bending moment (tip to root integrals, trapezoid rule)."""
    half = b_ref() / 2
    lift = LOAD_FACTOR * MASS * GRAVITY
    peak = 4 * lift / (3.141592653589793 * b_ref())
    ys = [half * i / POINTS for i in range(POINTS + 1)]
    ls = [peak * sqrt_ellipse(y / half) for y in ys]
    vs = [0.0] * len(ys)
    ms = [0.0] * len(ys)
    for i in range(POINTS - 1, -1, -1):
        dy = ys[i + 1] - ys[i]
        vs[i] = vs[i + 1] + (ls[i] + ls[i + 1]) / 2 * dy
        ms[i] = ms[i + 1] + (vs[i] + vs[i + 1]) / 2 * dy
    return ys, ls, vs, ms


def build() -> str:
    """The figure as SVG text."""
    ys, ls, vs, ms = loads()
    half = b_ref() / 2
    svg = Svg(900, 400, "Spanwise lift, shear force and bending moment", CAPTION)
    left, width = 90.0, 420.0
    panels = [
        ("l(y)", "N/m", ls, "fg-ln"),
        ("V(y)", "N", vs, "fg-acc"),
        ("M(y)", "N m", ms, "fg-bad"),
    ]
    for index, (name, unit, values, cls) in enumerate(panels):
        top = 40 + index * 112
        height = 78.0
        high = max(values)
        svg.line(left, top + height, left + width, top + height, "fg-thin")
        svg.line(left, top, left, top + height, "fg-thin")
        svg.poly(
            [
                (left + y / half * width, top + height - v / high * height)
                for y, v in zip(ys, values, strict=True)
            ],
            cls,
            close=False,
        )
        svg.text(left - 10, top + 12, f"{name} [{unit}]", "fg-t fg-b", "end")
        svg.text(left - 10, top + 28, f"root: {values[0]:.2f}", "fg-m", "end")
        svg.text(left + width + 8, top + height + 4, "tip: 0", "fg-m")
    svg.text(left, 380, "y = 0 centreline", "fg-m")
    svg.text(left + width, 380, f"y = b/2 = {half:.2f} m", "fg-m", "end")
    right = 560
    svg.text(right, 70, f"L = n m g = {LOAD_FACTOR * MASS * GRAVITY:.2f} N", "fg-h")
    svg.text(right, 94, f"Each half carries L/2 = {vs[0]:.2f} N: V(0).", "fg-t")
    svg.text(right, 130, "V(y) = integral of l from the tip to y", "fg-t")
    svg.text(right, 148, "M(y) = integral of V from the tip to y", "fg-t")
    svg.text(right, 184, f"M(0) = {ms[0]:.2f} N m: the wing root", "fg-t")
    svg.text(right, 202, "must carry it (strength-only, BR-W18).", "fg-t")
    return svg.render()
