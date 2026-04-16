"""Tests for the Construction-Parts file API + metadata CRUD (gh#57-9uk).

Covers POST upload, GET file download (with optional STEP→STL regeneration),
PUT metadata-only update, and DELETE with lock-protection. File storage
follows the components.py pattern: `tmp/construction_parts/{aeroplane}/...`.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from app.models.construction_part import ConstructionPartModel


# Minimal valid STL (binary header 80 bytes + uint32 triangle count = 0)
_EMPTY_BINARY_STL = b"\x00" * 80 + b"\x00\x00\x00\x00"

# Minimal valid ASCII STL with one zero-area triangle
_ASCII_STL_ONE_TRI = (
    b"solid placeholder\n"
    b"facet normal 0 0 1\n"
    b"  outer loop\n"
    b"    vertex 0 0 0\n"
    b"    vertex 1 0 0\n"
    b"    vertex 0 1 0\n"
    b"  endloop\n"
    b"endfacet\n"
    b"endsolid placeholder\n"
)


# --------------------------------------------------------------------------- #
# UPLOAD  POST /aeroplanes/{id}/construction-parts
# --------------------------------------------------------------------------- #

class TestUpload:

    def test_upload_stl_creates_part(self, client_and_db):
        client, _ = client_and_db
        files = {"file": ("test.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        data = {"name": "Bracket"}

        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data=data)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["name"] == "Bracket"
        assert body["aeroplane_id"] == "aero-1"
        assert body["locked"] is False
        # The file_format/file_path are surfaced for the consumer of the new fields
        assert body.get("file_format") in ("stl", "step")

    def test_upload_persists_file_to_disk(self, client_and_db):
        client, sf = client_and_db
        files = {"file": ("frame.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        res = client.post("/aeroplanes/aero-x/construction-parts", files=files, data={"name": "Frame"})
        part_id = res.json()["id"]

        session = sf()
        try:
            row = session.get(ConstructionPartModel, part_id)
            assert row.file_path is not None
            assert Path(row.file_path).exists(), f"file should exist at {row.file_path}"
            # File path lives under the per-aeroplane subdir
            assert "aero-x" in row.file_path
        finally:
            session.close()
            # Cleanup the stored file
            try:
                os.unlink(row.file_path)
            except FileNotFoundError:
                pass

    def test_upload_with_optional_metadata(self, client_and_db):
        client, _ = client_and_db
        material_res = client.post("/components", json={
            "name": "PLA+", "component_type": "material",
            "specs": {"density_kg_m3": 1240},
        })
        material_id = material_res.json()["id"]

        files = {"file": ("p.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        data = {
            "name": "Bulkhead",
            "material_component_id": str(material_id),
            "thumbnail_url": "/thumbs/bulkhead.png",
        }
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data=data)
        assert res.status_code == 201
        body = res.json()
        assert body["material_component_id"] == material_id
        assert body["thumbnail_url"] == "/thumbs/bulkhead.png"

    def test_upload_rejects_unknown_extension(self, client_and_db):
        client, _ = client_and_db
        files = {"file": ("bad.txt", b"not a model", "text/plain")}
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data={"name": "Bad"})
        assert res.status_code == 422

    def test_upload_rejects_oversized_file(self, client_and_db):
        client, _ = client_and_db
        # 60 MB > 50 MB limit
        big = b"\x00" * (60 * 1024 * 1024)
        files = {"file": ("big.stl", big, "application/octet-stream")}
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data={"name": "Big"})
        assert res.status_code == 413

    def test_upload_rejects_empty_file(self, client_and_db):
        client, _ = client_and_db
        files = {"file": ("empty.stl", b"", "application/octet-stream")}
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data={"name": "Empty"})
        assert res.status_code == 422

    def test_upload_records_file_format(self, client_and_db):
        client, _ = client_and_db
        files = {"file": ("p.STL", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        res = client.post("/aeroplanes/a/construction-parts", files=files, data={"name": "P"})
        assert res.json()["file_format"] == "stl"


# --------------------------------------------------------------------------- #
# DOWNLOAD  GET /aeroplanes/{id}/construction-parts/{partId}/file
# --------------------------------------------------------------------------- #

class TestDownload:

    def _upload_stl(self, client, aeroplane_id="aero-1", name="Stl"):
        files = {"file": (f"{name}.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        return client.post(
            f"/aeroplanes/{aeroplane_id}/construction-parts",
            files=files, data={"name": name},
        ).json()

    def test_download_stl_when_source_is_stl(self, client_and_db):
        client, _ = client_and_db
        part = self._upload_stl(client)

        res = client.get(f"/aeroplanes/aero-1/construction-parts/{part['id']}/file?format=stl")
        assert res.status_code == 200
        assert res.content == _ASCII_STL_ONE_TRI

    def test_download_returns_404_for_missing_part(self, client_and_db):
        client, _ = client_and_db
        res = client.get("/aeroplanes/aero-1/construction-parts/9999/file?format=stl")
        assert res.status_code == 404

    def test_download_step_from_stl_source_returns_422(self, client_and_db):
        """STEP cannot be regenerated from STL — 422 with a clear message."""
        client, _ = client_and_db
        part = self._upload_stl(client)
        res = client.get(f"/aeroplanes/aero-1/construction-parts/{part['id']}/file?format=step")
        assert res.status_code == 422

    def test_download_rejects_invalid_format(self, client_and_db):
        client, _ = client_and_db
        part = self._upload_stl(client)
        res = client.get(f"/aeroplanes/aero-1/construction-parts/{part['id']}/file?format=obj")
        assert res.status_code == 422

    def test_download_cross_aeroplane_returns_404(self, client_and_db):
        client, _ = client_and_db
        part = self._upload_stl(client, aeroplane_id="aero-1")
        res = client.get(f"/aeroplanes/aero-2/construction-parts/{part['id']}/file?format=stl")
        assert res.status_code == 404


# --------------------------------------------------------------------------- #
# UPDATE  PUT /aeroplanes/{id}/construction-parts/{partId}
# --------------------------------------------------------------------------- #

class TestUpdateMetadata:

    def _upload(self, client):
        files = {"file": ("p.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        return client.post(
            "/aeroplanes/aero-1/construction-parts",
            files=files, data={"name": "Original"},
        ).json()

    def test_put_updates_name(self, client_and_db):
        client, _ = client_and_db
        part = self._upload(client)
        res = client.put(
            f"/aeroplanes/aero-1/construction-parts/{part['id']}",
            json={"name": "Renamed", "material_component_id": None, "thumbnail_url": None},
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Renamed"

    def test_put_updates_material_component_id(self, client_and_db):
        client, _ = client_and_db
        material = client.post("/components", json={
            "name": "PETG", "component_type": "material", "specs": {"density_kg_m3": 1270},
        }).json()
        part = self._upload(client)

        res = client.put(
            f"/aeroplanes/aero-1/construction-parts/{part['id']}",
            json={"name": part["name"], "material_component_id": material["id"], "thumbnail_url": None},
        )
        assert res.status_code == 200
        assert res.json()["material_component_id"] == material["id"]

    def test_put_does_not_touch_geometry_or_file_path(self, client_and_db):
        client, sf = client_and_db
        part = self._upload(client)
        original_path = sf().get(ConstructionPartModel, part["id"]).file_path

        client.put(
            f"/aeroplanes/aero-1/construction-parts/{part['id']}",
            json={"name": "Renamed", "material_component_id": None, "thumbnail_url": None},
        )
        new_path = sf().get(ConstructionPartModel, part["id"]).file_path
        assert new_path == original_path

    def test_put_returns_404_for_missing(self, client_and_db):
        client, _ = client_and_db
        res = client.put(
            "/aeroplanes/aero-1/construction-parts/9999",
            json={"name": "X", "material_component_id": None, "thumbnail_url": None},
        )
        assert res.status_code == 404


# --------------------------------------------------------------------------- #
# DELETE
# --------------------------------------------------------------------------- #

class TestDelete:

    def _upload(self, client, name="P"):
        files = {"file": (f"{name}.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        return client.post(
            "/aeroplanes/aero-1/construction-parts",
            files=files, data={"name": name},
        ).json()

    def test_delete_unlocked_removes_row_and_file(self, client_and_db):
        client, sf = client_and_db
        part = self._upload(client)
        file_path = sf().get(ConstructionPartModel, part["id"]).file_path

        res = client.delete(f"/aeroplanes/aero-1/construction-parts/{part['id']}")
        assert res.status_code == 204
        assert sf().get(ConstructionPartModel, part["id"]) is None
        assert not Path(file_path).exists()

    def test_delete_locked_returns_409_and_keeps_state(self, client_and_db):
        client, sf = client_and_db
        part = self._upload(client)
        client.put(f"/aeroplanes/aero-1/construction-parts/{part['id']}/lock")

        file_path = sf().get(ConstructionPartModel, part["id"]).file_path
        res = client.delete(f"/aeroplanes/aero-1/construction-parts/{part['id']}")
        assert res.status_code == 409
        # State unchanged
        assert sf().get(ConstructionPartModel, part["id"]) is not None
        assert Path(file_path).exists()

    def test_delete_returns_404_for_missing(self, client_and_db):
        client, _ = client_and_db
        res = client.delete("/aeroplanes/aero-1/construction-parts/9999")
        assert res.status_code == 404

    def test_delete_cross_aeroplane_returns_404(self, client_and_db):
        client, _ = client_and_db
        part = self._upload(client)
        res = client.delete(f"/aeroplanes/aero-2/construction-parts/{part['id']}")
        assert res.status_code == 404


# --------------------------------------------------------------------------- #
# Geometry extraction (skipped on platforms without CadQuery)
# --------------------------------------------------------------------------- #

class TestGeometryExtraction:

    def test_geometry_extraction_skipped_for_stl_uploads(self, client_and_db):
        """MVP behavior: STL meshes are not analyzed for geometry; STEP is.

        STL gives a triangle soup, not a watertight solid — extracting volume
        cleanly needs extra deps (numpy-stl). Documented limitation. The
        upload still succeeds; geometry fields remain NULL.
        """
        client, _ = client_and_db
        files = {"file": ("triangle.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data={"name": "Tri"})
        body = res.json()
        for k in ("volume_mm3", "area_mm2", "bbox_x_mm", "bbox_y_mm", "bbox_z_mm"):
            assert body[k] is None, f"expected {k} to be NULL for STL upload"

    def test_upload_succeeds_when_cadquery_unavailable(self, client_and_db, monkeypatch):
        """If CadQuery is unavailable, the row is still created but geometry stays NULL."""
        from app.core import platform
        platform.cad_available.cache_clear()
        monkeypatch.setattr(platform, "cad_available", lambda: False)

        client, _ = client_and_db
        files = {"file": ("p.stl", _ASCII_STL_ONE_TRI, "application/octet-stream")}
        res = client.post("/aeroplanes/aero-1/construction-parts", files=files, data={"name": "NoCad"})
        assert res.status_code == 201
        body = res.json()
        # All geometry fields must be NULL
        assert body["volume_mm3"] is None
        assert body["area_mm2"] is None
        assert body["bbox_x_mm"] is None
        assert body["bbox_y_mm"] is None
        assert body["bbox_z_mm"] is None
