"""Tests for gh-960: warnings channel in PowertrainSizingResponse.

Verifies that the service emits descriptive warnings when aero parameters
fall back to RC-typical defaults, and prefers values from the aeroplane's
assumption_computation_context (gh-924 single source of truth).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.powertrain_sizing import (
    PowertrainSizingRequest,
    PowertrainSizingResponse,
)
from app.services.powertrain_sizing_service import (
    _DEFAULT_CD0,
    _DEFAULT_E_OSWALD,
    _DEFAULT_AR,
    _DEFAULT_S_REF_M2,
    _resolve_aero_params,
    size_powertrain,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


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


def _default_request(**overrides) -> PowertrainSizingRequest:
    defaults = dict(
        airframe_mass_kg=2.0,
        target_cruise_speed_ms=15.0,
        target_top_speed_ms=25.0,
        target_flight_time_min=10.0,
    )
    defaults.update(overrides)
    return PowertrainSizingRequest(**defaults)


def _mock_db_session(aeroplane=None, motors=None, batteries=None, escs=None):
    db = MagicMock()
    call_count = {"n": 0}

    def _build_chain(result):
        chain = MagicMock()
        chain.filter.return_value = chain
        chain.first.return_value = result if not isinstance(result, list) else None
        chain.all.return_value = result if isinstance(result, list) else []
        return chain

    queries = [
        _build_chain(aeroplane),
        _build_chain(motors or []),
        _build_chain(batteries or []),
        _build_chain(escs or []),
    ]

    def _side(model):
        idx = call_count["n"]
        call_count["n"] += 1
        return queries[idx]

    db.query.side_effect = _side
    return db


# ──────────────────────────────────────────────────────────────────────────────
# PowertrainSizingResponse.warnings field
# ──────────────────────────────────────────────────────────────────────────────


class TestPowertrainSizingResponseWarningsField:
    def test_warnings_field_exists_and_defaults_empty(self):
        r = PowertrainSizingResponse(recommendations=[])
        assert hasattr(r, "warnings")
        assert r.warnings == []

    def test_warnings_field_accepts_strings(self):
        r = PowertrainSizingResponse(
            recommendations=[],
            warnings=["Test warning 1", "Test warning 2"],
        )
        assert len(r.warnings) == 2

    def test_response_serialises_warnings(self):
        r = PowertrainSizingResponse(
            recommendations=[],
            warnings=["e_oswald assumed 0.8"],
        )
        d = r.model_dump()
        assert "warnings" in d
        assert d["warnings"] == ["e_oswald assumed 0.8"]


# ──────────────────────────────────────────────────────────────────────────────
# _resolve_aero_params
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveAeroParams:
    """Unit tests for the 3-tier priority resolver."""

    def test_all_from_request_no_warnings(self):
        request = _default_request(
            cd0=0.02,
            e_oswald=0.75,
            aspect_ratio=9.0,
            s_ref_m2=0.6,
        )
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context=None)
        assert cd0 == pytest.approx(0.02)
        assert e == pytest.approx(0.75)
        assert ar == pytest.approx(9.0)
        assert s == pytest.approx(0.6)
        assert warnings == []

    def test_request_wins_over_context(self):
        request = _default_request(e_oswald=0.70)
        ctx = {"e_oswald": 0.85, "cd0": 0.025, "aspect_ratio": 7.0, "s_ref_m2": 0.45}
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context=ctx)
        assert e == pytest.approx(0.70)  # request wins
        # other params come from context (no defaults triggered)
        assert cd0 == pytest.approx(0.025)
        assert ar == pytest.approx(7.0)
        assert s == pytest.approx(0.45)
        assert warnings == []

    def test_context_preferred_over_default(self):
        request = _default_request()  # no aero params
        ctx = {"e_oswald": 0.78, "cd0": 0.035, "aspect_ratio": 8.0, "s_ref_m2": 0.40}
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context=ctx)
        assert e == pytest.approx(0.78)
        assert cd0 == pytest.approx(0.035)
        assert warnings == []  # no defaults triggered

    def test_missing_e_oswald_emits_warning(self):
        request = _default_request()  # no e_oswald
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context={})
        assert e == pytest.approx(_DEFAULT_E_OSWALD)
        assert any("e_oswald" in w for w in warnings)

    def test_missing_cd0_emits_warning(self):
        request = _default_request()
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context={})
        assert cd0 == pytest.approx(_DEFAULT_CD0)
        assert any("cd0" in w for w in warnings)

    def test_missing_aspect_ratio_emits_warning(self):
        request = _default_request()
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context={})
        assert ar == pytest.approx(_DEFAULT_AR)
        assert any("aspect_ratio" in w for w in warnings)

    def test_missing_s_ref_emits_warning(self):
        request = _default_request()
        cd0, e, ar, s, warnings = _resolve_aero_params(request, context={})
        assert s == pytest.approx(_DEFAULT_S_REF_M2)
        assert any("s_ref_m2" in w for w in warnings)

    def test_no_params_four_warnings(self):
        request = _default_request()
        _, _, _, _, warnings = _resolve_aero_params(request, context=None)
        assert len(warnings) == 4

    def test_partial_context_only_missing_emit_warning(self):
        """When context has cd0 + e_oswald but not AR/s_ref → 2 warnings."""
        request = _default_request()
        ctx = {"cd0": 0.028, "e_oswald": 0.80}
        _, _, ar, s, warnings = _resolve_aero_params(request, context=ctx)
        assert ar == pytest.approx(_DEFAULT_AR)
        assert s == pytest.approx(_DEFAULT_S_REF_M2)
        assert len(warnings) == 2
        assert all(any(key in w for w in warnings) for key in ("aspect_ratio", "s_ref_m2"))

    def test_all_from_context_no_warnings(self):
        request = _default_request()
        ctx = {
            "cd0": 0.030,
            "e_oswald": 0.80,
            "aspect_ratio": 8.0,
            "s_ref_m2": 0.50,
        }
        _, _, _, _, warnings = _resolve_aero_params(request, context=ctx)
        assert warnings == []

    def test_none_context_triggers_all_defaults(self):
        request = _default_request()
        _, _, _, _, warnings = _resolve_aero_params(request, context=None)
        assert len(warnings) == 4

    def test_warning_mentions_default_value(self):
        request = _default_request()
        _, e, _, _, warnings = _resolve_aero_params(request, context=None)
        e_warning = next(w for w in warnings if "e_oswald" in w)
        assert str(_DEFAULT_E_OSWALD) in e_warning

    def test_warning_suggests_what_to_provide(self):
        request = _default_request()
        _, _, _, _, warnings = _resolve_aero_params(request, context=None)
        for w in warnings:
            assert "e_oswald" in w or "cd0" in w or "aspect_ratio" in w or "s_ref_m2" in w


# ──────────────────────────────────────────────────────────────────────────────
# size_powertrain integration (mocked DB)
# ──────────────────────────────────────────────────────────────────────────────


class TestSizePowertrainWarnings:
    def _make_plane(self, context=None):
        plane = SimpleNamespace(uuid=uuid.uuid4())
        plane.assumption_computation_context = context
        return plane

    def test_no_aero_params_response_has_warnings(self):
        plane = self._make_plane(context=None)
        motor = _make_motor()
        battery = _make_battery()
        db = _mock_db_session(aeroplane=plane, motors=[motor], batteries=[battery])
        request = _default_request()  # no aero params

        result = size_powertrain(db, plane.uuid, request)

        assert isinstance(result.warnings, list)
        assert len(result.warnings) > 0
        assert any("e_oswald" in w for w in result.warnings)

    def test_with_e_oswald_no_e_oswald_warning(self):
        plane = self._make_plane(context=None)
        motor = _make_motor()
        battery = _make_battery()
        db = _mock_db_session(aeroplane=plane, motors=[motor], batteries=[battery])
        request = _default_request(
            e_oswald=0.75,
            cd0=0.025,
            aspect_ratio=8.5,
            s_ref_m2=0.45,
        )

        result = size_powertrain(db, plane.uuid, request)

        # No warnings when all aero params are provided
        assert result.warnings == []

    def test_context_prevents_default_warnings(self):
        ctx = {
            "cd0": 0.030,
            "e_oswald": 0.80,
            "aspect_ratio": 8.0,
            "s_ref_m2": 0.50,
        }
        plane = self._make_plane(context=ctx)
        motor = _make_motor()
        battery = _make_battery()
        db = _mock_db_session(aeroplane=plane, motors=[motor], batteries=[battery])
        request = _default_request()  # no explicit aero params

        result = size_powertrain(db, plane.uuid, request)

        # Context fully covered — no warnings
        assert result.warnings == []

    def test_partial_context_emits_only_missing_warnings(self):
        """Context has cd0 and e_oswald but not AR and s_ref → 2 warnings."""
        ctx = {"cd0": 0.028, "e_oswald": 0.78}
        plane = self._make_plane(context=ctx)
        motor = _make_motor()
        battery = _make_battery()
        db = _mock_db_session(aeroplane=plane, motors=[motor], batteries=[battery])
        request = _default_request()

        result = size_powertrain(db, plane.uuid, request)

        assert len(result.warnings) == 2
        assert all(any(key in w for w in result.warnings) for key in ("aspect_ratio", "s_ref_m2"))

    def test_empty_catalog_returns_empty_with_no_warnings(self):
        """When no motors/batteries, warnings are empty (no sizing performed)."""
        plane = self._make_plane(context=None)
        db = _mock_db_session(aeroplane=plane, motors=[], batteries=[])
        request = _default_request()

        result = size_powertrain(db, plane.uuid, request)

        assert result.recommendations == []
        assert result.warnings == []
