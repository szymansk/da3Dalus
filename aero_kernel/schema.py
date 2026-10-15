"""Result types of the kernel (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4).

Warnings, quantity results, the compute result and provenance. All models are frozen and reject
unknown fields. :class:`KernelError` is re-exported from :mod:`aero_kernel.errors`.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Self

from aero_kernel.errors import KernelError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

__all__ = ["WARNING_CATALOGUE", "Interval", "KernelError", "KernelWarning", "WarningSeverity"]


class WarningSeverity(StrEnum):
    """Whether a warning is domain practice or a defect (ADR 0020, ch. 8.2)."""

    PRACTICE = "practice"
    DEFECT = "defect"


# The closed warning table (ch. 8.2): code -> fixed severity. A new code is added here by the unit
# that builds its source, never invented at the raise site.
WARNING_CATALOGUE: Mapping[str, WarningSeverity] = {
    "conflicting_mass": WarningSeverity.PRACTICE,
    "default_target_used": WarningSeverity.PRACTICE,
    "deflection_without_flap": WarningSeverity.PRACTICE,
    "precondition_unchecked": WarningSeverity.PRACTICE,
    "precondition_violated": WarningSeverity.DEFECT,
    "postcondition_unchecked": WarningSeverity.PRACTICE,
    "postcondition_violated": WarningSeverity.DEFECT,
}


class KernelWarning(BaseModel):
    """A value with a caveat (ch. 8.2); the ``DesignWarning`` shape of ADR 0020.

    The quantity a warning is reported on is the result that lists it, so there is no
    ``quantity`` field.

    Attributes:
        severity: ``practice`` (domain practice) or ``defect``; fixed by the code.
        code: Machine-readable code from :data:`WARNING_CATALOGUE`.
        message: The caveat, in natural language.
        origin: Slug of the quantity where the warning arose; ``None`` until the engine sets it.
        world: Method world the warning arose in (ch. 8.13).
        detail: Structured values the warning carries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    severity: WarningSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    origin: str | None = Field(default=None, min_length=1)
    world: str | None = None
    detail: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_code(self) -> Self:
        """Reject codes outside the table and severities that contradict it."""
        expected = WARNING_CATALOGUE.get(self.code)
        if expected is None:
            msg = f"code {self.code} is not in the warning catalogue; add it to WARNING_CATALOGUE"
            raise ValueError(msg)
        if expected is not self.severity:
            msg = f"code {self.code} has severity {expected.value}, not {self.severity.value}"
            raise ValueError(msg)
        return self


class Interval(BaseModel):
    """The spread of an uncertain quantity over its method worlds (ch. 8.13, A11).

    Never interval arithmetic: ``min`` and ``max`` are taken over the world values only.

    Attributes:
        min: Smallest world value, in the quantity's SI unit.
        max: Largest world value, in the quantity's SI unit.
        worlds: Value per world assignment (``neutral-point=avl,roll-rate=aerobuildup``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    min: float
    max: float
    worlds: dict[str, float] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_worlds(self) -> Self:
        """Require min and max to be the extremes of the world values."""
        if self.min != min(self.worlds.values()) or self.max != max(self.worlds.values()):
            msg = "interval min and max must equal the smallest and largest world value"
            raise ValueError(msg)
        return self
