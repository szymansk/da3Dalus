"""Runtime loader of the canon model (ARCHITECTURE ch. 8.9).

Reads the packaged ``canon_model.json``, the only canon file the kernel touches at runtime; the
canon document is never read here. A model that cannot be loaded is an ``internal`` error that
escalates: the kernel has no canon to compute with.
"""

import json
import logging
from pathlib import Path
from typing import cast, get_args

from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError
from pydantic import JsonValue, ValidationError

logger = logging.getLogger(__name__)

__all__ = ["SUPPORTED_SCHEMA_VERSION", "CanonLoadError", "default_model_path", "load_canon_model"]


def default_model_path() -> Path:
    """Return the path of the packaged canon model, ``canon/canon_model.json``."""
    return Path(__file__).resolve().parent / "canon_model.json"


# The one model shape this build understands; raised on every change of the types.
SUPPORTED_SCHEMA_VERSION: int = get_args(CanonModel.model_fields["schema_version"].annotation)[0]

# How many validation findings go into the error detail.
_MAX_FINDINGS = 10


class CanonLoadError(Exception):
    """The canon model could not be loaded.

    Attributes:
        error: The ``internal`` error describing the failure; it escalates.
    """

    def __init__(self, error: KernelError) -> None:
        """Create the exception.

        Args:
            error: The ``internal`` error describing the failure.
        """
        super().__init__(error.message)
        self.error = error


def _failure(
    reason: str, detail: dict[str, JsonValue] | None = None, cause: BaseException | None = None
) -> CanonLoadError:
    """Build, log and return the load failure.

    No file path enters the message (ADR 0019). The log carries the cause with its traceback and
    the validation findings.
    """
    error = KernelError(
        code=ErrorCategory.INTERNAL.value,
        category=ErrorCategory.INTERNAL,
        message=f"The canon model could not be loaded: {reason}.",
        hint="Re-import the canon with `python -m aero_kernel.importer` or reinstall the "
        "package; report this if it persists.",
        detail=detail or {},
    )
    logger.error(
        "canon model not loaded: %s", reason, exc_info=cause, extra={"findings": detail or {}}
    )
    return CanonLoadError(error)


def _findings(error: ValidationError) -> dict[str, JsonValue]:
    """Summarise a validation error as JSON: the count and the first findings."""
    entries = error.errors(include_url=False, include_context=False, include_input=False)
    return {
        "error_count": len(entries),
        "errors": [
            {"loc": ".".join(str(part) for part in entry["loc"]), "msg": entry["msg"]}
            for entry in entries[:_MAX_FINDINGS]
        ],
    }


def load_canon_model(path: Path | None = None) -> CanonModel:
    """Load and validate the canon model.

    The schema version is checked before the types, so a model of a newer shape reports its
    version instead of a cascade of unknown fields.

    Args:
        path: The model file; ``None`` means the packaged ``canon_model.json``.

    Returns:
        The validated model: types, content hash and every reference checked.

    Raises:
        CanonLoadError: If the file is unreadable, is no JSON object, has an unsupported
            ``schema_version``, or fails validation.
    """
    target = default_model_path() if path is None else path
    try:
        raw: object = json.loads(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise _failure(f"the file cannot be read ({type(exc).__name__})", cause=exc) from exc
    except ValueError as exc:  # json.JSONDecodeError and UnicodeDecodeError
        raise _failure(f"the file is not valid JSON ({type(exc).__name__})", cause=exc) from exc
    except RecursionError as exc:
        raise _failure("the JSON is nested too deeply", cause=exc) from exc
    if not isinstance(raw, dict):
        raise _failure("the file does not hold a JSON object")
    document = cast("dict[str, object]", raw)  # a JSON object always has string keys
    version = document.get("schema_version")
    if type(version) is not int or version != SUPPORTED_SCHEMA_VERSION:
        shown: JsonValue = version if isinstance(version, int | str) else None
        raise _failure(
            f"schema_version {shown!r} is not supported (this build reads "
            f"{SUPPORTED_SCHEMA_VERSION})",
            {"schema_version": shown, "supported": SUPPORTED_SCHEMA_VERSION},
        )
    try:
        model = CanonModel.model_validate(document)
    except ValidationError as exc:
        raise _failure("the model is invalid", _findings(exc), cause=exc) from exc
    logger.info(
        "canon model loaded: %s, source commit %s, importer %s",
        model.content_hash,
        model.source_commit,
        model.importer_version,
    )
    return model
