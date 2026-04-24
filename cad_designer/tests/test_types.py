"""Tests for cad_designer.airplane.types — Pydantic type aliases."""
import pytest
from pydantic import BaseModel, ValidationError

from cad_designer.airplane.types import (
    CoordinateSystemBase,
    DihedralInDegrees,
    Factor,
    TipType,
    WingSegmentType,
    WingSides,
)


# --- Helper models that use the type aliases as field types ---

class FactorModel(BaseModel):
    value: Factor  # type: ignore[valid-type]


class DihedralModel(BaseModel):
    value: DihedralInDegrees  # type: ignore[valid-type]


class CoordModel(BaseModel):
    value: CoordinateSystemBase


class SegmentModel(BaseModel):
    value: WingSegmentType


class TipModel(BaseModel):
    value: TipType


class SidesModel(BaseModel):
    value: WingSides


# ---- Factor -----------------------------------------------------------

class TestFactor:
    @pytest.mark.parametrize("val", [0.0, 0.5, 1.0, 0.001, 0.999])
    def test_accepts_valid_values(self, val):
        m = FactorModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", [-0.1, -1.0, 1.1, 2.0, 100.0])
    def test_rejects_out_of_range(self, val):
        with pytest.raises(ValidationError):
            FactorModel(value=val)


# ---- DihedralInDegrees -------------------------------------------------

class TestDihedralInDegrees:
    @pytest.mark.parametrize("val", [-180.0, -90.0, 0.0, 90.0, 180.0])
    def test_accepts_valid_values(self, val):
        m = DihedralModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", [-180.1, -200.0, 180.1, 360.0])
    def test_rejects_out_of_range(self, val):
        with pytest.raises(ValidationError):
            DihedralModel(value=val)


# ---- CoordinateSystemBase -----------------------------------------------

class TestCoordinateSystemBase:
    @pytest.mark.parametrize("val", ["world", "wing", "root_airfoil", "tip_airfoil"])
    def test_accepts_valid_lowercase(self, val):
        m = CoordModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", ["WORLD", "Wing", "ROOT_AIRFOIL", "TIP_AIRFOIL"])
    def test_case_insensitive_via_before_validator(self, val):
        m = CoordModel(value=val)
        assert m.value == val.lower()

    @pytest.mark.parametrize("val", ["fuselage", "unknown", ""])
    def test_rejects_invalid_values(self, val):
        with pytest.raises(ValidationError):
            CoordModel(value=val)


# ---- WingSegmentType ---------------------------------------------------

class TestWingSegmentType:
    @pytest.mark.parametrize("val", ["root", "segment", "tip"])
    def test_accepts_valid_lowercase(self, val):
        m = SegmentModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", ["ROOT", "Segment", "TIP"])
    def test_case_insensitive(self, val):
        m = SegmentModel(value=val)
        assert m.value == val.lower()

    @pytest.mark.parametrize("val", ["flap", "spar", ""])
    def test_rejects_invalid_values(self, val):
        with pytest.raises(ValidationError):
            SegmentModel(value=val)


# ---- TipType -----------------------------------------------------------

class TestTipType:
    @pytest.mark.parametrize("val", ["flat", "round"])
    def test_accepts_valid_values(self, val):
        m = TipModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", ["FLAT", "Round"])
    def test_case_insensitive(self, val):
        m = TipModel(value=val)
        assert m.value == val.lower()

    @pytest.mark.parametrize("val", ["pointy", "sharp", ""])
    def test_rejects_invalid_values(self, val):
        with pytest.raises(ValidationError):
            TipModel(value=val)


# ---- WingSides ---------------------------------------------------------

class TestWingSides:
    @pytest.mark.parametrize("val", ["LEFT", "RIGHT", "BOTH"])
    def test_accepts_valid_uppercase(self, val):
        m = SidesModel(value=val)
        assert m.value == val

    @pytest.mark.parametrize("val", ["left", "right", "both"])
    def test_case_insensitive_lowered_to_upper(self, val):
        m = SidesModel(value=val)
        assert m.value == val.upper()

    @pytest.mark.parametrize("val", ["center", "none", ""])
    def test_rejects_invalid_values(self, val):
        with pytest.raises(ValidationError):
            SidesModel(value=val)
