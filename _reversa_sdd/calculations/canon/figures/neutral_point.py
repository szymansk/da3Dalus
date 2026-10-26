"""Where the neutral point, the design CG and the static margin sit on the MAC."""

from _example import (
    ETA_TAIL,
    c_mac,
    canon_default,
    np_pappas,
    np_textbook,
    percent_mac,
    x_le_mac,
)
from _svg import Svg

CAPTION = (
    "On the MAC (0 % at its leading edge): the neutral point is an interval over method worlds "
    "(textbook, Pappas; AVL is the third world and needs a solver); the design CG sits SM_target "
    "ahead of it, x_cg,design = x_NP - SM_target c_MAC. Hand example, canon default SM_target."
)

LEFT, RIGHT, MAC_Y = 70.0, 830.0, 190.0
LOW, HIGH = -20.0, 110.0  # percentages of the MAC on the drawn axis


def at(percent: float) -> float:
    """Pixel x of a position in percent of the MAC."""
    return LEFT + (percent - LOW) / (HIGH - LOW) * (RIGHT - LEFT)


def build() -> str:
    """The figure as SVG text."""
    sm = canon_default("static-margin-target")
    worlds = [("textbook", percent_mac(np_textbook())), ("Pappas", percent_mac(np_pappas()))]
    near, far = min(w[1] for w in worlds), max(w[1] for w in worlds)
    svg = Svg(900, 375, "Neutral point, design CG and static margin on the MAC", CAPTION)
    svg.rect(at(0), MAC_Y - 14, at(100) - at(0), 28, "fg-wing")
    svg.text(at(0), MAC_Y + 34, "0 %  (x_le,MAC)", "fg-m", "middle")
    svg.text(at(100), MAC_Y + 34, "100 %  (x_le,MAC + c_MAC)", "fg-m", "middle")
    svg.line(at(25), MAC_Y - 14, at(25), MAC_Y + 14, "fg-thin")
    svg.text(at(25), MAC_Y + 34, "25 %  (wing AC)", "fg-m", "middle")
    # the neutral point interval
    svg.rect(at(near), MAC_Y - 52, at(far) - at(near), 8, "fg-accf")
    for index, (name, percent) in enumerate(worlds):
        x = at(percent)
        svg.line(x, MAC_Y - 52, x, MAC_Y + 14, "fg-acc")
        svg.text(
            x + (6 if index else -6),
            MAC_Y - 58 - 14 * index,
            f"{name} {percent:.1f} %",
            "fg-acct",
            "start" if index else "end",
        )
    svg.text(at(near), MAC_Y - 100, "x_NP, interval over the worlds", "fg-acct")
    # the design CG, one per NP end
    for name, percent in worlds:
        svg.circle(at(percent - sm * 100), MAC_Y, 5, "fg-goodf")
        svg.text(
            at(percent - sm * 100),
            MAC_Y + 4 + (-14 if name == "textbook" else 24),
            "x_cg",
            "fg-m",
            "middle",
        )
        svg.dim(
            at(percent - sm * 100),
            MAC_Y + 76 + (34 if name == "Pappas" else 0),
            at(percent),
            MAC_Y + 76 + (34 if name == "Pappas" else 0),
            f"SM = {sm * 100:.0f} % ({name})",
            "fg-good",
            "fg-goodf",
            "fg-t",
            20,
        )
    svg.text(
        at(worlds[0][1] - sm * 100),
        MAC_Y + 150,
        "x_cg,design = x_NP - SM_target c_MAC",
        "fg-t",
        "middle",
    )
    svg.text(
        60,
        360,
        f"Hand example: c_MAC = {c_mac():.3f} m, x_le,MAC = {x_le_mac():.3f} m, tail efficiency {ETA_TAIL}, "
        f"SM_target = {sm:g} (canon starting value). Positive SM is stable; the CG must not pass the NP.",
        "fg-m",
    )
    return svg.render()
