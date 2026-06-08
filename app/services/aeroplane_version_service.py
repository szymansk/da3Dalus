"""Version operations for the aircraft versioning system (gh-905).

All public functions follow the service-layer convention:
- Accept a ``db: Session`` as first argument.
- Do NOT call ``db.commit()`` — ``get_db()`` owns the commit boundary.
- Raise ``ServiceException`` subclasses for all domain errors.

Operations
----------
snapshot      — fork an immutable predecessor from the current head.
create_branch — clone a node into a new mutable branch head.
adopt_branch  — promote a branch to is_main, demote the old main.
restore       — create a new branch from an immutable snapshot.
discard_branch — delete a branch and its exclusive nodes (guarded).
compare       — return both nodes' metrics payloads (read-only).
list_tree     — return the full lineage graph for a root aeroplane.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.models.aeroplanemodel import AeroplaneModel, BranchModel
from app.services.aeroplane_clone_service import clone_aeroplane_subgraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ERR_NOT_FOUND = "Aeroplane not found"
_ERR_BRANCH_NOT_FOUND = "Branch not found"
_ERR_IMMUTABLE = "Cannot mutate an immutable snapshot node"


def _get_node(db: Session, node_id: int) -> AeroplaneModel:
    """Fetch an aeroplane node by integer PK; raise NotFoundError if absent."""
    node = db.query(AeroplaneModel).filter(AeroplaneModel.id == node_id).first()
    if node is None:
        raise NotFoundError(message=_ERR_NOT_FOUND, details={"id": node_id})
    return node


def _get_node_by_uuid(db: Session, uuid_str: str) -> AeroplaneModel:
    """Fetch an aeroplane node by UUID string; raise NotFoundError if absent."""
    node = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == uuid_str).first()
    if node is None:
        raise NotFoundError(message=_ERR_NOT_FOUND, details={"uuid": uuid_str})
    return node


def _get_branch(db: Session, branch_id: int) -> BranchModel:
    """Fetch a branch by PK; raise NotFoundError if absent."""
    branch = db.query(BranchModel).filter(BranchModel.id == branch_id).first()
    if branch is None:
        raise NotFoundError(message=_ERR_BRANCH_NOT_FOUND, details={"branch_id": branch_id})
    return branch


def _guard_immutable(node: AeroplaneModel) -> None:
    """Raise ValidationError if *node* is an immutable snapshot."""
    if node.is_immutable:
        raise ValidationError(
            message=_ERR_IMMUTABLE,
            details={"node_id": node.id, "is_immutable": True},
        )


def _metrics_payload(node: AeroplaneModel) -> dict[str, Any]:
    """Build a lightweight metrics snapshot from an aeroplane node.

    Returns ``assumption_computation_context`` plus key geometry/stability
    scalars that the Metrics Dashboard uses.  If the node has no context the
    dict is sparse but not empty.
    """
    payload: dict[str, Any] = {
        "id": node.id,
        "uuid": str(node.uuid),
        "name": node.name,
        "total_mass_kg": node.total_mass_kg,
    }

    # assumption_computation_context (the metrics source of truth)
    ctx = node.assumption_computation_context
    if ctx:
        payload["assumption_computation_context"] = ctx

    # Basic geometry summary
    payload["wing_count"] = len(node.wings or [])
    payload["fuselage_count"] = len(node.fuselages or [])

    # Stability summary (latest result)
    if node.stability_results:
        latest = node.stability_results[-1]
        payload["stability"] = {
            "static_margin_pct": latest.static_margin_pct,
            "is_statically_stable": latest.is_statically_stable,
            "neutral_point_x": latest.neutral_point_x,
            "mac": latest.mac,
        }

    return payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def snapshot(
    db: Session,
    node_id: int,
    label: str,
    note: str | None = None,
    provenance_message_id: int | None = None,
) -> AeroplaneModel:
    """Create an immutable snapshot of a branch head.

    The snapshot is inserted as the head's **predecessor** in the lineage:

        [old_predecessor] ← [snapshot (immutable)] ← [head (mutable, keeps editing)]

    The ``head`` node continues to be the editable node; the snapshot captures
    the state at this moment.

    Returns the newly created snapshot node.

    Raises
    ------
    NotFoundError
        If *node_id* does not exist.
    ValidationError
        If the node is already immutable (cannot snapshot an immutable node).
    """
    head = _get_node(db, node_id)
    _guard_immutable(head)

    # Resolve the lineage root: if the head IS the root its root_id may be NULL
    # or equal to its own id.  Either way the snapshot must carry the correct
    # root_id so it remains findable by list_tree.
    resolved_root_id = head.root_id if head.root_id is not None else head.id

    # Clone the current head into an immutable copy that becomes the predecessor.
    snapshot_node = clone_aeroplane_subgraph(
        db,
        head,
        immutable=True,
        branch_id=head.branch_id,
        predecessor_id=head.predecessor_id,  # inherits head's old predecessor
        root_id=resolved_root_id,
    )

    # Set version metadata on the snapshot.
    snapshot_node.version_label = label
    snapshot_node.version_note = note
    snapshot_node.provenance_message_id = provenance_message_id
    snapshot_node.created_by = "human"

    db.flush()  # ensure snapshot_node.id is populated

    # Wire the head to point to the snapshot as its new predecessor.
    head.predecessor_id = snapshot_node.id
    db.flush()

    logger.info(
        "snapshot: node %s → snapshot %s (label=%r)", head.id, snapshot_node.id, label
    )
    return snapshot_node


def create_branch(
    db: Session,
    from_node_id: int,
    name: str,
    created_by: str = "human",
) -> BranchModel:
    """Fork a new editable branch from *from_node_id*.

    Clones the node into a new mutable head, creates a ``BranchModel`` row,
    and returns the branch.

    Raises
    ------
    NotFoundError
        If *from_node_id* does not exist.
    """
    source = _get_node(db, from_node_id)

    # Determine the lineage root.
    root_id = source.root_id if source.root_id is not None else source.id

    # Clone into a mutable head (branch_id unknown yet — filled in below).
    new_head = clone_aeroplane_subgraph(
        db,
        source,
        immutable=False,
        branch_id=None,  # filled in after branch row exists
        predecessor_id=source.id,
        root_id=root_id,
    )
    new_head.created_by = created_by
    db.flush()  # obtain new_head.id

    # Create the branch row.
    branch = BranchModel(
        root_id=root_id,
        head_id=new_head.id,
        name=name,
        is_main=False,
        created_by=created_by,
    )
    db.add(branch)
    db.flush()  # obtain branch.id

    # Back-fill the branch_id on the new head.
    new_head.branch_id = branch.id
    db.flush()

    logger.info(
        "create_branch: source %s → new branch %s (head=%s, name=%r)",
        source.id,
        branch.id,
        new_head.id,
        name,
    )
    return branch


def adopt_branch(db: Session, branch_id: int) -> BranchModel:
    """Promote *branch* to ``is_main=True``, demoting the current main.

    The previous main branch is kept but ``is_main`` is set to False.

    Returns the newly promoted branch.

    Raises
    ------
    NotFoundError
        If *branch_id* does not exist.
    ConflictError
        If the branch is already the main branch.
    """
    branch = _get_branch(db, branch_id)

    if branch.is_main:
        raise ConflictError(
            message="Branch is already the main branch",
            details={"branch_id": branch_id},
        )

    # Demote the current main branch for this lineage root.
    current_main = (
        db.query(BranchModel)
        .filter(
            BranchModel.root_id == branch.root_id,
            BranchModel.is_main == True,  # noqa: E712
        )
        .first()
    )
    if current_main is not None:
        current_main.is_main = False
        db.flush()  # demote FIRST so the partial unique index never sees two is_main=True

    branch.is_main = True
    db.flush()

    logger.info(
        "adopt_branch: branch %s (name=%r) promoted to main; old main=%s",
        branch.id,
        branch.name,
        current_main.id if current_main else None,
    )
    return branch


def restore(
    db: Session,
    snapshot_node_id: int,
    name: str | None = None,
    created_by: str = "human",
) -> BranchModel:
    """Fork an editable branch from an immutable snapshot.

    Equivalent to ``create_branch(from_node=snapshot_node)``.  The branch name
    defaults to ``restore/<snapshot_label>`` if not supplied.

    Returns the new branch.

    Raises
    ------
    NotFoundError
        If *snapshot_node_id* does not exist.
    ValidationError
        If the target node is NOT immutable (restore is only meaningful from
        a frozen snapshot).
    """
    node = _get_node(db, snapshot_node_id)

    if not node.is_immutable:
        raise ValidationError(
            message="restore() requires an immutable snapshot node",
            details={"node_id": snapshot_node_id, "is_immutable": False},
        )

    branch_name = name or f"restore/{node.version_label or snapshot_node_id}"
    return create_branch(db, from_node_id=snapshot_node_id, name=branch_name, created_by=created_by)


def discard_branch(db: Session, branch_id: int) -> None:
    """Delete a branch and all nodes that belong exclusively to it.

    Guards:
    - Cannot discard ``is_main`` branch.
    - Cannot discard the only branch of a lineage root.

    Raises
    ------
    NotFoundError
        If *branch_id* does not exist.
    ConflictError
        If the branch is ``is_main`` or it's the only branch.
    """
    branch = _get_branch(db, branch_id)

    if branch.is_main:
        raise ConflictError(
            message="Cannot discard the main branch",
            details={"branch_id": branch_id},
        )

    # Count sibling branches for this lineage root.
    sibling_count = (
        db.query(BranchModel)
        .filter(BranchModel.root_id == branch.root_id)
        .count()
    )
    if sibling_count <= 1:
        raise ConflictError(
            message="Cannot discard the only branch of a lineage root",
            details={"branch_id": branch_id, "root_id": branch.root_id},
        )

    # Collect all aeroplane nodes belonging to this branch.
    # We delete the head plus any immutable snapshot nodes whose branch_id
    # matches this branch.
    nodes_to_delete = (
        db.query(AeroplaneModel)
        .filter(AeroplaneModel.branch_id == branch_id)
        .all()
    )

    # Clear predecessor links that reference any of the nodes we're about to
    # delete, so SQLite/PostgreSQL FK constraints don't block the deletes.
    # (The predecessor_id FK is deferred / use_alter, but SQLite doesn't support
    # deferrable FKs, so we null them out explicitly.)
    node_ids = {n.id for n in nodes_to_delete}
    if node_ids:
        db.query(AeroplaneModel).filter(
            AeroplaneModel.predecessor_id.in_(node_ids)
        ).update({"predecessor_id": None}, synchronize_session="fetch")

    # Delete the branch row FIRST (before the aeroplane nodes) so that the
    # branches.head_id NOT-NULL constraint is not violated when SQLAlchemy
    # tries to null the FK via the relationship on the aeroplane row.
    db.delete(branch)
    db.flush()

    # Delete aeroplane rows (cascade will handle owned subgraphs).
    for node in nodes_to_delete:
        db.delete(node)

    db.flush()

    logger.info(
        "discard_branch: branch %s deleted, %s node(s) removed",
        branch_id,
        len(nodes_to_delete),
    )


def compare(
    db: Session,
    node_a_id: int,
    node_b_id: int,
) -> tuple[AeroplaneModel, AeroplaneModel, dict, dict]:
    """Return both nodes with their metrics payloads.

    Returns (node_a, node_b, metrics_a, metrics_b) — read-only.

    Raises
    ------
    NotFoundError
        If either node does not exist.
    """
    node_a = _get_node(db, node_a_id)
    node_b = _get_node(db, node_b_id)
    return node_a, node_b, _metrics_payload(node_a), _metrics_payload(node_b)


def list_tree(
    db: Session,
    root_id: int,
) -> tuple[list[AeroplaneModel], list[BranchModel]]:
    """Return all nodes and branches for a lineage.

    Parameters
    ----------
    root_id:
        Integer PK of the lineage-root aeroplane.

    Returns
    -------
    (nodes, branches)

    Raises
    ------
    NotFoundError
        If the root node does not exist.
    """
    # Confirm the root exists.
    root = _get_node(db, root_id)

    # Nodes: the root itself plus all nodes that share the same root_id.
    nodes = (
        db.query(AeroplaneModel)
        .filter(
            (AeroplaneModel.id == root_id)
            | (AeroplaneModel.root_id == root_id)
        )
        .order_by(AeroplaneModel.id)
        .all()
    )

    branches = (
        db.query(BranchModel)
        .filter(BranchModel.root_id == root_id)
        .order_by(BranchModel.id)
        .all()
    )

    return nodes, branches


def list_aeroplanes_heads_only(db: Session) -> list[AeroplaneModel]:
    """Return only branch-head aeroplane nodes (``heads_only=True`` mode).

    Queries the branches table for all head_ids and returns those aeroplane
    rows, ordered by name.  Legacy aeroplanes (``branch_id IS NULL``) are
    also returned — they are pre-versioning rows and always visible.
    """
    from sqlalchemy import select

    head_ids_subquery = select(BranchModel.head_id).scalar_subquery()

    return (
        db.query(AeroplaneModel)
        .filter(
            (AeroplaneModel.branch_id == None)  # noqa: E711 — legacy rows
            | (AeroplaneModel.id.in_(head_ids_subquery))
        )
        .order_by(AeroplaneModel.name)
        .all()
    )
