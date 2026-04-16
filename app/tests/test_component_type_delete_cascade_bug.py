"""Reproduction test for the 2026-04-16 delete-cascades-to-everything bug.

User report: clicking Delete on a user-created type with id=11 left the
DB with "almost all" types gone (just one garbage entry remained).

Our current service code has `db.delete(row)` + `db.commit()` which
MUST only affect one row. This test proves that invariant.

If the test ever fails, someone re-introduced a bug that wipes unrelated
rows (cascade, missing WHERE clause, etc).
"""
from __future__ import annotations


class TestDeleteDoesNotCascade:

    def test_deleting_one_user_type_leaves_all_others_intact(self, client_and_db):
        client, _ = client_and_db

        # Baseline: 9 seeded types
        before = client.get("/component-types").json()
        seeded_ids = {t["id"] for t in before}
        assert len(seeded_ids) == 9

        # Create two user types
        ut1 = client.post("/component-types", json={
            "name": "u1", "label": "U1", "schema": [],
        }).json()
        ut2 = client.post("/component-types", json={
            "name": "u2_garbage", "label": "U2 Garbage", "schema": [],
        }).json()

        mid = client.get("/component-types").json()
        assert len(mid) == 11

        # Delete the second user type
        res = client.delete(f"/component-types/{ut2['id']}")
        assert res.status_code == 204

        # Everything else must still be there
        after = client.get("/component-types").json()
        remaining_ids = {t["id"] for t in after}

        assert len(after) == 10, (
            f"Expected 10 types after deleting one, got {len(after)}. "
            f"Remaining: {[t['name'] for t in after]}"
        )
        assert ut1["id"] in remaining_ids
        assert seeded_ids.issubset(remaining_ids), (
            f"Seeded types disappeared! "
            f"Missing: {seeded_ids - remaining_ids}"
        )

    def test_deleting_user_type_with_referenced_components_is_rejected(self, client_and_db):
        """Safety net: if a user type has components referencing it, the
        backend must refuse deletion with 409. No silent data loss."""
        client, _ = client_and_db

        ut = client.post("/component-types", json={
            "name": "ref_target", "label": "Ref Target", "schema": [],
        }).json()
        # Create a component referencing it
        client.post("/components", json={
            "name": "c1", "component_type": "ref_target", "specs": {},
        })

        before_count = len(client.get("/component-types").json())
        res = client.delete(f"/component-types/{ut['id']}")
        assert res.status_code == 409

        after_count = len(client.get("/component-types").json())
        assert after_count == before_count  # nothing changed

    def test_deleting_seeded_type_is_rejected(self, client_and_db):
        client, _ = client_and_db
        seeded = client.get("/component-types").json()
        material = next(t for t in seeded if t["name"] == "material")

        before_count = len(client.get("/component-types").json())
        res = client.delete(f"/component-types/{material['id']}")
        assert res.status_code == 409

        after_count = len(client.get("/component-types").json())
        assert after_count == before_count
