"""Tests for the Construction-Parts domain (gh#57-g4h).

Construction-Parts are per-aeroplane CAD bauteile (typically 3D-printed)
that complement the global COTS Component Library. This MVP covers:
  - listing parts per aeroplane
  - fetching a single part
  - toggling the `locked` flag via lock/unlock endpoints

File upload/download, general CRUD, and lock-aware regeneration are
future tickets (gh#57-9uk, gh#57-qim).
"""
from __future__ import annotations

from typing import Optional

from app.models.construction_part import ConstructionPartModel


# --------------------------------------------------------------------------- #
# Test helper: create a ConstructionPart directly in the DB
# --------------------------------------------------------------------------- #

def _make_part(
    session_factory,
    *,
    aeroplane_id: str,
    name: str = "BulkheadA",
    volume_mm3: Optional[float] = 12_345.6,
    area_mm2: Optional[float] = 987.6,
    bbox_x_mm: Optional[float] = 50.0,
    bbox_y_mm: Optional[float] = 40.0,
    bbox_z_mm: Optional[float] = 5.0,
    material_component_id: Optional[int] = None,
    locked: bool = False,
    thumbnail_url: Optional[str] = None,
) -> ConstructionPartModel:
    session = session_factory()
    try:
        part = ConstructionPartModel(
            aeroplane_id=aeroplane_id,
            name=name,
            volume_mm3=volume_mm3,
            area_mm2=area_mm2,
            bbox_x_mm=bbox_x_mm,
            bbox_y_mm=bbox_y_mm,
            bbox_z_mm=bbox_z_mm,
            material_component_id=material_component_id,
            locked=locked,
            thumbnail_url=thumbnail_url,
        )
        session.add(part)
        session.commit()
        session.refresh(part)
        return part
    finally:
        session.close()


# --------------------------------------------------------------------------- #
# LIST  GET /aeroplanes/{id}/construction-parts
# --------------------------------------------------------------------------- #

class TestListConstructionParts:

    def test_empty_list(self, client_and_db):
        client, _ = client_and_db
        res = client.get("/aeroplanes/aero-empty/construction-parts")
        assert res.status_code == 200
        body = res.json()
        assert body["aeroplane_id"] == "aero-empty"
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_returns_parts_for_aeroplane(self, client_and_db):
        client, sf = client_and_db
        _make_part(sf, aeroplane_id="aero-1", name="Rib_A")
        _make_part(sf, aeroplane_id="aero-1", name="Rib_B")

        res = client.get("/aeroplanes/aero-1/construction-parts")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        names = {item["name"] for item in body["items"]}
        assert names == {"Rib_A", "Rib_B"}

    def test_list_is_scoped_to_aeroplane(self, client_and_db):
        """A part on aero-1 must not leak into the list for aero-2."""
        client, sf = client_and_db
        _make_part(sf, aeroplane_id="aero-1", name="OnlyOnOne")
        _make_part(sf, aeroplane_id="aero-2", name="OnlyOnTwo")

        res_one = client.get("/aeroplanes/aero-1/construction-parts").json()
        res_two = client.get("/aeroplanes/aero-2/construction-parts").json()

        assert {i["name"] for i in res_one["items"]} == {"OnlyOnOne"}
        assert {i["name"] for i in res_two["items"]} == {"OnlyOnTwo"}

    def test_list_is_sorted_by_name(self, client_and_db):
        client, sf = client_and_db
        _make_part(sf, aeroplane_id="a", name="Zeta")
        _make_part(sf, aeroplane_id="a", name="Alpha")
        _make_part(sf, aeroplane_id="a", name="Mu")

        body = client.get("/aeroplanes/a/construction-parts").json()
        names = [item["name"] for item in body["items"]]
        assert names == ["Alpha", "Mu", "Zeta"]

    def test_list_exposes_required_metadata(self, client_and_db):
        client, sf = client_and_db
        _make_part(
            sf,
            aeroplane_id="a",
            name="Frame01",
            volume_mm3=1111.0,
            area_mm2=222.0,
            bbox_x_mm=10.0,
            bbox_y_mm=20.0,
            bbox_z_mm=30.0,
            locked=True,
            thumbnail_url="/thumbs/frame01.png",
        )
        body = client.get("/aeroplanes/a/construction-parts").json()
        item = body["items"][0]
        assert item["name"] == "Frame01"
        assert item["volume_mm3"] == 1111.0
        assert item["area_mm2"] == 222.0
        assert item["bbox_x_mm"] == 10.0
        assert item["bbox_y_mm"] == 20.0
        assert item["bbox_z_mm"] == 30.0
        assert item["locked"] is True
        assert item["thumbnail_url"] == "/thumbs/frame01.png"
        assert "id" in item
        assert "created_at" in item
        assert "updated_at" in item


