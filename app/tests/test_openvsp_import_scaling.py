"""Unit tests for OpenVSP import scaling helpers (gh-695).

Tests cover:
* ``_compute_max_wing_span`` — computes maximum |y| in m across all wings.
* ``_scale_aeroplane_lengths`` — multiplies length-typed fields by factor
  WITHOUT touching mass-typed fields (per ``feedback_openvsp_import_rc_scope``
  memory: mass scaling is intentionally out of scope for #695).
* Validation rules: factor ∈ (0.001, 10), span ∈ (0.1, 50), mutex.
"""

from __future__ import annotations

import pytest

from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingSchema,
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
    WingXSecSchema,
)
from app.schemas.weight_item import WeightItemWrite
from app.services.openvsp_import_service import (
    SCALE_FACTOR_MAX,
    SCALE_FACTOR_MIN,
    TARGET_SPAN_MAX,
    TARGET_SPAN_MIN,
    ScaleValidationError,
    _compute_max_wing_span,
    _resolve_scale_factor,
    _scale_aeroplane_lengths,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _xsec(xyz, chord, twist=0.0):
    return WingXSecSchema(
        xyz_le=list(xyz),
        chord=chord,
        twist=twist,
        airfoil="naca0015",
    )


def _make_wing(span_m: float, root_chord: float = 0.5, tip_chord: float = 0.2) -> AsbWingSchema:
    return AsbWingSchema(
        name="Main",
        symmetric=True,
        x_secs=[
            _xsec([0.0, 0.0, 0.0], root_chord),
            _xsec([0.1, span_m, 0.05], tip_chord),
        ],
    )


def _make_fuselage(length_m: float, half_width: float, half_height: float) -> FuselageSchema:
    return FuselageSchema(
        name="Body",
        x_secs=[
            FuselageXSecSuperEllipseSchema(
                xyz=[0.0, 0.0, 0.0],
                a=half_width,
                b=half_height,
                n=2.0,
            ),
            FuselageXSecSuperEllipseSchema(
                xyz=[length_m, 0.0, 0.0],
                a=half_width * 0.5,
                b=half_height * 0.5,
                n=2.0,
            ),
        ],
    )


def _weight(name: str, mass_kg: float, xyz=(0.0, 0.0, 0.0)) -> WeightItemWrite:
    x, y, z = xyz
    return WeightItemWrite(
        name=name,
        mass_kg=mass_kg,
        x_m=x,
        y_m=y,
        z_m=z,
        category="other",
    )


# ---------------------------------------------------------------------------
# _compute_max_wing_span
# ---------------------------------------------------------------------------


class TestComputeMaxWingSpan:
    def test_single_symmetric_wing_returns_full_span(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=2.5)}
        # symmetric wing: physical span is 2 * |y_tip|
        assert _compute_max_wing_span(ap) == pytest.approx(5.0)

    def test_single_asymmetric_wing_returns_half_span(self):
        ap = AeroplaneSchema(name="X")
        wing = _make_wing(span_m=3.0)
        wing.symmetric = False
        ap.wings = {"Main": wing}
        # asymmetric wing: only the tip-y is the span
        assert _compute_max_wing_span(ap) == pytest.approx(3.0)

    def test_picks_largest_wing_when_multiple(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {
            "Main": _make_wing(span_m=10.0),  # → 20 m
            "Tail": _make_wing(span_m=2.0),  # → 4 m
        }
        assert _compute_max_wing_span(ap) == pytest.approx(20.0)

    def test_zero_when_no_wings(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = None
        assert _compute_max_wing_span(ap) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _scale_aeroplane_lengths
# ---------------------------------------------------------------------------


class TestScaleAeroplaneLengths:
    def test_wing_xsec_lengths_scale(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=2.0, root_chord=0.5, tip_chord=0.2)}
        _scale_aeroplane_lengths(ap, 0.5)
        wing = ap.wings["Main"]
        assert wing.x_secs[0].chord == pytest.approx(0.25)
        assert wing.x_secs[1].chord == pytest.approx(0.10)
        assert wing.x_secs[1].xyz_le == pytest.approx([0.05, 1.0, 0.025])

    def test_twist_is_NOT_scaled(self):
        ap = AeroplaneSchema(name="X")
        wing = _make_wing(span_m=2.0)
        wing.x_secs[0].twist = 5.0
        wing.x_secs[1].twist = -1.0
        ap.wings = {"Main": wing}
        _scale_aeroplane_lengths(ap, 2.0)
        assert wing.x_secs[0].twist == pytest.approx(5.0)
        assert wing.x_secs[1].twist == pytest.approx(-1.0)

    def test_fuselage_xsec_lengths_scale(self):
        ap = AeroplaneSchema(name="X")
        ap.fuselages = {"Body": _make_fuselage(length_m=2.0, half_width=0.3, half_height=0.2)}
        _scale_aeroplane_lengths(ap, 2.0)
        fus = ap.fuselages["Body"]
        assert fus.x_secs[0].a == pytest.approx(0.6)
        assert fus.x_secs[0].b == pytest.approx(0.4)
        # x-position scales:
        assert fus.x_secs[1].xyz[0] == pytest.approx(4.0)

    def test_fuselage_n_exponent_is_NOT_scaled(self):
        ap = AeroplaneSchema(name="X")
        ap.fuselages = {"Body": _make_fuselage(length_m=2.0, half_width=0.3, half_height=0.2)}
        _scale_aeroplane_lengths(ap, 2.0)
        fus = ap.fuselages["Body"]
        assert fus.x_secs[0].n == pytest.approx(2.0)  # superellipse exponent stays

    def test_xyz_ref_scales(self):
        ap = AeroplaneSchema(name="X")
        ap.xyz_ref = [0.1, 0.0, -0.05]
        _scale_aeroplane_lengths(ap, 3.0)
        assert ap.xyz_ref == pytest.approx([0.3, 0.0, -0.15])

    def test_weight_item_positions_scale(self):
        ap = AeroplaneSchema(name="X")
        items = [_weight("Battery", 1.0, xyz=(0.4, 0.1, 0.0))]
        _scale_aeroplane_lengths(ap, 0.5, weight_items=items)
        assert items[0].x_m == pytest.approx(0.2)
        assert items[0].y_m == pytest.approx(0.05)
        assert items[0].z_m == pytest.approx(0.0)

    def test_weight_item_mass_is_NOT_scaled(self):
        """Per ``feedback_openvsp_import_rc_scope`` — mass scaling is OOS."""
        ap = AeroplaneSchema(name="X")
        items = [_weight("Battery", 1.234, xyz=(0.0, 0.0, 0.0))]
        _scale_aeroplane_lengths(ap, 10.0, weight_items=items)
        assert items[0].mass_kg == pytest.approx(1.234)

    def test_total_mass_kg_is_NOT_scaled(self):
        ap = AeroplaneSchema(name="X", total_mass_kg=2.5)
        _scale_aeroplane_lengths(ap, 4.0)
        assert ap.total_mass_kg == pytest.approx(2.5)

    def test_factor_of_one_is_noop(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=2.0, root_chord=0.5)}
        ap.fuselages = {"Body": _make_fuselage(length_m=1.0, half_width=0.2, half_height=0.1)}
        _scale_aeroplane_lengths(ap, 1.0)
        assert ap.wings["Main"].x_secs[1].xyz_le[1] == pytest.approx(2.0)
        assert ap.fuselages["Body"].x_secs[0].a == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# _resolve_scale_factor (validation + mutex)
