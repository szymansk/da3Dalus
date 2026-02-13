import pytest
from pydantic import ValidationError

from app.schemas.flight_profile import RCFlightProfileCreate


def valid_profile_payload() -> dict:
    return {
        "name": "rc_trainer_balanced",
        "type": "trainer",
        "environment": {"altitude_m": 0, "wind_mps": 0},
        "goals": {
            "cruise_speed_mps": 18,
            "max_level_speed_mps": 28,
            "min_speed_margin_vs_clean": 1.2,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.3,
            "target_turn_n": 2.0,
            "loiter_s": 480,
        },
        "handling": {
            "stability_preference": "stable",
            "roll_rate_target_dps": 120,
            "pitch_response": "smooth",
            "yaw_coupling_tolerance": "low",
        },
        "constraints": {"max_bank_deg": 60, "max_alpha_deg": 14, "max_beta_deg": 8},
    }


def test_schema_accepts_valid_minimum_profile():
    payload = valid_profile_payload()
    payload.pop("environment")
    payload.pop("handling")
    payload.pop("constraints")
    profile = RCFlightProfileCreate.model_validate(payload)
    assert profile.name == "rc_trainer_balanced"
    assert profile.environment.altitude_m == 0
    assert profile.handling.stability_preference == "stable"


def test_schema_rejects_negative_wind():
    payload = valid_profile_payload()
    payload["environment"]["wind_mps"] = -0.1
    with pytest.raises(ValidationError):
        RCFlightProfileCreate.model_validate(payload)


def test_schema_rejects_max_speed_below_cruise():
    payload = valid_profile_payload()
    payload["goals"]["max_level_speed_mps"] = 18
    with pytest.raises(ValidationError):
        RCFlightProfileCreate.model_validate(payload)


def test_schema_rejects_turn_n_above_bank_limit():
    payload = valid_profile_payload()
    payload["goals"]["target_turn_n"] = 3.0
    payload["constraints"]["max_bank_deg"] = 45
    with pytest.raises(ValidationError):
        RCFlightProfileCreate.model_validate(payload)
