"""Result types of the kernel (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4).

Warnings, quantity results, the compute result and provenance. All models are frozen and reject
unknown fields. :class:`KernelError` is re-exported from :mod:`aero_kernel.errors`.
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Literal, Self

from aero_kernel.errors import ErrorCategory, KernelError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

__all__ = ["WARNING_CATALOGUE", "Interval", "KernelError", "KernelWarning", "WarningSeverity"]


class WarningSeverity(StrEnum):
    """Whether a warning is domain practice or a defect (ADR 0020, ch. 8.2)."""

    PRACTICE = "practice"
    DEFECT = "defect"


# The accuracy tiers of the solvers (ch. 8.11), coarsest first.
Accuracy = Literal["xxsmall", "xsmall", "small", "medium", "large", "xlarge", "xxlarge", "xxxlarge"]

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


def dedupe_warnings(warnings: Iterable[KernelWarning]) -> tuple[KernelWarning, ...]:
    """Drop repeated warnings by (``code``, ``origin``, ``world``); the first occurrence wins.

    Args:
        warnings: Warnings of a quantity and its subtree, in collection order.

    Returns:
        The warnings without repeats, order kept.
    """
    unique: dict[tuple[str, str | None, str | None], KernelWarning] = {}
    for warning in warnings:
        unique.setdefault((warning.code, warning.origin, warning.world), warning)
    return tuple(unique.values())


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


class QuantityStatus(StrEnum):
    """The outcome class of a quantity (ch. 8.3)."""

    OK = "ok"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED = "skipped"
    ERROR = "error"


class ReasonCode(StrEnum):
    """Why a quantity is ``not_applicable`` or ``skipped`` (ch. 8.3).

    Separate from the error codes: these are expected outcomes, not failures.
    """

    CONDITION_NOT_MET = "condition_not_met"
    NOT_GIVEN = "not_given"
    DEPENDS_ON_NOT_APPLICABLE = "depends_on_not_applicable"
    LONG_RUN_NOT_INCLUDED = "long_run_not_included"
    DEPENDS_ON_SKIPPED = "depends_on_skipped"


# Which reason codes fit which non-ok status (ch. 8.3).
_REASONS_BY_STATUS: Mapping[QuantityStatus, frozenset[ReasonCode]] = {
    QuantityStatus.NOT_APPLICABLE: frozenset(
        {
            ReasonCode.CONDITION_NOT_MET,
            ReasonCode.NOT_GIVEN,
            ReasonCode.DEPENDS_ON_NOT_APPLICABLE,
        }
    ),
    QuantityStatus.SKIPPED: frozenset(
        {ReasonCode.LONG_RUN_NOT_INCLUDED, ReasonCode.DEPENDS_ON_SKIPPED}
    ),
}


class Reason(BaseModel):
    """Machine-readable code plus natural-language message for a non-ok status.

    Attributes:
        code: The reason code.
        message: The reason, in natural language.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ReasonCode
    message: str = Field(min_length=1)


