"""The graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13).

Pure structure: which applications a request needs, in which order, which of them are independent,
which method worlds a quantity has. Nothing here evaluates a formula or calls a tool.

Identifiers inside the graph are the canon's qualified ``<namespace>:<slug>`` form. Errors and world
assignments speak the public bare slug.
"""

import itertools
import logging
import math
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Self

from aero_kernel.canon.model import (
    CanonModel,
    CostClass,
    Formula,
    Quantity,
    WhenTerm,
)
from aero_kernel.errors import (
    ErrorCategory,
    KernelError,
    aggregate_upstream,
    display_slug,
    format_world_assignment,
    join_names,
    qualify,
)
from aero_kernel.geometry import AirplaneGeometry, Wing
from aero_kernel.schema import QuantityStatus, Reason, ReasonCode
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)

__all__ = [
    "PENDING_WHEN_TERMS",
    "CanonGraph",
    "Edge",
    "GraphModelError",
    "Node",
    "NodeId",
    "NodeOutcome",
    "Produce",
    "Propagated",
    "Read",
    "Resolved",
    "Subtree",
    "WhenFacts",
    "facts_from_geometry",
    "unmet_condition",
]

_FROZEN = ConfigDict(extra="forbid", frozen=True)


class GraphModelError(Exception):
    """The canon model is not a well-formed graph: an internal defect of the model, not of a request.

    The importer's checks should have caught it; the engine reports it as an ``internal`` error.
    """


class NodeId(BaseModel):
    """Identity of a node: one application of one formula.

    Attributes:
        formula: Qualified formula slug, ``<namespace>:<slug>``.
        application: Id of the application within the formula.
    """

    model_config = _FROZEN

    formula: str
    application: str

    def __hash__(self) -> int:
        """Hash by value; stated explicitly because the type checker does not infer pydantic's."""
        return hash((self.formula, self.application))

    @property
    def formula_slug(self) -> str:
        """The public bare slug of the formula, as errors and world assignments write it."""
        return self.formula.partition(":")[2]


class Read(BaseModel):
    """A quantity an application reads through one input parameter.

    Attributes:
        parameter: The formula's input parameter.
        quantity: Qualified slug of the quantity bound to it.
        optional: Whether the parameter is declared ``optional`` by the formula.
    """

    model_config = _FROZEN

    parameter: str
    quantity: str
    optional: bool


class Produce(BaseModel):
    """A quantity an application exposes through one output parameter.

    Attributes:
        parameter: The formula's output parameter.
        quantity: Qualified slug of the quantity it produces.
    """

    model_config = _FROZEN

    parameter: str
    quantity: str


class Node(BaseModel):
    """An application as a graph node (ch. 8.5).

    Attributes:
        id: Identity of the node.
        cost: Cost class of its formula (ch. 8.7).
        when: Geometry condition, or ``None``.
        given: Qualified slugs that must be supplied, empty if none.
        reads: The quantity-bound input parameters; constants are no reads.
        produces: The exposed output parameters; unexposed ones are left out.
        worlds: Method worlds of an uncertain formula, in canon order; empty if certain.
    """

    model_config = _FROZEN

    id: NodeId
    cost: CostClass
    when: WhenTerm | None
    given: tuple[str, ...]
    reads: tuple[Read, ...]
    produces: tuple[Produce, ...]
    worlds: tuple[str, ...]


class Resolved(BaseModel):
    """A requested quantity that a node can produce.

    Attributes:
        slug: Qualified slug of the quantity.
        requested: The request's exact spelling of the slug; results and errors echo it.
        quantity: The quantity's canon entry.
        producer: The node whose application produces it.
    """

    model_config = _FROZEN

    slug: str
    requested: str
    quantity: Quantity
    producer: NodeId


class Edge(BaseModel):
    """A value edge: a node reads a quantity that another node produces.

    Attributes:
        predecessor: The producing node.
        quantity: Qualified slug of the quantity that flows.
        parameter: The reader's input parameter it is bound to.
    """

    model_config = _FROZEN

    predecessor: NodeId
    quantity: str
    parameter: str


