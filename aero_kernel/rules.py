"""The rule parameters of a call: the canon's thresholds with the caller's overrides (gh-1260).

A threshold of a validation rule is never a literal in the kernel: it is a parameter of a rule in
``rules.yaml``. :class:`Rules` resolves it for one call: the canon value, or the caller's
override (``AircraftInput.rule_overrides``, key ``<rule>.<parameter>``), and remembers every value
it handed out so the call can declare it in the provenance (ADR 0020). A ``pending`` parameter is
a proposal the maintainer has not decided; the kernel refuses to read it.
"""

import math
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar

from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import DEFAULT_NAMESPACE, ErrorCategory, KernelError
from aero_kernel.schema import RuleUsed

__all__ = ["Rules", "node_rule_reads", "rule_override_errors", "unrecorded_rule_reads"]

# The thresholds the running node read, by (rule, parameter); ``None`` outside a node (validation).
# A context variable: every node runs in its own task, and ``asyncio.to_thread`` copies the context,
# so a read is credited to the node whose task made it, also when adapters share one ``Rules``
# (ARCHITECTURE ch. 8.4, maintainer 2026-10-29, #1332).
_NODE_READS: ContextVar[dict[tuple[str, str], RuleUsed] | None] = ContextVar(
    "node_rule_reads", default=None
)
# Whether reads are kept out of the call's and the node's record: set while the cache key is built.
_UNRECORDED: ContextVar[bool] = ContextVar("unrecorded_rule_reads", default=False)


@contextmanager
def node_rule_reads() -> Generator[dict[tuple[str, str], RuleUsed]]:
    """Collect the thresholds read in this context (one node's run) while the block runs.

    Yields:
        The thresholds read so far, by ``(rule, parameter)``; filled as the node reads.
    """
    reads: dict[tuple[str, str], RuleUsed] = {}
    token = _NODE_READS.set(reads)
    try:
        yield reads
    finally:
        _NODE_READS.reset(token)


@contextmanager
def unrecorded_rule_reads() -> Generator[None]:
    """Read thresholds without recording them, e.g. the solver settings that go into a cache key.

    A key is built before the node runs; whether its thresholds are declared is decided by the run
    (or, on a cache hit, by the stored entry), not by the lookup.
    """
    token = _UNRECORDED.set(True)
    try:
        yield
    finally:
        _UNRECORDED.reset(token)


class Rules:
    """The thresholds of one call, resolved from the canon model and the caller's overrides."""

    def __init__(self, model: CanonModel, overrides: Mapping[str, float] | None = None) -> None:
        """Create the resolver.

        Args:
            model: The canon model.
            overrides: Value per ``<rule>.<parameter>``; only adopted parameters may be overridden
                (:func:`rule_override_errors` refuses the rest before the call runs).
        """
        self._rules = model.namespaces[DEFAULT_NAMESPACE].rules
        self._overrides = dict(overrides or {})
        self._used: dict[tuple[str, str], RuleUsed] = {}

    def begin(self, overrides: Mapping[str, float] | None = None) -> None:
        """Start a call: take its overrides and forget what an earlier call used.

        Args:
            overrides: The caller's ``rule_overrides`` of this call.
        """
        self._overrides = dict(overrides or {})
        self._used = {}

    def value(self, rule: str, parameter: str) -> float:
        """Return a threshold: the caller's override, else the canon's value; and remember it.

        Args:
            rule: The rule id in ``rules.yaml``.
            parameter: The name of the parameter.

        Returns:
            The value, in the unit of the canon parameter.

        Raises:
            KeyError: If the canon has no such rule or parameter (a defect of the caller).
            ValueError: If the parameter is still ``pending``: a proposal is not read.
        """
        entry = self._rules[rule].parameters[parameter]
        if entry.status != "adopted":
            msg = f"the parameter {rule}.{parameter} is {entry.status}: the kernel does not read it"
            raise ValueError(msg)
        key = f"{rule}.{parameter}"
        overridden = key in self._overrides
        value = self._overrides[key] if overridden else entry.value
        if not _UNRECORDED.get():
            used = RuleUsed(
                rule=rule,
                parameter=parameter,
                value=value,
                unit=entry.unit,
                basis=entry.basis,
                overridden=overridden,
            )
            self._used[rule, parameter] = used
            reads = _NODE_READS.get()
            if reads is not None:
                reads[rule, parameter] = used
        return value

    def replay(self, used: Iterable[RuleUsed]) -> None:
        """Record thresholds a node read when it was computed, for a node served from the cache.

        The cache key holds the call's overrides, so a stored threshold is the one this call would
        have read (ch. 8.4).

        Args:
            used: The thresholds the stored node read.
        """
        reads = _NODE_READS.get()
        for entry in used:
            self._used[entry.rule, entry.parameter] = entry
            if reads is not None:
                reads[entry.rule, entry.parameter] = entry

    def used(self) -> tuple[RuleUsed, ...]:
        """The thresholds handed out so far, sorted by rule and parameter."""
        return tuple(self._used[key] for key in sorted(self._used))


def rule_override_errors(
    overrides: Mapping[str, float], model: CanonModel
) -> tuple[KernelError, ...]:
    """Refuse the overrides that name no adopted parameter of the canon, or are not finite.

    Args:
        overrides: The caller's ``rule_overrides``.
        model: The canon model.

    Returns:
        ``invalid_input`` errors at ``rule_overrides.<key>``, in key order.
    """
    rules = model.namespaces[DEFAULT_NAMESPACE].rules
    errors: list[KernelError] = []
    for key in sorted(overrides):
        rule, _, parameter = key.partition(".")
        entry = rules[rule].parameters.get(parameter) if rule in rules else None
        if entry is None:
            code, message, hint = (
                "unknown_rule_parameter",
                f"`{key}` is no parameter of a canon rule.",
                "Use the key <rule>.<parameter> of a rule in rules.yaml.",
            )
        elif entry.status != "adopted":
            code, message, hint = (
                "rule_parameter_pending",
                f"`{key}` is a proposal the maintainer has not decided; it cannot be overridden.",
                "Remove the override.",
            )
        elif not math.isfinite(overrides[key]):
            code, message, hint = (
                "non_finite_number",
                f"Value at rule_overrides.{key} is {overrides[key]}; it must be a finite number.",
                "Give the override a finite value.",
            )
        else:
            continue
        errors.append(
            KernelError(
                code=code,
                category=ErrorCategory.INVALID_INPUT,
                input_path=f"rule_overrides.{key}",
                message=message,
                hint=hint,
            )
        )
    return tuple(errors)
