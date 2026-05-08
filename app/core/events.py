"""Synchronous in-process pub/sub event bus for domain events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    aeroplane_id: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GeometryChanged(DomainEvent):
    source_model: str = ""  # "WingModel", "WingXSecModel", "FuselageModel"


@dataclass
class AssumptionChanged(DomainEvent):
    parameter_name: str = ""  # "mass", "cg_x", "cl_max", etc.


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Callable]] = {}

    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", type(event).__name__)

    def clear(self) -> None:
        self._subscribers.clear()


# Module-level singleton
event_bus = EventBus()
