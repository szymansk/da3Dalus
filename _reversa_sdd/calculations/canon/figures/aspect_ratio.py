"""AR = b_ref^2 / S_ref: the same area, two spans."""

from _example import aspect_ratio, b_ref, s_ref
from _svg import Svg

CAPTION = (
    "Aspect ratio is span squared over area: the same area S_ref spread over a long span is slender "
    "(high AR), over a short span stubby (low AR). Hand example from the reference wing."
)

SCALE = 300.0
SHORT_AR = 3.0


def build() -> str:
    """The figure as SVG text."""
    svg = Svg(900, 300, "Aspect ratio of two wings of equal area", CAPTION)
    area = s_ref()
    cases = [(b_ref(), "this example"), ((SHORT_AR * area) ** 0.5, "a stubby wing")]
    y0 = 40.0
    for span, name in cases:
        chord = area / span
        ar = span**2 / area
        left = 60 + (b_ref() - span) / 2 * SCALE
        svg.rect(left, y0, span * SCALE, chord * SCALE, "fg-wing")
        svg.text(60 + b_ref() * SCALE + 30, y0 + chord * SCALE / 2 - 6, name, "fg-m")
        svg.text(
            60 + b_ref() * SCALE + 30,
            y0 + chord * SCALE / 2 + 12,
            f"b = {span:.2f} m,  S = {area:.3f} m²",
            "fg-t",
        )
        svg.text(
            60 + b_ref() * SCALE + 30,
            y0 + chord * SCALE / 2 + 32,
            f"AR = b²/S = {ar:.2f}",
            "fg-acct",
        )
        y0 += chord * SCALE + 70
    svg.text(
        60,
        y0 - 20,
        f"AR = {aspect_ratio():.2f} here: {b_ref():.2f}² / {s_ref():.3f}. b and S are the reference values "
        "(centreline gap in both).",
        "fg-m",
    )
    return svg.render()