# ---------------------------------------------------------------------------


class TestResolveScaleFactor:
    def test_none_returns_none(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        assert _resolve_scale_factor(ap, None, None) is None

    def test_scale_factor_passthrough(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        assert _resolve_scale_factor(ap, None, 2.0) == pytest.approx(2.0)

    def test_target_span_computed(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=10.0)}  # → 20 m current
        # target 1.5 m → factor 0.075
        f = _resolve_scale_factor(ap, target_span_m=1.5, scale_factor=None)
        assert f == pytest.approx(1.5 / 20.0)

    def test_both_params_raises_mutex(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        with pytest.raises(ScaleValidationError) as exc:
            _resolve_scale_factor(ap, target_span_m=1.5, scale_factor=0.5)
        assert "mutual" in str(exc.value).lower() or "both" in str(exc.value).lower()

    def test_scale_factor_below_min_raises(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        with pytest.raises(ScaleValidationError):
            _resolve_scale_factor(ap, None, SCALE_FACTOR_MIN / 2.0)

    def test_scale_factor_above_max_raises(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        with pytest.raises(ScaleValidationError):
            _resolve_scale_factor(ap, None, SCALE_FACTOR_MAX + 1.0)

    def test_target_span_below_min_raises(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        with pytest.raises(ScaleValidationError):
            _resolve_scale_factor(ap, target_span_m=TARGET_SPAN_MIN / 2.0, scale_factor=None)

    def test_target_span_above_max_raises(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = {"Main": _make_wing(span_m=1.0)}
        with pytest.raises(ScaleValidationError):
            _resolve_scale_factor(ap, target_span_m=TARGET_SPAN_MAX + 1.0, scale_factor=None)

    def test_target_span_with_no_wings_raises(self):
        ap = AeroplaneSchema(name="X")
        ap.wings = None
        with pytest.raises(ScaleValidationError) as exc:
            _resolve_scale_factor(ap, target_span_m=1.5, scale_factor=None)
        assert "wing" in str(exc.value).lower() or "span" in str(exc.value).lower()
