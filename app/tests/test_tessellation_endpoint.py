"""
Test the POST /wings/{name}/tessellation endpoint.

This test creates an aeroplane with a simple wing, triggers tessellation,
polls for completion, and validates the result is valid three-cad-viewer JSON.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(client_and_db):
    test_client, _ = client_and_db
    yield test_client


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_tessellation_returns_valid_viewer_json(client: TestClient):
    """POST /tessellation → poll → result has shapes with vertices/triangles."""

    # 1. Create aeroplane
    create_res = client.post("/aeroplanes", params={"name": "tess_test"})
    assert create_res.status_code == 201
    aeroplane_id = create_res.json()["id"]

    # 2. Create a simple wing (2 x_secs)
    # Use the from-wingconfig endpoint with a proper airfoil path
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())

    wing_config = {
        "segments": [{
            "root_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
            "tip_airfoil": {"airfoil": airfoil_path, "chord": 120.0, "incidence": 0},
            "length": 500.0,
            "sweep": 0,
            "number_interpolation_points": 101,
        }],
        "nose_pnt": [0, 0, 0],
        "symmetric": True,
    }
    wing_res = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/from-wingconfig",
        json=wing_config,
    )
    assert wing_res.status_code == 201

    # 3. Trigger tessellation
    tess_res = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/test_wing/tessellation"
    )
    assert tess_res.status_code == 202

    # 4. Poll for completion
    deadline = time.monotonic() + 120.0
    result = None
    while time.monotonic() < deadline:
        status_res = client.get(f"/aeroplanes/{aeroplane_id}/status")
        assert status_res.status_code == 200
        payload = status_res.json()

        if payload["status"] == "SUCCESS":
            result = payload.get("result")
            break
        if payload["status"] == "FAILURE":
            pytest.fail(f"Tessellation failed: {payload}")

        time.sleep(0.5)

    assert result is not None, "Tessellation timed out"

    # 5. Validate three-cad-viewer JSON structure
    assert "data" in result, f"Result keys: {list(result.keys())}"
    data = result["data"]
    assert "shapes" in data, f"Data keys: {list(data.keys())}"

    shapes = data["shapes"]
    assert isinstance(shapes, dict), f"Shapes type: {type(shapes)}"

    # The shapes dict should have a bounding box
    assert "bb" in shapes, f"Shapes keys: {list(shapes.keys())}"
    bb = shapes["bb"]
    assert "xmin" in bb and "xmax" in bb, f"BB keys: {list(bb.keys())}"

    # The bounding box should be non-degenerate
    assert bb["xmax"] > bb["xmin"], f"BB x: {bb['xmin']} to {bb['xmax']}"
    assert bb["ymax"] > bb["ymin"], f"BB y: {bb['ymin']} to {bb['ymax']}"

    # Result should have config
    assert "config" in result
    assert "type" in result
    assert result["type"] == "data"
    assert result["count"] > 0