class NodeOutcome(BaseModel):
    """What happened to a node, as far as its successors care (ch. 8.13).

    Attributes:
        status: The node's status.
        error: Why it failed, exactly for status ``error``.
    """

    model_config = _FROZEN

    status: QuantityStatus
    error: KernelError | None = None

    @model_validator(mode="after")
    def _check_error(self) -> Self:
        """Require an error exactly with status ``error``."""
        if (self.status is QuantityStatus.ERROR) != (self.error is not None):
            msg = "an outcome carries an error exactly when its status is error"
            raise ValueError(msg)
        return self


class Propagated(BaseModel):
    """The status a node inherits from the predecessors it reads (ch. 8.13).

    Attributes:
        status: ``error``, ``skipped`` or ``not_applicable``.
        reason: Why, for ``skipped`` and ``not_applicable``.
        error: The ``upstream_failed`` error, for ``error``.
        reword: Builds the same propagation for another quantity; see :meth:`addressed_to`.
    """

    model_config = _FROZEN

    status: QuantityStatus
    reason: Reason | None = None
    error: KernelError | None = None
    reword: Callable[[str], "Propagated"] = Field(exclude=True, repr=False)

    def addressed_to(self, quantity: str) -> "Propagated":
        """Return the same propagation worded for another quantity of the same node.

        A node that produces several requested quantities has one status; each of them is told
        in its own name.

        Args:
            quantity: Slug of the quantity the message is reported for.

        Returns:
            The propagation with ``quantity`` in the error and the reason.
        """
        return self.reword(quantity)


