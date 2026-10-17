"""The runtime loader of the canon model (ARCHITECTURE ch. 8.9)."""

import builtins
import io
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

import pytest
from aero_kernel.canon import load
from aero_kernel.canon.load import CanonLoadError, load_canon_model
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory
from aero_kernel.tests.canon_builders import base_model


def write_model(tmp_path: Path, raw: Any, name: str = "canon_model.json") -> Path:
    """Write ``raw`` as JSON to ``tmp_path / name`` and return the file."""
    path = tmp_path / name
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_valid_model_loads(tmp_path: Path) -> None:
    model = load_canon_model(write_model(tmp_path, base_model()))
    assert model.namespaces["calc"].quantities["weight"].unit == "N"


def test_default_path_is_the_packaged_model() -> None:
    assert load.default_model_path().name == "canon_model.json"
    assert load.default_model_path().parent.name == "canon"


def test_no_path_loads_the_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_model(tmp_path, base_model())
    monkeypatch.setattr(load, "default_model_path", lambda: path)
    assert load_canon_model().content_hash == base_model()["content_hash"]


def test_loading_logs_one_info_line(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = write_model(tmp_path, base_model())
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.canon.load"):
        load_canon_model(path)
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
        load_canon_model(write_model(tmp_path, raw))
    assert_internal(caught.value)
    assert caught.value.error.detail == {"schema_version": version, "supported": 1}
    assert "schema_version" in caught.value.error.message


def test_missing_schema_version_is_refused(tmp_path: Path) -> None:
    raw = base_model()
    del raw["schema_version"]
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(write_model(tmp_path, raw))
    assert_internal(caught.value)


def test_missing_file_is_internal(tmp_path: Path) -> None:
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(tmp_path / "absent.json")
    assert_internal(caught.value)
    assert str(tmp_path) not in caught.value.error.message  # ADR 0019: no internal paths


def test_unreadable_json_is_internal(tmp_path: Path) -> None:
    path = tmp_path / "canon_model.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(path)
    assert_internal(caught.value)


def test_json_that_is_no_object_is_internal(tmp_path: Path) -> None:
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(write_model(tmp_path, [1, 2]))
    assert_internal(caught.value)


def test_invalid_model_lists_the_findings(tmp_path: Path) -> None:
    raw = base_model()
    raw["namespaces"]["calc"]["quantities"]["weight"]["unit"] = "furlong"
    raw["source_commit"] = "xyz"
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(write_model(tmp_path, raw))
    assert_internal(caught.value)
    detail = caught.value.error.detail
    assert detail["error_count"] == 2
    locations = {entry["loc"] for entry in detail["errors"]}  # type: ignore[index, union-attr]
    assert locations == {"source_commit", "namespaces.calc.quantities.weight.unit"}


def test_hash_mismatch_is_internal(tmp_path: Path) -> None:
    raw = base_model()
    raw["namespaces"]["calc"]["defaults"]["gravity"]["value"] = 9.81
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(write_model(tmp_path, raw))
    assert_internal(caught.value)


def test_load_failure_is_logged_once_at_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with (
        caplog.at_level(logging.DEBUG, logger="aero_kernel.canon.load"),
        pytest.raises(CanonLoadError),
    ):
        load_canon_model(tmp_path / "absent.json")
    assert [r.levelno for r in caplog.records if r.levelno >= logging.INFO] == [logging.ERROR]


def test_loader_opens_only_the_model_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Spy on every way to open a file, not only ``read_text`` (Q12: no canon document)."""
    path = write_model(tmp_path, base_model())
    opened: list[str] = []
    originals: dict[str, Callable[..., Any]] = {
        "builtins": builtins.open,
        "io": io.open,
        "path": Path.open,
        "os": os.open,
    }

    def spy(original: Callable[..., Any]) -> Callable[..., Any]:
        def recording(file: Any, *args: Any, **kwargs: Any) -> Any:
            opened.append(str(file))
            return original(file, *args, **kwargs)

        return recording

    def path_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(self))
        return originals["path"](self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy(originals["builtins"]))
    monkeypatch.setattr(io, "open", spy(originals["io"]))
    monkeypatch.setattr(os, "open", spy(originals["os"]))
    monkeypatch.setattr(Path, "open", path_open)
    path.read_text(encoding="utf-8")
    one_read = list(opened)  # what a single read of the model costs through the three entry points
    opened.clear()
    load_canon_model(path)
    assert opened == one_read
    assert set(opened) == {str(path)}


def failures(tmp_path: Path) -> list[CanonLoadError]:
    """Provoke one load failure of every kind and return the exceptions."""
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 200_000, encoding="utf-8")
    wrong_version = dict(base_model(), schema_version=2)
    invalid = dict(base_model(), source_commit="xyz")
    paths = [
        tmp_path / "absent.json",
        corrupt,
        deep,
        write_model(tmp_path, [1], "non_object.json"),
        write_model(tmp_path, wrong_version, "wrong_version.json"),
        write_model(tmp_path, invalid, "invalid.json"),
    ]
    caught: list[CanonLoadError] = []
    for path in paths:
        with pytest.raises(CanonLoadError) as raised:
            load_canon_model(path)
        caught.append(raised.value)
    return caught


def test_no_load_error_message_holds_a_file_path(tmp_path: Path) -> None:
    for error in failures(tmp_path):
        text = f"{error} {error.error.message} {error.error.hint} {error.error.detail}"
        assert str(tmp_path) not in text
        assert ".json" not in text
        assert "/" not in error.error.message


def test_deeply_nested_json_is_a_load_error(tmp_path: Path) -> None:
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 200_000, encoding="utf-8")
    with pytest.raises(CanonLoadError) as caught:
        load_canon_model(deep)
    assert_internal(caught.value)
    assert "nested" in caught.value.error.message


def test_error_log_carries_the_cause_and_the_findings_but_no_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    invalid = write_model(tmp_path, dict(base_model(), source_commit="xyz"))
    with (
        caplog.at_level(logging.ERROR, logger="aero_kernel.canon.load"),
        pytest.raises(CanonLoadError),
    ):
        load_canon_model(invalid)
    with (
        caplog.at_level(logging.ERROR, logger="aero_kernel.canon.load"),
        pytest.raises(CanonLoadError),
    ):
        load_canon_model(tmp_path / "absent.json")
    findings, missing = caplog.records
    assert findings.exc_info is not None
    assert findings.findings["error_count"] == 1  # type: ignore[attr-defined]  # logging extra
    assert missing.exc_info is not None
    assert all(str(tmp_path) not in r.getMessage() for r in caplog.records)


def test_supported_schema_version_is_the_models_literal() -> None:
    literal = get_args(CanonModel.model_fields["schema_version"].annotation)
    assert literal == (load.SUPPORTED_SCHEMA_VERSION,)


@pytest.mark.parametrize("content", ["{not json", "[" * 200_000], ids=["json", "nested"])
def test_json_and_nesting_failures_log_their_cause(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, content: str
) -> None:
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with (
        caplog.at_level(logging.ERROR, logger="aero_kernel.canon.load"),
        pytest.raises(CanonLoadError),
    ):
        load_canon_model(path)
    (record,) = caplog.records
    assert record.exc_info is not None
