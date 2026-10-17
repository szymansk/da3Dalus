"""The source commit of an import: git is always consulted inside a work tree (S3 amendment 1, T2)."""

import subprocess
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.importer.cli import main
from aero_kernel.tests.importer_builders import MINI_CANON, write_canon

GRAVITY = "quantities/gravity.md"


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` with a fixed identity and return its output."""
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    """A git repository with the mini canon committed: ``(canon directory, repository)``."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    canon = write_canon(root)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "canon")
    return canon, root


def run(canon: Path, out: Path, *extra: str) -> int:
    """Run the command line on ``canon``."""
    return main([str(canon), "--out", str(out), *extra])


def test_an_explicit_commit_that_matches_the_canon_is_taken(
    repo: tuple[Path, Path], tmp_path: Path
) -> None:
    canon, root = repo
    head = git(root, "rev-parse", "HEAD")
    assert run(canon, tmp_path / "out", "--source-commit", head) == 0
    assert load_canon_model(tmp_path / "out" / "canon_model.json").source_commit == head


def test_an_explicit_commit_does_not_skip_the_dirty_check(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, root = repo
    (canon / GRAVITY).write_text(MINI_CANON[GRAVITY] + "more\n", encoding="utf-8")
    assert run(canon, tmp_path / "out", "--source-commit", git(root, "rev-parse", "HEAD")) == 1
    assert "uncommitted" in capsys.readouterr().out


def test_a_staged_change_is_a_finding(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, root = repo
    (canon / GRAVITY).write_text(MINI_CANON[GRAVITY] + "more\n", encoding="utf-8")
    git(root, "add", ".")
    assert run(canon, tmp_path / "out", "--source-commit", git(root, "rev-parse", "HEAD")) == 1
    assert "uncommitted" in capsys.readouterr().out


def test_an_untracked_file_under_the_canon_is_a_finding(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, _ = repo
    (canon / "formulas" / "new.md").write_text("x\n", encoding="utf-8")
    assert run(canon, tmp_path / "out") == 1
    assert "uncommitted" in capsys.readouterr().out


def test_a_commit_the_repository_does_not_have_is_a_finding(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, _ = repo
    assert run(canon, tmp_path / "out", "--source-commit", "a" * 40) == 1
    assert "not a commit" in capsys.readouterr().out


def test_a_commit_the_canon_has_moved_on_from_is_a_finding(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, root = repo
    old = git(root, "rev-parse", "HEAD")
    (canon / GRAVITY).write_text(MINI_CANON[GRAVITY] + "more\n", encoding="utf-8")
    git(root, "commit", "-q", "-am", "change")
    assert run(canon, tmp_path / "out", "--source-commit", old) == 1
    assert "differs from commit" in capsys.readouterr().out


def test_the_dirty_finding_comes_with_the_findings_of_stage_1(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, _ = repo
    (canon / GRAVITY).write_text("no front matter\n", encoding="utf-8")
    assert run(canon, tmp_path / "out") == 1
    printed = capsys.readouterr().out
    assert "uncommitted" in printed
    assert "front matter" in printed


def test_a_failing_git_command_is_a_finding_not_a_pass(
    repo: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    canon, _ = repo
    real = subprocess.run

    def failing(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "status" in command:
            return subprocess.CompletedProcess(command, 2, "", "fatal: boom")
        return real(command, **kwargs)  # type: ignore[call-overload,no-any-return]  # forwards to the real run

    monkeypatch.setattr(subprocess, "run", failing)
    assert run(canon, tmp_path / "out") == 1
    assert "git status failed" in capsys.readouterr().out


def test_git_missing_inside_a_repository_is_a_finding(
    repo: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    canon, _ = repo

    def no_git(*_: object, **__: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", no_git)
    assert run(canon, tmp_path / "out", "--source-commit", "a" * 40) == 1
    assert "git is not available" in capsys.readouterr().out


def test_outside_git_an_explicit_commit_is_taken_as_given(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    assert run(canon, tmp_path / "out", "--source-commit", "b" * 40) == 0
    assert load_canon_model(tmp_path / "out" / "canon_model.json").source_commit == "b" * 40


def test_outside_git_without_a_commit_is_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(write_canon(tmp_path), tmp_path / "out") == 1
    assert "--source-commit" in capsys.readouterr().out
