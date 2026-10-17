"""The source-commit gate: the commit a packaged model names is on main and matches the canon (A2)."""

import subprocess
from pathlib import Path

import pytest
from aero_kernel.importer.cli import main as import_main
from aero_kernel.importer.gate import main
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


class Setup:
    """A repository whose ``origin/main`` is a local ref, with the mini canon and its model."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repo"
        self.root.mkdir()
        git(self.root, "init", "-q")
        self.canon = write_canon(self.root)
        git(self.root, "add", ".")
        git(self.root, "commit", "-q", "-m", "canon")
        self.model_dir = tmp_path / "model"
        self.publish_main()
        self.reimport()

    def publish_main(self) -> None:
        """Make ``origin/main`` point at HEAD, as a fetched main does."""
        git(self.root, "update-ref", "refs/remotes/origin/main", "HEAD")

    def reimport(self) -> None:
        """Write the model from the canon at HEAD's last canon commit."""
        assert import_main([str(self.canon), "--out", str(self.model_dir)]) == 0

    def run(self, *extra: str) -> int:
        """Run the gate."""
        return main([str(self.canon), "--model", str(self.model_dir / "canon_model.json"), *extra])

    def edit_canon(self) -> None:
        """Commit a change of the canon."""
        text = MINI_CANON[GRAVITY] + "more prose\n"
        (self.canon / GRAVITY).write_text(text, encoding="utf-8")
        git(self.root, "commit", "-q", "-am", "edit the canon")


@pytest.fixture
def setup(tmp_path: Path) -> Setup:
    return Setup(tmp_path)


def test_a_model_from_a_commit_on_main_passes(
    setup: Setup, capsys: pytest.CaptureFixture[str]
) -> None:
    assert setup.run() == 0
    sha = git(setup.root, "rev-parse", "HEAD")
    assert (
        capsys.readouterr().out.strip()
        == f"source commit {sha} is on origin/main and the canon matches it"
    )


def test_a_canon_edited_on_a_branch_is_a_finding(
    setup: Setup, capsys: pytest.CaptureFixture[str]
) -> None:
    git(setup.root, "checkout", "-q", "-b", "feature")
    setup.edit_canon()
    setup.reimport()  # the model names the branch commit, which main does not have
    sha = git(setup.root, "rev-parse", "HEAD")
    capsys.readouterr()  # the re-import printed a line
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == (
        f"source commit {sha} is not on origin/main: canon edited on the branch; land it on main first and re-import"
    )


def test_a_canon_edited_after_the_recorded_commit_is_a_finding(
    setup: Setup, capsys: pytest.CaptureFixture[str]
) -> None:
    recorded = git(setup.root, "rev-parse", "HEAD")
    setup.edit_canon()
    setup.publish_main()  # the edit is on main, but the model was not re-imported
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == (
        f"the canon directory differs from source commit {recorded}: re-import the model"
    )


def test_a_commit_the_repository_does_not_have_is_a_finding(
    setup: Setup, capsys: pytest.CaptureFixture[str]
) -> None:
    text = (setup.model_dir / "canon_model.json").read_text(encoding="utf-8")
    sha = text.split('"source_commit": "')[1][:40]
    (setup.model_dir / "canon_model.json").write_text(text.replace(sha, "a" * 40), encoding="utf-8")
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == (
        f"source commit {'a' * 40} is not in this repository's history: fetch the full history"
    )


def test_a_missing_upstream_is_a_finding(setup: Setup, capsys: pytest.CaptureFixture[str]) -> None:
    git(setup.root, "update-ref", "-d", "refs/remotes/origin/main")
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == (
        "cannot resolve origin/main: fetch it (git fetch origin main)"
    )


def test_another_upstream_can_be_named(setup: Setup) -> None:
    git(setup.root, "update-ref", "refs/remotes/origin/release", "HEAD")
    assert setup.run("--upstream", "origin/release") == 0


def test_a_shallow_clone_is_a_finding(
    setup: Setup, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", setup.root.as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    code = main(
        [
            str(clone / "canon"),
            "--model",
            str(setup.model_dir / "canon_model.json"),
            "--upstream",
            "origin/main",
        ]
    )
    assert code == 1
    assert capsys.readouterr().out.strip() == (
        "shallow clone: fetch the full history (git fetch --unshallow); the ancestry of the source commit is unknown"
    )


def test_a_missing_model_is_a_finding(setup: Setup, capsys: pytest.CaptureFixture[str]) -> None:
    (setup.model_dir / "canon_model.json").unlink()
    assert setup.run() == 1
    assert capsys.readouterr().out.strip().startswith("canon_model.json cannot be loaded")


def test_a_failing_git_command_is_a_finding_with_its_exit_code(
    setup: Setup, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = subprocess.run

    def failing(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "merge-base" in command:
            return subprocess.CompletedProcess(command, 128, "", "fatal: boom")
        return real(command, **kwargs)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", failing)
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == "git merge-base failed (exit 128): fatal: boom"


def test_git_missing_is_a_finding(
    setup: Setup, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_git(*_: object, **__: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", no_git)
    assert setup.run() == 1
    assert capsys.readouterr().out.strip() == "git is not available"
