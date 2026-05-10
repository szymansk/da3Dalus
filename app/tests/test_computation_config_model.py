import pytest
from app.models.computation_config import AircraftComputationConfigModel, COMPUTATION_CONFIG_DEFAULTS


def test_defaults_dict_has_all_columns():
    expected_keys = {
        "coarse_alpha_min_deg", "coarse_alpha_max_deg", "coarse_alpha_step_deg",
        "fine_alpha_margin_deg", "fine_alpha_step_deg", "fine_velocity_count",
        "debounce_seconds",
    }
    assert set(COMPUTATION_CONFIG_DEFAULTS.keys()) == expected_keys


def test_model_tablename():
    assert AircraftComputationConfigModel.__tablename__ == "aircraft_computation_config"
