"""The engine: one request through the canon graph (ARCHITECTURE ch. 6, 8.1, 8.3, 8.13).

``evaluate`` is the internal seam; the public ``compute`` supplies the shipped build. The engine
holds no state between calls. Every outcome of a node is a value (a result, a status or a
``KernelError``), never an exception that leaves the call.
"""

import asyncio
import logging
import math
import secrets
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from aero_kernel.build import Build
from aero_kernel.canon.model import Check, ConstBinding, Default, Formula
from aero_kernel.context import Context, Inputs, Solvers, Value
from aero_kernel.devices import devices_at_rest
from aero_kernel.errors import (
    ErrorCategory,
    FormulaError,
    KernelError,
    ToolRunTimeoutError,
    display_slug,
    format_world_assignment,
    internal_error,
    internal_error_from_exception,
    join_names,
    qualify,
)
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import (
    Node,
    NodeId,
    NodeOutcome,
    Propagated,
    Resolved,
    Subtree,
    facts_from_geometry,
    unmet_condition,
)
from aero_kernel.registry import CheckResult
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    DefaultUsed,
    Interval,
    KernelWarning,
    Polar,
    Provenance,
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
    dedupe_warnings,
)
from aero_kernel.validate import validate_aircraft, validate_request, validate_values
from pydantic import JsonValue

logger = logging.getLogger(__name__)

# The warning code by which a world declares itself outside its validity; it drops the assignment from
# the interval (ch. 8.13).
WORLD_OUTSIDE_VALIDITY = "world_outside_validity"

__all__ = ["evaluate", "log_call"]


@dataclass(frozen=True)
class _Defaulted:
    """A supplied input or target whose canon default a node bound.

    Attributes:
        slug: Qualified slug of the quantity.
        default: The canon default.
        role: The quantity's role, ``input`` or ``target``.
    """

    slug: str
    default: Default
    role: str


@dataclass(frozen=True)
class _NodeRun:
    """What happened to one node: its outcome for the successors and what its results need.

    A node has one status but may serve several requested quantities. The engine-authored texts
    (reasons and the engine's own errors) are therefore built per quantity from the record, never
    rewritten; a formula-authored message is kept as the formula wrote it.

    Attributes:
        outcome: The status (and error) the successors see, worded for ``anchor``.
        anchor: The name the outcome's texts use for the node's quantity.
        reason_for: Builds the reason of a ``not_applicable`` or ``skipped`` node for a quantity.
        error_for: Builds the error of an ``error`` node for a quantity.
        outputs: The returned value per output parameter, for status ``ok``.
        warnings: The warnings the node's formula reported.
        computed: Whether the failure was raised by the formula while computing (row 8 of the
            status order, whatever its code), not decided by the engine before the call.
    """

    outcome: NodeOutcome
    anchor: str
    reason_for: Callable[[str], Reason] | None = None
    error_for: Callable[[str], KernelError] | None = None
    outputs: Mapping[str, object] | None = None
    warnings: tuple[KernelWarning, ...] = ()
    computed: bool = False


def _unit_of(build: Build, slug: str) -> str | None:
    """The canon unit of a slug, or ``None`` if the kernel knows no such quantity."""
    quantity = build.model.quantity(slug)
    return None if quantity is None else quantity.unit


# The quantity types a value of v1 can carry between nodes (``Value``).
_CARRIED_TYPES = frozenset({"scalar", "airplane", "polar"})


def _in_scope(entry: Check, node: Node) -> bool:
    """Whether a pre- or postcondition belongs to the application of the node (absent = all)."""
    return entry.applications is None or node.id.application in entry.applications


def _check_warning(
    what: str, check_id: str, node: Node, result: CheckResult, origin: str
) -> KernelWarning:
    """The warning of an ``unchecked`` check or of a violated one whose ``on_violation`` is warning."""
    unchecked = result.state == "unchecked"
    verdict = "was not checked" if unchecked else "is violated"
    return KernelWarning.of(
        f"{what}_unchecked" if unchecked else f"{what}_violated",
        f"The {what} `{check_id}` of `{display_slug(node.id.formula)}` {verdict}: {result.message}",
        origin=origin,
        detail={what: check_id},
    )