class Subtree(BaseModel):
    """The part of the graph one request needs (ch. 6 steps 2 and 3, K29).

    Attributes:
        requested: The requested quantities that resolved, in request order; a duplicate is
            ``ComputeRequest``'s to reject, so none occurs here.
        errors: The errors of the rejected requested quantities, in request order.
        nodes: The needed nodes in topological order (``layers`` flattened).
        edges: Per node, the value edges it reads through; only what it actually reads.
        leaf_inputs: Qualified slugs of the supplied quantities the nodes read, sorted.
        layers: Nodes grouped so that every node's predecessors lie in earlier layers; the nodes
            of one layer are independent and may run concurrently. Sorted by formula, application.
    """

    model_config = _FROZEN

    requested: tuple[Resolved, ...]
    errors: tuple[KernelError, ...]
    nodes: tuple[Node, ...]
    edges: dict[NodeId, tuple[Edge, ...]]
    leaf_inputs: tuple[str, ...]
    layers: tuple[tuple[NodeId, ...], ...]

    def producer_of(self, slug: str) -> NodeId:
        """Return the node that produces a requested quantity.

        Args:
            slug: Bare or qualified slug of a quantity in ``requested``.

        Returns:
            The producing node.

        Raises:
            KeyError: If the quantity was not requested (or was rejected).
        """
        qualified = qualify(slug)
        for resolved in self.requested:
            if resolved.slug == qualified:
                return resolved.producer
        raise KeyError(slug)

    def long_run_nodes(self) -> tuple[NodeId, ...]:
        """Return the nodes of cost class ``minutes``, in order (ch. 8.7).

        The graph decides nothing: the engine skips them when ``include_long_runs`` is off.
        """
        return tuple(node.id for node in self.nodes if node.cost == "minutes")

    def propagate(
        self,
        node: NodeId,
        outcomes: Mapping[NodeId, NodeOutcome],
        *,
        quantity: str,
        status: QuantityStatus,
        world: str | None = None,
    ) -> Propagated | None:
        """Ask whether a node inherits a status from the predecessors it reads (ch. 8.13).

        The graph owns the inheritance (rows 2, 4 and 7 of the status order); the engine owns the
        order between all rows and calls this once per row. Only the predecessors the node reads
        count, an ``optional`` read included: ``optional`` only covers an absent supplied value. The
        causes of an error name the quantities the node reads (one per value edge), not the
        quantity its predecessor's own error was reported for.

        Args:
            node: The node.
            outcomes: The outcome of each of its predecessors (others are ignored).
            quantity: Slug of the quantity the status is reported for, used in an error or reason;
                :meth:`Propagated.addressed_to` rewords it for another quantity of the node.
            status: The status asked for: ``error`` (``upstream_failed``), ``skipped``
                (``depends_on_skipped``) or ``not_applicable`` (``depends_on_not_applicable``).
            world: Canonical world assignment string of the evaluation, if any.

        Returns:
            The inherited status, or ``None`` if no read predecessor has it.

        Raises:
            KeyError: If a read predecessor has no outcome.
            ValueError: If ``status`` is ``ok``, which nothing inherits.
        """
        if status is QuantityStatus.OK:
            msg = "status ok is not inherited"
            raise ValueError(msg)
        edges = self.edges[node]
        causes = [
            error.model_copy(update={"quantity": display_slug(edge.quantity)})
            for edge in edges
            if (error := outcomes[edge.predecessor].error) is not None
        ]
        read = [e.quantity for e in edges if outcomes[e.predecessor].status is status]
        if not (causes if status is QuantityStatus.ERROR else read):
            return None
        code = ReasonCode.DEPENDS_ON_SKIPPED
        wording = "skipped"
        if status is QuantityStatus.NOT_APPLICABLE:
            code, wording = ReasonCode.DEPENDS_ON_NOT_APPLICABLE, "not applicable"

        def build(name: str) -> Propagated:
            if status is QuantityStatus.ERROR:
                error = aggregate_upstream(
                    causes,
                    quantity=name,
                    formula=display_slug(node.formula),
                    application=node.application,
                    world=world,
                )
                return Propagated(status=status, error=error, reword=build)
            names = ", ".join(dict.fromkeys(f"`{display_slug(slug)}`" for slug in read))
            message = f"`{name}` reads {names}, which is {wording}."
            return Propagated(
                status=status, reason=Reason(code=code, message=message), reword=build
            )

        return build(quantity)

    def nodes_for(self, slug: str) -> tuple[NodeId, ...]:
        """Return the nodes a requested quantity needs, in topological order.

        Args:
            slug: Bare or qualified slug of a quantity in ``requested``.

        Returns:
            The quantity's own subtree: its producer and everything it reads back to the leaves.

        Raises:
            KeyError: If the quantity was not requested.
        """
        needed = self._closure(self.producer_of(slug))
        return tuple(node.id for node in self.nodes if node.id in needed)

    def uncertain_formulas(self, slug: str) -> tuple[str, ...]:
        """Return the uncertain formulas in a requested quantity's subtree (A11).

        Worlds follow value edges, so a formula that reads an uncertain quantity is in the subtree
        like any other; ``embeds`` carry none.

        Args:
            slug: Bare or qualified slug of a quantity in ``requested``.

        Returns:
            Bare formula slugs, sorted.

        Raises:
            KeyError: If the quantity was not requested.
        """
        return self._uncertain_in(self._closure(self.producer_of(slug)))

    def world_assignments(self, slug: str) -> tuple[dict[str, str], ...]:
        """Return the Cartesian product of the worlds of a quantity's uncertain formulas (A11).

        Args:
            slug: Bare or qualified slug of a quantity in ``requested``.

        Returns:
            One world per uncertain formula and assignment, formulas sorted by slug, worlds in
            canon order. A quantity with no uncertain formula has the one empty assignment, which
            stands for "no world". Write one with :func:`format_world_assignment`.

        Raises:
            KeyError: If the quantity was not requested.
        """
        worlds = self._worlds()
        formulas = self.uncertain_formulas(slug)
        return tuple(
            dict(zip(formulas, combination, strict=True))
            for combination in itertools.product(*(worlds[f] for f in formulas))
        )

    def assignment_key(self, node: NodeId, assignment: Mapping[str, str]) -> str | None:
        """Restrict a world assignment to the uncertain formulas a node depends on.

        Nodes with the same key compute the same value, so the engine runs them once and shares
        the result across the assignments.

        Args:
            node: A node of the subtree.
            assignment: A full assignment, as returned by :meth:`world_assignments`.

        Returns:
            The canonical string of the restricted assignment, or ``None`` if the node depends on
            no uncertain formula.

        Raises:
            KeyError: If the node is not in the subtree or the assignment lacks a needed formula.
        """
        formulas = self._uncertain_in(self._closure(node))
        if not formulas:
            return None
        return format_world_assignment({formula: assignment[formula] for formula in formulas})

    def _closure(self, root: NodeId) -> set[NodeId]:
        """The node and everything it reads, transitively."""
        found: set[NodeId] = set()
        pending = [root]
        while pending:
            node = pending.pop()
            if node not in found:
                found.add(node)
                pending.extend(edge.predecessor for edge in self.edges[node])
        return found

    def _worlds(self) -> dict[str, tuple[str, ...]]:
        """The worlds per uncertain formula (bare slug) among the subtree's nodes."""
        return {n.id.formula_slug: n.worlds for n in self.nodes if n.worlds}

    def _uncertain_in(self, members: set[NodeId]) -> tuple[str, ...]:
        """The sorted bare slugs of the uncertain formulas among the given nodes."""
        return tuple(
            sorted({n.id.formula_slug for n in self.nodes if n.worlds and n.id in members})
        )


