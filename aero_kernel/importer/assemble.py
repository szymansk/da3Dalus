"""Stage 3 of the import: validate the normalised namespace against the canon model (ch. 8.9).

The model types check themselves: vocabularies, structural integrity, references, defaults and the
content hash. A violation is translated into a finding that names the canon file and field.
"""

import re

from aero_kernel.canon.model import CanonModel, Namespace, compute_content_hash
from aero_kernel.errors import DEFAULT_NAMESPACE
from aero_kernel.importer import IMPORTER_VERSION
from aero_kernel.importer.findings import Finding
from pydantic import ValidationError

__all__ = ["assemble"]

_QUALIFIED = re.compile(rf"{DEFAULT_NAMESPACE}:([a-z0-9-]+)")
_VALUE_ERROR = "Value error, "


def _file_of(section: str, slug: str) -> str:
    """Return the canon file a section/slug of the model comes from."""
    return "defaults.yaml" if section == "defaults" else f"{section}/{slug}.md"


def _path(parts: tuple[int | str, ...]) -> str:
    """Render a validation location as ``a.b[0].c``."""
    text = ""
    for part in parts:
        text += f"[{part}]" if isinstance(part, int) else f"{'.' if text else ''}{part}"
    return text


def _translate(error: ValidationError) -> list[Finding]:
    """Turn a validation error of the model into findings with file, field and message."""
    findings: list[Finding] = []
    for entry in error.errors(include_url=False, include_context=False, include_input=False):
        location = entry["loc"]
        message = entry["msg"].removeprefix(_VALUE_ERROR)
        if len(location) >= 2 and location[0] in ("quantities", "formulas", "defaults"):
            findings.append(
                Finding(
                    file=_file_of(str(location[0]), str(location[1])),
                    field=_path(location[2:]) or "entry",
                    message=message,
                )
            )
            continue
        findings.extend(_model_level(message))
    return findings


def _model_level(message: str) -> list[Finding]:
    """Split a model-level message into one finding per problem."""
    findings: list[Finding] = []
    for problem in message.split("; "):
        reference = re.match(rf"{DEFAULT_NAMESPACE}:([a-z0-9-]+): (.*)", problem)
        if reference is not None:
            findings.append(
                Finding(
                    file=_file_of("formulas", reference.group(1)),
                    field="references",
                    message=reference.group(2),
                )
            )
        elif problem.startswith("default of"):
            slug = _QUALIFIED.search(problem)
            findings.append(
                Finding(
                    file="defaults.yaml",
                    field=slug.group(1) if slug else "defaults",
                    message=problem,
                )
            )
        else:
            findings.append(Finding(file="canon model", field="model", message=problem))
    return findings


def assemble(
    namespace: dict[str, object], source_commit: str
) -> tuple[CanonModel | None, list[Finding]]:
    """Validate the normalised calc namespace and build the canon model.

    Args:
        namespace: The result of stage 2.
        source_commit: The 40-hex commit of the canon document.

    Returns:
        The model, or ``None`` with the findings that name why it cannot be built.
    """
    try:
        validated = Namespace.model_validate(namespace)
        content = {DEFAULT_NAMESPACE: validated}
        model = CanonModel.model_validate(
            {
                "schema_version": 1,
                "content_hash": compute_content_hash(content),
                "source_commit": source_commit,
                "importer_version": IMPORTER_VERSION,
                "namespaces": {DEFAULT_NAMESPACE: validated.model_dump(mode="json")},
            }
        )
    except ValidationError as exc:
        return None, _translate(exc)
    return model, []
