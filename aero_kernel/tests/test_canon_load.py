"""The runtime loader of the canon model (ARCHITECTURE ch. 8.9)."""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.canon import load
from aero_kernel.canon.load import CanonLoadError, load_model
from aero_kernel.errors import ErrorCategory
from aero_kernel.tests.canon_builders import base_model


def write_model(tmp_path: Path, raw: Any) -> Path:
    """Write ``raw`` as JSON and return the file."""
    path = tmp_path / "canon_model.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_valid_model_loads(tmp_path: Path) -> None:
    model = load_model(write_model(tmp_path, base_model()))
    assert model.namespaces["calc"].quantities["weight"].unit == "N"


def test_default_path_is_the_packaged_model() -> None:
    assert load.DEFAULT_MODEL_PATH.name == "canon_model.json"
    assert load.DEFAULT_MODEL_PATH.parent.name == "canon"


def test_no_path_loads_the_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(load, "DEFAULT_MODEL_PATH", write_model(tmp_path, base_model()))
    assert load_model().content_hash == base_model()["content_hash"]


def test_loading_logs_one_info_line(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = write_model(tmp_path, base_model())
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.canon.load"):
        load_model(path)
    records = [r for r in caplog.records if r.levelno >= logging.INFO]
    assert [r.levelno for r in records] == [logging.INFO]
    assert base_model()["content_hash"] in records[0].getMessage()


def assert_internal(error: CanonLoadError) -> None:
    """Check the shape every load failure has: internal, escalate, not retryable."""
    kernel_error = error.error
    assert kernel_error.category is ErrorCategory.INTERNAL
    assert kernel_error.code == "internal"
    assert kernel_error.escalate is True
    assert kernel_error.retryable is False
    assert kernel_error.message
    assert kernel_error.hint


@pytest.mark.parametrize("version", [2, 0, "1", True, None])
def test_unknown_schema_version_is_refused_before_type_validation(
    tmp_path: Path, version: object
) -> None:
    raw = base_model()
    raw["schema_version"] = version
    raw["a_field_of_a_newer_shape"] = {}
    with pytest.raises(CanonLoadError) as caught:
        load_model(write_model(tmp_path, raw))
    assert_internal(caught.value)
    assert caught.value.error.detail == {"schema_version": version, "supported": 1}
    assert "schema_version" in caught.value.error.message


def test_missing_schema_version_is_refused(tmp_path: Path) -> None:
    raw = base_model()
    del raw["schema_version"]
    with pytest.raises(CanonLoadError) as caught:
        load_model(write_model(tmp_path, raw))
    assert_internal(caught.value)


def test_missing_file_is_internal(tmp_path: Path) -> None:
    with pytest.raises(CanonLoadError) as caught:
        load_model(tmp_path / "absent.json")
    assert_internal(caught.value)
    assert str(tmp_path) not in caught.value.error.message  # ADR 0019: no internal paths


def test_unreadable_json_is_internal(tmp_path: Path) -> None:
    path = tmp_path / "canon_model.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CanonLoadError) as caught:
        load_model(path)
    assert_internal(caught.value)


def test_json_that_is_no_object_is_internal(tmp_path: Path) -> None:
    with pytest.raises(CanonLoadError) as caught:
        load_model(write_model(tmp_path, [1, 2]))
    assert_internal(caught.value)


def test_invalid_model_lists_the_findings(tmp_path: Path) -> None:
    raw = base_model()
    raw["namespaces"]["calc"]["quantities"]["weight"]["unit"] = "furlong"
    raw["source_commit"] = "xyz"
    with pytest.raises(CanonLoadError) as caught:
        load_model(write_model(tmp_path, raw))
    assert_internal(caught.value)
    detail = caught.value.error.detail
    assert detail["error_count"] == 2
    locations = {entry["loc"] for entry in detail["errors"]}  # type: ignore[index, union-attr]
    assert locations == {"source_commit", "namespaces.calc.quantities.weight.unit"}


def test_hash_mismatch_is_internal(tmp_path: Path) -> None:
    raw = base_model()
    raw["namespaces"]["calc"]["quantities"]["gravity"]["default"]["value"] = 9.81
    with pytest.raises(CanonLoadError) as caught:
        load_model(write_model(tmp_path, raw))
    assert_internal(caught.value)


def test_load_failure_is_logged_once_at_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel.canon.load"),
        pytest.raises(CanonLoadError),
    ):
        load_model(tmp_path / "absent.json")
    assert [r.levelno for r in caplog.records if r.levelno >= logging.INFO] == [logging.ERROR]


def test_loader_reads_only_the_model_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_model(tmp_path, base_model())
    read: list[Path] = []
    original = Path.read_text

    def recording(self: Path, *args: Any, **kwargs: Any) -> str:
        read.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording)
    load_model(path)
    assert read == [path]
