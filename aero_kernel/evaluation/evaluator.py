"""Evaluate a kernel result against a rule table (maintainer, 2026-10-25).

A pure function: nothing is read, cached or computed. The canon computes and never judges (A10);
this package is the only place that says whether a computed value is inside a band. An uncertain
quantity (A11) is judged at both ends of its interval: it is ``inside`` only if the whole interval
is inside the band, ``below`` or ``above`` only if the whole interval is, and ``partly`` otherwise.
"""

import logging
from collections.abc import Sequence
from enum import StrEnum

from aero_kernel.evaluation.rules import (
    Band,
    Position,
    Rule,
    RuleTable,
    Severity,
    shipped_rule_table,
)
from aero_kernel.graph import PENDING_WHEN_TERMS, WhenFacts, facts_from_geometry
from aero_kernel.schema import (
    AirplaneGeometry,
    ComputeResult,
    Interval,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
)
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("aero_kernel.evaluation")

_NO_CONSEQUENCE = "the source names no consequence."

__all__ = [
    "RuleStatus",
    "RuleVerdict",
    "evaluate_rules",
    "judge_result",
    "quantities_to_request",
    "summarize_verdicts",
]


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
        quantity: Canon slug of the quantity the rule judges.
        status: The outcome.
        value: The judged value, for a scalar quantity.
        interval: The judged spread over method worlds, for an uncertain quantity.
        unit: Unit of the value and of the band.
        band: The rule's band, copied so a verdict stands alone.
        severity: For ``below``, ``above`` and ``partly``: how bad the side or sides left are; the
            worst when an interval reaches both.
        level: Name of the rule's level that contains the value, if any.
        explanation: Why, with the source's meaning where the band is left.
        text: A self-contained statement for a person or an LLM: rule, source, quantity, value
            (an interval with its worlds), band, severity, meaning and basis. Built from the rule
            table only; it is the LLM-facing contract of the evaluation layer.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    quantity: str
    status: RuleStatus
    value: float | None = None
    interval: Interval | None = None
    unit: str
    band: Band
    severity: Severity | None = None
    level: str | None = None
    explanation: str
    text: str


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
    table: RuleTable,
    result: ComputeResult,
    facts: WhenFacts,
    *,
    call_id: str | None = None,
) -> tuple[RuleVerdict, ...]:
    """Judge every rule of a table, and log the red and yellow verdicts.

    Args:
        table: The rule table.
        result: The kernel result; it need not contain every rule's quantity.
        facts: The ``when`` facts of the aircraft geometry.
        call_id: The kernel call the result came from, carried into the log records.

    Returns:
        One verdict per rule, in table order.
    """
    by_slug = {quantity.slug: quantity for quantity in result.quantities}
    verdicts = tuple(_judge(rule, by_slug.get(rule.quantity.slug), facts) for rule in table.rules)
    for verdict in verdicts:
        if verdict.severity is not None:
            _log_verdict(verdict, call_id)
    return verdicts


def judge_result(
    result: ComputeResult, airplane: AirplaneGeometry, *, call_id: str | None = None
) -> tuple[RuleVerdict, ...]:
    """Judge a kernel result against the shipped rule table, for the aircraft it was computed for.

    The caller needs neither the ``when`` facts nor the table: both follow from the geometry and
    the build.

    Args:
        result: The kernel result; it need not contain every rule's quantity.
        airplane: The geometry the result was computed for.
        call_id: The kernel call the result came from, carried into the log records.

    Returns:
        One verdict per rule of the shipped table, in table order.
    """
    return evaluate_rules(
        shipped_rule_table(), result, facts_from_geometry(airplane), call_id=call_id
    )


def _named(rule: Rule, explanation: str) -> str:
    """Make an explanation name its quantity; a value explanation already does."""
    quoted = f"`{rule.quantity.slug}`"
    return explanation if explanation.startswith(quoted) else f"{quoted}: {explanation}"


