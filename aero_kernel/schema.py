"""Result types of the kernel (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4).

Warnings, quantity results, the compute result and provenance. All models are frozen and reject
unknown fields. :class:`KernelError` is re-exported from :mod:`aero_kernel.errors`.
"""

from enum import StrEnum
from typing import Self

from aero_kernel.errors import KernelError
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["DesignWarning", "Interval", "KernelError", "WarningSeverity"]


class WarningSeverity(StrEnum):
    """Whether a warning is domain practice or a defect (ADR 0020, ch. 8.2)."""

    PRACTICE = "practice"
    DEFECT = "defect"


class DesignWarning(BaseModel):
    """A value with a caveat (ch. 8.2); the shape of ``DesignWarning`` of ADR 0020.

    Attributes:
        severity: ``practice`` (domain practice) or ``defect``.
        code: Machine-readable warning code.
        message: The caveat, in natural language.
        quantity: Slug of the quantity the warning is reported on.
        origin: Slug of the quantity where the warning arose.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    severity: WarningSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    quantity: str | None = None
    origin: str = Field(min_length=1)


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
