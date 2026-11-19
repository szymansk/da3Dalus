"""Result types of the kernel (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4).

Warnings, quantity results, the compute result and provenance. All models are frozen and reject
unknown fields. :class:`KernelError` is re-exported from :mod:`aero_kernel.errors`.
"""

import json
import math
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self

from aero_kernel.components import Components
from aero_kernel.errors import (
    ErrorCategory,
    KernelError,
    check_finite_json,
    parse_world_assignment,
    qualify,
)
from aero_kernel.geometry import AirplaneGeometry
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)

__all__ = [
    "WARNING_CATALOGUE",
    "AircraftInput",
    "AirplaneGeometry",
    "ComputeRequest",
    "ComputeResult",
    "Curve",
    "CurveResult",
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
    "RuleUsed",
    "StallCurve",
    "TimeBounds",
    "Timing",
    "WarningSeverity",
    "dedupe_warnings",
]


class WarningSeverity(StrEnum):
    """The three severities of ADR 0020 (ch. 8.2), fixed per warning code.

    ``notice``: a legitimate, declared substitution (domain practice). ``warning``: the number is
    usable, its confidence reduced. ``error``: the number is not physically meaningful; do not build
    on it. A value that cannot be computed at all is a ``KernelError``, never a warning.
    """

    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"


# Numbers in a result are strict (an int or float, never a bool or a string) and finite (ch. 8.3):
# NaN and infinity do not survive a JSON round trip.
FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]

# The closed warning table (ch. 8.2): code -> fixed severity. A new code is added here by the unit
# that builds its source, never invented at the raise site.
WARNING_CATALOGUE: Mapping[str, WarningSeverity] = {
    "conflicting_mass": WarningSeverity.NOTICE,
    "default_target_used": WarningSeverity.NOTICE,
    "deflection_without_flap": WarningSeverity.NOTICE,
    "geometry_deflection_ignored": WarningSeverity.NOTICE,
    "hinge_line_averaged": WarningSeverity.NOTICE,
    "aileron_deflection_beyond_reference": WarningSeverity.NOTICE,
    "control_surface_fit_range_unknown": WarningSeverity.NOTICE,
    "avl_flap_linearised": WarningSeverity.NOTICE,
    "flap_confidence_low": WarningSeverity.WARNING,
    "flap_deflection_beyond_validity": WarningSeverity.WARNING,
    "fuselage_not_modelled": WarningSeverity.NOTICE,
    "world_outside_validity": WarningSeverity.NOTICE,
    "avl_mesh_not_converged": WarningSeverity.WARNING,
    "avl_roll_rate_beyond_range": WarningSeverity.WARNING,
    "avl_refinement_unchecked": WarningSeverity.WARNING,
    "stall_break_resolution": WarningSeverity.WARNING,
    "precondition_unchecked": WarningSeverity.NOTICE,
    "precondition_violated": WarningSeverity.WARNING,
    "postcondition_unchecked": WarningSeverity.NOTICE,
    "postcondition_violated": WarningSeverity.WARNING,
    "reynolds_outside_band": WarningSeverity.WARNING,
    "reynolds_bubble_sensitive": WarningSeverity.NOTICE,
    "reynolds_above_band": WarningSeverity.NOTICE,
    "reynolds_outside_band_at_device": WarningSeverity.WARNING,
    "mach_above_limit": WarningSeverity.NOTICE,
    "mach_beyond_validity": WarningSeverity.ERROR,
    "minimum_sink_stall_limited": WarningSeverity.NOTICE,
    "avl_body_equivalent_round": WarningSeverity.NOTICE,
    "spiral_halving_time_reported": WarningSeverity.NOTICE,
    "fuselage_section_equivalent": WarningSeverity.NOTICE,
    "canopy_merged_into_fuselage": WarningSeverity.NOTICE,
    "canopy_merge_exponent_clamped": WarningSeverity.WARNING,
    "canopy_off_centre": WarningSeverity.WARNING,
    "spinner_merged_into_body": WarningSeverity.NOTICE,
    "spinner_merge_exponent_clamped": WarningSeverity.WARNING,
    "fuselage_axis_straightened": WarningSeverity.NOTICE,
    "induced_drag_viscous_factor_removed": WarningSeverity.NOTICE,
    "powertrain_route_winding_resistance": WarningSeverity.NOTICE,
    "small_glide_angle": WarningSeverity.WARNING,
    "polar_fit_residual": WarningSeverity.NOTICE,
    "polar_fit_nonphysical": WarningSeverity.ERROR,
    "hinge_moment_inviscid_estimate": WarningSeverity.NOTICE,
    "hinge_moment_pitch_untrimmed": WarningSeverity.NOTICE,
    "powered_limit_declared": WarningSeverity.NOTICE,
    "powered_speeds_skipped": WarningSeverity.NOTICE,
    "optimum_at_domain_bound": WarningSeverity.WARNING,
}


