"""Tests for the auto-tagging logic that derives pytest markers from test file paths.

gh-504: replaces the discipline of marking every test by hand. The
``pytest_collection_modifyitems`` hook in ``conftest.py`` delegates to
:func:`conftest._markers_for_path` to decide which markers a given test
file should receive. This module pins the mapping so a future rename
does not silently move a test between tiers.
"""

from __future__ import annotations

import pytest

from app.tests.conftest import _markers_for_path


@pytest.mark.parametrize(
    "path, expected",
    [
        # E2E / smoke -> e2e tier
        ("/repo/app/tests/test_aeroplane_wing_from_wingconfig_e2e.py", {"e2e"}),
        ("/repo/app/tests/test_analysis_smoke.py", {"e2e"}),
        # Integration -> integration tier
        ("/repo/app/tests/test_health_endpoint.py", set()),
        ("/repo/app/tests/test_assumption_compute_integration.py", {"integration"}),
        ("/repo/app/tests/test_ehawk_designer_workflow_integration.py", {"integration"}),
        # CadQuery-heavy files
        ("/repo/app/tests/test_tessellation_endpoint.py", {"requires_cadquery"}),
        ("/repo/app/tests/test_tessellation_cache.py", {"requires_cadquery"}),
        ("/repo/app/tests/test_fuselage_slice_quality.py", {"requires_cadquery"}),
        # AVL pipeline files
        (
            "/repo/app/tests/test_avl_generator_integration.py",
            {"requires_avl", "integration"},
        ),
        ("/repo/app/tests/test_avl_runner.py", {"requires_avl"}),
        (
            "/repo/app/tests/test_avl_strip_forces_integration.py",
            {"requires_avl", "integration"},
        ),
        # AVL files that are NOT runner/generator/strip_forces stay untagged
        ("/repo/app/tests/test_avl_dataclasses.py", set()),
        ("/repo/app/tests/test_avl_geometry.py", set()),
        # Plain unit tests get no auto-marker
        ("/repo/app/tests/test_api_utils.py", set()),
        ("/repo/app/tests/test_aeroplane_base.py", set()),
        # Multiple markers can stack: e2e file that also has _integration
        # in its name should pick up both (defensive — current files do not
        # actually overlap, but the hook must not be exclusive).
        (
            "/repo/app/tests/test_some_e2e_integration.py",
            {"e2e", "integration"},
        ),
    ],
)
def test_markers_for_path(path: str, expected: set[str]) -> None:
    assert set(_markers_for_path(path)) == expected


def test_marker_helper_is_idempotent() -> None:
    """Repeated calls on the same path produce the same marker set.

    Guards against any state leak inside the helper (e.g. a class-level cache).
    """
    path = "/repo/app/tests/test_tessellation_endpoint.py"
    first = set(_markers_for_path(path))
    second = set(_markers_for_path(path))
    assert first == second == {"requires_cadquery"}


def test_hook_is_registered() -> None:
    """``pytest_collection_modifyitems`` must be importable from conftest.

    Guards against the case where the helper is correct but the hook
    itself was deleted or renamed, leaving the auto-tagging silently
    inactive.
    """
    from app.tests import conftest

    assert callable(getattr(conftest, "pytest_collection_modifyitems", None)), (
        "conftest.py must expose pytest_collection_modifyitems for "
        "auto-tagging to take effect."
    )
