"""gh-772 #C — role→axis decomposition + unique naming for mixed control surfaces."""

import pytest

from app.services.control_surface_mixing import (
    assert_unique_control_names,
    axis_control_name,
    control_axes_for_surface,
    is_dual_role,
    parse_role_tag,
)


def _axes(role, **kw):
    defaults = dict(
        role=role,
        tagged_name=f"[{role}]Surf",
        symmetric=(role not in {"aileron", "rudder"}),
        hinge_point=0.75,
        deflection=3.0,
        wing_key="wing0",
        xsec_index=1,
    )
    defaults.update(kw)
    return control_axes_for_surface(**defaults)


class TestSingleAxisUnchanged:
    @pytest.mark.parametrize(
        "role,symmetric,expected_sgn",
        [
            ("elevator", True, 1.0),
            ("flap", True, 1.0),
            ("stabilator", True, 1.0),
            ("rudder", False, -1.0),
            ("aileron", False, -1.0),
        ],
    )
    def test_single_axis_keeps_name_and_sign(self, role, symmetric, expected_sgn):
        axes = _axes(role, symmetric=symmetric, tagged_name=f"[{role}]X")
        assert len(axes) == 1
        ax = axes[0]
        assert ax.name == f"[{role}]X"  # name preserved verbatim
        assert ax.sgn_dup == expected_sgn
        assert ax.gain == 1.0
        assert ax.deflection == 3.0


class TestDualRoleEmitsTwoAxes:
    @pytest.mark.parametrize(
        "role,primary_axis,secondary_axis",
        [
            ("elevon", "pitch", "roll"),
            ("flaperon", "lift", "roll"),
            ("ruddervator", "pitch", "yaw"),
        ],
    )
    def test_two_axes_primary_symmetric_secondary_antisymmetric(
        self, role, primary_axis, secondary_axis
    ):
        axes = _axes(role, mix_gain_primary=1.2, mix_gain_secondary=0.6)
        assert len(axes) == 2
        primary, secondary = axes
        assert primary.symmetric is True and primary.sgn_dup == 1.0
        assert primary.axis == primary_axis and primary.gain == 1.2
        assert secondary.symmetric is False and secondary.sgn_dup == -1.0
        assert secondary.axis == secondary_axis and secondary.gain == 0.6

    def test_secondary_axis_baseline_deflection_is_zero(self):
        # AeroBuildup fallback: never feed roll/yaw deflection into the single-axis ASB model.
        axes = _axes("elevon", deflection=5.0)
        assert axes[0].deflection == 5.0  # primary carries the symmetric deflection
        assert axes[1].deflection == 0.0  # secondary axis zeroed

    def test_names_are_unique_and_role_parseable(self):
        axes = _axes("ruddervator")
        names = [a.name for a in axes]
        assert names[0] != names[1]
        for a in axes:
            role, _ = parse_role_tag(a.name)
            assert role == "ruddervator"

    def test_no_sgndup_other_than_unit(self):
        # Differential must NEVER leak into geometry as a non-unit SgnDup.
        axes = _axes("elevon")
        assert all(abs(a.sgn_dup) == 1.0 for a in axes)


class TestNaming:
    def test_avl_safe_no_spaces(self):
        name = axis_control_name("elevon", "pitch", "Left Wing", 2)
        assert " " not in name
        assert name.startswith("[elevon]")

    def test_uniqueness_assertion_raises_on_collision(self):
        with pytest.raises(ValueError, match="collapse"):
            assert_unique_control_names(["[elevon]pitch_w_1", "[elevon]pitch_w_1"])

    def test_uniqueness_assertion_passes_when_unique(self):
        assert_unique_control_names(["a", "b", "c"])  # no raise

    def test_is_dual_role(self):
        assert is_dual_role("elevon")
        assert is_dual_role("ruddervator")
        assert not is_dual_role("aileron")
        assert not is_dual_role("elevator")
        assert not is_dual_role(None)