def _verdict(rule: Rule, status: RuleStatus, explanation: str, **extra: object) -> RuleVerdict:
    """Build a verdict of a rule."""
    return RuleVerdict.model_validate(
        {
            "rule_id": rule.id,
            "quantity": rule.quantity.slug,
            "status": status,
            "unit": rule.unit,
            "band": rule.band,
            "explanation": explanation,
            "text": f"{rule.title} (rule `{rule.id}`, {rule.source}): {_named(rule, explanation)}",
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
        worlds = ", ".join(f"{world}: {value:.4g}" for world, value in interval.worlds.items())
        text = f"{interval.min:.4g}…{interval.max:.4g}{_unit(rule)} over the worlds {worlds}"
    else:
        assert quantity.value is not None  # status ok carries exactly one of the two
        ends = (quantity.value, quantity.value)
        extra = {"value": quantity.value}
        text = f"{quantity.value:.4g}{_unit(rule)}"
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


def _unit(rule: Rule) -> str:
    """The unit with a leading space, empty for a dimensionless quantity."""
    return "" if rule.unit == "1" else f" {rule.unit}"


def _sentence(meaning: str | None) -> str:
    """The meaning of a side as a sentence; the source names none when it is absent."""
    return (meaning or _NO_CONSEQUENCE).rstrip(".") + "."


def _explain(
    rule: Rule, status: RuleStatus, text: str, positions: set[Position], level: str | None
) -> str:
    """Write the explanation: the value, the band and, outside it, severity, meaning and basis."""
    verb = {
        RuleStatus.INSIDE: "lies inside",
        RuleStatus.BELOW: "lies below",
        RuleStatus.ABOVE: "lies above",
        RuleStatus.PARTLY: "reaches outside",
    }[status]
    parts = [f"`{rule.quantity.slug}` = {text} {verb} the band {_band_text(rule.band)}"]
    sides = [
        (name, meaning, severity, basis)
        for name, position, meaning, severity, basis in (
            ("below", Position.BELOW, rule.below, rule.below_severity, rule.below_basis),
            ("above", Position.ABOVE, rule.above, rule.above_severity, rule.above_basis),
        )
        if position in positions
    ]
    if not sides:
        parts[0] += "."
    for name, meaning, severity, basis in sides:
        label = f"{name}, {severity.value}" if len(sides) > 1 else severity.value
        sentence = f"{label}: {_sentence(meaning)}"
        parts.append(f"{sentence} (basis: {basis})" if basis else sentence)
    if level is not None:
        level_meaning = next(lv.meaning for lv in rule.levels if lv.id == level)
        parts.append(f"Level {level}: {level_meaning}")
    if sides:
        parts[:2] = [f"{parts[0]} — {parts[1]}"]
    return " ".join(parts)


def summarize_verdicts(table: RuleTable, verdicts: Sequence[RuleVerdict]) -> str:
    """Summarise an evaluation for a person or an LLM: counts, then the red, then the yellow.

    Args:
        table: The rule table the verdicts came from.
        verdicts: The verdicts of :func:`evaluate_rules`.

    Returns:
        Text: a count line, then ``Red:`` and ``Yellow:`` sections with the verdict texts; a
        section is left out when it is empty.
    """
    red = [v for v in verdicts if v.severity is Severity.BAD]
    yellow = [v for v in verdicts if v.severity is Severity.CAUTION]
    count = {status: sum(v.status is status for v in verdicts) for status in RuleStatus}
    lines = [
        f"Evaluation against {table.source}: {len(verdicts)} rules, "
        f"{count[RuleStatus.INSIDE]} inside, {len(red)} bad (red), {len(yellow)} caution (yellow), "
        f"{count[RuleStatus.NOT_APPLICABLE]} not applicable, "
        f"{count[RuleStatus.NOT_AVAILABLE]} not available."
    ]
    for heading, items in (("Red:", red), ("Yellow:", yellow)):
        if items:
            lines.append(heading)
            lines.extend(f"- {v.text}" for v in items)
    return "\n".join(lines)


def _log_verdict(verdict: RuleVerdict, call_id: str | None) -> None:
    """Write a red or yellow verdict to the run log (INFO; WARNING stays for degraded operation)."""
    interval = verdict.interval
    logger.info(
        "%s",
        verdict.text,
        extra={
            "verdict": "evaluation",
            "call_id": call_id,
            "rule_id": verdict.rule_id,
            "quantity": verdict.quantity,
            "status": verdict.status.value,
            "severity": verdict.severity.value if verdict.severity is not None else None,
            "unit": verdict.unit,
            "value": verdict.value,
            "interval_min": interval.min if interval is not None else None,
            "interval_max": interval.max if interval is not None else None,
            "band_min": verdict.band.min,
            "band_max": verdict.band.max,
        },
    )
