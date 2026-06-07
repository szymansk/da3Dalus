"""Tests for app.services.design_version_service (RETIRED, gh-903).

The JSON-snapshot design_versions table has been dropped.  The service is now
a stub that raises NotFoundError for every call.  These tests verify:
  - The module still imports cleanly (no missing symbols).
  - Every public function raises NotFoundError (not AttributeError or anything
    that would break the API layer).

TODO(gh-905): replace with tests for the new versioning service once the
              row-copy operations are implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.services import design_version_service as svc
from app.schemas.design_version import DesignVersionCreate  # still importable


class TestDesignVersionServiceStub:
    """All public entry points must raise NotFoundError (the stub contract)."""

    def test_list_versions_raises(self):
        with pytest.raises(NotFoundError):
            svc.list_versions(MagicMock(), "any-uuid")

    def test_create_version_raises(self):
        data = DesignVersionCreate(label="v1")
        with pytest.raises(NotFoundError):
            svc.create_version(MagicMock(), "any-uuid", data)

    def test_get_version_raises(self):
        with pytest.raises(NotFoundError):
            svc.get_version(MagicMock(), "any-uuid", 1)

    def test_delete_version_raises(self):
        with pytest.raises(NotFoundError):
            svc.delete_version(MagicMock(), "any-uuid", 1)

    def test_diff_versions_raises(self):
        with pytest.raises(NotFoundError):
            svc.diff_versions(MagicMock(), "any-uuid", 1, 2)