def _sort_key(node: NodeId) -> tuple[str, str]:
    """Order nodes by formula slug, then application id."""
    return node.formula, node.application


def _layers(edges: dict[NodeId, tuple[Edge, ...]]) -> tuple[tuple[NodeId, ...], ...]:
    """Group nodes into layers of independent nodes (Kahn's algorithm, deterministic).

    Raises:
        GraphModelError: If the nodes contain a cycle.
    """
    predecessors = {node: {edge.predecessor for edge in held} for node, held in edges.items()}
    layers: list[tuple[NodeId, ...]] = []
    placed: set[NodeId] = set()
    remaining = set(edges)
    while remaining:
        ready = sorted((n for n in remaining if predecessors[n] <= placed), key=_sort_key)
        if not ready:
            raise GraphModelError(_cycle_message(predecessors, remaining))
        layers.append(tuple(ready))
        placed.update(ready)
        remaining.difference_update(ready)
    return tuple(layers)


def _cycle_message(predecessors: dict[NodeId, set[NodeId]], remaining: set[NodeId]) -> str:
    """Name one cycle among the nodes Kahn's algorithm could not place, in data-flow direction."""
    path = [min(remaining, key=_sort_key)]
    while True:
        # every unplaced node has an unplaced predecessor, otherwise it would have been placed
        following = min((p for p in predecessors[path[-1]] if p in remaining), key=_sort_key)
        if following in path:
            cycle = path[path.index(following) :]
            break
        path.append(following)
    flow = [cycle[0], *reversed(cycle[1:]), cycle[0]]
    return "cycle: " + " -> ".join(_label(node) for node in flow)


def _node(namespace: str, slug: str, formula: Formula, application_id: str) -> Node:
    """Build the node of one application."""
    application = formula.application(application_id)
    return Node(
        id=NodeId(formula=f"{namespace}:{slug}", application=application_id),
        cost=formula.cost,
        when=application.when,
        given=application.given or (),
        reads=tuple(
            Read(parameter=parameter, quantity=binding, optional=parameter in formula.optional)
            for parameter, binding in application.bind.items()
            if isinstance(binding, str)
        ),
        produces=tuple(
            Produce(parameter=parameter, quantity=quantity)
            for parameter, quantity in application.produce.items()
            if quantity is not None
        ),
        worlds=formula.worlds,
    )


def _label(node: NodeId) -> str:
    """Write a node id as ``<formula>.<application>``, the form of ``embeds``."""
    return f"{node.formula}.{node.application}"


