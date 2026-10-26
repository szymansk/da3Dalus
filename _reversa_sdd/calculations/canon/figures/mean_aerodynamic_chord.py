"""c_MAC is a length, x_le_MAC is where it starts: the trapezoid example."""

from _example import (
    C_ROOT,
    c_geo,
    C_TIP,
    X_LE_TIP,
    Y_ROOT,
    Y_TIP,
    c_mac,
    x_ac_wing,
    x_le_mac,
    y_mac,
)
from _svg import Svg

CAPTION = (
    "c_MAC is a length; x_le,MAC is the position where that length starts. Trapezoid half-wing "
    "(hand example, ASB 4.2.9 definitions): the aerodynamic centre is x_le,MAC + 0.25 c_MAC."
)

SCALE = 600.0
OX, OY = 270.0, 62.0


def px(y: float, x: float) -> tuple[float, float]:
    """Pixel of the planform point at station y (right) and x (aft, down)."""
    return OX + y * SCALE, OY + x * SCALE


def build() -> str:
    """The figure as SVG text."""
    svg = Svg(1000, 400, "Mean aerodynamic chord and its leading-edge position", CAPTION)
    svg.poly([px(0, 0), px(Y_ROOT, 0), px(Y_ROOT, c_geo()), px(0, c_geo())], "fg-gap")
    svg.poly([px(Y_ROOT, 0), px(Y_TIP, X_LE_TIP), px(Y_TIP, X_LE_TIP + C_TIP), px(Y_ROOT, C_ROOT)])
    cx, cy = px(0, 0)
    svg.line(cx, cy - 18, cx, OY + C_ROOT * SCALE + 18, "fg-thin fg-dash")
    svg.text(cx, cy - 24, "centreline y = 0", "fg-m", "middle")
    # the MAC
    mx, top = px(y_mac(), x_le_mac())
    _, bottom = px(y_mac(), x_le_mac() + c_mac())
    svg.line(mx, top, mx, bottom, "fg-acc")
    svg.circle(mx, top, 3.5, "fg-accf")
    svg.circle(mx, bottom, 3.5, "fg-accf")
    svg.text(mx + 9, (top + bottom) / 2 + 4, f"c_MAC = {c_mac():.3f} m  (a length)", "fg-acct")
    svg.text(mx + 9, top - 6, f"MAC at y = {y_mac():.3f} m", "fg-m")
    # the x axis (aft, down) with the two readings
    ax = OX - 62
    svg.arrow(ax, OY - 10, ax, OY + C_ROOT * SCALE + 24, "fg-thin", "fg-dot")
    svg.text(ax - 8, OY + C_ROOT * SCALE + 30, "x (aft)", "fg-m", "end")
    svg.line(ax - 5, OY, ax + 5, OY, "fg-ln")
    svg.text(ax - 10, OY + 4, "0  root LE", "fg-m", "end")
    svg.line(ax, top, mx, top, "fg-thin fg-dash")
    svg.line(ax - 5, top, ax + 5, top, "fg-acc")
    svg.text(ax - 10, top + 4, f"x_le,MAC = {x_le_mac():.3f} m", "fg-acct", "end")
    xac = OY + x_ac_wing() * SCALE
    svg.line(ax - 5, xac, mx, xac, "fg-thin fg-dash")
    svg.text(ax - 10, xac + 4, f"x_AC = {x_ac_wing():.3f} m", "fg-t", "end")
    wrong = OY + c_mac() * SCALE
    svg.line(ax - 5, wrong, ax + 5, wrong, "fg-bad")
    svg.text(ax - 10, wrong + 18, f"c_MAC = {c_mac():.3f} m is not a position", "fg-badt", "end")
    # the misreading box
    svg.rect(OX - 100, 300, 800, 84, "fg-box", 6)
    svg.text(OX - 86, 322, "Misreading", "fg-badt")
    svg.text(
        OX - 86,
        342,
        f"x = c_MAC ({c_mac():.3f} m) puts the MAC {c_mac() - x_le_mac():.3f} m too far aft. c_MAC is how long the chord is;",
        "fg-t",
    )
    svg.text(
        OX - 86,
        360,
        f"where it starts is x_le,MAC = {x_le_mac():.3f} m, and its trailing edge is x_le,MAC + c_MAC = "
        f"{x_le_mac() + c_mac():.3f} m.",
        "fg-t",
    )
    svg.text(
        OX - 86,
        376,
        f"Example: c_root {C_ROOT} m at y = {Y_ROOT} m, c_tip {C_TIP} m at y = {Y_TIP} m, tip leading edge {X_LE_TIP} m aft.",
        "fg-m",
    )
    return svg.render()
