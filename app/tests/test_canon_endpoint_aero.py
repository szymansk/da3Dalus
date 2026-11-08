"""Expert View backend (gh-1282): a fleet and a stored-aeroplane quantity through the endpoint.

Aero tier: real AeroSandbox and IPOPT. The fleet golden is the regression value of
``aero_kernel/tests/test_minimum_drag_speed_fleet.py`` (not a validation); the stored aeroplane's is
computed by hand from its geometry.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.aeroplanemodel import DesignAssumptionModel, WingModel, WingXSecModel
from app.tests.conftest import seed_integration_aeroplane

pytestmark = [pytest.mark.aero, pytest.mark.integration]

BRYAN_V_MD = 7.7115090  # m/s, regression golden of the kernel tests (straight body axis, #1358; was 7.6649267, before #1355 7.2306630, before #1346 7.4468700)


def test_bryan_minimum_drag_speed_through_the_endpoint(client_and_db):
    client, _ = client_and_db
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["minimum-drag-speed"]},
    )
    assert response.status_code == 200
    body = response.json()
    (quantity,) = body["quantities"]
    assert quantity["status"] == "ok"
    assert quantity["unit"] == "m/s"
    assert quantity["tool"] == "OPT"
    assert quantity["value"] == pytest.approx(BRYAN_V_MD, rel=1e-4)
    assert any(w["code"] == "reynolds_bubble_sensitive" for w in quantity["warnings"])
    assert body["input_errors"] == []
    assert {record["logger"].split(".")[0] for record in body["logs"]} == {"aero_kernel"}
    assert any(record["formula"] for record in body["logs"])
    assert all("/Users/" not in record["message"] for record in body["logs"])
    assert body["provenance"]["defaults_used"]


def test_wing_loading_of_a_stored_aeroplane_through_the_endpoint(client_and_db):
    # The main wing of the seeded aeroplane is a trapezoid from the centre line: chord 0.20 m at
    # the root, 0.15 m at the tip, 0.5 m half span, mirrored, so S_ref = 2 * 0.5 * 0.175 = 0.175 m^2
    # once its root twist (2 deg, which tilts the root chord out of the planform) is set to 0.
    # W/S = m g / S_ref with the mass assumption (1.1 kg) and standard gravity (canon default).
    client, session_factory = client_and_db
    with session_factory() as db:
        plane = seed_integration_aeroplane(db)
        root = (
            db.query(WingXSecModel)
            .join(WingModel)
            .filter(WingModel.aeroplane_id == plane.id, WingModel.name == "main_wing")
            .filter(WingXSecModel.sort_index == 0)
            .one()
        )
        root.twist = 0.0
        db.add(
            DesignAssumptionModel(
                aeroplane_id=plane.id,
                parameter_name="mass",
                estimate_value=1.1,
                active_source="ESTIMATE",
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        aeroplane_id = str(plane.uuid)
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"aeroplane": aeroplane_id}, "quantities": ["wing-loading"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input_errors"] == []
    (quantity,) = body["quantities"]
    assert quantity["status"] == "ok"
    assert quantity["unit"] == "N/m^2"
    assert quantity["value"] == pytest.approx(1.1 * 9.80665 / 0.175, rel=1e-6)