class KernelWarning(BaseModel):
    """A value with a caveat (ch. 8.2); the ``DesignWarning`` shape of ADR 0020.

    The quantity a warning is reported on is the result that lists it, so there is no
    ``quantity`` field.

    Attributes:
        severity: ``notice``, ``warning`` or ``error`` (ADR 0020); fixed by the code, so it must
            match :data:`WARNING_CATALOGUE`. :meth:`of` takes it from there.
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


# A measured run time in seconds: finite and never negative.
Seconds = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=0)]


class TimeBounds(BaseModel):
    """A run time known between two bounds, in seconds (ch. 8.3).

    Attributes:
        lower: The lower bound.
        upper: The upper bound; equal to ``lower`` when the time is known exactly.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    lower: Seconds
    upper: Seconds

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        """Require the lower bound not to exceed the upper one."""
        if self.lower > self.upper:
            msg = "the lower bound must not exceed the upper bound"
            raise ValueError(msg)
        return self


# Relative tolerance of the sum check in ``Timing``: the bounds are sums of floats.
_SUM_TOLERANCE = 1e-9


class Timing(BaseModel):
    """The measured run time of a quantity and of the chain before it, in seconds (ch. 8.3).

    The engine runs the independent nodes of a layer concurrently, so the time of the chain before
    a quantity is known only between two bounds:

    - ``upper`` is the **sum** of the own upper bounds of all distinct upstream nodes, each counted
      once even when two branches share it: the cost of the chain.
    - ``lower`` is the **longest path** through the upstream nodes by their own lower bounds: the
      earliest the quantity could start with unlimited concurrency.

    A node with several method worlds runs once per world assignment (ch. 8.13); its own upper bound
    is the sum of its runs, its own lower bound the longest single run. A node run once has equal
    bounds. A value served from the cache reports the time measured when it was computed.

    Attributes:
        own_s: The run time of the node that produces the quantity.
        before_s: The run time of the upstream nodes only (all ancestors of the producing node).
        total_s: ``before_s`` plus ``own_s``, bound by bound.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    own_s: TimeBounds
    before_s: TimeBounds
    total_s: TimeBounds

    @classmethod
    def of(cls, *, own: TimeBounds, before: TimeBounds) -> Self:
        """The timing of a node with its own bounds and those of the chain before it."""
        return cls(
            own_s=own,
            before_s=before,
            total_s=TimeBounds(lower=before.lower + own.lower, upper=before.upper + own.upper),
        )

    @model_validator(mode="after")
    def _check_total(self) -> Self:
        """Require the total to be the time before plus the own time, bound by bound."""
        pairs = (
            (self.total_s.lower, self.before_s.lower + self.own_s.lower),
            (self.total_s.upper, self.before_s.upper + self.own_s.upper),
        )
        if not all(math.isclose(a, b, rel_tol=_SUM_TOLERANCE) for a, b in pairs):
            msg = "total_s must be before_s plus own_s, bound by bound"
            raise ValueError(msg)
        return self


class Curve(BaseModel):
    """A sampled function of one variable (ch. 8.12): the canon type ``curve``.

    Attributes:
        x: The variable, strictly rising; empty where the curve has no point (a glide angle
            that does not exist).
        y: The value at each sample.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: tuple[FiniteFloat, ...]
    y: tuple[FiniteFloat, ...]

    @model_validator(mode="after")
    def _check_series(self) -> Self:
        """Require equally long series and a strictly rising variable (empty: no point)."""
        if len(self.x) != len(self.y):
            msg = "x and y must have the same length"
            raise ValueError(msg)
        if any(b <= a for a, b in zip(self.x, self.x[1:], strict=False)):
            msg = "x must be strictly rising"
            raise ValueError(msg)
        return self


class CurveResult(Curve):
    """A curve as the result of a ``curve`` quantity: the samples and what ``x`` is (ch. 8.3).

    ``y`` is in the result's ``unit``; ``x`` is the abscissa the canon declares for the quantity.

    Attributes:
        x_quantity: Slug of the canon quantity the curve runs over (the crow mix, the mass, the
            spanwise station).
        x_unit: Unit of ``x``, the unit of that quantity.
    """

    x_quantity: str = Field(min_length=1)
    x_unit: str = Field(min_length=1)


