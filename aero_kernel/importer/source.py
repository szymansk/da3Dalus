"""The source commit of an import: which commit of the canon document a model is imported from.

Inside a git work tree git is always consulted, whether or not the commit is given: the canon
directory must be clean and, for a given commit, identical to it. Outside git the commit must be
given and is taken as it is. A git command that fails is a finding, never a silent pass.
"""

import os
import re
import subprocess
from pathlib import Path

from aero_kernel.canon.model import SOURCE_COMMIT_REGEX
from aero_kernel.importer.findings import Finding

__all__ = ["commit_format_finding", "resolve_source"]

_COMMIT = re.compile(SOURCE_COMMIT_REGEX)


def commit_format_finding(commit: str) -> Finding | None:
    """Return the finding for a commit that is not 40 lower-case hex digits, or ``None``."""
    if _COMMIT.fullmatch(commit) is not None:
        return None
    return Finding(
        file="command line",
        field="source_commit",
        message=f"{commit!r} is not a 40-character lower-case hex git commit",
    )


def _finding(message: str) -> Finding:
    """Return a finding about the source commit."""
    return Finding(file=".", field="source_commit", message=message)


def _git(canon_dir: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run git in the canon directory; ``None`` if git cannot be started.

    Git runs in the C locale, and nothing here depends on its message text: only on exit codes.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(canon_dir), *args],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "LC_ALL": "C", "LANGUAGE": ""},
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
        detail = "" if exists is None else f" (git cat-file exit {exists.returncode})"
        return given, [*findings, _finding(f"{given} is not a commit of this repository{detail}")]
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

    Whether the canon is in a git work tree is decided by git's exit code and, when git fails, by
    a ``.git`` entry in a parent directory; never by git's message text, which is localised.

    Args:
        canon_dir: The canon document directory.
        given: The ``--source-commit`` value, or ``None``.

    Returns:
        The commit (``None`` if there is none) and the findings; with a finding nothing is written.
    """
    if given is not None and (malformed := commit_format_finding(given)) is not None:
        return None, [malformed]
    inside = _git(canon_dir, "rev-parse", "--is-inside-work-tree")
    in_repository = _has_git_directory(canon_dir)
    if inside is None:
        if in_repository:
            return given, [_finding("git is not available, but the canon is in a git repository")]
    elif inside.returncode == 0:
        if inside.stdout.strip() == "true":
            return _check_tree(canon_dir, given)
        return given, [
            _finding("the canon directory is inside a git directory, not in a work tree")
        ]
    elif in_repository:
        return given, [_failed("rev-parse --is-inside-work-tree", inside)]
    if given is None:
        return None, [_finding("the canon is not in a git repository; pass --source-commit <sha>")]
    return given, []
