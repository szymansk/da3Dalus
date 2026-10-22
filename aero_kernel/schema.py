"""Result types of the kernel (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4).

Warnings, quantity results, the compute result and provenance. All models are frozen and reject
unknown fields. :class:`KernelError` is re-exported from :mod:`aero_kernel.errors`.
"""

import json
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self

from aero_kernel.errors import (
    ErrorCategory,
    KernelError,
    check_finite_json,
    parse_world_assignment,
    qualify,
)
from aero_kernel.geometry import AirplaneGeometry
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

__all__ = [
    "WARNING_CATALOGUE",
    "AircraftInput",
    "AirplaneGeometry",
    "ComputeRequest",
    "ComputeResult",
    "DefaultUsed",
    "Interval",
    "KernelError",
    "KernelWarning",
    "Polar",
    "Provenance",
    "QuantityResult",
    "QuantityStatus",
    "Reason",
    "ReasonCode",
    "WarningSeverity",
    "dedupe_warnings",
]


class WarningSeverity(StrEnum):
    """Whether a warning is domain practice or a defect (ADR 0020, ch. 8.2)."""

    PRACTICE = "practice"
    DEFECT = "defect"


# Numbers in a result are strict (an int or float, never a bool or a string) and finite (ch. 8.3):
# NaN and infinity do not survive a JSON round trip.
FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]

# The closed warning table (ch. 8.2): code -> fixed severity. A new code is added here by the unit
# that builds its source, never invented at the raise site.
WARNING_CATALOGUE: Mapping[str, WarningSeverity] = {
    "conflicting_mass": WarningSeverity.PRACTICE,
    "default_target_used": WarningSeverity.PRACTICE,
    "deflection_without_flap": WarningSeverity.PRACTICE,
    "geometry_deflection_ignored": WarningSeverity.PRACTICE,
    "reference_wing_at_centreline": WarningSeverity.PRACTICE,
    "precondition_unchecked": WarningSeverity.PRACTICE,
    "precondition_violated": WarningSeverity.DEFECT,
    "postcondition_unchecked": WarningSeverity.PRACTICE,
    "postcondition_violated": WarningSeverity.DEFECT,
    "reynolds_outside_band": WarningSeverity.DEFECT,
    "reynolds_bubble_sensitive": WarningSeverity.PRACTICE,
    "mach_above_limit": WarningSeverity.PRACTICE,
    "mach_beyond_validity": WarningSeverity.DEFECT,
}