class CanonGraph:
    """The dependency structure of a canon model, built once and shared."""

    def __init__(self, model: CanonModel) -> None:
        """Index the model's applications.

        Args:
            model: The loaded canon model.
        """
        self._model = model
        self._nodes: dict[NodeId, Node] = {}
        for namespace, content in model.namespaces.items():
            for slug, formula in content.formulas.items():
                for application in formula.applications:
                    node = _node(namespace, slug, formula, application.id)
                    self._nodes[node.id] = node
        self._producers = self._index_producers()
        self._check_world_slugs()
        self._check_producers()
        _layers(self._edges_back_from(list(self._nodes)))  # a cycle anywhere is a model defect

    def _index_producers(self) -> dict[str, NodeId]:
        """Map every produced quantity to its one producing node."""
        producers: dict[str, NodeId] = {}
        for node in self._nodes.values():
            for produce in node.produces:
                other = producers.setdefault(produce.quantity, node.id)
                if other != node.id:
                    msg = (
                        f"{produce.quantity} has two producers: "
                        f"{_label(other)} and {_label(node.id)}"
                    )
                    raise GraphModelError(msg)
        return producers

    def _check_world_slugs(self) -> None:
        """Require the bare slugs of uncertain formulas to be unique: assignments are keyed by them."""
        owners: dict[str, str] = {}
        for node in self._nodes.values():
            if node.worlds:
                other = owners.setdefault(node.id.formula_slug, node.id.formula)
                if other != node.id.formula:
                    msg = (
                        f"uncertain formulas {other} and {node.id.formula} share the slug "
                        f"{node.id.formula_slug}; world assignments could not tell them apart"
                    )
                    raise GraphModelError(msg)

    def _check_producers(self) -> None:
        """Require every computed quantity (role ``derived`` or ``output``) to have a producer."""
        for namespace, content in self._model.namespaces.items():
            for slug, quantity in content.quantities.items():
                qualified = f"{namespace}:{slug}"
                if quantity.role in ("derived", "output") and qualified not in self._producers:
                    msg = f"{qualified} is computed but has no producer"
                    raise GraphModelError(msg)

    @property
    def node_ids(self) -> tuple[NodeId, ...]:
        """The ids of all nodes of the model."""
        return tuple(self._nodes)

    def node(self, node_id: NodeId) -> Node:
        """Return the node with the given id.

        Raises:
            KeyError: If the model has no such application.
        """
        return self._nodes[node_id]

    def subtree(self, quantities: Sequence[str]) -> Subtree:
        """Find the nodes a request needs and order them (ch. 6 steps 2 and 3).

        Only the requested quantities and what they read, back to the supplied leaves, are
        included (K29). Requests that do not resolve are reported in ``errors`` and add no node.

        Args:
            quantities: Requested quantity slugs, bare or qualified.

        Returns:
            The subtree.

        """
        requested: list[Resolved] = []
        errors: list[KernelError] = []
        for slug in quantities:
            resolved = self.resolve(slug)
            if isinstance(resolved, KernelError):
                errors.append(resolved)
            else:
                requested.append(resolved)
        edges = self._edges_back_from([r.producer for r in requested])
        layers = _layers(edges)
        leaves = {
            read.quantity
            for node in edges
            for read in self._nodes[node].reads
            if read.quantity not in self._producers
        }
        logger.debug(
            "subtree of %d quantities: %d nodes in %d layers",
            len(requested),
            len(edges),
            len(layers),
        )
        return Subtree(
            requested=tuple(requested),
            errors=tuple(errors),
            nodes=tuple(self._nodes[node] for layer in layers for node in layer),
            edges=edges,
            leaf_inputs=tuple(sorted(leaves)),
            layers=layers,
        )

    def _edges_back_from(self, roots: Sequence[NodeId]) -> dict[NodeId, tuple[Edge, ...]]:
        """Walk the value edges back from the roots; return the edges read per reached node."""
        edges: dict[NodeId, tuple[Edge, ...]] = {}
        pending = list(roots)
        while pending:
            node = pending.pop()
            if node in edges:
                continue
            edges[node] = tuple(
                Edge(
                    predecessor=self._producers[read.quantity],
                    quantity=read.quantity,
                    parameter=read.parameter,
                )
                for read in self._nodes[node].reads
                if read.quantity in self._producers
            )
            pending.extend(edge.predecessor for edge in edges[node])
        return edges

    def resolve(self, slug: str) -> Resolved | KernelError:
        """Check a requested slug and find its producing node (ch. 6 step 2, Q38).

        Args:
            slug: Bare or qualified quantity slug, as requested.

        Returns:
            The resolved quantity, or the per-quantity error the request earns: ``unknown_quantity``,
            ``not_requestable`` for an input or target, ``non_scalar_result`` for a quantity that
            is not a scalar (v1).

        """
        qualified = _try_qualify(slug)
        quantity = None if qualified is None else self._model.quantity(qualified)
        if qualified is None or quantity is None:
            return _request_error(
                slug,
                "unknown_quantity",
                ErrorCategory.INVALID_INPUT,
                f"`{slug}` is not a quantity of the canon.",
                "Use a quantity slug from the canon vocabulary.",
            )
        if quantity.role in ("input", "target"):
            return _request_error(
                slug,
                "not_requestable",
                ErrorCategory.INVALID_INPUT,
                f"`{slug}` is a {quantity.role}: it is supplied, not computed.",
                "Pass it in `values` and request a derived or output quantity.",
            )
        if quantity.type != "scalar":
            return _request_error(
                slug,
                "non_scalar_result",
                ErrorCategory.NOT_IMPLEMENTED,
                f"`{slug}` is a {quantity.type}; v1 returns scalar quantities only.",
                "Request a scalar quantity.",
            )
        # every computed quantity has a producer: the constructor checked it
        producer = self._producers[qualified]
        return Resolved(slug=qualified, requested=slug, quantity=quantity, producer=producer)


