"""Stage 3 of the import: validate the normalised namespace against the canon model (ch. 8.9).

The model types check themselves: vocabularies, names, structural integrity, references, defaults
and the content hash. :func:`findings_of` is the one function that turns a validation error of the
model into findings that name the canon file and field.
"""

import re

from aero_kernel.canon.model import CanonModel, Namespace, compute_content_hash
from aero_kernel.errors import DEFAULT_NAMESPACE, SLUG_REGEX
from aero_kernel.importer import IMPORTER_VERSION
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.yamlvalue import as_list
from pydantic import ValidationError

__all__ = ["assemble", "findings_of"]

_QUALIFIED = re.compile(rf"{DEFAULT_NAMESPACE}:({SLUG_REGEX})")
_REFERENCE_PROBLEM = re.compile(rf"{DEFAULT_NAMESPACE}:({SLUG_REGEX}): (.*)")
_VALUE_ERROR = "Value error, "

# The branches of the model's ``Binding`` union (a slug or a ``{const, source}`` constant), as pydantic
# names them in a location. Of the two reports only the one of the branch that fits the written
# value is kept.
_BINDING_BRANCHES = frozenset({"constrained-str", "ConstBinding"})
_SCALARS = (str, int, float, bool, type(None))
_SHORT = 60  # a written value longer than this is not repeated in a finding


def _file_of(section: str, slug: str) -> str:
    """Return the canon file a section/slug of the model comes from."""
    return "defaults.yaml" if section == "defaults" else f"{section}/{slug}.md"


def _path(parts: tuple[int | str, ...]) -> str:
    """Render a validation location as ``a.b[0].c``."""
    text = ""
    for part in parts:
        text += f"[{part}]" if isinstance(part, int) else f"{'.' if text else ''}{part}"
    return text


def _is_shown(value: object) -> bool:
    """Whether the written value is short enough to be named in a finding."""
    return isinstance(value, _SCALARS) or (
        (items := as_list(value)) is not None and len(repr(items)) <= _SHORT
    )


def _message(kind: str, text: str, context: dict[str, object] | None) -> str:
    """Return the message of a validation error in the importer's words."""
    if kind == "too_short" and context is not None and context.get("min_length") == 1:
        return "must not be empty"
    return text.removeprefix(_VALUE_ERROR)


def _is_other_binding_branch(location: tuple[int | str, ...], value: object) -> bool:
    """Whether an error belongs to the branch of a binding that the written value does not fit.

    A slug is reported by the string branch; a constant by the errors below ``ConstBinding``. The
    ``ConstBinding`` report at the branch itself only says "not a mapping", which the string
    branch already says.
    """
    tags = [index for index, part in enumerate(location) if part in _BINDING_BRANCHES]
    if not tags:
        return False
    index = tags[0]
    if location[index] == "ConstBinding":
        return index == len(location) - 1
    return isinstance(value, dict)


def findings_of(error: ValidationError) -> list[Finding]:
    """Turn a validation error of the canon model into findings with file, field and message.

    A location below ``quantities``, ``formulas`` or ``defaults`` names the entry (a default is
    named by its slug); a rule of the whole model names the entry its message cites. The error of
    a parent whose child is reported is dropped, and of the two branches of a binding only the one
    that fits the written value is kept.

    Args:
        error: The error ``Namespace`` or ``CanonModel`` validation raised.

    Returns:
        One finding per distinct problem.
    """
    entries = error.errors(include_url=False, include_context=True, include_input=True)
    locations = [entry["loc"] for entry in entries]
    findings: list[Finding] = []
    for entry in entries:
        location = entry["loc"]
        if any(other[: len(location)] == location and other != location for other in locations):
            continue  # a child of this location is reported with the real cause
        if _is_other_binding_branch(location, entry["input"]):
            continue
        location = tuple(part for part in location if part not in _BINDING_BRANCHES)
        message = _message(entry["type"], entry["msg"], entry.get("ctx"))
        value = entry["input"]
        if value is None and "bind" in location:
            message = "the input parameter is not bound by the application"
        elif entry["type"] != "missing" and _is_shown(value):
            message = f"{message} (got {value!r})"
        if len(location) >= 2 and location[0] in ("quantities", "formulas", "defaults"):
            slug = str(location[1])
            rest = (slug, *location[2:]) if location[0] == "defaults" else location[2:]
            findings.append(
                Finding(
                    file=_file_of(str(location[0]), slug),
                    field=_path(tuple(rest)) or "entry",
                    message=message,
                )
            )
        elif location:
            findings.append(Finding(file="canon model", field=_path(location), message=message))
        else:
            findings.extend(_model_level(message))
    return list(dict.fromkeys(findings))


def _model_level(message: str) -> list[Finding]:
    """Split a message of a whole-model rule into one finding per problem."""
    findings: list[Finding] = []
    for problem in message.split("; "):
        reference = _REFERENCE_PROBLEM.match(problem)
        if reference is not None:
            findings.append(
                Finding(
                    file=_file_of("formulas", reference.group(1)),
                    field="references",
                    message=reference.group(len(reference.groups())),
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
        return None, findings_of(exc)
    return model, []