class KernelWarning(BaseModel):
    """A value with a caveat (ch. 8.2); the ``DesignWarning`` shape of ADR 0020.

    The quantity a warning is reported on is the result that lists it, so there is no
    ``quantity`` field.

    Attributes:
        severity: ``practice`` (domain practice) or ``defect``; fixed by the code, so it must match
            :data:`WARNING_CATALOGUE`. :meth:`of` takes it from there.
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

    @classmethod
    def of(
        cls,
        code: str,
        message: str,
        *,
        origin: str | None = None,
        world: str | None = None,
        detail: dict[str, JsonValue] | None = None,
    ) -> Self:
        """Build a warning whose severity is the catalogue's for ``code``.

        Args:
            code: Code from :data:`WARNING_CATALOGUE`.
            message: The caveat, in natural language.
            origin: Slug of the quantity where the warning arose, if known.
            world: Method world the warning arose in.
            detail: Structured values the warning carries.

        Returns:
            The warning.

        Raises:
            ValueError: If the code is not in the catalogue, or the other fields are invalid.
        """
        severity = WARNING_CATALOGUE.get(code)
        if severity is None:
            msg = f"code {code} is not in the warning catalogue; add it to WARNING_CATALOGUE"
            raise ValueError(msg)
        return cls(
            severity=severity,
            code=code,
            message=message,
            origin=origin,
            world=world,
            detail=detail or {},
        )

    @model_validator(mode="after")
    def _check_code(self) -> Self:
        """Reject codes outside the table, a contradicting severity and a malformed world."""
        if self.world is not None:
            parse_world_assignment(self.world)
        check_finite_json(self.detail, "detail")
        expected = WARNING_CATALOGUE.get(self.code)
        if expected is None:
            msg = f"code {self.code} is not in the warning catalogue; add it to WARNING_CATALOGUE"
            raise ValueError(msg)
        if self.severity is not expected:
            msg = f"code {self.code} has severity {expected.value}, not {self.severity.value}"
            raise ValueError(msg)
        return self


def _warning_key(warning: KernelWarning) -> str:
    """Return the identity of a warning: its full content, canonically serialised (ch. 8.2).

    Two warnings are the same only if code, origin, world, message and detail all agree, so the
    same warning reaching a quantity along several paths collapses while two devices stay two.
    The key is the exact JSON content: ``1`` and ``1.0`` in ``detail``, and ``-0.0`` and ``0.0``,
    count as different.
    """
    return json.dumps(warning.model_dump(mode="json"), sort_keys=True)


def dedupe_warnings(warnings: Iterable[KernelWarning]) -> tuple[KernelWarning, ...]:
    """Drop repeated warnings, those equal in every field; the first occurrence wins.

    Equality is that of the exact JSON content (see :func:`_warning_key`): ``1`` vs ``1.0`` and
    ``-0.0`` vs ``0.0`` in ``detail`` are different warnings.

    Args:
        warnings: Warnings of a quantity and its subtree, in collection order.

    Returns:
        The warnings without repeats, order kept.
    """
    unique: dict[str, KernelWarning] = {}
    for warning in warnings:
        unique.setdefault(_warning_key(warning), warning)
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

    min: FiniteFloat
    max: FiniteFloat
    worlds: dict[str, FiniteFloat] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_worlds(self) -> Self:
        """Require canonical world keys, and min and max to be the extremes of the values."""
        formula_sets = {frozenset(parse_world_assignment(key)) for key in self.worlds}
        if len(formula_sets) != 1:
            msg = "every world assignment must assign the same formulas (Cartesian product)"
            raise ValueError(msg)
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
        unit: SI unit of ``value`` and ``interval``; ``None`` exactly when the kernel knows no
            quantity of that slug (unknown or malformed slug, or no loadable model), required for ``ok``.
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
    unit: str | None = Field(default=None, min_length=1)
    status: QuantityStatus
    reason: Reason | None = None
    value: FiniteFloat | None = None
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
        keys = [_warning_key(w) for w in self.warnings]
        if len(set(keys)) != len(keys):
            msg = "duplicate warning: identical warnings must be collapsed within a quantity"
            raise ValueError(msg)
        if self.from_cache and self.status is not QuantityStatus.OK:
            msg = f"from_cache requires status ok, not {self.status.value}: only ok is stored"
            raise ValueError(msg)
        has_result = self.value is not None or self.interval is not None
        if self.status is QuantityStatus.OK:
            if (self.value is None) == (self.interval is None):
                msg = "status ok needs exactly one of value and interval"
                raise ValueError(msg)
            if self.error is not None:
                msg = "status ok must not carry an error"
                raise ValueError(msg)
            for name, text in (
                ("unit", self.unit),
                ("tool", self.tool),
                ("application", self.application),
            ):
                if not text:
                    msg = f"status ok needs {name}: every value leads back to its application and tool"
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
    value: FiniteFloat
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)


class Provenance(BaseModel):
    """What a result was computed with (ch. 8.4).

    Attributes:
        build_digest: Hash over the code and canon model; identifies the exact build.
        canon_model_hash: Hash of the canon model; ``None`` only when the shipped model could
            not be loaded.
        tool_versions: Version per tool (aerosandbox, NeuralFoil model, AVL).
        solver_settings: Solver settings of the call.
        defaults_used: Every canon default the call took.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_digest: str = Field(min_length=1)
    canon_model_hash: str | None = Field(default=None, min_length=1)
    tool_versions: dict[
        Annotated[str, Field(min_length=1)], Annotated[str, Field(min_length=1)]
    ] = Field(default_factory=dict)
    solver_settings: dict[str, JsonValue] = Field(default_factory=dict)
    defaults_used: tuple[DefaultUsed, ...] = ()

    @model_validator(mode="after")
    def _check_solver_settings(self) -> Self:
        """Reject NaN and infinity anywhere in the solver settings."""
        check_finite_json(self.solver_settings, "solver_settings")
        return self


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


