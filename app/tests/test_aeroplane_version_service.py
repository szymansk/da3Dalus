"""Tests for aeroplane_version_service (gh-905).

All tests use a throwaway in-memory SQLite database — the user's real database
is NEVER touched.

Scenarios covered:
1. snapshot: creates immutable predecessor, head keeps editing.
2. create_branch: head is mutable; branch row exists; predecessor points to source.
3. adopt_branch: flips is_main; old main demoted.
4. discard_branch: guarded (main / only branch); removes nodes + branch.
5. restore: forks an editable branch from a frozen snapshot.
6. heads_only: list_aeroplanes_heads_only returns only heads + legacy rows.
7. Mutation on immutable node is rejected.
8. compare: returns both nodes with metrics payloads.
9. list_tree: returns correct nodes and branches for a lineage.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel, BranchModel
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.aeroplane_version_service import (
    adopt_branch,
    compare,
    create_branch,
    discard_branch,
    list_aeroplanes_heads_only,
    list_tree,
    restore,
    snapshot,
)

# Import all models so Base.metadata is complete for create_all
import app.models.analysismodels  # noqa: F401
import app.models.avl_geometry_file  # noqa: F401
import app.models.component  # noqa: F401
import app.models.component_type  # noqa: F401
import app.models.construction_part  # noqa: F401
import app.models.construction_plan  # noqa: F401
import app.models.flight_envelope_model  # noqa: F401
import app.models.flightprofilemodel  # noqa: F401
import app.models.mission_preset  # noqa: F401
import app.models.tessellation_cache  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=engine)


def _make_root(db: Session, name: str = "plane") -> tuple[AeroplaneModel, BranchModel]:
    """Create a minimal aeroplane + main branch (simulates the #903 backfill)."""
    node = AeroplaneModel(
        uuid=uuid.uuid4(),
        name=name,
        is_immutable=False,
    )
    db.add(node)
    db.flush()

    # Set root_id to itself (root of a fresh lineage)
    node.root_id = node.id
    db.flush()

    branch = BranchModel(
        root_id=node.id,
        head_id=node.id,
        name="main",
        is_main=True,
        created_by="human",
    )
    db.add(branch)
    db.flush()

    node.branch_id = branch.id
    db.flush()

    db.commit()
    return node, branch


# ---------------------------------------------------------------------------
# 1. snapshot
# ---------------------------------------------------------------------------


def test_snapshot_creates_immutable_predecessor(db: Session):
    head, branch = _make_root(db, "snap-test")

    snap = snapshot(db, head.id, label="v1", note="first save")
    db.commit()

    # The snapshot is immutable and has the correct label.
    assert snap.is_immutable is True
    assert snap.version_label == "v1"
    assert snap.version_note == "first save"

    # The snapshot's predecessor is the head's OLD predecessor (None here).
    assert snap.predecessor_id is None

    # The head now points to the snapshot as its predecessor.
    db.refresh(head)
    assert head.predecessor_id == snap.id
    assert head.is_immutable is False


def test_snapshot_on_immutable_raises(db: Session):
    head, branch = _make_root(db)
    # First snapshot
    snap = snapshot(db, head.id, label="v1")
    db.commit()

    # Trying to snapshot the immutable node should fail.
    with pytest.raises(ValidationError, match="immutable"):
        snapshot(db, snap.id, label="v2")


def test_snapshot_not_found_raises(db: Session):
    with pytest.raises(NotFoundError):
        snapshot(db, 99999, label="nope")


# ---------------------------------------------------------------------------
# 2. create_branch
# ---------------------------------------------------------------------------


def test_create_branch_produces_mutable_head(db: Session):
    source, _main_branch = _make_root(db, "branch-test")

    branch = create_branch(db, source.id, name="experiment", created_by="human")
    db.commit()

    assert branch.name == "experiment"
    assert branch.is_main is False
    assert branch.root_id == source.root_id

    # The new head is mutable.
    new_head = db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
    assert new_head is not None
    assert new_head.is_immutable is False
    assert new_head.predecessor_id == source.id
    assert new_head.branch_id == branch.id


def test_create_branch_not_found_raises(db: Session):
    with pytest.raises(NotFoundError):
        create_branch(db, 99999, name="nope")


# ---------------------------------------------------------------------------
# 3. adopt_branch
# ---------------------------------------------------------------------------


def test_adopt_branch_flips_is_main(db: Session):
    root, main_branch = _make_root(db, "adopt-test")

    # Create a side branch.
    side_branch = create_branch(db, root.id, name="side", created_by="human")
    db.commit()

    assert side_branch.is_main is False
    assert main_branch.is_main is True

    # Adopt the side branch.
    promoted = adopt_branch(db, side_branch.id)
    db.commit()

    db.refresh(main_branch)
    db.refresh(side_branch)

    assert promoted.is_main is True
    assert side_branch.is_main is True
    assert main_branch.is_main is False  # demoted


def test_adopt_already_main_raises(db: Session):
    root, main_branch = _make_root(db)

    with pytest.raises(ConflictError, match="already the main"):
        adopt_branch(db, main_branch.id)


def test_adopt_branch_not_found_raises(db: Session):
    with pytest.raises(NotFoundError):
        adopt_branch(db, 99999)


# ---------------------------------------------------------------------------
# 4. discard_branch
# ---------------------------------------------------------------------------


def test_discard_branch_removes_nodes_and_branch(db: Session):
    root, main_branch = _make_root(db, "discard-test")

    side_branch = create_branch(db, root.id, name="side")
    db.commit()

    side_head_id = side_branch.id
    side_node_id = side_branch.head_id

    discard_branch(db, side_branch.id)
    db.commit()

    # Branch row is gone.
    assert db.query(BranchModel).filter(BranchModel.id == side_head_id).first() is None
    # The side head aeroplane node is gone.
    assert db.query(AeroplaneModel).filter(AeroplaneModel.id == side_node_id).first() is None
    # The main root is intact.
    assert db.query(AeroplaneModel).filter(AeroplaneModel.id == root.id).first() is not None


def test_discard_main_branch_raises(db: Session):
    root, main_branch = _make_root(db)

    with pytest.raises(ConflictError, match="Cannot discard the main"):
        discard_branch(db, main_branch.id)


def test_discard_only_branch_raises(db: Session):
    """Even a non-main branch cannot be discarded if it's the only one."""
    root, main_branch = _make_root(db)
    # Demote main artificially so we have a single non-main branch:
    # but the guard still catches it because only 1 branch exists.
    main_branch.is_main = False
    db.flush()
    db.commit()

    with pytest.raises(ConflictError, match="only branch"):
        discard_branch(db, main_branch.id)


def test_discard_branch_not_found_raises(db: Session):
    with pytest.raises(NotFoundError):
        discard_branch(db, 99999)


# ---------------------------------------------------------------------------
# 5. restore
# ---------------------------------------------------------------------------


def test_restore_forks_from_snapshot(db: Session):
    head, branch = _make_root(db, "restore-test")

    # Create a snapshot first.
    snap = snapshot(db, head.id, label="before-change")
    db.commit()

    # Restore from the snapshot.
    restore_branch = restore(db, snap.id, name="restored")
    db.commit()

    assert restore_branch.name == "restored"
    restored_head = db.query(AeroplaneModel).filter(
        AeroplaneModel.id == restore_branch.head_id
    ).first()
    assert restored_head is not None
    assert restored_head.is_immutable is False
    assert restored_head.predecessor_id == snap.id


def test_restore_from_mutable_raises(db: Session):
    head, branch = _make_root(db)

    with pytest.raises(ValidationError, match="immutable"):
        restore(db, head.id)


# ---------------------------------------------------------------------------
# 6. heads_only
# ---------------------------------------------------------------------------


def test_list_aeroplanes_heads_only_filters_snapshots(db: Session):
    # Three aeroplanes: one legacy (no branch), one head, one snapshot.
    legacy = AeroplaneModel(uuid=uuid.uuid4(), name="legacy", is_immutable=False)
    db.add(legacy)
    db.flush()
    legacy.root_id = legacy.id
    db.flush()

    # A versioned aeroplane with main branch.
    root, main_branch = _make_root(db, "versioned")

    # Snapshot — creates an immutable node that should NOT appear in heads_only.
    snap = snapshot(db, root.id, label="v1")
    db.commit()

    results = list_aeroplanes_heads_only(db)
    result_ids = {r.id for r in results}

    # Legacy + root (head) must be in results; snapshot must NOT.
    assert legacy.id in result_ids
    assert root.id in result_ids
    assert snap.id not in result_ids


def test_list_aeroplanes_heads_only_returns_heads_from_all_branches(db: Session):
    root, main_branch = _make_root(db, "multi-branch")

    side_branch = create_branch(db, root.id, name="side")
    db.commit()

    results = list_aeroplanes_heads_only(db)
    result_ids = {r.id for r in results}

    # Both the main head (root) and the side branch head should appear.
    assert root.id in result_ids
    assert side_branch.head_id in result_ids


# ---------------------------------------------------------------------------
# 7. Mutation on immutable rejected
# ---------------------------------------------------------------------------


def test_snapshot_immutable_node_rejected(db: Session):
    head, branch = _make_root(db)
    snap = snapshot(db, head.id, label="v1")
    db.commit()

    with pytest.raises(ValidationError):
        snapshot(db, snap.id, label="v2")


# ---------------------------------------------------------------------------
# 8. compare
# ---------------------------------------------------------------------------


def test_compare_returns_both_nodes_and_metrics(db: Session):
    root_a, _ = _make_root(db, "alpha")
    root_b, _ = _make_root(db, "beta")
    db.commit()

    node_a, node_b, metrics_a, metrics_b = compare(db, root_a.id, root_b.id)

    assert node_a.id == root_a.id
    assert node_b.id == root_b.id
    assert metrics_a["name"] == "alpha"
    assert metrics_b["name"] == "beta"
    # Both metrics include the id and uuid keys.
    assert "id" in metrics_a
    assert "uuid" in metrics_b


def test_compare_not_found_raises(db: Session):
    root_a, _ = _make_root(db, "only")
    db.commit()

    with pytest.raises(NotFoundError):
        compare(db, root_a.id, 99999)


# ---------------------------------------------------------------------------
# 9. list_tree
# ---------------------------------------------------------------------------


def test_list_tree_returns_nodes_and_branches(db: Session):
    root, main_branch = _make_root(db, "tree-test")

    # Add a snapshot and a side branch.
    snap = snapshot(db, root.id, label="v1")
    db.commit()
    side_branch = create_branch(db, root.id, name="side")
    db.commit()

    nodes, branches = list_tree(db, root.id)

    node_ids = {n.id for n in nodes}
    branch_ids = {b.id for b in branches}

    assert root.id in node_ids
    assert snap.id in node_ids
    assert side_branch.head_id in node_ids
    assert main_branch.id in branch_ids
    assert side_branch.id in branch_ids


def test_list_tree_not_found_raises(db: Session):
    with pytest.raises(NotFoundError):
        list_tree(db, 99999)
