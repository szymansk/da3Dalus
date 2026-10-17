"""The source-commit gate: the commit a packaged model names is on main and matches the canon.

``python -m aero_kernel.importer.gate <canon-dir> [--model <canon_model.json>] [--upstream origin/main]``

CI runs it on pull requests and on main. The packaged model names the last commit that touched the
canon document (ARCHITECTURE ch. 8.9). That commit must survive a squash or rebase of the kernel
branch, so it must already be on main; and the canon directory must be what that commit holds.
Anything else means the canon was edited on the branch (it must land on main first) or the model was
not re-imported. Every failure is one line that names its cause.
"""

import argparse
from pathlib import Path

from aero_kernel.canon.load import CanonLoadError, default_model_path, load_canon_model
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.source import run_git

__all__ = ["check_source_commit", "main"]


def _line(message: str) -> list[Finding]:
    """A single gate finding."""
    return [Finding(file=".", field="source_commit", message=message)]


def check_source_commit(canon_dir: Path, model_path: Path, upstream: str) -> list[Finding]:
    """Check that the model's source commit is on ``upstream`` and equals the canon directory.

    Args:
        canon_dir: The canon document directory (inside a git work tree).
        model_path: The packaged ``canon_model.json``.
        upstream: The ref of main, e.g. ``origin/main``.

    Returns:
        Empty if the gate passes, otherwise one finding naming the cause.
    """
    try:
        sha = load_canon_model(model_path).source_commit
    except CanonLoadError as exc:
        return _line(f"{model_path.name} cannot be loaded ({exc})")
    shallow = run_git(canon_dir, "rev-parse", "--is-shallow-repository")
    if shallow is None:
        return _line("git is not available")
    if shallow.returncode == 0 and shallow.stdout.strip() == "true":
        return _line(
            "shallow clone: fetch the full history (git fetch --unshallow); "
            "the ancestry of the source commit is unknown"
        )
    known = run_git(canon_dir, "cat-file", "-e", f"{sha}^{{commit}}")
    if known is None or known.returncode != 0:
        return _line(
            f"source commit {sha} is not in this repository's history: fetch the full history"
        )
    main_ref = run_git(canon_dir, "rev-parse", "--verify", "--quiet", f"{upstream}^{{commit}}")
    if main_ref is None or main_ref.returncode != 0:
        return _line(f"cannot resolve {upstream}: fetch it (git fetch origin main)")
    ancestor = run_git(canon_dir, "merge-base", "--is-ancestor", sha, upstream)
    if ancestor is None:
        return _line("git is not available")
    if ancestor.returncode == 1:
        return _line(
            f"source commit {sha} is not on {upstream}: canon edited on the branch; "
            "land it on main first and re-import"
        )
    if ancestor.returncode != 0:
        return _line(
            f"git merge-base failed (exit {ancestor.returncode}): {ancestor.stderr.strip()}"
        )
    same = run_git(canon_dir, "diff", "--quiet", sha, "--", ".")
    if same is None:
        return _line("git is not available")
    if same.returncode == 1:
        return _line(f"the canon directory differs from source commit {sha}: re-import the model")
    if same.returncode != 0:
        return _line(f"git diff failed (exit {same.returncode}): {same.stderr.strip()}")
    return []


def main(argv: list[str] | None = None) -> int:
    """Run the gate.

    Args:
        argv: Command-line arguments; ``None`` means ``sys.argv[1:]``.

    Returns:
        ``0`` if the gate passes, ``1`` with the cause on standard output otherwise.
    """
    parser = argparse.ArgumentParser(
        prog="python -m aero_kernel.importer.gate",
        description="Fail unless the packaged model's source commit is on main and matches the canon.",
    )
    parser.add_argument("canon_dir", type=Path, help="the canon document directory")
    parser.add_argument("--model", type=Path, default=default_model_path())
    parser.add_argument("--upstream", default="origin/main", help="the ref of main")
    arguments = parser.parse_args(argv)
    findings = check_source_commit(arguments.canon_dir, arguments.model, arguments.upstream)
    if findings:
        for finding in findings:
            print(finding.message)
        return 1
    sha = load_canon_model(arguments.model).source_commit
    print(f"source commit {sha} is on {arguments.upstream} and the canon matches it")
    return 0
