"""Regression test for gh#815: alpha_sweep returns 500 on non-finite floats.

Cause: AeroBuildup can emit non-finite coefficients (NaN / +/-Inf) — e.g. a
degenerate fuselage with zero volume yields ``length**3 / volume`` -> NaN and a
zero Reynolds number yields ``log10(0)`` -> -inf. The aero analysis endpoints
return these raw computed dicts, and FastAPI serializes them through Starlette's
``JSONResponse.render``, which calls ``json.dumps(content, allow_nan=False)``.
stdlib json then raises ``ValueError: Out of range float values are not JSON
compliant`` -> unhandled HTTP 500 (the crash escapes the endpoint's try/except
because serialization happens after the handler returns).

Fix: the aero router serializes via a response class that represents non-finite
floats as JSON ``null`` — an honest "no value", not a fabricated fallback.

Two layers of tests:

1. Unit: the ``replace_nonfinite`` helper maps NaN/Inf (incl. numpy floats) to
   None recursively while preserving every finite/other value.
2. Integration: a real request through the aero router whose service returns a
   NaN/Inf-laden payload must respond 200 with nulls, not 500.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import numpy as np

from app.core.json_safe import replace_nonfinite


class TestReplaceNonFinite:
    def test_nan_and_infinities_become_none(self):
        assert replace_nonfinite(float("nan")) is None
        assert replace_nonfinite(float("inf")) is None
        assert replace_nonfinite(float("-inf")) is None

    def test_numpy_nonfinite_become_none(self):
        assert replace_nonfinite(np.float64("nan")) is None
        assert replace_nonfinite(np.float64("inf")) is None
        assert replace_nonfinite(np.float32("-inf")) is None

    def test_finite_and_other_values_preserved(self):
        assert replace_nonfinite(0.0) == 0.0
        assert replace_nonfinite(-3.5) == -3.5
        assert replace_nonfinite(7) == 7
        assert replace_nonfinite("ok") == "ok"
        assert replace_nonfinite(True) is True
        assert replace_nonfinite(None) is None

    def test_nested_structures_are_sanitized(self):
        payload = {
            "coefficients": {
                "CL": [0.1, float("nan"), 0.5],
                "CD": (0.01, float("inf"), 0.02),
            },
            "points": [{"alpha": float("-inf"), "CL": 1.2}],
            "name": "wing",
        }
        result = replace_nonfinite(payload)
        assert result["coefficients"]["CL"] == [0.1, None, 0.5]
        assert result["coefficients"]["CD"] == [0.01, None, 0.02]
        assert result["points"][0]["alpha"] is None
        assert result["points"][0]["CL"] == 1.2
        assert result["name"] == "wing"


class TestAlphaSweepEndpointDoesNotCrashOnNonFinite:
    def test_alpha_sweep_returns_200_with_nulls_not_500(self, client_and_db):
        client, _ = client_and_db
        plane_id = uuid.uuid4()

        # Payload shaped like a real alpha_sweep result, but with the non-finite
        # values AeroBuildup emits for degenerate geometry / zero Reynolds number.
        nan_payload = {
            "analysis": {
                "coefficients": {
                    "CL": [0.1, float("nan"), 0.5],
                    "CD": [0.01, float("inf"), 0.02],
                    "Cm": [-0.05, 0.0, float("-inf")],
                }
            },
            "characteristic_points": {
                "stall_point": {"alpha_deg": float("nan"), "CL": 1.2},
            },
            "speed_polar": None,
            "aircraft_name": "test-plane",
        }

        with patch(
            "app.services.analysis_service.analyze_alpha_sweep",
            new=AsyncMock(return_value=nan_payload),
        ):
            res = client.post(f"/aeroplanes/{plane_id}/alpha_sweep", json={})

        assert res.status_code == 200, f"expected 200, got {res.status_code}: {res.text[:300]}"
        body = res.json()
        coeffs = body["analysis"]["coefficients"]
        assert coeffs["CL"] == [0.1, None, 0.5]
        assert coeffs["CD"] == [0.01, None, 0.02]
        assert coeffs["Cm"] == [-0.05, 0.0, None]
        assert body["characteristic_points"]["stall_point"]["alpha_deg"] is None
        assert body["characteristic_points"]["stall_point"]["CL"] == 1.2
        assert body["aircraft_name"] == "test-plane"
