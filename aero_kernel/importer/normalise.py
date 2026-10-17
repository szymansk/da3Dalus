"""Stage 2 of the import: normalise the parsed entries into the shape of the canon model (ch. 8.9).

Slugs become dict keys, every reference is qualified ``calc:<slug>``, units fold into the closed
set, vocabulary terms are checked against the model's own Literals, applications are resolved
(defaults merged, the implicit one written out as ``default``), cost is declared or derived
(ch. 8.7), embeds are normalised and their closure computed. The result is a plain dict that
stage 3 validates against the model types.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast, get_args

from aero_kernel.canon.model import (
    CostClass,
    FormulaKind,
    OnViolation,
    QuantityRole,
    QuantityType,
    Tool,
    Unit,
    WhenTerm,
)
from aero_kernel.errors import DEFAULT_NAMESPACE, IDENTIFIER_REGEX, SLUG_REGEX, WORLD_NAME_REGEX
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.parse import Entry, ParsedCanon
from aero_kernel.importer.yamlvalue import as_list, as_mapping, is_number, is_text

__all__ = ["normalise"]

# Cost derived from the tool where the canon does not declare it (ch. 8.7); ``minutes`` is only declared.
_DERIVED_COST: dict[str, str] = {
    "APP": "instant",
    "ATM": "instant",
    "GEO": "instant",
    "KAT": "instant",
    "APC": "instant",
    "AB": "seconds",
    "AVL": "seconds",
    "OPT": "seconds",
}

_DIMENSIONLESS_SPELLINGS = ("1", "—")  # the canon writes the not-a-number types with an em dash
_EMBED_ITEM = re.compile(rf"(?P<slug>{SLUG_REGEX})(?:\.(?P<application>{IDENTIFIER_REGEX}))?")

JsonDict = dict[str, object]


class _Sink:
    """Collects the findings of one file."""

    def __init__(self, file: str, findings: list[Finding]) -> None:
        self.file = file
        self.findings = findings
        self.count = 0

    def add(self, field: str, message: str) -> None:
        """Record a finding of this file."""
        self.count += 1
        self.findings.append(Finding(file=self.file, field=field, message=message))


def _qualified(slug: str) -> str:
    """Return the fully qualified reference of a calc slug."""
    return f"{DEFAULT_NAMESPACE}:{slug}"


def _slug(value: object, sink: _Sink, field: str) -> str | None:
    """Return the qualified reference for a quantity slug, or report it."""
    if isinstance(value, str) and re.fullmatch(SLUG_REGEX, value):
        return _qualified(value)
    sink.add(field, f"must be a quantity slug (kebab-case string), not {value!r}")
    return None


def _choice(value: object, vocabulary: Sequence[str], sink: _Sink, field: str) -> str | None:
    """Return ``value`` if it is one of the closed vocabulary, else report it."""
    if isinstance(value, str) and value in vocabulary:
        return value
    sink.add(field, f"{value!r} is not one of {list(vocabulary)}")
    return None


def _unit(value: object, sink: _Sink, field: str) -> str | None:
    """Normalise a unit spelling into the closed set; ``1`` and ``—`` are dimensionless."""
    if isinstance(value, bool):
        sink.add(field, f"unknown unit {value!r}")
        return None
    if value == 1 and isinstance(value, int):
        return "1"
    if isinstance(value, str):
        if value in _DIMENSIONLESS_SPELLINGS:
            return "1"
        if value in get_args(Unit):
            return value
    sink.add(field, f"unknown unit {value!r}; the closed set is {list(get_args(Unit))}")
    return None


def _number(value: object) -> float:
    """Return a YAML number as a float (the model's numbers are strict floats)."""
    return float(cast("float", value))  # callers checked is_number first


def _parameter(name: object, sink: _Sink, field: str) -> str | None:
    """Return a parameter name if it is snake_case, else report it."""
    if isinstance(name, str) and re.fullmatch(WORLD_NAME_REGEX, name):
        return name
    sink.add(field, f"parameter name {name!r} must be snake_case")
    return None


# --- quantities -------------------------------------------------------------------------------


def _quantity(entry: Entry, findings: list[Finding]) -> JsonDict | None:
    """Normalise one quantity entry."""
    sink = _Sink(entry.file, findings)
    front = entry.front
    unit = _unit(front["unit"], sink, "unit")
    role = _choice(front["role"], get_args(QuantityRole), sink, "role")
    type_ = _choice(front["type"], get_args(QuantityType), sink, "type")
    uncertainty = front.get("uncertainty")
    if uncertainty is not None:
        uncertainty = _choice(uncertainty, ("interval",), sink, "uncertainty")
    positive = front.get("positive")
    if "positive" in front and positive is not True:
        sink.add("positive", f"must be true (omit the field otherwise), not {positive!r}")
    if sink.count:
        return None
    return {
        "symbol": front["symbol"],
        "unit": unit,
        "role": role,
        "type": type_,
        "uncertainty": uncertainty,
        "positive": True if positive is True else None,
    }


# --- formulas ---------------------------------------------------------------------------------


def _parameter_map(entry: Entry, name: str, sink: _Sink) -> dict[str, str | None]:
    """Normalise ``inputs`` or ``outputs``: parameter to qualified default slug or ``None``."""
    result: dict[str, str | None] = {}
    for key, value in (as_mapping(entry.front.get(name)) or {}).items():
        parameter = _parameter(key, sink, f"{name}.{key}")
        if parameter is None:
            continue
        result[parameter] = None if value is None else _slug(value, sink, f"{name}.{parameter}")
    return result


def _binding(value: object, sink: _Sink, field: str) -> object | None:
    """Normalise one ``bind`` value: a qualified slug or ``{const, source}``."""
    mapping = as_mapping(value)
    if mapping is None:
        if isinstance(value, str):
            return _slug(value, sink, field)
        sink.add(field, f"must be a quantity slug or {{const, source}}, not {value!r}")
        return None
    problems = 0
    if set(mapping) != {"const", "source"}:
        sink.add(field, "a constant binding has exactly the keys const and source")
        problems += 1
    if "const" in mapping and not is_number(mapping["const"]):
        sink.add(field, f"const must be a number, not {mapping['const']!r}")
        problems += 1
    if "source" in mapping and not is_text(mapping["source"]):
        sink.add(field, "a constant needs a non-empty source (ADR 0028)")
        problems += 1
    if problems:
        return None
    return {"const": _number(mapping["const"]), "source": mapping["source"]}


@dataclass(frozen=True)
class _Interface:
    """The inputs and outputs of a formula, which its applications start from."""

    inputs: dict[str, str | None]
    outputs: dict[str, str | None]


def _overrides(
    item: dict[object, object], key: str, known: dict[str, str | None], label: str, sink: _Sink
) -> dict[str, object]:
    """Read an application's ``bind`` or ``produce`` overrides."""
    result: dict[str, object] = {}
    raw = item.get(key)
    if raw is None:
        return result
    mapping = as_mapping(raw)
    where = f"applications[{label}].{key}"
    if mapping is None:
        sink.add(where, "must be a mapping")
        return result
    side = "input" if key == "bind" else "output"
    for name, value in mapping.items():
        field = f"{where}.{name}"
        if not isinstance(name, str) or name not in known:
            sink.add(field, f"{name!r} is no {side} parameter of the formula")
        elif key == "bind":
            bound = _binding(value, sink, field)
            if bound is not None:
                result[name] = bound
        elif value is None:
            result[name] = None
        else:
            produced = _slug(value, sink, field)
            if produced is not None:
                result[name] = produced
    return result


def _application(item: object, index: int, interface: _Interface, sink: _Sink) -> JsonDict | None:
    """Normalise one application: merge it over the formula's defaults."""
    mapping = as_mapping(item)
    if mapping is None:
        sink.add(f"applications[{index}]", "must be a mapping")
        return None
    identifier = mapping.get("id")
    label = str(identifier) if isinstance(identifier, str) else str(index)
    start = sink.count
    if identifier is None:
        sink.add(f"applications[{index}].id", "missing, but required")
    elif not (isinstance(identifier, str) and re.fullmatch(IDENTIFIER_REGEX, identifier)):
        sink.add(f"applications[{index}].id", f"{identifier!r} is not an identifier")
    for key in mapping:
        if key not in ("id", "bind", "produce", "when", "given"):
            sink.add(f"applications[{label}].{key}", "unknown field")
    bind: dict[str, object] = {
        name: slug for name, slug in interface.inputs.items() if slug is not None
    }
    bind.update(_overrides(mapping, "bind", interface.inputs, label, sink))
    produce: dict[str, object] = {
        name: slug for name, slug in interface.outputs.items() if slug is not None
    }
    produce.update(_overrides(mapping, "produce", interface.outputs, label, sink))
    for name in interface.inputs:
        if name not in bind:
            sink.add("applications", f"application {label}: input parameter {name} is not bound")
    for name in interface.outputs:
        if name not in produce:
            sink.add(
                "applications", f"application {label}: output parameter {name} is not produced"
            )
    when = mapping.get("when")
    if when is not None:
        when = _choice(when, get_args(WhenTerm), sink, f"applications[{label}].when")
    given = _given(mapping.get("given"), label, sink)
    if sink.count != start:
        return None
    return {"id": identifier, "bind": bind, "produce": produce, "when": when, "given": given}


def _given(raw: object, label: str, sink: _Sink) -> list[str] | None:
    """Normalise an application's ``given`` list; absent means always."""
    if raw is None:
        return None
    items = as_list(raw)
    where = f"applications[{label}].given"
    if items is None or not items:
        sink.add(where, "must be a non-empty list of quantity slugs")
        return None
    slugs = [_slug(value, sink, where) for value in items]
    return [slug for slug in slugs if slug is not None]


def _applications(entry: Entry, interface: _Interface, sink: _Sink) -> list[JsonDict]:
    """Normalise the applications; an entry without any has the implicit ``default`` one."""
    raw = entry.front.get("applications")
    items = [{"id": "default"}] if raw is None else (as_list(raw) or [])
    result: list[JsonDict] = []
    for index, item in enumerate(items):
        application = _application(item, index, interface, sink)
        if application is not None:
            result.append(application)
    return result


def _checks(entry: Entry, name: str, sink: _Sink) -> list[JsonDict]:
    """Normalise ``preconditions`` or ``postconditions``."""
    result: list[JsonDict] = []
    for index, item in enumerate(as_list(entry.front.get(name)) or []):
        mapping = as_mapping(item)
        if mapping is None:
            sink.add(f"{name}[{index}]", "must be a mapping")
            continue
        identifier = mapping.get("id")
        label = identifier if isinstance(identifier, str) else str(index)
        where = f"{name}[{label}]"
        start = sink.count
        if identifier is None:
            sink.add(f"{name}[{index}].id", "missing, but required")
        elif not (isinstance(identifier, str) and re.fullmatch(IDENTIFIER_REGEX, identifier)):
            sink.add(f"{name}[{index}].id", f"{identifier!r} is not an identifier")
        for key in mapping:
            if key not in ("id", "parameter", "on_violation", "applications"):
                sink.add(f"{where}.{key}", "unknown field")
        parameter = _parameter(mapping.get("parameter"), sink, f"{where}.parameter")
        violation = _choice(
            mapping.get("on_violation"), get_args(OnViolation), sink, f"{where}.on_violation"
        )
        applications = _application_ids(mapping.get("applications"), f"{where}.applications", sink)
        if sink.count == start:
            result.append(
                {
                    "id": identifier,
                    "parameter": parameter,
                    "on_violation": violation,
                    "applications": applications,
                }
            )
    return result


def _application_ids(raw: object, field: str, sink: _Sink) -> list[str] | None:
    """Normalise a check's ``applications`` list; absent means all of them."""
    if raw is None:
        return None
    items = as_list(raw)
    if items is None or not items:
        sink.add(field, "must be a non-empty list of application ids")
        return None
    ids = [i for i in items if isinstance(i, str) and re.fullmatch(IDENTIFIER_REGEX, i)]
    if len(ids) != len(items):
        sink.add(field, f"every item must be an application id, got {items!r}")
    return ids


def _name_list(entry: Entry, name: str, pattern: str, kind: str, sink: _Sink) -> list[str]:
    """Normalise a list of snake_case names (``optional``, ``worlds``)."""
    result: list[str] = []
    for index, value in enumerate(as_list(entry.front.get(name)) or []):
        if isinstance(value, str) and re.fullmatch(pattern, value):
            result.append(value)
        else:
            sink.add(f"{name}[{index}]", f"{value!r} is not a {kind}")
    return result


@dataclass(frozen=True)
class _Formula:
    """A formula after pass 1: its model dict and the embeds still to resolve."""

    file: str
    doc: JsonDict
    embeds: list[object]
    application_ids: list[str]


def _formula(entry: Entry, findings: list[Finding]) -> _Formula | None:
    """Normalise one formula entry (pass 1: everything except embeds)."""
    sink = _Sink(entry.file, findings)
    front = entry.front
    kind = _choice(front["kind"], get_args(FormulaKind), sink, "kind")
    tool = _choice(front["tool"], get_args(Tool), sink, "tool")
    interface = _Interface(
        inputs=_parameter_map(entry, "inputs", sink), outputs=_parameter_map(entry, "outputs", sink)
    )
    declared = front.get("cost")
    cost = _choice(declared, get_args(CostClass), sink, "cost") if declared is not None else None
    if declared is None and tool is not None:
        cost = _DERIVED_COST[tool]
    uncertainty = front.get("uncertainty")
    if uncertainty is not None:
        uncertainty = _choice(uncertainty, ("interval",), sink, "uncertainty")
    variables = [
        _slug(value, sink, f"variables[{index}]")
        for index, value in enumerate(as_list(front.get("variables")) or [])
    ]
    applications = _applications(entry, interface, sink)
    doc: JsonDict = {
        "kind": kind,
        "tool": tool,
        "cost": cost,
        "inputs": interface.inputs,
        "outputs": interface.outputs,
        "optional": _name_list(entry, "optional", WORLD_NAME_REGEX, "snake_case parameter", sink),
        "applications": applications,
        "preconditions": _checks(entry, "preconditions", sink),
        "postconditions": _checks(entry, "postconditions", sink),
        "uncertainty": uncertainty,
        "worlds": _name_list(entry, "worlds", WORLD_NAME_REGEX, "snake_case world name", sink),
        "variables": [slug for slug in variables if slug is not None],
    }
    if sink.count:
        return None
    ids = [str(application["id"]) for application in applications]
    return _Formula(entry.file, doc, as_list(front.get("embeds")) or [], ids)


# --- embeds -----------------------------------------------------------------------------------


def _resolve_embed(
    item: object, formulas: dict[str, _Formula], parsed: ParsedCanon, sink: _Sink
) -> str | None:
    """Normalise one embeds item to ``calc:<slug>.<application-id>``."""
    match = _EMBED_ITEM.fullmatch(item) if isinstance(item, str) else None
    if match is None:
        sink.add("embeds", f"{item!r} is not <slug> or <slug>.<application-id>")
        return None
    slug, application = match.group("slug"), match.group("application")
    target = formulas.get(slug)
    if target is None:
        if slug not in parsed.formulas:  # a formula that failed pass 1 has its own finding
            sink.add("embeds", f"embeds {item}, but there is no formula {slug}")
        return None
    if application is None:
        if len(target.application_ids) != 1:
            sink.add(
                "embeds",
                f"embeds {item}, but the formula has several applications "
                f"({', '.join(target.application_ids)}); name one as {slug}.<application-id>",
            )
            return None
        application = target.application_ids[0]
    elif application not in target.application_ids:
        sink.add("embeds", f"embeds {item}, but {slug} has no application {application}")
        return None
    return f"{_qualified(slug)}.{application}"


def _closure(
    slug: str, direct: dict[str, list[str]], visiting: frozenset[str] = frozenset()
) -> set[str]:
    """Return every embed reachable from a formula through ``embeds``, direct ones included."""
    reached: set[str] = set()
    for item in direct.get(slug, []):
        reached.add(item)
        target = item.removeprefix(f"{DEFAULT_NAMESPACE}:").rpartition(".")[0]
        if target not in visiting and target != slug:
            reached |= _closure(target, direct, visiting | {slug})
    return reached


def normalise(parsed: ParsedCanon) -> tuple[JsonDict, list[Finding]]:
    """Run stage 2 over parsed entries.

    Args:
        parsed: The result of stage 1, without findings.

    Returns:
        The calc namespace as a plain dict (``quantities``, ``formulas``, ``defaults``) and every
        stage-2 finding; the dict is only meaningful if there is no finding.
    """
    findings: list[Finding] = []
    quantities: dict[str, object] = {}
    for slug, entry in parsed.quantities.items():
        quantity = _quantity(entry, findings)
        if quantity is not None:
            quantities[slug] = quantity
    formulas: dict[str, _Formula] = {}
    for slug, entry in parsed.formulas.items():
        formula = _formula(entry, findings)
        if formula is not None:
            formulas[slug] = formula
    direct: dict[str, list[str]] = {}
    for slug, formula in formulas.items():
        sink = _Sink(formula.file, findings)
        resolved = [_resolve_embed(item, formulas, parsed, sink) for item in formula.embeds]
        direct[slug] = [item for item in resolved if item is not None]
    documents: dict[str, object] = {}
    for slug, formula in formulas.items():
        closure = sorted(_closure(slug, direct)) if direct[slug] else []
        documents[slug] = {**formula.doc, "embeds": direct[slug], "embeds_closure": closure}
    defaults: dict[str, object] = {}
    for slug, raw in parsed.defaults.items():
        sink = _Sink("defaults.yaml", findings)
        unit = _unit(raw.get("unit"), sink, f"{slug}.unit")
        if sink.count == 0 and unit is not None:
            defaults[slug] = {
                "value": _number(raw["value"]),
                "unit": unit,
                "source": raw["source"],
                "regime": raw["regime"],
            }
    return {"quantities": quantities, "formulas": documents, "defaults": defaults}, findings
