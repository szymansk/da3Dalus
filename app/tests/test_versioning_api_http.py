"""HTTP-level integration tests for the versioning API.

The service-layer E2E (test_versioning_e2e_migrated) does not exercise FastAPI
routing or response serialization. This caught a real bug (gh-914): the static
GET /aeroplanes/compare was shadowed by the dynamic GET /aeroplanes/{aeroplane_id}
(UUID), so 'compare' was parsed as a UUID → 422. These tests hit the real app
via TestClient so routing/serialization collisions are caught.
"""
from __future__ import annotations

from app.services import aeroplane_service
from app.services import aeroplane_version_service as vs


def _seed_two_nodes(SessionLocal):
    """Create an aeroplane + a branch head → two distinct integer node ids."""
    db = SessionLocal()
    try:
        ap = aeroplane_service.create_aeroplane(db, "HTTP-Cmp")
        db.commit()
        db.refresh(ap)
        br = vs.create_branch(db, ap.id, "variant")
        db.commit()
        db.refresh(br)
        return ap.id, ap.root_id, br.head_id
    finally:
        db.close()


def test_compare_route_not_shadowed_by_aeroplane_id(client_and_db):
    """GET /aeroplanes/compare must reach the compare handler, not be parsed as a UUID."""
    client, SessionLocal = client_and_db
    a_id, _root_id, b_id = _seed_two_nodes(SessionLocal)

    resp = client.get("/aeroplanes/compare", params={"a": a_id, "b": b_id})

    assert resp.status_code == 200, resp.text
    assert "uuid_parsing" not in resp.text  # regression guard for gh-914
    body = resp.json()
    assert "metrics_a" in body and "metrics_b" in body


def test_lineage_tree_over_http(client_and_db):
    client, SessionLocal = client_and_db
    _a, root_id, _b = _seed_two_nodes(SessionLocal)

    resp = client.get(f"/lineages/{root_id}/tree")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "nodes" in body and "branches" in body
    assert len(body["nodes"]) >= 2


def test_snapshot_and_branch_over_http(client_and_db):
    """POST snapshot + branch exercise routing + VersionNode/BranchOut serialization."""
    client, SessionLocal = client_and_db
    a_id, _root_id, _b = _seed_two_nodes(SessionLocal)

    snap = client.post(f"/aeroplanes/{a_id}/snapshot", json={"label": "http-snap", "note": "via http"})
    assert snap.status_code in (200, 201), snap.text

    branch = client.post(f"/aeroplanes/{a_id}/branch", json={"name": "http-branch"})
    assert branch.status_code in (200, 201), branch.text
    assert branch.json().get("name") == "http-branch"


def _seed_branch(SessionLocal):
    """Create an aeroplane with main branch and return (branch_id, aeroplane_id)."""
    from app.models.aeroplanemodel import BranchModel
    db = SessionLocal()
    try:
        ap = aeroplane_service.create_aeroplane(db, "Rename-Test")
        db.commit()
        db.refresh(ap)
        br = db.query(BranchModel).filter(BranchModel.head_id == ap.id).first()
        return br.id, ap.id
    finally:
        db.close()


def _seed_aeroplane_with_two_branches(SessionLocal):
    """Create an aeroplane with main branch + a side branch; return side_branch_id."""
    db = SessionLocal()
    try:
        ap = aeroplane_service.create_aeroplane(db, "TwoBranch-Test")
        db.commit()
        db.refresh(ap)
        side = vs.create_branch(db, ap.id, "original-side")
        db.commit()
        db.refresh(side)
        return side.id
    finally:
        db.close()


def test_rename_branch_returns_200_with_updated_name(client_and_db):
    """PATCH /branches/{id} with a valid name returns 200 and the renamed branch."""
    client, SessionLocal = client_and_db
    branch_id, _ap_id = _seed_branch(SessionLocal)

    resp = client.patch(f"/branches/{branch_id}", json={"name": "renamed-main"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "renamed-main"
    assert body["id"] == branch_id


def test_rename_branch_unknown_id_returns_404(client_and_db):
    """PATCH /branches/{id} for a nonexistent branch returns 404."""
    client, _ = client_and_db

    resp = client.patch("/branches/999999", json={"name": "ghost"})
    assert resp.status_code == 404, resp.text


def test_rename_branch_duplicate_name_returns_409(client_and_db):
    """PATCH /branches/{id} to a name already used by a sibling branch returns 409."""
    client, SessionLocal = client_and_db
    side_branch_id = _seed_aeroplane_with_two_branches(SessionLocal)

    # Try to rename the side branch to "main" (which the main branch already has).
    resp = client.patch(f"/branches/{side_branch_id}", json={"name": "main"})
    assert resp.status_code == 409, resp.text
