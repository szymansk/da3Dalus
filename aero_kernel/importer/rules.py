"""Stage 3 of the import, part two: the cross-formula rules of ARCHITECTURE ch. 8.6.

The model types check what one entry can check about itself. These rules look across entries of the
validated model: producers (A7), symbols (A8), names and roles of targets (A9), units across
applications (A4), and the embeds closure. Each violation is a finding with the canon file, a field
and a message. Every rule lives here and nowhere else (one home per rule).
"""

from aero_kernel.canon.model import Application, CanonModel, Formula, Namespace
from aero_kernel.errors import DEFAULT_NAMESPACE
from aero_kernel.importer.findings import Finding

__all__ = ["A9_TARGET_NAME_EXCEPTIONS", "FORBIDDEN_NAME_SEGMENTS", "check_model"]

# A9 (maintainer, 2026-10-02): a target carries ``target`` as a kebab segment of its name (``stall-speed-target``,
# ``roll-rate-target-cruise``). The one exception A9 names is the limit load factor, which keeps its
# technical symbol.
A9_TARGET_NAME_EXCEPTIONS = frozenset({"limit-load-factor"})
# A9: an input or target is what the design asks for; these words are requirements language, not names
# of quantities. Whole kebab segments only: ``required`` is a different word.
FORBIDDEN_NAME_SEGMENTS = frozenset({"requirement", "goal", "req"})

_PREFIX = f"{DEFAULT_NAMESPACE}:"


def _bare(reference: str) -> str:
    """Return the slug of a ``calc:`` reference."""
    return reference.removeprefix(_PREFIX)


def _item(reference: str) -> tuple[str, str]:
    """Split an embed item ``calc:<slug>.<application>`` into its formula slug and application id."""
    formula, _, application = _bare(reference).rpartition(".")
    return formula, application


def _quantity_file(slug: str) -> str:
    return f"quantities/{slug}.md"


def _formula_file(slug: str) -> str:
    return f"formulas/{slug}.md"


def _produced(application: Application) -> dict[str, str]:
    """Return the quantities an application writes: parameter to qualified slug."""
    return {name: slug for name, slug in application.produce.items() if slug is not None}


def _bound(application: Application) -> set[str]:
    """Return the quantities an application binds as inputs (constants excluded)."""
    return {value for value in application.bind.values() if isinstance(value, str)}


# --- producers (A7) and roles (A9) ---------------------------------------------------------------------------


def _producers(content: Namespace) -> list[Finding]:
    """One producer per quantity; every derived or output quantity has one; inputs have none."""
    findings: list[Finding] = []
    first: dict[str, str] = {}
    for slug, formula in sorted(content.formulas.items()):
        for index, application in enumerate(formula.applications):
            for parameter, quantity in _produced(application).items():
                where = f"{_PREFIX}{slug}.{application.id}"
                role = content.quantities[_bare(quantity)].role
                field = f"applications[{index}].produce.{parameter}"
                if role in ("input", "target"):
                    findings.append(
                        Finding(
                            file=_formula_file(slug),
                            field=field,
                            message=f"{quantity} has role {role}: the caller supplies it, no formula "
                            "may produce it (A9)",
                        )
                    )
                if quantity in first:
                    findings.append(
                        Finding(
                            file=_formula_file(slug),
                            field=field,
                            message=f"quantity {quantity} is already produced by {first[quantity]} (A7)",
                        )
                    )
                else:
                    first[quantity] = where
    for slug, quantity in sorted(content.quantities.items()):
        if quantity.role in ("derived", "output") and f"{_PREFIX}{slug}" not in first:
            findings.append(
                Finding(
                    file=_quantity_file(slug),
                    field="role",
                    message=f"quantity {_PREFIX}{slug} has role {quantity.role} but no formula produces it",
                )
            )
    return findings


def _names(content: Namespace) -> list[Finding]:
    """A9: a target has a ``target`` segment in its name; no input or target is called requirement.

    The reverse is no rule: an output computed at a target is named after it.
    """
    findings: list[Finding] = []
    for slug, quantity in sorted(content.quantities.items()):
        if (
            quantity.role == "target"
            and "target" not in slug.split("-")
            and slug not in A9_TARGET_NAME_EXCEPTIONS
        ):
            findings.append(
                Finding(
                    file=_quantity_file(slug),
                    field="canon",
                    message="a quantity of role target needs a target segment in its name (A9)",
                )
            )
        if quantity.role in ("input", "target"):
            words = sorted(FORBIDDEN_NAME_SEGMENTS & set(slug.split("-")))
            if words:
                findings.append(
                    Finding(
                        file=_quantity_file(slug),
                        field="canon",
                        message=f"the name of an input or target must not contain {words} (A9)",
                    )
                )
    return findings


