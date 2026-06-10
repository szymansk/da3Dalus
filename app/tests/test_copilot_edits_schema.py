"""Unit tests for copilot edit-ops DSL schema (gh-937).

Tests each op type for correct validation + discriminator routing.
Tests the compute_metrics_diff pure helper.
No DB required.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.copilot_edits import (
    AddXsec,
    EditOp,
    RemoveXsec,
    ReplaceWingConfig,
    SetAssumption,
    SetWingParam,
    SetXsec,
)
from app.services.copilot_apply_service import compute_metrics_diff


# ---------------------------------------------------------------------------
# SetAssumption
# ---------------------------------------------------------------------------


class TestSetAssumption:
    def test_valid(self):
        op = SetAssumption(type="SetAssumption", param="mass", value=2.5)
        assert op.type == "SetAssumption"
        assert op.param == "mass"
        assert op.value == 2.5

    def test_default_type(self):
        op = SetAssumption(param="cd0", value=0.025)
        assert op.type == "SetAssumption"

    def test_requires_param_and_value(self):
        with pytest.raises(ValidationError):
            SetAssumption(type="SetAssumption")  # missing param and value

    def test_negative_value_allowed(self):
        op = SetAssumption(param="cg_x", value=-0.1)
        assert op.value == -0.1


# ---------------------------------------------------------------------------
# SetXsec
# ---------------------------------------------------------------------------


class TestSetXsec:
    def test_valid_minimal(self):
        op = SetXsec(wing="main_wing", index=1)
        assert op.type == "SetXsec"
        assert op.wing == "main_wing"
        assert op.index == 1
        assert op.chord is None

    def test_valid_with_chord(self):
        op = SetXsec(wing="main_wing", index=0, chord=150.0)
        assert op.chord == 150.0

    def test_valid_all_fields(self):
        op = SetXsec(
            wing="main_wing",
            index=2,
            chord=120.0,
            twist=-1.5,
            airfoil="./components/airfoils/rg15.dat",
            dihedral=3.0,
        )
        assert op.airfoil == "./components/airfoils/rg15.dat"
        assert op.dihedral == 3.0

    def test_negative_index_rejected(self):
        with pytest.raises(ValidationError):
            SetXsec(wing="main_wing", index=-1)

    def test_zero_chord_rejected(self):
        with pytest.raises(ValidationError):
            SetXsec(wing="main_wing", index=0, chord=0.0)

    def test_negative_chord_rejected(self):
        with pytest.raises(ValidationError):
            SetXsec(wing="main_wing", index=0, chord=-10.0)


# ---------------------------------------------------------------------------
# AddXsec
# ---------------------------------------------------------------------------


class TestAddXsec:
    def test_valid_minimal(self):
        op = AddXsec(wing="main_wing", at_index=1, chord=100.0, span=150.0)
        assert op.type == "AddXsec"
        assert op.at_index == 1
        assert op.chord == 100.0
        assert op.span == 150.0

    def test_valid_with_dihedral_for_winglet(self):
        op = AddXsec(
            wing="main_wing",
            at_index=3,
            chord=60.0,
            span=80.0,
            dihedral=60.0,  # winglet knee
        )
        assert op.dihedral == 60.0

    def test_at_index_zero_rejected(self):
        with pytest.raises(ValidationError):
            AddXsec(wing="main_wing", at_index=0, chord=100.0, span=150.0)

    def test_zero_span_rejected(self):
        with pytest.raises(ValidationError):
            AddXsec(wing="main_wing", at_index=1, chord=100.0, span=0.0)

    def test_zero_chord_rejected(self):
        with pytest.raises(ValidationError):
            AddXsec(wing="main_wing", at_index=1, chord=0.0, span=100.0)

    def test_optional_fields_default_to_none(self):
        op = AddXsec(wing="main_wing", at_index=1, chord=100.0, span=150.0)
        assert op.airfoil is None
        assert op.twist is None
        assert op.dihedral is None


# ---------------------------------------------------------------------------
# RemoveXsec
# ---------------------------------------------------------------------------


class TestRemoveXsec:
    def test_valid(self):
        op = RemoveXsec(wing="main_wing", index=1)
        assert op.type == "RemoveXsec"
        assert op.index == 1

    def test_index_zero_rejected(self):
        with pytest.raises(ValidationError):
            RemoveXsec(wing="main_wing", index=0)

    def test_negative_index_rejected(self):
        with pytest.raises(ValidationError):
            RemoveXsec(wing="main_wing", index=-1)


# ---------------------------------------------------------------------------
# SetWingParam
# ---------------------------------------------------------------------------


class TestSetWingParam:
    def test_valid_sweep(self):
        op = SetWingParam(wing="main_wing", sweep_mm=5.0)
        assert op.sweep_mm == 5.0
        assert op.dihedral is None

    def test_valid_dihedral(self):
        op = SetWingParam(wing="main_wing", dihedral=2.0)
        assert op.dihedral == 2.0

    def test_requires_wing(self):
        with pytest.raises(ValidationError):
            SetWingParam()  # missing wing

    def test_all_none_is_noop(self):
        op = SetWingParam(wing="main_wing")
        assert op.sweep_mm is None
        assert op.dihedral is None


# ---------------------------------------------------------------------------
# ReplaceWingConfig
# ---------------------------------------------------------------------------


class TestReplaceWingConfig:
    def test_valid(self):
        payload = {
            "segments": [],
            "nose_pnt": [0.0, 0.0, 0.0],
            "symmetric": True,
        }
        op = ReplaceWingConfig(wing="main_wing", wing_config=payload)
        assert op.type == "ReplaceWingConfig"
        assert op.wing_config["symmetric"] is True

    def test_requires_wing_config(self):
        with pytest.raises(ValidationError):
            ReplaceWingConfig(wing="main_wing")


# ---------------------------------------------------------------------------
# EditOp discriminated union
# ---------------------------------------------------------------------------


class TestEditOpUnion:
    def _adapter(self):
        return TypeAdapter(list[EditOp])

    def test_mixed_ops_parsed(self):
        ops = self._adapter().validate_python(
            [
                {"type": "SetAssumption", "param": "mass", "value": 2.5},
                {"type": "SetXsec", "wing": "main_wing", "index": 1, "chord": 150.0},
                {
                    "type": "AddXsec",
                    "wing": "main_wing",
                    "at_index": 2,
                    "chord": 80.0,
                    "span": 100.0,
                },
                {"type": "RemoveXsec", "wing": "main_wing", "index": 1},
                {"type": "SetWingParam", "wing": "main_wing", "dihedral": 2.0},
            ]
        )
        assert len(ops) == 5
        assert ops[0].type == "SetAssumption"
        assert ops[1].type == "SetXsec"
        assert ops[2].type == "AddXsec"
        assert ops[3].type == "RemoveXsec"
        assert ops[4].type == "SetWingParam"

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            self._adapter().validate_python([{"type": "DeleteAllWings"}])

    def test_invalid_op_data_rejected(self):
        with pytest.raises(ValidationError):
            self._adapter().validate_python(
                [
                    {"type": "SetXsec", "wing": "main_wing", "index": -1}  # negative index
                ]
            )

    def test_empty_list_ok(self):
        ops = self._adapter().validate_python([])
        assert ops == []


# ---------------------------------------------------------------------------
# compute_metrics_diff
# ---------------------------------------------------------------------------


class TestComputeMetricsDiff:
    def _metrics(self, **overrides) -> dict:
        base: dict = {
            "total_mass_kg": 2.0,
            "assumption_computation_context": {
                "span_m": 1.2,
                "aspect_ratio": 8.0,
                "cd0": 0.025,
                "e_oswald": 0.85,
                "ld_max": 15.0,
                "x_np_m": 0.15,
                "static_margin_pct": 10.0,
                "v_stall_mps": 8.0,
                "v_min_sink_mps": 9.0,
                "v_cruise_mps": 12.0,
                "cl_max": 1.4,
                "wing_area_m2": 0.18,
            },
        }
        for key, val in overrides.items():
            if "." in key:
                parts = key.split(".", 1)
                base.setdefault(parts[0], {})[parts[1]] = val
            else:
                base[key] = val
        return base

    def test_changed_metric_reported(self):
        a = self._metrics(total_mass_kg=2.0)
        b = self._metrics(total_mass_kg=2.5)
        diff = compute_metrics_diff(a, b)
        assert "mass_kg" in diff
        assert diff["mass_kg"]["before"] == 2.0
        assert diff["mass_kg"]["after"] == 2.5
        assert abs(diff["mass_kg"]["delta"] - 0.5) < 1e-9

    def test_unchanged_metric_not_reported(self):
        a = self._metrics()
        b = self._metrics()
        diff = compute_metrics_diff(a, b)
        assert diff == {}

    def test_nested_metric_changed(self):
        a = self._metrics()
        # Override nested field
        a["assumption_computation_context"]["static_margin_pct"] = 8.0
        b = self._metrics()
        b["assumption_computation_context"]["static_margin_pct"] = 12.0
        diff = compute_metrics_diff(a, b)
        assert "static_margin_pct" in diff
        assert diff["static_margin_pct"]["delta"] == pytest.approx(4.0)

    def test_missing_key_in_after(self):
        a = self._metrics(total_mass_kg=2.0)
        b = {"assumption_computation_context": {}}
        diff = compute_metrics_diff(a, b)
        # mass_kg present in a but absent in b → should appear with before but no after
        assert "mass_kg" in diff
        assert diff["mass_kg"]["before"] == 2.0
        assert "after" not in diff["mass_kg"]

    def test_missing_key_in_before(self):
        a = {"assumption_computation_context": {}}
        b = self._metrics(total_mass_kg=3.0)
        diff = compute_metrics_diff(a, b)
        assert "mass_kg" in diff
        assert diff["mass_kg"]["after"] == 3.0
        assert "before" not in diff["mass_kg"]

    def test_multiple_changes_all_reported(self):
        a = self._metrics()
        b = self._metrics()
        b["total_mass_kg"] = 3.0
        b["assumption_computation_context"]["span_m"] = 1.5
        b["assumption_computation_context"]["cd0"] = 0.02
        diff = compute_metrics_diff(a, b)
        assert len(diff) == 3
        assert "mass_kg" in diff
        assert "span_m" in diff
        assert "cd0" in diff

    def test_delta_sign(self):
        a = self._metrics()
        b = self._metrics()
        a["assumption_computation_context"]["static_margin_pct"] = 15.0
        b["assumption_computation_context"]["static_margin_pct"] = 8.0
        diff = compute_metrics_diff(a, b)
        # static_margin decreases
        assert diff["static_margin_pct"]["delta"] < 0
