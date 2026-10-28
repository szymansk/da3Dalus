"""Capture the kernel's log records of one request (gh-1282).

The kernel configures no logging; the application decides. The Expert View shows the records of
its request, so a handler on the ``aero_kernel`` logger collects them into the sink of the request
that is running in the current context. Concurrent requests keep their own records: the sink is a
context variable, and ``asyncio.to_thread`` copies the context into the worker thread.
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from app.schemas.canon import CanonLogRecord

KERNEL_LOGGER = "aero_kernel"

# An absolute file path: at least two segments after a slash that follows no word character
# (``m/s`` and ``N/m`` are not paths). Messages are domain-level; a path is an internal detail.
_PATH = re.compile(r"(?<![\w.])/(?:[\w.\-]+/)+[\w.\-]+")

_sink: ContextVar[list[CanonLogRecord] | None] = ContextVar("kernel_log_sink", default=None)
_lock = threading.Lock()
_depth = 0
_saved_level = logging.NOTSET


class _SinkHandler(logging.Handler):
    """Append each record to the sink of the request running in this context, if any."""

    def emit(self, record: logging.LogRecord) -> None:
        sink = _sink.get()
        if sink is None:
            return
        sink.append(
            CanonLogRecord(
                time=datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                )[:-3]
                + "Z",
                level=record.levelname,
                logger=record.name,
                message=_PATH.sub("<path>", record.getMessage()),
                formula=_extra(record, "formula"),
                quantity=_extra(record, "quantity"),
            )
        )


def _extra(record: logging.LogRecord, name: str) -> str | None:
    """A string attribute the kernel attached to the record, if any."""
    value = getattr(record, name, None)
    return value if isinstance(value, str) else None


_handler = _SinkHandler(level=logging.DEBUG)


@contextmanager
def capture_kernel_logs() -> Iterator[list[CanonLogRecord]]:
    """Collect the kernel's records, down to DEBUG, while the block runs.

    The kernel logger is lowered to DEBUG for the duration (and restored after the last of the
    concurrent captures), so the capture does not depend on the application's log level.

    Yields:
        The list the records are appended to, in emission order.
    """
    global _depth, _saved_level
    kernel_logger = logging.getLogger(KERNEL_LOGGER)
    sink: list[CanonLogRecord] = []
    token = _sink.set(sink)
    with _lock:
        if _depth == 0:
            _saved_level = kernel_logger.level
            kernel_logger.setLevel(logging.DEBUG)
            kernel_logger.addHandler(_handler)
        _depth += 1
    try:
        yield sink
    finally:
        _sink.reset(token)
        with _lock:
            _depth -= 1
            if _depth == 0:
                kernel_logger.removeHandler(_handler)
                kernel_logger.setLevel(_saved_level)