class QuantityResult(BaseModel):
    """The result for one requested quantity (ch. 8.3).

    Attributes:
        slug: Canon slug of the quantity.
        unit: SI unit of ``value`` and ``interval``.
        status: Outcome class.
        reason: Why the quantity is ``not_applicable`` or ``skipped``.
        value: The value (floats only in v1).
        interval: The spread over method worlds, for an uncertain quantity.
        tool: Tool that produced the value.
        application: Id of the application that produced the value.
        validated: Always ``False``: no value is validated against flight data (A11).
        warnings: Caveats of this quantity and its subtree.
        error: Why there is no value, for status ``error``.
        from_cache: Whether the value was served from the cache.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(min_length=1)
    unit: str
    status: QuantityStatus
    reason: Reason | None = None
    value: float | None = None
    interval: Interval | None = None
    tool: str | None = None
    application: str | None = None
    validated: Literal[False] = False
    warnings: tuple[KernelWarning, ...] = ()
    error: KernelError | None = None
    from_cache: bool = False

    @model_validator(mode="after")
    def _check_status(self) -> Self:
        """Enforce the status invariants of ch. 8.3."""
        keys = [(w.code, w.origin, w.world) for w in self.warnings]
        if len(set(keys)) != len(keys):
            msg = "duplicate warning: (code, origin, world) must be unique within a quantity"
            raise ValueError(msg)
        has_result = self.value is not None or self.interval is not None
        if self.status is QuantityStatus.OK:
            if (self.value is None) == (self.interval is None):
                msg = "status ok needs exactly one of value and interval"
                raise ValueError(msg)
            if self.error is not None:
                msg = "status ok must not carry an error"
                raise ValueError(msg)
        elif has_result:
            msg = f"status {self.status.value} must not carry a value or interval"
            raise ValueError(msg)
        if self.status is QuantityStatus.ERROR and self.error is None:
            msg = "status error needs an error"
            raise ValueError(msg)
        if self.error is not None and self.error.quantity not in (None, self.slug):
            msg = f"error.quantity {self.error.quantity} must equal slug {self.slug}"
            raise ValueError(msg)
        allowed = _REASONS_BY_STATUS.get(self.status)
        if allowed is None:
            if self.reason is not None:
                msg = f"status {self.status.value} must not carry a reason"
                raise ValueError(msg)
        else:
            if self.reason is None or self.reason.code not in allowed:
                msg = f"status {self.status.value} needs a reason with a fitting code"
                raise ValueError(msg)
            if self.error is not None:
                msg = f"status {self.status.value} must not carry an error"
                raise ValueError(msg)
        return self


class DefaultUsed(BaseModel):
    """A canon default the call took (ch. 8.11).

    Attributes:
        slug: Slug of the quantity whose default was taken.
        value: The default value, in ``unit``.
        unit: SI unit of ``value``.
        source: Where the default comes from.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)


class Provenance(BaseModel):
    """What a result was computed with (ch. 8.4).

    Attributes:
        kernel_version: ``aero_kernel.__version__``.
        build_digest: Hash over the code and canon model; identifies the exact build.
        canon_model_hash: Hash of the canon model.
        canon_source_commit: Commit of the canon document the model was imported from.
        tool_versions: Version per tool (aerosandbox, NeuralFoil model, AVL).
        accuracy: Accuracy tier of the call.
        solver_settings: Solver settings of the call.
        defaults_used: Every canon default the call took.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kernel_version: str = Field(min_length=1)
    build_digest: str = Field(min_length=1)
    canon_model_hash: str = Field(min_length=1)
    canon_source_commit: str = Field(min_length=1)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    accuracy: Accuracy
    solver_settings: dict[str, JsonValue] = Field(default_factory=dict)
    defaults_used: tuple[DefaultUsed, ...] = ()


class ComputeResult(BaseModel):
    """The result of one ``compute()`` call (ch. 8.3).

    Attributes:
        quantities: One result per requested slug, in request order.
        input_errors: ``invalid_input`` errors from validation; non-empty means nothing was computed.
        provenance: What the result was computed with.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    quantities: tuple[QuantityResult, ...] = ()
    input_errors: tuple[KernelError, ...] = ()
    provenance: Provenance

    @model_validator(mode="after")
    def _check_result(self) -> Self:
        """Enforce the invariants of ch. 8.3."""
        if any(e.category is not ErrorCategory.INVALID_INPUT for e in self.input_errors):
            msg = "input_errors may only hold errors of category invalid_input"
            raise ValueError(msg)
        if self.input_errors and self.quantities:
            msg = "non-empty input_errors means nothing was computed: quantities must be empty"
            raise ValueError(msg)
        slugs = [q.slug for q in self.quantities]
        if len(set(slugs)) != len(slugs):
            msg = "each requested slug appears once: duplicate slug in quantities"
            raise ValueError(msg)
        return self
