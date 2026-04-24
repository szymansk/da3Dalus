"""Extended unit tests for app.services.cad_service.

Covers task management, exporter mapping, blueprint building,
settings extraction, result callbacks, and export file path logic.
Heavy CadQuery/OCCT dependencies are mocked — these tests focus on
orchestration logic, not geometry.
"""

from __future__ import annotations

import os
import pickle
from concurrent.futures import Future
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationError,
)
from app.schemas.AeroplaneRequest import (
    AeroplaneSettings,
    CreatorUrlType,
    ExporterUrlType,
    ServoSettings,
)
from app.schemas.Printer3dSettings import Printer3dSettings
from app.services import cad_service


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _inject_task(aeroplane_id: str, task: Dict[str, Any]) -> None:
    """Directly inject a task into the module-level dict (test helper)."""
    with cad_service.tasks_lock:
        cad_service.tasks[aeroplane_id] = task


# --------------------------------------------------------------------------- #
# get_task_status
# --------------------------------------------------------------------------- #


class TestGetTaskStatus:
    def test_returns_none_when_no_task(self):
        assert cad_service.get_task_status("missing-id") is None

    def test_returns_task_when_present(self):
        _inject_task("abc-123", {"status": "PENDING"})
        result = cad_service.get_task_status("abc-123")
        assert result == {"status": "PENDING"}


# --------------------------------------------------------------------------- #
# register_pending_task
# --------------------------------------------------------------------------- #


class TestRegisterPendingTask:
    def test_creates_pending_entry(self):
        cad_service.register_pending_task("new-task-id")
        with cad_service.tasks_lock:
            assert cad_service.tasks["new-task-id"] == {"status": "PENDING"}

    def test_overwrites_existing_entry(self):
        _inject_task("overwrite-id", {"status": "SUCCESS", "result": {}})
        cad_service.register_pending_task("overwrite-id")
        with cad_service.tasks_lock:
            assert cad_service.tasks["overwrite-id"] == {"status": "PENDING"}


# --------------------------------------------------------------------------- #
# check_task_available
# --------------------------------------------------------------------------- #


class TestCheckTaskAvailable:
    def test_no_existing_task_does_not_raise(self):
        cad_service.check_task_available("fresh-id")

    def test_completed_task_is_removed(self):
        _inject_task("done-id", {"status": "SUCCESS", "future": None})
        cad_service.check_task_available("done-id")
        assert cad_service.get_task_status("done-id") is None

    def test_running_future_raises_conflict(self):
        future = MagicMock(spec=Future)
        future.running.return_value = True
        _inject_task("busy-id", {"status": "RUNNING", "future": future})

        with pytest.raises(ConflictError, match="Another task is already running"):
            cad_service.check_task_available("busy-id")

    def test_pending_status_with_future_raises_conflict(self):
        future = MagicMock(spec=Future)
        future.running.return_value = False
        _inject_task("pending-id", {"status": "PENDING", "future": future})

        with pytest.raises(ConflictError):
            cad_service.check_task_available("pending-id")

    def test_non_running_future_with_done_status_is_removed(self):
        future = MagicMock(spec=Future)
        future.running.return_value = False
        _inject_task("stale-id", {"status": "SUCCESS", "future": future})

        cad_service.check_task_available("stale-id")
        assert cad_service.get_task_status("stale-id") is None


# --------------------------------------------------------------------------- #
# map_exporter_type
# --------------------------------------------------------------------------- #


class TestMapExporterType:
    @pytest.mark.parametrize(
        "url_type, expected_class",
        [
            (ExporterUrlType.STL, "ExportToStlCreator"),
            (ExporterUrlType.STEP, "ExportToStepCreator"),
            (ExporterUrlType.IGES, "ExportToIgesCreator"),
            (ExporterUrlType.THREEMF, "ExportTo3MFCreator"),
        ],
    )
    def test_supported_types(self, url_type, expected_class):
        assert cad_service.map_exporter_type(url_type) == expected_class

    def test_unsupported_type_raises_validation_error(self):
        """AMF is in the enum but not in the mapping."""
        with pytest.raises(ValidationError, match="Unsupported exporter type"):
            cad_service.map_exporter_type(ExporterUrlType.AMF)


# --------------------------------------------------------------------------- #
# build_wing_blueprint
# --------------------------------------------------------------------------- #


