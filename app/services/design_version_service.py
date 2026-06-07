"""Design Version Service — RETIRED (gh-903).

The JSON-snapshot ``design_versions`` table has been dropped and replaced by
the row-copy versioning system (BranchModel + new AeroplaneModel columns).
This module is preserved as a stub so that existing imports do not break
while the API endpoints are re-wired in gh-905 (Version operations + API).

TODO(gh-905): replace all functions below with the new versioning service.
"""

from app.core.exceptions import NotFoundError
from app.schemas.design_version import (  # noqa: F401 — re-exported for compat
    DesignVersionCreate,
    DesignVersionDiff,
    DesignVersionRead,
    DesignVersionSummary,
)


def list_versions(db, aeroplane_uuid):  # type: ignore[no-untyped-def]
    """Stub — design_versions table has been dropped (gh-903)."""
    raise NotFoundError(
        entity="DesignVersion",
        resource_id="n/a",
    )


def create_version(db, aeroplane_uuid, data):  # type: ignore[no-untyped-def]
    """Stub — design_versions table has been dropped (gh-903)."""
    raise NotFoundError(
        entity="DesignVersion",
        resource_id="n/a",
    )


def get_version(db, aeroplane_uuid, version_id: int):  # type: ignore[no-untyped-def]
    """Stub — design_versions table has been dropped (gh-903)."""
    raise NotFoundError(
        entity="DesignVersion",
        resource_id=version_id,
    )


def delete_version(db, aeroplane_uuid, version_id: int):  # type: ignore[no-untyped-def]
    """Stub — design_versions table has been dropped (gh-903)."""
    raise NotFoundError(
        entity="DesignVersion",
        resource_id=version_id,
    )


def diff_versions(db, aeroplane_uuid, version_a_id: int, version_b_id: int):  # type: ignore[no-untyped-def]
    """Stub — design_versions table has been dropped (gh-903)."""
    raise NotFoundError(
        entity="DesignVersion",
        resource_id=version_a_id,
    )
