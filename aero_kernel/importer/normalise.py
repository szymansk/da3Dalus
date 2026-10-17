"""Stage 2 of the import: normalise the parsed entries into the shape of the canon model (ch. 8.9).

Only what the model cannot do for itself happens here: numbers become floats, the unit spellings
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

from aero_kernel.canon.model import CostClass, Tool
from aero_kernel.errors import DEFAULT_NAMESPACE, IDENTIFIER_REGEX, SLUG_REGEX
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.parse import Entry, ParsedCanon
from aero_kernel.importer.yamlvalue import as_list, as_mapping

__all__ = ["DERIVED_COST", "normalise"]

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


def _float(value: object) -> object:
    """Return a YAML number as a float (the model's numbers are strict floats).

    A boolean stays a boolean, so the model rejects it.
    """
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return value


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


def _quantity(entry: Entry) -> JsonDict:
    """Normalise one quantity entry: the unit folds, everything else is carried as written."""
    return {
        name: _unit(value) if name == "unit" else value
        for name, value in entry.front.items()
        if name in ("symbol", "unit", "role", "type", "uncertainty", "positive")
    }


def _default(raw: dict[str, object]) -> JsonDict:
    """Normalise one ``defaults.yaml`` entry: the value becomes a float, the unit folds."""
    return {
        name: _float(value) if name == "value" else _unit(value) if name == "unit" else value
        for name, value in raw.items()
    }


# --- formulas ---------------------------------------------------------------------------------


def _binding(raw: object) -> object:
    """Normalise one ``bind`` value: a slug is qualified, a constant's number becomes a float."""
    mapping = as_mapping(raw)
    if mapping is None:
        return _qualified(raw)
    return {key: _float(value) if key == "const" else value for key, value in mapping.items()}


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


def _application(item: object, inputs: object, outputs: object) -> object:
    """Merge one application over the formula's defaults; the model rejects what does not fit."""
    mapping = as_mapping(item)
    if mapping is None:
        return item
    return {
        **mapping,
        "bind": _merged(inputs, mapping.get("bind"), _binding),
        "produce": _merged(
            {key: value for key, value in (as_mapping(outputs) or {}).items() if value is not None},
            mapping.get("produce"),
            _qualified,
        ),
        **({"given": _qualified_list(mapping["given"])} if "given" in mapping else {}),
    }


def _applications(entry: Entry, inputs: object, outputs: object) -> list[object]:
    """Return the merged applications; an entry without any has the implicit ``default``."""
    raw = entry.front.get("applications")
    items = [{"id": "default"}] if raw is None else (as_list(raw) or [])
    return [_application(item, inputs, outputs) for item in items]


def _formula(entry: Entry, applications_of: dict[str, list[str]]) -> tuple[JsonDict, list[object]]:
    """Normalise one formula entry except for its embeds; return it with its raw embeds items."""
    front = entry.front
    tool = front["tool"]
    inputs = _qualified_map(front["inputs"])
    outputs = _qualified_map(front["outputs"])
    doc: JsonDict = {
        "kind": front["kind"],
        "tool": tool,
        "inputs": inputs,
        "outputs": outputs,
        "applications": _applications(entry, inputs, outputs),
    }
    if "cost" in front:
        doc["cost"] = front["cost"]
    elif isinstance(tool, str) and tool in DERIVED_COST:
        doc["cost"] = DERIVED_COST[tool]
    for name in ("preconditions", "postconditions", "optional", "uncertainty", "worlds"):
        if name in front:
            doc[name] = front[name]
    if "variables" in front:
        doc["variables"] = _qualified_list(front["variables"])
    applications_of[entry.slug] = [
        str(mapping["id"])
        for item in cast("list[object]", doc["applications"])
        if (mapping := as_mapping(item)) is not None and "id" in mapping
    ]
    return doc, as_list(front.get("embeds")) or []


# --- embeds -----------------------------------------------------------------------------------


def _resolve_embed(
    item: object, applications_of: dict[str, list[str]]
) -> tuple[str | None, str | None]:
    """Normalise one embeds item to ``calc:<slug>.<application-id>``; return it or why not."""
    match = _EMBED_ITEM.fullmatch(item) if isinstance(item, str) else None
    if match is None:
        return None, f"{item!r} is not <slug> or <slug>.<application-id>"
    slug, application = match.group("slug"), match.group("application")
    applications = applications_of.get(slug)
    if applications is None:
        return None, f"embeds {item}, but there is no formula {slug}"
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
        The calc namespace as a plain dict (``quantities``, ``formulas``, ``defaults``) and the
        findings about embeds; the dict is only meaningful if there is no finding.
    """
    findings: list[Finding] = []
    applications_of: dict[str, list[str]] = {}
    documents: dict[str, JsonDict] = {}
    raw_embeds: dict[str, list[object]] = {}
    for slug, entry in parsed.formulas.items():
        documents[slug], raw_embeds[slug] = _formula(entry, applications_of)
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
        "quantities": {slug: _quantity(entry) for slug, entry in parsed.quantities.items()},
        "formulas": documents,
        "defaults": {slug: _default(raw) for slug, raw in parsed.defaults.items()},
    }, findings