class TestBuildWingBlueprint:
    def test_wing_loft_creator_type(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="main_wing",
            creator_url_type=CreatorUrlType.WING_LOFT,
            exporter_class="ExportToStepCreator",
        )
        wing_node = bp["successors"]["main_wing"]
        assert wing_node["creator"]["$TYPE"] == "WingLoftCreator"
        assert "leading_edge_offset_factor" not in wing_node["creator"]

    def test_vase_mode_creator_type_with_offset_factors(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="test_wing",
            creator_url_type=CreatorUrlType.VASE_MODE_WING,
            exporter_class="ExportToStlCreator",
            leading_edge_offset_factor=0.2,
            trailing_edge_offset_factor=0.3,
        )
        wing_node = bp["successors"]["test_wing"]
        assert wing_node["creator"]["$TYPE"] == "VaseModeWingCreator"
        assert wing_node["creator"]["leading_edge_offset_factor"] == 0.2
        assert wing_node["creator"]["trailing_edge_offset_factor"] == 0.3

    def test_blueprint_structure(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="w1",
            creator_url_type=CreatorUrlType.WING_LOFT,
            exporter_class="ExportToStepCreator",
        )
        assert bp["$TYPE"] == "ConstructionRootNode"
        assert "w1" in bp["successors"]
        assert "output-wing" in bp["successors"]

    def test_exporter_node_properties(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="w1",
            creator_url_type=CreatorUrlType.WING_LOFT,
            exporter_class="ExportToStepCreator",
        )
        exporter = bp["successors"]["output-wing"]["creator"]
        assert exporter["$TYPE"] == "ExportToStepCreator"
        assert exporter["file_path"] == "./tmp/exports"
        assert exporter["angular_tolerance"] == 0.1
        assert exporter["tolerance"] == 0.1

    def test_default_offset_factors(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="w",
            creator_url_type=CreatorUrlType.VASE_MODE_WING,
            exporter_class="ExportToStlCreator",
        )
        creator = bp["successors"]["w"]["creator"]
        assert creator["leading_edge_offset_factor"] == 0.1
        assert creator["trailing_edge_offset_factor"] == 0.15

    def test_wing_node_metadata(self):
        bp = cad_service.build_wing_blueprint(
            wing_name="my_wing",
            creator_url_type=CreatorUrlType.WING_LOFT,
            exporter_class="ExportToStepCreator",
        )
        wing = bp["successors"]["my_wing"]
        assert wing["$TYPE"] == "ConstructionStepNode"
        assert wing["creator_id"] == "my_wing"
        assert wing["creator"]["wing_index"] == "my_wing"
        assert wing["creator"]["wing_side"] == "BOTH"
        assert wing["creator"]["offset"] == 0


# --------------------------------------------------------------------------- #
# _extract_aeroplane_settings
# --------------------------------------------------------------------------- #


class TestExtractAeroplaneSettings:
    def test_none_settings_returns_empty(self):
        servo_dumps, printer_pickle = cad_service._extract_aeroplane_settings(None)
        assert servo_dumps == {}
        assert printer_pickle is None

    def test_settings_without_servo_or_printer(self):
        settings = AeroplaneSettings()
        servo_dumps, printer_pickle = cad_service._extract_aeroplane_settings(settings)
        assert servo_dumps == {}
        assert printer_pickle is None

    def test_servo_settings_are_dumped(self):
        servo = ServoSettings(
            height=10, width=5, length=20, lever_length=8,
            rot_x=1.0, rot_y=2.0, rot_z=3.0,
        )
        settings = AeroplaneSettings(servo_information={1: servo})
        servo_dumps, _ = cad_service._extract_aeroplane_settings(settings)

        assert 1 in servo_dumps
        assert servo_dumps[1]["height"] == 10
        assert servo_dumps[1]["width"] == 5
        assert servo_dumps[1]["rot_x"] == 1.0

    def test_printer_settings_are_pickled(self):
        printer = Printer3dSettings(
            layer_height=0.24, wall_thickness=0.42, rel_gap_wall_thickness=0.075
        )
        settings = AeroplaneSettings(printer_settings=printer)
        _, printer_pickle = cad_service._extract_aeroplane_settings(settings)

        assert printer_pickle is not None
        restored = pickle.loads(printer_pickle)
        assert restored.layer_height == 0.24
        assert restored.wall_thickness == 0.42

    def test_multiple_servo_entries(self):
        s1 = ServoSettings(height=1, width=1, length=1, lever_length=1)
        s2 = ServoSettings(height=2, width=2, length=2, lever_length=2)
        settings = AeroplaneSettings(servo_information={1: s1, 2: s2})
        servo_dumps, _ = cad_service._extract_aeroplane_settings(settings)

        assert len(servo_dumps) == 2
        assert servo_dumps[1]["height"] == 1
        assert servo_dumps[2]["height"] == 2


