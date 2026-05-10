"""Tests for GeometryChanged → assumption recompute wiring."""

from unittest.mock import patch

from app.core.events import GeometryChanged


def test_geometry_changed_schedules_recompute():
    from app.services.invalidation_service import (
        _on_geometry_changed_recompute_assumptions,
    )

    event = GeometryChanged(aeroplane_id=42, source_model="WingModel")

    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        _on_geometry_changed_recompute_assumptions(event)

    mock_tracker.schedule_recompute_assumptions.assert_called_once_with(42)