class _Call:
    """The state of one ``evaluate`` call: nothing in it outlives the call."""

    def __init__(
        self,
        build: Build,
        aircraft: AircraftInput,
        request: ComputeRequest,
        subtree: Subtree,
        call_id: str,
        input_warnings: Sequence[KernelWarning],
        solvers: Solvers,
    ) -> None:
        self.build = build
        self.aircraft = aircraft
        # The supplied geometry as the leaf value: every device at 0 deg (ch. 8.11), where the
        # geometry_deflection_ignored warning is raised.
        self.airplane_at_rest = devices_at_rest(aircraft.airplane)
        self.request = request
        self.subtree = subtree
        self.call_id = call_id
        self.input_warnings = input_warnings
        self.solvers = solvers
        # the defaults taken so far, by qualified slug: only nodes that run take one (ch. 8.11)
        self.taken: dict[str, Default] = {}
        # the versions of the tools whose formulas this call actually called (ch. 8.4)
        self.tool_versions: dict[str, str] = {}
        # the settings of those solvers, e.g. the NeuralFoil model size (ch. 8.4)
        self.solver_settings: dict[str, JsonValue] = {}
        self.nodes: dict[NodeId, Node] = {node.id: node for node in subtree.nodes}
        self.values = {qualify(slug): value for slug, value in aircraft.values.items()}
        # One run per (node, world key): a node runs once per assignment of the uncertain formulas
        # it depends on, and once, under the key None, if it depends on none (ch. 8.13).
        self.runs: dict[tuple[NodeId, str | None], _NodeRun] = {}
        self.slots = {n.id: subtree.node_assignments(n.id) for n in subtree.nodes}
        # the first requested spelling of a node's quantities names the node in its messages
        self.requested_by_node: dict[NodeId, str] = {}
        for resolved in subtree.requested:
            self.requested_by_node.setdefault(resolved.producer, resolved.requested)

    # --- running the graph -----------------------------------------------------------------

    async def run(self) -> None:
        """Run the layers in order; the nodes of a layer concurrently."""
        for layer in self.subtree.layers:
            async with asyncio.TaskGroup() as group:
                for node_id in layer:
                    for key, assignment in self.slots[node_id]:
                        group.create_task(self._finish(self.nodes[node_id], key, assignment))

    async def _finish(self, node: Node, key: str | None, assignment: Mapping[str, str]) -> None:
        """Run one node under one assignment and record its run the moment it is done.

        Recorded here and not after the layer, so that a node that finished before the time
        budget expired keeps its value even if its layer did not complete.
        """
        self.runs[(node.id, key)] = _labelled(await self._node(node, key, assignment), key)

    def _run_of(self, node_id: NodeId, assignment: Mapping[str, str]) -> _NodeRun:
        """The run of a node under the assignment: its own key is the assignment restricted to it."""
        return self.runs[(node_id, self.subtree.assignment_key(node_id, assignment))]

    def close_open_nodes(self) -> None:
        """Give every node that did not finish when the time budget expired a ``timeout`` run.

        Dependents of an open node are open too. Their pool jobs, if any, finish and are discarded
        (ch. 8.10).
        """
        for node_id, node in self.nodes.items():
            for key, _assignment in self.slots[node_id]:
                if (node_id, key) not in self.runs:
                    self.runs[(node_id, key)] = _labelled(
                        self._failed(
                            self._anchor(node),
                            lambda slug, open_node=node: self._timeout_error(slug, open_node),
                        ),
                        key,
                    )

    def _timeout_error(self, slug: str, node: Node) -> KernelError:
        """The error of a quantity still open when the time budget expired."""
        budget = self.request.time_budget_s
        return KernelError(
            code="timeout",
            category=ErrorCategory.TIMEOUT,
            quantity=slug,
            formula=display_slug(node.id.formula),
            application=node.id.application,
            message=f"`{slug}` did not finish within the time budget of {budget} s.",
            hint="Raise time_budget_s, or request fewer or cheaper quantities.",
            detail={"time_budget_s": budget},
        )

    def _run_limit_error(self, slug: str, node: Node, raised: ToolRunTimeoutError) -> KernelError:
        """The error of a quantity whose tool run exceeded the adapter's own maximum run time."""
        return KernelError(
            code="timeout",
            category=ErrorCategory.TIMEOUT,
            quantity=slug,
            formula=display_slug(node.id.formula),
            application=node.id.application,
            message=f"`{slug}` did not finish: {raised.what} exceeded {raised.limit_s} s.",
            hint="The run was stopped; check the geometry for a configuration the tool cannot solve.",
            detail={"run_limit_s": raised.limit_s},
        )

    def _anchor(self, node: Node) -> str:
        """The name of the node's quantity in its errors: the requested spelling, else its first."""
        requested = self.requested_by_node.get(node.id)
        return requested or display_slug(node.produces[0].quantity)

    def _formula(self, node: Node) -> tuple[Formula, str]:
        """The node's formula and its public slug."""
        formula = self.build.model.formula(node.id.formula)
        assert formula is not None  # the graph was built from this very model
        return formula, display_slug(node.id.formula)

    async def _node(self, node: Node, key: str | None, assignment: Mapping[str, str]) -> _NodeRun:
        """Run one node; any defect of the engine itself becomes an ``internal`` outcome."""
        extra = {
            "call_id": self.call_id,
            "formula": display_slug(node.id.formula),
            "application": node.id.application,
        }
        started = time.perf_counter()
        logger.debug("node started", extra=extra)
        try:
            run = await self._evaluate_node(node, key, assignment)
        except Exception as exc:  # a node never raises out of the call (ch. 8.1)
            anchor = self._anchor(node)
            formula = display_slug(node.id.formula)
            # logged once for the crash, however many quantities of the node are requested
            logged = internal_error_from_exception(
                exc,
                quantity=anchor,
                formula=formula,
                application=node.id.application,
                call_id=self.call_id,
            )
            run = self._failed(
                anchor,
                lambda slug, crash=exc: internal_error(
                    crash,
                    quantity=slug,
                    formula=formula,
                    application=node.id.application,
                ),
                logged,
            )
        logger.debug(
            "node finished: %s in %.1f ms",
            run.outcome.status.value,
            (time.perf_counter() - started) * 1000,
            extra=extra,
        )
        return run

    @staticmethod
    def _failed(
        anchor: str,
        error_for: Callable[[str], KernelError],
        error: KernelError | None = None,
        *,
        computed: bool = False,
    ) -> _NodeRun:
        """A node that failed; ``error`` is its error worded for the anchor, if already built."""
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.ERROR, error=error or error_for(anchor)),
            anchor=anchor,
            error_for=error_for,
            computed=computed,
        )

    @staticmethod
    def _without_value(
        anchor: str, status: QuantityStatus, reason_for: Callable[[str], Reason]
    ) -> _NodeRun:
        """A node that is ``not_applicable`` or ``skipped``."""
        return _NodeRun(outcome=NodeOutcome(status=status), anchor=anchor, reason_for=reason_for)

    async def _evaluate_node(
        self, node: Node, key: str | None, assignment: Mapping[str, str]
    ) -> _NodeRun:
        """The status order of ch. 8.13, row by row; the first row that applies decides.

        1 an unmet condition, 2 a not applicable predecessor, 3 a kernel gap (no implementation,
        a ``when`` term without a fact, a value v1 cannot carry), 4 a failed predecessor, 5 a
        missing input, 6 a long run the request does not include, 7 a skipped predecessor.
        """
        formula, formula_slug = self._formula(node)
        anchor = self._anchor(node)
        application = node.id.application

        condition = unmet_condition(
            node, facts_from_geometry(self.aircraft.airplane), self.aircraft.values.keys()
        )
        if isinstance(condition, Reason):
            return self._without_value(
                anchor, QuantityStatus.NOT_APPLICABLE, lambda slug, reason=condition: reason
            )
        inherited = self._inherit(node, anchor, QuantityStatus.NOT_APPLICABLE, key, assignment)
        if inherited is not None:
            return inherited

        implementation = self.build.registry.implementation(node.id.formula)
        unsupported = self._unsupported_reads(node)
        # row 3, inner order: a condition without a fact, a read v1 cannot carry, no implementation
        if isinstance(condition, KernelError):
            return self._failed(
                anchor,
                lambda slug, error=condition: error.model_copy(
                    update={"quantity": slug, "formula": formula_slug}
                ),
            )
        if unsupported:
            return self._failed(
                anchor,
                lambda slug: self._unsupported_error(node, slug, formula_slug, unsupported),
            )
        if implementation is None:
            return self._failed(
                anchor,
                lambda slug: KernelError(
                    code=ErrorCategory.NOT_IMPLEMENTED.value,
                    category=ErrorCategory.NOT_IMPLEMENTED,
                    quantity=slug,
                    formula=formula_slug,
                    application=application,
                    message=f"`{formula_slug}` is in the canon, not in the kernel yet.",
                    hint="Request a quantity whose formula is implemented.",
                ),
            )

        inherited = self._inherit(node, anchor, QuantityStatus.ERROR, key, assignment)
        if inherited is not None:
            return inherited
        inputs, missing, defaults = self._inputs(node, formula, assignment)
        if missing:
            return self._failed(
                anchor, lambda slug: self._missing_input(node, slug, formula_slug, missing)
            )
        if node.cost == "minutes" and not self.request.include_long_runs:
            return self._without_value(
                anchor,
                QuantityStatus.SKIPPED,
                lambda slug: Reason(
                    code=ReasonCode.LONG_RUN_NOT_INCLUDED,
                    message=f"`{slug}` is a long run and the request does not include long runs.",
                ),
            )
        inherited = self._inherit(node, anchor, QuantityStatus.SKIPPED, key, assignment)
        if inherited is not None:
            return inherited

        origin = display_slug(node.produces[0].quantity)
        world = assignment.get(node.id.formula_slug) if node.worlds else None
        warner = Context(origin=origin, solvers=self.solvers, world=world)
        default_warnings = self._take_defaults(defaults)
        pre_warnings, refused = self._run_checks("pre", node, formula, inputs, None, origin)
        if refused is not None:
            return self._failed(
                anchor, lambda slug, error=refused: error.model_copy(update={"quantity": slug})
            )
        # A called formula used its tool even if it then fails, like a default (ch. 8.11).
        # A formula with worlds used the tool of its world, not its own (ch. 8.4, #1221).
        tool = self.build.model.tool_of(node.id.formula, world)
        self.tool_versions.update(self.solvers.tool_versions_of(tool))
        self.solver_settings.update(self.solvers.settings_of(tool))
        try:
            returned = await implementation.func(inputs, warner)
        except ToolRunTimeoutError as exc:
            return self._failed(
                anchor,
                lambda slug, raised=exc: self._run_limit_error(slug, node, raised),
                computed=True,
            )
        except FormulaError as exc:
            path = self._input_path(node, formula, exc.parameter)
            return self._failed(
                anchor,
                lambda slug, raised=exc: raised.to_kernel_error(
                    quantity=slug, formula=formula_slug, application=application, input_path=path
                ),
                computed=True,
            )
        self._check_outputs(node, formula, returned)
        post_warnings, discarded = self._run_checks("post", node, formula, inputs, returned, origin)
        if discarded is not None:
            return self._failed(
                anchor, lambda slug, error=discarded: error.model_copy(update={"quantity": slug})
            )
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.OK),
            anchor=anchor,
            outputs=returned,
            warnings=(*default_warnings, *pre_warnings, *warner.warnings, *post_warnings),
        )

    def _run_checks(
        self,
        kind: Literal["pre", "post"],
        node: Node,
        formula: Formula,
        inputs: Inputs,
        outputs: Mapping[str, object] | None,
        origin: str,
    ) -> tuple[list[KernelWarning], KernelError | None]:
        """Run the pre- or postconditions of an application (ch. 8.5, Q25).

        Only the checks whose ``applications`` include this one run (absent = all). A check the
        canon declares and the registry lacks is ``unchecked``, never silently held (ADR 0020).
        ``unchecked`` and, with ``on_violation: warning``, ``violated`` give a warning and the value
        stays; ``violated`` with ``on_violation: error`` gives the error (for a postcondition the
        caller discards every output of the application).

        Returns:
            The warnings, and the error of the first violated ``error`` check, if any.
        """
        what = "precondition" if kind == "pre" else "postcondition"
        declared = formula.preconditions if kind == "pre" else formula.postconditions
        registered = self.build.registry.checks(node.id.formula, kind)
        warnings: list[KernelWarning] = []
        for entry in declared:
            if not _in_scope(entry, node):
                continue
            result = self._check_result(kind, what, registered.get(entry.id), inputs, outputs)
            logger.debug("%s %s: %s", what, entry.id, result.state, extra={"call_id": self.call_id})
            if result.state == "held":
                continue
            if result.state == "violated" and entry.on_violation == "error":
                return warnings, self._violation_error(kind, what, entry.id, node, result.message)
            warnings.append(_check_warning(what, entry.id, node, result, origin))
        return warnings, None

    @staticmethod
    def _check_result(
        kind: Literal["pre", "post"],
        what: str,
        function: Callable[..., CheckResult] | None,
        inputs: Inputs,
        outputs: Mapping[str, object] | None,
    ) -> CheckResult:
        """Run one check; a check the registry lacks is ``unchecked``."""
        if function is None:
            return CheckResult(
                state="unchecked", message=f"no implementation of the {what} is registered"
            )
        if kind == "pre":
            return function(inputs)
        assert outputs is not None  # a postcondition runs after the implementation
        return function(inputs, outputs)

    @staticmethod
    def _violation_error(
        kind: Literal["pre", "post"], what: str, check_id: str, node: Node, message: str
    ) -> KernelError:
        """The error of a violated check whose ``on_violation`` is ``error``."""
        formula_slug = display_slug(node.id.formula)
        return KernelError(
            code=f"{what}_violated",
            category=ErrorCategory.UNSUPPORTED_CONFIGURATION,
            formula=formula_slug,
            application=node.id.application,
            message=f"The {what} `{check_id}` of `{formula_slug}` is violated: {message}",
            hint=(
                "Change the inputs so that the formula applies."
                if kind == "pre"
                else "The value was discarded; the evaluation is not trustworthy."
            ),
            detail={what: check_id},
        )

    def _inherit(
        self,
        node: Node,
        anchor: str,
        status: QuantityStatus,
        key: str | None,
        assignment: Mapping[str, str],
    ) -> _NodeRun | None:
        """The run of a node that inherits ``status`` from a predecessor it reads, if it does.

        The predecessors count as they ran under this node's assignment.
        """
        propagated = self.subtree.propagate(
            node.id,
            {
                edge.predecessor: self._run_of(edge.predecessor, assignment).outcome
                for edge in self.subtree.edges[node.id]
            },
            quantity=anchor,
            status=status,
            world=key,
        )
        return None if propagated is None else self._propagated(anchor, propagated)

    def _propagated(self, anchor: str, propagated: Propagated) -> _NodeRun:
        """A node that inherits its status from a predecessor it reads."""
        if propagated.error is not None:
            return self._failed(
                anchor,
                lambda slug: _error_of(propagated.addressed_to(slug)),
                propagated.error,
            )
        return self._without_value(
            anchor, propagated.status, lambda slug: _reason_of(propagated.addressed_to(slug))
        )

    # --- inputs ----------------------------------------------------------------------------

    def _unsupported_reads(self, node: Node) -> list[tuple[str, str]]:
        """The ``(slug, type)`` of every bound quantity whose value v1 cannot carry."""
        found: list[tuple[str, str]] = []
        for binding in self._bound_quantities(node):
            quantity = self.build.model.quantity(binding)
            if quantity is not None and quantity.type not in _CARRIED_TYPES:
                found.append((binding, quantity.type))
        return found

    def _bound_quantities(self, node: Node) -> list[str]:
        """The qualified slugs the node's application binds, in the formula's parameter order."""
        formula, _ = self._formula(node)
        application = formula.application(node.id.application)
        return [b for b in application.bind.values() if isinstance(b, str)]

    @staticmethod
    def _unsupported_error(
        node: Node, quantity: str, formula_slug: str, unsupported: Sequence[tuple[str, str]]
    ) -> KernelError:
        """The ``not_implemented`` error of a node that reads values v1 cannot carry."""
        names = join_names([f"`{display_slug(slug)}` (a {kind})" for slug, kind in unsupported])
        return KernelError(
            code="unsupported_value_type",
            category=ErrorCategory.NOT_IMPLEMENTED,
            quantity=quantity,
            formula=formula_slug,
            application=node.id.application,
            message=f"`{quantity}` reads {names}, which the kernel cannot carry yet.",
            hint="Request a quantity that reads scalars and the airplane only.",
            detail={"quantities": list[JsonValue](display_slug(slug) for slug, _ in unsupported)},
        )

    def _inputs(
        self, node: Node, formula: Formula, assignment: Mapping[str, str]
    ) -> tuple[Inputs, list[str], list[_Defaulted]]:
        """Bind the formula's parameters.

        Returns:
            ``x``, the qualified slugs of the missing inputs, and the defaults that were bound
            (taken only if the formula is then called).
        """
        application = formula.application(node.id.application)
        bound: dict[str, Value | None] = {}
        missing: list[str] = []
        defaulted: list[_Defaulted] = []
        for parameter, binding in application.bind.items():
            if isinstance(binding, ConstBinding):
                bound[parameter] = binding.const
                continue
            value = self._read(node, binding, assignment)
            if value is not None:
                bound[parameter] = value
            elif any(edge.quantity == binding for edge in self.subtree.edges[node.id]):
                continue  # a predecessor has no value: that is its status (row 7), not a missing input
            elif (default := self._default_of(binding)) is not None:
                bound[parameter] = default.value
                role = self.build.model.quantity(binding)
                assert role is not None  # a default belongs to a quantity of the model
                defaulted.append(_Defaulted(binding, default, role.role))
            elif parameter in formula.optional:
                bound[parameter] = None
            else:
                missing.append(binding)
        return bound, missing, defaulted

    def _default_of(self, slug: str) -> Default | None:
        """The canon default of a supplied quantity, if the model states one."""
        namespace, _, name = slug.partition(":")
        return self.build.model.namespaces[namespace].defaults.get(name)

    def _take_defaults(self, bound: Sequence[_Defaulted]) -> list[KernelWarning]:
        """Record the defaults a node that is about to run takes; return their warnings.

        Each default is logged once per call and slug, as its own INFO line, in the order the
        node binds them: the formula's parameter order. A target default is a substitution and gives
        the ``default_target_used`` warning, which this node's quantity and everything computed
        from it inherit; a constant's default gives none (ch. 8.11).
        """
        warnings: list[KernelWarning] = []
        for taken in bound:
            default, shown = taken.default, display_slug(taken.slug)
            if taken.slug not in self.taken:
                self.taken[taken.slug] = default
                logger.info(
                    "default used: %s = %s %s (%s)",
                    shown,
                    default.value,
                    default.unit,
                    default.source,
                    extra={"call_id": self.call_id, "quantity": shown, "role": taken.role},
                )
            if taken.role == "target":
                warnings.append(
                    KernelWarning.of(
                        "default_target_used",
                        f"`{shown}` was not set; the canon default {default.value} "
                        f"{default.unit} is used ({default.source}).",
                        origin=shown,
                        detail={
                            "value": default.value,
                            "unit": default.unit,
                            "source": default.source,
                        },
                    )
                )
        return warnings

    def defaults_used(self) -> tuple[DefaultUsed, ...]:
        """The defaults taken by nodes that ran, sorted by display slug."""
        return tuple(
            DefaultUsed(slug=shown, value=d.value, unit=d.unit, source=d.source)
            for shown, d in sorted((display_slug(slug), d) for slug, d in self.taken.items())
        )

    def _read(self, node: Node, slug: str, assignment: Mapping[str, str]) -> Value | None:
        """The value of a bound quantity: a predecessor's output or a supplied input."""
        for edge in self.subtree.edges[node.id]:
            if edge.quantity == slug:
                predecessor = self.nodes[edge.predecessor]
                parameter = next(p.parameter for p in predecessor.produces if p.quantity == slug)
                outputs = self._run_of(edge.predecessor, assignment).outputs
                value = None if outputs is None else outputs[parameter]
                return value if isinstance(value, float | AirplaneGeometry | Polar) else None
        quantity = self.build.model.quantity(slug)
        if quantity is not None and quantity.type == "airplane":
            return self.airplane_at_rest
        return self.values.get(slug) if quantity is not None and quantity.type == "scalar" else None

    @staticmethod
    def _missing_input(
        node: Node, quantity: str, formula_slug: str, missing: Sequence[str]
    ) -> KernelError:
        """The ``missing_input`` error of a node that reads values nobody supplied.

        One error for all of them; its ``input_path`` is the first missing input in the formula's
        parameter order (every other one is in ``detail.inputs``).
        """
        shown = [display_slug(slug) for slug in missing]
        verb = "was" if len(shown) == 1 else "were"
        return KernelError(
            code="missing_input",
            category=ErrorCategory.INVALID_INPUT,
            quantity=quantity,
            formula=formula_slug,
            application=node.id.application,
            input_path=f"values.{shown[0]}",
            message=f"`{quantity}` needs {join_names([f'`{n}`' for n in shown])}, "
            f"which {verb} not supplied.",
            hint=f"Supply {join_names([f'`{n}`' for n in shown])} in `values`.",
            detail={"inputs": list[JsonValue](shown)},
        )

    def _input_path(self, node: Node, formula: Formula, parameter: str | None) -> str | None:
        """Where the caller finds the input a formula blames: derived from its binding."""
        if parameter is None:
            return None
        binding = formula.application(node.id.application).bind.get(parameter)
        if not isinstance(binding, str):
            return None
        quantity = self.build.model.quantity(binding)
        if quantity is None or quantity.role not in ("input", "target"):
            return None
        # an input of another type is a kernel gap before any formula runs (row 3)
        return "airplane" if quantity.type == "airplane" else f"values.{display_slug(binding)}"

    # --- outputs ---------------------------------------------------------------------------

    def _check_outputs(self, node: Node, formula: Formula, returned: Mapping[str, object]) -> None:
        """Require exactly the output parameters, and a value of its type for each carried output.

        The key of an output whose type v1 cannot carry (curve, ...) must be present, but its value
        is neither carried nor type-checked: the engine discards it, and whoever reads it is
        ``not_implemented`` (``unsupported_value_type``). The type check for each such type arrives
        with the unit that adds it to ``Value`` (the polar did with ``stall-break``).

        Raises:
            ValueError: If the formula returned other parameters than the canon declares.
            TypeError: If an exposed scalar, airplane or polar output is not a value of its type.
        """
        expected = set(formula.application(node.id.application).produce)
        if set(returned) != expected:
            msg = f"formula returned {sorted(returned)}, the canon declares {sorted(expected)}"
            raise ValueError(msg)
        for produce in node.produces:
            quantity = self.build.model.quantity(produce.quantity)
            assert quantity is not None  # a produced quantity is one of the model
            value = returned[produce.parameter]
            if quantity.type == "scalar" and not (
                isinstance(value, float) and math.isfinite(value)
            ):
                msg = f"output {produce.parameter} is not a finite float"
                raise TypeError(msg)
            if quantity.type == "airplane" and not isinstance(value, AirplaneGeometry):
                msg = f"output {produce.parameter} is not an airplane geometry"
                raise TypeError(msg)
            if quantity.type == "polar" and not isinstance(value, Polar):
                msg = f"output {produce.parameter} is not a polar"
                raise TypeError(msg)

    # --- results ---------------------------------------------------------------------------

    def result_of(self, resolved: Resolved) -> QuantityResult:
        """The result of one requested quantity.

        A quantity without uncertain formulas has one result. One with worlds (A11) has one result
        per assignment, merged: all ``ok`` gives an interval over the assignments; otherwise the
        quantity is an error or has no value, never a narrower interval (ch. 8.13).
        """
        assignments = self.subtree.world_assignments(resolved.requested)
        if len(assignments) == 1 and not assignments[0]:
            return self._result_under(resolved, {})
        results = [
            (
                format_world_assignment(a),
                self._result_under(resolved, a),
                self._run_of(resolved.producer, a).computed,
            )
            for a in assignments
        ]
        return _merge_worlds(resolved.requested, resolved.quantity.unit, results)

    def _result_under(self, resolved: Resolved, assignment: Mapping[str, str]) -> QuantityResult:
        """The result of one requested quantity under one world assignment.

        An ``ok`` quantity lists, deduplicated by content and in this order: the warnings of the
        nodes of its subtree in topological order (within a node, the defaults taken before the
        formula's own warnings), then the validation warnings whose origin the subtree reads, in
        validation order.
        """
        run = self._run_of(resolved.producer, assignment)
        slug, unit = resolved.requested, resolved.quantity.unit
        status = run.outcome.status
        if status is QuantityStatus.ERROR:
            assert run.error_for is not None  # set with every error outcome
            return QuantityResult(slug=slug, unit=unit, status=status, error=run.error_for(slug))
        if status is not QuantityStatus.OK:
            assert run.reason_for is not None  # set with every skipped or not_applicable outcome
            return QuantityResult(slug=slug, unit=unit, status=status, reason=run.reason_for(slug))
        node = self.nodes[resolved.producer]
        parameter = next(p.parameter for p in node.produces if p.quantity == resolved.slug)
        formula, _ = self._formula(node)
        value = None if run.outputs is None else run.outputs[parameter]
        assert isinstance(value, float)  # checked by _check_outputs for a scalar
        subtree_nodes = self.subtree.nodes_for(resolved.slug)
        read = {r.quantity for node_id in subtree_nodes for r in self.nodes[node_id].reads}
        inherited: list[KernelWarning] = []
        for warning in self.input_warnings:
            assert warning.origin is not None  # validation names the origin of every warning
            if qualify(warning.origin) in read:
                inherited.append(warning)
        warnings = dedupe_warnings(
            [
                *(
                    w
                    for node_id in subtree_nodes
                    for w in self._run_of(node_id, assignment).warnings
                ),
                *inherited,
            ]
        )
        return QuantityResult(
            slug=slug,
            unit=unit,
            status=status,
            value=value,
            tool=formula.tool,
            application=node.id.application,
            warnings=warnings,
        )


