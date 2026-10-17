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


def test_a_change_outside_the_canon_directory_does_not_matter(
    repo: tuple[Path, Path], tmp_path: Path
) -> None:
    """The dirty check is scoped to the canon directory."""
    _, root = repo
    canon = root / "canon"
    (root / "elsewhere.txt").write_text("untracked\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignored\n", encoding="utf-8")
    assert run(canon, tmp_path / "out") == 0


def test_the_dirty_finding_does_not_advertise_the_explicit_commit_as_a_way_out(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, _ = repo
    (canon / GRAVITY).write_text(MINI_CANON[GRAVITY] + "more\n", encoding="utf-8")
    assert run(canon, tmp_path / "out") == 1
    printed = capsys.readouterr().out
    assert "uncommitted" in printed
    assert "--source-commit" not in printed


# --- S3 amendment 3: git decided on exit codes and the file system, not on English text ---------------


def fake_run(
    results: dict[str, subprocess.CompletedProcess[str]],
    real: object = subprocess.run,
) -> object:
    """Return a ``subprocess.run`` stand-in answering the git sub-commands in ``results``."""

    def run_(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        for word, done in results.items():
            if word in command:
                return done
        return real(command, **kwargs)  # type: ignore[operator,no-any-return]  # forwards to the real run

    return run_


def completed(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    """A finished git command."""
    return subprocess.CompletedProcess(["git"], code, out, err)


def test_a_localised_not_a_repository_message_still_takes_the_outside_git_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    german = completed(
        128, err="fatal: Kein Git-Repository (oder irgendein Elternverzeichnis): .git"
    )
    monkeypatch.setattr(subprocess, "run", fake_run({"--is-inside-work-tree": german}))
    canon = write_canon(tmp_path)
    assert run(canon, tmp_path / "out", "--source-commit", "b" * 40) == 0


def test_git_runs_with_the_c_locale(
    repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canon, _ = repo
    environments: list[dict[str, str]] = []
    real = subprocess.run

    def spy(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        environments.append(dict(kwargs["env"]))  # type: ignore[call-overload]  # the env of every git call
        return real(command, **kwargs)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", spy)
    assert run(canon, tmp_path / "out") == 0
    assert environments
    assert all(env["LC_ALL"] == "C" and env["LANGUAGE"] == "" for env in environments)


def test_a_canon_inside_the_git_directory_is_a_finding(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, root = repo
    assert run(root / ".git" / "hooks", tmp_path / "out", "--source-commit", "a" * 40) == 1
    assert "inside a git directory, not in a work tree" in capsys.readouterr().out


def test_a_malformed_commit_is_judged_before_git_is_called(
    repo: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    canon, _ = repo
    calls: list[list[str]] = []
    real = subprocess.run

    def spy(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return real(command, **kwargs)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", spy)
    assert run(canon, tmp_path / "out", "--source-commit", "not-a-sha") == 1
    assert calls == []
    assert "40-character" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "--is-inside-work-tree",
            "git rev-parse --is-inside-work-tree failed (exit 128): fatal: dubious ownership",
        ),
        ("diff", "git diff failed (exit 2): fatal: boom"),
    ],
)
def test_every_failing_git_command_is_a_finding_with_exit_code_and_stderr(
    repo: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    expected: str,
) -> None:
    canon, root = repo
    code = 128 if command == "--is-inside-work-tree" else 2
    err = "fatal: dubious ownership" if code == 128 else "fatal: boom"
    monkeypatch.setattr(subprocess, "run", fake_run({command: completed(code, err=err)}))
    assert run(canon, tmp_path / "out", "--source-commit", git(root, "rev-parse", "HEAD")) == 1
    assert expected in capsys.readouterr().out


def test_an_empty_repository_without_a_head_is_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    git(root, "init", "-q")
    canon = write_canon(root)
    assert run(canon, tmp_path / "out") == 1
    printed = capsys.readouterr().out
    assert "git rev-parse HEAD failed" in printed
    assert "uncommitted" in printed  # both are reported


def test_a_later_commit_elsewhere_does_not_invalidate_the_canon_commit(
    repo: tuple[Path, Path], tmp_path: Path
) -> None:
    canon, root = repo
    earlier = git(root, "rev-parse", "HEAD")
    (root / "unrelated.txt").write_text("x\n", encoding="utf-8")
    git(root, "add", "unrelated.txt")
    git(root, "commit", "-q", "-m", "unrelated")
    assert run(canon, tmp_path / "out", "--source-commit", earlier) == 0


def test_a_tree_is_not_a_commit(
    repo: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    canon, root = repo
    tree = git(root, "rev-parse", "HEAD^{tree}")
    assert run(canon, tmp_path / "out", "--source-commit", tree) == 1
    assert "not a commit of this repository" in capsys.readouterr().out
