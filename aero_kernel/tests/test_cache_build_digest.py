"""Build digest (ARCHITECTURE ch. 8.4, Q27)."""

import hashlib
import logging
from pathlib import Path

import pytest
from aero_kernel.cache import build_digest
from aero_kernel.canonical import sha256_of


def _tree(root: Path) -> Path:
    """A fake package: code, excluded directories and a canon model."""
    (root / "formulas").mkdir(parents=True)
    (root / "canon").mkdir()
    (root / "tests").mkdir()
    (root / "tools").mkdir()
    (root / "importer").mkdir()
    (root / "engine.py").write_text("a = 1\n")
    (root / "formulas" / "tools.py").write_text("b = 2\n")
    (root / "canon" / "canon_model.json").write_text("{}")
    for excluded in ("tests", "tools", "importer"):
        (root / excluded / "x.py").write_text("c = 3\n")
    return root


def test_digest_is_prefixed_sha256(tmp_path: Path) -> None:
    digest = build_digest(_tree(tmp_path))
    assert digest.startswith("sha256:")
    assert digest == build_digest(tmp_path)


@pytest.mark.parametrize("relative", ["engine.py", "formulas/tools.py", "canon/canon_model.json"])
def test_changed_file_changes_digest(tmp_path: Path, relative: str) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / relative).write_text("changed\n")
    assert build_digest(root) != before


def test_new_py_file_changes_digest(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / "new.py").write_text("")
    assert build_digest(root) != before


@pytest.mark.parametrize("excluded", ["tests", "tools", "importer"])
def test_top_level_excluded_directories_do_not_count(tmp_path: Path, excluded: str) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / excluded / "x.py").write_text("changed\n")
    (root / excluded / "y.py").write_text("new\n")
    assert build_digest(root) == before


def test_non_py_files_do_not_count(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / "README.md").write_text("x")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "engine.cpython-311.pyc").write_bytes(b"x")
    assert build_digest(root) == before


def test_missing_canon_model_is_a_stable_state(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = _tree(tmp_path)
    (root / "canon" / "canon_model.json").unlink()
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        digest = build_digest(root)
    assert digest == build_digest(root)
    assert "canon_model.json" in caplog.text
    (root / "canon" / "canon_model.json").write_text("{}")
    assert build_digest(root) != digest


def test_default_root_is_the_package() -> None:
    assert build_digest().startswith("sha256:")


def test_a_nested_directory_named_tools_counts(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "formulas" / "tools").mkdir()
    (root / "formulas" / "tools" / "x.py").write_text("b = 2\n")
    before = build_digest(root)
    (root / "formulas" / "tools" / "x.py").write_text("b = 3\n")
    assert build_digest(root) != before


def test_the_absent_canon_model_enters_the_digest_as_null(tmp_path: Path) -> None:
    root = tmp_path
    (root / "canon").mkdir()
    (root / "engine.py").write_text("a = 1\n")
    engine_hash = hashlib.sha256(b"a = 1\n").hexdigest()
    expected = sha256_of(
        [
            {"path": "engine.py", "sha256": engine_hash},
            {"path": "canon/canon_model.json", "sha256": None},
        ]
    )
    assert build_digest(root) == expected


def test_the_absent_canon_model_is_logged_at_debug_only(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = _tree(tmp_path)
    (root / "canon" / "canon_model.json").unlink()
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.cache"):
        build_digest(root)
    levels = [record.levelno for record in caplog.records if "canon" in record.getMessage()]
    assert levels == [logging.DEBUG]


def test_renaming_a_file_changes_the_digest(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / "engine.py").rename(root / "engine2.py")
    assert build_digest(root) != before


def test_an_edit_of_the_same_size_changes_the_digest(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = build_digest(root)
    (root / "engine.py").write_text("a = 2\n")
    assert build_digest(root) != before