def _labelled(run: _NodeRun, key: str | None) -> _NodeRun:
    """The run with the world it arose in on its warnings and its error (ch. 8.13)."""
    if key is None:
        return run

    def with_world(error: KernelError) -> KernelError:
        return error if error.world is not None else error.model_copy(update={"world": key})

    def labelled_error_for(build: Callable[[str], KernelError]) -> Callable[[str], KernelError]:
        return lambda slug: with_world(build(slug))

    error_for = run.error_for
    outcome_error = run.outcome.error
    return _NodeRun(
        anchor=run.anchor,
        reason_for=run.reason_for,
        outputs=run.outputs,
        computed=run.computed,
        outcome=run.outcome.model_copy(
            update={"error": None if outcome_error is None else with_world(outcome_error)}
        ),
        error_for=None if error_for is None else labelled_error_for(error_for),
        warnings=tuple(
            w if w.world is not None else w.model_copy(update={"world": key}) for w in run.warnings
        ),
    )


# Error codes by the row of the status order (ch. 8.13) they belong to; any other error is a failed
# computation (the last row).
_ROW_BY_CODE = {
    "not_implemented": 3,
    "unsupported_value_type": 3,
    "continuous_uncertainty": 3,
    "non_scalar_result": 3,
    "upstream_failed": 4,
    "missing_input": 5,
}
_ROW_OF_A_COMPUTED_FAILURE = 8


