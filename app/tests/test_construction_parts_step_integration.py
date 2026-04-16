"""End-to-end integration test for STEP upload (gh#80).

Unit tests elsewhere cover the weight formulas in isolation. This test
closes the coverage gap on the STEP-parser path itself: it uploads a
real 10×10×10 mm cube STEP file (known geometry), verifies that
CadQuery's importStep → Volume/Area/BoundingBox returns the expected
numbers, assigns a material, wires the part into the component tree,
and verifies the aggregated weight comes out right.

Skipped on platforms without CadQuery (linux/aarch64 per pyproject.toml
markers) so CI can still run the rest of the suite on restricted hosts.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.platform import cad_available
from app.models.construction_part import ConstructionPartModel

CUBE_FIXTURE = Path(__file__).parent / "fixtures" / "cad" / "cube_10mm.step"
CUBE_VOLUME_MM3 = 1000.0       # 10 × 10 × 10
CUBE_AREA_MM2 = 600.0          # 6 × 10 × 10
CUBE_EDGE_MM = 10.0
PLA_DENSITY_KG_M3 = 1240       # typical PLA
# 1000 mm³ × 1240 kg/m³ × 1e-6 = 1.24 g
EXPECTED_WEIGHT_G = CUBE_VOLUME_MM3 * PLA_DENSITY_KG_M3 / 1e6


@pytest.fixture()
def _skip_if_no_cadquery():
    if not cad_available():
        pytest.skip("CadQuery not available on this platform")


@pytest.fixture()
def cube_step_bytes():
    assert CUBE_FIXTURE.exists(), f"missing fixture: {CUBE_FIXTURE}"
    return CUBE_FIXTURE.read_bytes()


# --------------------------------------------------------------------------- #
# AC-03 — STEP upload extracts the expected geometry
# --------------------------------------------------------------------------- #

class TestCubeStepUpload:

    def test_upload_extracts_correct_volume_and_area(
        self, client_and_db, _skip_if_no_cadquery, cube_step_bytes
    ):
        client, sf = client_and_db
        files = {"file": ("cube_10mm.step", cube_step_bytes, "application/octet-stream")}
        res = client.post(
            "/aeroplanes/aero-cube/construction-parts",
            files=files,
            data={"name": "Cube10mm"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        part_id = body["id"]

        # Volume / Area within ±0.1% tolerance — CadQuery returns floats, and
        # STEP export/import is not perfectly exact.
        assert body["volume_mm3"] is not None
        assert 999.0 <= body["volume_mm3"] <= 1001.0, body["volume_mm3"]
        assert 599.0 <= body["area_mm2"] <= 601.0, body["area_mm2"]

        # Bounding box: each edge 10 mm ±0.1
        for key in ("bbox_x_mm", "bbox_y_mm", "bbox_z_mm"):
            v = body[key]
            assert v is not None
            assert 9.9 <= v <= 10.1, f"{key}={v}"

        assert body["file_format"] == "step"

        # File must be written to disk under tmp/construction_parts/{aeroplane}/
        session = sf()
        try:
            row = session.get(ConstructionPartModel, part_id)
            assert row.file_path is not None
            stored = Path(row.file_path)
            assert stored.exists(), f"stored file missing: {stored}"
            assert "aero-cube" in row.file_path
        finally:
            session.close()
            # Teardown: remove the stored upload so we don't leak files.
            try:
                stored.unlink()
            except (FileNotFoundError, NameError):
                pass


# --------------------------------------------------------------------------- #
# AC-04 — Full weight pipeline: upload → material → tree → weight
# --------------------------------------------------------------------------- #

class TestEndToEndWeight:

    def test_cube_wired_into_tree_produces_expected_weight(
        self, client_and_db, _skip_if_no_cadquery, cube_step_bytes
    ):
        client, sf = client_and_db

        # 1. Define PLA+ material (density 1240 kg/m³).
        material = client.post("/components", json={
            "name": "PLA+",
            "component_type": "material",
            "specs": {"density_kg_m3": PLA_DENSITY_KG_M3, "print_type": "volume"},
        }).json()

        # 2. Upload the cube STEP with the material already linked.
        files = {"file": ("cube_10mm.step", cube_step_bytes, "application/octet-stream")}
        part = client.post(
            "/aeroplanes/aero-cube/construction-parts",
            files=files,
            data={"name": "Cube10mm", "material_component_id": str(material["id"])},
        ).json()

        # 3. Assign the part into the component tree as a cad_shape leaf.
        node_res = client.post("/aeroplanes/aero-cube/component-tree", json={
            "node_type": "cad_shape",
            "name": "cube-in-tree",
            "construction_part_id": part["id"],
        })
        assert node_res.status_code == 201, node_res.text
        node = node_res.json()

        # Snapshot logic (N1) must have copied volume+area+material onto the node
        assert 999.0 <= node["volume_mm3"] <= 1001.0
        assert node["material_id"] == material["id"]

        # 4. GET the tree and verify weight enrichment.
        tree = client.get("/aeroplanes/aero-cube/component-tree").json()
        root = tree["root_nodes"][0]

        assert root["own_weight_source"] == "calculated"
        assert root["weight_status"] == "valid"
        # Expected 1.24 g ± 0.01
        assert abs(root["own_weight_g"] - EXPECTED_WEIGHT_G) < 0.01, root["own_weight_g"]
        assert abs(root["total_weight_g"] - EXPECTED_WEIGHT_G) < 0.01, root["total_weight_g"]

        # Teardown
        session = sf()
        try:
            row = session.get(ConstructionPartModel, part["id"])
            if row and row.file_path:
                try:
                    Path(row.file_path).unlink()
                except FileNotFoundError:
                    pass
        finally:
            session.close()
