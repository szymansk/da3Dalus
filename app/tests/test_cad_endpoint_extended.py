"""Extended tests for app/api/v2/endpoints/cad.py.

Covers the helper functions (_raise_http_from_domain, _ensure_file_under_tmp,
_offset_refs, _expand_bounding_box, _merge_tessellation_entries) and all
endpoint error-handling branches that were not exercised by existing tests.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from pathlib import Path as FilePath
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v2.endpoints.cad import (
    _ensure_file_under_tmp,
    _expand_bounding_box,
    _merge_tessellation_entries,
    _offset_refs,
    _raise_http_from_domain,
    create_wing_loft,
    download_aeroplane_zip,
    get_aeroplane_task_status,
    get_aeroplane_tessellation,
    start_wing_tessellation,
)
from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.schemas.AeroplaneRequest import CreatorUrlType, ExporterUrlType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def plane_id():
    return uuid.uuid4()


@pytest.fixture()
def mock_db():
    return MagicMock()


# ---------------------------------------------------------------------------
# _raise_http_from_domain — all branches
# ---------------------------------------------------------------------------


class TestRaiseHttpFromDomain:
    def test_not_found_maps_to_404(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(NotFoundError("missing"))
        assert exc_info.value.status_code == 404

    def test_validation_error_maps_to_422(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ValidationError("bad"))
        assert exc_info.value.status_code == 422

    def test_validation_domain_error_maps_to_422(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ValidationDomainError("domain"))
        assert exc_info.value.status_code == 422

    def test_conflict_error_maps_to_409(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ConflictError("conflict"))
        assert exc_info.value.status_code == 409

    def test_internal_error_maps_to_500(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(InternalError("crash"))
        assert exc_info.value.status_code == 500

    def test_generic_service_exception_maps_to_500(self):
        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ServiceException("unknown"))
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# _ensure_file_under_tmp
# ---------------------------------------------------------------------------


class TestEnsureFileUnderTmp:
    def test_file_already_under_tmp(self, tmp_path):
        """If the file is already under cwd/tmp, it should be returned as-is."""
        # Create a fake file under a tmp dir inside a temporary cwd
        fake_cwd = tmp_path / "project"
        fake_cwd.mkdir()
        tmp_dir = fake_cwd / "tmp" / "some-id" / "zip"
        tmp_dir.mkdir(parents=True)
        target_file = tmp_dir / "export.zip"
        target_file.write_text("data")

        with patch("app.api.v2.endpoints.cad.FilePath.cwd", return_value=fake_cwd):
            result = _ensure_file_under_tmp(str(target_file), "some-id")

        assert result == target_file.resolve()

    def test_file_outside_tmp_gets_copied(self, tmp_path):
        """If the file is outside tmp, it should be copied into tmp."""
        fake_cwd = tmp_path / "project"
        fake_cwd.mkdir()

        # Source file is outside tmp
        source_dir = tmp_path / "elsewhere"
        source_dir.mkdir()
        source_file = source_dir / "export.zip"
        source_file.write_text("zipdata")

        aeroplane_id = "test-plane-123"

        with patch("app.api.v2.endpoints.cad.FilePath.cwd", return_value=fake_cwd):
            result = _ensure_file_under_tmp(str(source_file), aeroplane_id)

        # Should have been copied under fake_cwd/tmp/<id>/zip/
        expected_dir = fake_cwd / "tmp" / aeroplane_id / "zip"
        assert result.parent == expected_dir.resolve()
        assert result.name == "export.zip"
        assert result.read_text() == "zipdata"

    def test_relative_path_is_resolved(self, tmp_path):
        """A relative path should be resolved relative to cwd."""
        fake_cwd = tmp_path / "project"
        fake_cwd.mkdir()

        # Create source file at fake_cwd/data/export.zip
        data_dir = fake_cwd / "data"
        data_dir.mkdir()
        source = data_dir / "export.zip"
        source.write_text("contents")

        with patch("app.api.v2.endpoints.cad.FilePath.cwd", return_value=fake_cwd):
            result = _ensure_file_under_tmp("data/export.zip", "plane-1")

        expected_dir = fake_cwd / "tmp" / "plane-1" / "zip"
        assert result.parent == expected_dir.resolve()
        assert result.read_text() == "contents"


# ---------------------------------------------------------------------------
# _offset_refs
# ---------------------------------------------------------------------------


class TestOffsetRefs:
    def test_offsets_ref_in_dict(self):
        node = {"ref": 0, "other": "value"}
        _offset_refs(node, 5)
        assert node["ref"] == 5

    def test_offsets_ref_in_nested_dict(self):
        node = {"child": {"ref": 2}}
        _offset_refs(node, 10)
        assert node["child"]["ref"] == 12

    def test_offsets_ref_in_list(self):
        node = [{"ref": 1}, {"ref": 3}]
        _offset_refs(node, 100)
        assert node[0]["ref"] == 101
        assert node[1]["ref"] == 103

    def test_handles_float_ref(self):
        node = {"ref": 2.5}
        _offset_refs(node, 3)
        assert node["ref"] == 5

    def test_no_ref_key_is_noop(self):
        node = {"name": "shape", "color": "red"}
        _offset_refs(node, 10)
        assert node == {"name": "shape", "color": "red"}

    def test_empty_structures(self):
        _offset_refs({}, 5)
        _offset_refs([], 5)
        _offset_refs("string", 5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _expand_bounding_box
# ---------------------------------------------------------------------------


class TestExpandBoundingBox:
    def test_expands_with_valid_bb(self):
        bb_min = [10.0, 10.0, 10.0]
        bb_max = [-10.0, -10.0, -10.0]
        shapes = {"bb": {"min": [1.0, 2.0, 3.0], "max": [4.0, 5.0, 6.0]}}
        _expand_bounding_box(bb_min, bb_max, shapes)
        assert bb_min == [1.0, 2.0, 3.0]
        assert bb_max == [4.0, 5.0, 6.0]

    def test_no_bb_key_is_noop(self):
        bb_min = [0.0, 0.0, 0.0]
        bb_max = [1.0, 1.0, 1.0]
        _expand_bounding_box(bb_min, bb_max, {})
        assert bb_min == [0.0, 0.0, 0.0]
        assert bb_max == [1.0, 1.0, 1.0]

    def test_missing_min_in_bb_is_noop(self):
        bb_min = [0.0, 0.0, 0.0]
        bb_max = [1.0, 1.0, 1.0]
        _expand_bounding_box(bb_min, bb_max, {"bb": {"max": [2, 2, 2]}})
        assert bb_min == [0.0, 0.0, 0.0]

    def test_multiple_expansions_take_extremes(self):
        bb_min = [float("inf")] * 3
        bb_max = [float("-inf")] * 3
        shapes1 = {"bb": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]}}
        shapes2 = {"bb": {"min": [-1.0, -2.0, -3.0], "max": [5.0, 5.0, 5.0]}}
        _expand_bounding_box(bb_min, bb_max, shapes1)
        _expand_bounding_box(bb_min, bb_max, shapes2)
        assert bb_min == [-1.0, -2.0, -3.0]
        assert bb_max == [5.0, 5.0, 5.0]


# ---------------------------------------------------------------------------
# _merge_tessellation_entries
# ---------------------------------------------------------------------------


class TestMergeTessellationEntries:
    def _make_entry(
        self, *, component_type="wing", shapes=None, instances=None, count=1, bb=None
    ):
        entry = MagicMock()
        entry.component_type = component_type
        entry.is_stale = False
        data = {}
        if shapes is not None:
            data["shapes"] = shapes
        if instances is not None:
            data["instances"] = instances
        if bb is not None and shapes is not None:
            shapes["bb"] = bb
        entry.tessellation_json = {"data": data, "count": count}
        return entry

    def test_empty_entries(self):
        parts, instances, count, bb = _merge_tessellation_entries([])
        assert parts == []
        assert instances == []
        assert count == 0
        assert bb == {"min": [0, 0, 0], "max": [0, 0, 0]}

    def test_single_wing_entry(self):
        entry = self._make_entry(
            component_type="wing",
            shapes={"version": 3, "name": "wing"},
            instances=[{"id": 0}],
            count=5,
            bb={"min": [0, 0, 0], "max": [1, 1, 1]},
        )
        parts, instances, count, bb = _merge_tessellation_entries([entry])
        assert len(parts) == 1
        assert parts[0]["color"] == "#FF8400"  # wing color
        assert instances == [{"id": 0}]
        assert count == 5
        assert bb == {"min": [0, 0, 0], "max": [1, 1, 1]}

    def test_fuselage_gets_grey_color(self):
        entry = self._make_entry(
            component_type="fuselage",
            shapes={"version": 3, "name": "fuse"},
            instances=[],
            count=3,
            bb={"min": [-1, -1, -1], "max": [2, 2, 2]},
        )
        parts, _, _, _ = _merge_tessellation_entries([entry])
        assert parts[0]["color"] == "#888888"

    def test_multiple_entries_merge_instances_and_offset_refs(self):
        entry1 = self._make_entry(
            component_type="wing",
            shapes={"version": 3, "name": "w1", "ref": 0},
            instances=[{"id": 0}, {"id": 1}],
            count=2,
            bb={"min": [0, 0, 0], "max": [1, 1, 1]},
        )
        entry2 = self._make_entry(
            component_type="fuselage",
            shapes={"version": 3, "name": "f1", "ref": 0},
            instances=[{"id": 0}],
            count=3,
            bb={"min": [-1, -1, -1], "max": [2, 2, 2]},
        )
        parts, instances, count, bb = _merge_tessellation_entries([entry1, entry2])
        assert len(parts) == 2
        assert len(instances) == 3  # 2 + 1
        assert count == 5
        # Second entry's ref should be offset by len(first instances) = 2
        assert parts[1]["ref"] == 2
        # BB should be the combined extremes
        assert bb["min"] == [-1, -1, -1]
        assert bb["max"] == [2, 2, 2]

    def test_entry_without_shapes_is_skipped(self):
        entry = self._make_entry(
            component_type="wing",
            shapes=None,
            instances=[{"id": 0}],
            count=1,
        )
        parts, instances, count, bb = _merge_tessellation_entries([entry])
        assert parts == []
        assert instances == [{"id": 0}]
        assert count == 1


# ---------------------------------------------------------------------------
# start_wing_tessellation
# ---------------------------------------------------------------------------


class TestStartWingTessellation:
    def test_success(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        mock_wing = MagicMock()
        mock_wing_schema = MagicMock()

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_wing_from_aeroplane",
                return_value=mock_wing,
            ),
            patch(
                "app.converters.model_schema_converters.wing_model_to_asb_wing_schema",
                return_value=mock_wing_schema,
            ),
            patch("pickle.dumps", return_value=b"fake_pickle"),
            patch(
                "app.api.v2.endpoints.cad.tessellation_service.start_tessellation_task",
            ) as mock_start,
        ):
            result = asyncio.run(
                start_wing_tessellation(plane_id, "main_wing", mock_db)
            )

        assert result.aeroplane_id == str(plane_id)
        mock_start.assert_called_once()

    def test_not_found_maps_to_404(self, plane_id, mock_db):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
            side_effect=NotFoundError("no plane"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    start_wing_tessellation(plane_id, "wing", mock_db)
                )
        assert exc_info.value.status_code == 404

    def test_unexpected_error_maps_to_500(self, plane_id, mock_db):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    start_wing_tessellation(plane_id, "wing", mock_db)
                )
        assert exc_info.value.status_code == 500
        assert "boom" in exc_info.value.detail


# ---------------------------------------------------------------------------
# get_aeroplane_tessellation
# ---------------------------------------------------------------------------


class TestGetAeroplaneTessellation:
    def test_success_returns_combined_scene(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        mock_aeroplane.name = "TestPlane"
        mock_aeroplane.id = 1

        mock_entry = MagicMock()
        mock_entry.component_type = "wing"
        mock_entry.is_stale = False
        mock_entry.tessellation_json = {
            "data": {
                "shapes": {
                    "version": 3,
                    "name": "wing",
                    "bb": {"min": [0, 0, 0], "max": [1, 1, 1]},
                },
                "instances": [{"id": 0}],
            },
            "count": 5,
        }

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.tessellation_cache_service.get_all_cached",
                return_value=[mock_entry],
            ),
        ):
            result = asyncio.run(get_aeroplane_tessellation(plane_id, mock_db))

        assert result["type"] == "data"
        assert result["count"] == 5
        assert result["is_stale"] is False
        assert "data" in result
        assert "shapes" in result["data"]

    def test_no_cached_entries_returns_404(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.tessellation_cache_service.get_all_cached",
                return_value=[],
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_aeroplane_tessellation(plane_id, mock_db))

        assert exc_info.value.status_code == 404
        assert "No cached tessellations" in exc_info.value.detail

    def test_aeroplane_not_found_maps_to_404(self, plane_id, mock_db):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
            side_effect=NotFoundError("no plane"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_aeroplane_tessellation(plane_id, mock_db))
        assert exc_info.value.status_code == 404

    def test_unexpected_error_maps_to_500(self, plane_id, mock_db):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
            side_effect=RuntimeError("surprise"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_aeroplane_tessellation(plane_id, mock_db))
        assert exc_info.value.status_code == 500

    def test_is_stale_flag_propagated(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        mock_aeroplane.name = "Plane"
        mock_aeroplane.id = 1

        entry1 = MagicMock()
        entry1.component_type = "wing"
        entry1.is_stale = False
        entry1.tessellation_json = {
            "data": {"shapes": {"version": 3}, "instances": []},
            "count": 1,
        }
        entry2 = MagicMock()
        entry2.component_type = "fuselage"
        entry2.is_stale = True
        entry2.tessellation_json = {
            "data": {"shapes": {"version": 3}, "instances": []},
            "count": 1,
        }

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.tessellation_cache_service.get_all_cached",
                return_value=[entry1, entry2],
            ),
        ):
            result = asyncio.run(get_aeroplane_tessellation(plane_id, mock_db))

        assert result["is_stale"] is True


# ---------------------------------------------------------------------------
# create_wing_loft
# ---------------------------------------------------------------------------


class TestCreateWingLoft:
    def test_success(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        mock_wing = MagicMock()

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_wing_from_aeroplane",
                return_value=mock_wing,
            ),
            patch(
                "app.api.v2.endpoints.cad.cad_service.start_wing_export_task",
            ) as mock_export,
        ):
            result = asyncio.run(
                create_wing_loft(
                    aeroplane_id=plane_id,
                    wing_name="main_wing",
                    db=mock_db,
                    leading_edge_offset_factor=0.1,
                    trailing_edge_offset_factor=0.15,
                    aeroplane_settings=None,
                    creator_url_type=CreatorUrlType.WING_LOFT,
                    exporter_url_type=ExporterUrlType.STL,
                )
            )

        assert result.aeroplane_id == str(plane_id)
        mock_export.assert_called_once()

    def test_not_found_maps_to_404(self, plane_id, mock_db):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
            side_effect=NotFoundError("no plane"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    create_wing_loft(
                        plane_id, "wing", mock_db,
                        creator_url_type=CreatorUrlType.WING_LOFT,
                        exporter_url_type=ExporterUrlType.STL,
                    )
                )
        assert exc_info.value.status_code == 404

    def test_conflict_error_maps_to_409(self, plane_id, mock_db):
        mock_aeroplane = MagicMock()
        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_aeroplane_with_wings",
                return_value=mock_aeroplane,
            ),
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_wing_from_aeroplane",
                side_effect=ConflictError("export in progress"),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    create_wing_loft(
                        plane_id, "wing", mock_db,
                        creator_url_type=CreatorUrlType.WING_LOFT,
                        exporter_url_type=ExporterUrlType.STL,
                    )
                )
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# get_aeroplane_task_status
# ---------------------------------------------------------------------------


class TestGetAeroplaneTaskStatus:
    def test_pending_status(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "PENDING"},
        ):
            result = asyncio.run(
                get_aeroplane_task_status("some-id")
            )
        assert result.status == "PENDING"
        assert result.message == "Task is pending."
        assert result.result is None

    def test_success_status(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "SUCCESS", "result": {"key": "value"}},
        ):
            result = asyncio.run(
                get_aeroplane_task_status("some-id")
            )
        assert result.status == "SUCCESS"
        assert result.message is None
        assert result.result == {"key": "value"}

    def test_failure_status(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "FAILURE", "error": "Out of memory"},
        ):
            result = asyncio.run(
                get_aeroplane_task_status("some-id")
            )
        assert result.status == "FAILURE"
        assert result.message == "Out of memory"

    def test_failure_without_error_key(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "FAILURE"},
        ):
            result = asyncio.run(
                get_aeroplane_task_status("some-id")
            )
        assert result.message == "An error occurred"

    def test_unknown_status_returns_processing_message(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "RUNNING"},
        ):
            result = asyncio.run(
                get_aeroplane_task_status("some-id")
            )
        assert result.status == "RUNNING"
        assert result.message == "Task is processing."

    def test_tessellation_task_type_builds_correct_key(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "PENDING"},
        ) as mock_get:
            asyncio.run(
                get_aeroplane_task_status(
                    "plane-1",
                    task_type="tessellation",
                    wing_name="main_wing",
                )
            )
        mock_get.assert_called_once_with("plane-1:tessellation:main_wing")

    def test_custom_task_type_builds_correct_key(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "PENDING"},
        ) as mock_get:
            asyncio.run(
                get_aeroplane_task_status("plane-1", task_type="export")
            )
        mock_get.assert_called_once_with("plane-1:export")

    def test_no_task_type_uses_aeroplane_id_as_key(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            return_value={"status": "PENDING"},
        ) as mock_get:
            asyncio.run(
                get_aeroplane_task_status("plane-1")
            )
        mock_get.assert_called_once_with("plane-1")

    def test_service_exception_maps_correctly(self):
        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_task_result",
            side_effect=NotFoundError("no task"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_aeroplane_task_status("bad-id"))
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# download_aeroplane_zip
# ---------------------------------------------------------------------------


class TestDownloadAeroplaneZip:
    def test_success(self, tmp_path):
        # Create a fake file that cad_service would return
        fake_file = tmp_path / "export.zip"
        fake_file.write_text("fake_zip")

        mock_settings = MagicMock()
        mock_settings.base_url = "http://testserver"
        mock_request = MagicMock()
        mock_request.base_url = "http://testserver/"

        fake_cwd = tmp_path / "project"
        fake_cwd.mkdir()

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_export_file_path",
                return_value=str(fake_file),
            ),
            patch(
                "app.api.v2.endpoints.cad._ensure_file_under_tmp",
                return_value=fake_cwd / "tmp" / "plane" / "zip" / "export.zip",
            ),
            patch(
                "app.api.v2.endpoints.cad.FilePath.cwd",
                return_value=fake_cwd,
            ),
        ):
            result = asyncio.run(
                download_aeroplane_zip(
                    aeroplane_id="plane-1",
                    wing_name="main_wing",
                    creator_url_type="wing_loft",
                    exporter_url_type="stl",
                    settings=mock_settings,
                    request=mock_request,
                )
            )

        assert result.filename == "export.zip"
        assert result.mime_type == "application/zip"
        assert "static" in result.url

    def test_not_found_maps_to_404(self):
        mock_settings = MagicMock()
        mock_settings.base_url = "http://testserver"
        mock_request = MagicMock()
        mock_request.base_url = "http://testserver/"

        with patch(
            "app.api.v2.endpoints.cad.cad_service.get_export_file_path",
            side_effect=NotFoundError("no export"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    download_aeroplane_zip(
                        "plane-1", "wing", "wing_loft", "stl",
                        mock_settings, mock_request,
                    )
                )
        assert exc_info.value.status_code == 404

    def test_apiserver_base_url_falls_back_to_settings(self, tmp_path):
        fake_file = tmp_path / "export.zip"
        fake_file.write_text("zip")

        mock_settings = MagicMock()
        mock_settings.base_url = "http://real-server"
        mock_request = MagicMock()
        mock_request.base_url = "apiserver"

        fake_cwd = tmp_path / "project"
        fake_cwd.mkdir()

        with (
            patch(
                "app.api.v2.endpoints.cad.cad_service.get_export_file_path",
                return_value=str(fake_file),
            ),
            patch(
                "app.api.v2.endpoints.cad._ensure_file_under_tmp",
                return_value=fake_cwd / "tmp" / "p" / "zip" / "export.zip",
            ),
            patch(
                "app.api.v2.endpoints.cad.FilePath.cwd",
                return_value=fake_cwd,
            ),
        ):
            result = asyncio.run(
                download_aeroplane_zip(
                    "p", "wing", "wing_loft", "stl",
                    mock_settings, mock_request,
                )
            )

        assert "real-server" in result.url