class QuantityResult(BaseModel):
    """The result for one requested quantity (ch. 8.3).

    Attributes:
        slug: Canon slug of the quantity.
        unit: SI unit of ``value`` and ``interval``; ``None`` exactly when the kernel knows no
            quantity of that slug (unknown or malformed slug, or no loadable model), required for ``ok``.
        status: Outcome class.
        reason: Why the quantity is ``not_applicable`` or ``skipped``.
        value: The value of a scalar quantity.
        surfaces: The value of a ``per_control_surface`` quantity: per surface key, per application
            id, the value in ``unit``. The union of the applicable applications' entries; a
            dual-role surface has one entry per role.
        curve: The value of a ``curve`` quantity: the samples ``x`` and ``y``, ``y`` in ``unit``,
            with the canon quantity ``x`` runs over and its unit (``x_quantity``, ``x_unit``).
        interval: The spread over method worlds, for an uncertain quantity.
        tool: Tool that produced the value.
        application: Id of the application that produced the value.
        validated: Always ``False``: no value is validated against flight data (A11).
        warnings: Caveats of this quantity and its subtree.
        error: Why there is no value, for status ``error``.
        from_cache: Whether the value was served from the cache.
        timing: The measured run time of the quantity and of the chain before it, for a quantity
            whose producing node ran in every world assignment, ``ok`` or ``error``. ``None`` for
            ``not_applicable`` and ``skipped`` (the formula did not run), for a quantity the graph
            rejected before anything ran, and for one still open when the time budget expired.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(min_length=1)
    unit: str | None = Field(default=None, min_length=1)
    status: QuantityStatus
    reason: Reason | None = None
    value: FiniteFloat | None = None
    surfaces: dict[str, dict[str, FiniteFloat]] | None = None
    interval: Interval | None = None
    curve: CurveResult | None = None
    tool: str | None = None
    application: str | None = None
    validated: Literal[False] = False
    warnings: tuple[KernelWarning, ...] = ()
    error: KernelError | None = None
    from_cache: bool = False
    timing: Timing | None = None

    @model_validator(mode="after")
    def _check_timing(self) -> Self:
        """Only a quantity whose formula ran carries a timing."""
        if self.timing is not None and self.status in (
            QuantityStatus.NOT_APPLICABLE,
            QuantityStatus.SKIPPED,
        ):
            msg = f"status {self.status.value} must not carry a timing: the formula did not run"
            raise ValueError(msg)
        return self

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
        carried = (self.value, self.interval, self.surfaces, self.curve)
        has_result = any(x is not None for x in carried)
        if self.status is QuantityStatus.OK:
            if sum(x is not None for x in carried) != 1:
                msg = "status ok needs exactly one of value, interval, surfaces and curve"
                raise ValueError(msg)
            if self.surfaces is not None and (not self.surfaces or not all(self.surfaces.values())):
                msg = "surfaces needs at least one surface, each with at least one application"
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
            msg = (
                f"status {self.status.value} must not carry a value or interval, surfaces or curve"
            )
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


class RuleUsed(BaseModel):
    """A threshold of a validation rule that the call used (gh-1260, ADR 0020).

    Attributes:
        rule: The rule id in the canon's ``rules.yaml``.
        parameter: The name of the parameter.
        value: The value used, in ``unit``: the canon's, or the caller's override.
        unit: The unit of ``value``.
        basis: What kind of value the canon's parameter is (``convention``, ``sourced`` ...).
        overridden: Whether the caller's override replaced the canon value.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str = Field(min_length=1)
    parameter: str = Field(min_length=1)
    value: FiniteFloat
    unit: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    overridden: bool


