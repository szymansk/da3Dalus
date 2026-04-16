"""Tests for the Component Types CRUD API (gh#83).

A component type defines the specs-schema for components of that type.
Seeded types (`deletable=false`) cannot be deleted; user-added types
require reference_count=0 to delete.
"""
from __future__ import annotations


def _create_type(client, name="custom_tube", label="Custom Tube", schema=None):
    return client.post("/component-types", json={
        "name": name,
        "label": label,
        "description": None,
        "schema": schema or [],
    }).json()


# --------------------------------------------------------------------------- #
# GET list
# --------------------------------------------------------------------------- #

class TestListTypes:

    def test_list_includes_seeded_types(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        names = {t["name"] for t in body}
        # all 9 seeded types must exist
        assert {"material", "servo", "brushless_motor", "battery",
                "esc", "propeller", "receiver", "flight_controller",
                "generic"}.issubset(names)

    def test_list_is_sorted_by_label(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        labels = [t["label"] for t in body]
        assert labels == sorted(labels)

    def test_list_includes_reference_count(self, client_and_db):
        client, _ = client_and_db
        # Add a component of type 'servo'
        client.post("/components", json={
            "name": "s1", "component_type": "servo", "specs": {},
        })
        body = client.get("/component-types").json()
        servo = next(t for t in body if t["name"] == "servo")
        assert servo["reference_count"] == 1

    def test_seeded_types_are_not_deletable(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        for t in body:
            assert t["deletable"] is False


# --------------------------------------------------------------------------- #
# GET single
# --------------------------------------------------------------------------- #

class TestGetType:

    def test_material_has_density_property_in_schema(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        material = next(t for t in body if t["name"] == "material")
        prop_names = {p["name"] for p in material["schema"]}
        assert "density_kg_m3" in prop_names
        density = next(p for p in material["schema"] if p["name"] == "density_kg_m3")
        assert density["type"] == "number"
        assert density["required"] is True

    def test_get_by_id_returns_full_type(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        some = body[0]
        single = client.get(f"/component-types/{some['id']}").json()
        assert single["id"] == some["id"]
        assert single["name"] == some["name"]

    def test_get_returns_404_for_missing_id(self, client_and_db):
        client, _ = client_and_db
        assert client.get("/component-types/99999").status_code == 404


# --------------------------------------------------------------------------- #
# POST create
# --------------------------------------------------------------------------- #

class TestCreateType:

    def test_create_user_type_defaults_deletable_true(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="carbon_tube", label="Carbon Tube")
        assert t["name"] == "carbon_tube"
        assert t["deletable"] is True
        assert t["reference_count"] == 0

    def test_create_forces_deletable_true_even_if_false_in_request(self, client_and_db):
        """`deletable=false` in the request is ignored — user-created types are always deletable."""
        client, _ = client_and_db
        res = client.post("/component-types", json={
            "name": "xxx", "label": "X", "deletable": False, "schema": [],
        })
        assert res.status_code == 201
        assert res.json()["deletable"] is True

    def test_create_with_duplicate_name_returns_409(self, client_and_db):
        client, _ = client_and_db
        _create_type(client, name="foo")
        res = client.post("/component-types", json={
            "name": "foo", "label": "Foo 2", "schema": [],
        })
        assert res.status_code == 409

    def test_create_with_duplicate_of_seeded_name_returns_409(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/component-types", json={
            "name": "material", "label": "...", "schema": [],
        })
        assert res.status_code == 409

    def test_create_with_number_property(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="with_number", schema=[
            {"name": "foo", "label": "Foo", "type": "number", "min": 0, "max": 100, "required": True},
        ])
        assert t["schema"][0]["type"] == "number"
        assert t["schema"][0]["min"] == 0

    def test_create_with_enum_property(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="with_enum", schema=[
            {"name": "color", "label": "Color", "type": "enum", "options": ["red", "green", "blue"]},
        ])
        assert t["schema"][0]["options"] == ["red", "green", "blue"]

    def test_create_enum_without_options_is_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/component-types", json={
            "name": "bad_enum", "label": "Bad", "schema": [
                {"name": "x", "label": "X", "type": "enum"},
            ],
        })
        assert res.status_code == 422

    def test_create_property_with_invalid_type_is_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/component-types", json={
            "name": "bad_type", "label": "Bad", "schema": [
                {"name": "x", "label": "X", "type": "color"},  # not supported
            ],
        })
        assert res.status_code == 422

    def test_create_property_with_non_snake_case_name_is_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/component-types", json={
            "name": "bad_prop_name", "label": "Bad", "schema": [
                {"name": "BadName", "label": "X", "type": "number"},
            ],
        })
        assert res.status_code == 422


