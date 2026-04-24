"""Tests for cad_designer.airplane.aircraft_topology.wing.Spare."""

import pytest
from cadquery import Vector

from cad_designer.airplane.aircraft_topology.wing.Spare import Spare, SpareMode


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestSpareInit:
    """Test Spare constructor and default values."""

    def test_minimal_construction(self):
        s = Spare(spare_support_dimension_width=10.0, spare_support_dimension_height=5.0)
        assert s.spare_support_dimension_width == 10.0
        assert s.spare_support_dimension_height == 5.0
        assert s.spare_position_factor is None
        assert s.spare_length is None
        assert s.spare_start == 0.0
        assert s.spare_mode == "standard"
        assert s.spare_vector is None
        assert s.spare_origin is None

    def test_full_construction(self):
        s = Spare(
            spare_support_dimension_width=12.0,
            spare_support_dimension_height=8.0,
            spare_position_factor=0.3,
            spare_length=100.0,
            spare_start=5.0,
            spare_vector=(0.0, 1.0, 0.0),
            spare_origin=(10.0, 20.0, 30.0),
            spare_mode="follow",
        )
        assert s.spare_support_dimension_width == 12.0
        assert s.spare_support_dimension_height == 8.0
        assert s.spare_position_factor == 0.3
        assert s.spare_length == 100.0
        assert s.spare_start == 5.0
        assert s.spare_mode == "follow"
        assert isinstance(s.spare_vector, Vector)
        assert s.spare_vector.toTuple() == pytest.approx((0.0, 1.0, 0.0))
        assert isinstance(s.spare_origin, Vector)
        assert s.spare_origin.toTuple() == pytest.approx((10.0, 20.0, 30.0))

    def test_vector_none_stays_none(self):
        s = Spare(spare_support_dimension_width=1.0, spare_support_dimension_height=1.0)
        assert s.spare_vector is None
        assert s.spare_origin is None

    def test_vector_tuple_converted_to_cadquery_vector(self):
        s = Spare(
            spare_support_dimension_width=1.0,
            spare_support_dimension_height=1.0,
            spare_vector=(1.0, 2.0, 3.0),
        )
        assert isinstance(s.spare_vector, Vector)

    def test_zero_dimensions_allowed(self):
        s = Spare(spare_support_dimension_width=0.0, spare_support_dimension_height=0.0)
        assert s.spare_support_dimension_width == 0.0
        assert s.spare_support_dimension_height == 0.0


# ---------------------------------------------------------------------------
# Spare modes
# ---------------------------------------------------------------------------

class TestSpareModes:
    """Test all valid SpareMode values."""

    @pytest.mark.parametrize(
        "mode",
        ["normal", "follow", "standard", "standard_backward", "orthogonal_backward"],
    )
    def test_valid_modes(self, mode):
        s = Spare(
            spare_support_dimension_width=5.0,
            spare_support_dimension_height=3.0,
            spare_mode=mode,
        )
        assert s.spare_mode == mode


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSpareSerialization:
    """Test __getstate__, from_json_dict, and round-trip."""

    def test_getstate_without_vectors(self):
        s = Spare(spare_support_dimension_width=10.0, spare_support_dimension_height=5.0)
        state = s.__getstate__()
        assert state["spare_support_dimension_width"] == 10.0
        assert state["spare_support_dimension_height"] == 5.0
        assert state["spare_vector"] is None
        assert state["spare_origin"] is None

    def test_getstate_with_vectors(self):
        s = Spare(
            spare_support_dimension_width=10.0,
            spare_support_dimension_height=5.0,
            spare_vector=(1.0, 0.0, 0.0),
            spare_origin=(5.0, 10.0, 15.0),
        )
        state = s.__getstate__()
        # Vectors should be serialized as tuples, not cadquery.Vector
        assert isinstance(state["spare_vector"], tuple)
        assert state["spare_vector"] == pytest.approx((1.0, 0.0, 0.0))
        assert isinstance(state["spare_origin"], tuple)
        assert state["spare_origin"] == pytest.approx((5.0, 10.0, 15.0))

    def test_from_json_dict_minimal(self):
        data = {}
        s = Spare.from_json_dict(data)
        assert s.spare_support_dimension_width == 0
        assert s.spare_support_dimension_height == 0
        assert s.spare_mode == "standard"

    def test_from_json_dict_full(self):
        data = {
            "spare_support_dimension_width": 12.0,
            "spare_support_dimension_height": 8.0,
            "spare_position_factor": 0.25,
            "spare_length": 200.0,
            "spare_start": 10.0,
            "spare_vector": (0.0, 1.0, 0.0),
            "spare_origin": (1.0, 2.0, 3.0),
            "spare_mode": "follow",
        }
        s = Spare.from_json_dict(data)
        assert s.spare_support_dimension_width == 12.0
        assert s.spare_support_dimension_height == 8.0
        assert s.spare_position_factor == 0.25
        assert s.spare_length == 200.0
        assert s.spare_start == 10.0
        assert s.spare_mode == "follow"
        assert isinstance(s.spare_vector, Vector)
        assert isinstance(s.spare_origin, Vector)

    def test_roundtrip(self):
        original = Spare(
            spare_support_dimension_width=15.0,
            spare_support_dimension_height=7.5,
            spare_position_factor=0.4,
            spare_length=150.0,
            spare_start=3.0,
            spare_vector=(0.0, 0.0, 1.0),
            spare_origin=(10.0, 20.0, 0.0),
            spare_mode="normal",
        )
        state = original.__getstate__()
        restored = Spare.from_json_dict(state)

        assert restored.spare_support_dimension_width == original.spare_support_dimension_width
        assert restored.spare_support_dimension_height == original.spare_support_dimension_height
        assert restored.spare_position_factor == original.spare_position_factor
        assert restored.spare_length == original.spare_length
        assert restored.spare_start == original.spare_start
        assert restored.spare_mode == original.spare_mode
        assert restored.spare_vector.toTuple() == pytest.approx(original.spare_vector.toTuple())
        assert restored.spare_origin.toTuple() == pytest.approx(original.spare_origin.toTuple())

    def test_roundtrip_none_vectors(self):
        original = Spare(spare_support_dimension_width=5.0, spare_support_dimension_height=3.0)
        state = original.__getstate__()
        restored = Spare.from_json_dict(state)
        assert restored.spare_vector is None
        assert restored.spare_origin is None


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

class TestSpareRepr:
    def test_repr_does_not_raise(self):
        s = Spare(spare_support_dimension_width=10.0, spare_support_dimension_height=5.0, spare_mode="follow")
        result = repr(s)
        assert "follow" in result
