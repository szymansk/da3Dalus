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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from aero_kernel.build import Build
from aero_kernel.canon.model import ConstBinding, Formula
from aero_kernel.context import Context, Inputs, Value
from aero_kernel.errors import (
    ErrorCategory,
    FormulaError,
    KernelError,
    aggregate_upstream,
    display_slug,
    internal_error_from_exception,
    qualify,
)
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import (
    GraphModelError,
    Node,
    NodeId,
    NodeOutcome,
    Resolved,
    Subtree,
    facts_from_geometry,
    unmet_condition,
)
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    KernelWarning,
    Provenance,
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
    dedupe_warnings,
)
from aero_kernel.validate import validate_aircraft, validate_values

logger = logging.getLogger(__name__)

__all__ = ["evaluate"]


@dataclass(frozen=True)
class _NodeRun:
    """What happened to one node: its outcome for the successors and what its results need.

    Attributes:
        outcome: The status (and error) the successors see.
        reason: Why the node is ``not_applicable`` or ``skipped``.
        anchor: The name its error and messages use for the node's quantity.
        outputs: The returned value per output parameter, for status ``ok``.
        warnings: The warnings the node's formula reported.
    """

    outcome: NodeOutcome
    anchor: str
    reason: Reason | None = None
    outputs: Mapping[str, object] | None = None
    warnings: tuple[KernelWarning, ...] = ()


def _rename(error: KernelError, old: str, new: str) -> KernelError:
    """Re-address a node's error to another quantity the node produces (the requested spelling)."""
    if old == new:
        return error
    return error.model_copy(
        update={
            "quantity": new,
            "message": error.message.replace(f"`{old}`", f"`{new}`"),
            "hint": error.hint.replace(f"`{old}`", f"`{new}`"),
        }
    )


def _unit_of(build: Build, slug: str) -> str | None:
    """The canon unit of a slug, or ``None`` if the kernel knows no such quantity."""
    quantity = build.model.quantity(slug)
    return None if quantity is None else quantity.unit


