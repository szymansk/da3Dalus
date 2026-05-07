"""Tests for the flight envelope feature — schemas, model, computation, service."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError


# ────────────────────────────────────────────────────────────────────────────
# Task 1: Schema tests
# ────────────────────────────────────────────────────────────────────────────


class TestVnPoint:
    """VnPoint schema validation."""

    def test_valid_point(self):
        from app.schemas.flight_envelope import VnPoint

        p = VnPoint(velocity_mps=25.0, load_factor=2.5)
        assert p.velocity_mps == 25.0
        assert p.load_factor == 2.5

    def test_zero_velocity_accepted(self):
        from app.schemas.flight_envelope import VnPoint

        p = VnPoint(velocity_mps=0.0, load_factor=1.0)
        assert p.velocity_mps == 0.0

    def test_negative_velocity_rejected(self):
        from app.schemas.flight_envelope import VnPoint

        with pytest.raises(PydanticValidationError, match="velocity"):
            VnPoint(velocity_mps=-1.0, load_factor=1.0)


class TestVnCurve:
    """VnCurve schema validation."""

    def test_valid_curve(self):
        from app.schemas.flight_envelope import VnCurve, VnPoint

        pos = [VnPoint(velocity_mps=10.0, load_factor=1.0)]
        neg = [VnPoint(velocity_mps=10.0, load_factor=-0.5)]
        curve = VnCurve(
            positive=pos,
            negative=neg,
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        assert curve.dive_speed_mps == 40.0
        assert len(curve.positive) == 1


class TestPerformanceKPI:
    """PerformanceKPI schema validation."""

    def test_valid_kpi(self):
        from app.schemas.flight_envelope import PerformanceKPI

        kpi = PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=8.5,
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        )
        assert kpi.label == "stall_speed"
        assert kpi.confidence == "estimated"

    def test_invalid_confidence_rejected(self):
        from app.schemas.flight_envelope import PerformanceKPI

        with pytest.raises(PydanticValidationError):
            PerformanceKPI(
                label="stall_speed",
                display_name="Stall Speed",
                value=8.5,
                unit="m/s",
                source_op_id=None,
                confidence="guess",
            )


class TestVnMarker:
    """VnMarker schema validation."""

    def test_valid_marker(self):
        from app.schemas.flight_envelope import VnMarker

        m = VnMarker(
            op_id=1,
            name="cruise",
            velocity_mps=20.0,
            load_factor=1.0,
            status="TRIMMED",
            label="cruise",
        )
        assert m.op_id == 1
        assert m.name == "cruise"


class TestFlightEnvelopeRead:
    """FlightEnvelopeRead schema validation."""

    def test_valid_read(self):
        from app.schemas.flight_envelope import (
            FlightEnvelopeRead,
            PerformanceKPI,
            VnCurve,
            VnMarker,
            VnPoint,
        )

        now = datetime.now(timezone.utc)
        curve = VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        kpi = PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=8.5,
            unit="m/s",
            source_op_id=None,
            confidence="estimated",
        )
        marker = VnMarker(
            op_id=1,
            name="cruise",
            velocity_mps=20.0,
            load_factor=1.0,
            status="TRIMMED",
            label="cruise",
        )
        envelope = FlightEnvelopeRead(
            id=1,
            aeroplane_id=42,
            vn_curve=curve,
            kpis=[kpi],
            operating_points=[marker],
            assumptions_snapshot={"mass": 1.5},
            computed_at=now,
        )
        assert envelope.aeroplane_id == 42
        assert len(envelope.kpis) == 1
        assert len(envelope.operating_points) == 1


class TestComputeEnvelopeRequest:
    """ComputeEnvelopeRequest schema validation."""

    def test_default_force_recompute(self):
        from app.schemas.flight_envelope import ComputeEnvelopeRequest

        req = ComputeEnvelopeRequest()
        assert req.force_recompute is False

    def test_force_recompute_true(self):
        from app.schemas.flight_envelope import ComputeEnvelopeRequest

        req = ComputeEnvelopeRequest(force_recompute=True)
        assert req.force_recompute is True
