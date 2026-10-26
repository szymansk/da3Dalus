"""S_ref and b_ref carry the centreline gap: the same planform with and without it."""

from _example import (
    C_ROOT,
    C_TIP,
    c_geo,
    X_LE_TIP,
    Y_ROOT,
    Y_TIP,
    aspect_ratio,
    b_panels,
    b_ref,
    gap_area,
    s_panels,
    s_ref,
)
from _svg import Svg

CAPTION = (
    "The reference wing runs through the fuselage: S_ref counts the strip between the centreline "
    "and the root, b_ref is measured from the centreline. Hand example, ASB 4.2.9 flags "
    "include_centerline_distance=True."
)

SCALE = 330.0
CX, OY = 560.0, 70.0


def build() -> str:
    """The figure as SVG text."""
    svg = Svg(960, 370, "Reference area and span with the centreline gap", CAPTION)

    def px(y: float, x: float) -> tuple[float, float]:
        return CX + y * SCALE, OY + x * SCALE

    for sign in (1, -1):
        svg.poly(
            [px(0, 0), px(sign * Y_ROOT, 0), px(sign * Y_ROOT, c_geo()), px(0, c_geo())], "fg-gap"
        )
        svg.poly(
            [
                px(sign * Y_ROOT, 0),
                px(sign * Y_TIP, X_LE_TIP),
                px(sign * Y_TIP, X_LE_TIP + C_TIP),
                px(sign * Y_ROOT, C_ROOT),
            ]
        )
    top = OY - 30
    svg.line(CX, top - 8, CX, OY + C_ROOT * SCALE + 12, "fg-thin fg-dash")
    svg.dim(
        px(-Y_TIP, 0)[0],
        top,
        px(Y_TIP, 0)[0],
        top,
        f"b_ref = {b_ref():.2f} m (from the centreline)",
    )
    for sign in (1, -1):
        svg.line(
            px(sign * Y_TIP, 0)[0],
            top - 5,
            px(sign * Y_TIP, X_LE_TIP)[0],
            OY + X_LE_TIP * SCALE,
            "fg-thin",
        )
    below = OY + C_ROOT * SCALE + 32
    svg.dim(px(-Y_TIP, 0)[0], below, px(-Y_ROOT, 0)[0], below, "", shift=0)
    svg.dim(px(Y_ROOT, 0)[0], below, px(Y_TIP, 0)[0], below, "", shift=0)
    svg.text(
        CX,
        below + 24,
        f"b_panels = {b_panels():.2f} m (the two panels, without the gap)",
        "fg-m",
        "middle",
    )
    svg.text(CX + 5, OY + 0.5 * C_ROOT * SCALE, "gap", "fg-m")
    # the numbers
    left = 40
    svg.text(left, 118, "Area", "fg-h")
    svg.text(left, 138, f"panels only:  {s_panels():.3f} m²", "fg-t")
    svg.text(left, 156, f"+ two gaps:   {2 * gap_area():.3f} m²", "fg-t")
    svg.text(left, 176, f"S_ref = {s_ref():.3f} m²", "fg-acct")
    svg.text(left, 196, "gap strip: root extruded to the centreline", "fg-m")
    svg.text(left, 212, f"with the geometric chord {c_geo():.3f} m (ASB)", "fg-m")
    svg.rect(left - 10, 270, 360, 84, "fg-box", 6)
    svg.text(left + 4, 290, "Misreading", "fg-badt")
    svg.text(left + 4, 308, f"Area without the gap ({s_panels():.2f} m²) with the span", "fg-t")
    svg.text(
        left + 4,
        324,
        f"with it ({b_ref():.2f} m) gives AR = {b_ref() ** 2 / s_panels():.2f},",
        "fg-t",
    )
    svg.text(left + 4, 340, f"not the consistent AR = {aspect_ratio():.2f}.", "fg-t")
    return svg.render()
