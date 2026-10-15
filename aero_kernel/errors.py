"""Error catalogue of the kernel (ARCHITECTURE ch. 8.1).

An error means *no value*. A value with a caveat is a warning, not an error.
``not_applicable`` is a quantity status (ch. 8.3), not an error, so it is not a category here.

This module is independent of the result types: ``schema.py`` re-exports :class:`KernelError`.
"""

import logging
import math
import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic.config import JsonDict

logger = logging.getLogger(__name__)

__all__ = [
    "CODE_CATALOGUE",
    "WORLD_NAME_REGEX",
    "ErrorCategory",
    "FormulaError",
    "KernelError",
    "aggregate_upstream",
    "check_finite_json",
    "flags_for",
    "format_world_assignment",
    "internal_error_from_exception",
    "is_slug",
    "is_world_name",
    "parse_world_assignment",
]


class ErrorCategory(StrEnum):
    """The error categories of ch. 8.1."""

    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_CONFIGURATION = "unsupported_configuration"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_CONVERGED = "not_converged"
    TIMEOUT = "timeout"
    TOOL_UNAVAILABLE = "tool_unavailable"
    UPSTREAM_FAILED = "upstream_failed"
    INTERNAL = "internal"


# (retryable, escalate) per category, the table of ch. 8.1. ``upstream_failed`` is absent: its
# flags are derived from its root causes (see ``aggregate_upstream``).
_FLAGS: Mapping[ErrorCategory, tuple[bool, bool]] = {
    ErrorCategory.INVALID_INPUT: (False, False),
    ErrorCategory.UNSUPPORTED_CONFIGURATION: (False, False),
    ErrorCategory.NOT_IMPLEMENTED: (False, False),
    ErrorCategory.NOT_CONVERGED: (True, False),
    ErrorCategory.TIMEOUT: (True, False),
    ErrorCategory.TOOL_UNAVAILABLE: (False, True),
    ErrorCategory.INTERNAL: (False, True),
}

# The closed code table (ch. 8.1): every code belongs to exactly one category, so a root cause's
# flags follow from its code. A new code is added here, never invented at the raise site. Each
# category also has a default code equal to its name. Warning codes and the reason codes of
# non-error statuses (``condition_not_met``, ``not_given``, ...) are not in this table.
CODE_CATALOGUE: Mapping[str, ErrorCategory] = {
    **{category.value: category for category in ErrorCategory},
    "missing_input": ErrorCategory.INVALID_INPUT,
    "unresolved_airfoil": ErrorCategory.INVALID_INPUT,
    "non_finite_number": ErrorCategory.INVALID_INPUT,
    "non_positive_length": ErrorCategory.INVALID_INPUT,
    "non_positive_thickness": ErrorCategory.INVALID_INPUT,
    "non_positive_exponent": ErrorCategory.INVALID_INPUT,
    "too_few_sections": ErrorCategory.INVALID_INPUT,
    "invalid_airfoil_contour": ErrorCategory.INVALID_INPUT,
    "segment_on_last_section": ErrorCategory.INVALID_INPUT,
    "control_surface_without_device": ErrorCategory.INVALID_INPUT,
    "unknown_quantity": ErrorCategory.INVALID_INPUT,
    "not_an_input": ErrorCategory.INVALID_INPUT,
    "non_positive_value": ErrorCategory.INVALID_INPUT,
    "target_above_method_maximum": ErrorCategory.UNSUPPORTED_CONFIGURATION,
    "precondition_violated": ErrorCategory.UNSUPPORTED_CONFIGURATION,
    "postcondition_violated": ErrorCategory.UNSUPPORTED_CONFIGURATION,
    "continuous_uncertainty": ErrorCategory.NOT_IMPLEMENTED,
    "non_scalar_result": ErrorCategory.NOT_IMPLEMENTED,
}

_UPSTREAM = ErrorCategory.UPSTREAM_FAILED

