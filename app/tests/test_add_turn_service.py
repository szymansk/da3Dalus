"""gh-806: add-turn service creates a single trimmed coordinated-turn OP."""

import math

import pytest
from pydantic import ValidationError

from app.schemas.aeroanalysisschema import AddTurnRequest


class TestAddTurnRequest:
    def test_defaults(self):
        req = AddTurnRequest(bank_angle_deg=30.0)
        assert req.bank_angle_deg == 30.0
        assert req.velocity is None and req.altitude is None and req.name is None

    @pytest.mark.parametrize("bad", [0.0, -5.0, 90.0, 95.0])
    def test_bank_bounds(self, bad):
        with pytest.raises(ValidationError):
            AddTurnRequest(bank_angle_deg=bad)


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_add_turn_creates_op(client_and_db):
    from app.services.add_turn_service import add_turn_operating_point
    from app.tests.conftest import seed_smoke_conventional_ttail

    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        op = add_turn_operating_point(
            session, aeroplane.uuid, AddTurnRequest(bank_angle_deg=30.0)
        )
        session.flush()
        assert op.name == "turn_30"
        assert op.r is not None and abs(op.r) > 0.0
        assert op.aircraft_id == aeroplane.id
    finally:
        session.close()
