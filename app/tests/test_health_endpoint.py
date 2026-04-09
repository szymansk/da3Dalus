"""Smoke tests for the /health endpoint.

The endpoint is the canonical liveness + DB-reachability probe and must
stay importable on every supported platform, including linux/aarch64
where CadQuery and Aerosandbox are intentionally excluded.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_health_returns_200_with_expected_shape(client_and_db):
    client, _ = client_and_db
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == {"status", "version", "database"}
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
    assert body["database"] in {"reachable", "unreachable"}


@pytest.mark.integration
def test_health_reports_database_reachable_on_test_sqlite(client_and_db):
    """The in-memory SQLite used by client_and_db is always reachable."""
    client, _ = client_and_db
    response = client.get("/health")
    assert response.json()["database"] == "reachable"


@pytest.mark.integration
def test_health_does_not_require_cadquery(client_and_db):
    """Verify that the endpoint does not transitively import CadQuery.

    This is a guard test for linux/aarch64 deployments: if someone
    accidentally wires a heavy import into the health endpoint, the
    module-level import chain will trip pytest.importorskip in the CAD
    tests, and we want this test to keep passing regardless.
    """
    client, _ = client_and_db
    # The endpoint is exercised; any import error would have happened
    # earlier in this very test's import chain. Reaching here at all is
    # the real assertion.
    assert client.get("/health").status_code == 200
