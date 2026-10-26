"""Stage 2 of the import: normalise the parsed entries into the shape of the canon model (ch. 8.9).

Only what the model cannot do for itself happens here: the unit spellings
``1`` and ``—`` fold into ``1``, the cost is derived from the tool, every reference is qualified
``calc:<slug>``, the defaults of ``bind`` and ``produce`` are merged into every application (the
implicit one is written out as ``default``), embeds are resolved and their closure computed.
Everything else passes through raw: the model types report a wrong vocabulary term, a malformed name
or a missing source, and ``assemble`` turns that report into ``file: field: message`` (one home per
rule, ch. 8.6).
"""

import re
from collections.abc import Callable
from typing import cast

from aero_kernel.canon.model import CostClass
from aero_kernel.canon.taxonomy import Tool
from aero_kernel.errors import DEFAULT_NAMESPACE, IDENTIFIER_REGEX, SLUG_REGEX
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.parse import Entry, ParsedCanon
from aero_kernel.importer.yamlvalue import as_list, as_mapping

__all__ = ["DERIVED_COST", "QUANTITY_TAG_FAMILIES", "normalise"]

# The tag families a quantity carries as fields; a formula carries ``direction``.
QUANTITY_TAG_FAMILIES = ("module", "point", "stage", "group", "discipline")

