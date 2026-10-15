"""Shared pytest configuration for the ``aero_kernel`` tests."""

from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def package_root() -> Path:
    """Directory of the ``aero_kernel`` package."""
    return PACKAGE_ROOT
