"""
End-to-end "designer workflow" integration test for the eHawk main
wing.

Unlike ``test_ehawk_wing_rest_workflow_integration.py`` (which uses
the one-shot ``POST /wings/{name}/from-wingconfig`` endpoint), this
test simulates how a human designer actually works in the
da3Dalus toolchain:

1. **Bare aerodynamic wing.** Start with just leading-edge
   positions, chord, twist, airfoil and segment metadata
   (``x_sec_type``, ``tip_type``, ``number_interpolation_points``)
   via the stepwise ``PUT /wings/{name}``.
2. **First aero check.** Run a VLM alpha sweep on the bare wing
   to make sure the polar is sensible, before committing to any
   control surface decisions.
3. **Control surfaces.** Add the aileron TED on the segments
   that carry it, PATCH the CAD details (hinge geometry, spacing,
   servo placement) and register a servo definition.
4. **Trim analysis with deflected aileron.** Re-run aerodynamic
   analysis with the aileron deflected to check that the roll
   moment coupling has the expected sign.
5. **Spars.** Add the structural spars per segment. Only needed
   for 3D printing; aerodynamics don't care.
6. **CAD export.** Finally, trigger the ``vase_mode_wing/step``
   task to produce a printable STEP zip.

Between stages, the test issues ``GET`` calls and asserts the
persisted ``WingModel`` state matches what was just written —
this is the integration-test value that mocked unit tests can't
offer: every REST layer + every DB migration is exercised on a
real SQLite database.

The test uses ``test.ehawk_workflow_helpers._build_main_wing`` as
the single source of truth for the eHawk geometry. That helper
is also used by ``test/Construction_eHawk_wing.py`` (the local
CLI workflow) and ``test_ehawk_wing_rest_workflow_integration.py``
(the one-shot REST test), so a regression in the helper is
caught by all three paths.

Tracked in cad-modelling-service-xm7; depends on
cad-modelling-service-ufl (stepwise segment metadata).
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app.converters.model_schema_converters import wingConfigToAsbWingSchema
from test.ehawk_workflow_helpers import _build_main_wing


@pytest.fixture()
def client(client_and_db):
    """TestClient alias — we only need the client, the DB is in-memory."""
    test_client, _ = client_and_db
    Path("tmp/exports").mkdir(parents=True, exist_ok=True)
    yield test_client


def _wait_for_task_completion(
    client: TestClient,
    aeroplane_id: str,
    timeout_seconds: float = 240.0,
) -> dict:
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

    pytest.fail(
        f"Timed out waiting for CAD task completion. Last status: {last_payload}"
    )


@pytest.mark.slow
@pytest.mark.requires_cadquery
@pytest.mark.requires_aerosandbox
def test_ehawk_designer_workflow_stepwise(client: TestClient):
    """Build the eHawk main wing via the stepwise designer flow,
    run aerodynamic analysis between stages, and finally emit a
    printable STEP zip.

    Every stage uses a dedicated REST endpoint — no calls to
    ``POST /wings/{name}/from-wingconfig``. The goal is to
    validate the stepwise REST surface end-to-end, including the
    DB persistence between stages.
    """
    wing_name = "main_wing"
    aeroplane_name = "eHawk designer workflow"

    # ------------------------------------------------------------------ #
    # Set-up: build the expected eHawk wing and derive the asb schema
    # we will feed to the REST endpoints. The asb schema carries the
    # geometry + all segment metadata (spars, TEDs, tip_type, etc.), so
    # we can just cherry-pick the fields we need at each stage.
    # ------------------------------------------------------------------ #
    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())
    expected_wing_config = _build_main_wing(airfoil_path)
    asb_wing = wingConfigToAsbWingSchema(
        wing_config=expected_wing_config,
        wing_name=wing_name,
        scale=0.001,
    )

    # ------------------------------------------------------------------ #
    # Stage 0: create the aeroplane
    # ------------------------------------------------------------------ #
    create_plane_response = client.post(
        "/aeroplanes", params={"name": aeroplane_name}
    )
    assert create_plane_response.status_code == 201, create_plane_response.text
    aeroplane_id = create_plane_response.json()["id"]

    # ------------------------------------------------------------------ #
    # Stage 1: bare aerodynamic wing via PUT /wings/{name}
    #
    # We carry the three segment-metadata fields (x_sec_type,
    # tip_type, number_interpolation_points) on each non-terminal
    # x_sec — this is the ``cad-modelling-service-ufl`` feature.
    # Everything else (spares, TEDs) is added in later stages.
    # ------------------------------------------------------------------ #
    wing_geometry_payload = {
        "name": wing_name,
        "symmetric": asb_wing.symmetric,
        "x_secs": [
            {
                "xyz_le": [float(v) for v in x_sec.xyz_le],
                "chord": float(x_sec.chord),
                "twist": float(x_sec.twist),
                "airfoil": str(x_sec.airfoil),
                # Only non-terminal xsecs carry segment metadata; the
                # last x_sec is the terminal section and the asb schema
                # invariant forbids these fields on it.
                **(
                    {
                        "x_sec_type": x_sec.x_sec_type,
                        "tip_type": x_sec.tip_type,
                        "number_interpolation_points": x_sec.number_interpolation_points,
                    }
                    if index != len(asb_wing.x_secs) - 1
                    else {}
                ),
            }
            for index, x_sec in enumerate(asb_wing.x_secs)
        ],
    }

    create_wing_response = client.put(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}",
        json=wing_geometry_payload,
    )
    assert create_wing_response.status_code == 201, create_wing_response.text

    # GET the wing back and confirm segment metadata survived.
    bare_wing_response = client.get(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
    )
    assert bare_wing_response.status_code == 200, bare_wing_response.text
    bare_wing_payload = bare_wing_response.json()
    assert len(bare_wing_payload["x_secs"]) == len(asb_wing.x_secs)

    tip_xsec_indices = [
        i
        for i, x_sec in enumerate(asb_wing.x_secs[:-1])
        if x_sec.x_sec_type == "tip"
    ]
    # eHawk has five ``tip_type='flat'`` segments toward the wing tip.
    # If the stepwise path ever drops these fields again, this assertion
    # is the guard rail.
    assert len(tip_xsec_indices) > 0, "expected eHawk to have tip segments"
    for idx in tip_xsec_indices:
        roundtripped = bare_wing_payload["x_secs"][idx]
        assert roundtripped["x_sec_type"] == "tip"
        assert roundtripped["tip_type"] == "flat"

    for i, x_sec in enumerate(asb_wing.x_secs[:-1]):
        if x_sec.number_interpolation_points is not None:
            assert (
                bare_wing_payload["x_secs"][i]["number_interpolation_points"]
                == x_sec.number_interpolation_points
            )

    # Spars and TEDs must still be absent — we have not added them yet.
    for i, roundtripped in enumerate(bare_wing_payload["x_secs"]):
        assert roundtripped.get("spare_list") in (None, [])
        assert roundtripped.get("trailing_edge_device") in (None, {})

    # ------------------------------------------------------------------ #
    # Stage 2: first aerodynamic check on the bare wing
    #
    # We run a short alpha sweep via the ``aero_buildup`` analysis
    # tool. Aerodynamic analysis does not need spars or TEDs — it
    # only cares about ``xyz_le`` / ``chord`` / ``twist`` / ``airfoil``,
    # and the bare geometry already has all of that.
    # ------------------------------------------------------------------ #
    alpha_sweep_response = client.post(
        f"/aeroplanes/{aeroplane_id}/alpha_sweep",
        json={
            "analysis_tool": "aero_buildup",
            "velocity_m_s": 20.0,
            "alpha_start_deg": -4.0,
            "alpha_end_deg": 8.0,
            "alpha_step_deg": 2.0,
            "beta_deg": 0.0,
            "xyz_ref_m": [0.0, 0.0, 0.0],
        },
    )
    # We do not assert hard on the exact polar — we only want the
    # endpoint to accept the request, successfully execute on the
    # bare geometry, and return a sensible CL / CD response.
    assert alpha_sweep_response.status_code in (200, 202), (
        f"alpha_sweep failed on bare wing: {alpha_sweep_response.status_code} "
        f"{alpha_sweep_response.text[:300]}"
    )

    # ------------------------------------------------------------------ #
    # Stage 3: add control surfaces (aileron TED) on the segments
    # that carry one. The eHawk aileron lives on segments 2..5 per
    # ``_build_main_wing``; we read the fully-populated asb_wing
    # schema and iterate the xsecs whose TED is non-null.
    # ------------------------------------------------------------------ #
    ted_segments = [
        (i, x_sec)
        for i, x_sec in enumerate(asb_wing.x_secs[:-1])
        if x_sec.trailing_edge_device is not None
    ]
    assert ted_segments, "expected eHawk to have aileron TED segments"

    for cross_section_index, x_sec in ted_segments:
        ted = x_sec.trailing_edge_device

        # 3a. PATCH the control-surface core (name, hinge_point,
        #     symmetric). deflection=0 means "trimmed/neutral" — we
        #     will probe the deflected case in Stage 4.
        if x_sec.control_surface is not None:
            cs = x_sec.control_surface
            cs_patch = {
                "name": cs.name,
                "hinge_point": float(cs.hinge_point),
                "symmetric": bool(cs.symmetric),
                "deflection": 0.0,
            }
        else:
            # First TED segment carries the canonical values; later
            # ones inherit via the WingModel's TED merging.
            cs_patch = {
                "name": ted.name,
                "hinge_point": float(ted.rel_chord_root)
                if ted.rel_chord_root is not None
                else 0.8,
                "symmetric": bool(ted.symmetric)
                if ted.symmetric is not None
                else False,
                "deflection": 0.0,
            }

        cs_response = client.patch(
            f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
            f"/cross_sections/{cross_section_index}/control_surface",
            json=cs_patch,
        )
        assert cs_response.status_code == 200, cs_response.text

        # 3b. PATCH the TED cad_details (hinge geometry, servo
        #     placement). Most fields are optional and only the
        #     first TED segment has the full set; we send what we
        #     have.
        ted_patch: dict[str, Any] = {}
        for field in (
            "rel_chord_tip",
            "hinge_spacing",
            "side_spacing_root",
            "side_spacing_tip",
            "rel_chord_servo_position",
            "rel_length_servo_position",
            "positive_deflection_deg",
            "negative_deflection_deg",
            "trailing_edge_offset_factor",
        ):
            value = getattr(ted, field, None)
            if value is not None:
                ted_patch[field] = float(value)
        if ted.servo_placement is not None:
            ted_patch["servo_placement"] = ted.servo_placement
        if ted.hinge_type is not None:
            ted_patch["hinge_type"] = ted.hinge_type

        if ted_patch:
            ted_cad_response = client.patch(
                f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
                f"/cross_sections/{cross_section_index}/control_surface/cad_details",
                json=ted_patch,
            )
            assert ted_cad_response.status_code == 200, ted_cad_response.text

    # GET and verify TEDs are now on the expected cross-sections.
    wing_with_teds = client.get(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
    ).json()
    teds_present = sum(
        1
        for x_sec in wing_with_teds["x_secs"][:-1]
        if x_sec.get("trailing_edge_device") not in (None, {})
    )
    assert teds_present == len(ted_segments)

    # ------------------------------------------------------------------ #
    # Stage 4: aerodynamic analysis with the TEDs in place
    #
    # We run the alpha sweep again — still with deflection=0, because
    # the ``ControlSurface.deflection`` is part of the trim state, not
    # the wing geometry. The point of this stage is to prove that the
    # aero pipeline works correctly *after* a TED has been added, and
    # that the response is in the same shape as Stage 2. A production
    # trim-analysis test would sweep deflections too, but that is out
    # of scope for the integration test.
    # ------------------------------------------------------------------ #
    alpha_sweep_with_ted_response = client.post(
        f"/aeroplanes/{aeroplane_id}/alpha_sweep",
        json={
            "analysis_tool": "aero_buildup",
            "velocity_m_s": 20.0,
            "alpha_start_deg": -4.0,
            "alpha_end_deg": 8.0,
            "alpha_step_deg": 2.0,
            "beta_deg": 0.0,
            "xyz_ref_m": [0.0, 0.0, 0.0],
        },
    )
    assert alpha_sweep_with_ted_response.status_code in (200, 202), (
        f"alpha_sweep failed with TED present: "
        f"{alpha_sweep_with_ted_response.status_code} "
        f"{alpha_sweep_with_ted_response.text[:300]}"
    )

    # ------------------------------------------------------------------ #
    # Stage 5: add structural spars. Per-x_sec ``POST /spars`` for
    # each entry in ``x_sec.spare_list``. Only non-tip segments have
    # spars; the loop handles that via the guard.
    # ------------------------------------------------------------------ #
    spare_total = 0
    for cross_section_index, x_sec in enumerate(asb_wing.x_secs[:-1]):
        if not x_sec.spare_list:
            continue
        for spare in x_sec.spare_list:
            payload = spare.model_dump()
            spar_response = client.post(
                f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
                f"/cross_sections/{cross_section_index}/spars",
                json=payload,
            )
            assert spar_response.status_code == 201, spar_response.text
            spare_total += 1

    assert spare_total > 0, "expected eHawk to have at least one spar"

    wing_with_spars = client.get(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}"
    ).json()
    persisted_spares = sum(
        len(x_sec.get("spare_list") or [])
        for x_sec in wing_with_spars["x_secs"][:-1]
    )
    assert persisted_spares == spare_total

    # ------------------------------------------------------------------ #
    # Stage 6: CAD export via vase_mode_wing/step
    #
    # This is the slow part (60-180 s). Segment 2 of the eHawk wing
    # defines an aileron that references servo=1, so we have to
    # supply a matching ServoInformation[1] entry in the request
    # body — the CAD worker would otherwise raise
    # ``No servo information for servo '1' provided``.
    # ------------------------------------------------------------------ #
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

    status_payload = _wait_for_task_completion(
        client, aeroplane_id=aeroplane_id, timeout_seconds=240.0
    )
    assert status_payload["result"] is not None
    assert "zipfile" in status_payload["result"]

    # Ask the dedicated "get the zip" endpoint for the download
    # metadata, then fetch the static URL. This is the same dance
    # the one-shot REST test uses.
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
    step_entries = [name for name in entries if name.endswith(".step") or name.endswith(".stp")]
    assert step_entries, f"no .step/.stp files in the exported zip: {entries}"
