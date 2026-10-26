"""The stall break on a polar: where the lift has fallen by the fraction f past its peak."""

from _example import canon_default
from _svg import Svg

CAPTION = (
    "Stall break: past the peak (alpha_S, C_L,max) the lift falls; alpha_break is where it has "
    "dropped to (1 - f) C_L,max, found by a forward scan with linear interpolation between samples; "
    "the width is alpha_break - alpha_S. Illustrative polar (hand example, not a computed one); "
    "f is the canon default."
)

STEP = 0.5  # deg, the sample spacing of the example polar
ALPHA_END = 20.0
SLOPE = 0.1  # per deg
ALPHA_0 = -2.0
ALPHA_PEAK = 12.0
FALL = 0.012  # per deg^2 past the peak


def polar() -> list[tuple[float, float]]:
    """The example polar as (alpha in deg, C_L) samples."""
    peak = SLOPE * (ALPHA_PEAK - ALPHA_0)
    samples = []
    for i in range(int((ALPHA_END - ALPHA_0) / STEP) + 1):
        alpha = ALPHA_0 + i * STEP
        cl = (
            SLOPE * (alpha - ALPHA_0)
            if alpha <= ALPHA_PEAK
            else peak - FALL * (alpha - ALPHA_PEAK) ** 2
        )
        samples.append((alpha, cl))
    return samples


def stall_break(samples: list[tuple[float, float]], f: float) -> tuple[float, float, float, float]:
    """The canon procedure: alpha_S, C_L,max, alpha_break and the width of the break."""
    peak = max(range(len(samples)), key=lambda i: samples[i][1])
    alpha_s, cl_max = samples[peak]
    level = (1 - f) * cl_max
    for (a0, c0), (a1, c1) in zip(samples[peak:], samples[peak + 1 :], strict=False):
        if c1 <= level:
            alpha_break = a0 + (c0 - level) / (c0 - c1) * (a1 - a0)
            return alpha_s, cl_max, alpha_break, alpha_break - alpha_s
    msg = "the polar does not fall to (1 - f) C_L,max"
    raise ValueError(msg)


def build() -> str:
    """The figure as SVG text."""
    f = canon_default("stall-break-fraction")
    samples = polar()
    alpha_s, cl_max, alpha_break, width = stall_break(samples, f)
    left, right, top, bottom = 90.0, 560.0, 50.0, 300.0
    a_lo, a_hi, c_hi = -4.0, ALPHA_END, 1.6

    def px(alpha: float, cl: float) -> tuple[float, float]:
        return (
            left + (alpha - a_lo) / (a_hi - a_lo) * (right - left),
            bottom - cl / c_hi * (bottom - top),
        )

    svg = Svg(900, 350, "Stall break on a lift polar", CAPTION)
    svg.arrow(left, bottom, right + 20, bottom, "fg-thin", "fg-dot")
    svg.arrow(px(0, 0)[0], bottom + 10, px(0, 0)[0], top - 14, "fg-thin", "fg-dot")
    svg.text(right + 20, bottom + 18, "alpha (deg)", "fg-m", "end")
    svg.text(px(0, 0)[0] + 8, top - 4, "C_L", "fg-m")
    svg.poly([px(a, c) for a, c in samples], "fg-ln", close=False)
    for a, c in samples:
        svg.circle(*px(a, c), 2, "fg-dot")
    level = (1 - f) * cl_max
    svg.line(*px(a_lo, level), *px(a_hi, level), "fg-thin fg-dash")
    svg.text(
        px(a_lo, level)[0] + 4, px(a_lo, level)[1] - 5, f"(1 - f) C_L,max = {level:.3f}", "fg-m"
    )
    svg.circle(*px(alpha_s, cl_max), 5, "fg-accf")
    svg.text(
        px(alpha_s, cl_max)[0] - 8,
        px(alpha_s, cl_max)[1] - 10,
        f"alpha_S = {alpha_s:g} deg,  C_L,max = {cl_max:.2f}",
        "fg-acct",
        "end",
    )
    svg.circle(*px(alpha_break, level), 5, "fg-badf")
    svg.text(
        px(alpha_break, level)[0] + 10,
        px(alpha_break, level)[1] - 12,
        f"alpha_break = {alpha_break:.2f} deg",
        "fg-badt",
    )
    y = px(0, 0)[1] + 28
    svg.dim(px(alpha_s, 0)[0], y, px(alpha_break, 0)[0], y, f"width = {width:.2f} deg", shift=16)
    for alpha in (alpha_s, alpha_break):
        svg.line(px(alpha, 0)[0], bottom, px(alpha, 0)[0], y + 6, "fg-thin fg-dash")
    left_text = 660
    svg.text(left_text, 90, f"f = {f:g}", "fg-h")
    svg.text(left_text, 112, "the canon's cut, a convention", "fg-m")
    svg.text(left_text, 150, "Not C_L,max itself:", "fg-t")
    svg.text(left_text, 168, "the break is where the lift", "fg-t")
    svg.text(left_text, 186, "has visibly fallen.", "fg-t")
    svg.text(left_text, 224, f"Samples every {STEP:g} deg; the", "fg-m")
    svg.text(left_text, 240, "crossing is interpolated.", "fg-m")
    return svg.render()
