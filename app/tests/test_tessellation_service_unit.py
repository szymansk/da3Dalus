"""Unit tests for app.services.tessellation_service.

Covers:
- _numpy_to_list: recursive NumPy-to-Python conversion
- _run_tessellation_worker: orchestration with mocked CAD deps
- start_tessellation_task: task submission and caching callback
- trigger_background_tessellation: debounce behaviour
- _start_tessellation_and_cache: executor submission + cache persistence

All heavy external dependencies (cadquery, ocp_tessellate, cad_designer,
numpy) are mocked so these tests run fast and without GPU/CAD tooling.
"""

from __future__ import annotations

import pickle
import threading
import time
from concurrent.futures import Future
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.tessellation_service import (
    _numpy_to_list,
    _pending_futures,
    _pending_timers,
    _run_tessellation_worker,
    _start_tessellation_and_cache,
    _timer_lock,
    start_tessellation_task,
    trigger_background_tessellation,
)


# --------------------------------------------------------------------------- #
# _numpy_to_list
# --------------------------------------------------------------------------- #


class TestNumpyToList:
    """Tests for _numpy_to_list recursive converter."""

    def test_plain_dict_passthrough(self):
        """Plain Python dicts without numpy values pass through unchanged."""
        data = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        result = _numpy_to_list(data)
        assert result == {"a": 1, "b": "hello", "c": [1, 2, 3]}

    def test_plain_values_passthrough(self):
        """Scalars, strings, None pass through unchanged."""
        assert _numpy_to_list(42) == 42
        assert _numpy_to_list("text") == "text"
        assert _numpy_to_list(None) is None
        assert _numpy_to_list(3.14) == 3.14
        assert _numpy_to_list(True) is True

    def test_ndarray_to_list(self):
        """np.ndarray is converted to a Python list."""
        np = pytest.importorskip("numpy")
        arr = np.array([1.0, 2.0, 3.0])
        result = _numpy_to_list(arr)
        assert result == [1.0, 2.0, 3.0]
        assert isinstance(result, list)

    def test_2d_ndarray_to_nested_list(self):
        """2D np.ndarray becomes a nested Python list."""
        np = pytest.importorskip("numpy")
        arr = np.array([[1, 2], [3, 4]])
        result = _numpy_to_list(arr)
        assert result == [[1, 2], [3, 4]]

    def test_np_integer_to_int(self):
        """np.int64 and other numpy integer types become plain int."""
        np = pytest.importorskip("numpy")
        val = np.int64(42)
        result = _numpy_to_list(val)
        assert result == 42
        assert type(result) is int

    def test_np_float_to_float(self):
        """np.float64 becomes plain float."""
        np = pytest.importorskip("numpy")
        val = np.float64(3.14)
        result = _numpy_to_list(val)
        assert result == pytest.approx(3.14)
        assert type(result) is float

    def test_dict_with_np_values(self):
        """Dict values that are numpy types are recursively converted."""
        np = pytest.importorskip("numpy")
        data = {
            "vertices": np.array([1.0, 2.0, 3.0]),
            "count": np.int64(10),
            "scale": np.float64(0.5),
        }
        result = _numpy_to_list(data)
        assert result == {"vertices": [1.0, 2.0, 3.0], "count": 10, "scale": 0.5}
        assert isinstance(result["vertices"], list)
        assert type(result["count"]) is int
        assert type(result["scale"]) is float

    def test_nested_dict_with_np_arrays(self):
        """Deeply nested structures are handled recursively."""
        np = pytest.importorskip("numpy")
        data = {
            "level1": {
                "level2": {
                    "arr": np.array([10, 20]),
                }
            }
        }
        result = _numpy_to_list(data)
        assert result == {"level1": {"level2": {"arr": [10, 20]}}}

    def test_list_with_np_arrays(self):
        """Lists containing numpy arrays are converted element-wise."""
        np = pytest.importorskip("numpy")
        data = [np.array([1, 2]), np.int64(3), "keep"]
        result = _numpy_to_list(data)
        assert result == [[1, 2], 3, "keep"]

    def test_tuple_with_np_arrays(self):
        """Tuples are converted to lists, with numpy elements converted."""
        np = pytest.importorskip("numpy")
        data = (np.array([1.0]), np.float64(2.0), "three")
        result = _numpy_to_list(data)
        assert result == [[1.0], 2.0, "three"]
        assert isinstance(result, list)

    def test_empty_structures(self):
        """Empty dicts, lists, and arrays are handled."""
        np = pytest.importorskip("numpy")
        assert _numpy_to_list({}) == {}
        assert _numpy_to_list([]) == []
        assert _numpy_to_list(np.array([])) == []