# --------------------------------------------------------------------------- #
# DETAIL  GET /aeroplanes/{id}/construction-parts/{partId}
# --------------------------------------------------------------------------- #

class TestGetConstructionPart:

    def test_get_returns_part(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="a", name="X")

        res = client.get(f"/aeroplanes/a/construction-parts/{part.id}")
        assert res.status_code == 200
        body = res.json()
        assert body["id"] == part.id
        assert body["name"] == "X"
        assert body["aeroplane_id"] == "a"

    def test_get_returns_404_for_missing(self, client_and_db):
        client, _ = client_and_db
        res = client.get("/aeroplanes/a/construction-parts/9999")
        assert res.status_code == 404

    def test_get_returns_404_when_aeroplane_mismatch(self, client_and_db):
        """A part on aero-1 must not be retrievable via aero-2."""
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="aero-1", name="X")

        res = client.get(f"/aeroplanes/aero-2/construction-parts/{part.id}")
        assert res.status_code == 404


# --------------------------------------------------------------------------- #
# LOCK / UNLOCK
# PUT /aeroplanes/{id}/construction-parts/{partId}/lock
# PUT /aeroplanes/{id}/construction-parts/{partId}/unlock
# --------------------------------------------------------------------------- #

class TestLockUnlock:

    def test_lock_sets_flag_true(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="a", name="P", locked=False)

        res = client.put(f"/aeroplanes/a/construction-parts/{part.id}/lock")
        assert res.status_code == 200
        assert res.json()["locked"] is True

        fetched = client.get(f"/aeroplanes/a/construction-parts/{part.id}").json()
        assert fetched["locked"] is True

    def test_lock_is_idempotent(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="a", name="P", locked=True)

        res = client.put(f"/aeroplanes/a/construction-parts/{part.id}/lock")
        assert res.status_code == 200
        assert res.json()["locked"] is True

    def test_unlock_sets_flag_false(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="a", name="P", locked=True)

        res = client.put(f"/aeroplanes/a/construction-parts/{part.id}/unlock")
        assert res.status_code == 200
        assert res.json()["locked"] is False

        fetched = client.get(f"/aeroplanes/a/construction-parts/{part.id}").json()
        assert fetched["locked"] is False

    def test_unlock_is_idempotent(self, client_and_db):
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="a", name="P", locked=False)

        res = client.put(f"/aeroplanes/a/construction-parts/{part.id}/unlock")
        assert res.status_code == 200
        assert res.json()["locked"] is False

    def test_lock_missing_part_returns_404(self, client_and_db):
        client, _ = client_and_db
        res = client.put("/aeroplanes/a/construction-parts/9999/lock")
        assert res.status_code == 404

    def test_unlock_missing_part_returns_404(self, client_and_db):
        client, _ = client_and_db
        res = client.put("/aeroplanes/a/construction-parts/9999/unlock")
        assert res.status_code == 404

    def test_lock_rejects_aeroplane_mismatch(self, client_and_db):
        """Lock via wrong aeroplane path must 404 (not silently flip the flag)."""
        client, sf = client_and_db
        part = _make_part(sf, aeroplane_id="aero-1", name="P", locked=False)

        res = client.put(f"/aeroplanes/aero-2/construction-parts/{part.id}/lock")
        assert res.status_code == 404

        # Original part must remain unlocked.
        fetched = client.get(f"/aeroplanes/aero-1/construction-parts/{part.id}").json()
        assert fetched["locked"] is False


# --------------------------------------------------------------------------- #
# Material FK wiring
# --------------------------------------------------------------------------- #

class TestMaterialLink:

    def test_material_component_id_is_surfaced(self, client_and_db):
        """material_component_id references a component with type='material'."""
        client, sf = client_and_db
        material_res = client.post(
            "/components",
            json={
                "name": "PLA+",
                "component_type": "material",
                "manufacturer": "eSUN",
                "specs": {"density_kg_m3": 1240},
            },
        )
        assert material_res.status_code == 201
        material_id = material_res.json()["id"]

        _make_part(sf, aeroplane_id="a", name="WithMaterial", material_component_id=material_id)

        body = client.get("/aeroplanes/a/construction-parts").json()
        assert body["items"][0]["material_component_id"] == material_id
