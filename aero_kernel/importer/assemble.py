"""Stage 3 of the import: validate the normalised namespace against the canon model (ch. 8.9).

The model types check themselves: vocabularies, names, structural integrity, references, defaults
and the content hash. :func:`findings_of` is the one function that turns a validation error of the
model into findings that name the canon file and field; it reads the structured context of the
whole-model rules and never parses message text.
"""

from aero_kernel.canon.model import (
    BINDING_TAGS,
    CanonModel,
    CanonProblem,
    Namespace,
    compute_content_hash,
)
from aero_kernel.errors import DEFAULT_NAMESPACE
from aero_kernel.importer import IMPORTER_VERSION
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.yamlvalue import as_list
from pydantic import ValidationError
from pydantic_core import ErrorDetails

__all__ = ["assemble", "findings_of"]

_VALUE_ERROR = "Value error, "
_SCALARS = (str, int, float, bool, type(None))
_SHORT = 60  # a written value longer than this is not repeated in a finding
_SECTIONS = ("quantities", "formulas", "defaults")


def _file_of(section: str, slug: str, namespace: str = DEFAULT_NAMESPACE) -> str:
    """Return the canon file a section/slug of the model comes from."""
    if section == "defaults":
        return "defaults.yaml"
    prefix = "" if namespace == DEFAULT_NAMESPACE else f"{namespace}/"
    return f"{prefix}{section}/{slug}.md"


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


def _message(entry: ErrorDetails) -> str:
    """Return the message of a validation error in the importer's words, with the written value."""
    context = entry.get("ctx")
    if entry["type"] == "too_short" and context is not None and context.get("min_length") == 1:
        return "must not be empty"
    message = entry["msg"].removeprefix(_VALUE_ERROR)
    if entry["type"] != "missing" and _is_shown(entry["input"]):
        message = f"{message} (got {entry['input']!r})"
    return message


def _without_binding_tag(location: tuple[int | str, ...]) -> tuple[int | str, ...]:
    """Drop the branch tag the model's ``Binding`` union puts after the parameter name.

    The tag has one fixed place: ``formulas / <slug> / applications / <i> / bind / <parameter> / tag``.
    """
    if (
        len(location) > 6
        and location[0] == "formulas"
        and location[2] == "applications"
        and location[4] == "bind"
        and location[6] in BINDING_TAGS
    ):
        return location[:6] + location[7:]
    return location


def _source_key(entry: ErrorDetails) -> tuple[str, str, str, str, str] | None:
    """Key a fault of a formula's ``inputs``/``outputs``; its merged copies carry the same key."""
    location = entry["loc"]
    if len(location) >= 4 and location[0] == "formulas" and location[2] in ("inputs", "outputs"):
        return (
            str(location[1]),
            str(location[2]),
            str(location[3]),
            entry["type"],
            repr(entry["input"]),
        )
    return None


def _copy_key(
    entry: ErrorDetails, location: tuple[int | str, ...]
) -> tuple[str, str, str, str, str] | None:
    """Key of the formula-level fault an application-level fault would merely repeat."""
    if len(location) >= 6 and location[0] == "formulas" and location[2] == "applications":
        side = {"bind": "inputs", "produce": "outputs"}.get(str(location[4]))
        if side is not None:
            return (str(location[1]), side, str(location[5]), entry["type"], repr(entry["input"]))
    return None


_DEFAULT_SIDE = {"bind": "inputs", "produce": "outputs"}


def _is_merged_copy(problem: CanonProblem, written: set[tuple[str, str, str, str]]) -> bool:
    """Whether an application-level problem merely repeats one of the formula's own defaults."""
    side, parameter = problem["side"], problem["parameter"]
    if side not in _DEFAULT_SIDE or parameter is None:
        return False
    return (problem["slug"], _DEFAULT_SIDE[side], parameter, problem["text"]) in written


def _problem_finding(problem: CanonProblem) -> Finding:
    """Turn one located problem of a whole-model rule into a finding."""
    section, slug = problem["section"], problem["slug"]
    field = slug if section == "defaults" else problem["field"] or "entry"
    return Finding(
        file=_file_of(section, slug, problem["namespace"]), field=field, message=problem["text"]
    )


def _finding(entry: ErrorDetails, location: tuple[int | str, ...]) -> Finding:
    """Turn one validation error into a finding."""
    message = _message(entry)
    if len(location) >= 2 and location[0] in _SECTIONS:
        slug = str(location[1])
        rest = (slug, *location[2:]) if location[0] == "defaults" else location[2:]
        return Finding(
            file=_file_of(str(location[0]), slug),
            field=_path(tuple(rest)) or "entry",
            message=message,
        )
    if location:
        return Finding(file="canon model", field=_path(location), message=message)
    return Finding(file="canon model", field="model", message=message)


def findings_of(error: ValidationError) -> list[Finding]:
    """Turn a validation error of the canon model into findings with file, field and message.

    A location below ``quantities``, ``formulas`` or ``defaults`` names the entry (a default is
    named by its slug). A whole-model rule carries its located problems in the error context. The
    error of a parent whose child is reported is dropped, and so is the copy of a formula-level
    fault that the default merge repeated in an application: one fault, one finding.

    Args:
        error: The error ``Namespace`` or ``CanonModel`` validation raised.

    Returns:
        One finding per problem.
    """
    entries = error.errors(include_url=False, include_context=True, include_input=True)
    locations = [_without_binding_tag(entry["loc"]) for entry in entries]
    sources = {key for entry in entries if (key := _source_key(entry)) is not None}
    findings: list[Finding] = []
    for entry in entries:
        context = entry.get("ctx")
        if entry["type"] == "canon_problems" and context is not None:
            problems: list[CanonProblem] = context["problems"]
            written = {
                (p["slug"], p["side"], p["parameter"], p["text"])
                for p in problems
                if p["side"] in ("inputs", "outputs") and p["parameter"] is not None
            }
            findings.extend(
                _problem_finding(problem)
                for problem in problems
                if not _is_merged_copy(problem, written)
            )
            continue
        location = _without_binding_tag(entry["loc"])
        if any(other[: len(location)] == location and other != location for other in locations):
            continue  # a child of this location is reported with the real cause
        if _copy_key(entry, location) in sources:
            continue
        findings.append(_finding(entry, location))
    return findings


def assemble(namespace: dict[str, object]) -> tuple[CanonModel | None, list[Finding]]:
    """Validate the normalised calc namespace and build the canon model.

    Args:
        namespace: The result of stage 2.

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
                "importer_version": IMPORTER_VERSION,
                "namespaces": {DEFAULT_NAMESPACE: validated.model_dump(mode="json")},
            }
        )
    except ValidationError as exc:
        return None, findings_of(exc)
    return model, []
