"""Declared distance between a fuselage section's contour and its super-ellipse fit (gh-1349).

The aerodynamic solvers compute with ``a``, ``b``, ``n``, ``n_lower``; the contour is display and
CAD geometry only (ADR 0022). When the fit's extent is more than the canon's
``fuselage-contour-fit.max_fit_deviation`` (1 mm, maintainer 2026-11-03) away from the contour's,
the analysed body is coarser than the one drawn and built. That is declared, never refused
(ADR 0020). The distance and the threshold are the aero kernel's, so the app and the kernel report
the same number.
"""

from __future__ import annotations

from collections.abc import Iterable

from aero_kernel.fuselage_contour import contour_fit_deviation

from app.schemas.design_warning import DesignWarning
from app.schemas.fuselage_contour import canon_threshold

FUSELAGE_CONTOUR_FIT_MISMATCH_CODE = "FUSELAGE_CONTOUR_FIT_MISMATCH"


def fuselage_contour_fit_warnings(fuselages: Iterable) -> list[DesignWarning]:
    """Declare every section whose contour the super-ellipse fit misses by more than 1 mm.

    Args:
        fuselages: Fuselage models or schemas; their sections' contours were validated on write.

    Returns:
        One ``warning`` per offending section, in fuselage and section order.
    """
    warnings: list[DesignWarning] = []
    limit: float | None = None
    for fuselage in fuselages:
        for index, x_sec in enumerate(fuselage.x_secs or []):
            if x_sec.contour is None:
                continue
            if limit is None:
                limit = canon_threshold("fuselage-contour-fit", "max_fit_deviation")
            contour = [(float(y), float(z)) for y, z in x_sec.contour]
            deviation = contour_fit_deviation(contour, float(x_sec.a), float(x_sec.b))
            if deviation <= limit:
                continue
            warnings.append(
                DesignWarning(
                    code=FUSELAGE_CONTOUR_FIT_MISMATCH_CODE,
                    category="substituted_assumption",
                    severity="warning",
                    message=(
                        f"Section {index} of fuselage {fuselage.name!r}: the super-ellipse fit "
                        f"(a = {x_sec.a * 1000:.1f} mm, b = {x_sec.b * 1000:.1f} mm) is "
                        f"{deviation * 1000:.1f} mm away from the section's contour, more than "
                        f"{limit * 1000:g} mm. The aerodynamic analysis uses the fit, so it sees "
                        "a coarser body than the one drawn and built. Refit a and b to the contour."
                    ),
                    context={
                        "fuselage": fuselage.name,
                        "section": index,
                        "deviation_m": deviation,
                        "max_fit_deviation_m": limit,
                        "a": x_sec.a,
                        "b": x_sec.b,
                    },
                )
            )
    return warnings
