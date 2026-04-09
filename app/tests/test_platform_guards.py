"""Tests for the platform capability probes and HTTP guards.

These tests verify the logic that keeps the app importable on platforms
where CadQuery or Aerosandbox are excluded from dependencies. They do
not require an aarch64 environment to run — they patch the probes.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core import platform


@pytest.mark.unit
def test_cad_available_is_true_on_dev_environments():
    """CadQuery is expected to be present on macOS and amd64 Linux."""
    # The probe is lru_cached; the first call exercises the real import.
    platform.cad_available.cache_clear()
    assert platform.cad_available() is True


@pytest.mark.unit
def test_aerosandbox_available_is_true_on_dev_environments():
    platform.aerosandbox_available.cache_clear()
    assert platform.aerosandbox_available() is True


@pytest.mark.unit
def test_require_cad_raises_503_when_unavailable(monkeypatch):
    monkeypatch.setattr(platform, "cad_available", lambda: False)
    with pytest.raises(HTTPException) as exc_info:
        platform.require_cad()
    assert exc_info.value.status_code == 503
    assert "CadQuery" in exc_info.value.detail


@pytest.mark.unit
def test_require_aerosandbox_raises_503_when_unavailable(monkeypatch):
    monkeypatch.setattr(platform, "aerosandbox_available", lambda: False)
    with pytest.raises(HTTPException) as exc_info:
        platform.require_aerosandbox()
    assert exc_info.value.status_code == 503
    assert "Aerosandbox" in exc_info.value.detail


@pytest.mark.unit
def test_require_cad_no_raise_when_available(monkeypatch):
    monkeypatch.setattr(platform, "cad_available", lambda: True)
    # Should not raise.
    platform.require_cad()
