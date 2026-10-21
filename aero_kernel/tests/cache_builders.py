"""Helpers shared by the cache tests."""

from aero_kernel.cache import Entry


def entry(value: float = 1.0) -> Entry:
    """An entry with one output ``v``."""
    return Entry(outputs={"v": value}, warnings=())