# --------------------------------------------------------------------------- #
# _apply_worker_result
# --------------------------------------------------------------------------- #


class TestApplyWorkerResult:
    def test_updates_status_and_result(self):
        _inject_task("apply-id", {"status": "PENDING"})
        cad_service._apply_worker_result(
            "apply-id",
            {"status": "SUCCESS", "result": {"zipfile": "/tmp/test.zip"}},
        )
        task = cad_service.get_task_status("apply-id")
        assert task["status"] == "SUCCESS"
        assert task["result"]["zipfile"] == "/tmp/test.zip"

    def test_updates_with_error(self):
        _inject_task("err-id", {"status": "PENDING"})
        cad_service._apply_worker_result(
            "err-id",
            {"status": "FAILURE", "error": "boom", "traceback": "tb..."},
        )
        task = cad_service.get_task_status("err-id")
        assert task["status"] == "FAILURE"
        assert task["error"] == "boom"
        assert task["traceback"] == "tb..."

    def test_noop_when_task_missing(self):
        """Should not raise even if the task was already removed."""
        cad_service._apply_worker_result("ghost-id", {"status": "SUCCESS"})

    def test_defaults_to_failure_when_status_missing(self):
        _inject_task("no-status", {"status": "PENDING"})
        cad_service._apply_worker_result("no-status", {})
        task = cad_service.get_task_status("no-status")
        assert task["status"] == "FAILURE"


# --------------------------------------------------------------------------- #
# _make_task_done_callback
# --------------------------------------------------------------------------- #


class TestMakeTaskDoneCallback:
    def test_successful_future_applies_result(self):
        _inject_task("cb-ok", {"status": "PENDING"})
        callback = cad_service._make_task_done_callback("cb-ok")

        future = MagicMock(spec=Future)
        future.result.return_value = {
            "status": "SUCCESS",
            "result": {"zipfile": "/tmp/ok.zip"},
        }
        callback(future)

        task = cad_service.get_task_status("cb-ok")
        assert task["status"] == "SUCCESS"

    def test_crashed_future_records_failure(self):
        _inject_task("cb-crash", {"status": "PENDING"})
        callback = cad_service._make_task_done_callback("cb-crash")

        future = MagicMock(spec=Future)
        future.result.side_effect = RuntimeError("worker died")
        callback(future)

        task = cad_service.get_task_status("cb-crash")
        assert task["status"] == "FAILURE"
        assert "Worker crashed" in task["error"]
        assert "RuntimeError" in task["error"]

    def test_crashed_future_when_task_already_removed(self):
        """Should not raise if the task was concurrently cleaned up."""
        callback = cad_service._make_task_done_callback("cb-gone")
        future = MagicMock(spec=Future)
        future.result.side_effect = RuntimeError("boom")
        # Should not raise
        callback(future)


# --------------------------------------------------------------------------- #
# get_task_result
# --------------------------------------------------------------------------- #


class TestGetTaskResult:
    def test_missing_task_raises_not_found(self):
        with pytest.raises(NotFoundError, match="Task not found"):
            cad_service.get_task_result("no-such-id")

    def test_pending_task_returns_status(self):
        _inject_task("res-pend", {"status": "PENDING"})
        result = cad_service.get_task_result("res-pend")
        assert result["status"] == "PENDING"
        assert result["result"] is None
        assert result["error"] is None

    def test_running_future_updates_status(self):
        future = MagicMock(spec=Future)
        future.running.return_value = True
        _inject_task("res-run", {"status": "PENDING", "future": future})

        result = cad_service.get_task_result("res-run")
        assert result["status"] == "RUNNING"

    def test_completed_task_returns_result(self):
        _inject_task(
            "res-done",
            {
                "status": "SUCCESS",
                "result": {"zipfile": "/tmp/done.zip"},
                "future": None,
            },
        )
        result = cad_service.get_task_result("res-done")
        assert result["status"] == "SUCCESS"
        assert result["result"]["zipfile"] == "/tmp/done.zip"

    def test_failed_task_returns_error(self):
        _inject_task(
            "res-fail",
            {"status": "FAILURE", "error": "something broke", "future": None},
        )
        result = cad_service.get_task_result("res-fail")
        assert result["status"] == "FAILURE"
        assert result["error"] == "something broke"


# --------------------------------------------------------------------------- #
# get_export_file_path
# --------------------------------------------------------------------------- #


