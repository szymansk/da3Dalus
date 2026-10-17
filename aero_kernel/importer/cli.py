"""Command line of the importer: ``python -m aero_kernel.importer <canon-dir> [options]``."""

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from aero_kernel.canon.load import default_model_path
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.importer.write import write_outputs

__all__ = ["main"]

MODEL_NAME = "canon_model.json"
REPORT_NAME = "IMPORT_REPORT.md"


def _git(canon_dir: Path, *args: str) -> tuple[int, str]:
    """Run git in the canon directory; return its exit code and trimmed output."""
    try:
        done = subprocess.run(
            ["git", "-C", str(canon_dir), *args], check=False, capture_output=True, text=True
        )
    except OSError:
        return 127, ""
    return done.returncode, done.stdout.strip()


def _source_commit(canon_dir: Path) -> tuple[str, list[Finding]]:
    """Return the git HEAD of the canon, or the findings that say why there is none.

    Uncommitted changes under the canon directory are a finding: the model would claim a commit
    it was not imported from.
    """
    code, head = _git(canon_dir, "rev-parse", "HEAD")
    if code != 0:
        return "", [
            Finding(
                file=".",
                field="source_commit",
                message="the canon is not in a git repository; pass --source-commit <sha>",
            )
        ]
    _, status = _git(canon_dir, "status", "--porcelain", "--", ".")
    if status:
        return "", [
            Finding(
                file=".",
                field="source_commit",
                message="uncommitted changes under the canon directory; commit them or pass "
                f"--source-commit <sha>: {' | '.join(status.splitlines()[:5])}",
            )
        ]
    return head, []


def main(argv: list[str] | None = None) -> int:
    """Import a canon document into the canon model.

    Args:
        argv: Command-line arguments; ``None`` means ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``1`` if there is a finding or the outputs cannot be written.
    """
    parser = argparse.ArgumentParser(
        prog="python -m aero_kernel.importer",
        description="Import the canon document into canon_model.json and IMPORT_REPORT.md.",
    )
    parser.add_argument("canon_dir", type=Path, help="the canon document directory")
    parser.add_argument(
        "--out", type=Path, default=default_model_path().parent, help="output directory"
    )
    parser.add_argument("--source-commit", help="commit of the canon document (default: git HEAD)")
    arguments = parser.parse_args(argv)
    canon_dir: Path = arguments.canon_dir
    commit: str | None = arguments.source_commit
    if commit is None:
        commit, findings = _source_commit(canon_dir)
        if findings:
            return _report(findings)
    result = import_canon(canon_dir, commit)
    if result.model is None or result.model_json is None or result.report is None:
        return _report(result.findings)
    try:
        write_outputs(arguments.out, {MODEL_NAME: result.model_json, REPORT_NAME: result.report})
    except OSError as exc:
        return _report([Finding(file=MODEL_NAME, field="write", message=str(exc))])
    print(f"imported {MODEL_NAME} ({result.model.content_hash}) into {arguments.out}")
    return 0


def _report(findings: Sequence[Finding]) -> int:
    """Print the findings, one per line, and return the failing exit code."""
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s); nothing written", file=sys.stderr)
    return 1
