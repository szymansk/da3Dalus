"""The source commit of an import: which commit of the canon document a model is imported from.

Inside a git work tree git is always consulted, whether or not the commit is given: the canon
directory must be clean and, for a given commit, identical to it. Outside git the commit must be
given and is taken as it is. A git command that fails is a finding, never a silent pass.
"""

import subprocess
from pathlib import Path

from aero_kernel.importer.findings import Finding

__all__ = ["resolve_source"]

_NOT_A_REPOSITORY = "not a git repository"


def _finding(message: str) -> Finding:
    """Return a finding about the source commit."""
    return Finding(file=".", field="source_commit", message=message)


def _git(canon_dir: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run git in the canon directory; ``None`` if git cannot be started."""
    try:
        return subprocess.run(
            ["git", "-C", str(canon_dir), *args], check=False, capture_output=True, text=True
        )
    except OSError:
        return None


def _has_git_directory(canon_dir: Path) -> bool:
    """Whether the canon directory or a parent holds a ``.git`` entry."""
    return any((parent / ".git").exists() for parent in (canon_dir, *canon_dir.resolve().parents))


def _failed(name: str, done: subprocess.CompletedProcess[str]) -> Finding:
    """Return the finding for a git command that exited unsuccessfully."""
    return _finding(f"git {name} failed (exit {done.returncode}): {done.stderr.strip()}")


def _check_tree(canon_dir: Path, given: str | None) -> tuple[str | None, list[Finding]]:
    """Check a canon inside a work tree; return its commit and the findings."""
    status = _git(canon_dir, "status", "--porcelain", "--", ".")
    if status is None or status.returncode != 0:
        return None, [_failed("status", status) if status else _finding("git is not available")]
    findings: list[Finding] = []
    if status.stdout.strip():
        shown = " | ".join(status.stdout.strip().splitlines()[:5])
        findings.append(
            _finding(f"uncommitted changes under the canon directory (commit them first): {shown}")
        )
    if given is None:
        head = _git(canon_dir, "rev-parse", "HEAD")
        if head is None or head.returncode != 0:
            return None, [
                *findings,
                _failed("rev-parse HEAD", head) if head else _finding("git is not available"),
            ]
        return head.stdout.strip(), findings
    exists = _git(canon_dir, "cat-file", "-e", f"{given}^{{commit}}")
    if exists is None or exists.returncode != 0:
        return given, [*findings, _finding(f"{given} is not a commit of this repository")]
    same = _git(canon_dir, "diff", "--quiet", given, "--", ".")
    if same is None or same.returncode not in (0, 1):
        return given, [
            *findings,
            _failed("diff", same) if same else _finding("git is not available"),
        ]
    if same.returncode == 1:
        findings.append(_finding(f"the canon directory differs from commit {given}"))
    return given, findings


def resolve_source(canon_dir: Path, given: str | None) -> tuple[str | None, list[Finding]]:
    """Resolve and check the commit a canon document is imported from.

    Args:
        canon_dir: The canon document directory.
        given: The ``--source-commit`` value, or ``None``.

    Returns:
        The commit (``None`` if there is none) and the findings; with a finding nothing is written.
    """
    inside = _git(canon_dir, "rev-parse", "--is-inside-work-tree")
    if inside is None:
        if _has_git_directory(canon_dir):
            return given, [_finding("git is not available, but the canon is in a git repository")]
    elif inside.returncode == 0 and inside.stdout.strip() == "true":
        return _check_tree(canon_dir, given)
    elif _NOT_A_REPOSITORY not in inside.stderr:
        return given, [_failed("rev-parse --is-inside-work-tree", inside)]
    if given is None:
        return None, [_finding("the canon is not in a git repository; pass --source-commit <sha>")]
    return given, []
