"""Tests for Component specs validation against the type schema (gh#83).

The existing `POST /components` / `PUT /components/{id}` now validates the
`specs` payload against the property schema of the referenced type. Tolerant
mode: unknown keys are accepted and stored; known keys are checked.
"""
from __future__ import annotations


class TestComponentTypeValidation:

    def test_unknown_component_type_is_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "x", "component_type": "not_a_real_type", "specs": {},
        })
        assert res.status_code == 422


class TestRequiredFieldValidation:

    def test_missing_required_density_for_material_is_rejected(self, client_and_db):
        """The seeded `material` type requires `density_kg_m3`."""
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "PLA", "component_type": "material", "specs": {},
        })
        assert res.status_code == 422

    def test_material_with_density_succeeds(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "PLA", "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        })
        assert res.status_code == 201
        assert res.json()["specs"]["density_kg_m3"] == 1240


class TestNumberRangeValidation:

    def test_number_below_min_is_rejected(self, client_and_db):
        """`density_kg_m3` has min=100 in the seeded material schema."""
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "impossible", "component_type": "material",
            "specs": {"density_kg_m3": 50},  # below min=100
        })
        assert res.status_code == 422

    def test_number_above_max_is_rejected(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "neutron-star", "component_type": "material",
            "specs": {"density_kg_m3": 1e6},  # way above any plausible max
        })
        assert res.status_code == 422


class TestEnumValidation:

    def test_enum_value_not_in_options_is_rejected(self, client_and_db):
        """Material `print_type` enum must be volume|surface."""
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "odd", "component_type": "material",
            "specs": {"density_kg_m3": 1240, "print_type": "sideways"},
        })
        assert res.status_code == 422

    def test_enum_value_in_options_succeeds(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "pla", "component_type": "material",
            "specs": {"density_kg_m3": 1240, "print_type": "volume"},
        })
        assert res.status_code == 201


class TestBooleanValidation:

    def test_non_boolean_for_boolean_property_is_rejected(self, client_and_db):
        client, _ = client_and_db
        # Create a custom type with a boolean property
        client.post("/component-types", json={
            "name": "boolish", "label": "Boolish", "schema": [
                {"name": "is_spicy", "label": "Is Spicy", "type": "boolean"},
            ],
        })
        res = client.post("/components", json={
            "name": "c", "component_type": "boolish",
            "specs": {"is_spicy": "maybe"},
        })
        assert res.status_code == 422


class TestToleranceForUnknownKeys:

    def test_unknown_keys_in_specs_are_accepted_and_stored(self, client_and_db):
        """Tolerant mode: anything extra is just stored alongside the validated fields."""
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "weird", "component_type": "material",
            "specs": {
                "density_kg_m3": 1240,
                "totally_made_up_key": "whatever",
                "legacy_field": 42,
            },
        })
        assert res.status_code == 201
        stored = res.json()["specs"]
        assert stored["density_kg_m3"] == 1240
        assert stored["totally_made_up_key"] == "whatever"
        assert stored["legacy_field"] == 42


class TestPutValidation:

    def test_put_validates_same_as_post(self, client_and_db):
        """The same spec rules fire on update."""
        client, _ = client_and_db
        # Create with a valid specs payload
        comp = client.post("/components", json={
            "name": "PLA", "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        }).json()
        # Now PUT with an invalid enum
        res = client.put(f"/components/{comp['id']}", json={
            "name": comp["name"], "component_type": comp["component_type"],
            "specs": {"density_kg_m3": 1240, "print_type": "sideways"},
        })
        assert res.status_code == 422


class TestBackwardCompat:

    def test_get_components_types_endpoint_still_works(self, client_and_db):
        """The legacy /components/types endpoint returns the same shape ({types: [...]}) but now dynamic."""
        client, _ = client_and_db
        body = client.get("/components/types").json()
        assert "types" in body
        assert "material" in body["types"]
        assert "servo" in body["types"]
