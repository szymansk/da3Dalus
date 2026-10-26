"""A tiny deterministic SVG builder for the canon figures.

Colours are the navigator's CSS variables with light-theme fallbacks, so a figure reads in both
themes when inlined and also stands alone as a file. Nothing here knows a canon quantity.
"""

import math

STYLE = """
.fg-t{fill:var(--ink,#23211C);font:12px 'Geist','Helvetica Neue',Arial,sans-serif}
.fg-b{font-weight:600}
.fg-m{fill:var(--ink-2,#6B675E);font:11px 'Geist','Helvetica Neue',Arial,sans-serif}
.fg-h{fill:var(--ink,#23211C);font:600 13px 'Geist','Helvetica Neue',Arial,sans-serif}
.fg-ln{stroke:var(--ink,#23211C);stroke-width:1.4;fill:none}
.fg-thin{stroke:var(--ink-3,#9A958A);stroke-width:1;fill:none}
.fg-dash{stroke-dasharray:5 4}
.fg-wing{fill:var(--inp-bg,#EBF1F7);stroke:var(--inp,#4C7198);stroke-width:1.4}
.fg-gap{fill:var(--hub-bg,#FAF2E4);stroke:var(--hub,#A67C3C);stroke-width:1.2;stroke-dasharray:4 3}
.fg-acc{stroke:var(--sel,#6B4FA0);stroke-width:2;fill:none}
.fg-accf{fill:var(--sel,#6B4FA0)}
.fg-acct{fill:var(--sel,#6B4FA0);font:600 12px 'Geist','Helvetica Neue',Arial,sans-serif}
.fg-bad{stroke:var(--bad,#C0392B);stroke-width:2;fill:none}
.fg-badf{fill:var(--bad,#C0392B)}
.fg-badt{fill:var(--bad,#C0392B);font:600 12px 'Geist','Helvetica Neue',Arial,sans-serif}
.fg-good{stroke:var(--good,#2E8B57);stroke-width:2;fill:none}
.fg-goodf{fill:var(--good,#2E8B57)}
.fg-box{fill:var(--panel,#FFFFFF);stroke:var(--line-2,#CFC9BC);stroke-width:1}
.fg-dot{fill:var(--ink,#23211C)}
"""


def num(value: float) -> str:
    """Format a coordinate: two decimals, trailing zeros dropped, never ``-0``."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


class Svg:
    """An SVG document of fixed pixel size, scaled by the viewer through its viewBox."""

    def __init__(self, width: float, height: float, title: str, description: str) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.description = description
        self.parts: list[str] = []

    def add(self, markup: str) -> None:
        """Append raw markup."""
        self.parts.append(markup)

    def line(self, x1: float, y1: float, x2: float, y2: float, cls: str = "fg-ln") -> None:
        """A straight line."""
        self.add(
            f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" class="{cls}"/>'
        )

    def poly(
        self, points: list[tuple[float, float]], cls: str = "fg-wing", close: bool = True
    ) -> None:
        """A polygon, or an open polyline with ``close=False``."""
        coords = " ".join(f"{num(x)},{num(y)}" for x, y in points)
        tag = "polygon" if close else "polyline"
        self.add(f'<{tag} points="{coords}" class="{cls}"/>')

    def rect(
        self, x: float, y: float, w: float, h: float, cls: str = "fg-box", rx: float = 0
    ) -> None:
        """A rectangle."""
        self.add(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(rx)}" class="{cls}"/>'
        )

    def circle(self, x: float, y: float, r: float, cls: str = "fg-dot") -> None:
        """A circle."""
        self.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" class="{cls}"/>')

    def text(
        self, x: float, y: float, content: str, cls: str = "fg-t", anchor: str = "start"
    ) -> None:
        """A text; the content is escaped."""
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.add(
            f'<text x="{num(x)}" y="{num(y)}" class="{cls}" text-anchor="{anchor}">{safe}</text>'
        )

    def arrowhead(
        self, x: float, y: float, angle: float, fill: str = "fg-dot", size: float = 7
    ) -> None:
        """A filled arrowhead whose tip is at (x, y) and that points along ``angle`` (radians)."""
        spread = 0.38
        left = (x - size * math.cos(angle - spread), y - size * math.sin(angle - spread))
        right = (x - size * math.cos(angle + spread), y - size * math.sin(angle + spread))
        self.poly([(x, y), left, right], fill)

    def arrow(
        self, x1: float, y1: float, x2: float, y2: float, cls: str = "fg-ln", head: str = "fg-dot"
    ) -> None:
        """A line with an arrowhead at its end."""
        angle = math.atan2(y2 - y1, x2 - x1)
        self.line(x1, y1, x2 - 6 * math.cos(angle), y2 - 6 * math.sin(angle), cls)
        self.arrowhead(x2, y2, angle, head)

    def dim(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        label: str,
        cls: str = "fg-acc",
        head: str = "fg-accf",
        label_cls: str = "fg-acct",
        shift: float = -7,
    ) -> None:
        """A dimension line with arrowheads at both ends and a label beside its middle."""
        angle = math.atan2(y2 - y1, x2 - x1)
        self.line(x1, y1, x2, y2, cls)
        self.arrowhead(x1, y1, angle + math.pi, head)
        self.arrowhead(x2, y2, angle, head)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        normal = (-math.sin(angle), math.cos(angle))
        anchor = "middle"
        self.text(mx + shift * normal[0], my + shift * normal[1], label, label_cls, anchor)

    def render(self) -> str:
        """The document as text, ending with a newline."""
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {num(self.width)} {num(self.height)}" '
            f'role="img" aria-labelledby="fg-title fg-desc">'
            f'<title id="fg-title">{self.title}</title><desc id="fg-desc">{self.description}</desc>'
            f"<style>{STYLE}</style>"
        )
        return head + "".join(self.parts) + "</svg>\n"
