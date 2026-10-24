"""Stage 3 of the import, part three: the tags of the canon entries against the taxonomy (ch. 8.9).

``taxonomy.yaml`` states every value of every tag family. These rules check what the tags of the
entries say against it: a tag value is in the taxonomy, a quantity carries the tags its place in
the calculation requires, a target stands in a module that holds targets, a group agrees with the
stage and module of its quantities, a formula's tool is declared, and a probe names a
quantity that exists. A family the taxonomy leaves empty is not used by the canon: it accepts no
tag and requires none.
"""

from collections.abc import Sequence

from aero_kernel.canon.model import Namespace, Quantity
from aero_kernel.canon.taxonomy import Taxonomy
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.normalise import QUANTITY_TAG_FAMILIES

__all__ = ["check_tags"]


def _file(slug: str) -> str:
    return f"quantities/{slug}.md"


def _unknown(value: str, family: str, ids: Sequence[str]) -> str:
    """Return the message for a value that the taxonomy lacks."""
    declared = ", ".join(ids) if ids else "none declared"
    return f"{value!r} is not in the taxonomy ({family}: {declared})"


def _family_ids(taxonomy: Taxonomy) -> dict[str, list[str]]:
    """Return the ids of each quantity family, by the name of the tag field."""
    return {
        "module": [value.id for value in taxonomy.modules],
        "point": [value.id for value in taxonomy.points],
        "stage": [value.id for value in taxonomy.stages],
        "group": [value.id for value in taxonomy.groups],
        "discipline": [value.id for value in taxonomy.disciplines],
    }


_PLURAL = {
    "module": "modules",
    "point": "points",
    "stage": "stages",
    "group": "groups",
    "discipline": "disciplines",
}


def _known_values(content: Namespace) -> list[Finding]:
    """Every tag value of a quantity and every direction of a formula is in the taxonomy."""
    findings: list[Finding] = []
    families = _family_ids(content.taxonomy)
    for slug, quantity in sorted(content.quantities.items()):
        for family in QUANTITY_TAG_FAMILIES:
            value: str | None = getattr(quantity, family)
            if value is not None and value not in families[family]:
                findings.append(
                    Finding(
                        file=_file(slug),
                        field=family,
                        message=_unknown(value, _PLURAL[family], families[family]),
                    )
                )
    directions = [value.id for value in content.taxonomy.directions]
    tools = [value.id for value in content.taxonomy.tools]
    for slug, formula in sorted(content.formulas.items()):
        file = f"formulas/{slug}.md"
        if formula.direction is not None and formula.direction not in directions:
            findings.append(
                Finding(
                    file=file,
                    field="direction",
                    message=_unknown(formula.direction, "directions", directions),
                )
            )
        if formula.tool not in tools:
            findings.append(
                Finding(file=file, field="tool", message=_unknown(formula.tool, "tools", tools))
            )
    return findings


def _flows(content: Namespace) -> tuple[set[str], set[str]]:
    """Return the quantities some application produces and those some application reads."""
    produced: set[str] = set()
    consumed: set[str] = set()
    for formula in content.formulas.values():
        for application in formula.applications:
            produced.update(
                value.removeprefix("calc:") for value in application.produce.values() if value
            )
            consumed.update(
                value.removeprefix("calc:")
                for value in application.bind.values()
                if isinstance(value, str)
            )
            consumed.update(slug.removeprefix("calc:") for slug in application.given or ())
    return produced, consumed


def _required(slug: str, field: str, place: str) -> Finding:
    return Finding(file=_file(slug), field=field, message=f"missing: {place} needs a {field} tag")


def _missing_tags(content: Namespace) -> list[Finding]:
    """A quantity carries the tags its place in the calculation requires."""
    taxonomy = content.taxonomy
    families = _family_ids(taxonomy)
    reference_stages = {stage.id for stage in taxonomy.stages if stage.reference}
    produced, consumed = _flows(content)
    findings: list[Finding] = []
    for slug, quantity in sorted(content.quantities.items()):
        is_reference = quantity.stage in reference_stages
        places: list[tuple[str, str]] = []
        if slug not in produced:
            places.append(("module", "an input or target"))
        else:
            places.append(
                ("stage", "an intermediate quantity")
                if slug in consumed
                else ("point", "a final result")
            )
            if not is_reference:
                places.append(("discipline", "a derived quantity"))
        if is_reference:
            places += [("module", "a reference"), ("group", "a reference")]
        # An intermediate quantity needs a stage, a final result a point.
        for field, place in places:
            if families[field] and getattr(quantity, field) is None:
                findings.append(_required(slug, field, place))
    return findings


def _targets(content: Namespace) -> list[Finding]:
    """A target stands in a module that holds targets, and only a target does."""
    holders = {module.id for module in content.taxonomy.modules if module.holds_targets}
    findings: list[Finding] = []
    for slug, quantity in sorted(content.quantities.items()):
        if quantity.module is None or not content.taxonomy.modules:
            continue
        is_target = quantity.role == "target"
        if is_target and quantity.module not in holders:
            findings.append(
                Finding(
                    file=_file(slug),
                    field="module",
                    message=f"a target stands in a module that holds targets, not {quantity.module!r}",
                )
            )
        if not is_target and quantity.module in holders:
            findings.append(
                Finding(
                    file=_file(slug),
                    field="module",
                    message=f"module {quantity.module!r} holds only targets; this quantity is {quantity.role}",
                )
            )
    return findings


def _group_agrees(slug: str, quantity: Quantity, taxonomy: Taxonomy) -> list[Finding]:
    """The stage and module a group states are those of its quantity."""
    group = next((value for value in taxonomy.groups if value.id == quantity.group), None)
    if group is None:
        return []
    return [
        Finding(
            file=_file(slug),
            field="group",
            message=f"group {group.id!r} belongs to {name} {wanted!r}; this quantity has "
            f"{name} {have!r}",
        )
        for name, wanted, have in (
            ("stage", group.stage, quantity.stage),
            ("module", group.module, quantity.module),
        )
        if wanted is not None and wanted != have
    ]


def _groups(content: Namespace) -> list[Finding]:
    """Every quantity's group agrees with its stage and module."""
    return [
        finding
        for slug, quantity in sorted(content.quantities.items())
        for finding in _group_agrees(slug, quantity, content.taxonomy)
    ]


def _probes(content: Namespace) -> list[Finding]:
    """A probe names an existing quantity other than itself."""
    findings: list[Finding] = []
    for slug, quantity in sorted(content.quantities.items()):
        if quantity.checks is None:
            continue
        if quantity.checks == slug:
            message = "a quantity cannot check itself"
        elif quantity.checks not in content.quantities:
            message = f"no quantity {quantity.checks!r}"
        else:
            continue
        findings.append(Finding(file=_file(slug), field="checks", message=message))
    return findings


def check_tags(content: Namespace) -> list[Finding]:
    """Check the tags of one namespace against its taxonomy.

    Args:
        content: A validated namespace.

    Returns:
        Every violation; empty if the tags obey all rules.
    """
    return [
        *_known_values(content),
        *_missing_tags(content),
        *_targets(content),
        *_groups(content),
        *_probes(content),
    ]