def _row(result: QuantityResult, *, computed: bool) -> int:
    """The row of the status order (ch. 8.13) of a result that is not ``ok``.

    ``computed``: the formula raised the failure while computing. That is row 8 whatever its code,
    so a ``missing_input`` the formula raised is not the engine's row 5.
    """
    if result.status is QuantityStatus.NOT_APPLICABLE:
        return 2
    if result.status is QuantityStatus.SKIPPED:
        return 7
    assert result.error is not None  # status error carries an error
    if computed:
        return _ROW_OF_A_COMPUTED_FAILURE
    return _ROW_BY_CODE.get(result.error.code, _ROW_OF_A_COMPUTED_FAILURE)


def _excluded(result: QuantityResult) -> bool:
    """Whether the assignment lies outside the validity of a world it ran in (ch. 8.13).

    The exclusion is the declaration itself: a ``world_outside_validity`` warning anywhere in the
    result's subtree. The assignment keeps its value (the warning names it) but is not in the interval.
    """
    return any(w.code == WORLD_OUTSIDE_VALIDITY for w in result.warnings)


def _merge_worlds(
    slug: str, unit: str | None, results: Sequence[tuple[str, QuantityResult, bool]]
) -> QuantityResult:
    """Merge the results of one quantity over its world assignments (ch. 8.13, A11).

    All ``ok``: an interval over the assignment values, without the assignments a world declared
    outside its validity (``world_outside_validity``); if every assignment is excluded the quantity
    is an error. Otherwise the failure that comes first by its row of the status order, then by the
    assignment key; an error carries the values that did compute in ``detail.worlds_ok``. A failed
    assignment is never dropped from the interval; only a declared exclusion is.
    """
    if all(result.status is QuantityStatus.OK for _, result, _ in results):
        return _interval_of(slug, unit, results)
    _, _, chosen = min(
        (
            (_row(result, computed=computed), key, result)
            for key, result, computed in results
            if result.status is not QuantityStatus.OK
        ),
        key=lambda candidate: (candidate[0], candidate[1]),
    )
    if chosen.error is None:
        return chosen
    worlds_ok = {
        key: result.value for key, result, _ in results if result.status is QuantityStatus.OK
    }
    error = chosen.error
    if _alike_in_every_world(results):
        error = error.model_copy(update={"world": None})  # the cause is in no world
    error = error.model_copy(update={"detail": {**error.detail, "worlds_ok": worlds_ok}})
    return chosen.model_copy(update={"error": error})


