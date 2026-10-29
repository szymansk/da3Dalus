"""Expert View backend (gh-1282, ADR 0030): the canon endpoints with the kernel boundary stubbed."""

from __future__ import annotations

import pytest
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    Provenance,
    QuantityResult,
    QuantityStatus,
    TimeBounds,
    Timing,
)

from fastapi.testclient import TestClient

from app.main import app as application
from app.services import canon_service


@pytest.fixture
def enveloped_client() -> TestClient:
    """A client of the real application, whose handlers turn errors into the one error envelope.

    Not entered as a context manager: the startup seeding of the database does not run.
    """
    return TestClient(application)


async def stub_kernel(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    quantity = QuantityResult(
        slug=request.quantities[0],
        unit="m/s",
        status=QuantityStatus.OK,
        value=7.5,
        tool="APP",
        application="a",
        timing=Timing.of(
            own=TimeBounds(lower=0.25, upper=0.75), before=TimeBounds(lower=1.0, upper=1.5)
        ),
    )
    return ComputeResult(quantities=(quantity,), provenance=Provenance(build_digest="test"))


class Facade:
    """Replaces the shared ``CachedKernel`` with the stub."""

    compute = staticmethod(stub_kernel)


def use_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer the cached path (the default) with the stub."""
    monkeypatch.setattr(canon_service, "KERNEL", Facade())


@pytest.mark.integration
def test_the_fleet_is_listed(client_and_db):
    client, _ = client_and_db
    response = client.get("/canon/fleet")
    assert response.status_code == 200
    ids = {entry["id"] for entry in response.json()}
    assert ids == {"bryan", "jaguar", "rv-7", "chekker", "wiesel", "belemnitos"}
    assert set(response.json()[0]) == {"id", "name", "mass_kg", "flap_deflections"}


@pytest.mark.integration
def test_a_quantity_is_computed(client_and_db, monkeypatch):
    use_kernel(monkeypatch)
    client, _ = client_and_db
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "quantities",
        "input_errors",
        "provenance",
        "verdicts",
        "needs_confirmation",
        "logs",
    }
    assert body["quantities"][0]["slug"] == "stall-speed"
    assert body["quantities"][0]["value"] == pytest.approx(7.5)
    assert body["needs_confirmation"] == []
    timing = body["quantities"][0]["timing"]
    assert timing["own_s"] == {"lower": pytest.approx(0.25), "upper": pytest.approx(0.75)}
    assert timing["before_s"] == {"lower": pytest.approx(1.0), "upper": pytest.approx(1.5)}
    assert timing["total_s"] == {"lower": pytest.approx(1.25), "upper": pytest.approx(2.25)}


@pytest.mark.integration
def test_an_unknown_aircraft_answers_with_the_error_envelope(enveloped_client, monkeypatch):
    use_kernel(monkeypatch)
    client = enveloped_client
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "nonexistent"}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.integration
def test_no_quantity_answers_with_the_error_envelope(enveloped_client):
    client = enveloped_client
    response = client.post(
        "/canon/compute", json={"aircraft": {"fleet": "bryan"}, "quantities": []}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_a_quantity_requested_twice_answers_with_the_error_envelope(enveloped_client):
    client = enveloped_client
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed", "stall-speed"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_a_fresh_request_recomputes_without_the_cache(client_and_db, monkeypatch):
    monkeypatch.setattr(canon_service, "compute", stub_kernel)
    monkeypatch.setattr(canon_service, "KERNEL", None)  # the facade must not be touched
    client, _ = client_and_db
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed"], "fresh": True},
    )
    assert response.status_code == 200
    assert response.json()["quantities"][0]["from_cache"] is False


def test_the_compute_request_documents_the_fresh_flag(enveloped_client):
    schema = enveloped_client.get("/openapi.json").json()["components"]["schemas"]
    fresh = schema["CanonComputeRequest"]["properties"]["fresh"]
    assert fresh["default"] is False
    assert "cache" in fresh["description"]