class TestGetExportFilePath:
    def test_no_task_raises_not_found(self):
        with pytest.raises(NotFoundError, match="Task not found"):
            cad_service.get_export_file_path("missing")

    def test_non_success_status_raises_validation_error(self):
        _inject_task("exp-pend", {"status": "PENDING"})
        with pytest.raises(ValidationError, match="not completed"):
            cad_service.get_export_file_path("exp-pend")

    def test_failure_status_raises_validation_error(self):
        _inject_task("exp-fail", {"status": "FAILURE"})
        with pytest.raises(ValidationError, match="not completed"):
            cad_service.get_export_file_path("exp-fail")

    def test_missing_result_raises_internal_error(self):
        _inject_task("exp-nores", {"status": "SUCCESS", "result": None})
        with pytest.raises(InternalError, match="File not available"):
            cad_service.get_export_file_path("exp-nores")

    def test_missing_zipfile_key_raises_internal_error(self):
        _inject_task("exp-nozip", {"status": "SUCCESS", "result": {"other": "x"}})
        with pytest.raises(InternalError, match="File not available"):
            cad_service.get_export_file_path("exp-nozip")

    def test_file_not_on_disk_raises_not_found(self):
        _inject_task(
            "exp-nodisk",
            {"status": "SUCCESS", "result": {"zipfile": "/nonexistent/path.zip"}},
        )
        with pytest.raises(NotFoundError, match="File not found"):
            cad_service.get_export_file_path("exp-nodisk")

    def test_existing_file_returns_path(self, tmp_path):
        zipfile = tmp_path / "export.zip"
        zipfile.write_text("fake-zip")
        _inject_task(
            "exp-ok",
            {"status": "SUCCESS", "result": {"zipfile": str(zipfile)}},
        )
        result = cad_service.get_export_file_path("exp-ok")
        assert result == str(zipfile)


# --------------------------------------------------------------------------- #
# get_wing_from_aeroplane
# --------------------------------------------------------------------------- #


class TestGetWingFromAeroplane:
    def _make_aeroplane_with_wings(self, wing_names: list[str]) -> MagicMock:
        aeroplane = MagicMock()
        wings = []
        for name in wing_names:
            wing = MagicMock()
            wing.name = name
            wings.append(wing)
        aeroplane.wings = wings
        aeroplane.uuid = "test-uuid"
        return aeroplane

    def test_found_wing(self):
        aeroplane = self._make_aeroplane_with_wings(["main_wing", "tail"])
        wing = cad_service.get_wing_from_aeroplane(aeroplane, "main_wing")
        assert wing.name == "main_wing"

    def test_missing_wing_raises_not_found(self):
        aeroplane = self._make_aeroplane_with_wings(["main_wing"])
        with pytest.raises(NotFoundError, match="Wing not found"):
            cad_service.get_wing_from_aeroplane(aeroplane, "nonexistent")

    def test_empty_wings_list(self):
        aeroplane = self._make_aeroplane_with_wings([])
        with pytest.raises(NotFoundError):
            cad_service.get_wing_from_aeroplane(aeroplane, "any")


# --------------------------------------------------------------------------- #
# get_aeroplane_with_wings (DB interaction)
# --------------------------------------------------------------------------- #


class TestGetAeroplaneWithWings:
    def test_not_found_raises(self, client_and_db):
        """Uses a real in-memory DB session."""
        import uuid

        _, session_factory = client_and_db
        session = session_factory()
        try:
            with pytest.raises(NotFoundError, match="Aeroplane not found"):
                cad_service.get_aeroplane_with_wings(session, uuid.uuid4())
        finally:
            session.close()

    def test_found_aeroplane_returns_model(self, client_and_db):
        from app.tests.conftest import make_aeroplane

        _, session_factory = client_and_db
        session = session_factory()
        try:
            aeroplane = make_aeroplane(session, name="test-plane")
            result = cad_service.get_aeroplane_with_wings(session, aeroplane.uuid)
            assert result.name == "test-plane"
            assert result.uuid == aeroplane.uuid
        finally:
            session.close()


# --------------------------------------------------------------------------- #
# shutdown_executor
# --------------------------------------------------------------------------- #


class TestShutdownExecutor:
    def test_shutdown_when_no_executor(self):
        """Should not raise when executor is None."""
        cad_service.shutdown_executor()

    def test_shutdown_sets_executor_to_none(self):
        """After shutdown, _executor should be None."""
        # Force-create the executor
        executor = cad_service._get_executor()
        assert executor is not None
        cad_service.shutdown_executor()
        assert cad_service._executor is None

    def test_shutdown_tolerates_exception(self):
        """If executor.shutdown() raises, the function logs and clears."""
        bad_executor = MagicMock()
        bad_executor.shutdown.side_effect = OSError("mock failure")

        with cad_service._executor_lock:
            cad_service._executor = bad_executor

        # Should not raise
        cad_service.shutdown_executor()
        assert cad_service._executor is None


