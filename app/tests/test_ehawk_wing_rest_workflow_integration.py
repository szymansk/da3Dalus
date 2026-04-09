from __future__ import annotations

import io
import time
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app import schemas
from app.converters.model_schema_converters import wingConfigToAsbWingSchema
from test.ehawk_workflow_helpers import _build_main_wing

# `client_and_db` fixture is provided by app/tests/conftest.py.
# The autouse `clean_cad_task_state` fixture (also in conftest.py) takes
# care of clearing the cad_service.tasks global before and after each test.


@pytest.fixture()
def client(client_and_db):
    """Backwards-compatible alias returning just the TestClient.

    The REST E2E test only needs the TestClient, not the SessionLocal. This
    thin wrapper keeps the test body unchanged while delegating to the
    shared conftest fixture.
    """
    test_client, _ = client_and_db
    Path("tmp/exports").mkdir(parents=True, exist_ok=True)
    yield test_client


def _wait_for_task_completion(client: TestClient, aeroplane_id: str, timeout_seconds: float = 240.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict | None = None

    while time.monotonic() < deadline:
        status_response = client.get(f"/aeroplanes/{aeroplane_id}/status")
        assert status_response.status_code == 200, status_response.text

        last_payload = status_response.json()
        status_value = last_payload["status"]
        if status_value == "SUCCESS":
            return last_payload
        if status_value == "FAILURE":
            pytest.fail(f"CAD task failed: {last_payload}")

        time.sleep(0.5)

    pytest.fail(f"Timed out waiting for CAD task completion. Last status payload: {last_payload}")


def _build_full_ehawk_asb_wing_schema() -> schemas.AsbWingSchema:
    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())
    wing_config = _build_main_wing(airfoil_path)
    return wingConfigToAsbWingSchema(
        wing_config=wing_config,
        wing_name="main_wing",
        scale=0.001,
    )


