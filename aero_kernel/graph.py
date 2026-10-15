"""The graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13).

Pure structure: which applications a request needs, in which order, which of them are independent,
which method worlds a quantity has. Nothing here evaluates a formula or calls a tool.

Identifiers inside the graph are the canon's qualified ``<namespace>:<slug>`` form. Errors and world
assignments speak the public bare slug.
"""

import logging

from aero_kernel.canon.model import (
    DEFAULT_NAMESPACE,
    CanonModel,
    CostClass,
    Formula,
    Quantity,
    WhenTerm,
)
from aero_kernel.errors import ErrorCategory, KernelError
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
