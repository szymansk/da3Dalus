"""Expert View backend (gh-1282): one fleet quantity through the endpoint with the real kernel.

Aero tier: real AeroSandbox and IPOPT. The golden is the regression value of
``aero_kernel/tests/test_minimum_drag_speed_fleet.py`` (not a validation).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.aero, pytest.mark.integration]

BRYAN_V_MD = 7.4468700  # m/s, regression golden of the kernel tests


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
