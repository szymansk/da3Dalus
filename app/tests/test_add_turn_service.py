"""gh-806: add-turn service creates a single trimmed coordinated-turn OP."""

import math

import pytest
from pydantic import ValidationError

from app.core.exceptions import ValidationError as DomainValidationError
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


def test_add_turn_rejects_aircraft_without_lateral_control(client_and_db, monkeypatch):
    """A turn needs roll or yaw control; without it, adding one must raise, not persist."""
    import app.services.add_turn_service as svc
    from app.tests.conftest import seed_smoke_conventional_ttail

    # Force "no lateral controls" regardless of the seeded aircraft.
    monkeypatch.setattr(
        "app.services.operating_point_generator_service._detect_control_capabilities",
        lambda *_a, **_k: {
            "has_roll_control": False,
            "has_yaw_control": False,
            "has_flap": False,
            "available_controls": [],
        },
    )
    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        with pytest.raises(DomainValidationError):
            svc.add_turn_operating_point(
                session, aeroplane.uuid, svc.AddTurnRequest(bank_angle_deg=30.0)
            )
    finally:
        session.close()


def _patch_solver(monkeypatch, *, point, caps=None):
    """Stub the AeroSandbox-heavy boundaries so the add-turn orchestration runs fast.

    Only the geometry build, capability detection and the Opti/AeroBuildup trim are
    stubbed; the real reference-speed/mass/CG loaders, feasibility guard, enrichment
    and DB persistence all execute, so this covers the service's actual wiring.
    """
    from types import SimpleNamespace

    caps = caps or {
        "has_roll_control": True,
        "has_yaw_control": True,
        "has_flap": False,
        "available_controls": ["[aileron]Aileron", "[rudder]Rudder", "[elevator]Elevator"],
    }
    monkeypatch.setattr(
        "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
        lambda plane_schema=None, **_k: SimpleNamespace(xyz_ref=[0.0, 0.0, 0.0]),
    )
    monkeypatch.setattr(
        "app.services.operating_point_generator_service._detect_control_capabilities",
        lambda *_a, **_k: caps,
    )
    monkeypatch.setattr(
        "app.services.operating_point_generator_service._trim_or_estimate_point",
        lambda **_k: point,
    )


def _stub_point(velocity):
    from app.schemas.aeroanalysisschema import OperatingPointStatus
    from app.services.operating_point_generator_service import TrimmedPoint

    return TrimmedPoint(
        name="turn_60",
        description="stub turn",
        config="clean",
        velocity=velocity,
        altitude=0.0,
        alpha_rad=0.05,
        beta_rad=0.0,
        p=0.0,
        q=0.7,
        r=0.4,
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={"[elevator]Elevator": 1.5, "[aileron]Aileron": 0.1, "[rudder]Rudder": 0.02},
        trim_score=0.0,
        trim_residuals={},
        trim_method="opti",
    )


def test_add_turn_persists_trimmed_point_and_flags_substall(client_and_db, monkeypatch):
    """Success path (no real solver): the service persists the trimmed point, runs the
    feasibility guard, and computes enrichment. A clearly sub-stall speed at 60 deg
    bank must be flagged LIMIT_REACHED + STALL_IN_TURN."""
    import app.services.add_turn_service as svc
    from app.schemas.aeroanalysisschema import OperatingPointStatus
    from app.tests.conftest import seed_smoke_conventional_ttail

    _patch_solver(monkeypatch, point=_stub_point(velocity=5.0))  # 5 m/s @60deg => below V_stall*sqrt(2)
    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        op = svc.add_turn_operating_point(
            session, aeroplane.uuid, svc.AddTurnRequest(bank_angle_deg=60.0, velocity=5.0)
        )
        session.flush()
        assert op.name == "turn_60"
        assert op.aircraft_id == aeroplane.id
        assert op.config == "clean"
        assert op.velocity == 5.0
        assert op.controls == {"[elevator]Elevator": 1.5, "[aileron]Aileron": 0.1, "[rudder]Rudder": 0.02}
        # feasibility guard ran inside the service:
        assert op.status == OperatingPointStatus.LIMIT_REACHED.value
        assert any("STALL_IN_TURN" in w for w in op.warnings)
        # enrichment ran (best-effort) and was stored:
        assert op.trim_enrichment is not None
    finally:
        session.close()


def test_add_turn_persists_even_if_enrichment_fails(client_and_db, monkeypatch):
    """Enrichment is best-effort: if it raises, the OP is still persisted (enrichment None)
    and the failure is logged — the OP must not be lost."""
    import app.services.add_turn_service as svc
    from app.tests.conftest import seed_smoke_conventional_ttail

    _patch_solver(monkeypatch, point=_stub_point(velocity=30.0))

    def _boom(*_a, **_k):
        raise RuntimeError("enrichment exploded")

    monkeypatch.setattr("app.services.trim_enrichment_service.compute_enrichment", _boom)
    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        op = svc.add_turn_operating_point(
            session, aeroplane.uuid, svc.AddTurnRequest(bank_angle_deg=60.0, velocity=30.0)
        )
        session.flush()
        assert op.name == "turn_60"
        assert op.trim_enrichment is None  # enrichment swallowed, OP still persisted
    finally:
        session.close()


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
