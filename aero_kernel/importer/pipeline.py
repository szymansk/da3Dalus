"""The import pipeline: stages 1 to 3 over a canon directory, producing the texts to write."""

import logging
from pathlib import Path

from aero_kernel.canon.model import CanonModel
from aero_kernel.importer.approval import derive_approval
from aero_kernel.importer.assemble import assemble
from aero_kernel.importer.data_sources import (
    Catalogue,
    check_data_sources,
    find_repo_root,
    load_catalogue,
)
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


def _status(front: dict[str, object]) -> str:
    """Return a formula entry's own ``status`` (stage 1 of the approval)."""
    status = front.get("status")
    return status if isinstance(status, str) else "draft"


def import_canon(canon_dir: Path, repo_root: Path | None = None) -> ImportResult:
    """Run stages 1 to 3 and render the outputs; all or nothing.

    A stage that finds something stops the pipeline after reporting all of its own findings.

    Args:
        canon_dir: The canon document directory.
        repo_root: The repository the ``data:`` locations are checked against; ``None`` finds the
            repository above the canon directory, and without one only defaults are checked.

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
    root = repo_root if repo_root is not None else find_repo_root(canon_dir)
    findings.extend(
        check_data_sources(model, Catalogue() if root is None else load_catalogue(root))
    )
    if findings:
        return ImportResult(findings=tuple(findings))
    logger.info(
        "canon imported: %d formulas, %d quantities, hash %s",
        len(model.namespaces["calc"].formulas),
        len(model.namespaces["calc"].quantities),
        model.content_hash,
    )
    stage1 = {slug: _status(entry.front) for slug, entry in parsed.formulas.items()}
    return ImportResult(
        model=model,
        model_json=model_text(model),
        report=report_text(model, derive_approval(model, stage1)),
    )