def _try_qualify(slug: str) -> str | None:
    """Qualify a slug; a malformed one names no quantity, so ``None``."""
    try:
        return qualify(slug)
    except ValueError:
        return None


def _request_error(
    slug: str, code: str, category: ErrorCategory, message: str, hint: str
) -> KernelError:
    """Build the error of one rejected requested quantity."""
    return KernelError(code=code, category=category, quantity=slug, message=message, hint=hint)


# --- application conditions (ch. 8.5) -----------------------------------------------------------


class WhenFacts(BaseModel):
    """The facts of an aircraft's geometry that the closed ``when`` vocabulary asks about.

    Attributes:
        has_aileron: A device acts as aileron, flaperon or elevon.
        has_separate_flap_and_aileron: A flap and a distinct aileron or elevon exist; a flaperon
            counts as neither (D10).
        has_vertical_tail: The aircraft has a vertical tail (provisional rule, see below).
    """

    model_config = _FROZEN

    has_aileron: bool
    has_separate_flap_and_aileron: bool
    has_vertical_tail: bool

    def holds(self, term: WhenTerm) -> bool:
        """Tell whether a ``when`` term holds.

        Args:
            term: A term of the closed vocabulary.

        Returns:
            Its fact.

        Raises:
            ValueError: If the term is in :data:`PENDING_WHEN_TERMS`; it has no fact yet and
                :func:`unmet_condition` reports it as a ``not_implemented`` error instead.
        """
        if term in PENDING_WHEN_TERMS:
            msg = f"the when-term {term} has no fact yet ({PENDING_WHEN_TERMS[term]})"
            raise ValueError(msg)
        return {
            "has_aileron": self.has_aileron,
            "has_separate_flap_and_aileron": self.has_separate_flap_and_aileron,
            "has_vertical_tail": self.has_vertical_tail,
        }[term]


# Terms of the closed vocabulary whose fact is not implemented yet, with the ticket that brings it.
PENDING_WHEN_TERMS: Mapping[str, str] = {"has_horizontal_tail": "#1187"}
_AILERON_ROLES = frozenset({"aileron", "flaperon", "elevon"})
# A butterfly layout (D10) needs a flap and a distinct aileron or elevon; a flaperon is neither.
_BUTTERFLY_FLAP_ROLES = frozenset({"flap"})
_BUTTERFLY_AILERON_ROLES = frozenset({"aileron", "elevon"})
_RUDDER_ROLES = frozenset({"rudder", "ruddervator"})


def _roles(wing: Wing) -> list[str]:
    """The roles of a wing's trailing-edge devices, one per rib that carries one."""
    return [
        x_sec.trailing_edge_device.role
        for x_sec in wing.x_secs
        if x_sec.trailing_edge_device is not None
    ]


def _planform_area(wing: Wing) -> float:
    """Planform area of one stored half: mean chord times y-z segment span, summed (m^2).

    The span is measured in the y-z plane, so sweep does not count.
    """
    return sum(
        (a.chord + b.chord) / 2 * math.hypot(b.xyz_le[1] - a.xyz_le[1], b.xyz_le[2] - a.xyz_le[2])
        for a, b in zip(wing.x_secs, wing.x_secs[1:], strict=False)
    )


