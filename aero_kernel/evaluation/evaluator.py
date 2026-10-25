"""Evaluate a kernel result against a rule table (maintainer, 2026-10-25).

A pure function: nothing is read, cached or computed. The canon computes and never judges (A10);
this package is the only place that says whether a computed value is inside a band. An uncertain
quantity (A11) is judged at both ends of its interval: it is ``inside`` only if the whole interval
is inside the band, ``below`` or ``above`` only if the whole interval is, and ``partly`` otherwise.
"""

from enum import StrEnum

from aero_kernel.evaluation.rules import Band, Position, Rule, RuleTable, Severity
from aero_kernel.graph import PENDING_WHEN_TERMS, WhenFacts
from aero_kernel.schema import (
    ComputeResult,
    Interval,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
)
from pydantic import BaseModel, ConfigDict

_NO_CONSEQUENCE = "the source names no consequence."

__all__ = ["RuleStatus", "RuleVerdict", "evaluate_rules", "quantities_to_request"]


class RuleStatus(StrEnum):
    """The outcome of one rule."""

    INSIDE = "inside"
    BELOW = "below"
    ABOVE = "above"
    PARTLY = "partly"
    NOT_APPLICABLE = "not_applicable"
    NOT_AVAILABLE = "not_available"


class RuleVerdict(BaseModel):
    """The verdict on one rule.

    Attributes:
        rule_id: Id of the rule.
        status: The outcome.
        value: The judged value, for a scalar quantity.
        interval: The judged spread over method worlds, for an uncertain quantity.
        unit: Unit of the value and of the band.
        band: The rule's band, copied so a verdict stands alone.
        severity: For ``below``, ``above`` and ``partly``: how bad the side or sides left are; the
            worst when an interval reaches both.
        level: Name of the rule's level that contains the value, if any.
        explanation: A sentence saying why, with the source's meaning where the band is left.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    status: RuleStatus
    value: float | None = None
    interval: Interval | None = None
    unit: str
    band: Band
    severity: Severity | None = None
    level: str | None = None
    explanation: str


def quantities_to_request(table: RuleTable) -> tuple[str, ...]:
    """List the canon quantities a caller must request for the table to be judged.

    Args:
        table: The rule table.

    Returns:
        The distinct slugs of the rules whose quantity is in the canon, in table order.
    """
    slugs = [rule.quantity.slug for rule in table.rules if rule.quantity.planned is None]
    return tuple(dict.fromkeys(slugs))


def evaluate_rules(
    table: RuleTable, result: ComputeResult, facts: WhenFacts
) -> tuple[RuleVerdict, ...]:
    """Judge every rule of a table.

    Args:
        table: The rule table.
        result: The kernel result; it need not contain every rule's quantity.
        facts: The ``when`` facts of the aircraft geometry.

    Returns:
        One verdict per rule, in table order.
    """
    by_slug = {quantity.slug: quantity for quantity in result.quantities}
    return tuple(_judge(rule, by_slug.get(rule.quantity.slug), facts) for rule in table.rules)


def _verdict(rule: Rule, status: RuleStatus, explanation: str, **extra: object) -> RuleVerdict:
    """Build a verdict of a rule."""
    return RuleVerdict.model_validate(
        {
            "rule_id": rule.id,
            "status": status,
            "unit": rule.unit,
            "band": rule.band,
            "explanation": explanation,
            **extra,
        }
    )


def _judge(rule: Rule, quantity: QuantityResult | None, facts: WhenFacts) -> RuleVerdict:
    """Judge one rule: conditions first, then availability, then the value."""
    unmet = _unmet_condition(rule, facts)
    if unmet is not None:
        return unmet
    if rule.quantity.planned is not None:
        return _verdict(
            rule,
            RuleStatus.NOT_AVAILABLE,
            f"`{rule.quantity.slug}` is not in the canon yet ({rule.quantity.planned}).",
        )
    if quantity is None:
        return _verdict(
            rule,
            RuleStatus.NOT_AVAILABLE,
            f"`{rule.quantity.slug}` is not in the result; request it from the kernel.",
        )
    if quantity.status is QuantityStatus.NOT_APPLICABLE:
        reason = quantity.reason.message if quantity.reason is not None else "no reason given"
        if quantity.reason is not None and quantity.reason.code is ReasonCode.NOT_GIVEN:
            # Not a property of the aircraft: the caller has not supplied what the quantity needs.
            return _verdict(rule, RuleStatus.NOT_AVAILABLE, f"Not supplied: {reason}")
        return _verdict(
            rule, RuleStatus.NOT_APPLICABLE, f"The kernel found it not applicable: {reason}"
        )
    if quantity.status is not QuantityStatus.OK:
        return _verdict(
            rule,
            RuleStatus.NOT_AVAILABLE,
            f"`{rule.quantity.slug}` has no value (status {quantity.status.value}).",
        )
    return _judge_value(rule, quantity)


def _unmet_condition(rule: Rule, facts: WhenFacts) -> RuleVerdict | None:
    """Return the verdict of a rule whose geometry conditions do not allow a judgement, else ``None``."""
    for term in (*rule.when, *rule.when_not):
        if term in PENDING_WHEN_TERMS:
            return _verdict(
                rule,
                RuleStatus.NOT_AVAILABLE,
                f"The condition `{term}` cannot be evaluated yet ({PENDING_WHEN_TERMS[term]}).",
            )
    for term in rule.when:
        if not facts.holds(term):
            return _verdict(
                rule, RuleStatus.NOT_APPLICABLE, f"The rule applies only when `{term}` holds."
            )
    for term in rule.when_not:
        if facts.holds(term):
            return _verdict(
                rule, RuleStatus.NOT_APPLICABLE, f"The rule does not apply when `{term}` holds."
            )
    return None


def _judge_value(rule: Rule, quantity: QuantityResult) -> RuleVerdict:
    """Judge a computed scalar or interval against the band."""
    if quantity.interval is not None:
        interval = quantity.interval
        ends = (interval.min, interval.max)
        extra: dict[str, object] = {"interval": interval}
        text = f"{interval.min:.4g}…{interval.max:.4g} {rule.unit}"
    else:
        assert quantity.value is not None  # status ok carries exactly one of the two
        ends = (quantity.value, quantity.value)
        extra = {"value": quantity.value}
        text = f"{quantity.value:.4g} {rule.unit}"
    positions = {rule.band.position(end) for end in ends}
    levels = {rule.level_of(end) for end in ends}
    level = next(iter(levels)) if len(levels) == 1 else None
    if level is not None:
        extra["level"] = level
    status = _status_of(positions)
    severity = _severity_of(rule, positions)
    if severity is not None:
        extra["severity"] = severity
    return _verdict(rule, status, _explain(rule, status, text, positions, level), **extra)


def _severity_of(rule: Rule, positions: set[Position]) -> Severity | None:
    """The worst severity of the sides a value reaches outside the band, if any."""
    found: set[Severity] = set()
    if Position.BELOW in positions:
        found.add(rule.below_severity)
    if Position.ABOVE in positions:
        found.add(rule.above_severity)
    if Severity.BAD in found:
        return Severity.BAD
    return Severity.CAUTION if found else None


def _status_of(positions: set[Position]) -> RuleStatus:
    """Combine the positions of the ends of a value: all the same, or ``partly``."""
    if len(positions) > 1:
        return RuleStatus.PARTLY
    return {
        Position.INSIDE: RuleStatus.INSIDE,
        Position.BELOW: RuleStatus.BELOW,
        Position.ABOVE: RuleStatus.ABOVE,
    }[next(iter(positions))]


def _band_text(band: Band) -> str:
    """Write a band as ``low…high``, ``≥ low`` or ``≤ high``."""
    if band.min is not None and band.max is not None:
        return f"{band.min:g}…{band.max:g}"
    if band.min is not None:
        return f"≥ {band.min:g}"
    return f"≤ {band.max:g}"


def _explain(
    rule: Rule, status: RuleStatus, text: str, positions: set[Position], level: str | None
) -> str:
    """Write the explanation: the value, the band, the source and the meaning of leaving it."""
    band = _band_text(rule.band)
    verb = {
        RuleStatus.INSIDE: "lies inside",
        RuleStatus.BELOW: "lies below",
        RuleStatus.ABOVE: "lies above",
        RuleStatus.PARTLY: "reaches outside",
    }[status]
    parts = [f"{rule.title}: {text} {verb} the band {band} ({rule.source})."]
    for side, position, meaning, severity, basis in (
        ("Below", Position.BELOW, rule.below, rule.below_severity, rule.below_basis),
        ("Above", Position.ABOVE, rule.above, rule.above_severity, rule.above_basis),
    ):
        if position in positions:
            text = f"{side} ({severity.value}): {meaning or _NO_CONSEQUENCE}"
            parts.append(f"{text} Basis: {basis}." if basis else text)
    if level is not None:
        meaning = next(lv.meaning for lv in rule.levels if lv.id == level)
        parts.append(f"Level {level}: {meaning}")
    return " ".join(parts)
