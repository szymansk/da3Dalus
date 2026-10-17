"""Importer stage 5 (write) and the command line: all or nothing, atomic, idempotent."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.importer import IMPORTER_VERSION
from aero_kernel.importer.cli import main
from aero_kernel.tests.importer_builders import MINI_CANON, SOURCE_COMMIT, write_canon

MODEL = "canon_model.json"
REPORT = "IMPORT_REPORT.md"


def import_to(canon: Path, out: Path, *extra: str) -> int:
    """Run the command line on ``canon`` and return its exit code."""
    return main([str(canon), "--out", str(out), "--source-commit", SOURCE_COMMIT, *extra])


def test_the_import_writes_a_loadable_model_and_a_report(tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert import_to(write_canon(tmp_path), out) == 0
    model = load_canon_model(out / MODEL)
    assert model.source_commit == SOURCE_COMMIT
    assert model.importer_version == IMPORTER_VERSION
    assert model.schema_version == 1
    assert sorted(path.name for path in out.iterdir()) == [REPORT, MODEL]


def test_the_model_file_has_the_stable_format(tmp_path: Path) -> None:
    out = tmp_path / "out"
    import_to(write_canon(tmp_path), out)
    text = (out / MODEL).read_text(encoding="utf-8")
    document = json.loads(text)
    assert text == json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_the_report_names_commit_version_hash_counts_and_the_formula_table(tmp_path: Path) -> None:
    out = tmp_path / "out"
    import_to(write_canon(tmp_path), out)
    report = (out / REPORT).read_text(encoding="utf-8")
    model = load_canon_model(out / MODEL)
    assert SOURCE_COMMIT in report
    assert IMPORTER_VERSION in report
    assert model.content_hash in report
    assert "| formula | kind | tool | cost | applications |" in report
    assert "| weighing | procedure | AB | seconds | clean, flapped |" in report
    assert "| outer | optimization | OPT | minutes | default |" in report
    assert "- formulas: 5" in report
    assert "- quantities: 10" in report
    assert "- defaults: 1" in report
    assert str(tmp_path) not in report


def test_importing_twice_is_byte_identical(tmp_path: Path) -> None:
    """Q13, also from another directory and with another canon directory name."""
    first, second = tmp_path / "first", tmp_path / "second"
    canon = write_canon(tmp_path)
    assert import_to(canon, first) == 0
    moved = canon.rename(tmp_path / "other-name")
    assert import_to(moved, second) == 0
    for name in (MODEL, REPORT):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_the_content_hash_ignores_the_commit(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    one, two = tmp_path / "one", tmp_path / "two"
    import_to(canon, one)
    main([str(canon), "--out", str(two), "--source-commit", "f" * 40])
    assert load_canon_model(one / MODEL).content_hash == load_canon_model(two / MODEL).content_hash


def test_a_finding_writes_nothing_and_prints_file_field_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Q14: an unknown unit is a finding naming file and field; no file appears."""
    out = tmp_path / "out"
    canon = write_canon(
        tmp_path,
        {"quantities/gravity.md": MINI_CANON["quantities/gravity.md"].replace("m/s^2", "furlong")},
    )
    assert import_to(canon, out) == 1
    assert not out.exists()
    printed = capsys.readouterr().out
    assert "quantities/gravity.md: unit: " in printed
    assert "furlong" in printed
    assert "Traceback" not in printed


def test_a_finding_leaves_an_existing_model_untouched(tmp_path: Path) -> None:
    out = tmp_path / "out"
    good = write_canon(tmp_path)
    import_to(good, out)
    before = {name: (out / name).read_bytes() for name in (MODEL, REPORT)}
    bad = write_canon(
        tmp_path / "bad",
        {"quantities/gravity.md": MINI_CANON["quantities/gravity.md"].replace("m/s^2", "furlong")},
    )
    assert import_to(bad, out) == 1
    assert {name: (out / name).read_bytes() for name in (MODEL, REPORT)} == before


def test_a_failing_write_leaves_the_old_files_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    canon = write_canon(tmp_path)
    import_to(canon, out)
    before = {name: (out / name).read_bytes() for name in (MODEL, REPORT)}
    changed = write_canon(
        tmp_path / "changed",
        {"defaults.yaml": MINI_CANON["defaults.yaml"].replace("9.80665", "9.8")},
    )

    def refuse(*_: object) -> None:
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(os, "replace", refuse)
    assert import_to(changed, out) == 1
    assert "disk full" in capsys.readouterr().out
    assert {name: (out / name).read_bytes() for name in (MODEL, REPORT)} == before
    assert sorted(path.name for path in out.iterdir()) == [REPORT, MODEL]


def test_an_unreadable_canon_directory_is_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert import_to(tmp_path / "missing", tmp_path / "out") == 1
    assert "missing" in capsys.readouterr().out


def test_a_malformed_source_commit_is_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon = write_canon(tmp_path)
    assert main([str(canon), "--out", str(tmp_path / "out"), "--source-commit", "abc"]) == 1
    assert "source_commit" in capsys.readouterr().out


# --- the source commit from git ---------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` with a fixed identity and return its output."""
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def test_the_source_commit_defaults_to_the_git_head_of_the_canon(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    canon = write_canon(tmp_path)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "canon")
    out = tmp_path / "out"
    assert main([str(canon), "--out", str(out)]) == 0
    assert load_canon_model(out / MODEL).source_commit == git(tmp_path, "rev-parse", "HEAD")


def test_uncommitted_changes_under_the_canon_are_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    git(tmp_path, "init", "-q")
    canon = write_canon(tmp_path)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "canon")
    (canon / "quantities" / "gravity.md").write_text("changed\n", encoding="utf-8")
    out = tmp_path / "out"
    assert main([str(canon), "--out", str(out)]) == 1
    assert "uncommitted" in capsys.readouterr().out
    assert not out.exists()


def test_a_canon_outside_a_git_repository_needs_an_explicit_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon = write_canon(tmp_path)
    assert main([str(canon), "--out", str(tmp_path / "out")]) == 1
    assert "--source-commit" in capsys.readouterr().out


def test_a_missing_git_executable_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_git(*_: object, **__: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", no_git)
    assert main([str(write_canon(tmp_path)), "--out", str(tmp_path / "out")]) == 1
    assert "--source-commit" in capsys.readouterr().out


@pytest.mark.parametrize("existing", [False, True])
def test_the_outputs_have_normal_permissions_under_the_umask(
    tmp_path: Path, existing: bool
) -> None:
    """mkstemp makes 0600 files; the committed model must be 0666 minus the umask (S6)."""
    out = tmp_path / "out"
    previous = os.umask(0o022)
    try:
        canon = write_canon(tmp_path)
        if existing:
            import_to(canon, out)
            (out / MODEL).chmod(0o600)
        import_to(canon, out)
    finally:
        os.umask(previous)
    for name in (MODEL, REPORT):
        assert (out / name).stat().st_mode & 0o777 == 0o644
