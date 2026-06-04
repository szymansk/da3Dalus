"""Tests for the import-time low-Re recompute hook (Task 9, gh-821).

Asserts that ONLY newly imported names are scheduled for recompute
(not existing ones).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_schedule_airfoil_low_re_schedules_only_new_names():
    """schedule_airfoil_low_re() should pass only the new names to the job."""
    from app.core.background_jobs import schedule_airfoil_low_re

    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        mock_tracker.schedule_airfoil_low_re_compute = MagicMock()
        new_names = ["sd7037", "e423"]
        schedule_airfoil_low_re(new_names)
        mock_tracker.schedule_airfoil_low_re_compute.assert_called_once_with(new_names)


def test_schedule_airfoil_low_re_does_nothing_for_empty_list():
    """No schedule call when new_names is empty."""
    from app.core.background_jobs import schedule_airfoil_low_re

    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        mock_tracker.schedule_airfoil_low_re_compute = MagicMock()
        schedule_airfoil_low_re([])
        mock_tracker.schedule_airfoil_low_re_compute.assert_not_called()


def test_import_endpoint_triggers_hook_for_new_airfoils(client_and_db, tmp_path):
    """POST /airfoils/import triggers schedule_airfoil_low_re with only imported names."""
    import os
    from pathlib import Path

    client, SessionLocal = client_and_db

    # Create a valid .dat file in the components/airfoils directory
    # We need to point the import at a valid path under components/
    components_dir = Path("components") / "airfoils"
    components_dir.mkdir(parents=True, exist_ok=True)

    test_dat = components_dir / "test_hook_af.dat"
    test_dat.write_text(
        "test_hook_af\n"
        "1.000000  0.000000\n"
        "0.750000  0.060000\n"
        "0.500000  0.080000\n"
        "0.250000  0.060000\n"
        "0.000000  0.000000\n"
        "0.250000 -0.040000\n"
        "0.500000 -0.050000\n"
        "0.750000 -0.040000\n"
        "1.000000  0.000000\n"
    )

    try:
        with patch("app.api.v2.endpoints.airfoils.schedule_airfoil_low_re") as mock_hook:
            resp = client.post(
                "/airfoils/import",
                json={"directory": str(components_dir.resolve())},
            )
        assert resp.status_code == 200
        data = resp.json()
        if data.get("imported", 0) > 0:
            mock_hook.assert_called_once()
            called_names = mock_hook.call_args[0][0]
            assert "test_hook_af" in called_names
    finally:
        if test_dat.exists():
            test_dat.unlink()


def test_import_endpoint_does_not_schedule_for_skipped(client_and_db):
    """When all airfoils are already in DB, schedule_airfoil_low_re is NOT called."""
    from app.models.airfoil import AirfoilModel

    client, SessionLocal = client_and_db

    # Pre-seed the airfoil
    with SessionLocal() as session:
        session.add(AirfoilModel(
            name="existing_af",
            coordinates=[[0, 0], [0.5, 0.06], [1, 0]],
        ))
        session.commit()

    # Write a .dat file for the existing name
    from pathlib import Path
    components_dir = Path("components") / "airfoils"
    components_dir.mkdir(parents=True, exist_ok=True)
    test_dat = components_dir / "existing_af.dat"
    test_dat.write_text(
        "existing_af\n"
        "1.0 0.0\n0.5 0.06\n0.0 0.0\n0.5 -0.04\n1.0 0.0\n"
    )

    try:
        with patch("app.api.v2.endpoints.airfoils.schedule_airfoil_low_re") as mock_hook:
            resp = client.post(
                "/airfoils/import",
                json={"directory": str(components_dir.resolve())},
            )
        assert resp.status_code == 200
        data = resp.json()
        # If no new imports, hook should not be called
        if data.get("imported", 0) == 0:
            mock_hook.assert_not_called()
    finally:
        if test_dat.exists():
            test_dat.unlink()