# Cost derived from the tool where the canon does not declare it (ch. 8.7); ``minutes`` is only declared.
DERIVED_COST: dict[Tool, CostClass] = {
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


def _qualified(value: object) -> object:
    """Qualify a slug as ``calc:<slug>``; any other value stays for the model to reject."""
    return f"{DEFAULT_NAMESPACE}:{value}" if isinstance(value, str) else value


def _unit(value: object) -> object:
    """Fold the dimensionless spellings ``1`` and ``—`` into ``"1"``; any other value stays."""
    if isinstance(value, int) and not isinstance(value, bool) and value == 1:
        return "1"
    if value in _DIMENSIONLESS_SPELLINGS:
        return "1"
    return value


def _qualified_map(raw: object) -> dict[object, object]:
    """Qualify the slug of every value of a parameter mapping; ``None`` (bound per application) stays."""
    return {key: _qualified(value) for key, value in (as_mapping(raw) or {}).items()}


def _qualified_list(raw: object) -> object:
    """Qualify every slug of a list."""
    items = as_list(raw)
    return raw if items is None else [_qualified(item) for item in items]


# --- quantities and defaults ------------------------------------------------------------------


def _tag_values(entry: Entry, family: str, findings: list[Finding]) -> list[str]:
    """Return the values of the entry's ``<family>/<value>`` tags; more than one is a finding."""
    prefix = f"{family}/"
    values = [
        tag.removeprefix(prefix)
        for tag in as_list(entry.front.get("tags")) or []
        if isinstance(tag, str) and tag.startswith(prefix)
    ]
    if len(values) > 1:
        findings.append(
            Finding(
                file=entry.file,
                field=family,
                message=f"more than one {family} tag ({', '.join(values)}): exactly one is allowed",
            )
        )
    return values


def _quantity(entry: Entry, findings: list[Finding]) -> JsonDict:
    """Normalise one quantity entry: the unit folds, the tags become fields, the rest is as written."""
    document: JsonDict = {
        name: _unit(value) if name == "unit" else value
        for name, value in entry.front.items()
        if name
        in (
            "symbol",
            "unit",
            "role",
            "type",
            "uncertainty",
            "positive",
            "at_most",
            "checks",
        )
    }
    if "data" in entry.front:
        raw = entry.front["data"]
        document["data"] = as_list(raw) or [raw]
    if "consistency" in entry.front:
        raw = entry.front["consistency"]
        document["consistency"] = as_list(raw) or [raw]
    for family in QUANTITY_TAG_FAMILIES:
        values = _tag_values(entry, family, findings)
        if values:
            document[family] = values[0]
    return document


def _default(raw: dict[str, object]) -> JsonDict:
    """Normalise one ``defaults.yaml`` entry: the unit folds, the rest is carried as written."""
    return {name: _unit(value) if name == "unit" else value for name, value in raw.items()}


def _rule(raw: dict[str, object]) -> JsonDict:
    """Normalise one ``rules.yaml`` entry: the unit of each parameter folds, the rest is carried."""
    document: JsonDict = dict(raw)
    parameters = as_mapping(raw.get("parameters"))
    if parameters is not None:
        document["parameters"] = {
            str(name): _parameter(parameter) for name, parameter in parameters.items()
        }
    return document


def _parameter(raw: object) -> object:
    """Normalise one rule parameter; anything that is not a mapping is left for the model to refuse."""
    mapping = as_mapping(raw)
    if mapping is None:
        return raw
    return {str(name): _unit(value) if name == "unit" else value for name, value in mapping.items()}


# --- formulas ---------------------------------------------------------------------------------


def _binding(raw: object) -> object:
    """Normalise one ``bind`` value: a slug is qualified, a constant is carried as written."""
    mapping = as_mapping(raw)
    if mapping is None:
        return _qualified(raw)
    return dict(mapping)


def _merged(defaults: object, overrides: object, convert: Callable[[object], object]) -> object:
    """Merge an application's ``bind`` or ``produce`` over the formula's defaults.

    A raw override that is no mapping is returned as it is, for the model to reject.
    """
    defaults_map = as_mapping(defaults)
    merged: dict[object, object] = {} if defaults_map is None else dict(defaults_map)
    if overrides is None:
        return merged
    overrides_map = as_mapping(overrides)
    if overrides_map is None:
        return overrides
    for key, value in overrides_map.items():
        merged[key] = convert(value)
    return merged


def _non_null(parameters: object) -> dict[object, object]:
    """Return the parameters that have a default quantity; the others are bound per application."""
    return {
        key: value for key, value in (as_mapping(parameters) or {}).items() if value is not None
    }


def _application(item: object, inputs: object, outputs: object) -> object:
    """Merge one application over the formula's defaults; the model rejects what does not fit."""
    mapping = as_mapping(item)
    if mapping is None:
        return item
    return {
        **mapping,
        "bind": _merged(_non_null(inputs), mapping.get("bind"), _binding),
        "produce": _merged(_non_null(outputs), mapping.get("produce"), _qualified),
        **({"given": _qualified_list(mapping["given"])} if "given" in mapping else {}),
    }


def _applications(
    entry: Entry, inputs: object, outputs: object, findings: list[Finding]
) -> tuple[list[object], list[str] | None]:
    """Return the merged applications and their ids; the ids are ``None`` if they cannot be read.

    An entry without ``applications`` has the implicit ``default``. Embed resolution needs every
    application to be a mapping with a string ``id``; that is checked here, the rest by the model.
    """
    raw = entry.front.get("applications")
    # Stage 1 guarantees that a present ``applications`` is a list.
    items = [{"id": "default"}] if raw is None else cast("list[object]", raw)
    if not items:
        findings.append(
            Finding(
                file=entry.file,
                field="applications",
                message="must not be empty; omit the field for the implicit application",
            )
        )
        return [], None
    ids: list[str] | None = []
    for index, item in enumerate(items):
        mapping = as_mapping(item)
        identifier = None if mapping is None else mapping.get("id")
        problem = (
            "must be a mapping"
            if mapping is None
            else "missing, but required"
            if identifier is None
            else None
            if isinstance(identifier, str)
            else "must be a string"
        )
        if problem is not None:
            field = f"applications[{index}]" + ("" if mapping is None else ".id")
            findings.append(Finding(file=entry.file, field=field, message=problem))
            ids = None
        elif ids is not None:
            ids.append(str(identifier))
    return [_application(item, inputs, outputs) for item in items], ids


def _default_direction(taxonomy: dict[str, object] | None) -> str | None:
    """Return the id of the default direction of the raw taxonomy, if it names one."""
    for item in as_list((taxonomy or {}).get("directions")) or []:
        mapping = as_mapping(item)
        if mapping is not None and mapping.get("default") is True:
            identifier = mapping.get("id")
            return identifier if isinstance(identifier, str) else None
    return None


def _formula(
    entry: Entry, default_direction: str | None, findings: list[Finding]
) -> tuple[JsonDict, list[object], list[str] | None]:
    """Normalise one formula entry except for its embeds; return it with its raw embeds items."""
    front = entry.front
    tool = front["tool"]
    inputs = _qualified_map(front["inputs"])
    outputs = _qualified_map(front["outputs"])
    applications, ids = _applications(entry, inputs, outputs, findings)
    doc: JsonDict = {
        "kind": front["kind"],
        "tool": tool,
        "inputs": inputs,
        "outputs": outputs,
        "applications": applications,
    }
    direction = _tag_values(entry, "direction", findings)
    if direction or default_direction is not None:
        doc["direction"] = direction[0] if direction else default_direction
    if "cost" in front:
        doc["cost"] = front["cost"]
    elif isinstance(tool, str) and tool in DERIVED_COST:
        doc["cost"] = DERIVED_COST[tool]
    for name in ("preconditions", "postconditions", "optional", "uncertainty", "worlds"):
        if name in front:
            doc[name] = front[name]
    if "variables" in front:
        doc["variables"] = _qualified_list(front["variables"])
    return doc, as_list(front.get("embeds")) or [], ids


# --- embeds -----------------------------------------------------------------------------------


def _resolve_embed(
    item: object, applications_of: dict[str, list[str] | None]
) -> tuple[str | None, str | None]:
    """Normalise one embeds item to ``calc:<slug>.<application-id>``; return it or why not.

    An embed of a formula whose applications cannot be read returns neither: that formula has its
    own finding, and a second one about the embed would only be a cascade.
    """
    match = _EMBED_ITEM.fullmatch(item) if isinstance(item, str) else None
    if match is None:
        return None, f"{item!r} is not <slug> or <slug>.<application-id>"
    slug, application = match.group("slug"), match.group("application")
    if slug not in applications_of:
        return None, f"embeds {item}, but there is no formula {slug}"
    applications = applications_of[slug]
    if applications is None:
        return None, None
    if application is None:
        if len(applications) != 1:
            return None, (
                f"embeds {item}, but the formula has several applications "
                f"({', '.join(applications)}); name one as {slug}.<application-id>"
            )
        application = applications[0]
    elif application not in applications:
        return None, f"embeds {item}, but {slug} has no application {application}"
    return f"{DEFAULT_NAMESPACE}:{slug}.{application}", None


def _closure(slug: str, direct: dict[str, list[str]]) -> set[str]:
    """Return every embed reachable from a formula through ``embeds``, direct ones included.

    Each formula is expanded once, so a chain of diamonds costs linear time, and a cycle (a
    finding of checkpoint (b)) still ends: the closure of a cycle holds its members.
    """
    reached: set[str] = set()
    expanded = {slug}
    pending = [slug]
    while pending:
        for item in direct.get(pending.pop(), []):
            reached.add(item)
            target = item.removeprefix(f"{DEFAULT_NAMESPACE}:").rpartition(".")[0]
            if target not in expanded:
                expanded.add(target)
                pending.append(target)
    return reached


def normalise(parsed: ParsedCanon) -> tuple[JsonDict, list[Finding]]:
    """Run stage 2 over parsed entries.

    Args:
        parsed: The result of stage 1, without findings.

    Returns:
        The calc namespace as a plain dict (``quantities``, ``formulas``, ``defaults``) and the
        findings about embeds; the dict is only meaningful if there is no finding.
    """
    findings: list[Finding] = []
    applications_of: dict[str, list[str] | None] = {}
    documents: dict[str, JsonDict] = {}
    raw_embeds: dict[str, list[object]] = {}
    default_direction = _default_direction(parsed.taxonomy)
    for slug, entry in parsed.formulas.items():
        documents[slug], raw_embeds[slug], applications_of[slug] = _formula(
            entry, default_direction, findings
        )
    direct: dict[str, list[str]] = {}
    for slug, items in raw_embeds.items():
        direct[slug] = []
        for item in items:
            resolved, problem = _resolve_embed(item, applications_of)
            if problem is not None:
                findings.append(
                    Finding(file=parsed.formulas[slug].file, field="embeds", message=problem)
                )
            elif resolved in direct[slug]:
                findings.append(
                    Finding(
                        file=parsed.formulas[slug].file,
                        field="embeds",
                        message=f"{item!r} is listed twice",
                    )
                )
            elif resolved is not None:
                direct[slug].append(resolved)
    for slug, document in documents.items():
        document["embeds"] = direct[slug]
        document["embeds_closure"] = sorted(_closure(slug, direct)) if direct[slug] else []
    return {
        "quantities": {
            slug: _quantity(entry, findings) for slug, entry in parsed.quantities.items()
        },
        "formulas": documents,
        "defaults": {slug: _default(raw) for slug, raw in parsed.defaults.items()},
        "rules": {slug: _rule(raw) for slug, raw in parsed.rules.items()},
        "taxonomy": parsed.taxonomy or {},
    }, findings
