"""Tests for POST /aeroplanes/{id}/recompute — manual recompute trigger.

The recompute button on the workbench info-chip row and the tail-sizing
pencil-action both rely on this endpoint to enqueue the same background
job that AssumptionChanged / GeometryChanged events enqueue.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from app.tests.conftest import make_aeroplane


class TestRecomputeEndpoint:
    def test_returns_202_and_schedules_recompute(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            aeroplane_uuid = str(aeroplane.uuid)
            aeroplane_pk = aeroplane.id

        with patch(
            "app.core.background_jobs.job_tracker.schedule_recompute_assumptions"
        ) as mock_schedule:
            resp = client.post(f"/aeroplanes/{aeroplane_uuid}/recompute")

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] in {"debouncing", "computing", "idle"}
        mock_schedule.assert_called_once_with(aeroplane_pk)

    def test_returns_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(f"/aeroplanes/{uuid.uuid4()}/recompute")
        assert resp.status_code == 404

    def test_repeated_calls_reschedule(self, client_and_db):
        """Pressing the button twice must enqueue twice — debounce inside
        the job tracker collapses the work, but the endpoint must not
        silently drop the second call."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            aeroplane_uuid = str(aeroplane.uuid)

        with patch(
            "app.core.background_jobs.job_tracker.schedule_recompute_assumptions"
        ) as mock_schedule:
            client.post(f"/aeroplanes/{aeroplane_uuid}/recompute")
            client.post(f"/aeroplanes/{aeroplane_uuid}/recompute")

        assert mock_schedule.call_count == 2
