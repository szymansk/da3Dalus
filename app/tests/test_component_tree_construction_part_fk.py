"""Tests for the construction_part_id FK on component_tree (gh#57-u4d / gh#34).

A `cad_shape` tree node can reference a Construction-Part (D1, gh#57-g4h)
via `construction_part_id`. When such a node is created, the service
snapshots the part's `volume_mm3`, `area_mm2`, and `material_component_id`
(mapped to the tree node's `material_id` field) so weight calculations
do not need a join on every read.
"""
from __future__ import annotations

from typing import Optional

from app.models.construction_part import ConstructionPartModel


def _make_part(
    session_factory,
    *,
    aeroplane_id: str,
    name: str = "Frame_A",
    volume_mm3: Optional[float] = 12_345.6,
    area_mm2: Optional[float] = 987.6,
    material_component_id: Optional[int] = None,
    locked: bool = False,
) -> ConstructionPartModel:
    session = session_factory()
    try:
        part = ConstructionPartModel(
            aeroplane_id=aeroplane_id,
            name=name,
            volume_mm3=volume_mm3,
            area_mm2=area_mm2,
            material_component_id=material_component_id,
            locked=locked,
        )
        session.add(part)
        session.commit()
        session.refresh(part)
        return part
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# Schema + round-trip (AC-N1-2)
# --------------------------------------------------------------------------- #

class TestSchemaRoundTrip:

    def test_construction_part_id_is_returned_in_get(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="aero-x", name="Bracket")

        # Create a cad_shape node via the existing endpoint, then verify GET
        node_res = client.post("/aeroplanes/aero-x/component-tree", json={
            "node_type": "cad_shape",
            "name": "Bracket-instance",
            "construction_part_id": part.id,
        })
        assert node_res.status_code == 201, node_res.text
        node = node_res.json()
        assert node["construction_part_id"] == part.id

        # Round-trip via list endpoint
        tree = client.get("/aeroplanes/aero-x/component-tree").json()
        assert tree["root_nodes"][0]["construction_part_id"] == part.id

    def test_construction_part_id_omitted_defaults_to_null(self, client_and_db):
        """Existing tree-node creation flows (group, cots, Creator-pipeline cad_shape) keep working."""
        client, _ = client_and_db
        node = client.post("/aeroplanes/aero-y/component-tree", json={
            "node_type": "group",
            "name": "main_wing",
        }).json()
        assert node["construction_part_id"] is None


# --------------------------------------------------------------------------- #
# Snapshot semantics (AC-N1-3)
# --------------------------------------------------------------------------- #

class TestSnapshotOnCreate:

    def test_volume_and_area_are_copied_from_part(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(
            sf,
            aeroplane_id="aero-1",
            name="Spar",
            volume_mm3=5000.0,
            area_mm2=750.0,
        )

        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cad_shape",
            "name": "Spar-instance",
            "construction_part_id": part.id,
        }).json()

        assert node["volume_mm3"] == 5000.0
        assert node["area_mm2"] == 750.0

    def test_material_component_id_maps_to_tree_material_id(self, client_and_db):
        """The construction_part has material_component_id; the tree node uses material_id (existing field)."""
        client, sf = client_and_db

        material = client.post("/components", json={
            "name": "PLA+",
            "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        }).json()

        part = _make_part(
            sf,
            aeroplane_id="aero-1",
            name="Bulkhead",
            material_component_id=material["id"],
        )

        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cad_shape",
            "name": "Bulkhead-instance",
            "construction_part_id": part.id,
        }).json()

        assert node["material_id"] == material["id"]

    def test_explicit_field_values_override_snapshot(self, client_and_db):
        """If the caller passes a value explicitly, it wins over the snapshot.

        This keeps the API symmetric with the existing creator-pipeline flow
        where shape_key+volume_mm3 are passed together. The snapshot only
        fills NULL fields.
        """
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="aero-1", name="Frame", volume_mm3=5000.0)

        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cad_shape",
            "name": "Frame-explicit",
            "construction_part_id": part.id,
            "volume_mm3": 9999.0,  # explicit override
        }).json()

        assert node["volume_mm3"] == 9999.0
        assert node["construction_part_id"] == part.id


# --------------------------------------------------------------------------- #
# Validation (AC-N1-4)
# --------------------------------------------------------------------------- #

class TestValidation:

    def test_non_existent_construction_part_id_returns_422(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cad_shape",
            "name": "Ghost",
            "construction_part_id": 99999,
        })
        assert res.status_code == 422
        assert "construction_part" in res.json().get("error", {}).get("message", "").lower() \
            or "construction_part" in str(res.json()).lower()

    def test_cross_aeroplane_construction_part_id_returns_422(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="aero-foreign", name="ForeignPart")

        res = client.post("/aeroplanes/aero-local/component-tree", json={
            "node_type": "cad_shape",
            "name": "ImportingForeign",
            "construction_part_id": part.id,
        })
        assert res.status_code == 422


# --------------------------------------------------------------------------- #
# Backward compatibility (AC-N1-5)
# --------------------------------------------------------------------------- #

class TestBackwardCompat:

    def test_creator_pipeline_cad_shape_still_works(self, client_and_db):
        """A cad_shape node can be created with shape_key/shape_hash and no construction_part_id.
        This is the auto-sync flow from gh#34, must not regress."""
        client, _ = client_and_db
        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cad_shape",
            "name": "AutoSyncedSegment",
            "shape_key": "main_wing_segment_0_shell",
            "shape_hash": "deadbeef",
            "volume_mm3": 1234.0,
        }).json()
        assert node["shape_key"] == "main_wing_segment_0_shell"
        assert node["construction_part_id"] is None
        assert node["volume_mm3"] == 1234.0

    def test_cots_node_unaffected(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "Servo", "component_type": "servo", "mass_g": 14, "specs": {},
        }).json()
        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "cots",
            "name": "Servo-instance",
            "component_id": comp["id"],
        }).json()
        assert node["construction_part_id"] is None
        assert node["component_id"] == comp["id"]

    def test_group_node_unaffected(self, client_and_db):
        client, _ = client_and_db
        node = client.post("/aeroplanes/aero-1/component-tree", json={
            "node_type": "group",
            "name": "main_wing",
        }).json()
        assert node["construction_part_id"] is None
