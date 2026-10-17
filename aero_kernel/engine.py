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

from aero_kernel.build import Build
from aero_kernel.canon.model import ConstBinding, Formula
from aero_kernel.context import Context, Inputs, Value
from aero_kernel.errors import (
    ErrorCategory,
    FormulaError,
    KernelError,
    display_slug,
    internal_error,
    internal_error_from_exception,
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
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    KernelWarning,
    Provenance,
    QuantityResult,
    QuantityStatus,
    Reason,
    dedupe_warnings,
)
from aero_kernel.validate import validate_aircraft, validate_values
from pydantic import JsonValue

logger = logging.getLogger(__name__)

__all__ = ["evaluate"]


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
    """

    outcome: NodeOutcome
    anchor: str
    reason_for: Callable[[str], Reason] | None = None
    error_for: Callable[[str], KernelError] | None = None
    outputs: Mapping[str, object] | None = None
    warnings: tuple[KernelWarning, ...] = ()


def _unit_of(build: Build, slug: str) -> str | None:
    """The canon unit of a slug, or ``None`` if the kernel knows no such quantity."""
    quantity = build.model.quantity(slug)
    return None if quantity is None else quantity.unit


# The quantity types a value of v1 can carry between nodes (``Value``).
_CARRIED_TYPES = frozenset({"scalar", "airplane"})


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
        anchor: str, error_for: Callable[[str], KernelError], error: KernelError | None = None
    ) -> _NodeRun:
        """A node that failed; ``error`` is its error worded for the anchor, if already built."""
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.ERROR, error=error or error_for(anchor)),
            anchor=anchor,
            error_for=error_for,
        )

    @staticmethod
    def _without_value(
        anchor: str, status: QuantityStatus, reason_for: Callable[[str], Reason]
    ) -> _NodeRun:
        """A node that is ``not_applicable`` or ``skipped``."""
        return _NodeRun(outcome=NodeOutcome(status=status), anchor=anchor, reason_for=reason_for)

    async def _evaluate_node(self, node: Node) -> _NodeRun:
        """The decision chain of one node (ch. 6 steps 4 and 5)."""
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
        if isinstance(condition, KernelError):
            return self._failed(
                anchor,
                lambda slug, error=condition: error.model_copy(
                    update={"quantity": slug, "formula": formula_slug}
                ),
            )

        propagated = self.subtree.propagate(
            node.id,
            {node_id: run.outcome for node_id, run in self.runs.items()},
            quantity=anchor,
            skip_long_run=node.cost == "minutes" and not self.request.include_long_runs,
        )
        if propagated is not None:
            return self._propagated(anchor, propagated)

        unsupported = self._unsupported_reads(node)
        if unsupported:
            return self._failed(
                anchor,
                lambda slug: self._unsupported_error(node, slug, formula_slug, unsupported),
            )
        inputs, missing = self._inputs(node, formula)
        if missing:
            return self._failed(
                anchor, lambda slug: self._missing_input(node, slug, formula_slug, missing)
            )
        implementation = self.build.registry.implementation(node.id.formula)
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

        warner = Context(origin=display_slug(node.produces[0].quantity))
        try:
            returned = await implementation.func(inputs, warner)
        except FormulaError as exc:
            path = self._input_path(node, formula, exc.parameter)
            return self._failed(
                anchor,
                lambda slug, raised=exc: raised.to_kernel_error(
                    quantity=slug, formula=formula_slug, application=application, input_path=path
                ),
            )
        self._check_outputs(node, formula, returned)
        return _NodeRun(
            outcome=NodeOutcome(status=QuantityStatus.OK),
            anchor=anchor,
            outputs=returned,
            warnings=warner.warnings,
        )

    def _propagated(self, anchor: str, propagated: Propagated) -> _NodeRun:
        """A node whose status its predecessors or its cost class force on it."""
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
        names = _enumerate([f"`{display_slug(slug)}` (a {kind})" for slug, kind in unsupported])
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
            message=f"`{quantity}` needs {_enumerate([f'`{n}`' for n in shown])}, "
            f"which {verb} not supplied.",
            hint=f"Supply {_enumerate([f'`{n}`' for n in shown])} in `values`.",
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
        if quantity.type == "airplane":
            return "airplane"
        return f"values.{display_slug(binding)}" if quantity.type == "scalar" else None

    # --- outputs ---------------------------------------------------------------------------

    def _check_outputs(self, node: Node, formula: Formula, returned: Mapping[str, object]) -> None:
        """Require exactly the output parameters, and a value of its type for each carried output.

        Outputs of a type v1 cannot carry are not carried: whoever reads one is
        ``not_implemented`` (``unsupported_value_type``).

        Raises:
            ValueError: If the formula returned other parameters than the canon declares.
            TypeError: If an exposed scalar or airplane output is not a value of its type.
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


def _enumerate(names: Sequence[str]) -> str:
    """Write names as a list in prose: ``a``, ``a and b``, ``a, b and c``."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _error_of(propagated: Propagated) -> KernelError:
    """The error of a propagation that forces status ``error``."""
    assert propagated.error is not None
    return propagated.error


def _reason_of(propagated: Propagated) -> Reason:
    """The reason of a propagation that forces status ``skipped`` or ``not_applicable``."""
    assert propagated.reason is not None
    return propagated.reason


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
    subtree = build.graph.subtree(request.quantities)
    call = _Call(build, aircraft, request, subtree, call_id)
    await call.run()
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
        provenance=_provenance(build),
    )
    _log_summary(call_id, result, started)
    return result