# --------------------------------------------------------------------------- #
# _convert_wing_to_pickle
# --------------------------------------------------------------------------- #


class TestConvertWingToPickle:
    @patch("app.services.cad_service.wing_model_to_asb_wing_schema")
    def test_conversion_failure_raises_internal_error(self, mock_convert):
        mock_convert.side_effect = ValueError("bad wing data")
        wing = MagicMock()
        with pytest.raises(InternalError, match="Wing data conversion failed"):
            cad_service._convert_wing_to_pickle(wing, "w1", "plane-1")

    @patch("app.services.cad_service.wing_model_to_asb_wing_schema")
    def test_successful_conversion_returns_bytes(self, mock_convert):
        # Use a picklable object (a plain string) as the schema stand-in
        mock_convert.return_value = "fake-wing-schema"
        result = cad_service._convert_wing_to_pickle(MagicMock(), "w1", "plane-1")
        assert isinstance(result, bytes)
        restored = pickle.loads(result)
        assert "w1" in restored
        assert restored["w1"] == "fake-wing-schema"

    @patch("app.services.cad_service.pickle.dumps")
    @patch("app.services.cad_service.wing_model_to_asb_wing_schema")
    def test_pickle_failure_raises_internal_error(self, mock_convert, mock_dumps):
        mock_convert.return_value = MagicMock()
        mock_dumps.side_effect = TypeError("cannot pickle")
        wing = MagicMock()
        with pytest.raises(InternalError, match="Failed to prepare wing data"):
            cad_service._convert_wing_to_pickle(wing, "w1", "plane-1")


# --------------------------------------------------------------------------- #
# start_wing_export_task (orchestration)
# --------------------------------------------------------------------------- #


class TestStartWingExportTask:
    @patch("app.services.cad_service._get_executor")
    @patch("app.services.cad_service._convert_wing_to_pickle")
    def test_submits_to_executor(self, mock_convert, mock_get_executor):
        mock_convert.return_value = b"pickled-wing"
        mock_future = MagicMock(spec=Future)
        mock_executor = MagicMock()
        mock_executor.submit.return_value = mock_future
        mock_get_executor.return_value = mock_executor

        wing = MagicMock()
        cad_service.start_wing_export_task(
            aeroplane_id="task-submit-id",
            wing=wing,
            wing_name="main_wing",
            creator_url_type=CreatorUrlType.WING_LOFT,
            exporter_url_type=ExporterUrlType.STEP,
            leading_edge_offset_factor=0.1,
            trailing_edge_offset_factor=0.15,
            aeroplane_settings=None,
        )

        mock_executor.submit.assert_called_once()
        mock_future.add_done_callback.assert_called_once()

        task = cad_service.get_task_status("task-submit-id")
        assert task is not None
        assert task["future"] is mock_future

    @patch("app.services.cad_service._get_executor")
    @patch("app.services.cad_service._convert_wing_to_pickle")
    def test_rejects_when_task_running(self, mock_convert, mock_get_executor):
        future = MagicMock(spec=Future)
        future.running.return_value = True
        _inject_task("busy-task", {"status": "RUNNING", "future": future})

        with pytest.raises(ConflictError):
            cad_service.start_wing_export_task(
                aeroplane_id="busy-task",
                wing=MagicMock(),
                wing_name="w",
                creator_url_type=CreatorUrlType.WING_LOFT,
                exporter_url_type=ExporterUrlType.STEP,
                leading_edge_offset_factor=0.1,
                trailing_edge_offset_factor=0.15,
                aeroplane_settings=None,
            )

    @patch("app.services.cad_service._get_executor")
    @patch("app.services.cad_service._convert_wing_to_pickle")
    def test_unsupported_exporter_raises_validation(
        self, mock_convert, mock_get_executor
    ):
        mock_convert.return_value = b"pickled"
        with pytest.raises(ValidationError, match="Unsupported exporter type"):
            cad_service.start_wing_export_task(
                aeroplane_id="bad-exporter",
                wing=MagicMock(),
                wing_name="w",
                creator_url_type=CreatorUrlType.WING_LOFT,
                exporter_url_type=ExporterUrlType.AMF,
                leading_edge_offset_factor=0.1,
                trailing_edge_offset_factor=0.15,
                aeroplane_settings=None,
            )