def _interval_of(
    slug: str, unit: str | None, results: Sequence[tuple[str, QuantityResult, bool]]
) -> QuantityResult:
    """The interval of an all-``ok`` quantity over the assignments inside every world's validity."""
    kept = [(key, result) for key, result, _ in results if not _excluded(result)]
    if not kept:
        excluded: dict[str, JsonValue] = {key: result.value for key, result, _ in results}
        return QuantityResult(
            slug=slug,
            unit=unit,
            status=QuantityStatus.ERROR,
            error=KernelError(
                code="all_worlds_outside_validity",
                category=ErrorCategory.UNSUPPORTED_CONFIGURATION,
                quantity=slug,
                message=(
                    f"Every method world of `{slug}` declared itself outside its validity, "
                    "so no interval remains."
                ),
                hint="The values of the excluded worlds are in detail.worlds_excluded.",
                detail={"worlds_excluded": excluded},
            ),
        )
    values: dict[str, float] = {}
    for key, result in kept:
        assert result.value is not None
        values[key] = result.value
    first = kept[0][1]
    return QuantityResult(
        slug=slug,
        unit=unit,
        status=QuantityStatus.OK,
        interval=Interval(min=min(values.values()), max=max(values.values()), worlds=values),
        tool=first.tool,
        application=first.application,
        warnings=dedupe_warnings([w for _, result, _ in results for w in result.warnings]),
    )