# --------------------------------------------------------------------------- #
# PUT update
# --------------------------------------------------------------------------- #

class TestUpdateType:

    def test_put_updates_label_and_description(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="myt", label="Old")
        res = client.put(f"/component-types/{t['id']}", json={
            "name": t["name"], "label": "New", "description": "now with desc",
            "schema": t["schema"],
        })
        assert res.status_code == 200
        body = res.json()
        assert body["label"] == "New"
        assert body["description"] == "now with desc"

    def test_put_ignores_name_change(self, client_and_db):
        """Name is immutable after create — PUT with a different name is ignored."""
        client, _ = client_and_db
        t = _create_type(client, name="original")
        res = client.put(f"/component-types/{t['id']}", json={
            "name": "renamed", "label": t["label"], "schema": t["schema"],
        })
        assert res.status_code == 200
        assert res.json()["name"] == "original"

    def test_put_ignores_deletable_change(self, client_and_db):
        """The deletable flag is fixed at create-time for user types and always false for seeded."""
        client, _ = client_and_db
        # Try to make a seeded type deletable
        body = client.get("/component-types").json()
        seeded = next(t for t in body if t["name"] == "material")
        res = client.put(f"/component-types/{seeded['id']}", json={
            "name": seeded["name"], "label": seeded["label"],
            "deletable": True,
            "schema": seeded["schema"],
        })
        assert res.status_code == 200
        assert res.json()["deletable"] is False

    def test_put_can_edit_seeded_schema(self, client_and_db):
        """Seeded types' schemas are editable (only name + deletable are locked)."""
        client, _ = client_and_db
        body = client.get("/component-types").json()
        servo = next(t for t in body if t["name"] == "servo")
        new_schema = servo["schema"] + [
            {"name": "notes", "label": "Notes", "type": "string"},
        ]
        res = client.put(f"/component-types/{servo['id']}", json={
            "name": servo["name"], "label": servo["label"],
            "schema": new_schema,
        })
        assert res.status_code == 200
        prop_names = {p["name"] for p in res.json()["schema"]}
        assert "notes" in prop_names


# --------------------------------------------------------------------------- #
# DELETE
# --------------------------------------------------------------------------- #

class TestDeleteType:

    def test_delete_seeded_type_returns_409(self, client_and_db):
        client, _ = client_and_db
        body = client.get("/component-types").json()
        seeded = next(t for t in body if t["name"] == "material")
        res = client.delete(f"/component-types/{seeded['id']}")
        assert res.status_code == 409

    def test_delete_user_type_with_no_references_returns_204(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="doomed")
        res = client.delete(f"/component-types/{t['id']}")
        assert res.status_code == 204
        # Confirm it's gone
        assert client.get(f"/component-types/{t['id']}").status_code == 404

    def test_delete_user_type_with_references_returns_409(self, client_and_db):
        client, _ = client_and_db
        t = _create_type(client, name="ref_guarded")
        # reference it
        client.post("/components", json={
            "name": "c1", "component_type": "ref_guarded", "specs": {},
        })
        res = client.delete(f"/component-types/{t['id']}")
        assert res.status_code == 409

    def test_delete_missing_id_returns_404(self, client_and_db):
        client, _ = client_and_db
        assert client.delete("/component-types/99999").status_code == 404
