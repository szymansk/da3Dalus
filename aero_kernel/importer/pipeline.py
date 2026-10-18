"""The import pipeline: stages 1 to 3 over a canon directory, producing the texts to write."""

import logging
from pathlib import Path

from aero_kernel.canon.model import CanonModel
from aero_kernel.importer.assemble import assemble
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.normalise import normalise
from aero_kernel.importer.parse import parse_canon
from aero_kernel.importer.report import model_text, report_text
from aero_kernel.importer.rules import check_model
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = ["ImportResult", "import_canon"]


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


def import_canon(canon_dir: Path) -> ImportResult:
    """Run stages 1 to 3 and render the outputs; all or nothing.

    A stage that finds something stops the pipeline after reporting all of its own findings.

    Args:
        canon_dir: The canon document directory.

    Returns:
        The result; it holds either findings or the model and the texts to write.
    """
    parsed = parse_canon(canon_dir)
    if parsed.findings:
        return ImportResult(findings=tuple(parsed.findings))
    namespace, findings = normalise(parsed)
    if findings:
        return ImportResult(findings=tuple(findings))
    model, findings = assemble(namespace)
    if model is None:
        return ImportResult(findings=tuple(findings))
    findings = check_model(model)
    if findings:
        return ImportResult(findings=tuple(findings))
    logger.info(
        "canon imported: %d formulas, %d quantities, hash %s",
        len(model.namespaces["calc"].formulas),
        len(model.namespaces["calc"].quantities),
        model.content_hash,
    )
    return ImportResult(model=model, model_json=model_text(model), report=report_text(model))
