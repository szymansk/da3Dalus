"""Validation of the optional fuselage-section contour (gh-1349).

The rules and their threshold are the aero kernel's (canon rule ``fuselage-contour``): the app applies the same functions to the same numbers, so a contour the
API accepts is one the kernel accepts. Nothing is repaired: an invalid contour is refused
(ADR 0020).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from aero_kernel.build import shipped_build
from aero_kernel.fuselage_contour import contour_defect, contour_set_defects
from aero_kernel.rules import Rules
from pydantic import Field

ContourCoordinate = Annotated[float, Field(allow_inf_nan=False)]
ContourPoint = tuple[ContourCoordinate, ContourCoordinate]


def canon_threshold(rule: str, parameter: str) -> float:
    """Return the adopted value of a canon rule parameter (``rules.yaml``)."""
    return Rules(shipped_build().model).value(rule, parameter)


def check_contour(contour: Sequence[ContourPoint]) -> None:
    """Raise ``ValueError`` naming the offending point if a section's contour breaks a rule."""
    minimum = int(canon_threshold("fuselage-contour", "min_contour_points"))
    defect = contour_defect(contour, minimum)
    if defect is None:
        return
    where = "contour" if defect.point is None else f"contour[{defect.point}]"
    raise ValueError(f"{where}: the contour {defect.message}")


def contour_set_messages(
    contours: Sequence[Sequence[ContourPoint] | None],
) -> list[tuple[int, str]]:
    """Return ``(section index, message)`` for every section breaking the all-or-none rule."""
    return [
        (defect.section, f"x_secs[{defect.section}] {defect.message}")
        for defect in contour_set_defects(contours)
    ]
