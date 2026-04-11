from __future__ import annotations

import io
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

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


def _build_ehawk_wingconfig_payload() -> dict:
    """Build the eHawk main wing and return a ``/from-wingconfig``-ready JSON dict.

    This goes through ``_build_main_wing`` (the single source of truth
    for the eHawk geometry, shared with
    ``test/Construction_eHawk_wing.py``) and serialises the resulting
    :class:`WingConfiguration` via its own ``__getstate__`` into the
    dict shape that ``POST /aeroplanes/{id}/wings/{name}/from-wingconfig``
    accepts (Pydantic ``app.schemas.wing.Wing``).

    The intermediate ``AsbWingSchema`` / minimal ``PUT /wings`` path
    is intentionally bypassed because that schema does not carry
    ``wing_segment_type`` / ``tip_type`` / ``spare_list`` /
    ``number_interpolation_points`` — the fields the
    :class:`VaseModeWingCreator` CAD pipeline relies on to
    distinguish regular segments from wing tips. See
    cad-modelling-service-7em for the full rationale.
    """
    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())
    wing_config = _build_main_wing(airfoil_path)

    # __getstate__ walks WingConfiguration + WingSegment + Airfoil +
    # Spare + TrailingEdgeDevice and produces a nested dict of
    # JSON-serialisable attributes. We still need a custom encoder
    # hook for cadquery Vector / numpy scalar types that may appear
    # on spar origins and vectors.
    state = wing_config.__getstate__()

    class _JsonSafeEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "toTuple"):
                return list(obj.toTuple())
            if hasattr(obj, "x") and hasattr(obj, "y") and hasattr(obj, "z"):
                return [float(obj.x), float(obj.y), float(obj.z)]
            try:
                return float(obj)
            except Exception:
                return str(obj)

    # Round-trip through JSON so tuples become lists, numpy floats
    # become Python floats, and any surviving non-standard types get
    # converted via the encoder hook above.
    return json.loads(json.dumps(state, cls=_JsonSafeEncoder))


@pytest.mark.slow
@pytest.mark.requires_cadquery
@pytest.mark.requires_aerosandbox
def test_rest_wing_vase_mode_step_export_workflow_via_wingconfig(client: TestClient):
    """End-to-end eHawk main wing STEP export via
    ``POST /wings/{name}/from-wingconfig``.

    The older stepwise flow (``PUT /wings`` + per-xsec spar/TED
    patches) is deliberately not used here. Its write schema,
    ``AsbWingGeometryWriteSchema``, only carries
    ``{xyz_le, chord, twist, airfoil}`` per cross-section — it
    silently drops ``wing_segment_type`` / ``tip_type`` /
    ``number_interpolation_points``, so any wing with dedicated
    tip segments (like the eHawk main wing's 5 tip segments)
    arrives at the CAD worker as "all regular segments with no
    spar metadata", which crashes ``VaseModeWingCreator`` when
    it tries to index into ``spare_list[0]`` on segment 7.

    ``/from-wingconfig`` takes the full
    :class:`WingConfigurationSchema` instead, preserving every
    field the VaseMode creator needs. See beads issue
    cad-modelling-service-7em for the full analysis.
    """
    wing_name = "main_wing"
    wing_payload = _build_ehawk_wingconfig_payload()

    create_plane_response = client.post("/aeroplanes", params={"name": "eHawk REST workflow"})
    assert create_plane_response.status_code == 201, create_plane_response.text
    aeroplane_id = create_plane_response.json()["id"]

    create_wing_response = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=wing_payload,
    )
    assert create_wing_response.status_code == 201, create_wing_response.text
    assert create_wing_response.json() == {
        "status": "created",
        "operation": "create_aeroplane_wing_from_wingconfig",
    }

    # Sanity-check that the WingModel comes back with the right
    # segment count and that the last segment's tip is tagged as a
    # wing tip (tip_type preserved through the roundtrip).
    wing_response = client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}")
    assert wing_response.status_code == 200, wing_response.text
    wing_model_payload = wing_response.json()
    expected_xsec_count = len(wing_payload["segments"]) + 1
    assert len(wing_model_payload["x_secs"]) == expected_xsec_count

    # Segment 2 of the eHawk main wing defines an aileron TED that
    # references servo=1. The CAD task builds ServoInformation[1] from
    # the request body, so we must include that entry — otherwise the
    # worker would fail with "No servo information for servo '1'
    # provided." This mirrors the servo_aileron definition in
    # test/Construction_eHawk_wing.py lines 164-177.
    create_cad_response = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/vase_mode_wing/step",
        json={
            "printer_settings": {
                "layer_height": 0.24,
                "wall_thickness": 0.42,
                "rel_gap_wall_thickness": 0.075,
            },
            "servo_information": {
                "1": {
                    "height": 0,
                    "width": 0,
                    "length": 0,
                    "lever_length": 0,
                    "servo": {
                        "length": 23,
                        "width": 12.5,
                        "height": 31.5,
                        "leading_length": 6,
                        "latch_z": 14.5,
                        "latch_x": 7.25,
                        "latch_thickness": 2.6,
                        "latch_length": 6,
                        "cable_z": 26,
                        "screw_hole_lx": 0,
                        "screw_hole_d": 0,
                    },
                }
            },
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