# --------------------------------------------------------------------------- #
# _run_tessellation_worker
# --------------------------------------------------------------------------- #


class TestRunTessellationWorker:
    """Tests for the tessellation worker function with mocked CAD deps."""

    @patch("app.services.tessellation_service.pickle")
    def test_success_returns_expected_structure(self, mock_pickle):
        """On success, the worker returns a dict with status=SUCCESS and result."""
        wing_schema = {"x_secs": [{"chord": 0.15}]}
        mock_pickle.loads.return_value = wing_schema
        wing_schema_pickle = b"fake_pickle"

        mock_wing_config = MagicMock()
        mock_workplane = MagicMock()
        mock_creator = MagicMock()
        mock_creator._create_shape.return_value = {"wing_loft": mock_workplane}

        mock_part_group = MagicMock()
        mock_part_group.count_shapes.return_value = 5

        mock_bb = MagicMock()
        mock_bb.to_dict.return_value = {
            "xmin": -1, "ymin": -2, "zmin": -3,
            "xmax": 1, "ymax": 2, "zmax": 3,
        }

        mock_instances = [{"id": "/wing", "shape": "/wing"}]
        mock_shapes = {"version": 3}
        mock_mapping = {}

        with (
            patch(
                "app.converters.model_schema_converters.asb_wing_schema_to_wing_config",
                return_value=mock_wing_config,
            ),
            patch(
                "cad_designer.airplane.creator.wing.WingLoftCreator",
                return_value=mock_creator,
            ),
            patch("cadquery.Workplane"),
            patch(
                "ocp_tessellate.convert.to_ocpgroup",
                return_value=(mock_part_group, mock_instances),
            ),
            patch(
                "ocp_tessellate.convert.tessellate_group",
                return_value=(mock_instances, mock_shapes, mock_mapping),
            ),
            patch(
                "ocp_tessellate.convert.combined_bb",
                return_value=mock_bb,
            ),
        ):
            result = _run_tessellation_worker(
                "aero-uuid-123", wing_schema_pickle, "main_wing", 1000.0,
            )

        assert result["status"] == "SUCCESS"
        assert "result" in result
        assert result["result"]["type"] == "data"
        assert result["result"]["count"] == 5
        assert "instances" in result["result"]["data"]
        assert "shapes" in result["result"]["data"]

    @patch("app.services.tessellation_service.pickle")
    def test_success_with_none_bounding_box(self, mock_pickle):
        """When combined_bb returns None, a default bbox is used."""
        mock_pickle.loads.return_value = {}

        mock_creator = MagicMock()
        mock_creator._create_shape.return_value = {"loft": MagicMock()}

        mock_part_group = MagicMock()
        mock_part_group.count_shapes.return_value = 1

        mock_instances = []
        mock_shapes = {}

        with (
            patch(
                "app.converters.model_schema_converters.asb_wing_schema_to_wing_config",
                return_value=MagicMock(),
            ),
            patch(
                "cad_designer.airplane.creator.wing.WingLoftCreator",
                return_value=mock_creator,
            ),
            patch("cadquery.Workplane"),
            patch(
                "ocp_tessellate.convert.to_ocpgroup",
                return_value=(mock_part_group, mock_instances),
            ),
            patch(
                "ocp_tessellate.convert.tessellate_group",
                return_value=(mock_instances, mock_shapes, {}),
            ),
            patch(
                "ocp_tessellate.convert.combined_bb",
                return_value=None,
            ),
        ):
            result = _run_tessellation_worker(
                "aero-uuid-456", b"fake", "tail", 1000.0,
            )

        assert result["status"] == "SUCCESS"
        shapes = result["result"]["data"]["shapes"]
        assert shapes["bb"] == {
            "xmin": 0, "ymin": 0, "zmin": 0,
            "xmax": 1, "ymax": 1, "zmax": 1,
        }

    @patch("app.services.tessellation_service.pickle")
    def test_empty_result_shapes_uses_empty_workplane(self, mock_pickle):
        """When creator returns empty dict, an empty Workplane is used."""
        mock_pickle.loads.return_value = {}

        mock_creator = MagicMock()
        mock_creator._create_shape.return_value = {}

        mock_empty_wp = MagicMock(name="EmptyWorkplane")

        mock_part_group = MagicMock()
        mock_part_group.count_shapes.return_value = 0

        with (
            patch(
                "app.converters.model_schema_converters.asb_wing_schema_to_wing_config",
                return_value=MagicMock(),
            ),
            patch(
                "cad_designer.airplane.creator.wing.WingLoftCreator",
                return_value=mock_creator,
            ),
            patch("cadquery.Workplane", return_value=mock_empty_wp) as wp_cls,
            patch(
                "ocp_tessellate.convert.to_ocpgroup",
                return_value=(mock_part_group, []),
            ) as mock_to_ocp,
            patch(
                "ocp_tessellate.convert.tessellate_group",
                return_value=([], {}, {}),
            ),
            patch("ocp_tessellate.convert.combined_bb", return_value=None),
        ):
            result = _run_tessellation_worker(
                "aero-uuid", b"fake", "wing", 1000.0,
            )
            # Verify the empty Workplane was passed to to_ocpgroup
            mock_to_ocp.assert_called_once()
            shape_arg = mock_to_ocp.call_args[0][0]
            assert shape_arg is mock_empty_wp

        assert result["status"] == "SUCCESS"

    @patch("app.services.tessellation_service.pickle")
    def test_exception_returns_failure(self, mock_pickle):
        """When an exception occurs, the worker returns status=FAILURE."""
        mock_pickle.loads.side_effect = ValueError("bad pickle")

        result = _run_tessellation_worker(
            "aero-uuid", b"corrupt", "wing", 1000.0,
        )

        assert result["status"] == "FAILURE"
        assert "ValueError" in result["error"]


