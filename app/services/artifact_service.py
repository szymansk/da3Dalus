"""Artifact directory management for construction plan executions.

Each execution gets a dedicated directory:
    <ARTIFACTS_BASE_DIR>/<aeroplane_id>/<plan_id>/<execution_id>/

The execution_id is a UTC timestamp (e.g. "20260425T120630Z").

All path operations validate that the resolved path stays within
ARTIFACTS_BASE_DIR to prevent path traversal attacks.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.schemas.construction_plan import ArtifactDirectory, ArtifactFile

logger = logging.getLogger(__name__)


def _ensure_within_base(path: Path) -> Path:
    """Resolve and verify the path is inside ARTIFACTS_BASE_DIR.

    Raises ValidationError if the resolved path escapes the base directory.
    """
    base = settings.ARTIFACTS_BASE_DIR
    resolved = path.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValidationError(message=f"Path escapes artifacts base: {path}") from exc
    return resolved


def new_execution_id() -> str:
    """Generate a UTC timestamp execution id (e.g. '20260425T120630Z')."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def create_execution_dir(aeroplane_id: str, plan_id: int) -> tuple[str, Path]:
    """Create a fresh artifact directory for an execution.

    Returns (execution_id, absolute_path).
    """
    execution_id = new_execution_id()
    relative = Path(aeroplane_id) / str(plan_id) / execution_id
    abs_path = _ensure_within_base(settings.ARTIFACTS_BASE_DIR / relative)
    abs_path.mkdir(parents=True, exist_ok=True)
    logger.info("Created artifact dir: %s", abs_path)
    return execution_id, abs_path


def list_executions(plan_id: int) -> list[ArtifactDirectory]:
    """List all execution directories for a given plan.

    Walks <ARTIFACTS_BASE_DIR>/<aeroplane>/<plan_id>/<execution_id>.
    """
    base = settings.ARTIFACTS_BASE_DIR
    if not base.exists():
        return []
    try:
        out: list[ArtifactDirectory] = []
        for aero_dir in base.iterdir():
            if not aero_dir.is_dir():
                continue
            plan_dir = aero_dir / str(plan_id)
            if not plan_dir.is_dir():
                continue
            for exec_dir in plan_dir.iterdir():
                if not exec_dir.is_dir():
                    continue
                stat = exec_dir.stat()
                file_count = sum(1 for _ in exec_dir.rglob("*") if _.is_file())
                out.append(
                    ArtifactDirectory(
                        execution_id=exec_dir.name,
                        plan_id=plan_id,
                        aeroplane_id=aero_dir.name,
                        created=datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
                        file_count=file_count,
                    )
                )
        out.sort(key=lambda d: d.execution_id, reverse=True)
        return out
    except OSError as exc:
        logger.exception("Failed to list executions for plan %s", plan_id)
        raise InternalError(message="Cannot read artifact directory") from exc


def list_files(plan_id: int, execution_id: str, subpath: str = "") -> list[ArtifactFile]:
    """List files in an execution's artifact directory (or a subdirectory)."""
    exec_dir = _resolve_execution_dir(plan_id, execution_id)
    if subpath:
        target = exec_dir / subpath
        target = _ensure_within_base(target)
        if not target.is_dir():
            raise NotFoundError(message=f"Directory not found: {subpath}")
        exec_dir = target
    try:
        files: list[ArtifactFile] = []
        for entry in sorted(exec_dir.iterdir()):
            stat = entry.stat()
            files.append(
                ArtifactFile(
                    name=entry.name,
                    is_dir=entry.is_dir(),
                    size_bytes=stat.st_size if entry.is_file() else 0,
                    modified=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                )
            )
        return files
    except OSError as exc:
        logger.exception("Failed to list files in %s", exec_dir)
        raise InternalError(message="Cannot read artifact files") from exc


def get_file_path(plan_id: int, execution_id: str, filename: str) -> Path:
    """Resolve a file path inside an execution dir, with traversal protection."""
    exec_dir = _resolve_execution_dir(plan_id, execution_id)
    candidate = exec_dir / filename
    resolved = _ensure_within_base(candidate)
    # Reject symlinks to prevent indirect escapes
    if candidate.is_symlink():
        raise ValidationError(message=f"Symbolic links are not allowed: {filename}")
    if not resolved.is_file():
        raise NotFoundError(message=f"File not found: {filename}")
    return resolved


def delete_file(plan_id: int, execution_id: str, filename: str) -> None:
    """Delete a file inside an execution dir."""
    path = get_file_path(plan_id, execution_id, filename)
    try:
        path.unlink()
    except OSError as exc:
        logger.exception("Failed to delete artifact file %s", path)
        raise InternalError(message=f"Cannot delete file: {filename}") from exc
    logger.info("Deleted artifact file: %s", path)


def _resolve_execution_dir(plan_id: int, execution_id: str) -> Path:
    """Find and validate the execution directory for plan_id/execution_id."""
    base = settings.ARTIFACTS_BASE_DIR
    if not base.exists():
        raise NotFoundError(message="No artifacts base directory")
    for aero_dir in base.iterdir():
        candidate = aero_dir / str(plan_id) / execution_id
        if candidate.is_dir():
            return _ensure_within_base(candidate)
    raise NotFoundError(message=f"Execution {execution_id} not found for plan {plan_id}")
