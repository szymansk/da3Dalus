"""The evaluation layer: design rules applied to kernel results, outside the canon (A10).

The canon computes and never judges; this package holds the judgement. A rule table (data) and a
kernel result go in, a verdict per rule comes out. Nothing here computes a physical quantity.
"""

from aero_kernel.evaluation.evaluator import (
    RuleStatus,
    RuleVerdict,
    evaluate_rules,
    judge_result,
    quantities_to_request,
    summarize_verdicts,
)
from aero_kernel.evaluation.rules import (
    Band,
    Level,
    Position,
    QuantityRef,
    Rule,
    RuleTable,
    Severity,
    check_rule_table,
    shipped_rule_table,
)

__all__ = [
    "Band",
    "Level",
    "Position",
    "QuantityRef",
    "Rule",
    "RuleStatus",
    "RuleTable",
    "RuleVerdict",
    "Severity",
    "check_rule_table",
    "evaluate_rules",
    "judge_result",
    "quantities_to_request",
    "shipped_rule_table",
    "summarize_verdicts",
]
