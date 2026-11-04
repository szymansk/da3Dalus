"""Plausibility of stored fuselage cross-sections where no source geometry survives (Q-FD-3 ③).

A stored ``a``/``b`` pair cannot be checked against anything once the STEP it came from is gone.
What can be checked is the body's proportion: a fuselage many times wider than tall (or the
reverse) more likely carries a swapped or doubled half-axis than a real shape. Such a body is
declared, never refused, because genuinely flat RC fuselages exist (a 0.5 kg foamie at 4:1).
"""

from __future__ import annotations

from collections.abc import Iterable

from app.converters.superellipse_asb import FULL_OVER_HALF_AXIS
from app.schemas.design_warning import DesignWarning

FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND_CODE = "FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND"

# Plausible range of the body's full width over its full height, 2a/2b.
# Source: Q-FD-3 (_reversa_sdd/questions.md, expert consensus endorsed by the maintainer
# 2026-08-14), "RC practice"; confidence medium. Outside it: severity "warning", never an error.
FUSELAGE_ASPECT_RATIO_BAND: tuple[float, float] = (0.3, 3.0)


def fuselage_aspect_ratio_warnings(fuselages: Iterable) -> list[DesignWarning]:
    """Declare every fuselage whose ``max(2a) / max(2b)`` lies outside the band.

    Each axis is judged by its own largest section, so a tapering nose or tail point does not
    decide the ratio. A body with no extent on either axis has no ratio; the degenerate-body
    guards (gh-790, gh-804) already handle it.
    """
    low, high = FUSELAGE_ASPECT_RATIO_BAND
    warnings = []
    for fuselage in fuselages:
        sections = fuselage.x_secs or []
        max_width = max((FULL_OVER_HALF_AXIS * float(xs.a) for xs in sections), default=0.0)
        max_height = max((FULL_OVER_HALF_AXIS * float(xs.b) for xs in sections), default=0.0)
        if max_width <= 0.0 or max_height <= 0.0:
            continue
        ratio = max_width / max_height
        if low <= ratio <= high:
            continue
        warnings.append(
            DesignWarning(
                code=FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND_CODE,
                category="substituted_assumption",
                severity="warning",
                message=(
                    f"Fuselage {fuselage.name!r} is {ratio:.2f} times as wide as it is tall "
                    f"(width {max_width * 1000:.1f} mm, height {max_height * 1000:.1f} mm), "
                    f"outside the plausible range {low}-{high}. The analysis takes a and b as "
                    "the half-width and half-height; a swapped or doubled value would give the "
                    "same picture. Check the cross-sections."
                ),
                context={
                    "fuselage": fuselage.name,
                    "width_over_height": ratio,
                    "max_width_m": max_width,
                    "max_height_m": max_height,
                    "band": [low, high],
                },
            )
        )
    return warnings
