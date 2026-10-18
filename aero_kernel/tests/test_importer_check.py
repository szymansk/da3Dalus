"""``importer --check``: the CI gate that keeps the committed model in step with the canon (ch. 8.9)."""

import json
import runpy
import subprocess
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.importer.cli import main
from aero_kernel.tests.importer_builders import MINI_CANON, write_canon

MODEL = "canon_model.json"
REPORT = "IMPORT_REPORT.md"


def import_to(canon: Path, out: Path) -> None:
    """Write the committed model the check compares against."""
    assert main([str(canon), "--out", str(out)]) == 0


def check(canon: Path, out: Path) -> int:
    """Run ``--check`` against the model in ``out``."""
    return main([str(canon), "--out", str(out), "--check"])


def snapshot(directory: Path) -> dict[str, bytes]:
    """The bytes of every file in a directory (empty if it does not exist)."""
    if not directory.exists():
        return {}
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def test_a_current_model_passes_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    before = snapshot(out)
    capsys.readouterr()
    assert check(canon, out) == 0
    expected = load_canon_model(out / MODEL).content_hash
    assert capsys.readouterr().out.strip() == f"{MODEL} is current ({expected})"
    assert snapshot(out) == before


def test_a_changed_canon_makes_the_model_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    committed = load_canon_model(out / MODEL).content_hash
    (canon / "defaults.yaml").write_text(
        MINI_CANON["defaults.yaml"].replace("9.80665", "9.8"), encoding="utf-8"
    )
    before = snapshot(out)
    capsys.readouterr()
    assert check(canon, out) == 1
    printed = capsys.readouterr().out
    assert printed.startswith(
        f"{MODEL} is stale: content_hash committed {committed}, canon sha256:"
    )
    assert "re-import with python -m aero_kernel.importer" in printed
    assert snapshot(out) == before


def test_a_finding_in_the_canon_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    (canon / "quantities" / "gravity.md").write_text("no front matter\n", encoding="utf-8")
    capsys.readouterr()
    assert check(canon, out) == 1
    printed = capsys.readouterr().out
    assert "quantities/gravity.md: front matter: no front matter between '---' lines" in printed
    assert "current" not in printed


def test_a_missing_committed_model_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check(write_canon(tmp_path), tmp_path / "nowhere") == 1
    assert f"{MODEL} is stale: it cannot be loaded" in capsys.readouterr().out


def test_an_unloadable_committed_model_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / MODEL).write_text("not json\n", encoding="utf-8")
    assert check(write_canon(tmp_path), out) == 1
    assert f"{MODEL} is stale: it cannot be loaded" in capsys.readouterr().out


def test_a_different_importer_version_makes_the_model_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    document = json.loads((out / MODEL).read_text(encoding="utf-8"))
    document["importer_version"] = "0.0.1"
    (out / MODEL).write_text(json.dumps(document), encoding="utf-8")
    capsys.readouterr()
    assert check(canon, out) == 1
    assert "importer_version committed 0.0.1, importer " in capsys.readouterr().out


def test_a_different_schema_version_makes_the_model_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    document = json.loads((out / MODEL).read_text(encoding="utf-8"))
    document["schema_version"] = 2
    (out / MODEL).write_text(json.dumps(document), encoding="utf-8")
    capsys.readouterr()
    assert check(canon, out) == 1
    assert f"{MODEL} is stale: it cannot be loaded" in capsys.readouterr().out


def test_the_check_needs_no_git_and_ignores_a_dirty_canon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    calls: list[list[str]] = []

    def no_git(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", no_git)
    assert check(canon, out) == 0
    assert calls == []


def test_the_report_file_is_not_compared(tmp_path: Path) -> None:
    """The report is not part of what the check compares."""
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    (out / REPORT).write_text("edited\n", encoding="utf-8")
    assert check(canon, out) == 0


def test_run_as_a_module_the_import_check_exits_1_on_a_stale_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI runs ``python -m aero_kernel.importer ... --check``; that entry point must really run."""
    canon, out = write_canon(tmp_path), tmp_path / "out"
    import_to(canon, out)
    (canon / "defaults.yaml").write_text(
        MINI_CANON["defaults.yaml"].replace("9.80665", "9.8"), encoding="utf-8"
    )
    monkeypatch.setattr("sys.argv", ["importer", str(canon), "--out", str(out), "--check"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("aero_kernel.importer", run_name="__main__")
    assert raised.value.code == 1
