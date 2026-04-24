"""Tests for app.services.design_version_service.

Covers all public CRUD functions, internal helpers (_compute_diff,
_diff_lists, serialization), and error paths (NotFoundError, DB errors).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignVersionModel,
    MissionObjectivesModel,
    WeightItemModel,
)
from app.schemas.design_version import (
    DesignVersionCreate,
    DesignVersionDiff,
    DesignVersionRead,
    DesignVersionSummary,
)
from app.services.design_version_service import (
    _build_snapshot,
    _compute_diff,
    _diff_lists,
    _get_aeroplane,
    _get_version,
    _serialize_fuselage,
    _serialize_mission_objectives,
    _serialize_weight_items,
    _serialize_wing,
    create_version,
    delete_version,
    diff_versions,
    get_version,
    list_versions,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_mock_aeroplane(
    *,
    aeroplane_id: int = 1,
    aeroplane_uuid: uuid.UUID | None = None,
    name: str = "test-plane",
    total_mass_kg: float | None = 5.0,
    xyz_ref: list[float] | None = None,
    wings: list | None = None,
    fuselages: list | None = None,
    mission_objectives: Any = None,
    weight_items: list | None = None,
    design_versions: list | None = None,
) -> MagicMock:
    ap = MagicMock(spec=AeroplaneModel)
    ap.id = aeroplane_id
    ap.uuid = aeroplane_uuid or uuid.uuid4()
    ap.name = name
    ap.total_mass_kg = total_mass_kg
    ap.xyz_ref = xyz_ref or [0.0, 0.0, 0.0]
    ap.wings = wings or []
    ap.fuselages = fuselages or []
    ap.mission_objectives = mission_objectives
    ap.weight_items = weight_items or []
    ap.design_versions = design_versions or []
    return ap


def _make_mock_version(
    *,
    version_id: int = 10,
    label: str = "v1",
    description: str | None = None,
    parent_version_id: int | None = None,
    snapshot: dict | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    ver = MagicMock(spec=DesignVersionModel)
    ver.id = version_id
    ver.label = label
    ver.description = description
    ver.parent_version_id = parent_version_id
    ver.snapshot = snapshot or {"name": "test"}
    ver.created_at = created_at or datetime.now(timezone.utc)
    return ver


def _make_mock_xsec(columns: dict[str, Any], wing_id: int = 1) -> MagicMock:
    """Create a mock cross-section with __table__.columns support."""
    xsec = MagicMock()
    xsec.sort_index = columns.get("sort_index", 0)

    # Build mock columns
    mock_cols = []
    for col_name in columns:
        col = MagicMock()
        col.name = col_name
        mock_cols.append(col)
    # Add the excluded columns so the filter logic is exercised
    for excluded in ("id", "wing_id"):
        col = MagicMock()
        col.name = excluded
        mock_cols.append(col)

    xsec.__table__ = MagicMock()
    xsec.__table__.columns = mock_cols

    # Make getattr work for each column
    for col_name, val in columns.items():
        setattr(xsec, col_name, val)
    xsec.id = 99
    xsec.wing_id = wing_id
    return xsec


def _make_mock_fuselage_xsec(columns: dict[str, Any], fuselage_id: int = 1) -> MagicMock:
    xsec = MagicMock()
    xsec.sort_index = columns.get("sort_index", 0)

    mock_cols = []
    for col_name in columns:
        col = MagicMock()
        col.name = col_name
        mock_cols.append(col)
    for excluded in ("id", "fuselage_id"):
        col = MagicMock()
        col.name = excluded
        mock_cols.append(col)

    xsec.__table__ = MagicMock()
    xsec.__table__.columns = mock_cols

    for col_name, val in columns.items():
        setattr(xsec, col_name, val)
    xsec.id = 99
    xsec.fuselage_id = fuselage_id
    return xsec


# ── _get_aeroplane ─────────────────────────────────────────────────────


class TestGetAeroplane:
    def test_found(self):
        mock_db = MagicMock()
        ap = _make_mock_aeroplane()
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        result = _get_aeroplane(mock_db, ap.uuid)
        assert result is ap

    def test_not_found_raises(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(NotFoundError) as exc_info:
            _get_aeroplane(mock_db, uuid.uuid4())
        assert "Aeroplane" in str(exc_info.value)


# ── _get_version ────────────────────────────────────────────────────────


class TestGetVersion:
    def test_found(self):
        v1 = _make_mock_version(version_id=1)
        v2 = _make_mock_version(version_id=2)
        ap = _make_mock_aeroplane(design_versions=[v1, v2])
        assert _get_version(ap, 2) is v2

    def test_not_found_raises(self):
        ap = _make_mock_aeroplane(design_versions=[])
        with pytest.raises(NotFoundError) as exc_info:
            _get_version(ap, 999)
        assert "DesignVersion" in str(exc_info.value)


# ── Serialization helpers ──────────────────────────────────────────────


class TestSerializeWing:
    def test_basic_wing(self):
        xsec = _make_mock_xsec({
            "sort_index": 0,
            "chord": 0.3,
            "twist": 2.0,
            "airfoil": "naca0012",
        })
        wing = MagicMock()
        wing.name = "main_wing"
        wing.symmetric = True
        wing.x_secs = [xsec]

        result = _serialize_wing(wing)
        assert result["name"] == "main_wing"
        assert result["symmetric"] is True
        assert len(result["x_secs"]) == 1
        xs = result["x_secs"][0]
        assert xs["sort_index"] == 0
        assert xs["chord"] == 0.3
        assert xs["twist"] == 2.0
        assert xs["airfoil"] == "naca0012"
        # Excluded columns must not appear
        assert "id" not in xs
        assert "wing_id" not in xs

    def test_empty_xsecs(self):
        wing = MagicMock()
        wing.name = "bare_wing"
        wing.symmetric = False
        wing.x_secs = []
        result = _serialize_wing(wing)
        assert result["x_secs"] == []


class TestSerializeFuselage:
    def test_basic_fuselage(self):
        xsec = _make_mock_fuselage_xsec({
            "sort_index": 0,
            "radius": 0.1,
        })
        fus = MagicMock()
        fus.name = "main_fus"
        fus.x_secs = [xsec]

        result = _serialize_fuselage(fus)
        assert result["name"] == "main_fus"
        assert len(result["x_secs"]) == 1
        assert "id" not in result["x_secs"][0]
        assert "fuselage_id" not in result["x_secs"][0]


class TestSerializeMissionObjectives:
    def test_none_returns_none(self):
        assert _serialize_mission_objectives(None) is None

    def test_with_objectives(self):
        obj = MagicMock(spec=MissionObjectivesModel)
        col_payload = MagicMock()
        col_payload.name = "payload_kg"
        col_id = MagicMock()
        col_id.name = "id"
        col_ap = MagicMock()
        col_ap.name = "aeroplane_id"
        obj.__table__ = MagicMock()
        obj.__table__.columns = [col_id, col_ap, col_payload]
        obj.payload_kg = 2.5

        result = _serialize_mission_objectives(obj)
        assert result == {"payload_kg": 2.5}
        assert "id" not in result
        assert "aeroplane_id" not in result


class TestSerializeWeightItems:
    def test_empty_list(self):
        assert _serialize_weight_items([]) == []

    def test_with_items(self):
        item = MagicMock(spec=WeightItemModel)
        col_id = MagicMock()
        col_id.name = "id"
        col_ap = MagicMock()
        col_ap.name = "aeroplane_id"
        col_name = MagicMock()
        col_name.name = "name"
        col_mass = MagicMock()
        col_mass.name = "mass_kg"
        item.__table__ = MagicMock()
        item.__table__.columns = [col_id, col_ap, col_name, col_mass]
        item.name = "battery"
        item.mass_kg = 0.5

        result = _serialize_weight_items([item])
        assert len(result) == 1
        assert result[0] == {"name": "battery", "mass_kg": 0.5}


class TestBuildSnapshot:
    def test_full_snapshot(self):
        wing = MagicMock()
        wing.name = "w1"
        wing.symmetric = True
        wing.x_secs = []

        fus = MagicMock()
        fus.name = "f1"
        fus.x_secs = []

        ap = _make_mock_aeroplane(
            name="my-plane",
            total_mass_kg=3.0,
            xyz_ref=[0.1, 0.2, 0.3],
            wings=[wing],
            fuselages=[fus],
            mission_objectives=None,
            weight_items=[],
        )

        result = _build_snapshot(ap)
        assert result["name"] == "my-plane"
        assert result["total_mass_kg"] == 3.0
        assert result["xyz_ref"] == [0.1, 0.2, 0.3]
        assert len(result["wings"]) == 1
        assert len(result["fuselages"]) == 1
        assert result["mission_objectives"] is None
        assert result["weight_items"] == []


# ── list_versions ──────────────────────────────────────────────────────


class TestListVersions:
    def test_returns_summaries(self):
        mock_db = MagicMock()
        now = datetime.now(timezone.utc)
        v1 = _make_mock_version(version_id=1, label="v1", created_at=now)
        v2 = _make_mock_version(version_id=2, label="v2", created_at=now)
        ap = _make_mock_aeroplane(design_versions=[v1, v2])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        result = list_versions(mock_db, ap.uuid)
        assert len(result) == 2
        assert all(isinstance(s, DesignVersionSummary) for s in result)
        assert result[0].label == "v1"
        assert result[1].label == "v2"

    def test_empty_list(self):
        mock_db = MagicMock()
        ap = _make_mock_aeroplane(design_versions=[])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        result = list_versions(mock_db, ap.uuid)
        assert result == []

    def test_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(NotFoundError):
            list_versions(mock_db, uuid.uuid4())


# ── create_version ─────────────────────────────────────────────────────


class TestCreateVersion:
    def test_success(self):
        mock_db = MagicMock()
        now = datetime.now(timezone.utc)
        ap = _make_mock_aeroplane(
            wings=[], fuselages=[], weight_items=[], mission_objectives=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        # After commit + refresh, the version object should have an id and created_at
        def fake_refresh(obj):
            obj.id = 42
            obj.created_at = now
            obj.parent_version_id = None

        mock_db.refresh.side_effect = fake_refresh

        data = DesignVersionCreate(label="snapshot-1", description="first version")
        result = create_version(mock_db, ap.uuid, data)

        assert isinstance(result, DesignVersionSummary)
        assert result.id == 42
        assert result.label == "snapshot-1"
        assert result.description == "first version"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        data = DesignVersionCreate(label="x")
        with pytest.raises(NotFoundError):
            create_version(mock_db, uuid.uuid4(), data)

    def test_db_error_rolls_back(self):
        mock_db = MagicMock()
        ap = _make_mock_aeroplane(
            wings=[], fuselages=[], weight_items=[], mission_objectives=None
        )
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        mock_db.commit.side_effect = SQLAlchemyError("disk full")

        data = DesignVersionCreate(label="boom")
        with pytest.raises(InternalError, match="Database error"):
            create_version(mock_db, ap.uuid, data)
        mock_db.rollback.assert_called_once()


# ── get_version (CRUD) ──────────────────────────────────────────────────


class TestGetVersionCrud:
    def test_success(self):
        mock_db = MagicMock()
        now = datetime.now(timezone.utc)
        snap = {"name": "plane", "wings": []}
        ver = _make_mock_version(version_id=5, label="v5", snapshot=snap, created_at=now)
        ap = _make_mock_aeroplane(design_versions=[ver])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        result = get_version(mock_db, ap.uuid, 5)
        assert isinstance(result, DesignVersionRead)
        assert result.id == 5
        assert result.snapshot == snap

    def test_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(NotFoundError):
            get_version(mock_db, uuid.uuid4(), 1)

    def test_version_not_found(self):
        mock_db = MagicMock()
        ap = _make_mock_aeroplane(design_versions=[])
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        with pytest.raises(NotFoundError):
            get_version(mock_db, ap.uuid, 999)


# ── delete_version ──────────────────────────────────────────────────────


class TestDeleteVersion:
    def test_success(self):
        mock_db = MagicMock()
        ver = _make_mock_version(version_id=7)
        ap = _make_mock_aeroplane(design_versions=[ver])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        delete_version(mock_db, ap.uuid, 7)
        mock_db.delete.assert_called_once_with(ver)
        mock_db.commit.assert_called_once()

    def test_aeroplane_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(NotFoundError):
            delete_version(mock_db, uuid.uuid4(), 1)

    def test_version_not_found(self):
        mock_db = MagicMock()
        ap = _make_mock_aeroplane(design_versions=[])
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        with pytest.raises(NotFoundError):
            delete_version(mock_db, ap.uuid, 1)

    def test_db_error_rolls_back(self):
        mock_db = MagicMock()
        ver = _make_mock_version(version_id=7)
        ap = _make_mock_aeroplane(design_versions=[ver])
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        mock_db.commit.side_effect = SQLAlchemyError("lock timeout")

        with pytest.raises(InternalError, match="Database error"):
            delete_version(mock_db, ap.uuid, 7)
        mock_db.rollback.assert_called_once()


# ── diff_versions ──────────────────────────────────────────────────────


class TestDiffVersions:
    def test_identical_snapshots(self):
        mock_db = MagicMock()
        snap = {"name": "same", "mass": 5.0}
        v1 = _make_mock_version(version_id=1, snapshot=snap)
        v2 = _make_mock_version(version_id=2, snapshot=dict(snap))  # copy
        ap = _make_mock_aeroplane(design_versions=[v1, v2])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        result = diff_versions(mock_db, ap.uuid, 1, 2)
        assert isinstance(result, DesignVersionDiff)
        assert result.version_a == 1
        assert result.version_b == 2
        assert result.changes == []

    def test_with_changes(self):
        mock_db = MagicMock()
        snap_a = {"name": "old", "mass": 5.0}
        snap_b = {"name": "new", "mass": 5.0}
        v1 = _make_mock_version(version_id=1, snapshot=snap_a)
        v2 = _make_mock_version(version_id=2, snapshot=snap_b)
        ap = _make_mock_aeroplane(design_versions=[v1, v2])
        mock_db.query.return_value.filter.return_value.first.return_value = ap

        result = diff_versions(mock_db, ap.uuid, 1, 2)
        assert len(result.changes) == 1
        assert result.changes[0]["path"] == "name"
        assert result.changes[0]["type"] == "changed"

    def test_version_not_found(self):
        mock_db = MagicMock()
        v1 = _make_mock_version(version_id=1)
        ap = _make_mock_aeroplane(design_versions=[v1])
        mock_db.query.return_value.filter.return_value.first.return_value = ap
        with pytest.raises(NotFoundError):
            diff_versions(mock_db, ap.uuid, 1, 999)


# ── _compute_diff ──────────────────────────────────────────────────────


class TestComputeDiff:
    def test_no_changes(self):
        assert _compute_diff({"a": 1}, {"a": 1}) == []

    def test_changed_value(self):
        changes = _compute_diff({"x": 1}, {"x": 2})
        assert len(changes) == 1
        assert changes[0] == {"path": "x", "type": "changed", "old": 1, "new": 2}

    def test_added_key(self):
        changes = _compute_diff({}, {"new_key": 42})
        assert len(changes) == 1
        assert changes[0] == {"path": "new_key", "type": "added", "value": 42}

    def test_removed_key(self):
        changes = _compute_diff({"old_key": 42}, {})
        assert len(changes) == 1
        assert changes[0] == {"path": "old_key", "type": "removed", "value": 42}

    def test_nested_dict_diff(self):
        a = {"outer": {"inner": 1}}
        b = {"outer": {"inner": 2}}
        changes = _compute_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "outer.inner"
        assert changes[0]["type"] == "changed"

    def test_nested_list_diff(self):
        a = {"items": [1, 2]}
        b = {"items": [1, 3]}
        changes = _compute_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "items[1]"
        assert changes[0]["old"] == 2
        assert changes[0]["new"] == 3

    def test_multiple_changes_sorted_by_key(self):
        a = {"b": 1, "a": 2}
        b = {"b": 10, "a": 20}
        changes = _compute_diff(a, b)
        assert len(changes) == 2
        # Keys are sorted: "a" before "b"
        assert changes[0]["path"] == "a"
        assert changes[1]["path"] == "b"

    def test_prefix_propagation(self):
        changes = _compute_diff({"k": 1}, {"k": 2}, prefix="root")
        assert changes[0]["path"] == "root.k"

    def test_none_to_value_is_added(self):
        changes = _compute_diff({"k": None}, {"k": 42})
        assert changes[0]["type"] == "added"
        assert changes[0]["value"] == 42

    def test_value_to_none_is_removed(self):
        changes = _compute_diff({"k": 42}, {"k": None})
        assert changes[0]["type"] == "removed"
        assert changes[0]["value"] == 42

    def test_both_none_no_change(self):
        assert _compute_diff({"k": None}, {"k": None}) == []


# ── _diff_lists ─────────────────────────────────────────────────────────


class TestDiffLists:
    def test_identical_lists(self):
        assert _diff_lists([1, 2, 3], [1, 2, 3], "items") == []

    def test_changed_element(self):
        changes = _diff_lists([1], [2], "arr")
        assert changes == [{"path": "arr[0]", "type": "changed", "old": 1, "new": 2}]

    def test_added_element(self):
        changes = _diff_lists([], [99], "arr")
        assert changes == [{"path": "arr[0]", "type": "added", "value": 99}]

    def test_removed_element(self):
        changes = _diff_lists([99], [], "arr")
        assert changes == [{"path": "arr[0]", "type": "removed", "value": 99}]

    def test_nested_dict_in_list(self):
        a = [{"x": 1}]
        b = [{"x": 2}]
        changes = _diff_lists(a, b, "items")
        assert len(changes) == 1
        assert changes[0]["path"] == "items[0].x"

    def test_mixed_lengths(self):
        a = [10, 20]
        b = [10, 20, 30, 40]
        changes = _diff_lists(a, b, "arr")
        assert len(changes) == 2
        assert changes[0]["path"] == "arr[2]"
        assert changes[0]["type"] == "added"
        assert changes[1]["path"] == "arr[3]"

    def test_both_empty(self):
        assert _diff_lists([], [], "arr") == []

    def test_longer_a_than_b(self):
        changes = _diff_lists([1, 2, 3], [1], "arr")
        assert len(changes) == 2
        assert changes[0] == {"path": "arr[1]", "type": "removed", "value": 2}
        assert changes[1] == {"path": "arr[2]", "type": "removed", "value": 3}
