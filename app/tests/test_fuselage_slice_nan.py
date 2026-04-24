"""Test that NaN/Inf values from aerosandbox don't crash the slice endpoint (GH#301).

When area_wetted() returns NaN, the endpoint must return valid JSON
with None for the affected fields instead of crashing with ValueError.
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import InternalError


# Raw return value from cad_designer slicing — contains NaN
MOCK_XSECS = [
    {"xyz": [0, 0, 0], "a": 0.01, "b": 0.01, "n": 2.0},
    {"xyz": [0.1, 0, 0], "a": 0.05, "b": 0.04, "n": 2.3},
]

MOCK_METRICS_NAN = {
    "original_volume": 1.0,
    "original_area": 2.0,
    "reconstructed_volume": 0.5,
    "reconstructed_area": float("nan"),
    "volume_ratio": 0.5,
    "area_ratio": float("nan"),
}

MOCK_METRICS_INF = {
    "original_volume": 1.0,
    "original_area": 2.0,
    "reconstructed_volume": float("inf"),
    "reconstructed_area": float("-inf"),
    "volume_ratio": float("inf"),
    "area_ratio": float("-inf"),
}


class TestFuselageSliceNanHandling:
    """NaN/Inf values from aerosandbox must not crash JSON serialisation."""

    def _mock_slice(self, client, metrics):
        """Helper: POST /fuselages/slice with mocked slice_step_to_fuselage."""
        # Patch the lazy import inside slice_step_file
        mock_fn = MagicMock(return_value=(MOCK_XSECS, metrics))
        with patch.dict("sys.modules", {"cad_designer.aerosandbox.slicing": MagicMock(slice_step_to_fuselage=mock_fn)}):
            return client.post(
                "/fuselages/slice",
                files={"file": ("test.step", io.BytesIO(b"ISO-10303"), "application/step")},
            )

    def test_nan_metrics_return_none(self, client_and_db):
        """NaN values should become None in the JSON response."""
        client, _ = client_and_db
        resp = self._mock_slice(client, MOCK_METRICS_NAN)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["fidelity"]["area_ratio"] is None
        assert data["reconstructed_properties"]["surface_area_m2"] is None

    def test_inf_metrics_return_none(self, client_and_db):
        """Inf values should become None in the JSON response."""
        client, _ = client_and_db
        resp = self._mock_slice(client, MOCK_METRICS_INF)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["fidelity"]["area_ratio"] is None
        assert data["fidelity"]["volume_ratio"] is None
        assert data["reconstructed_properties"]["volume_m3"] is None
        assert data["reconstructed_properties"]["surface_area_m2"] is None

    def test_normal_metrics_unchanged(self, client_and_db):
        """Normal float values should pass through unchanged."""
        normal_metrics = {
            "original_volume": 1.0,
            "original_area": 2.0,
            "reconstructed_volume": 0.95,
            "reconstructed_area": 1.85,
            "volume_ratio": 0.95,
            "area_ratio": 0.925,
        }
        client, _ = client_and_db
        resp = self._mock_slice(client, normal_metrics)
        assert resp.status_code == 200
        data = resp.json()
        assert data["fidelity"]["area_ratio"] == 0.925
        assert data["fidelity"]["volume_ratio"] == 0.95
