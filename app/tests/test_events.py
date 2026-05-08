"""Tests for app/core/events.py — domain event bus."""

from __future__ import annotations

import pytest

from app.core.events import (
    AssumptionChanged,
    DomainEvent,
    EventBus,
    GeometryChanged,
    event_bus,
)


class TestDomainEventCreation:
    """Test dataclass creation for domain events."""

    def test_geometry_changed_defaults(self):
        event = GeometryChanged(aeroplane_id=1)
        assert event.aeroplane_id == 1
        assert event.source_model == ""
        assert event.timestamp is not None

    def test_geometry_changed_with_source(self):
        event = GeometryChanged(aeroplane_id=42, source_model="WingModel")
        assert event.aeroplane_id == 42
        assert event.source_model == "WingModel"

    def test_assumption_changed_defaults(self):
        event = AssumptionChanged(aeroplane_id=1)
        assert event.aeroplane_id == 1
        assert event.parameter_name == ""

    def test_assumption_changed_with_parameter(self):
        event = AssumptionChanged(aeroplane_id=5, parameter_name="mass")
        assert event.aeroplane_id == 5
        assert event.parameter_name == "mass"

    def test_domain_event_has_timestamp(self):
        event = DomainEvent(aeroplane_id=1)
        assert event.timestamp is not None


class TestEventBusSubscribePublish:
    """Test EventBus subscribe and publish mechanics."""

    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(GeometryChanged, lambda e: received.append(e))

        event = GeometryChanged(aeroplane_id=1, source_model="WingModel")
        bus.publish(event)

        assert len(received) == 1
        assert received[0] is event

    def test_multiple_subscribers_same_event(self):
        bus = EventBus()
        received_a = []
        received_b = []
        bus.subscribe(GeometryChanged, lambda e: received_a.append(e))
        bus.subscribe(GeometryChanged, lambda e: received_b.append(e))

        event = GeometryChanged(aeroplane_id=1)
        bus.publish(event)

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_different_event_types_are_independent(self):
        bus = EventBus()
        geo_received = []
        assumption_received = []
        bus.subscribe(GeometryChanged, lambda e: geo_received.append(e))
        bus.subscribe(AssumptionChanged, lambda e: assumption_received.append(e))

        bus.publish(GeometryChanged(aeroplane_id=1))
        bus.publish(AssumptionChanged(aeroplane_id=2, parameter_name="mass"))

        assert len(geo_received) == 1
        assert len(assumption_received) == 1
        assert geo_received[0].aeroplane_id == 1
        assert assumption_received[0].aeroplane_id == 2

    def test_publish_with_no_subscribers_is_noop(self):
        bus = EventBus()
        # Should not raise
        bus.publish(GeometryChanged(aeroplane_id=1))

    def test_handler_exception_does_not_propagate(self):
        bus = EventBus()
        received = []

        def failing_handler(event):
            raise RuntimeError("handler error")

        def good_handler(event):
            received.append(event)

        bus.subscribe(GeometryChanged, failing_handler)
        bus.subscribe(GeometryChanged, good_handler)

        # Should not raise; the second handler should still run
        bus.publish(GeometryChanged(aeroplane_id=1))
        assert len(received) == 1

    def test_clear_removes_all_subscribers(self):
        bus = EventBus()
        received = []
        bus.subscribe(GeometryChanged, lambda e: received.append(e))
        bus.clear()

        bus.publish(GeometryChanged(aeroplane_id=1))
        assert len(received) == 0


class TestModuleLevelSingleton:
    """Test that the module-level event_bus singleton works."""

    def test_event_bus_is_an_eventbus_instance(self):
        assert isinstance(event_bus, EventBus)

    def test_event_bus_subscribe_and_publish(self):
        received = []
        event_bus.subscribe(GeometryChanged, lambda e: received.append(e))
        try:
            event_bus.publish(GeometryChanged(aeroplane_id=99))
            assert len(received) >= 1
        finally:
            event_bus.clear()
