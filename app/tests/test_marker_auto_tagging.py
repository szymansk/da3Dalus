"""Tests for the auto-tagging logic that derives pytest markers from test file paths.

gh-504: replaces the discipline of marking every test by hand. The
``pytest_collection_modifyitems`` hook in ``conftest.py`` delegates to
:func:`conftest._markers_for_path` to decide which markers a given test
file should receive. This module pins the mapping so a future rename
does not silently move a test between tiers.
"""

from __future__ import annotations

import pytest

from app.tests.conftest import _markers_for_path, pytest_collection_modifyitems


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
        # Non-integration AVL file with runner-like name still gets requires_avl
        # (intentional — strip_forces tests invoke the real binary).
        ("/repo/app/tests/test_avl_strip_forces.py", {"requires_avl"}),
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
        # Multiple markers can stack: synthetic case showing that an e2e
        # file with _integration in its name picks up both. No such file
        # currently exists in app/tests/ — it pins the helper's behaviour.
        (
            "/repo/app/tests/test_some_e2e_integration.py",  # synthetic
            {"e2e", "integration"},
        ),
        # Directory components must not leak into the heuristic: the
        # helper uses os.path.basename, so a containing directory named
        # "_e2e" does not promote a plain unit test.
        ("/repo/_e2e/test_api_utils.py", set()),
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


class _FakeItem:
    """Minimal stand-in for ``pytest.Item`` used to drive the hook in isolation.

    The real ``pytest.Item`` carries a lot of pytest-internal state we do
    not need to exercise the hook's marker-application logic.
    """

    def __init__(self, path: str) -> None:
        self.path = path  # the hook calls str(item.path)
        self.applied: list[str] = []

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        self.applied.append(marker.name)


def test_hook_applies_markers_to_collected_items() -> None:
    """End-to-end: feed mock items through the real hook and assert the
    applied marker names.

    A weaker ``callable(...)`` check on the hook symbol would pass even if
    the hook body were broken (typo in ``add_marker``, wrong attribute
    access, etc.). This test exercises the real call path so any such
    regression surfaces immediately.
    """
    tessellation_item = _FakeItem("/x/test_tessellation_endpoint.py")
    e2e_item = _FakeItem("/x/test_some_workflow_e2e.py")
    plain_item = _FakeItem("/x/test_api_utils.py")
    avl_runner = _FakeItem("/x/test_avl_runner.py")

    pytest_collection_modifyitems(
        None,  # type: ignore[arg-type] — hook ignores config
        [tessellation_item, e2e_item, plain_item, avl_runner],  # type: ignore[list-item]
    )

    assert tessellation_item.applied == ["requires_cadquery"]
    assert e2e_item.applied == ["e2e"]
    assert plain_item.applied == []
    assert avl_runner.applied == ["requires_avl"]
