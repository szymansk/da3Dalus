"""Tail volumes: arm times area over the wing's area times its span, from quarter-chord to quarter-chord."""

from _example import S_FIN, S_TAIL, X_AC_FIN, X_AC_TAIL, b_ref, s_ref, x_ac_wing
from _svg import Svg

CAPTION = (
    "Tail arms l_H,25 and l_V,25 run from the wing's quarter-chord MAC to the tail's; V_H and V_V "
    "are arm times tail area over wing area times chord or span. Hand example. Arms from the design "
    "CG (l_H,CG, l_V,CG, Drela's definition) follow with #1272."
)

SCALE = 330.0
OX, OY = 80.0, 180.0


def build() -> str:
    """The figure as SVG text."""
    svg = Svg(900, 420, "Tail arms and tail volumes", CAPTION)
    l_h = X_AC_TAIL - x_ac_wing()
    l_v = X_AC_FIN - x_ac_wing()
    v_v = S_FIN * l_v / (s_ref() * b_ref())

    def px(x: float, y: float) -> tuple[float, float]:
        return OX + x * SCALE, OY + y * SCALE

    # top view, nose to the left, x aft to the right
    svg.line(*px(-0.1, 0), *px(1.0, 0), "fg-thin fg-dash")
    svg.rect(*px(-0.05, -0.045), 0.95 * SCALE, 0.09 * SCALE, "fg-box", 8)
    svg.poly([px(0.0, 0.0), px(0.12, 0.9 * 0.55), px(0.27, 0.9 * 0.55), px(0.30, 0.0)], "fg-wing")
    svg.poly([px(0.0, 0.0), px(0.12, -0.9 * 0.55), px(0.27, -0.9 * 0.55), px(0.30, 0.0)], "fg-wing")
    tail_half = 0.265
    svg.poly(
        [
            px(X_AC_TAIL - 0.04, 0),
            px(X_AC_TAIL - 0.01, tail_half),
            px(X_AC_TAIL + 0.04, tail_half),
            px(X_AC_TAIL + 0.05, 0),
        ],
        "fg-wing",
    )
    svg.poly(
        [
            px(X_AC_TAIL - 0.04, 0),
            px(X_AC_TAIL - 0.01, -tail_half),
            px(X_AC_TAIL + 0.04, -tail_half),
            px(X_AC_TAIL + 0.05, 0),
        ],
        "fg-wing",
    )
    svg.rect(*px(X_AC_FIN - 0.05, -0.012), 0.1 * SCALE, 0.024 * SCALE, "fg-gap")
    wx, wy = px(x_ac_wing(), 0)
    hx, hy = px(X_AC_TAIL, 0)
    fx, _ = px(X_AC_FIN, 0)
    svg.circle(wx, wy, 4, "fg-accf")
    svg.circle(hx, hy, 4, "fg-accf")
    svg.circle(fx, wy, 4, "fg-badf")
    svg.dim(wx, 380, hx, 380, f"l_H,25 = {l_h:.3f} m", shift=-8)
    svg.dim(wx, 412, fx, 412, f"l_V,25 = {l_v:.3f} m", "fg-bad", "fg-badf", "fg-badt", -8)
    for x in (wx, hx):
        svg.line(x, wy, x, 380, "fg-thin fg-dash")
    svg.line(fx, wy, fx, 412, "fg-thin fg-dash")
    svg.text(wx + 24, wy - 0.9 * 0.55 * SCALE - 8, "wing", "fg-m", "middle")
    svg.text(hx, wy - tail_half * SCALE - 8, "H-tail", "fg-m", "middle")
    svg.text(fx + 24, wy + 26, "fin (top view: a line)", "fg-m")
    left = 560
    svg.text(left, 80, "V_V = S_V l_V,25 / (S_ref b_ref)", "fg-h")
    svg.text(
        left, 100, f"= {S_FIN} x {l_v:.3f} / ({s_ref():.3f} x {b_ref():.2f}) = {v_v:.4f}", "fg-t"
    )
    svg.text(left, 126, "V_H = S_H l_H,25 / (S_ref c_MAC)", "fg-h")
    svg.text(left, 146, f"S_H = {S_TAIL} m², l_H,25 = {l_h:.3f} m", "fg-t")
    svg.circle(left + 5, 200, 4, "fg-accf")
    svg.text(left + 16, 204, "quarter-chord MAC of the wing and of the H-tail", "fg-m")
    svg.circle(left + 5, 220, 4, "fg-badf")
    svg.text(left + 16, 224, "quarter-chord MAC of the fin", "fg-m")
    svg.text(left, 262, "Not Drela's arm yet: his l is measured from the CG.", "fg-badt")
    return svg.render()
