"""Command line of the importer: ``python -m aero_kernel.importer <canon-dir> [options]``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aero_kernel.canon.load import CanonLoadError, default_model_path, load_canon_model
from aero_kernel.canon.model import CanonModel
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.importer.source import resolve_source
from aero_kernel.importer.write import PartialWriteError, write_outputs

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
    parser.add_argument(
        "--source-commit",
        help="commit of the canon document (default: the last commit that touched it)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; fail on a finding or if the committed model is stale",
    )
    arguments = parser.parse_args(argv)
    canon_dir: Path = arguments.canon_dir
    if arguments.check:
        return _check(canon_dir, arguments.out)
    commit, source_findings = resolve_source(canon_dir, arguments.source_commit)
    result = import_canon(canon_dir, commit, source_findings=source_findings)
    if result.model is None or result.model_json is None or result.report is None:
        return _report(result.findings)
    try:
        write_outputs(arguments.out, {MODEL_NAME: result.model_json, REPORT_NAME: result.report})
    except PartialWriteError as exc:
        print(f"{exc.unwritten[0]}: write: {exc}")
        print(
            f"partly written: {', '.join(exc.written)} was written, "
            f"{', '.join(exc.unwritten)} was not written and still holds the previous import; "
            "run the import again",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        return _report([Finding(file=MODEL_NAME, field="write", message=str(exc))])
    print(f"imported {MODEL_NAME} ({result.model.content_hash}) into {arguments.out}")
    return 0


# The commit of a --check build is never compared, so it needs no git: any well-formed value will do.
_CHECK_COMMIT = "0" * 40


def _differences(committed: CanonModel, fresh: CanonModel) -> list[str]:
    """Name what differs between the committed model and a fresh import; empty if they agree.

    Only the content hash and the two versions are compared. The source commit changes with every
    commit of the canon directory and is not content.
    """
    pairs = (
        ("content_hash", committed.content_hash, fresh.content_hash),
        ("schema_version", committed.schema_version, fresh.schema_version),
        ("importer_version", committed.importer_version, fresh.importer_version),
    )
    return [
        f"{name} committed {old}, {'importer' if name == 'importer_version' else 'canon'} {new}"
        for name, old, new in pairs
        if old != new
    ]


def _check(canon_dir: Path, out: Path) -> int:
    """Run stages 1 to 3 and compare with the committed model; write nothing.

    Returns:
        ``0`` if the committed model is current, ``1`` on a finding or a stale model.
    """
    result = import_canon(canon_dir, _CHECK_COMMIT)
    if result.model is None:
        return _report(result.findings)
    try:
        committed = load_canon_model(out / MODEL_NAME)
    except CanonLoadError as exc:
        print(f"{MODEL_NAME} is stale: it cannot be loaded ({exc})")
        return 1
    differences = _differences(committed, result.model)
    if differences:
        print(
            f"{MODEL_NAME} is stale: {'; '.join(differences)} "
            f"(re-import with python -m aero_kernel.importer {canon_dir})"
        )
        return 1
    print(f"{MODEL_NAME} is current ({committed.content_hash})")
    return 0


def _report(findings: Sequence[Finding]) -> int:
    """Print the findings, one per line, and return the failing exit code."""
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s); nothing written", file=sys.stderr)
    return 1