class Polar(BaseModel):
    """A sampled whole-aircraft polar over angle of attack (ch. 8.12): the solver's own values.

    Attributes:
        alpha_deg: Angle of attack in degrees, strictly rising.
        cl: Lift coefficient, normalised by the reference area of the airplane.
        cd: Drag coefficient (the solver's drag, not a fitted parabola, ADR 0026).
        cm: Pitching-moment coefficient about the airplane's reference point.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    alpha_deg: tuple[FiniteFloat, ...] = Field(min_length=2)
    cl: tuple[FiniteFloat, ...]
    cd: tuple[FiniteFloat, ...]
    cm: tuple[FiniteFloat, ...]

    @model_validator(mode="after")
    def _check_series(self) -> Self:
        """Require equally long series and a strictly rising angle of attack."""
        lengths = {len(self.alpha_deg), len(self.cl), len(self.cd), len(self.cm)}
        if len(lengths) != 1:
            msg = "alpha_deg, cl, cd and cm must have the same length"
            raise ValueError(msg)
        if any(b <= a for a, b in zip(self.alpha_deg, self.alpha_deg[1:], strict=False)):
            msg = "alpha_deg must be strictly rising"
            raise ValueError(msg)
        return self


class AircraftInput(BaseModel):
    """The aircraft of a call (ch. 8.11): geometry plus the input and target values.

    Types only: a well-typed but inadmissible value (NaN, a negative mass) parses and becomes an
    ``input_errors`` entry in ``validate.py``. The mass is only ever ``values["aircraft-mass"]``.

    Attributes:
        airplane: The geometry document; its millimetre fields are metres once parsed.
        values: Value per canon input or target slug, in the quantity's SI unit.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    values: dict[Annotated[str, Field(min_length=1)], Annotated[float, Field(strict=True)]] = Field(
        default_factory=dict
    )


class ComputeRequest(BaseModel):
    """What to compute (ch. 8.11): quantities by canon slug, plus the call's solver settings.

    Attributes:
        quantities: Canon quantity slugs (not formula slugs); at least one, each once.
        include_long_runs: Whether quantities of cost class ``minutes`` run (ch. 8.7).
        time_budget_s: One wall-clock budget in seconds for the whole request, or ``None`` for
            none (ch. 8.10). Quantities still open when it expires are ``timeout`` errors; the
            finished ones are returned. Admissibility (finite, > 0) is validation's.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    quantities: tuple[Annotated[str, Field(min_length=1)], ...] = Field(min_length=1)
    include_long_runs: bool = Field(default=False, strict=True)
    time_budget_s: float | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def _check_unique_quantities(self) -> Self:
        """Reject a quantity requested twice, also in two spellings (bare means ``calc:``).

        A malformed slug is compared by its raw spelling: it is an unknown quantity, which the
        graph reports per quantity.
        """
        seen: dict[str, str] = {}
        for slug in self.quantities:
            try:
                qualified = qualify(slug)
            except ValueError:  # malformed: an unknown quantity, reported per quantity (ch. 8.11)
                qualified = slug
            if qualified in seen:
                first = seen[qualified]
                msg = f"duplicate quantity in request: {slug}" + (
                    "" if first == slug else f" (the same quantity as {first})"
                )
                raise ValueError(msg)
            seen[qualified] = slug
        return self
