"""gh-806: default generation yields three trimmed turns with real rates."""

import pytest


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_default_set_has_three_turns_with_rates(client_and_db):
    from app.services.operating_point_generator_service import generate_default_set_for_aircraft
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        result = generate_default_set_for_aircraft(session, aeroplane.uuid, replace_existing=True)
    finally:
        session.close()

    names = {op.name for op in result.operating_points}
    assert {"turn_20", "turn_40", "turn_60"} <= names
    turns = [op for op in result.operating_points if op.name in {"turn_20", "turn_40", "turn_60"}]
    assert all(abs(op.r) > 0.0 for op in turns)
