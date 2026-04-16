"""Thorough end-to-end coverage for the component-types interface (gh#83).

Follows the 2026-04-16 "delete wiped almost everything" incident. Covers:

  * Row-count invariants: every mutation changes by exactly the expected delta.
  * DB-level verification: after each HTTP call we query the ORM directly to
    confirm the persisted state matches the response.
  * Safe edge cases: trailing slash, non-integer id, negative/zero id,
    missing body, malformed schema, duplicate name.
  * Round-trips: POST → GET → PUT → GET → DELETE → GET with count + content
    checks at each step.
  * Concurrent/rapid DELETE: firing DELETE for the same id twice must leave
    other rows untouched (idempotency-ish — second call returns 404).
"""
from __future__ import annotations

from app.models.component_type import ComponentTypeModel


def _count_types_in_db(session_factory) -> int:
    s = session_factory()
    try:
        return s.query(ComponentTypeModel).count()
    finally:
        s.close()


def _names_in_db(session_factory) -> set[str]:
    s = session_factory()
    try:
        return {row.name for row in s.query(ComponentTypeModel).all()}
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Row-count invariants — the core of the data-loss regression guard
# --------------------------------------------------------------------------- #

class TestRowCountInvariants:
    """Every mutation changes the row count by exactly the expected delta."""

    def test_seed_produces_exactly_9_rows(self, client_and_db):
        _, sf = client_and_db
        assert _count_types_in_db(sf) == 9

    def test_create_adds_exactly_one_row(self, client_and_db):
        client, sf = client_and_db
        before = _count_types_in_db(sf)
        client.post("/component-types", json={
            "name": "u1", "label": "U1", "schema": [],
        })
        assert _count_types_in_db(sf) == before + 1

    def test_update_does_not_change_row_count(self, client_and_db):
        client, sf = client_and_db
        body = client.get("/component-types").json()
        servo = next(t for t in body if t["name"] == "servo")

        before = _count_types_in_db(sf)
        client.put(f"/component-types/{servo['id']}", json={
            "name": servo["name"], "label": "Servo (edited)",
            "description": None, "schema": servo["schema"],
        })
        assert _count_types_in_db(sf) == before

    def test_delete_removes_exactly_one_row(self, client_and_db):
        client, sf = client_and_db
        created = client.post("/component-types", json={
            "name": "doomed", "label": "Doomed", "schema": [],
        }).json()
        before = _count_types_in_db(sf)
        res = client.delete(f"/component-types/{created['id']}")
        assert res.status_code == 204
        assert _count_types_in_db(sf) == before - 1

    def test_rejected_delete_does_not_change_row_count(self, client_and_db):
        """Seeded DELETE, referenced DELETE, and missing DELETE must all be no-ops."""
        client, sf = client_and_db
        before_count = _count_types_in_db(sf)
        before_names = _names_in_db(sf)

        body = client.get("/component-types").json()
        material = next(t for t in body if t["name"] == "material")

        # Seeded → 409, no change
        client.delete(f"/component-types/{material['id']}")
        # Missing → 404, no change
        client.delete("/component-types/99999")
        # Create a ref'd type, try to delete, expect 409
        ref_target = client.post("/component-types", json={
            "name": "ref_target", "label": "RefT", "schema": [],
        }).json()
        client.post("/components", json={
            "name": "c1", "component_type": "ref_target", "specs": {},
        })
        client.delete(f"/component-types/{ref_target['id']}")

        assert _count_types_in_db(sf) == before_count + 1  # only ref_target added
        assert before_names.issubset(_names_in_db(sf))


# --------------------------------------------------------------------------- #
# Full lifecycle round-trip
# --------------------------------------------------------------------------- #

class TestLifecycleRoundTrip:

    def test_create_get_update_get_delete_get_roundtrip(self, client_and_db):
        client, sf = client_and_db

        # CREATE
        created = client.post("/component-types", json={
            "name": "rt_type", "label": "Round-Trip", "description": "x",
            "schema": [
                {"name": "foo", "label": "Foo", "type": "number", "min": 0, "max": 10},
            ],
        }).json()
        assert created["deletable"] is True
        assert created["schema"][0]["name"] == "foo"

        # GET by id
        got = client.get(f"/component-types/{created['id']}").json()
        assert got == created

        # UPDATE (schema change)
        updated_payload = {
            "name": created["name"], "label": "Round-Trip v2",
            "description": "changed",
            "schema": [
                {"name": "foo", "label": "Foo", "type": "number", "min": 0, "max": 10},
                {"name": "bar", "label": "Bar", "type": "string"},
            ],
        }
        put_res = client.put(f"/component-types/{created['id']}", json=updated_payload)
        assert put_res.status_code == 200
        assert put_res.json()["label"] == "Round-Trip v2"
        assert len(put_res.json()["schema"]) == 2

        # GET after PUT
        re_got = client.get(f"/component-types/{created['id']}").json()
        assert re_got["label"] == "Round-Trip v2"
        assert len(re_got["schema"]) == 2

        # DELETE
        del_res = client.delete(f"/component-types/{created['id']}")
        assert del_res.status_code == 204

        # GET after DELETE → 404
        assert client.get(f"/component-types/{created['id']}").status_code == 404

        # DB state: 9 seeded types, user type gone
        assert _count_types_in_db(sf) == 9


