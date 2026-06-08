"""End-to-end exercise of the versioning backend against a MIGRATED schema.

Runs against whatever SQLALCHEMY_DATABASE_URL points to (a throwaway DB that has
been `alembic upgrade head`-ed, so the partial unique index + all real
constraints are present — the layer where create_all unit tests miss bugs).
Exits non-zero on the first failure.
"""
from __future__ import annotations

import sys

from app.db.session import SessionLocal
from app.services import aeroplane_service
from app.services import aeroplane_version_service as vs
from app.models.aeroplanemodel import AeroplaneModel, BranchModel

ok = 0
fail = 0


def check(label: str, cond: bool, extra: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {extra}")


def main_branch_of(db, root_id: int) -> BranchModel:
    return (
        db.query(BranchModel)
        .filter(BranchModel.root_id == root_id, BranchModel.is_main.is_(True))
        .one()
    )


def count_main(db, root_id: int) -> int:
    return (
        db.query(BranchModel)
        .filter(BranchModel.root_id == root_id, BranchModel.is_main.is_(True))
        .count()
    )


db = SessionLocal()
try:
    # 1) create_aeroplane → must bootstrap a main branch + versioning columns
    ap = aeroplane_service.create_aeroplane(db, "E2E-Plane")
    db.commit()
    db.refresh(ap)
    root_id = ap.root_id
    check("create_aeroplane sets root_id=self", ap.root_id == ap.id, f"root_id={ap.root_id} id={ap.id}")
    check("create_aeroplane sets branch_id", ap.branch_id is not None)
    check("create_aeroplane node is mutable", not ap.is_immutable)
    mb = main_branch_of(db, root_id)
    check("create_aeroplane creates a main branch", mb.head_id == ap.id and mb.name == "main")
    check("exactly one main for root", count_main(db, root_id) == 1)
    heads = vs.list_aeroplanes_heads_only(db)
    check("new aeroplane is a head", any(h.id == ap.id for h in heads))

    # 2) snapshot → immutable predecessor, root_id set (gh-910), head unchanged
    snap = vs.snapshot(db, ap.id, "snap-1", "first snapshot")
    db.commit()
    db.refresh(snap)
    db.refresh(mb)
    check("snapshot is immutable", bool(snap.is_immutable))
    check("snapshot has root_id (gh-910)", snap.root_id == root_id, f"snap.root_id={snap.root_id}")
    check("snapshot NOT a head (heads_only excludes it)",
          all(h.id != snap.id for h in vs.list_aeroplanes_heads_only(db)))
    db.refresh(ap)
    check("branch head unchanged after snapshot", mb.head_id == ap.id)

    # 3) create_branch (variant) from the head
    br_variant = vs.create_branch(db, ap.id, "variant")
    db.commit()
    db.refresh(br_variant)
    variant_head_id = br_variant.head_id
    check("create_branch new mutable head (clone)", variant_head_id != ap.id)
    check("variant branch not main", not br_variant.is_main)
    check("variant head in heads", any(h.id == variant_head_id for h in vs.list_aeroplanes_heads_only(db)))

    # 4) adopt variant  ← gh-912 (must not violate the one-main partial index)
    try:
        vs.adopt_branch(db, br_variant.id)
        db.commit()
        adopt_ok = True
        err = ""
    except Exception as exc:  # noqa: BLE001
        adopt_ok = False
        err = repr(exc)
        db.rollback()
    check("adopt variant succeeds (no IntegrityError)", adopt_ok, err)
    check("exactly one main after adopt", count_main(db, root_id) == 1)
    if adopt_ok:
        db.refresh(br_variant)
        check("variant is now main", bool(br_variant.is_main))

    # 5) re-adopt original main (round trip)
    try:
        vs.adopt_branch(db, mb.id)
        db.commit()
        readopt_ok = True
        err = ""
    except Exception as exc:  # noqa: BLE001
        readopt_ok = False
        err = repr(exc)
        db.rollback()
    check("re-adopt original main succeeds (round trip)", readopt_ok, err)
    check("still exactly one main after round trip", count_main(db, root_id) == 1)

    # 6) restore from the snapshot
    br_restore = vs.restore(db, snap.id, "restored")
    db.commit()
    db.refresh(br_restore)
    check("restore creates a new branch from snapshot", br_restore.id not in (mb.id, br_variant.id))
    check("restore head is mutable clone", br_restore.head_id != snap.id)

    # 7) compare two nodes
    na, nb, ma, mbx = vs.compare(db, ap.id, variant_head_id)
    check("compare returns both nodes + metric dicts", na.id == ap.id and nb.id == variant_head_id
          and isinstance(ma, dict) and isinstance(mbx, dict))

    # 8) list_tree
    nodes, branches = vs.list_tree(db, root_id)
    check("list_tree returns the lineage nodes", len(nodes) >= 4, f"nodes={len(nodes)}")
    check("list_tree returns the branches", len(branches) >= 3, f"branches={len(branches)}")

    # 9) discard a non-main branch
    vs.discard_branch(db, br_variant.id)
    db.commit()
    check("discard non-main branch removed it",
          db.query(BranchModel).filter(BranchModel.id == br_variant.id).first() is None)

    # 10) discard guards: cannot discard main
    try:
        vs.discard_branch(db, mb.id)
        db.commit()
        guarded = False
    except Exception:  # noqa: BLE001
        db.rollback()
        guarded = True
    check("discard main is guarded (raises)", guarded)

    # 11) mutation guard: snapshot on an immutable node is rejected
    try:
        vs.snapshot(db, snap.id, "bad")
        db.commit()
        immut_guarded = False
    except Exception:  # noqa: BLE001
        db.rollback()
        immut_guarded = True
    check("snapshot on immutable node is guarded", immut_guarded)

finally:
    db.close()

print(f"\n=== E2E: {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