class Provenance(BaseModel):
    """What a result was computed with (ch. 8.4).

    Attributes:
        build_digest: Hash over the code and canon model; identifies the exact build.
        canon_model_hash: Hash of the canon model; ``None`` only when the shipped model could
            not be loaded.
        tool_versions: Version per tool (aerosandbox, NeuralFoil model, AVL).
        solver_settings: Solver settings of the call.
        defaults_used: Every canon default the call took.
        rules_used: Every validation threshold the call used, with the caller's overrides marked.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_digest: str = Field(min_length=1)
    canon_model_hash: str | None = Field(default=None, min_length=1)
    tool_versions: dict[
        Annotated[str, Field(min_length=1)], Annotated[str, Field(min_length=1)]
    ] = Field(default_factory=dict)
    solver_settings: dict[str, JsonValue] = Field(default_factory=dict)
    defaults_used: tuple[DefaultUsed, ...] = ()
    rules_used: tuple[RuleUsed, ...] = ()

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


class FlowConditions(BaseModel):
    """The flow a polar was computed at: speed and the air state (so a reader can re-sweep it).

    Attributes:
        v_ms: True airspeed in m/s.
        density: Air density in kg/m^3.
        dynamic_viscosity: Dynamic viscosity in Pa s.
        speed_of_sound: Speed of sound in m/s.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_ms: float = Field(gt=0.0, allow_inf_nan=False)
    density: float = Field(gt=0.0, allow_inf_nan=False)
    dynamic_viscosity: float = Field(gt=0.0, allow_inf_nan=False)
    speed_of_sound: float = Field(gt=0.0, allow_inf_nan=False)


class Polar(BaseModel):
    """A sampled whole-aircraft polar over angle of attack (ch. 8.12): the solver's own values.

    Attributes:
        alpha_deg: Angle of attack in degrees, strictly rising.
        cl: Lift coefficient, normalised by the reference area of the airplane.
        cd: Drag coefficient (the solver's drag, not a fitted parabola, ADR 0026).
        conditions: The flow the sweep was computed at; ``None`` for a polar built by hand.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    alpha_deg: tuple[FiniteFloat, ...] = Field(min_length=2)
    cl: tuple[FiniteFloat, ...]
    cd: tuple[FiniteFloat, ...]
    conditions: FlowConditions | None = None

    @model_validator(mode="after")
    def _check_series(self) -> Self:
        """Require equally long series and a strictly rising angle of attack."""
        lengths = {len(self.alpha_deg), len(self.cl), len(self.cd)}
        if len(lengths) != 1:
            msg = "alpha_deg, cl and cd must have the same length"
            raise ValueError(msg)
        if any(b <= a for a, b in zip(self.alpha_deg, self.alpha_deg[1:], strict=False)):
            msg = "alpha_deg must be strictly rising"
            raise ValueError(msg)
        return self


class StallCurve(Curve):
    """A stall speed over a swept variable, with the sweep each point was solved on (ch. 8.12).

    The postcondition ``optimum_at_first_cl_peak`` is checked at every point, so the curve carries
    what the check reads: the stall angle, the lift coefficient and the sweep of each point.

    Attributes:
        alpha_s: The stall angle of each point in degrees.
        cl_max: The lift coefficient at each stall.
        polars: The sweep at each point's stall speed, with ``alpha_s`` among its samples.
    """

    alpha_s: tuple[FiniteFloat, ...]
    cl_max: tuple[FiniteFloat, ...]
    polars: tuple[Polar, ...]

    @model_validator(mode="after")
    def _check_points(self) -> Self:
        """Require one stall angle, coefficient and sweep per point."""
        if not len(self.alpha_s) == len(self.cl_max) == len(self.polars) == len(self.x):
            msg = "alpha_s, cl_max and polars must have one entry per point"
            raise ValueError(msg)
        return self


class AircraftInput(BaseModel):
    """The aircraft of a call (ch. 8.11): geometry plus the input and target values.

    Types only: a well-typed but inadmissible value (NaN, a negative mass) parses and becomes an
    ``input_errors`` entry in ``validate.py``. The mass is only ever ``values["aircraft-mass"]``.

    Attributes:
        airplane: The geometry document; its millimetre fields are metres once parsed.
        components: The fitted motor, battery and propeller, a contract of its own; ``None`` if
            none are pushed (the quantities that read them are then ``missing_input``).
        values: Value per canon input or target slug, in the quantity's SI unit.
        rule_overrides: Value per ``<rule>.<parameter>`` of the canon's ``rules.yaml``, for an expert
            user whose aircraft breaks a convention (e.g. a main wing inclined past 45 deg); each
            override used is declared in the provenance.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    airplane: AirplaneGeometry
    components: Components | None = None
    values: dict[Annotated[str, Field(min_length=1)], Annotated[float, Field(strict=True)]] = Field(
        default_factory=dict
    )
    rule_overrides: dict[
        Annotated[str, Field(min_length=1)], Annotated[float, Field(strict=True)]
    ] = Field(default_factory=dict)


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
