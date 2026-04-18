"""Tests for the extended components catalog (GH#37).

Uses the client_and_db fixture for in-memory SQLite isolation.
"""

import io


class TestComponentTypes:

    def test_returns_all_types(self, client_and_db):
        client, _ = client_and_db
        res = client.get("/components/types")
        assert res.status_code == 200
        types = res.json()["types"]
        assert "servo" in types
        assert "material" in types
        assert "propeller" in types
        assert "generic" in types
        assert len(types) == 10


class TestComponentCRUDExtended:

    def test_create_material_component(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "PLA+",
            "component_type": "material",
            "manufacturer": "eSUN",
            "specs": {"density_kg_m3": 1240, "print_resolution_mm": 0.4, "print_type": "volume"},
        })
        assert res.status_code == 201
        assert res.json()["component_type"] == "material"
        assert res.json()["specs"]["density_kg_m3"] == 1240

    def test_create_propeller_component(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "APC 10x5",
            "component_type": "propeller",
            "manufacturer": "APC",
            "mass_g": 15,
            "specs": {"diameter_in": 10, "pitch_in": 5, "blades": 2},
        })
        assert res.status_code == 201
        assert res.json()["component_type"] == "propeller"

    def test_create_generic_component(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "M3x10 Screw Pack",
            "component_type": "generic",
            "mass_g": 2.5,
            "specs": {"quantity": 50},
        })
        assert res.status_code == 201
        assert res.json()["component_type"] == "generic"

    def test_create_with_bbox(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "Savox SH-0257MG",
            "component_type": "servo",
            "manufacturer": "Savox",
            "mass_g": 14.2,
            "bbox_x_mm": 22.8,
            "bbox_y_mm": 12.0,
            "bbox_z_mm": 25.4,
            "specs": {"torque_kgcm": 2.2},
        })
        assert res.status_code == 201
        data = res.json()
        assert data["bbox_x_mm"] == 22.8
        assert data["bbox_y_mm"] == 12.0
        assert data["bbox_z_mm"] == 25.4

    def test_bbox_fields_default_to_none(self, client_and_db):
        client, _ = client_and_db
        res = client.post("/components", json={
            "name": "Simple Part",
            "component_type": "generic",
            "specs": {},
        })
        assert res.status_code == 201
        data = res.json()
        assert data["bbox_x_mm"] is None
        assert data["model_ref"] is None


class TestComponentSearch:

    def test_search_by_manufacturer(self, client_and_db):
        client, _ = client_and_db
        client.post("/components", json={
            "name": "Test Motor",
            "component_type": "brushless_motor",
            "manufacturer": "UniqueManufacturerXYZ",
            # brushless_motor seed schema requires kv_rpm_per_volt (gh#83)
            "specs": {"kv_rpm_per_volt": 880},
        })
        res = client.get("/components", params={"q": "UniqueManufacturer"})
        assert res.status_code == 200
        assert any(c["manufacturer"] == "UniqueManufacturerXYZ" for c in res.json()["items"])


class TestModelUploadDownload:

    def test_upload_step_file(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "Upload Test", "component_type": "generic", "specs": {},
        }).json()
        res = client.post(
            f"/components/{comp['id']}/model",
            files={"file": ("test.step", io.BytesIO(b"ISO-10303-21;"), "application/step")},
        )
        assert res.status_code == 200
        assert res.json()["model_ref"] is not None

    def test_download_model_file(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "Download Test", "component_type": "generic", "specs": {},
        }).json()
        client.post(
            f"/components/{comp['id']}/model",
            files={"file": ("dl.step", io.BytesIO(b"ISO-10303-21; content"), "application/step")},
        )
        res = client.get(f"/components/{comp['id']}/model")
        assert res.status_code == 200
        assert b"ISO-10303-21" in res.content

    def test_download_without_model_returns_404(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "No Model", "component_type": "generic", "specs": {},
        }).json()
        res = client.get(f"/components/{comp['id']}/model")
        assert res.status_code == 404

    def test_upload_unsupported_format_rejected(self, client_and_db):
        client, _ = client_and_db
        comp = client.post("/components", json={
            "name": "Bad Upload", "component_type": "generic", "specs": {},
        }).json()
        res = client.post(
            f"/components/{comp['id']}/model",
            files={"file": ("bad.pdf", io.BytesIO(b"pdf"), "application/pdf")},
        )
        assert res.status_code == 422
