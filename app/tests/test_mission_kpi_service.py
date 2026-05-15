"""Unit tests for mission_kpi_service (gh-547).

Phase 2 Task 2.1: per-axis closed-form KPI calculators built on top of
the cached ``assumption_computation_context`` payload of an aeroplane.

The aggregator + endpoint tests (Task 2.2 / 2.3) live below the
per-axis tests once those calculators exist.
"""
from __future__ import annotations

import math

import pytest

from app.services.mission_kpi_service import (
    _kpi_climb_energy,
    _kpi_cruise,
    _kpi_glide,
    _kpi_maneuver,
    _kpi_stall_safety,
    _kpi_wing_loading,
    _normalise_score,
)


def test_normalise_clips_outside_range():
    assert _normalise_score(5.0, 0.0, 10.0) == 0.5
    assert _normalise_score(15.0, 0.0, 10.0) == 1.0
    assert _normalise_score(-3.0, 0.0, 10.0) == 0.0


def test_normalise_degenerate_range_returns_zero():
    assert _normalise_score(5.0, 10.0, 10.0) == 0.0
    assert _normalise_score(5.0, 10.0, 5.0) == 0.0


def test_kpi_stall_safety_from_context():
    ctx = {"v_cruise_mps": 18.0, "v_s1_mps": 12.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value == pytest.approx(1.5)
    assert kpi.score_0_1 == pytest.approx((1.5 - 1.3) / (2.5 - 1.3))
    assert kpi.provenance == "computed"
    assert kpi.unit == "-"


def test_kpi_stall_safety_missing_when_v_s1_absent():
    ctx = {"v_cruise_mps": 18.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value is None
    assert kpi.score_0_1 is None
    assert kpi.provenance == "missing"


def test_kpi_stall_safety_missing_when_v_cruise_absent():
    ctx = {"v_s1_mps": 12.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.provenance == "missing"


def test_kpi_glide_from_polar_by_config():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {
            "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
        },
    }
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    # (L/D)_max = 0.5 * sqrt(pi * e * AR / CD0)
    expected = 0.5 * math.sqrt(math.pi * 0.80 * 8.0 / 0.025)
    assert kpi.value == pytest.approx(expected, rel=1e-3)
    assert kpi.provenance == "computed"


def test_kpi_glide_missing_when_polar_absent():
    ctx = {"aspect_ratio": 8.0}
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    assert kpi.provenance == "missing"


def test_kpi_glide_missing_when_cd0_zero():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {"clean": {"cd0": 0.0, "e_oswald": 0.8}},
    }
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    assert kpi.provenance == "missing"


def test_kpi_climb_energy_from_polar():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {"clean": {"cd0": 0.025, "e_oswald": 0.80}},
    }
    kpi = _kpi_climb_energy(ctx, range_min=5.0, range_max=25.0)
    assert kpi.value is not None
    assert kpi.value > 0
    assert kpi.provenance == "computed"


def test_kpi_climb_energy_missing_when_no_polar():
    ctx = {"aspect_ratio": 8.0}
    kpi = _kpi_climb_energy(ctx, range_min=5.0, range_max=25.0)
    assert kpi.provenance == "missing"


def test_kpi_cruise_from_context():
    ctx = {"v_cruise_mps": 22.0}
    kpi = _kpi_cruise(ctx, range_min=10.0, range_max=25.0)
    assert kpi.value == pytest.approx(22.0)
    assert kpi.unit == "m/s"
    assert kpi.score_0_1 == pytest.approx((22.0 - 10.0) / (25.0 - 10.0))
    assert kpi.provenance == "computed"


def test_kpi_cruise_missing():
    kpi = _kpi_cruise({}, range_min=10.0, range_max=25.0)
    assert kpi.provenance == "missing"


def test_kpi_maneuver_from_context():
    ctx = {"flight_envelope_n_max": 4.5}
    kpi = _kpi_maneuver(ctx, range_min=2.0, range_max=5.0)
    assert kpi.value == pytest.approx(4.5)
    assert kpi.unit == "g"
    assert kpi.provenance == "computed"


def test_kpi_maneuver_missing():
    kpi = _kpi_maneuver({}, range_min=2.0, range_max=5.0)
    assert kpi.provenance == "missing"


def test_kpi_wing_loading_from_mass_and_sref():
    ctx = {"s_ref_m2": 0.30}
    kpi = _kpi_wing_loading(ctx, mass_kg=2.0, range_min=20.0, range_max=80.0)
    expected = 2.0 * 9.81 / 0.30
    assert kpi.value == pytest.approx(expected)
    assert kpi.unit == "N/m²"
    assert kpi.provenance == "computed"


def test_kpi_wing_loading_missing_when_no_mass():
    ctx = {"s_ref_m2": 0.30}
    kpi = _kpi_wing_loading(ctx, mass_kg=None, range_min=20.0, range_max=80.0)
    assert kpi.provenance == "missing"


def test_kpi_wing_loading_missing_when_no_sref():
    kpi = _kpi_wing_loading({}, mass_kg=2.0, range_min=20.0, range_max=80.0)
    assert kpi.provenance == "missing"
