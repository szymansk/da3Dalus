"""TDD tests for the Turbulator domain object — gh-934 Slice 1.

All tests here must be RED before production code is written.
"""

import pytest

from cad_designer.airplane.aircraft_topology.wing.Turbulator import Turbulator
from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_turbulator(**kwargs) -> Turbulator:
    defaults = dict(
        form="zigzag",
        height_mm=0.3,
        position_root=0.1,
        position_tip=None,
        enabled=True,
    )
    defaults.update(kwargs)
    return Turbulator(**defaults)


def _make_segment(turbulator=None) -> WingSegment:
    root_airfoil = Airfoil(airfoil="./components/airfoils/rg15.dat", chord=200.0)
    return WingSegment(
        root_airfoil=root_airfoil,
        length=100.0,
        turbulator=turbulator,
    )


# ---------------------------------------------------------------------------
# Turbulator construction
# ---------------------------------------------------------------------------


class TestTurbulatorConstruction:
    def test_defaults(self):
        t = Turbulator(position_root=0.1)
        assert t.form == "zigzag"
        assert t.height_mm == pytest.approx(0.3)
        assert t.position_root == pytest.approx(0.1)
        assert t.position_tip == pytest.approx(0.1)  # defaults to position_root
        assert t.enabled is True

    def test_explicit_values(self):
        t = Turbulator(
            form="dots",
            height_mm=0.5,
            position_root=0.15,
            position_tip=0.2,
            enabled=False,
        )
        assert t.form == "dots"
        assert t.height_mm == pytest.approx(0.5)
        assert t.position_root == pytest.approx(0.15)
        assert t.position_tip == pytest.approx(0.2)
        assert t.enabled is False

    def test_thread_form(self):
        t = Turbulator(form="thread", position_root=0.12)
        assert t.form == "thread"

    def test_repr_contains_form(self):
        t = _make_turbulator()
        assert "zigzag" in repr(t)


# ---------------------------------------------------------------------------
# Turbulator __getstate__ / from_json_dict round-trip
# ---------------------------------------------------------------------------


class TestTurbulatorRoundTrip:
    def test_getstate_keys(self):
        t = _make_turbulator(form="dots", height_mm=0.4, position_root=0.08, position_tip=0.12)
        state = t.__getstate__()
        assert "form" in state
        assert "height_mm" in state
        assert "position_root" in state
        assert "position_tip" in state
        assert "enabled" in state

    def test_getstate_values(self):
        t = _make_turbulator(
            form="thread", height_mm=0.6, position_root=0.05, position_tip=0.07, enabled=False
        )
        state = t.__getstate__()
        assert state["form"] == "thread"
        assert state["height_mm"] == pytest.approx(0.6)
        assert state["position_root"] == pytest.approx(0.05)
        assert state["position_tip"] == pytest.approx(0.07)
        assert state["enabled"] is False

    def test_from_json_dict_roundtrip(self):
        t = _make_turbulator(
            form="dots", height_mm=0.25, position_root=0.09, position_tip=0.11, enabled=False
        )
        state = t.__getstate__()
        t2 = Turbulator.from_json_dict(state)
        assert t2.form == t.form
        assert t2.height_mm == pytest.approx(t.height_mm)
        assert t2.position_root == pytest.approx(t.position_root)
        assert t2.position_tip == pytest.approx(t.position_tip)
        assert t2.enabled == t.enabled

    def test_from_json_dict_defaults_position_tip(self):
        """from_json_dict without position_tip should default to position_root."""
        data = {"form": "zigzag", "height_mm": 0.3, "position_root": 0.1, "enabled": True}
        t = Turbulator.from_json_dict(data)
        assert t.position_tip == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# WingSegment carries turbulator
# ---------------------------------------------------------------------------


class TestWingSegmentTurbulator:
    def test_default_turbulator_is_none(self):
        seg = _make_segment(turbulator=None)
        assert seg.turbulator is None

    def test_segment_stores_turbulator(self):
        t = _make_turbulator()
        seg = _make_segment(turbulator=t)
        assert seg.turbulator is t

    def test_segment_getstate_includes_turbulator(self):
        t = _make_turbulator(form="dots", height_mm=0.4, position_root=0.1, position_tip=0.15)
        seg = _make_segment(turbulator=t)
        state = seg.__getstate__()
        assert "turbulator" in state
        assert state["turbulator"]["form"] == "dots"
        assert state["turbulator"]["height_mm"] == pytest.approx(0.4)

    def test_segment_getstate_none_turbulator(self):
        seg = _make_segment(turbulator=None)
        state = seg.__getstate__()
        assert "turbulator" in state
        assert state["turbulator"] is None

    def test_segment_from_json_dict_roundtrip_with_turbulator(self):
        t = _make_turbulator(
            form="thread", height_mm=0.3, position_root=0.08, position_tip=0.1, enabled=True
        )
        seg = _make_segment(turbulator=t)
        state = seg.__getstate__()
        seg2 = WingSegment.from_json_dict(state)
        assert seg2.turbulator is not None
        assert seg2.turbulator.form == "thread"
        assert seg2.turbulator.height_mm == pytest.approx(0.3)
        assert seg2.turbulator.position_root == pytest.approx(0.08)
        assert seg2.turbulator.position_tip == pytest.approx(0.1)
        assert seg2.turbulator.enabled is True

    def test_segment_from_json_dict_roundtrip_without_turbulator(self):
        seg = _make_segment(turbulator=None)
        state = seg.__getstate__()
        seg2 = WingSegment.from_json_dict(state)
        assert seg2.turbulator is None


# ---------------------------------------------------------------------------
# Backward-compatibility: old dicts without 'turbulator' key
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_wing_segment_from_old_dict_no_turbulator_key(self):
        """WingSegment.from_json_dict on a pre-gh-934 dict (no 'turbulator' key) must yield turbulator=None."""
        old_dict = {
            "root_airfoil": {
                "airfoil": "./components/airfoils/rg15.dat",
                "chord": 200.0,
                "dihedral_as_rotation_in_degrees": 0.0,
                "incidence": 0.0,
            },
            "tip_airfoil": {
                "airfoil": "./components/airfoils/rg15.dat",
                "chord": 180.0,
                "dihedral_as_rotation_in_degrees": 0.0,
                "incidence": 0.0,
            },
            "length": 100.0,
            "sweep": 0.0,
            "sweep_angle": 0.0,
            "spare_list": None,
            "trailing_edge_device": None,
            "number_interpolation_points": None,
            "tip_type": None,
            "wing_segment_type": "segment",
            # NOTE: NO 'turbulator' key — simulates a pre-gh-934 serialised dict
        }
        seg = WingSegment.from_json_dict(old_dict)
        assert seg.turbulator is None
