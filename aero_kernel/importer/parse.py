"""Stage 1 of the import: read the front matter of every entry and ``defaults.yaml`` (ch. 8.9).

Only the front matter is parsed; the prose below it is never read. This stage checks what can be
checked without knowing the vocabularies: that a file is readable YAML, carries its markers and
required fields of the right container type, names no field the README does not define, and holds
nothing the canon forbids (an ``# ESCALATED:`` comment, a YAML 1.1 boolean, a default inside a
quantity).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.yamlvalue import (
    DuplicateKeyError,
    as_mapping,
    load_unique,
    scan_tokens,
)

__all__ = ["Entry", "ParsedCanon", "parse_canon"]

# Fields the README "Machine-readable fields" defines and the model carries.
FORMULA_CARRIED = frozenset(
    {
        "kind",
        "tool",
        "inputs",
        "outputs",
        "applications",
        "preconditions",
        "postconditions",
        "embeds",
        "variables",
        "optional",
        "uncertainty",
        "worlds",
        "cost",
    }
)
# Fields the README keeps for readers and for approval; the model drops them (ch. 8.9, the
# complete list). Anything else is an unknown field.
FORMULA_DROPPED = frozenset(
    {
        "canon",
        "entry",
        "output",
        "status",
        "shape",
        "tags",
        "tex",
        "source_status",
        "dimensional_check",
    }
)
QUANTITY_CARRIED = frozenset({"symbol", "unit", "role", "type", "positive", "uncertainty"})
QUANTITY_DROPPED = frozenset({"canon", "kind", "status", "tags"})

# Container type of each field: str, mapping or list. Required fields are listed apart.
_FORMULA_SHAPE = {
    "kind": "string",
    "tool": "string",
    "inputs": "mapping",
    "outputs": "mapping",
    "applications": "list",
    "preconditions": "list",
    "postconditions": "list",
    "embeds": "list",
    "variables": "list",
    "optional": "list",
    "uncertainty": "string",
    "worlds": "list",
    "cost": "string",
}
_FORMULA_REQUIRED = ("kind", "tool", "inputs", "outputs")
_QUANTITY_SHAPE = {
    "symbol": "string",
    "role": "string",
    "type": "string",
    "uncertainty": "string",
}
_QUANTITY_REQUIRED = ("symbol", "unit", "role", "type")

_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_ESCALATED = re.compile(r"(?:^|\s)#\s*ESCALATED\b:?(.*)$", re.MULTILINE)
# Plain scalars a YAML 1.1 reader turns into booleans; the canon uses none of them.
_YAML11_BOOLEANS = frozenset({"on", "off", "yes", "no", "y", "n"})


@dataclass(frozen=True)
class Entry:
    """One parsed canon entry.

    Attributes:
        file: Path relative to the canon directory, e.g. ``formulas/stall-speed.md``.
        slug: The entry's ``canon`` slug.
        front: The front matter.
    """

    file: str
    slug: str
    front: dict[str, object]


@dataclass
class ParsedCanon:
    """The result of stage 1.

    Attributes:
        formulas: The formula entries by slug.
        quantities: The quantity entries by slug.
        defaults: The raw ``defaults.yaml`` entries by slug.
        findings: Everything stage 1 found.
    """

    formulas: dict[str, Entry] = field(default_factory=lambda: dict[str, Entry]())
    quantities: dict[str, Entry] = field(default_factory=lambda: dict[str, Entry]())
    defaults: dict[str, dict[str, object]] = field(
        default_factory=lambda: dict[str, dict[str, object]]()
    )
    findings: list[Finding] = field(default_factory=lambda: list[Finding]())


def _one_line(exc: Exception) -> str:
    """Return an exception's text on one line, without a traceback."""
    return " ".join(str(exc).split())


def _shape_problem(value: object, shape: str) -> str | None:
    """Return why ``value`` is not of the container ``shape``, or ``None``."""
    ok = {
        "string": isinstance(value, str),
        "mapping": isinstance(value, dict),
        "list": isinstance(value, list),
    }[shape]
    return None if ok else f"must be a {shape}, not {type(value).__name__}"


