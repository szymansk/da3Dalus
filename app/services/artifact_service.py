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


_last_execution_id: str | None = None
_last_execution_id_suffix: int = 0


def new_execution_id() -> str:
    """Generate a UTC timestamp execution id (e.g. '20260425T120630Z').

    Within the same process, consecutive calls in the same UTC second
    return distinct ids by appending a numeric suffix
    (e.g. '20260425T120630Z-1'). This guarantees that callers which
    treat the id as a unique handle never collide.
    """
    global _last_execution_id, _last_execution_id_suffix
    base_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if base_id == _last_execution_id:
        _last_execution_id_suffix += 1
        return f"{base_id}-{_last_execution_id_suffix}"
    _last_execution_id = base_id
    _last_execution_id_suffix = 0
    return base_id


def create_execution_dir(aeroplane_id: str, plan_id: int) -> tuple[str, Path]:
    """Create a fresh artifact directory for an execution.

    Returns (execution_id, absolute_path).
    """
    execution_id = new_execution_id()
    relative = Path(aeroplane_id) / str(plan_id) / execution_id
    abs_path = _ensure_within_base(settings.ARTIFACTS_BASE_DIR / relative)
    try:
        abs_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception("Failed to create artifact dir %s", abs_path)
        raise InternalError(message=f"Cannot create artifact directory: {exc}") from exc
    logger.info("Created artifact dir: %s", abs_path)
    return execution_id, abs_path


TEMPLATE_RUNS_PREFIX = "_template_runs"


def create_template_execution_dir(template_id: int) -> tuple[str, Path]:
    """Create a fresh artifact directory for a template execution.

    Wipes any previous execution under <base>/_template_runs/<template_id>/
    so at most one template execution exists per template at any time.
    Returns (execution_id, absolute_path).
    """
    import shutil

    base = settings.ARTIFACTS_BASE_DIR
    template_root = base / TEMPLATE_RUNS_PREFIX / str(template_id)
    if template_root.exists():
        # Validate containment before destructive operation.
        _ensure_within_base(template_root)
        try:
            shutil.rmtree(template_root)
        except OSError as exc:
            logger.exception("Failed to wipe template run dir %s", template_root)
            raise InternalError(message=f"Cannot reset template run directory: {exc}") from exc

    execution_id = new_execution_id()
    abs_path = base / TEMPLATE_RUNS_PREFIX / str(template_id) / execution_id
    try:
        abs_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception("Failed to create template artifact dir %s", abs_path)
        raise InternalError(message=f"Cannot create template artifact directory: {exc}") from exc
    abs_path = _ensure_within_base(abs_path)
    logger.info("Created template artifact dir: %s", abs_path)
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


def _to_artifact_file(entry: Path, name: str) -> ArtifactFile:
    """Build an ArtifactFile from a filesystem entry."""
    stat = entry.stat()
    is_dir = entry.is_dir()
    return ArtifactFile(
        name=name,
        is_dir=is_dir,
        size_bytes=stat.st_size if not is_dir else 0,
        modified=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    )


def list_files(
    plan_id: int,
    execution_id: str,
    subpath: str = "",
    recursive: bool = False,
) -> list[ArtifactFile]:
    """List files in an execution's artifact directory.

    With ``recursive=True``, returns a flat list of all files under the
    execution directory (or under ``subpath``) with relative paths in the
    ``name`` field — directories are omitted. Without it, returns only
    immediate children (files and subdirectories), matching the original
    breadcrumb-browser behaviour.
    """
    exec_dir = _resolve_execution_dir(plan_id, execution_id)
    if subpath:
        target = exec_dir / subpath
        target = _ensure_within_base(target)
        if not target.is_dir():
            raise NotFoundError(message=f"Directory not found: {subpath}")
        exec_dir = target
    try:
        if recursive:
            return [
                _to_artifact_file(entry, entry.relative_to(exec_dir).as_posix())
                for entry in sorted(exec_dir.rglob("*"))
                if entry.is_file()
            ]
        return [_to_artifact_file(entry, entry.name) for entry in sorted(exec_dir.iterdir())]
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


def delete_execution(plan_id: int, execution_id: str) -> None:
    """Delete an entire execution directory and all its contents."""
    import shutil

    exec_dir = _resolve_execution_dir(plan_id, execution_id)
    try:
        shutil.rmtree(exec_dir)
    except OSError as exc:
        logger.exception("Failed to delete execution dir %s", exec_dir)
        raise InternalError(message=f"Cannot delete execution: {execution_id}") from exc
    logger.info("Deleted execution dir: %s", exec_dir)


def zip_execution(plan_id: int, execution_id: str) -> Path:
    """Zip an entire execution directory and return the path to the zip file.

    The zip is written to a temp file (auto-cleaned by the OS / next
    template run). Empty executions yield a valid empty zip (200 OK
    semantics, not a 404).
    """
    import os as _os
    import tempfile
    import zipfile

    exec_dir = _resolve_execution_dir(plan_id, execution_id)

    fd, tmp_name = tempfile.mkstemp(prefix=f"plan{plan_id}-{execution_id}-", suffix=".zip")
    _os.close(fd)  # we re-open via zipfile
    zip_path = Path(tmp_name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(exec_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                arcname = file_path.relative_to(exec_dir).as_posix()
                zf.write(file_path, arcname=arcname)
    except OSError as exc:
        # Log the validated exec_dir path (sanitised by _ensure_within_base),
        # not the raw user-supplied execution_id, to avoid log injection
        # (pythonsecurity:S5145).
        logger.exception("Failed to build zip for execution at %s", exec_dir)
        zip_path.unlink(missing_ok=True)
        raise InternalError(message=f"Cannot build zip: {exc}") from exc

    return zip_path


def _resolve_execution_dir(plan_id: int, execution_id: str) -> Path:
    """Find and validate the execution directory for plan_id/execution_id.

    Searches first under <base>/<aero_id>/<plan_id>/<exec_id> (plan
    executions). If not found, falls back to
    <base>/_template_runs/<plan_id>/<exec_id> (template executions).
    """
    base = settings.ARTIFACTS_BASE_DIR
    if not base.exists():
        raise NotFoundError(message="No artifacts base directory")

    # 1) Search per-aeroplane plan execution dirs (skip the template-runs
    #    prefix so a template exec_id is not coincidentally returned as
    #    a plan dir).
    for aero_dir in base.iterdir():
        if not aero_dir.is_dir() or aero_dir.name == TEMPLATE_RUNS_PREFIX:
            continue
        candidate = aero_dir / str(plan_id) / execution_id
        if candidate.is_dir():
            return _ensure_within_base(candidate)

    # 2) Fall back to template runs.
    tpl_candidate = base / TEMPLATE_RUNS_PREFIX / str(plan_id) / execution_id
    if tpl_candidate.is_dir():
        return _ensure_within_base(tpl_candidate)

    raise NotFoundError(message=f"Execution {execution_id} not found for plan {plan_id}")
