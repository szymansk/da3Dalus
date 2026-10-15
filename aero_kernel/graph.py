"""The graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13).

Pure structure: which applications a request needs, in which order, which of them are independent,
which method worlds a quantity has. Nothing here evaluates a formula or calls a tool.

Identifiers inside the graph are the canon's qualified ``<namespace>:<slug>`` form. Errors and world
assignments speak the public bare slug.
"""

import logging
import math
from collections.abc import Collection, Sequence

from aero_kernel.canon.model import (
    DEFAULT_NAMESPACE,
    CanonModel,
    CostClass,
    Formula,
    Quantity,
    WhenTerm,
)
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.geometry import AirplaneGeometry, Wing
from aero_kernel.schema import Reason, ReasonCode
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = [
    "CanonGraph",
    "GraphModelError",
    "Node",
    "NodeId",
    "Produce",
    "Read",
    "Resolved",
    "qualify",
]

_FROZEN = ConfigDict(extra="forbid", frozen=True)


def qualify(slug: str) -> str:
    """Write a slug in its qualified form; a bare slug belongs to the default namespace."""
    return slug if ":" in slug else f"{DEFAULT_NAMESPACE}:{slug}"


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
        quantity: The quantity's canon entry.
        producer: The node whose application produces it.
    """

    model_config = _FROZEN

    slug: str
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


class Subtree(BaseModel):
    """The part of the graph one request needs (ch. 6 steps 2 and 3, K29).

    Attributes:
        requested: The requested quantities that resolved, each once, in request order.
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
        self._check_reads()

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

    def _check_reads(self) -> None:
        """Require every read quantity to be a supplied one or to have a producer."""
        for node in self._nodes.values():
            for read in node.reads:
                quantity = self._model.quantity(read.quantity)
                supplied = quantity is not None and quantity.role in ("input", "target")
                if not supplied and read.quantity not in self._producers:
                    msg = f"{read.quantity} is read by {_label(node.id)} but has no producer"
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

        Raises:
            GraphModelError: If the needed nodes contain a cycle, or a requested quantity has no
                producer.
        """
        requested: list[Resolved] = []
        errors: list[KernelError] = []
        for slug in quantities:
            resolved = self.resolve(slug)
            if isinstance(resolved, KernelError):
                errors.append(resolved)
            elif all(resolved.slug != other.slug for other in requested):
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

        Raises:
            GraphModelError: If the quantity is requestable but no application produces it.
        """
        qualified = qualify(slug)
        quantity = self._model.quantity(qualified)
        if quantity is None:
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
        producer = self._producers.get(qualified)
        if producer is None:
            msg = f"requested {qualified} has no producer"
            raise GraphModelError(msg)
        return Resolved(slug=qualified, quantity=quantity, producer=producer)


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
        has_separate_flap_and_aileron: A flap-acting and a distinct aileron-acting device exist.
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
        """
        return {
            "has_aileron": self.has_aileron,
            "has_separate_flap_and_aileron": self.has_separate_flap_and_aileron,
            "has_vertical_tail": self.has_vertical_tail,
        }[term]


_AILERON_ROLES = frozenset({"aileron", "flaperon", "elevon"})
_FLAP_ROLES = frozenset({"flap", "flaperon"})
_RUDDER_ROLES = frozenset({"rudder", "ruddervator"})


def _roles(wing: Wing) -> list[str]:
    """The roles of a wing's trailing-edge devices, one per rib that carries one."""
    return [
        x_sec.trailing_edge_device.role
        for x_sec in wing.x_secs
        if x_sec.trailing_edge_device is not None
    ]


def _planform_area(wing: Wing) -> float:
    """Planform area of one stored half: mean chord times segment length, summed (m^2)."""
    return sum(
        (a.chord + b.chord) / 2 * math.dist(a.xyz_le, b.xyz_le)
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
            flap_role in _FLAP_ROLES and aileron_role in _AILERON_ROLES and flap != aileron
            for flap, flap_role in devices
            for aileron, aileron_role in devices
        ),
        has_vertical_tail=_has_vertical_tail(wings),
    )


def unmet_condition(node: Node, facts: WhenFacts, supplied: Collection[str]) -> Reason | None:
    """Check a node's ``when`` and ``given`` conditions; ``when`` first.

    Args:
        node: The application's node.
        facts: The geometry facts of the aircraft.
        supplied: Slugs (bare or qualified) of the input and target values that were supplied.

    Returns:
        ``condition_not_met`` or ``not_given`` with a message naming the term or the missing
        slugs, or ``None`` if the application exists.
    """
    if node.when is not None and not facts.holds(node.when):
        return Reason(
            code=ReasonCode.CONDITION_NOT_MET,
            message=f"The aircraft does not satisfy `{node.when}`.",
        )
    given = {qualify(slug) for slug in supplied}
    missing = [slug for slug in node.given if slug not in given]
    if missing:
        names = ", ".join(f"`{slug.partition(':')[2]}`" for slug in missing)
        return Reason(code=ReasonCode.NOT_GIVEN, message=f"{names} was not supplied.")
    return None