def _alike_in_every_world(results: Sequence[tuple[str, QuantityResult, bool]]) -> bool:
    """Whether every assignment failed with the same error, the world label aside.

    Then the cause is the airplane or a shared input, not a method world (ch. 8.13).
    """
    errors = [result.error for _, result, _ in results]
    if any(error is None for error in errors):
        return False
    unlabelled = [error.model_copy(update={"world": None}) for error in errors if error is not None]
    return all(error == unlabelled[0] for error in unlabelled)


def _error_of(propagated: Propagated) -> KernelError:
    """The error of a propagation that forces status ``error``."""
    assert propagated.error is not None
    return propagated.error


def _reason_of(propagated: Propagated) -> Reason:
    """The reason of a propagation that forces status ``skipped`` or ``not_applicable``."""
    assert propagated.reason is not None
    return propagated.reason


def _provenance(
    build: Build,
    defaults: tuple[DefaultUsed, ...] = (),
    tool_versions: Mapping[str, str] | None = None,
    solver_settings: Mapping[str, JsonValue] | None = None,
) -> Provenance:
    """The provenance of a call on a loaded build."""
    return Provenance(
        defaults_used=defaults,
        tool_versions=dict(tool_versions or {}),
        solver_settings=dict(solver_settings or {}),
        build_digest=build.digest,
        canon_model_hash=build.model.content_hash,
    )