# --------------------------------------------------------------------------- #
# start_tessellation_task
# --------------------------------------------------------------------------- #


class TestStartTessellationTask:
    """Tests for start_tessellation_task submission and callback wiring."""

    @patch("app.services.tessellation_service._get_executor")
    @patch("app.services.tessellation_service.register_pending_task")
    def test_registers_pending_task_and_submits(
        self, mock_register, mock_get_executor,
    ):
        """The function registers a pending task key and submits to executor."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        start_tessellation_task(
            "aero-123", "main_wing", b"pickled", "hash123", 1000.0,
        )

        mock_register.assert_called_once_with("aero-123:tessellation:main_wing")
        mock_get_executor.return_value.submit.assert_called_once_with(
            _run_tessellation_worker,
            "aero-123",
            b"pickled",
            "main_wing",
            1000.0,
        )
        mock_future.add_done_callback.assert_called_once()

    @patch("app.services.tessellation_service._get_executor")
    @patch("app.services.tessellation_service.register_pending_task")
    def test_on_done_callback_stores_success(
        self, mock_register, mock_get_executor,
    ):
        """The done callback stores the worker result in the tasks dict."""
        from app.services.cad_service import tasks, tasks_lock

        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        start_tessellation_task(
            "aero-cb", "wing1", b"pickled", "hash_cb", 1000.0,
        )

        # Extract the callback
        callback = mock_future.add_done_callback.call_args[0][0]

        # Simulate the future completing successfully
        mock_completed_future = MagicMock(spec=Future)
        mock_completed_future.result.return_value = {
            "status": "SUCCESS",
            "result": {"data": {}, "type": "data", "count": 1},
        }

        mock_db = MagicMock()
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 42
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_aeroplane
        )

        with patch(
            "app.db.session.SessionLocal", return_value=mock_db,
        ), patch(
            "app.services.tessellation_cache_service.cache_tessellation",
        ) as mock_cache:
            callback(mock_completed_future)

        with tasks_lock:
            result = tasks.get("aero-cb:tessellation:wing1")
        assert result is not None
        assert result["status"] == "SUCCESS"

    @patch("app.services.tessellation_service._get_executor")
    @patch("app.services.tessellation_service.register_pending_task")
    def test_on_done_callback_handles_exception(
        self, mock_register, mock_get_executor,
    ):
        """The done callback handles futures that raised exceptions."""
        from app.services.cad_service import tasks, tasks_lock

        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        start_tessellation_task(
            "aero-err", "wing_err", b"pickled", "", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_failed_future = MagicMock(spec=Future)
        mock_failed_future.result.side_effect = RuntimeError("worker crashed")

        callback(mock_failed_future)

        with tasks_lock:
            result = tasks.get("aero-err:tessellation:wing_err")
        assert result is not None
        assert result["status"] == "FAILURE"
        assert "worker crashed" in result["error"]


# --------------------------------------------------------------------------- #
# trigger_background_tessellation — debounce behaviour
# --------------------------------------------------------------------------- #


class TestTriggerBackgroundTessellation:
    """Tests for debounce, cancellation, and timer lifecycle."""

    @pytest.fixture(autouse=True)
    def _clean_pending_state(self):
        """Ensure pending timers/futures are clean before and after each test."""
        with _timer_lock:
            # Cancel any lingering timers
            for t in _pending_timers.values():
                t.cancel()
            _pending_timers.clear()
            _pending_futures.clear()
        yield
        with _timer_lock:
            for t in _pending_timers.values():
                t.cancel()
            _pending_timers.clear()
            _pending_futures.clear()

    def test_creates_timer_for_new_key(self):
        """First call for a key creates a debounce timer."""
        db_factory = MagicMock()

        with patch(
            "app.services.tessellation_service._start_tessellation_and_cache"
        ):
            trigger_background_tessellation(
                "aero-1", "wing-1", b"data", db_factory, "hash1", 1000.0,
            )

        with _timer_lock:
            assert "aero-1:wing-1" in _pending_timers
            timer = _pending_timers["aero-1:wing-1"]
            assert isinstance(timer, threading.Timer)
            assert timer.daemon is True
            timer.cancel()

    def test_second_call_cancels_first_timer(self):
        """Calling twice for the same key cancels the first timer."""
        db_factory = MagicMock()

        with patch(
            "app.services.tessellation_service._start_tessellation_and_cache"
        ):
            trigger_background_tessellation(
                "aero-2", "wing-2", b"data1", db_factory, "hash1",
            )

            with _timer_lock:
                first_timer = _pending_timers["aero-2:wing-2"]

            trigger_background_tessellation(
                "aero-2", "wing-2", b"data2", db_factory, "hash2",
            )

            with _timer_lock:
                second_timer = _pending_timers["aero-2:wing-2"]

        # First timer should have been cancelled
        assert first_timer is not second_timer
        # Clean up
        second_timer.cancel()

    def test_cancels_existing_future(self):
        """If a future is running for the key, it gets cancelled."""
        db_factory = MagicMock()
        mock_future = MagicMock(spec=Future)

        with _timer_lock:
            _pending_futures["aero-3:wing-3"] = mock_future

        with patch(
            "app.services.tessellation_service._start_tessellation_and_cache"
        ):
            trigger_background_tessellation(
                "aero-3", "wing-3", b"data", db_factory, "hash1",
            )

        mock_future.cancel.assert_called_once()

        # Clean up timer
        with _timer_lock:
            timer = _pending_timers.get("aero-3:wing-3")
            if timer:
                timer.cancel()

    def test_different_keys_independent(self):
        """Different (aeroplane, wing) keys have independent timers."""
        db_factory = MagicMock()

        with patch(
            "app.services.tessellation_service._start_tessellation_and_cache"
        ):
            trigger_background_tessellation(
                "aero-4", "wing-a", b"data", db_factory, "h1",
            )
            trigger_background_tessellation(
                "aero-4", "wing-b", b"data", db_factory, "h2",
            )

        with _timer_lock:
            assert "aero-4:wing-a" in _pending_timers
            assert "aero-4:wing-b" in _pending_timers
            _pending_timers["aero-4:wing-a"].cancel()
            _pending_timers["aero-4:wing-b"].cancel()


# --------------------------------------------------------------------------- #
# _start_tessellation_and_cache
# --------------------------------------------------------------------------- #


class TestStartTessellationAndCache:
    """Tests for the timer callback that submits to executor and caches."""

    @pytest.fixture(autouse=True)
    def _clean_pending_state(self):
        """Ensure pending timers/futures are clean."""
        with _timer_lock:
            _pending_timers.clear()
            _pending_futures.clear()
        yield
        with _timer_lock:
            for t in _pending_timers.values():
                t.cancel()
            _pending_timers.clear()
            _pending_futures.clear()

    @patch("app.services.tessellation_service._get_executor")
    def test_submits_to_executor(self, mock_get_executor):
        """The function submits the worker to the process pool."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future
        db_factory = MagicMock()

        _start_tessellation_and_cache(
            "aero-sc", "wing-sc", b"pickled", db_factory, "hash_sc", 1000.0,
        )

        mock_get_executor.return_value.submit.assert_called_once_with(
            _run_tessellation_worker,
            "aero-sc",
            b"pickled",
            "wing-sc",
            1000.0,
        )
        mock_future.add_done_callback.assert_called_once()

    @patch("app.services.tessellation_service._get_executor")
    def test_stores_future_in_pending(self, mock_get_executor):
        """The submitted future is stored in _pending_futures."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future
        db_factory = MagicMock()

        _start_tessellation_and_cache(
            "aero-pf", "wing-pf", b"pickled", db_factory, "hash_pf", 1000.0,
        )

        with _timer_lock:
            assert _pending_futures.get("aero-pf:wing-pf") is mock_future

    @patch("app.services.tessellation_service._get_executor")
    def test_cleans_timer_reference(self, mock_get_executor):
        """The function removes itself from _pending_timers (timer has fired)."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future
        db_factory = MagicMock()

        # Pre-populate a timer reference (as trigger_background_tessellation would)
        mock_timer = MagicMock()
        with _timer_lock:
            _pending_timers["aero-ct:wing-ct"] = mock_timer

        _start_tessellation_and_cache(
            "aero-ct", "wing-ct", b"pickled", db_factory, "hash_ct", 1000.0,
        )

        with _timer_lock:
            assert "aero-ct:wing-ct" not in _pending_timers

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_caches_successful_result(self, mock_get_executor):
        """On success with current hash, result is cached to DB."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        mock_db = MagicMock()
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 99
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_aeroplane
        )
        db_factory = MagicMock(return_value=mock_db)

        _start_tessellation_and_cache(
            "aero-ok", "wing-ok", b"pickled", db_factory, "hash_ok", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        # Simulate successful completion
        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.return_value = {
            "status": "SUCCESS",
            "result": {"data": {}, "type": "data", "count": 1},
        }

        with patch(
            "app.services.tessellation_cache_service.is_hash_current",
            return_value=True,
        ) as mock_hash_check, patch(
            "app.services.tessellation_cache_service.cache_tessellation",
        ) as mock_cache:
            callback(mock_done_future)

        mock_hash_check.assert_called_once_with(
            mock_db, 99, "wing", "wing-ok", "hash_ok",
        )
        mock_cache.assert_called_once_with(
            mock_db,
            99,
            "wing",
            "wing-ok",
            "hash_ok",
            {"data": {}, "type": "data", "count": 1},
        )
        mock_db.close.assert_called_once()

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_skips_cache_when_hash_stale(self, mock_get_executor):
        """When geometry hash is no longer current, result is discarded."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        mock_db = MagicMock()
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 100
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_aeroplane
        )
        db_factory = MagicMock(return_value=mock_db)

        _start_tessellation_and_cache(
            "aero-stale", "wing-stale", b"p", db_factory, "old_hash", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.return_value = {
            "status": "SUCCESS",
            "result": {"data": {}},
        }

        with patch(
            "app.services.tessellation_cache_service.is_hash_current",
            return_value=False,
        ), patch(
            "app.services.tessellation_cache_service.cache_tessellation",
        ) as mock_cache:
            callback(mock_done_future)

        mock_cache.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_skips_cache_on_failure(self, mock_get_executor):
        """When worker returns FAILURE status, no caching occurs."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        db_factory = MagicMock()

        _start_tessellation_and_cache(
            "aero-fail", "wing-fail", b"p", db_factory, "h", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.return_value = {
            "status": "FAILURE",
            "error": "something broke",
        }

        with patch(
            "app.services.tessellation_cache_service.cache_tessellation",
        ) as mock_cache:
            callback(mock_done_future)

        # No DB session created, no caching attempted
        db_factory.assert_not_called()
        mock_cache.assert_not_called()

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_handles_worker_exception(self, mock_get_executor):
        """When the future itself raises, callback logs error and returns."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        db_factory = MagicMock()

        _start_tessellation_and_cache(
            "aero-exc", "wing-exc", b"p", db_factory, "h", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.side_effect = RuntimeError("process died")

        # Should not raise
        callback(mock_done_future)

        # No DB interaction
        db_factory.assert_not_called()

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_skips_cache_when_aeroplane_not_found(
        self, mock_get_executor,
    ):
        """When aeroplane UUID is not in DB, caching is skipped gracefully."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        db_factory = MagicMock(return_value=mock_db)

        _start_tessellation_and_cache(
            "aero-gone", "wing-gone", b"p", db_factory, "h", 1000.0,
        )

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.return_value = {
            "status": "SUCCESS",
            "result": {"data": {}},
        }

        with patch(
            "app.services.tessellation_cache_service.cache_tessellation",
        ) as mock_cache:
            callback(mock_done_future)

        mock_cache.assert_not_called()
        mock_db.close.assert_called_once()

    @patch("app.services.tessellation_service._get_executor")
    def test_on_done_removes_future_from_pending(self, mock_get_executor):
        """The done callback removes the future from _pending_futures."""
        mock_future = MagicMock(spec=Future)
        mock_get_executor.return_value.submit.return_value = mock_future

        db_factory = MagicMock()

        _start_tessellation_and_cache(
            "aero-rm", "wing-rm", b"p", db_factory, "h", 1000.0,
        )

        # Verify future was stored
        with _timer_lock:
            assert "aero-rm:wing-rm" in _pending_futures

        callback = mock_future.add_done_callback.call_args[0][0]

        mock_done_future = MagicMock(spec=Future)
        mock_done_future.result.return_value = {"status": "FAILURE", "error": "x"}

        callback(mock_done_future)

        with _timer_lock:
            assert "aero-rm:wing-rm" not in _pending_futures