@pytest.mark.slow
@pytest.mark.requires_cadquery
@pytest.mark.requires_aerosandbox
def test_rest_stepwise_wing_vase_mode_step_export_workflow(client: TestClient):
    wing_name = "main_wing"
    asb_wing = _build_full_ehawk_asb_wing_schema()

    create_plane_response = client.post("/aeroplanes", params={"name": "eHawk REST workflow"})
    assert create_plane_response.status_code == 201, create_plane_response.text
    aeroplane_id = create_plane_response.json()["id"]

    wing_geometry_payload = {
        "name": wing_name,
        "symmetric": asb_wing.symmetric,
        "x_secs": [
            {
                "xyz_le": [float(value) for value in x_sec.xyz_le],
                "chord": float(x_sec.chord),
                "twist": float(x_sec.twist),
                "airfoil": str(x_sec.airfoil),
            }
            for x_sec in asb_wing.x_secs
        ],
    }

    create_wing_response = client.put(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}",
        json=wing_geometry_payload,
    )
    assert create_wing_response.status_code == 201, create_wing_response.text
    assert create_wing_response.json() == {
        "status": "created",
        "operation": "create_aeroplane_wing",
    }

    for cross_section_index, x_sec in enumerate(asb_wing.x_secs[:-1]):
        if x_sec.control_surface is not None:
            control_surface_patch = {
                "name": x_sec.control_surface.name,
                "hinge_point": float(x_sec.control_surface.hinge_point),
                "symmetric": bool(x_sec.control_surface.symmetric),
                "deflection": float(x_sec.control_surface.deflection),
            }
            control_surface_response = client.patch(
                f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface",
                json=control_surface_patch,
            )
            assert control_surface_response.status_code == 200, control_surface_response.text

        ted = x_sec.trailing_edge_device
        if ted is not None:
            ted_patch = {}
            if ted.rel_chord_tip is not None:
                ted_patch["rel_chord_tip"] = float(ted.rel_chord_tip)
            if ted.hinge_spacing is not None:
                ted_patch["hinge_spacing"] = float(ted.hinge_spacing)
            if ted.side_spacing_root is not None:
                ted_patch["side_spacing_root"] = float(ted.side_spacing_root)
            if ted.side_spacing_tip is not None:
                ted_patch["side_spacing_tip"] = float(ted.side_spacing_tip)
            if ted.servo_placement is not None:
                ted_patch["servo_placement"] = ted.servo_placement
            if ted.rel_chord_servo_position is not None:
                ted_patch["rel_chord_servo_position"] = float(ted.rel_chord_servo_position)
            if ted.rel_length_servo_position is not None:
                ted_patch["rel_length_servo_position"] = float(ted.rel_length_servo_position)
            if ted.positive_deflection_deg is not None:
                ted_patch["positive_deflection_deg"] = float(ted.positive_deflection_deg)
            if ted.negative_deflection_deg is not None:
                ted_patch["negative_deflection_deg"] = float(ted.negative_deflection_deg)
            if ted.trailing_edge_offset_factor is not None:
                ted_patch["trailing_edge_offset_factor"] = float(ted.trailing_edge_offset_factor)
            if ted.hinge_type is not None:
                ted_patch["hinge_type"] = ted.hinge_type

            if ted_patch:
                ted_response = client.patch(
                    f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/control_surface/cad_details",
                    json=ted_patch,
                )
                assert ted_response.status_code == 200, ted_response.text

        for spare in x_sec.spare_list or []:
            create_spar_response = client.post(
                f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{cross_section_index}/spars",
                json=spare.model_dump(),
            )
            assert create_spar_response.status_code == 201, create_spar_response.text
            assert create_spar_response.json() == {
                "status": "created",
                "operation": "create_wing_cross_section_spar",
            }

    wing_response = client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}")
    assert wing_response.status_code == 200, wing_response.text
    wing_payload = wing_response.json()
    assert len(wing_payload["x_secs"]) == len(asb_wing.x_secs)
    expected_control_surfaces = sum(1 for x_sec in asb_wing.x_secs[:-1] if x_sec.control_surface is not None)
    actual_control_surfaces = sum(1 for x_sec in wing_payload["x_secs"][:-1] if x_sec["control_surface"] is not None)
    assert actual_control_surfaces == expected_control_surfaces
    expected_spares = sum(len(x_sec.spare_list or []) for x_sec in asb_wing.x_secs[:-1])
    actual_spares = sum(len(x_sec["spare_list"] or []) for x_sec in wing_payload["x_secs"][:-1])
    assert actual_spares == expected_spares
    assert wing_payload["x_secs"][-1]["trailing_edge_device"] is None

    create_cad_response = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/vase_mode_wing/step",
        json={
            "printer_settings": {
                "layer_height": 0.24,
                "wall_thickness": 0.42,
                "rel_gap_wall_thickness": 0.075,
            },
            "servo_information": {},
        },
    )
    assert create_cad_response.status_code == 202, create_cad_response.text
    assert create_cad_response.json() == {
        "aeroplane_id": aeroplane_id,
        "href": f"/aeroplanes/{aeroplane_id}",
    }

    status_payload = _wait_for_task_completion(client, aeroplane_id=aeroplane_id, timeout_seconds=240.0)
    assert status_payload["result"] is not None
    assert "zipfile" in status_payload["result"]

    download_response = client.get(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/vase_mode_wing/step/zip",
    )
    assert download_response.status_code == 200, download_response.text
    download_payload = download_response.json()
    assert download_payload["filename"].endswith(".zip")
    assert download_payload["mime_type"] == "application/zip"

    static_zip_path = urlparse(download_payload["url"]).path
    static_zip_response = client.get(static_zip_path)
    assert static_zip_response.status_code == 200
    assert "zip" in static_zip_response.headers["content-type"]

    with ZipFile(io.BytesIO(static_zip_response.content)) as archive:
        entries = archive.namelist()

    assert entries, "Export ZIP should not be empty."
    assert "tmp/exports/output-wing.stp" in entries
    assert "tmp/exports/output-wing_main_wing.step" in entries
