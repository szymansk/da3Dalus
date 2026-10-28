"""The declared-warning shape of ADR 0020 (one DesignWarning channel, no undeclared fallbacks)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

WarningCategory = Literal[
    "substituted_assumption",
    "fit_not_converged",
    "geometry_healed",
    "input_missing",
    "result_truncated",
    "capability_unavailable",
]
WarningSeverity = Literal["notice", "warning", "error"]


class DesignWarning(BaseModel):
    """A substitution or inference that the numbers depend on, declared instead of hidden."""

    code: str = Field(..., description="Stable machine token, e.g. SURFACE_TYPE_INFERRED")
    category: WarningCategory
    severity: WarningSeverity = Field(
        ...,
        description=(
            "notice: legitimate, declared substitution; warning: usable, confidence reduced; "
            "error: not physically meaningful, do not build on it"
        ),
    )
    message: str = Field(..., description="Human-readable, including the justification")
    context: dict[str, Any] = Field(default_factory=dict, description="The concrete values")
