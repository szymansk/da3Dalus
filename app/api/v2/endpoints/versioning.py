"""FastAPI endpoints for the aircraft versioning system (gh-905).

Routes
------
POST  /aeroplanes/{id}/snapshot          snapshot current head
POST  /aeroplanes/{id}/branch            create a new branch from a node
POST  /branches/{id}/adopt               promote branch to main
POST  /aeroplanes/{snapshot_id}/restore  fork editable head from a snapshot
DELETE /branches/{id}                    discard branch (guarded)
GET   /lineages/{root_id}/tree           version graph for a lineage
GET   /aeroplanes/compare?a=&b=          two-node metrics comparison
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.versioning import (
    BranchOut,
    BranchRequest,
    CompareOut,
    SnapshotRequest,
    TreeOut,
    TreeNodeOut,
    VersionNode,
)
from app.services import aeroplane_version_service as svc
from app.models.aeroplanemodel import AeroplaneModel, BranchModel

logger = logging.getLogger(__name__)

router = APIRouter()

_TAGS_VERSIONING = ["versioning"]


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


def _node_to_schema(node: AeroplaneModel) -> VersionNode:
    return VersionNode(
        id=node.id,
        uuid=str(node.uuid),
        name=node.name,
        branch_id=node.branch_id,
        predecessor_id=node.predecessor_id,
        root_id=node.root_id,
        is_immutable=node.is_immutable,
        version_label=node.version_label,
        version_note=node.version_note,
        created_by=node.created_by,
        provenance_message_id=node.provenance_message_id,
        preview_png=node.preview_png,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _branch_to_schema(branch: BranchModel) -> BranchOut:
    return BranchOut(
        id=branch.id,
        root_id=branch.root_id,
        head_id=branch.head_id,
        name=branch.name,
        is_main=branch.is_main,
        created_by=branch.created_by,
        created_at=branch.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/aeroplanes/{aeroplane_id}/snapshot",
    status_code=status.HTTP_201_CREATED,
    tags=_TAGS_VERSIONING,
    operation_id="snapshot_aeroplane",
    responses={
        404: {"description": "Aeroplane not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error — e.g. node is immutable"},
    },
)
async def snapshot_aeroplane(
    aeroplane_id: Annotated[int, Path(..., description="Integer PK of the aeroplane head node")],
    body: Annotated[SnapshotRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> VersionNode:
    """Create an immutable snapshot of the current head.

    The snapshot is inserted as the predecessor of *aeroplane_id*; the head
    continues to be the live editable node.
    """
    node = _call(
        svc.snapshot,
        db,
        aeroplane_id,
        body.label,
        body.note,
        body.provenance_message_id,
    )
    return _node_to_schema(node)


@router.post(
    "/aeroplanes/{aeroplane_id}/branch",
    status_code=status.HTTP_201_CREATED,
    tags=_TAGS_VERSIONING,
    operation_id="create_branch",
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Validation error"},
    },
)
async def create_branch(
    aeroplane_id: Annotated[int, Path(..., description="Integer PK of the source node")],
    body: Annotated[BranchRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> BranchOut:
    """Fork a new editable branch from a node (mutable head or immutable snapshot)."""
    branch = _call(svc.create_branch, db, aeroplane_id, body.name, body.created_by or "human")
    return _branch_to_schema(branch)


@router.post(
    "/branches/{branch_id}/adopt",
    status_code=status.HTTP_200_OK,
    tags=_TAGS_VERSIONING,
    operation_id="adopt_branch",
    responses={
        404: {"description": "Branch not found"},
        409: {"description": "Already the main branch"},
    },
)
async def adopt_branch(
    branch_id: Annotated[int, Path(..., description="Integer PK of the branch to promote")],
    db: Annotated[Session, Depends(get_db)],
) -> BranchOut:
    """Promote a branch to ``is_main=True``.

    The previous main branch is demoted (kept) automatically.
    """
    branch = _call(svc.adopt_branch, db, branch_id)
    return _branch_to_schema(branch)


@router.post(
    "/aeroplanes/{snapshot_id}/restore",
    status_code=status.HTTP_201_CREATED,
    tags=_TAGS_VERSIONING,
    operation_id="restore_snapshot",
    responses={
        404: {"description": "Snapshot node not found"},
        422: {"description": "Node is not an immutable snapshot"},
    },
)
async def restore_snapshot(
    snapshot_id: Annotated[int, Path(..., description="Integer PK of the immutable snapshot node")],
    body: Annotated[BranchRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> BranchOut:
    """Fork an editable branch from an immutable snapshot (undo / rollback).

    Creates a new mutable head from the frozen state of *snapshot_id*.
    """
    branch = _call(
        svc.restore,
        db,
        snapshot_id,
        body.name,
        body.created_by or "human",
    )
    return _branch_to_schema(branch)


@router.delete(
    "/branches/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=_TAGS_VERSIONING,
    operation_id="discard_branch",
    responses={
        404: {"description": "Branch not found"},
        409: {"description": "Cannot discard main or only branch"},
    },
)
async def discard_branch(
    branch_id: Annotated[int, Path(..., description="Integer PK of the branch to discard")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Discard a branch and all of its exclusively-owned aeroplane nodes.

    Guards: cannot discard the ``is_main`` branch or the only branch of a
    lineage root.
    """
    _call(svc.discard_branch, db, branch_id)


@router.get(
    "/lineages/{root_id}/tree",
    status_code=status.HTTP_200_OK,
    tags=_TAGS_VERSIONING,
    operation_id="get_lineage_tree",
    responses={
        404: {"description": "Root node not found"},
    },
)
async def get_lineage_tree(
    root_id: Annotated[int, Path(..., description="Integer PK of the lineage root aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> TreeOut:
    """Return the full version lineage graph (nodes + branches)."""
    nodes, branches = _call(svc.list_tree, db, root_id)

    # Determine which node ids are branch heads for the is_head flag.
    head_ids: set[int] = {b.head_id for b in branches}

    tree_nodes = [
        TreeNodeOut(
            id=n.id,
            uuid=str(n.uuid),
            name=n.name,
            branch_id=n.branch_id,
            predecessor_id=n.predecessor_id,
            root_id=n.root_id,
            is_immutable=n.is_immutable,
            is_head=(n.id in head_ids),
            version_label=n.version_label,
            version_note=n.version_note,
            created_by=n.created_by,
            created_at=n.created_at,
        )
        for n in nodes
    ]
    branch_outs = [_branch_to_schema(b) for b in branches]

    return TreeOut(root_id=root_id, nodes=tree_nodes, branches=branch_outs)


@router.get(
    "/aeroplanes/compare",
    status_code=status.HTTP_200_OK,
    tags=_TAGS_VERSIONING,
    operation_id="compare_aeroplane_nodes",
    responses={
        404: {"description": "One or both nodes not found"},
    },
)
async def compare_aeroplane_nodes(
    a: Annotated[int, Query(..., description="Integer PK of the first aeroplane node")],
    b: Annotated[int, Query(..., description="Integer PK of the second aeroplane node")],
    db: Annotated[Session, Depends(get_db)],
) -> CompareOut:
    """Return the metrics payloads for two aeroplane nodes side by side."""
    node_a, node_b, metrics_a, metrics_b = _call(svc.compare, db, a, b)
    return CompareOut(
        node_a=_node_to_schema(node_a),
        node_b=_node_to_schema(node_b),
        metrics_a=metrics_a,
        metrics_b=metrics_b,
    )
