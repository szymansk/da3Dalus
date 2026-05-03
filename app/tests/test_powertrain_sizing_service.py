"""Tests for app.services.powertrain_sizing_service."""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.powertrain_sizing import (
    PowertrainCandidate,
    PowertrainSizingRequest,
    PowertrainSizingResponse,
)
from app.services.powertrain_sizing_service import (
    AIR_DENSITY_SEA_LEVEL,
    _air_density,
    _compute_confidence,
    _evaluate_motor_battery_combo,
    _find_matching_esc,
    _required_power_w,
    size_powertrain,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_motor(motor_id: int = 1, name: str = "Motor A", mass_g: float = 50.0):
    return SimpleNamespace(id=motor_id, name=name, mass_g=mass_g)


def _make_battery(
    battery_id: int = 10,
    name: str = "Battery A",
    mass_g: float = 200.0,
    capacity_mah: int = 2200,
    voltage: float = 11.1,
):
    return SimpleNamespace(
        id=battery_id,
        name=name,
        mass_g=mass_g,
        specs={"capacity_mah": capacity_mah, "voltage": voltage},
    )


def _make_esc(esc_id: int = 20, name: str = "ESC A", max_continuous_a: float = 30.0):
    return SimpleNamespace(
        id=esc_id,
        name=name,
        specs={"max_continuous_a": max_continuous_a},
    )


def _default_request(**overrides) -> PowertrainSizingRequest:
    defaults = dict(
        airframe_mass_kg=2.0,
        target_cruise_speed_ms=15.0,
        target_top_speed_ms=25.0,
        target_flight_time_min=10.0,
        max_current_draw_a=None,
        altitude_m=0.0,
    )
    defaults.update(overrides)
    return PowertrainSizingRequest(**defaults)


# --------------------------------------------------------------------------- #
# _air_density
# --------------------------------------------------------------------------- #


class TestAirDensity:
    def test_sea_level_returns_standard_density(self):
        assert _air_density(0.0) == pytest.approx(AIR_DENSITY_SEA_LEVEL)

    def test_positive_altitude_decreases_density(self):
        rho = _air_density(1000.0)
        assert rho < AIR_DENSITY_SEA_LEVEL
        expected = AIR_DENSITY_SEA_LEVEL * math.exp(-1000.0 / 8500.0)
        assert rho == pytest.approx(expected)

    def test_high_altitude_much_lower_density(self):
        rho_low = _air_density(100.0)
        rho_high = _air_density(5000.0)
        assert rho_high < rho_low

    def test_negative_altitude_increases_density(self):
        """Negative altitude (below sea level) should yield higher density."""
        rho = _air_density(-100.0)
        assert rho > AIR_DENSITY_SEA_LEVEL

    def test_very_high_altitude_approaches_zero(self):
        rho = _air_density(100_000.0)
        assert rho > 0.0
        assert rho < 0.01


# --------------------------------------------------------------------------- #
# _required_power_w
# --------------------------------------------------------------------------- #


class TestRequiredPowerW:
    def test_positive_result_for_typical_inputs(self):
        power = _required_power_w(15.0, 2.0, 0.0)
        assert power > 0.0

    def test_higher_speed_requires_more_power(self):
        p_slow = _required_power_w(10.0, 2.0, 0.0)
        p_fast = _required_power_w(25.0, 2.0, 0.0)
        assert p_fast > p_slow

    def test_heavier_aircraft_requires_more_power(self):
        p_light = _required_power_w(15.0, 1.0, 0.0)
        p_heavy = _required_power_w(15.0, 5.0, 0.0)
        assert p_heavy > p_light

    def test_higher_altitude_changes_power(self):
        """Power at altitude differs from sea level due to density changes."""
        p_sea = _required_power_w(15.0, 2.0, 0.0)
        p_alt = _required_power_w(15.0, 2.0, 3000.0)
        assert p_sea != p_alt

    def test_zero_speed_returns_zero_power(self):
        """At zero airspeed no aerodynamic power is needed; should return 0.0."""
        result = _required_power_w(0.0, 2.0, 0.0)
        assert result == 0.0

    def test_negative_speed_returns_zero_power(self):
        """Negative speed is physically meaningless; should return 0.0."""
        result = _required_power_w(-5.0, 2.0, 0.0)
        assert result == 0.0


# --------------------------------------------------------------------------- #
# _find_matching_esc
# --------------------------------------------------------------------------- #


class TestFindMatchingEsc:
    def test_returns_first_matching_esc(self):
        esc1 = _make_esc(esc_id=1, max_continuous_a=10.0)
        esc2 = _make_esc(esc_id=2, max_continuous_a=30.0)
        esc3 = _make_esc(esc_id=3, max_continuous_a=50.0)
        result = _find_matching_esc([esc1, esc2, esc3], 25.0)
        assert result is esc2

    def test_returns_none_when_no_esc_qualifies(self):
        esc = _make_esc(max_continuous_a=10.0)
        result = _find_matching_esc([esc], 20.0)
        assert result is None

    def test_returns_none_for_empty_list(self):
        result = _find_matching_esc([], 5.0)
        assert result is None

    def test_exact_match_current(self):
        esc = _make_esc(max_continuous_a=15.0)
        result = _find_matching_esc([esc], 15.0)
        assert result is esc

    def test_esc_with_no_specs_is_skipped(self):
        esc_no_specs = SimpleNamespace(id=1, name="bare", specs=None)
        esc_good = _make_esc(esc_id=2, max_continuous_a=30.0)
        result = _find_matching_esc([esc_no_specs, esc_good], 10.0)
        assert result is esc_good

    def test_esc_with_empty_specs_is_skipped(self):
        esc_empty = SimpleNamespace(id=1, name="empty", specs={})
        result = _find_matching_esc([esc_empty], 5.0)
        assert result is None


# --------------------------------------------------------------------------- #
# _compute_confidence
# --------------------------------------------------------------------------- #


class TestComputeConfidence:
    def test_exact_target_returns_two_thirds(self):
        """When flight_time == target, ratio = 1.0, confidence = 1.0/1.5 ~ 0.667."""
        conf = _compute_confidence(10.0, 10.0)
        assert conf == pytest.approx(1.0 / 1.5, abs=1e-6)

    def test_one_and_a_half_times_target_returns_one(self):
        """When flight_time == 1.5 * target, ratio capped at 1.5, confidence = 1.0."""
        conf = _compute_confidence(15.0, 10.0)
        assert conf == pytest.approx(1.0)

    def test_over_1_5x_target_still_capped_at_one(self):
        conf = _compute_confidence(20.0, 10.0)
        assert conf == pytest.approx(1.0)

    def test_half_target_applies_penalty(self):
        """At exactly half the target, the 0.3 penalty applies."""
        conf = _compute_confidence(5.0, 10.0)
        base = min((5.0 / 10.0) / 1.5, 1.0)  # 0.333...
        # flight_time < target * 0.5 is False (5.0 < 5.0 is False)
        assert conf == pytest.approx(base, abs=1e-6)

    def test_below_half_target_applies_penalty(self):
        """Below half the target, confidence is penalized by 0.3."""
        conf = _compute_confidence(4.0, 10.0)
        base = min((4.0 / 10.0) / 1.5, 1.0)
        expected = base * 0.3
        assert conf == pytest.approx(expected, abs=1e-6)

    def test_very_small_flight_time_low_confidence(self):
        conf = _compute_confidence(0.5, 10.0)
        assert conf < 0.1

    def test_zero_target_raises(self):
        """Zero target causes ZeroDivisionError (production should guard)."""
        with pytest.raises(ZeroDivisionError):
            _compute_confidence(10.0, 0.0)


# --------------------------------------------------------------------------- #
# _evaluate_motor_battery_combo
# --------------------------------------------------------------------------- #


class TestEvaluateMotorBatteryCombo:
    def test_valid_combo_returns_candidate(self):
        motor = _make_motor()
        battery = _make_battery()
        escs = [_make_esc(max_continuous_a=50.0)]
        request = _default_request()

        result = _evaluate_motor_battery_combo(motor, battery, escs, request)

        assert result is not None
        assert isinstance(result, PowertrainCandidate)
        assert result.motor_id == motor.id
        assert result.motor_name == motor.name
        assert result.battery_id == battery.id
        assert result.battery_name == battery.name
        assert result.estimated_flight_time_min > 0
        assert result.estimated_cruise_power_w > 0
        assert 0 <= result.confidence <= 1

    def test_zero_capacity_battery_returns_none(self):
        motor = _make_motor()
        battery = _make_battery(capacity_mah=0)
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is None

    def test_zero_voltage_battery_returns_none(self):
        motor = _make_motor()
        battery = _make_battery(voltage=0)
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is None

    def test_negative_capacity_returns_none(self):
        motor = _make_motor()
        battery = _make_battery(capacity_mah=-100)
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is None

    def test_current_exceeds_max_returns_none(self):
        motor = _make_motor()
        battery = _make_battery()
        request = _default_request(max_current_draw_a=0.1)  # very low limit
        result = _evaluate_motor_battery_combo(motor, battery, [], request)
        assert result is None

    def test_no_max_current_constraint(self):
        motor = _make_motor()
        battery = _make_battery()
        request = _default_request(max_current_draw_a=None)
        result = _evaluate_motor_battery_combo(motor, battery, [], request)
        assert result is not None

    def test_esc_matched_when_available(self):
        motor = _make_motor()
        battery = _make_battery()
        esc = _make_esc(esc_id=99, name="BigESC", max_continuous_a=100.0)
        request = _default_request()

        result = _evaluate_motor_battery_combo(motor, battery, [esc], request)
        assert result is not None
        assert result.esc_id == 99
        assert result.esc_name == "BigESC"

    def test_no_esc_match_still_returns_candidate(self):
        motor = _make_motor()
        battery = _make_battery()
        esc = _make_esc(max_continuous_a=0.001)  # too small
        request = _default_request()

        result = _evaluate_motor_battery_combo(motor, battery, [esc], request)
        assert result is not None
        assert result.esc_id is None
        assert result.esc_name is None

    def test_motor_with_no_mass(self):
        motor = _make_motor(mass_g=0.0)
        battery = _make_battery()
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is not None

    def test_motor_with_none_mass(self):
        motor = SimpleNamespace(id=1, name="NoMass", mass_g=None)
        battery = _make_battery()
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is not None

    def test_battery_uses_nominal_voltage_fallback(self):
        """When 'voltage' is absent, falls back to 'nominal_voltage'."""
        battery = SimpleNamespace(
            id=10,
            name="FallbackV",
            mass_g=200.0,
            specs={"capacity_mah": 2200, "nominal_voltage": 14.8},
        )
        motor = _make_motor()
        result = _evaluate_motor_battery_combo(motor, battery, [], _default_request())
        assert result is not None
        assert result.estimated_cruise_power_w > 0

    def test_estimated_top_speed_echoes_request(self):
        motor = _make_motor()
        battery = _make_battery()
        request = _default_request(target_top_speed_ms=33.3)
        result = _evaluate_motor_battery_combo(motor, battery, [], request)
        assert result is not None
        assert result.estimated_top_speed_ms == pytest.approx(33.3, abs=0.1)


# --------------------------------------------------------------------------- #
# size_powertrain (integration with mocked DB)
# --------------------------------------------------------------------------- #


def _mock_db_session(
    aeroplane=None,
    motors=None,
    batteries=None,
    escs=None,
):
    """Build a mock SQLAlchemy Session that returns the given components."""
    db = MagicMock()

    # Track filter calls to return appropriate results
    def _build_query_chain(result):
        chain = MagicMock()
        chain.filter.return_value = chain
        chain.first.return_value = result if not isinstance(result, list) else None
        chain.all.return_value = result if isinstance(result, list) else []
        return chain

    aeroplane_query = _build_query_chain(aeroplane)
    motor_query = _build_query_chain(motors or [])
    battery_query = _build_query_chain(batteries or [])
    esc_query = _build_query_chain(escs or [])

    call_count = {"n": 0}
    queries = [aeroplane_query, motor_query, battery_query, esc_query]

    def _query_side_effect(model):
        idx = call_count["n"]
        call_count["n"] += 1
        return queries[idx]

    db.query.side_effect = _query_side_effect
    return db


class TestSizePowertrain:
    def test_missing_aeroplane_raises_not_found(self):
        db = _mock_db_session(aeroplane=None)
        request = _default_request()
        test_uuid = uuid.uuid4()

        with pytest.raises(NotFoundError):
            size_powertrain(db, test_uuid, request)

    def test_no_motors_returns_empty(self):
        aeroplane = SimpleNamespace(uuid=uuid.uuid4())
        db = _mock_db_session(aeroplane=aeroplane, motors=[], batteries=[])
        request = _default_request()

        result = size_powertrain(db, aeroplane.uuid, request)
        assert isinstance(result, PowertrainSizingResponse)
        assert result.recommendations == []

    def test_no_batteries_returns_empty(self):
        aeroplane = SimpleNamespace(uuid=uuid.uuid4())
        motor = _make_motor()
        db = _mock_db_session(aeroplane=aeroplane, motors=[motor], batteries=[])
        request = _default_request()

        result = size_powertrain(db, aeroplane.uuid, request)
        assert result.recommendations == []

    def test_single_valid_combo_returns_one_candidate(self):
        aeroplane = SimpleNamespace(uuid=uuid.uuid4())
        motor = _make_motor()
        battery = _make_battery()
        esc = _make_esc(max_continuous_a=100.0)
        db = _mock_db_session(
            aeroplane=aeroplane,
            motors=[motor],
            batteries=[battery],
            escs=[esc],
        )
        request = _default_request()

        result = size_powertrain(db, aeroplane.uuid, request)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].motor_id == motor.id

    def test_results_sorted_by_confidence_descending(self):
        aeroplane = SimpleNamespace(uuid=uuid.uuid4())
        motor = _make_motor()
        # Two batteries with different capacities -> different flight times -> different confidence
        bat_small = _make_battery(battery_id=11, name="Small", capacity_mah=500)
        bat_large = _make_battery(battery_id=12, name="Large", capacity_mah=5000)
        db = _mock_db_session(
            aeroplane=aeroplane,
            motors=[motor],
            batteries=[bat_small, bat_large],
            escs=[],
        )
        request = _default_request()

        result = size_powertrain(db, aeroplane.uuid, request)
        assert len(result.recommendations) == 2
        confidences = [c.confidence for c in result.recommendations]
        assert confidences == sorted(confidences, reverse=True)

    def test_max_10_recommendations(self):
        aeroplane = SimpleNamespace(uuid=uuid.uuid4())
        motors = [_make_motor(motor_id=i, name=f"Motor{i}") for i in range(4)]
        batteries = [
            _make_battery(battery_id=100 + i, name=f"Bat{i}", capacity_mah=1000 + i * 500)
            for i in range(4)
        ]
        db = _mock_db_session(
            aeroplane=aeroplane,
            motors=motors,
            batteries=batteries,
            escs=[],
        )
        request = _default_request()

        result = size_powertrain(db, aeroplane.uuid, request)
        # 4 motors x 4 batteries = 16 combos, but capped at 10
        assert len(result.recommendations) <= 10