# --------------------------------------------------------------------------- #
# Edge cases around the path / body
# --------------------------------------------------------------------------- #

class TestEdgeCases:

    def test_delete_with_trailing_slash_is_method_not_allowed_or_redirect(self, client_and_db):
        client, sf = client_and_db
        before = _count_types_in_db(sf)
        # Trailing slash on the list URL (/component-types/) must NOT match
        # the DELETE route — which is /component-types/{id}.
        res = client.delete("/component-types/", follow_redirects=False)
        assert res.status_code in (405, 307)
        if res.status_code == 307:
            # Even if redirected, the redirect target must not accept DELETE.
            res2 = client.delete(res.headers["location"])
            assert res2.status_code == 405
        assert _count_types_in_db(sf) == before

    def test_delete_with_non_integer_id_is_422(self, client_and_db):
        client, sf = client_and_db
        before = _count_types_in_db(sf)
        res = client.delete("/component-types/abc")
        assert res.status_code == 422
        assert _count_types_in_db(sf) == before

    def test_delete_with_zero_or_negative_id_is_404(self, client_and_db):
        client, sf = client_and_db
        before = _count_types_in_db(sf)
        assert client.delete("/component-types/0").status_code == 404
        assert client.delete("/component-types/-1").status_code == 404
        assert _count_types_in_db(sf) == before

    def test_double_delete_second_returns_404_without_side_effects(self, client_and_db):
        client, sf = client_and_db
        created = client.post("/component-types", json={
            "name": "once", "label": "Once", "schema": [],
        }).json()
        first = client.delete(f"/component-types/{created['id']}")
        assert first.status_code == 204

        before = _count_types_in_db(sf)
        second = client.delete(f"/component-types/{created['id']}")
        assert second.status_code == 404
        assert _count_types_in_db(sf) == before

    def test_create_with_duplicate_name_is_rejected_and_doesnt_touch_existing(self, client_and_db):
        client, sf = client_and_db
        before_names = _names_in_db(sf)
        res = client.post("/component-types", json={
            "name": "material", "label": "Dup", "schema": [],
        })
        assert res.status_code == 409
        assert _names_in_db(sf) == before_names


# --------------------------------------------------------------------------- #
# Concurrent requests — verify no cross-contamination
# --------------------------------------------------------------------------- #

class TestMultipleMutations:

    def test_sequential_create_delete_pairs_leave_count_stable(self, client_and_db):
        client, sf = client_and_db
        baseline = _count_types_in_db(sf)
        for i in range(5):
            created = client.post("/component-types", json={
                "name": f"temp_{i}", "label": f"Temp {i}", "schema": [],
            }).json()
            assert _count_types_in_db(sf) == baseline + 1
            res = client.delete(f"/component-types/{created['id']}")
            assert res.status_code == 204
            assert _count_types_in_db(sf) == baseline

    def test_create_many_delete_one_leaves_others(self, client_and_db):
        client, sf = client_and_db
        created_ids = []
        for i in range(5):
            r = client.post("/component-types", json={
                "name": f"keep_{i}", "label": f"Keep {i}", "schema": [],
            })
            assert r.status_code == 201, r.text
            created_ids.append(r.json()["id"])

        before = _count_types_in_db(sf)
        assert before == 9 + 5

        # Delete just one
        res = client.delete(f"/component-types/{created_ids[2]}")
        assert res.status_code == 204

        # Others all still there
        all_types = client.get("/component-types").json()
        remaining_ids = {t["id"] for t in all_types}
        assert created_ids[0] in remaining_ids
        assert created_ids[1] in remaining_ids
        assert created_ids[2] not in remaining_ids  # the one we deleted
        assert created_ids[3] in remaining_ids
        assert created_ids[4] in remaining_ids
        assert _count_types_in_db(sf) == before - 1


# --------------------------------------------------------------------------- #
# Schema integrity after repair migration
# --------------------------------------------------------------------------- #

class TestSchemaIntegrity:

    def test_all_seeded_schemas_come_back_as_lists_after_roundtrip(self, client_and_db):
        """Belt-and-suspenders: ensure every seeded type has a list-shaped
        schema in the HTTP response. Regression for the JSON-string bug."""
        client, _ = client_and_db
        body = client.get("/component-types").json()
        for t in body:
            assert isinstance(t["schema"], list), (
                f"Type {t['name']!r}: schema is {type(t['schema']).__name__}, not list"
            )

    def test_material_density_property_round_trips(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        material = next(t for t in body if t["name"] == "material")
        density = next(p for p in material["schema"] if p["name"] == "density_kg_m3")
        assert density["type"] == "number"
        assert density["required"] is True
        assert density["min"] == 100
        assert density["max"] == 20000
        assert density["unit"] == "kg/m³"
