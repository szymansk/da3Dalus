"""Command line of the importer: ``python -m aero_kernel.importer <canon-dir> [options]``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aero_kernel.canon.load import default_model_path
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.importer.source import resolve_source
from aero_kernel.importer.write import write_outputs

__all__ = ["main"]

MODEL_NAME = "canon_model.json"
REPORT_NAME = "IMPORT_REPORT.md"


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
    commit, source_findings = resolve_source(canon_dir, arguments.source_commit)
    result = import_canon(canon_dir, commit, source_findings=source_findings)
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
