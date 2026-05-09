"""Smoke tests — verify analysis endpoints don't crash across aircraft configs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.tests.conftest import (
    seed_design_assumptions,
    seed_smoke_conventional_cross,
    seed_smoke_conventional_ttail,
    seed_smoke_flap_aileron_ttail,
    seed_smoke_flaperon_ttail,
    seed_smoke_flying_wing,
    seed_smoke_stabilator_ttail,
    seed_smoke_vtail_ruddervator,
)


@dataclass(frozen=True)
class SmokeConfig:
    name: str
    factory: Callable[[Session], AeroplaneModel]
    trim_ted: str


SMOKE_CONFIGS = [
    SmokeConfig("conventional-ttail", seed_smoke_conventional_ttail, "Elevator"),
    SmokeConfig("vtail-ruddervator", seed_smoke_vtail_ruddervator, "Ruddervator"),
    SmokeConfig("conventional-cross", seed_smoke_conventional_cross, "Elevator"),
    SmokeConfig("flying-wing", seed_smoke_flying_wing, "Elevon_0"),
    SmokeConfig("flaperon-ttail", seed_smoke_flaperon_ttail, "Elevator"),
    SmokeConfig("flap-aileron-ttail", seed_smoke_flap_aileron_ttail, "Elevator"),
    SmokeConfig("stabilator-ttail", seed_smoke_stabilator_ttail, "Aileron"),
]


@pytest.fixture(params=SMOKE_CONFIGS, ids=lambda c: c.name)
def smoke_plane(request, client_and_db):
    """Yield (client, aeroplane, config) for each aircraft configuration."""
    config: SmokeConfig = request.param
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = config.factory(session)
        seed_design_assumptions(session, aeroplane.id)
    finally:
        session.close()
    return client, aeroplane, config


@pytest.mark.integration
def test_smoke_factories(client_and_db):
    """Verify all 7 smoke-plane factories create valid aeroplanes (sanity check)."""
    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        for config in SMOKE_CONFIGS:
            aeroplane = config.factory(session)
            assert aeroplane.id is not None, f"{config.name}: aeroplane.id is None"
            assert aeroplane.name == f"smoke-{config.name}", (
                f"{config.name}: unexpected name {aeroplane.name!r}"
            )
    finally:
        session.close()


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_alpha_sweep(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/alpha_sweep",
        json={
            "alpha_start": -5,
            "alpha_end": 15,
            "alpha_num": 5,
            "velocity": 15.0,
            "altitude": 0,
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_strip_forces(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/strip_forces",
        json={"alpha": 5.0, "velocity": 15.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "surfaces" in data, f"{config.name}: missing 'surfaces' key"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_streamlines(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/streamlines",
        json={"alpha": 5.0, "velocity": 15.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_flight_envelope(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/flight-envelope/compute",
        json={},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_stability_summary(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/stability_summary/aerobuildup",
        json={"velocity": 15.0, "alpha": 5.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "neutral_point_x" in data, f"{config.name}: missing 'neutral_point_x'"
    assert "static_margin" in data, f"{config.name}: missing 'static_margin'"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_generate_default_ops(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-pointsets/generate-default",
        json={"replace_existing": True},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "operating_points" in data, f"{config.name}: missing 'operating_points'"


@pytest.mark.slow
@pytest.mark.requires_avl
def test_avl_trim(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-points/avl-trim",
        json={
            "operating_point": {
                "velocity": 15.0,
                "alpha": 5.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.15, 0.0, 0.0],
                "altitude": 0.0,
            },
            "trim_constraints": [
                {"variable": "alpha", "target": "PM", "value": 0.0},
            ],
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_aerobuildup_trim(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-points/aerobuildup-trim",
        json={
            "operating_point": {
                "velocity": 15.0,
                "alpha": 5.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.15, 0.0, 0.0],
                "altitude": 0.0,
            },
            "trim_variable": config.trim_ted,
            "target_coefficient": "Cm",
            "target_value": 0.0,
            "deflection_bounds": [-25.0, 25.0],
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_mass_sweep(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
        json={
            "masses_kg": [1.0, 1.5, 2.0],
            "velocity": 15.0,
            "altitude": 0,
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "points" in data, f"{config.name}: missing 'points'"


@pytest.mark.integration
def test_cg_comparison(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.get(f"/aeroplanes/{aeroplane.uuid}/cg_comparison")
    assert response.status_code == 200, f"{config.name}: {response.text}"
