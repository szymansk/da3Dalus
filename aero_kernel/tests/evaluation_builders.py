"""Builders of small rule tables, kernel results and geometry facts for the evaluation tests."""

from typing import Any

# ``Any`` is the raw-YAML boundary: these are hand-written rule dicts that the rule table validates.
from aero_kernel.evaluation.rules import Rule, RuleTable
from aero_kernel.graph import WhenFacts
from aero_kernel.schema import (
    ComputeResult,
    Interval,
    Provenance,
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
)


def rule_dict(**extra: Any) -> dict[str, Any]:
    """A rule over ``static-margin-target`` with the band 0.05 to 0.15."""
    return {
        "id": "static-margin",
        "title": "Static margin",
        "quantity": {"slug": "static-margin-target"},
        "unit": "1",
        "band": {"min": 0.05, "max": 0.15},
        "source": "Drela, Lab 11 Notes, Eq. (2)",
        "below": "Negative: unstable.",
        "above": "Large trim changes with speed.",
        **extra,
    }


def rule_of(**extra: Any) -> Rule:
    """A validated rule."""
    return Rule.model_validate(rule_dict(**extra))


def table_of(*rules: Rule) -> RuleTable:
    """A validated rule table."""
    return RuleTable(source="Drela, Lab 11 Notes", rules=rules)


def facts(**overrides: bool) -> WhenFacts:
    """Geometry facts of an aircraft that has nothing, with overrides."""
    base = {
        "has_aileron": False,
        "has_elevator": False,
        "has_flap": False,
        "has_horizontal_tail": False,
        "has_no_aileron": True,
        "has_rudder": False,
        "has_separate_flap_and_aileron": False,
        "has_vertical_tail": False,
    }
    return WhenFacts(**{**base, **overrides})


def ok(slug: str, value: float, unit: str = "1") -> QuantityResult:
    """A computed scalar."""
    return QuantityResult(
        slug=slug, unit=unit, status=QuantityStatus.OK, value=value, tool="APP", application="a"
    )


def spread(slug: str, low: float, high: float, unit: str = "1") -> QuantityResult:
    """A computed interval over two method worlds."""
    interval = Interval(min=low, max=high, worlds={"neutral-point=a": low, "neutral-point=b": high})
    return QuantityResult(
        slug=slug,
        unit=unit,
        status=QuantityStatus.OK,
        interval=interval,
        tool="APP",
        application="a",
    )


def not_applicable(slug: str) -> QuantityResult:
    """A quantity the kernel found not applicable."""
    return QuantityResult(
        slug=slug,
        status=QuantityStatus.NOT_APPLICABLE,
        reason=Reason(code=ReasonCode.CONDITION_NOT_MET, message="No fin."),
    )


def not_given(slug: str) -> QuantityResult:
    """A quantity that needs a value the caller did not supply."""
    return QuantityResult(
        slug=slug,
        status=QuantityStatus.NOT_APPLICABLE,
        reason=Reason(code=ReasonCode.NOT_GIVEN, message="No CG."),
    )


def result_of(*quantities: QuantityResult) -> ComputeResult:
    """A kernel result with these quantities."""
    return ComputeResult(quantities=quantities, provenance=Provenance(build_digest="test"))
