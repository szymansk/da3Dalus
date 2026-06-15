"""Tests for the powertrain sizing modal params endpoint (gh-197).

The endpoint returns pre-filled defaults for the Powertrain Sizing Modal:
  - altitude_m: from mission context (fallback 0.0)
  - cd0: from assumption_computation_context (fallback RC default with warning)
  - s_ref_m2: from assumption_computation_context (fallback with warning)
  - motors: list of brushless_motor components with efficiency_pct from specs
  - warnings: forwarded from context resolution
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.powertrain_sizing_modal import (
    MotorSuggestion,
    PowertrainModalParamsResponse,
)
from app.services.powertrain_sizing_modal_service import (
    get_modal_params,
    DEFAULT_MOTOR_ETA,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_aeroplane(
    aero_uuid=None,
    ctx: dict | None = None,
):
    plane = SimpleNamespace(
        uuid=aero_uuid or uuid.uuid4(),
        assumption_computation_context=ctx or {},
    )
    return plane


def _make_motor(
    motor_id: int = 1,
    name: str = "D-Power M2826/10",
    mass_g: float = 50.0,
    manufacturer: str = "D-Power",
    specs: dict | None = None,
):
    return SimpleNamespace(
        id=motor_id,
        name=name,
        mass_g=mass_g,
        manufacturer=manufacturer,
        description=None,
        specs=specs or {},
    )


def _make_db(aeroplane=None, motors=None):
    db = MagicMock()
    call_count = {"n": 0}

    aeroplane_chain = MagicMock()
    aeroplane_chain.filter.return_value = aeroplane_chain
    aeroplane_chain.first.return_value = aeroplane

    motor_chain = MagicMock()
    motor_chain.filter.return_value = motor_chain
    motor_chain.all.return_value = motors or []

    queries = [aeroplane_chain, motor_chain]

    def _query_side(model):
        idx = call_count["n"]
        call_count["n"] += 1
        return queries[idx]

    db.query.side_effect = _query_side
    return db


# ---------------------------------------------------------------------------
# Tests: PowertrainModalParamsResponse schema
# ---------------------------------------------------------------------------


class TestPowertrainModalParamsResponse:
    def test_schema_has_required_fields(self):
        resp = PowertrainModalParamsResponse(
            altitude_m=0.0,
            cd0=0.03,
            s_ref_m2=0.5,
            eta_prop=0.65,
            eta_motor=DEFAULT_MOTOR_ETA,
            motors=[],
            warnings=[],
        )
        assert resp.altitude_m == 0.0
        assert resp.cd0 == 0.03
        assert resp.s_ref_m2 == 0.5
        assert resp.eta_prop == 0.65
        assert resp.eta_motor == DEFAULT_MOTOR_ETA
        assert resp.motors == []
        assert resp.warnings == []

    def test_motor_suggestion_carries_efficiency(self):
        m = MotorSuggestion(
            id=1,
            name="Motor A",
            manufacturer="ACME",
            mass_g=55.0,
            efficiency_pct=85.0,
            kv=1200,
            max_power_w=350.0,
        )
        assert m.efficiency_pct == 85.0
        assert m.kv == 1200


# ---------------------------------------------------------------------------
# Tests: get_modal_params service
# ---------------------------------------------------------------------------


class TestGetModalParams:
    def test_missing_aeroplane_raises(self):
        db = _make_db(aeroplane=None, motors=[])
        with pytest.raises(Exception, match="not found|Not Found"):
            get_modal_params(db, uuid.uuid4())

    def test_empty_context_uses_defaults_and_warns(self):
        plane = _make_aeroplane(ctx={})
        db = _make_db(aeroplane=plane, motors=[])

        result = get_modal_params(db, plane.uuid)

        assert result.altitude_m == 0.0  # default
        # cd0 and s_ref_m2 use RC defaults, warnings are emitted
        assert result.cd0 > 0
        assert result.s_ref_m2 > 0
        assert len(result.warnings) >= 1  # at least one param was defaulted

    def test_context_cd0_and_sref_are_used(self):
        plane = _make_aeroplane(ctx={"cd0": 0.025, "s_ref_m2": 0.42})
        db = _make_db(aeroplane=plane, motors=[])

        result = get_modal_params(db, plane.uuid)

        assert result.cd0 == pytest.approx(0.025)
        assert result.s_ref_m2 == pytest.approx(0.42)
        # cd0 and s_ref present → no warning for those
        cd0_warnings = [w for w in result.warnings if "cd0" in w.lower()]
        sref_warnings = [w for w in result.warnings if "s_ref" in w.lower()]
        assert cd0_warnings == []
        assert sref_warnings == []

    def test_motors_included_with_efficiency_from_specs(self):
        plane = _make_aeroplane(ctx={"cd0": 0.03, "s_ref_m2": 0.5})
        motor = _make_motor(
            motor_id=42,
            name="D-Power M2826",
            mass_g=55.0,
            specs={"kv": 1100, "efficiency_pct": 82.0, "max_power_w": 320.0},
        )
        db = _make_db(aeroplane=plane, motors=[motor])

        result = get_modal_params(db, plane.uuid)

        assert len(result.motors) == 1
        m = result.motors[0]
        assert m.id == 42
        assert m.name == "D-Power M2826"
        assert m.kv == 1100
        assert m.efficiency_pct == pytest.approx(82.0)
        assert m.max_power_w == pytest.approx(320.0)

    def test_kv_read_from_real_gh986_specs_key(self):
        """Regression (gh-990): real catalog data stores KV under
        'kv_rpm_per_volt' (gh-986 schema), not 'kv'. The modal must read it,
        otherwise every motor shows KV=null in the UI."""
        plane = _make_aeroplane(ctx={"cd0": 0.03, "s_ref_m2": 0.5})
        motor = _make_motor(
            motor_id=37,
            name="AL 28-09",
            specs={
                "kv_rpm_per_volt": 980,
                "io_no_load_a": 0.7,
                "continuous_current_a": 12.0,
                "max_current_a": 14.0,
            },
        )
        db = _make_db(aeroplane=plane, motors=[motor])

        result = get_modal_params(db, plane.uuid)

        assert result.motors[0].kv == pytest.approx(980.0)

    def test_motors_without_efficiency_use_default(self):
        plane = _make_aeroplane(ctx={"cd0": 0.03, "s_ref_m2": 0.5})
        motor = _make_motor(motor_id=5, specs={})  # no efficiency_pct in specs
        db = _make_db(aeroplane=plane, motors=[motor])

        result = get_modal_params(db, plane.uuid)

        assert len(result.motors) == 1
        assert result.motors[0].efficiency_pct == pytest.approx(DEFAULT_MOTOR_ETA * 100)

    def test_default_eta_motor_is_brushless_typical(self):
        # Brushless motors typically 85% efficiency
        assert 0.80 <= DEFAULT_MOTOR_ETA <= 0.92

    def test_eta_prop_default_returned(self):
        plane = _make_aeroplane(ctx={})
        db = _make_db(aeroplane=plane, motors=[])

        result = get_modal_params(db, plane.uuid)

        assert 0.50 <= result.eta_prop <= 0.90

    def test_multiple_motors_all_returned(self):
        plane = _make_aeroplane(ctx={"cd0": 0.03, "s_ref_m2": 0.5})
        motors = [
            _make_motor(motor_id=i, name=f"Motor {i}", specs={"kv": 900 + i * 100})
            for i in range(5)
        ]
        db = _make_db(aeroplane=plane, motors=motors)

        result = get_modal_params(db, plane.uuid)
        assert len(result.motors) == 5
