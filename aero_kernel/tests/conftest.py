"""Shared pytest configuration for the ``aero_kernel`` tests."""

from pathlib import Path

import pytest
from aero_kernel.canon.load import load_model
from aero_kernel.canon.model import CanonModel

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def package_root() -> Path:
    """Directory of the ``aero_kernel`` package."""
    return PACKAGE_ROOT


@pytest.fixture(scope="session")
def flight_canon() -> CanonModel:
    """The fixture canon model of tests/fixtures/flight_canon.json (frozen, shared)."""
    return load_model(PACKAGE_ROOT / "tests" / "fixtures" / "flight_canon.json")
