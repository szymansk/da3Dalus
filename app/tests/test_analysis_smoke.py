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


def test_smoke_factories(client_and_db):
    """Verify all 7 smoke-plane factories create valid aeroplanes (sanity check)."""
    client, SessionLocal = client_and_db
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