def _has_vertical_tail(wings: dict[str, Wing]) -> bool:
    """Tell whether another wing is a fin or V-tail behind the main wing's root chord.

    PROVISIONAL (ARCHITECTURE ch. 8.5, awaiting the maintainer's confirmation as D9). The main
    wing is the symmetric wing of the largest planform area. A vertical tail is another wing that
    is not symmetric (a fin) or carries a rudder or ruddervator device (a V-tail), and whose
    first rib lies at or behind the main wing's root trailing edge. Winglets are ribs of the main
    wing and a tailless centre fin overlaps the root chord, so neither counts.
    """
    ribbed = {name: wing for name, wing in wings.items() if wing.x_secs}
    symmetric = {name: wing for name, wing in ribbed.items() if wing.symmetric}
    if not symmetric:
        return False
    main_name = max(symmetric, key=lambda name: _planform_area(symmetric[name]))
    root = ribbed[main_name].x_secs[0]
    trailing_edge_x = root.xyz_le[0] + root.chord
    return any(
        (not wing.symmetric or _RUDDER_ROLES & set(_roles(wing)))
        and wing.x_secs[0].xyz_le[0] >= trailing_edge_x
        for name, wing in ribbed.items()
        if name != main_name
    )


def facts_from_geometry(airplane: AirplaneGeometry) -> WhenFacts:
    """Derive the ``when`` facts of a geometry (ch. 8.5).

    Roles come from ``trailing_edge_device.role`` only, never from a name or a control surface.
    A device is one rib of one wing.

    Args:
        airplane: The aircraft geometry.

    Returns:
        The facts; all false for an aircraft without wings.
    """
    wings = airplane.wings or {}
    devices = [
        ((name, index), x_sec.trailing_edge_device.role)
        for name, wing in wings.items()
        for index, x_sec in enumerate(wing.x_secs)
        if x_sec.trailing_edge_device is not None
    ]
    return WhenFacts(
        has_aileron=any(role in _AILERON_ROLES for _, role in devices),
        has_separate_flap_and_aileron=any(
            flap_role in _BUTTERFLY_FLAP_ROLES
            and aileron_role in _BUTTERFLY_AILERON_ROLES
            and flap != aileron
            for flap, flap_role in devices
            for aileron, aileron_role in devices
        ),
        has_vertical_tail=_has_vertical_tail(wings),
    )


def unmet_condition(
    node: Node, facts: WhenFacts, supplied: Collection[str]
) -> Reason | KernelError | None:
    """Check a node's ``when`` and ``given`` conditions (row 1 of the status order, ch. 8.13).

    A ``when`` term that has facts is checked first, then ``given``; a ``when`` term without a fact
    yet comes last, because an unmet ``given`` makes the application not exist whatever that fact
    would say.

    Args:
        node: The application's node.
        facts: The geometry facts of the aircraft.
        supplied: Slugs (bare or qualified) of the input and target values that were supplied.

    Returns:
        ``condition_not_met`` or ``not_given`` with a message naming the term or the missing
        slugs; a ``not_implemented`` error if the ``when`` term has no fact yet
        (:data:`PENDING_WHEN_TERMS`); or ``None`` if the application exists.
    """
    pending = node.when in PENDING_WHEN_TERMS
    if node.when is not None and not pending and not facts.holds(node.when):
        return Reason(
            code=ReasonCode.CONDITION_NOT_MET,
            message=f"The aircraft does not satisfy `{node.when}`.",
        )
    given = {qualify(slug) for slug in supplied}
    missing = [slug for slug in node.given if slug not in given]
    if missing:
        names = join_names([f"`{display_slug(slug)}`" for slug in missing])
        verb = "was" if len(missing) == 1 else "were"
        return Reason(code=ReasonCode.NOT_GIVEN, message=f"{names} {verb} not supplied.")
    if node.when is not None and pending:
        return KernelError(
            code=ErrorCategory.NOT_IMPLEMENTED.value,
            category=ErrorCategory.NOT_IMPLEMENTED,
            formula=node.id.formula,
            application=node.id.application,
            message=f"The condition `{node.when}` cannot be evaluated yet.",
            hint=f"Its fact is not implemented ({PENDING_WHEN_TERMS[node.when]}).",
        )
    return None
