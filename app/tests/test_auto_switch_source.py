"""Tests for auto_switch_source parameter in update_calculated_value."""

from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, patch
from app.services.design_assumptions_service import update_calculated_value
from app.models.aeroplanemodel import DesignAssumptionModel


@pytest.fixture
def mock_db_with_assumption():
    """Create a mock DB session with an assumption row."""
    db = MagicMock()
    row = MagicMock(spec=DesignAssumptionModel)
    row.parameter_name = "cl_max"
    row.estimate_value = 1.4
    row.calculated_value = None
    row.calculated_source = None
    row.active_source = "ESTIMATE"
    row.divergence_pct = None
    row.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    row.id = 1
    row.aeroplane_id = 1

    db.query.return_value.filter.return_value.first.return_value = row
    return db, row


def test_auto_switch_on_first_calculated_value(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "cl_max", 1.35, "aerobuildup", auto_switch_source=True)

    assert row.calculated_value == 1.35
    assert row.active_source == "CALCULATED"


def test_no_auto_switch_when_already_has_calculated(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    row.calculated_value = 1.3  # already has a value
    row.active_source = "ESTIMATE"  # user chose estimate

    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "cl_max", 1.35, "aerobuildup", auto_switch_source=True)

    assert row.calculated_value == 1.35
    assert row.active_source == "ESTIMATE"  # not overridden


def test_no_auto_switch_for_design_choice(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    row.parameter_name = "g_limit"

    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "g_limit", 3.5, "computed", auto_switch_source=True)

    assert row.active_source == "ESTIMATE"  # design choices never auto-switch
