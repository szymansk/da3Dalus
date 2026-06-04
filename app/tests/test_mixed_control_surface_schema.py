"""Tests for gh-772 #A — TED mix-gain + differential_ratio schema fields & validators.

Mixed control surfaces (aileron differential, elevon, flaperon, ruddervator) need
per-axis mix gains and a differential ratio. differential_ratio is a reporting-only
kinematic; mix_gain_secondary only exists for dual-role surfaces. The validators
keep impossible combinations off axis-less roles.
"""

import pytest
from pydantic import ValidationError

from app.schemas.aeroplaneschema import (
    ControlSurfaceRole,
    TrailingEdgeDeviceDetailSchema,
    TrailingEdgeDevicePatchSchema,
)


class TestMixFieldDefaults:
    def test_defaults_are_unity(self):
        ted = TrailingEdgeDeviceDetailSchema(role=ControlSurfaceRole.ELEVON)
        assert ted.mix_gain_primary == 1.0
        assert ted.mix_gain_secondary == 1.0
        assert ted.differential_ratio == 1.0

    def test_single_axis_role_unchanged(self):
        ted = TrailingEdgeDeviceDetailSchema(role=ControlSurfaceRole.ELEVATOR)
        assert ted.mix_gain_primary == 1.0
        assert ted.differential_ratio == 1.0


class TestRangeValidation:
    @pytest.mark.parametrize("bad", [0.0, -1.0, 5.1])
    def test_mix_gain_primary_out_of_range(self, bad):
        with pytest.raises(ValidationError):
            TrailingEdgeDeviceDetailSchema(role=ControlSurfaceRole.ELEVON, mix_gain_primary=bad)

    @pytest.mark.parametrize("bad", [0.3, 0.2, 3.1, 0.0])
    def test_differential_ratio_out_of_range(self, bad):
        with pytest.raises(ValidationError):
            TrailingEdgeDeviceDetailSchema(role=ControlSurfaceRole.AILERON, differential_ratio=bad)

    def test_differential_ratio_in_range_ok(self):
        ted = TrailingEdgeDeviceDetailSchema(
            role=ControlSurfaceRole.AILERON, differential_ratio=2.0
        )
        assert ted.differential_ratio == 2.0


class TestRoleAwareValidation:
    @pytest.mark.parametrize("role", ["aileron", "elevon", "flaperon", "ruddervator"])
    def test_differential_allowed_for_roles_with_antisymmetric_axis(self, role):
        ted = TrailingEdgeDeviceDetailSchema(role=role, differential_ratio=1.5)
        assert ted.differential_ratio == 1.5

    @pytest.mark.parametrize("role", ["elevator", "flap", "stabilator", "rudder"])
    def test_differential_rejected_for_axisless_roles(self, role):
        with pytest.raises(ValidationError):
            TrailingEdgeDeviceDetailSchema(role=role, differential_ratio=1.5)

    @pytest.mark.parametrize("role", ["elevon", "flaperon", "ruddervator"])
    def test_secondary_gain_allowed_for_dual_roles(self, role):
        ted = TrailingEdgeDeviceDetailSchema(role=role, mix_gain_secondary=0.5)
        assert ted.mix_gain_secondary == 0.5

    @pytest.mark.parametrize("role", ["aileron", "elevator", "flap", "rudder"])
    def test_secondary_gain_rejected_for_non_dual_roles(self, role):
        with pytest.raises(ValidationError):
            TrailingEdgeDeviceDetailSchema(role=role, mix_gain_secondary=0.5)


class TestPatchSchema:
    def test_patch_accepts_fields(self):
        patch = TrailingEdgeDevicePatchSchema(
            role=ControlSurfaceRole.ELEVON,
            mix_gain_secondary=0.6,
            differential_ratio=1.2,
        )
        assert patch.mix_gain_secondary == 0.6
        assert patch.differential_ratio == 1.2

    def test_patch_validates_when_role_present(self):
        with pytest.raises(ValidationError):
            TrailingEdgeDevicePatchSchema(role=ControlSurfaceRole.ELEVATOR, differential_ratio=1.5)

    def test_patch_skips_role_validation_when_role_absent(self):
        # Without a role on a patch we cannot cross-validate; range still applies.
        patch = TrailingEdgeDevicePatchSchema(differential_ratio=1.5)
        assert patch.differential_ratio == 1.5
