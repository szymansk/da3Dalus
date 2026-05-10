import pytest
from app.schemas.computation_config import ComputationConfigRead, ComputationConfigWrite


def test_read_schema_has_all_fields():
    data = ComputationConfigRead(
        id=1,
        aeroplane_id=1,
        coarse_alpha_min_deg=-5.0,
        coarse_alpha_max_deg=25.0,
        coarse_alpha_step_deg=1.0,
        fine_alpha_margin_deg=5.0,
        fine_alpha_step_deg=0.5,
        fine_velocity_count=8,
        debounce_seconds=2.0,
    )
    assert data.coarse_alpha_step_deg == 1.0
    assert data.fine_velocity_count == 8


def test_write_schema_partial_update():
    data = ComputationConfigWrite(coarse_alpha_step_deg=0.5)
    assert data.coarse_alpha_step_deg == 0.5
    assert data.fine_velocity_count is None


def test_write_schema_validates_positive_step():
    with pytest.raises(ValueError):
        ComputationConfigWrite(coarse_alpha_step_deg=0.0)
