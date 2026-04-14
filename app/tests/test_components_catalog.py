"""Tests for the extended components catalog (GH#37)."""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestComponentTypes:
    """GET /components/types"""

    def test_returns_all_types(self):
        res = client.get("/components/types")
        assert res.status_code == 200
        data = res.json()
        assert "types" in data
        types = data["types"]
        assert "servo" in types
        assert "brushless_motor" in types
        assert "material" in types
        assert "propeller" in types
        assert "generic" in types
        assert len(types) == 9


class TestComponentCRUDExtended:
    """Test new fields (bbox, model_ref) and new types."""

    def test_create_material_component(self):
        res = client.post("/components", json={
            "name": "PLA+",
            "component_type": "material",
            "manufacturer": "eSUN",
            "mass_g": None,
            "specs": {
                "density_kg_m3": 1240,
                "print_resolution_mm": 0.4,
                "print_type": "volume",
            },
        })
        assert res.status_code == 201
        data = res.json()
        assert data["component_type"] == "material"
        assert data["specs"]["density_kg_m3"] == 1240

    def test_create_propeller_component(self):
        res = client.post("/components", json={
            "name": "APC 10x5",
            "component_type": "propeller",
            "manufacturer": "APC",
            "mass_g": 15,
            "specs": {
                "diameter_in": 10,
                "pitch_in": 5,
                "blades": 2,
                "material": "glass-filled nylon",
            },
        })
        assert res.status_code == 201
        assert res.json()["component_type"] == "propeller"

    def test_create_generic_component(self):
        res = client.post("/components", json={
            "name": "M3x10 Screw Pack",
            "component_type": "generic",
            "mass_g": 2.5,
            "specs": {"quantity": 50, "material": "stainless steel"},
        })
        assert res.status_code == 201
        assert res.json()["component_type"] == "generic"

    def test_create_with_bbox(self):
        res = client.post("/components", json={
            "name": "Savox SH-0257MG",
            "component_type": "servo",
            "manufacturer": "Savox",
            "mass_g": 14.2,
            "bbox_x_mm": 22.8,
            "bbox_y_mm": 12.0,
            "bbox_z_mm": 25.4,
            "specs": {"torque_kgcm": 2.2, "speed_s_60deg": 0.09, "voltage_v": 6.0},
        })
        assert res.status_code == 201
        data = res.json()
        assert data["bbox_x_mm"] == 22.8
        assert data["bbox_y_mm"] == 12.0
        assert data["bbox_z_mm"] == 25.4

    def test_bbox_fields_default_to_none(self):
        res = client.post("/components", json={
            "name": "Simple Part",
            "component_type": "generic",
            "specs": {},
        })
        assert res.status_code == 201
        data = res.json()
        assert data["bbox_x_mm"] is None
        assert data["bbox_y_mm"] is None
        assert data["bbox_z_mm"] is None
        assert data["model_ref"] is None


class TestComponentSearch:
    """Test search by name and manufacturer."""

    def test_search_by_manufacturer(self):
        # Create component with known manufacturer
        client.post("/components", json={
            "name": "Test Motor",
            "component_type": "brushless_motor",
            "manufacturer": "UniqueManufacturerXYZ",
            "specs": {},
        })
        res = client.get("/components", params={"q": "UniqueManufacturer"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert any(c["manufacturer"] == "UniqueManufacturerXYZ" for c in items)


class TestModelUploadDownload:
    """Test STEP/STL file upload and download."""

    def test_upload_step_file(self):
        # Create component first
        create_res = client.post("/components", json={
            "name": "Upload Test Part",
            "component_type": "generic",
            "specs": {},
        })
        comp_id = create_res.json()["id"]

        # Upload a fake STEP file
        step_content = b"ISO-10303-21; (fake step content for testing)"
        res = client.post(
            f"/components/{comp_id}/model",
            files={"file": ("test_part.step", io.BytesIO(step_content), "application/step")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["model_ref"] is not None
        assert "step" in data["model_ref"]

    def test_download_model_file(self):
        # Create + upload
        create_res = client.post("/components", json={
            "name": "Download Test Part",
            "component_type": "generic",
            "specs": {},
        })
        comp_id = create_res.json()["id"]

        step_content = b"ISO-10303-21; (fake step content for download test)"
        client.post(
            f"/components/{comp_id}/model",
            files={"file": ("download_test.step", io.BytesIO(step_content), "application/step")},
        )

        # Download
        res = client.get(f"/components/{comp_id}/model")
        assert res.status_code == 200
        assert b"ISO-10303-21" in res.content

    def test_download_without_model_returns_404(self):
        create_res = client.post("/components", json={
            "name": "No Model Part",
            "component_type": "generic",
            "specs": {},
        })
        comp_id = create_res.json()["id"]
        res = client.get(f"/components/{comp_id}/model")
        assert res.status_code == 404

    def test_upload_unsupported_format_rejected(self):
        create_res = client.post("/components", json={
            "name": "Bad Upload Part",
            "component_type": "generic",
            "specs": {},
        })
        comp_id = create_res.json()["id"]
        res = client.post(
            f"/components/{comp_id}/model",
            files={"file": ("bad.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
        )
        assert res.status_code == 422