def _scan_front_matter(raw: str, file: str, findings: list[Finding]) -> None:
    """Report an ``# ESCALATED:`` comment and a YAML 1.1 boolean in the raw front matter."""
    for match in _ESCALATED.finditer(raw):
        reason = match.group(1).strip()
        findings.append(
            Finding(
                file=file,
                field="ESCALATED",
                message=f"the entry is escalated and undecided ({reason or 'no reason given'}); "
                "the maintainer decides it before it is imported",
            )
        )
    booleans = [
        token.value
        for token in scan_tokens(raw)
        if isinstance(token, yaml.ScalarToken)
        and token.plain
        and token.value.lower() in _YAML11_BOOLEANS
    ]
    if booleans:
        findings.append(
            Finding(
                file=file,
                field="yaml",
                message=f"YAML 1.1 reads {booleans} as booleans; write true or false for a "
                'boolean field, and quote a string such as the newton unit ("N")',
            )
        )


def _read_front(path: Path, file: str, findings: list[Finding]) -> dict[str, object] | None:
    """Read and parse the front matter of one entry, or report why it cannot be."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(
            Finding(file=file, field="front matter", message=f"unreadable: {_one_line(exc)}")
        )
        return None
    match = _FRONT_MATTER.match(text)
    if match is None:
        findings.append(
            Finding(file=file, field="front matter", message="no front matter between '---' lines")
        )
        return None
    raw = match.group(1)
    try:
        parsed: object = load_unique(raw)
    except DuplicateKeyError as exc:
        # The front matter starts on line 2, below the opening '---'.
        findings.append(
            Finding(
                file=file,
                field="front matter",
                message=f"duplicate key {exc.key!r} (line {exc.line + 1})",
            )
        )
        return None
    except yaml.YAMLError as exc:
        findings.append(
            Finding(file=file, field="front matter", message=f"invalid YAML: {_one_line(exc)}")
        )
        return None
    mapping = as_mapping(parsed)
    if mapping is None:
        findings.append(
            Finding(file=file, field="front matter", message="the front matter must be a mapping")
        )
        return None
    _scan_front_matter(raw, file, findings)
    front: dict[str, object] = {}
    for key, value in mapping.items():
        if isinstance(key, str):
            front[key] = value
        else:
            findings.append(
                Finding(file=file, field=str(key), message="a field name must be a string")
            )
    return front


def _check_entry(
    front: dict[str, object],
    file: str,
    *,
    is_formula: bool,
    findings: list[Finding],
) -> None:
    """Check marker, fields and container types of one entry."""
    marker, expected = ("entry", "formula") if is_formula else ("kind", "quantity")
    if front.get(marker) != expected:
        findings.append(
            Finding(
                file=file,
                field=marker,
                message=f"must be {expected!r} (found {front.get(marker)!r})",
            )
        )
    carried, dropped, shape, required = (
        (FORMULA_CARRIED, FORMULA_DROPPED, _FORMULA_SHAPE, _FORMULA_REQUIRED)
        if is_formula
        else (QUANTITY_CARRIED, QUANTITY_DROPPED, _QUANTITY_SHAPE, _QUANTITY_REQUIRED)
    )
    for name, value in front.items():
        if name == "default" and not is_formula:
            findings.append(
                Finding(
                    file=file,
                    field="default",
                    message="a default belongs in defaults.yaml, not in the front matter",
                )
            )
        elif name not in carried and name not in dropped:
            findings.append(
                Finding(
                    file=file,
                    field=name,
                    message="unknown field: the README does not define it",
                )
            )
        elif name in shape and (problem := _shape_problem(value, shape[name])):
            findings.append(Finding(file=file, field=name, message=problem))
    if "positive" in front and front["positive"] is None:
        findings.append(
            Finding(
                file=file,
                field="positive",
                message="must be true; omit the field for a quantity that is not positive",
            )
        )
    for name in required:
        if name not in front:
            findings.append(Finding(file=file, field=name, message="missing, but required"))


def _read_entries(canon_dir: Path, sub: str, parsed: ParsedCanon) -> None:
    """Read every entry of ``formulas`` or ``quantities`` into ``parsed``."""
    is_formula = sub == "formulas"
    target = parsed.formulas if is_formula else parsed.quantities
    directory = canon_dir / sub
    if not directory.is_dir():
        parsed.findings.append(
            Finding(file=sub, field="directory", message=f"{directory} is not a directory")
        )
        return
    for path in sorted(directory.iterdir()):
        file = f"{sub}/{path.name}"
        if path.is_dir() and path.suffix == ".md":
            parsed.findings.append(
                Finding(file=file, field="file", message="is a directory, not an entry file")
            )
            continue
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.suffix != ".md":
            parsed.findings.append(
                Finding(file=file, field="file", message="not a .md entry; rename or remove it")
            )
            continue
        front = _read_front(path, file, parsed.findings)
        if front is None:
            continue
        slug = front.get("canon")
        if not isinstance(slug, str):
            problem = (
                "missing: the entry needs a 'canon:' slug" if slug is None else "must be a string"
            )
            parsed.findings.append(Finding(file=file, field="canon", message=problem))
            # The entry cannot be registered, but its other faults are still reported.
            _check_entry(front, file, is_formula=is_formula, findings=parsed.findings)
            continue
        if slug != path.stem:
            parsed.findings.append(
                Finding(
                    file=file,
                    field="canon",
                    message=f"canon slug {slug!r} differs from the file name {path.stem!r}",
                )
            )
        if slug in target:
            parsed.findings.append(
                Finding(
                    file=file,
                    field="canon",
                    message=f"duplicate canon slug {slug!r}, also in {target[slug].file}",
                )
            )
            continue
        _check_entry(front, file, is_formula=is_formula, findings=parsed.findings)
        target[slug] = Entry(file=file, slug=slug, front=front)


def _keep_default(slug: str, value: object, parsed: ParsedCanon) -> None:
    """Keep one ``defaults.yaml`` entry; the model types check its content."""
    entry = as_mapping(value)
    if entry is None:
        parsed.findings.append(
            Finding(
                file="defaults.yaml",
                field=slug,
                message="must be a mapping {value, unit, basis, source, regime}",
            )
        )
        return
    parsed.defaults[slug] = {str(key): item for key, item in entry.items()}


def _read_defaults(canon_dir: Path, parsed: ParsedCanon) -> None:
    """Read ``defaults.yaml``; an empty file or ``{}`` means no defaults, a missing file is a finding."""
    path = canon_dir / "defaults.yaml"
    file = "defaults.yaml"
    if not path.is_file():
        parsed.findings.append(
            Finding(
                file=file,
                field="document",
                message="missing: an empty file or {} means no defaults",
            )
        )
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        parsed.findings.append(
            Finding(file=file, field="document", message=f"unreadable: {_one_line(exc)}")
        )
        return
    try:
        document: object = load_unique(text)
    except DuplicateKeyError as exc:
        parsed.findings.append(
            Finding(
                file=file,
                field=".".join((*exc.path, str(exc.key))),
                message=f"duplicate key {exc.key!r} (line {exc.line})",
            )
        )
        return
    except yaml.YAMLError as exc:
        parsed.findings.append(
            Finding(file=file, field="document", message=f"invalid YAML: {_one_line(exc)}")
        )
        return
    _scan_front_matter(text, file, parsed.findings)
    if document is None:
        return
    mapping = as_mapping(document)
    if mapping is None:
        parsed.findings.append(
            Finding(file=file, field="document", message="must be a mapping <slug>: {...}")
        )
        return
    for key, value in mapping.items():
        if isinstance(key, str):
            _keep_default(key, value, parsed)
        else:
            parsed.findings.append(
                Finding(file=file, field=str(key), message="a slug must be a string")
            )


def parse_canon(canon_dir: Path) -> ParsedCanon:
    """Run stage 1 over a canon directory.

    Args:
        canon_dir: The canon document directory (``formulas/``, ``quantities/``, ``defaults.yaml``).

    Returns:
        The parsed entries and every stage-1 finding; the entries are only meaningful if there is
        no finding.
    """
    parsed = ParsedCanon()
    if not canon_dir.is_dir():
        parsed.findings.append(
            Finding(file=".", field="canon directory", message=f"{canon_dir} is not a directory")
        )
        return parsed
    _read_entries(canon_dir, "formulas", parsed)
    _read_entries(canon_dir, "quantities", parsed)
    _read_defaults(canon_dir, parsed)
    return parsed
