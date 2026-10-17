"""The import pipeline: stages 1 to 3 over a canon directory, producing the texts to write."""

import logging
import re
from collections.abc import Sequence
from pathlib import Path

from aero_kernel.canon.model import CanonModel
from aero_kernel.importer.assemble import assemble
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.normalise import normalise
from aero_kernel.importer.parse import parse_canon
from aero_kernel.importer.report import model_text, report_text
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["ImportResult", "import_canon"]

_COMMIT = re.compile(r"[0-9a-f]{40}")


class ImportResult(BaseModel):
    """The outcome of an import: findings, or the model with the texts of its two outputs.

    Attributes:
        findings: Everything wrong in the canon; empty on success.
        model: The canon model; ``None`` exactly if there is a finding.
        model_json: The text of ``canon_model.json``; ``None`` exactly if there is a finding.
        report: The text of ``IMPORT_REPORT.md``; ``None`` exactly if there is a finding.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: tuple[Finding, ...] = ()
    model: CanonModel | None = None
    model_json: str | None = None
    report: str | None = None


def import_canon(
    canon_dir: Path, source_commit: str | None, *, source_findings: Sequence[Finding] = ()
) -> ImportResult:
    """Run stages 1 to 3 and render the outputs; all or nothing.

    A stage that finds something stops the pipeline after reporting all of its own findings.

    Args:
        canon_dir: The canon document directory.
        source_commit: The 40-hex commit of the canon document; ``None`` if there is none, which
            ``source_findings`` then explains.
        source_findings: Findings about the source commit; they are reported with those of stage 1.

    Returns:
        The result; it holds either findings or the model and the texts to write.
    """
    findings: list[Finding] = list(source_findings)
    if source_commit is not None and _COMMIT.fullmatch(source_commit) is None:
        findings.append(
            Finding(
                file="command line",
                field="source_commit",
                message=f"{source_commit!r} is not a 40-character lower-case hex git commit",
            )
        )
    if source_commit is None and not findings:
        findings.append(
            Finding(file="command line", field="source_commit", message="no source commit given")
        )
    parsed = parse_canon(canon_dir)
    findings.extend(parsed.findings)
    if findings or source_commit is None:
        return ImportResult(findings=tuple(findings))
    namespace, findings = normalise(parsed)
    if findings:
        return ImportResult(findings=tuple(findings))
    model, findings = assemble(namespace, source_commit)
    if model is None:
        return ImportResult(findings=tuple(findings))
    logger.info(
        "canon imported: %d formulas, %d quantities, hash %s",
        len(model.namespaces["calc"].formulas),
        len(model.namespaces["calc"].quantities),
        model.content_hash,
    )
    return ImportResult(model=model, model_json=model_text(model), report=report_text(model))