def _internal(slug: str) -> KernelError:
    """The ``internal`` error of a defect that is not tied to one exception."""
    return KernelError(
        code=ErrorCategory.INTERNAL.value,
        category=ErrorCategory.INTERNAL,
        quantity=slug,
        message=f"Internal error while computing `{slug}`.",
        hint="Report it; attach input and provenance.",
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
    ) -> None:
        self.build = build
        self.aircraft = aircraft
        self.request = request
        self.subtree = subtree
        self.call_id = call_id
        self.nodes: dict[NodeId, Node] = {node.id: node for node in subtree.nodes}
        self.values = {qualify(slug): value for slug, value in aircraft.values.items()}
        self.runs: dict[NodeId, _NodeRun] = {}
        facts = facts_from_geometry(aircraft.airplane)
        self.conditions = {
            node.id: unmet_condition(node, facts, aircraft.values.keys()) for node in subtree.nodes
        }
        # the first requested spelling of a node's quantities names the node in its messages
        self.requested_by_node: dict[NodeId, str] = {}
        for resolved in subtree.requested:
            self.requested_by_node.setdefault(resolved.producer, resolved.requested)

    # --- running the graph -----------------------------------------------------------------

    async def run(self) -> None:
        """Run the layers in order; the nodes of a layer concurrently."""
        for layer in self.subtree.layers:
            async with asyncio.TaskGroup() as group:
                tasks = [group.create_task(self._node(self.nodes[node_id])) for node_id in layer]
            for node_id, task in zip(layer, tasks, strict=True):
                self.runs[node_id] = task.result()

    def _anchor(self, node: Node) -> str:
        """The name of the node's quantity in its errors: the requested spelling, else its first."""
        requested = self.requested_by_node.get(node.id)
        return requested or display_slug(node.produces[0].quantity)

    def _formula(self, node: Node) -> tuple[Formula, str]:
        """The node's formula and its public slug."""
        formula = self.build.model.formula(node.id.formula)
        assert formula is not None  # the graph was built from this very model
        return formula, display_slug(node.id.formula)

    async def _node(self, node: Node) -> _NodeRun:
        """Run one node; any defect of the engine itself becomes an ``internal`` outcome."""
        extra = {
            "call_id": self.call_id,
            "formula": display_slug(node.id.formula),
            "application": node.id.application,
        }
        started = time.perf_counter()
        logger.debug("node started", extra=extra)
        try:
            run = await self._evaluate_node(node)
        except Exception as exc:  # a node never raises out of the call (ch. 8.1)
            anchor = self._anchor(node)
            error = internal_error_from_exception(
                exc,
                quantity=anchor,
                formula=display_slug(node.id.formula),
                application=node.id.application,
                call_id=self.call_id,
            )
            run = self._failed(anchor, error)
        logger.debug(
            "node finished: %s in %.1f ms",
            run.outcome.status.value,
            (time.perf_counter() - started) * 1000,
            extra=extra,
        )
        return run

    @staticmethod
    def _failed(anchor: str, error: KernelError) -> _NodeRun:
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.ERROR, error=error), anchor=anchor
        )

    @staticmethod
    def _without_value(anchor: str, status: QuantityStatus, reason: Reason) -> _NodeRun:
        return _NodeRun(outcome=NodeOutcome(status=status), anchor=anchor, reason=reason)

    async def _evaluate_node(self, node: Node) -> _NodeRun:
        """The decision chain of one node (ch. 6 steps 4 and 5)."""
        formula, formula_slug = self._formula(node)
        anchor = self._anchor(node)
        context = {"quantity": anchor, "formula": formula_slug, "application": node.id.application}

        condition = self.conditions[node.id]
        if isinstance(condition, Reason):
            return self._without_value(anchor, QuantityStatus.NOT_APPLICABLE, condition)
        if isinstance(condition, KernelError):
            return self._failed(anchor, condition.model_copy(update=context))

        causes = [
            error.model_copy(update={"quantity": display_slug(edge.quantity)})
            for edge in self.subtree.edges[node.id]
            if (error := self.runs[edge.predecessor].outcome.error) is not None
        ]
        if causes:
            return self._failed(
                anchor,
                aggregate_upstream(
                    causes,
                    quantity=anchor,
                    formula=formula_slug,
                    application=node.id.application,
                ),
            )
        if node.cost == "minutes" and not self.request.include_long_runs:
            return self._without_value(
                anchor,
                QuantityStatus.SKIPPED,
                Reason(
                    code=ReasonCode.LONG_RUN_NOT_INCLUDED,
                    message=f"`{anchor}` is a long run and the request does not include long runs.",
                ),
            )
        propagated = self.subtree.propagate(
            node.id, {k: v.outcome for k, v in self.runs.items()}, quantity=anchor
        )
        if propagated is not None and propagated.reason is not None:
            return self._without_value(anchor, propagated.status, propagated.reason)

        inputs, missing = self._inputs(node, formula)
        if missing:
            return self._failed(anchor, self._missing_input(node, anchor, formula_slug, missing))
        implementation = self.build.registry.implementation(node.id.formula)
        if implementation is None:
            return self._failed(
                anchor,
                KernelError(
                    code=ErrorCategory.NOT_IMPLEMENTED.value,
                    category=ErrorCategory.NOT_IMPLEMENTED,
                    quantity=anchor,
                    formula=formula_slug,
                    application=node.id.application,
                    message=f"`{formula_slug}` is in the canon, not in the kernel yet.",
                    hint="Request a quantity whose formula is implemented.",
                ),
            )

        warner = Context(origin=display_slug(node.produces[0].quantity))
        try:
            returned = await implementation.func(inputs, warner)
        except FormulaError as exc:
            return self._failed(
                anchor,
                exc.to_kernel_error(
                    **context, input_path=self._input_path(node, formula, exc.parameter)
                ),
            )
        self._check_outputs(node, formula, returned)
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.OK),
            anchor=anchor,
            outputs=returned,
            warnings=warner.warnings,
        )

    # --- inputs ----------------------------------------------------------------------------

    def _inputs(self, node: Node, formula: Formula) -> tuple[Inputs, list[str]]:
        """Bind the formula's parameters: ``x`` and the qualified slugs of missing inputs."""
        application = formula.application(node.id.application)
        bound: dict[str, Value | None] = {}
        missing: list[str] = []
        for parameter, binding in application.bind.items():
            if isinstance(binding, ConstBinding):
                bound[parameter] = binding.const
                continue
            value = self._read(node, binding)
            if value is not None:
                bound[parameter] = value
            elif parameter in formula.optional:
                bound[parameter] = None
            else:
                missing.append(binding)
        return bound, missing

    def _read(self, node: Node, slug: str) -> Value | None:
        """The value of a bound quantity: a predecessor's output or a supplied input."""
        for edge in self.subtree.edges[node.id]:
            if edge.quantity == slug:
                predecessor = self.nodes[edge.predecessor]
                parameter = next(p.parameter for p in predecessor.produces if p.quantity == slug)
                outputs = self.runs[edge.predecessor].outputs
                value = None if outputs is None else outputs[parameter]
                return value if isinstance(value, float | AirplaneGeometry) else None
        quantity = self.build.model.quantity(slug)
        if quantity is not None and quantity.type == "airplane":
            return self.aircraft.airplane
        return self.values.get(slug) if quantity is not None and quantity.type == "scalar" else None

    def _missing_input(
        self, node: Node, anchor: str, formula_slug: str, missing: Sequence[str]
    ) -> KernelError:
        """The ``missing_input`` error of a node that reads values nobody supplied."""
        names = ", ".join(f"`{display_slug(slug)}`" for slug in missing)
        first = self.build.model.quantity(missing[0])
        path = (
            f"values.{display_slug(missing[0])}"
            if first is not None and first.type == "scalar"
            else None
        )
        return KernelError(
            code="missing_input",
            category=ErrorCategory.INVALID_INPUT,
            quantity=anchor,
            formula=formula_slug,
            application=node.id.application,
            input_path=path,
            message=f"`{anchor}` needs {names}, which was not supplied.",
            hint=f"Supply {names}.",
            detail={"inputs": [display_slug(slug) for slug in missing]},
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
        if quantity.type == "airplane":
            return "airplane"
        return f"values.{display_slug(binding)}" if quantity.type == "scalar" else None

    # --- outputs ---------------------------------------------------------------------------

    def _check_outputs(self, node: Node, formula: Formula, returned: Mapping[str, object]) -> None:
        """Require exactly the output parameters, and a finite float for each exposed scalar.

        Raises:
            ValueError: If the formula returned other parameters than the canon declares.
            TypeError: If an exposed output is not a value of its quantity's type.
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

    # --- results ---------------------------------------------------------------------------

    def result_of(self, resolved: Resolved) -> QuantityResult:
        """The result of one requested quantity."""
        run = self.runs[resolved.producer]
        slug, unit = resolved.requested, resolved.quantity.unit
        status = run.outcome.status
        if status is QuantityStatus.ERROR:
            error = run.outcome.error
            assert error is not None  # NodeOutcome: an error exactly with status error
            return QuantityResult(
                slug=slug, unit=unit, status=status, error=_rename(error, run.anchor, slug)
            )
        if status is not QuantityStatus.OK:
            return QuantityResult(slug=slug, unit=unit, status=status, reason=run.reason)
        node = self.nodes[resolved.producer]
        parameter = next(p.parameter for p in node.produces if p.quantity == resolved.slug)
        formula, _ = self._formula(node)
        value = None if run.outputs is None else run.outputs[parameter]
        assert isinstance(value, float)  # checked by _check_outputs for a scalar
        warnings = dedupe_warnings(
            warning
            for node_id in self.subtree.nodes_for(resolved.slug)
            for warning in self.runs[node_id].warnings
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


def _provenance(build: Build) -> Provenance:
    """The provenance of a call on a loaded build."""
    return Provenance(
        build_digest=build.digest,
        canon_model_hash=build.model.content_hash,
        canon_source_commit=build.model.source_commit,
    )


def _log_summary(call_id: str, result: ComputeResult, started: float) -> None:
    """The one ``INFO`` line of a call (ch. 8.14)."""
    counts = Counter(q.status.value for q in result.quantities)
    logger.info(
        "compute: %d quantities (%s), %d input errors, %.1f ms",
        len(result.quantities),
        ", ".join(f"{status}={n}" for status, n in sorted(counts.items())) or "none",
        len(result.input_errors),
        (time.perf_counter() - started) * 1000,
        extra={"call_id": call_id},
    )


def _graph_defect(
    build: Build, request: ComputeRequest, exc: GraphModelError, call_id: str
) -> ComputeResult:
    """Every requested quantity is ``internal``: the model's graph cannot serve the request."""
    logger.error(
        "the canon graph cannot serve the request", exc_info=exc, extra={"call_id": call_id}
    )
    quantities = tuple(
        QuantityResult(
            slug=slug,
            unit=_unit_of(build, slug),
            status=QuantityStatus.ERROR,
            error=_internal(slug),
        )
        for slug in request.quantities
    )
    return ComputeResult(quantities=quantities, provenance=_provenance(build))


async def evaluate(build: Build, aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    """Compute a request on a build (ch. 6); the internal seam under ``compute``.

    Args:
        build: The canon model with its graph and implementations.
        aircraft: The geometry and the input and target values, in canon units.
        request: The quantities to compute.

    Returns:
        ``input_errors`` and nothing computed if the input is inadmissible, else one result per
        requested slug in request order. Never raises for a computational failure.
    """
    call_id = secrets.token_hex(4)
    started = time.perf_counter()
    errors = validate_aircraft(aircraft).errors + validate_values(aircraft.values, build.model)
    if errors:
        result = ComputeResult(input_errors=errors, provenance=_provenance(build))
        _log_summary(call_id, result, started)
        return result
    try:
        subtree = build.graph.subtree(request.quantities)
    except GraphModelError as exc:
        result = _graph_defect(build, request, exc, call_id)
        _log_summary(call_id, result, started)
        return result
    call = _Call(build, aircraft, request, subtree, call_id)
    await call.run()
    results: dict[str, QuantityResult] = {
        error.quantity: QuantityResult(
            slug=error.quantity,
            unit=_unit_of(build, error.quantity),
            status=QuantityStatus.ERROR,
            error=error,
        )
        for error in subtree.errors
        if error.quantity is not None
    }
    results.update({r.requested: call.result_of(r) for r in subtree.requested})
    result = ComputeResult(
        quantities=tuple(results[slug] for slug in request.quantities),
        provenance=_provenance(build),
    )
    _log_summary(call_id, result, started)
    return result