def _symbols(content: Namespace) -> list[Finding]:
    """A8: a symbol names one quantity."""
    findings: list[Finding] = []
    owner: dict[str, str] = {}
    for slug, quantity in sorted(content.quantities.items()):
        if quantity.symbol in owner:
            findings.append(
                Finding(
                    file=_quantity_file(slug),
                    field="symbol",
                    message=f"symbol {quantity.symbol!r} is already used by {_PREFIX}{owner[quantity.symbol]} (A8)",
                )
            )
        else:
            owner[quantity.symbol] = slug
    return findings


# --- units across applications (A4) ---------------------------------------------------------------------------


def _units(content: Namespace) -> list[Finding]:
    """A4: one parameter has one unit in every application that binds or produces it."""
    findings: list[Finding] = []
    for slug, formula in sorted(content.formulas.items()):
        for side in ("bind", "produce"):
            seen: dict[str, tuple[str, str, str]] = {}
            for index, application in enumerate(formula.applications):
                values = application.bind if side == "bind" else application.produce
                for parameter, value in values.items():
                    if not isinstance(value, str):
                        continue
                    unit = content.quantities[_bare(value)].unit
                    if parameter not in seen:
                        seen[parameter] = (value, unit, application.id)
                    elif seen[parameter][1] != unit:
                        other, other_unit, other_application = seen[parameter]
                        findings.append(
                            Finding(
                                file=_formula_file(slug),
                                field=f"applications[{index}].{side}.{parameter}",
                                message=f"parameter {parameter} is {value} ({unit}) here but {other} "
                                f"({other_unit}) in application {other_application} (A4)",
                            )
                        )
    return findings


# --- the embeds closure --------------------------------------------------------------------------------------


def _cycle_members(content: Namespace) -> dict[str, str]:
    """Return the formulas with an application in their own embeds closure, and one such item each."""
    members: dict[str, str] = {}
    for slug, formula in sorted(content.formulas.items()):
        for application in formula.applications:
            item = f"{_PREFIX}{slug}.{application.id}"
            if item in formula.embeds_closure:
                members[slug] = item
                break
    return members


def _cycles(members: dict[str, str]) -> list[Finding]:
    """No application of a formula is in its own embeds closure; reported once per member formula."""
    return [
        Finding(
            file=_formula_file(slug),
            field="embeds",
            message=f"{item} is in its own embeds closure (a cycle)",
        )
        for slug, item in members.items()
    ]


def _closure_applications(content: Namespace, formula: Formula) -> list[tuple[str, Application]]:
    """Return the embedded applications of a formula's closure, as written."""
    result: list[tuple[str, Application]] = []
    for reference in formula.embeds_closure:
        target, application = _item(reference)
        result.append((target, content.formulas[target].application(application)))
    return result


def _embeds(content: Namespace, members: dict[str, str]) -> list[Finding]:
    """Variables are read in the closure; no interval formula is embedded; every input is accounted for.

    A formula whose closure contains a cycle member has no defined closure and is skipped; the cycle
    itself is the finding.
    """
    findings: list[Finding] = []
    for slug, formula in sorted(content.formulas.items()):
        if not formula.embeds:
            continue
        if any(_item(reference)[0] in members for reference in formula.embeds_closure):
            continue
        inside = _closure_applications(content, formula)
        read_inside = set[str]().union(*(_bound(application) for _, application in inside))
        produced_inside = set[str]().union(
            *(set(_produced(application).values()) for _, application in inside)
        )
        own_inputs = set[str]().union(
            *(_bound(application) for application in formula.applications)
        )
        supplied = own_inputs | produced_inside | set(formula.variables)
        for position, variable in enumerate(formula.variables):
            if variable not in read_inside:
                findings.append(
                    Finding(
                        file=_formula_file(slug),
                        field=f"variables[{position}]",
                        message=f"{variable} is read by no formula in the embeds closure",
                    )
                )
        for target, application in inside:
            item = f"{_PREFIX}{target}.{application.id}"
            if content.formulas[target].uncertainty == "interval":
                findings.append(
                    Finding(
                        file=_formula_file(slug),
                        field="embeds",
                        message=f"{_PREFIX}{target} has uncertainty: interval and may not be embedded",
                    )
                )
            for quantity in _bound(application) - supplied:  # check_model sorts the findings
                findings.append(
                    Finding(
                        file=_formula_file(slug),
                        field="embeds",
                        message=f"input {quantity} of embedded {item} is neither a variable of "
                        f"{_PREFIX}{slug}, an input of it, nor produced inside the closure",
                    )
                )
    return findings


def check_model(model: CanonModel) -> list[Finding]:
    """Check the cross-formula rules of a validated model.

    Args:
        model: The canon model, already valid as a whole.

    Returns:
        Every violation, ordered by file and field; empty if the canon obeys all rules.
    """
    findings: list[Finding] = []
    for content in model.namespaces.values():
        findings.extend(_producers(content))
        findings.extend(_names(content))
        findings.extend(_symbols(content))
        findings.extend(_units(content))
        members = _cycle_members(content)
        findings.extend(_cycles(members))
        findings.extend(_embeds(content, members))
    unique = dict.fromkeys(findings)
    return sorted(unique, key=lambda finding: (finding.file, finding.field, finding.message))
