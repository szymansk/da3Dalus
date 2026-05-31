"""gh-806: default target set has three coordinated turns at 20/40/60 deg."""

import math

from app.services.operating_point_generator_service import (
    _build_target_definitions,
    _required_capabilities_for_target,
)

_PROFILE = {
    "goals": {"cruise_speed_mps": 20.0},
    "environment": {"altitude_m": 0.0},
}
_REFS = {"vs_clean": 12.0, "vs_to": 11.0, "vs_ldg": 10.0, "provenance": "polar"}


def _targets():
    return {t["name"]: t for t in _build_target_definitions(_PROFILE, _REFS)}


def test_turn_n2_replaced_by_three_banks():
    names = _targets()
    assert "turn_n2" not in names
    for bank in (20, 40, 60):
        assert f"turn_{bank}" in names


def test_turn_targets_carry_bank_and_load_factor():
    t = _targets()["turn_40"]
    assert t["bank_deg"] == 40.0
    assert t["n_target"] == round(1.0 / math.cos(math.radians(40.0)), 4)


def test_turn_targets_need_roll_or_yaw_control():
    assert _required_capabilities_for_target("turn_20") == {"has_roll_control|has_yaw_control"}
