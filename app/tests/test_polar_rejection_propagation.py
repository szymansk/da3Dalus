"""gh-630: end-to-end check that polar_by_config.rejection is exposed via the
get_computation_context API endpoint.

The test drives `recompute_assumptions` (service layer, not HTTP) with all
ASB-bound helpers stubbed out and `_fit_parabolic_polar` returning a synthetic
rejection.  It then fetches the cached context via the real HTTP endpoint and
asserts the rejection dict is present in the `clean` config slot.

Design choices:
- No HTTP recompute endpoint exists — the service is triggered directly, which
  is the same pattern used by all other assumption-compute tests.
- The `client_and_db` fixture yields `(TestClient, SessionLocal)` — a 2-tuple.
- URL confirmed from design_assumptions.py: `/aeroplanes/{uuid}/assumptions/
  computation-context` (no `/api/v2` prefix; the app is mounted at the root).
- The mock returns the same 4-tuple for every `_fit_parabolic_polar` call.
  All three configs (clean, takeoff, landing) therefore receive the same
  rejection.  The assertion only checks the `clean` slot.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from app.schemas.polar_by_config import PolarRejection
from app.services.assumption_compute_service import recompute_assumptions
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_REJECTION = PolarRejection(
    gate="negative_slope_k",
    category="design",
    fitted_value=-0.001,
    threshold="k > 0",
    hint="Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
)

_EXPECTED_REJECTION_DICT = {
    "gate": "negative_slope_k",
    "category": "design",
    "fitted_value": -0.001,
    "threshold": "k > 0",
    "hint": "Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
}


def _make_fake_airplane() -> SimpleNamespace:
    """Minimal stub for asb_airplane — no flap → fallback to clean polar for all configs."""
    fake_wing = SimpleNamespace(
        area=lambda: 0.30,
        mean_aerodynamic_chord=lambda: 0.20,
        span=lambda: 1.5,
        xsecs=[SimpleNamespace(control_surfaces=[])],
    )
    plane = SimpleNamespace(
        wings=[fake_wing],
        xyz_ref=[0.08, 0.0, 0.0],
        s_ref=0.30,
        c_ref=0.20,
        b_ref=1.5,
    )
    plane.with_control_deflections = lambda _mapping: plane
    return plane


@contextlib.contextmanager
def _enter_patches_with_rejection():
    """Stub all ASB-bound helpers and inject the synthetic rejection via
    `_fit_parabolic_polar`."""
    cl_array = np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
    cd_array = np.array([0.026, 0.028, 0.032, 0.039, 0.049, 0.062])
    v_array = np.linspace(9.0, 28.0, 6)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._build_asb_airplane",
                return_value=_make_fake_airplane(),
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._stability_run_at_cruise",
                return_value=(0.085, 0.20, 0.025, 0.30),  # x_np, MAC, CD0, s_ref
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._coarse_alpha_sweep",
                return_value=15.0,
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._fine_sweep_cl_max",
                return_value=(1.35, cl_array, cd_array, v_array, np.zeros_like(cl_array)),
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._extract_cl_alpha_from_linear_sweep",
                return_value=5.7,
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._load_flight_profile_speeds",
                return_value=(18.0, 28.0, True),
            )
        )
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._extract_flap_ted_max",
                return_value=None,  # no flap → clean polar cloned to takeoff / landing
            )
        )
        # The key stub: every call to _fit_parabolic_polar returns the synthetic rejection.
        stack.enter_context(
            patch(
                "app.services.assumption_compute_service._fit_parabolic_polar",
                return_value=(None, None, None, _FAKE_REJECTION),
            )
        )
        yield


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestRejectionInComputationContextEndpoint:
    """gh-630: rejection is serialised through the full stack to the HTTP response."""

    def test_design_rejection_is_serialised(self, client_and_db):
        """After a recompute that produces a rejection, the GET computation-context
        endpoint returns the rejection dict nested inside polar_by_config.clean."""
        client, SessionLocal = client_and_db

        # --- arrange: create an aeroplane and seed default assumptions ---
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            seed_defaults(db, str(aeroplane.uuid))
            db.commit()
            aeroplane_uuid = str(aeroplane.uuid)

        # --- act: run recompute with the synthetic rejection injected ---
        with _enter_patches_with_rejection():
            with SessionLocal() as db:
                recompute_assumptions(db, aeroplane_uuid)
                db.commit()

        # --- assert: HTTP endpoint exposes the rejection ---
        r = client.get(f"/aeroplanes/{aeroplane_uuid}/assumptions/computation-context")
        assert r.status_code == 200, r.text
        ctx = r.json()

        assert "polar_by_config" in ctx, "polar_by_config key missing from context"
        clean = ctx["polar_by_config"]["clean"]
        assert clean["rejection"] == _EXPECTED_REJECTION_DICT, (
            f"Expected rejection dict {_EXPECTED_REJECTION_DICT!r}, got {clean['rejection']!r}"
        )