# The only categories a formula or adapter may raise; the others belong to the engine (ch. 8.12).
_FORMULA_CATEGORIES = frozenset(
    {
        ErrorCategory.INVALID_INPUT,
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        ErrorCategory.NOT_CONVERGED,
        ErrorCategory.TOOL_UNAVAILABLE,
    }
)


_DETAIL_ADAPTER: TypeAdapter[dict[str, JsonValue]] = TypeAdapter(dict[str, JsonValue])


def check_finite_json(value: JsonValue, path: str) -> None:
    """Raise ``ValueError`` if a JSON tree holds NaN or infinity (ch. 8.3).

    They would serialise as ``null`` and fail re-validation.

    Args:
        value: A JSON value: dicts and lists are walked recursively.
        path: Where ``value`` sits, for the message (``detail``); extended while walking.

    Raises:
        ValueError: Naming the path of the first non-finite float.
    """
    if isinstance(value, float):
        if not math.isfinite(value):
            msg = f"{path} must be finite, got {value}"
            raise ValueError(msg)
    elif isinstance(value, dict):
        for key, item in value.items():
            check_finite_json(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_finite_json(item, f"{path}[{index}]")


def _check_code(code: str, category: ErrorCategory) -> None:
    """Raise ``ValueError`` unless ``code`` is catalogued under ``category``."""
    expected = CODE_CATALOGUE.get(code)
    if expected is None:
        msg = f"code {code} is not in the error catalogue; add it to CODE_CATALOGUE"
        raise ValueError(msg)
    if expected is not category:
        msg = f"code {code} belongs to category {expected.value}, not {category.value}"
        raise ValueError(msg)


_SLUG_PATTERN = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")


def is_slug(text: str) -> bool:
    """Tell whether ``text`` is a canon slug: kebab-case, e.g. ``aircraft-mass``."""
    return _SLUG_PATTERN.fullmatch(text) is not None


# The regular expression of a world name, public so the canon model's JSON Schema states the same.
WORLD_NAME_REGEX = r"[a-z][a-z0-9]*(_[a-z0-9]+)*"
_WORLD_PATTERN = re.compile(WORLD_NAME_REGEX)


def is_world_name(text: str) -> bool:
    """Tell whether ``text`` is a method-world name: snake_case, e.g. ``aero_buildup``."""
    return _WORLD_PATTERN.fullmatch(text) is not None


def _check_world_pair(slug: str, world: str) -> None:
    """Raise ``ValueError`` unless ``slug`` is kebab-case and ``world`` snake_case."""
    if not is_slug(slug) or not is_world_name(world):
        msg = f"world assignment has a malformed pair {slug}={world}"
        raise ValueError(msg)


def format_world_assignment(assignment: Mapping[str, str]) -> str:
    """Write a world assignment in its canonical form (ch. 8.13).

    Args:
        assignment: World name per uncertain formula slug.

    Returns:
        Pairs ``<formula-slug>=<world>`` sorted by slug and joined by ``,`` without spaces.

    Raises:
        ValueError: If the assignment is empty or a slug or world name is malformed.
    """
    if not assignment:
        msg = "world assignment must not be empty"
        raise ValueError(msg)
    for slug, world in assignment.items():
        _check_world_pair(slug, world)
    return ",".join(f"{slug}={assignment[slug]}" for slug in sorted(assignment))


def parse_world_assignment(text: str) -> dict[str, str]:
    """Parse the canonical world assignment string (ch. 8.13).

    Args:
        text: For example ``neutral-point=avl,roll-rate=aerobuildup``. A single formula's world
            is one pair, never a bare world name.

    Returns:
        World name per formula slug.

    Raises:
        ValueError: If the text is empty, a pair is malformed, the slugs are not unique or not
            sorted, or a slug (kebab-case) or world name (snake_case) is malformed.
    """
    assignment: dict[str, str] = {}
    for pair in text.split(","):
        slug, separator, world = pair.partition("=")
        if not separator:
            msg = f"world assignment {text!r} has a pair without '=': {pair!r}"
            raise ValueError(msg)
        _check_world_pair(slug, world)
        if slug in assignment:
            msg = f"world assignment {text!r} repeats formula {slug}"
            raise ValueError(msg)
        assignment[slug] = world
    if format_world_assignment(assignment) != text:
        msg = f"world assignment {text!r} is not sorted by formula slug"
        raise ValueError(msg)
    return assignment


def flags_for(category: ErrorCategory) -> tuple[bool, bool]:
    """Return ``(retryable, escalate)`` the table of ch. 8.1 prescribes for a category.

    Args:
        category: Any category except ``upstream_failed``.

    Returns:
        The two flags.

    Raises:
        ValueError: For ``upstream_failed``, whose flags derive from its causes.
    """
    if category is _UPSTREAM:
        msg = "upstream_failed has no fixed flags; derive them with aggregate_upstream()"
        raise ValueError(msg)
    return _FLAGS[category]


def _drop_default(schema: JsonDict) -> None:
    """Do not advertise the placeholder ``False`` as the real default of a flag.

    The flags default to ``False`` only so the type checker accepts omitting them; the validator
    fills the real value from the category (or requires it for ``upstream_failed``).
    """
    schema.pop("default", None)


_FLAG_DESCRIPTION = (
    "Omitted: taken from the category table (ch. 8.1); required for upstream_failed."
)


class KernelError(BaseModel):
    """A computational failure: no value (ch. 8.1).

    ``retryable`` and ``escalate`` may be omitted for every category except ``upstream_failed``; they
    then take the value of the category table. Given explicitly they must equal it. The code must
    be in :data:`CODE_CATALOGUE` under the given category. ``upstream_failed`` errors are built
    only by :func:`aggregate_upstream`.

    Attributes:
        code: Machine-readable code from the closed :data:`CODE_CATALOGUE`.
        category: The error category.
        retryable: Whether repeating the call (with other settings) can help.
        escalate: Whether an agent cannot resolve this itself and a human has to act.
        quantity: Slug of the failed quantity.
        formula: Slug of the formula that failed.
        application: Id of the application that failed.
        world: Method world that failed (ch. 8.13) as a canonical assignment string, one
            ``<formula-slug>=<world>`` pair per uncertain formula (``neutral-point=avl``).
        input_path: Path of the offending input value.
        message: The cause, in natural language.
        hint: What to do.
        detail: Structured data about the failure.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_serialization_defaults_required=True
    )

    code: str = Field(min_length=1)
    category: ErrorCategory
    retryable: bool = Field(
        default=False, description=_FLAG_DESCRIPTION, json_schema_extra=_drop_default
    )
    escalate: bool = Field(
        default=False, description=_FLAG_DESCRIPTION, json_schema_extra=_drop_default
    )
    quantity: str | None = None
    formula: str | None = None
    application: str | None = None
    world: str | None = None
    input_path: str | None = None
    message: str = Field(min_length=1)
    hint: str = Field(min_length=1)
    detail: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _fill_flags(cls, data: object) -> object:
        """Fill omitted flags from the category table; ``upstream_failed`` must give both."""
        if not isinstance(data, dict):
            return data
        raw = cast(
            "dict[str, object]", data
        )  # pydantic hands the raw mapping; keys are field names
        try:
            category = ErrorCategory(raw.get("category"))
        except ValueError:
            return raw  # the field validation reports the invalid category
        if category is _UPSTREAM:
            if "retryable" not in raw or "escalate" not in raw:
                msg = "upstream_failed requires explicit retryable and escalate (see aggregate_upstream)"
                raise ValueError(msg)
            return raw
        retryable, escalate = _FLAGS[category]
        return {"retryable": retryable, "escalate": escalate, **raw}

    @model_validator(mode="after")
    def _check_category(self) -> Self:
        """Reject flags that contradict the category or the roots, and codes outside the table."""
        _check_code(self.code, self.category)
        if self.world is not None:
            parse_world_assignment(self.world)
        check_finite_json(self.detail, "detail")
        if self.category is _UPSTREAM:
            expected = _root_flags(_roots(self))
        else:
            expected = _FLAGS[self.category]
        if (self.retryable, self.escalate) != expected:
            msg = (
                f"retryable={self.retryable}, escalate={self.escalate} contradict "
                f"{'the root causes' if self.category is _UPSTREAM else 'category ' + self.category.value}"
                " (ch. 8.1)"
            )
            raise ValueError(msg)
        return self


class FormulaError(Exception):
    """Raised by a formula for an expected failure instead of returning a substitute (ch. 8.12).

    The engine translates it into a :class:`KernelError` with :meth:`to_kernel_error`.

    Attributes:
        category: One of invalid_input, unsupported_configuration, not_converged, tool_unavailable.
        code: Machine-readable code from :data:`CODE_CATALOGUE`.
        message: The cause, in natural language.
        hint: What to do.
        detail: Structured data about the failure.
        input_path: Path of the offending input value.
    """

    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        hint: str,
        detail: Mapping[str, JsonValue] | None = None,
        input_path: str | None = None,
    ) -> None:
        """Create the error.

        Args:
            category: The error category.
            code: Machine-readable code.
            message: The cause, in natural language.
            hint: What to do.
            detail: Structured data about the failure.
            input_path: Path of the offending input value.

        Raises:
            ValueError: If the category belongs to the engine (timeout, upstream_failed,
                not_implemented, internal), the code is not catalogued under the category,
                the message or hint is empty, or the detail is not valid JSON data.
        """
        if category not in _FORMULA_CATEGORIES:
            msg = f"category {category.value} belongs to the engine; a formula cannot raise it"
            raise ValueError(msg)
        _check_code(code, category)
        for name, text in (("message", message), ("hint", hint)):
            if not text:
                msg = f"FormulaError {name} must not be empty"
                raise ValueError(msg)
        try:
            checked_detail = _DETAIL_ADAPTER.validate_python(detail or {})
        except ValidationError as error:
            msg = f"FormulaError detail must be JSON-serialisable: {error}"
            raise ValueError(msg) from error
        check_finite_json(checked_detail, "FormulaError detail")
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.hint = hint
        self.detail: dict[str, JsonValue] = checked_detail
        self.input_path = input_path

    def to_kernel_error(
        self,
        *,
        quantity: str | None = None,
        formula: str | None = None,
        application: str | None = None,
        world: str | None = None,
    ) -> KernelError:
        """Translate into a :class:`KernelError`, adding the context the engine knows.

        Args:
            quantity: Slug of the quantity being computed.
            formula: Slug of the raising formula.
            application: Id of the application.
            world: Canonical world assignment string (``neutral-point=avl``), ch. 8.13.

        Returns:
            The error with the flags of its category.
        """
        return KernelError(
            code=self.code,
            category=self.category,
            quantity=quantity,
            formula=formula,
            application=application,
            world=world,
            input_path=self.input_path,
            message=self.message,
            hint=self.hint,
            detail=self.detail,
        )


def internal_error_from_exception(
    exc: BaseException,
    *,
    quantity: str,
    formula: str | None = None,
    application: str | None = None,
    world: str | None = None,
    call_id: str | None = None,
    scope: str | None = None,
) -> KernelError:
    """Translate any exception that is not a :class:`FormulaError` into an ``internal`` error.

    Only the exception type enters the error: its text can carry file paths and internals
    (ADR 0019). The text and traceback are logged here at ``ERROR`` (the equivalent of
    ``logger.exception``, which needs an active ``except`` block) with the call context (ch. 8.14).

    Args:
        exc: The unexpected exception.
        quantity: Slug of the quantity being computed.
        formula: Slug of the raising formula.
        application: Id of the application.
        world: Canonical world assignment string (``neutral-point=avl``), ch. 8.13.
        call_id: Short id of the ``compute()`` call, for the log.
        scope: Cache scope of the call, for the log.

    Returns:
        An ``internal`` error.
    """
    logger.error(
        "internal error while computing %s: %s",
        quantity,
        exc,
        exc_info=exc,
        extra={
            "call_id": call_id,
            "quantity": quantity,
            "formula": formula,
            "application": application,
            "world": world,
            "scope": scope,
        },
    )
    return KernelError(
        code=ErrorCategory.INTERNAL.value,
        category=ErrorCategory.INTERNAL,
        quantity=quantity,
        formula=formula,
        application=application,
        world=world,
        message=f"Internal error ({type(exc).__name__}) while computing `{quantity}`.",
        hint="Report it; attach input and provenance.",
    )


def _roots(cause: KernelError) -> list[tuple[str, str]]:
    """Return the root causes (quantity, code) of an error, flattening ``upstream_failed``."""
    if cause.category is _UPSTREAM:
        entries = cause.detail.get("causes")
        if not isinstance(entries, list) or not entries:
            msg = "upstream_failed cause has no detail.causes"
            raise ValueError(msg)
        roots: list[tuple[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                msg = "upstream_failed detail.causes entries must be objects"
                raise ValueError(msg)
            quantity, code = entry.get("quantity"), entry.get("code")
            if not isinstance(quantity, str) or not isinstance(code, str):
                msg = "upstream_failed detail.causes entries need string quantity and code"
                raise ValueError(msg)
            category = CODE_CATALOGUE.get(code)
            if category is None or category is _UPSTREAM:
                msg = f"upstream_failed detail.causes entry has no root code: {code}"
                raise ValueError(msg)
            roots.append((quantity, code))
        return roots
    if cause.quantity is None:
        msg = f"root cause {cause.code} has no quantity"
        raise ValueError(msg)
    return [(cause.quantity, cause.code)]


def _root_flags(roots: Sequence[tuple[str, str]]) -> tuple[bool, bool]:
    """Combine the flags of root causes: retryable if all are, escalate if any does."""
    flags = [flags_for(CODE_CATALOGUE[code]) for _, code in roots]
    return all(r for r, _ in flags), any(e for _, e in flags)


def aggregate_upstream(
    causes: Sequence[KernelError],
    *,
    quantity: str,
    formula: str | None = None,
    application: str | None = None,
    world: str | None = None,
) -> KernelError:
    """Build the ``upstream_failed`` error of a quantity whose predecessors failed (ch. 8.1).

    ``retryable`` is true only if every root cause is retryable, ``escalate`` if any root cause
    escalates; each root's flags follow from its code through the closed table. ``detail.causes``
    lists the root causes (quantity, code), never the chain in between. This is the only
    intended way to build an ``upstream_failed`` error.

    Args:
        causes: The failed predecessors' errors; at least one.
        quantity: Slug of the quantity that cannot be computed.
        formula: Slug of its formula.
        application: Id of its application.
        world: Canonical world assignment string (``neutral-point=avl``), ch. 8.13.

    Returns:
        The ``upstream_failed`` error.

    Raises:
        ValueError: If there is no cause, or a cause has no quantity or malformed ``detail.causes``.
    """
    if not causes:
        msg = "aggregate_upstream needs at least one cause"
        raise ValueError(msg)
    roots = list(dict.fromkeys(root for cause in causes for root in _roots(cause)))
    names = ", ".join(f"`{root_quantity}`" for root_quantity in dict.fromkeys(q for q, _ in roots))
    retryable, escalate = _root_flags(roots)
    return KernelError(
        code=_UPSTREAM.value,
        category=_UPSTREAM,
        retryable=retryable,
        escalate=escalate,
        quantity=quantity,
        formula=formula,
        application=application,
        world=world,
        message=f"`{quantity}` has no value because {names} failed.",
        hint=f"Fix {names} first.",
        detail={"causes": [{"quantity": q, "code": c} for q, c in roots]},
    )
