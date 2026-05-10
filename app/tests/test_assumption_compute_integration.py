"""Integration tests for the full assumption recompute pipeline (gh-465, Task 11).

Verifies:
1. The GeometryChanged handler delegates to job_tracker.schedule_recompute_assumptions
2. The recompute pipeline correctly emits AssumptionChanged(parameter_name="cg_x")
3. Idempotent: a second recompute with same inputs does NOT emit a duplicate event
"""
import pytest
from unittest.mock import patch
from types import SimpleNamespace

from app.core.events import (
    AssumptionChanged,
    GeometryChanged,
    event_bus,
)
from app.models.aeroplanemodel import DesignAssumptionModel
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


@pytest.mark.integration
def test_geometry_changed_handler_schedules_recompute():
    """Handler delegates to job_tracker.schedule_recompute_assumptions."""
    from app.services.invalidation_service import (
        _on_geometry_changed_recompute_assumptions,
    )

    # Patch the origin module — the handler does a lazy
    # `from app.core.background_jobs import job_tracker`.
    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        _on_geometry_changed_recompute_assumptions(
            GeometryChanged(aeroplane_id=42, source_model="WingModel")
        )

    mock_tracker.schedule_recompute_assumptions.assert_called_once_with(42)


@pytest.mark.integration
def test_recompute_publishes_assumption_changed_on_cg_change(client_and_db):
    """Full pipeline: recompute with seeded assumptions emits AssumptionChanged for cg_x."""
    from app.services.assumption_compute_service import recompute_assumptions

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    patches = [
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=SimpleNamespace(wings=[object()], xyz_ref=[0.08, 0.0, 0.0]),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.020),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=14.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=1.35,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0),
        ),
    ]

    try:
        for p in patches:
            p.start()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    finally:
        for p in patches:
            p.stop()
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    cg_events = [e for e in captured if e.parameter_name == "cg_x"]
    assert len(cg_events) == 1


@pytest.mark.integration
def test_recompute_does_not_publish_when_cg_unchanged(client_and_db):
    """Second recompute with same inputs does not emit a duplicate event."""
    from app.services.assumption_compute_service import recompute_assumptions

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    patches = [
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=SimpleNamespace(wings=[object()], xyz_ref=[0.08, 0.0, 0.0]),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.020),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=14.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=1.35,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0),
        ),
    ]

    try:
        for p in patches:
            p.start()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    finally:
        for p in patches:
            p.stop()
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    cg_events = [e for e in captured if e.parameter_name == "cg_x"]
    assert len(cg_events) == 1  # Only first call emitted; second was idempotent