def log_call(
    call_id: str,
    request: ComputeRequest,
    result: ComputeResult,
    started: float,
    note: str | None = None,
) -> None:
    """The one ``INFO`` line of a call (ch. 8.14); also used by the failing-build path of ``compute``.

    Args:
        call_id: Short id of the call.
        request: The request.
        result: The result of the call.
        started: ``time.perf_counter()`` at the start of the call.
        note: What else to say about the call, appended after the timing.
    """
    counts = Counter(q.status.value for q in result.quantities)
    logger.info(
        "compute: [%s] include_long_runs=%s, %d quantities (%s), %d input errors, %.1f ms%s",
        ", ".join(request.quantities),
        request.include_long_runs,
        len(result.quantities),
        ", ".join(f"{status}={n}" for status, n in sorted(counts.items())) or "none",
        len(result.input_errors),
        (time.perf_counter() - started) * 1000,
        "" if note is None else f"; {note}",
        extra={"call_id": call_id},
    )


async def evaluate(
    build: Build, aircraft: AircraftInput, request: ComputeRequest, *, solvers: Solvers
) -> ComputeResult:
    """Compute a request on a build (ch. 6); the internal seam under ``compute``.

    Args:
        build: The canon model with its graph and implementations.
        aircraft: The geometry and the input and target values, in canon units.
        request: The quantities to compute.
        solvers: The solver adapters of the call; the caller owns their runtime.

    Returns:
        ``input_errors`` and nothing computed if the input is inadmissible, else one result per
        requested slug in request order. Never raises for a computational failure.
    """
    call_id = secrets.token_hex(4)
    started = time.perf_counter()
    validation = validate_aircraft(aircraft)
    errors = (
        validation.errors
        + validate_values(aircraft.values, build.model)
        + validate_request(request)
    )
    if errors:
        result = ComputeResult(input_errors=errors, provenance=_provenance(build))
        log_call(call_id, request, result, started)
        return result
    subtree = build.graph.subtree(request.quantities)
    call = _Call(build, aircraft, request, subtree, call_id, validation.warnings, solvers)
    try:
        async with asyncio.timeout(request.time_budget_s):
            await call.run()
    except TimeoutError:
        logger.debug(
            "time budget of %s s expired", request.time_budget_s, extra={"call_id": call_id}
        )
        call.close_open_nodes()
    results: dict[str, QuantityResult] = {}
    for error in subtree.errors:
        assert error.quantity is not None  # the graph words a rejection for the requested slug
        results[error.quantity] = QuantityResult(
            slug=error.quantity,
            unit=_unit_of(build, error.quantity),
            status=QuantityStatus.ERROR,
            error=error,
        )
    results.update({r.requested: call.result_of(r) for r in subtree.requested})
    result = ComputeResult(
        quantities=tuple(results[slug] for slug in request.quantities),
        provenance=_provenance(
            build, call.defaults_used(), call.tool_versions, call.solver_settings
        ),
    )
    log_call(call_id, request, result, started)
    return result
