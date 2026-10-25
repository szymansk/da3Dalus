"""The rule table of the evaluation layer: bands, their meaning and their source (maintainer, 2026-10-25).

The canon computes and never judges (A10). A rule says which canon quantity it judges, in which
band the value is acceptable, what it means to leave the band, and where that comes from. The table
is data: no band lives in code. Validation against the canon model catches a rule that names a
quantity the canon does not have.
"""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from aero_kernel.canon.model import CanonModel, FiniteNumber, Unit, WhenTerm
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

__all__ = [
    "Band",
    "Level",
    "Position",
    "QuantityRef",
    "Rule",
    "RuleTable",
    "Severity",
    "check_rule_table",
    "shipped_rule_table",
]

_FROZEN = ConfigDict(extra="forbid", frozen=True)
_NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_RuleId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
_Ticket = Annotated[str, StringConstraints(pattern=r"^#[1-9][0-9]*$")]


class Position(StrEnum):
    """Where a number lies relative to a band."""

    BELOW = "below"
    INSIDE = "inside"
    ABOVE = "above"


class Severity(StrEnum):
    """How bad it is to leave a band on one side.

    ``BAD`` is a defect the source names; ``CAUTION`` is a cost without a defect, for example drag
    that buys nothing.
    """

    CAUTION = "caution"
    BAD = "bad"


class Band(BaseModel):
    """A range of acceptable values with open ends allowed, in the rule's unit.

    Attributes:
        min: Lower end; ``None`` for no lower end.
        max: Upper end; ``None`` for no upper end.
        min_inclusive: Whether ``min`` itself is inside.
        max_inclusive: Whether ``max`` itself is inside.
    """

    model_config = _FROZEN

    min: FiniteNumber | None = None
    max: FiniteNumber | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    @model_validator(mode="after")
    def _check_ends(self) -> Self:
        """Require at least one end, and the lower below the upper."""
        if self.min is None and self.max is None:
            msg = "a band needs at least one end"
            raise ValueError(msg)
        if self.min is not None and self.max is not None and self.min >= self.max:
            msg = f"band min {self.min} must be below max {self.max}"
            raise ValueError(msg)
        return self

    def position(self, value: float) -> Position:
        """Tell where a value lies relative to the band.

        Args:
            value: The number, in the band's unit.

        Returns:
            ``BELOW`` or ``ABOVE`` outside the band, ``INSIDE`` otherwise.
        """
        if self.min is not None and (
            value < self.min or (value == self.min and not self.min_inclusive)
        ):
            return Position.BELOW
        if self.max is not None and (
            value > self.max or (value == self.max and not self.max_inclusive)
        ):
            return Position.ABOVE
        return Position.INSIDE


class Level(Band):
    """A named sub-range with its own meaning, for a rule that says more than inside or outside.

    Attributes:
        id: Short name of the level.
        meaning: What the source says about a value in this range.
    """

    id: _RuleId
    meaning: _NonBlank


class QuantityRef(BaseModel):
    """The canon quantity a rule judges.

    Attributes:
        slug: Canon slug of the quantity.
        planned: Ticket that will add the quantity to the canon; present exactly while the canon
            lacks it. The rule is then ``not_available``.
    """

    model_config = _FROZEN

    slug: _RuleId
    planned: _Ticket | None = None


class Rule(BaseModel):
    """One design rule.

    Attributes:
        id: Short identifier of the rule.
        title: What the rule judges, for people.
        quantity: The canon quantity judged.
        unit: Unit of the band; must equal the canon quantity's unit.
        band: The acceptable range.
        levels: Optional finer ranges, matched in order; the first that contains the value names it.
        source: Where the band comes from, with the equation number.
        when: Geometry terms that must all hold for the rule to apply.
        when_not: Geometry terms none of which may hold for the rule to apply.
        below: What the source says about a value below the band; absent where the source names no
            consequence, and not allowed when the band has no lower end.
        above: What the source says about a value above the band; absent where the source names no
            consequence, and not allowed when the band has no upper end.
        below_severity: How bad a value below the band is; ``bad`` unless stated.
        above_severity: How bad a value above the band is; ``bad`` unless stated.
        below_basis: Where a non-default severity or an unsourced meaning of the lower side comes
            from, when it is not the rule's ``source``.
        above_basis: The same for the upper side.
        note: A difference between the source's definition and the canon quantity's, or any other
            caveat a reader needs.
    """

    model_config = _FROZEN

    id: _RuleId
    title: _NonBlank
    quantity: QuantityRef
    unit: Unit
    band: Band
    levels: tuple[Level, ...] = ()
    source: _NonBlank
    when: tuple[WhenTerm, ...] = ()
    when_not: tuple[WhenTerm, ...] = ()
    below: _NonBlank | None = None
    above: _NonBlank | None = None
    below_severity: Severity = Severity.BAD
    above_severity: Severity = Severity.BAD
    below_basis: _NonBlank | None = None
    above_basis: _NonBlank | None = None
    note: _NonBlank | None = None

    @model_validator(mode="after")
    def _check_meanings(self) -> Self:
        """Reject anything stated for a side the band lacks; a side may have no meaning where the source names none."""
        for side, bound, meaning, severity, basis in (
            ("below", self.band.min, self.below, self.below_severity, self.below_basis),
            ("above", self.band.max, self.above, self.above_severity, self.above_basis),
        ):
            if bound is not None:
                continue
            if meaning is not None or basis is not None or severity is not Severity.BAD:
                msg = f"rule {self.id}: the band has no {side} side, so its meaning, severity and basis must be absent"
                raise ValueError(msg)
        return self

    def level_of(self, value: float) -> str | None:
        """Name the first level that contains a value.

        Args:
            value: The number, in the rule's unit.

        Returns:
            The level id, or ``None`` if no level contains it.
        """
        for level in self.levels:
            if level.position(value) is Position.INSIDE:
                return level.id
        return None


class RuleTable(BaseModel):
    """A set of rules from one source.

    Attributes:
        source: The document the rules come from.
        rules: The rules; ids are unique.
    """

    model_config = _FROZEN

    source: _NonBlank
    rules: Annotated[tuple[Rule, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        """Require unique rule ids."""
        ids = [rule.id for rule in self.rules]
        duplicated = sorted({i for i in ids if ids.count(i) > 1})
        if duplicated:
            msg = f"duplicate rule ids: {duplicated}"
            raise ValueError(msg)
        return self


def check_rule_table(table: RuleTable, model: CanonModel) -> list[str]:
    """Check a rule table against the canon model.

    A rule must name a canon quantity of the same unit; a quantity the canon lacks is allowed only
    with a ``planned`` ticket, and a ``planned`` marker on a quantity the canon has is stale.

    Args:
        table: The rule table.
        model: The canon model.

    Returns:
        One sentence per problem; empty if the table is consistent.
    """
    quantities = {slug: q for ns in model.namespaces.values() for slug, q in ns.quantities.items()}
    problems: list[str] = []
    for rule in table.rules:
        ref = rule.quantity
        known = quantities.get(ref.slug)
        if known is None and ref.planned is None:
            problems.append(
                f"rule {rule.id}: the canon has no quantity {ref.slug} and none is planned"
            )
        elif known is not None and ref.planned is not None:
            problems.append(
                f"rule {rule.id}: {ref.slug} is in the canon, so the planned marker {ref.planned} is stale"
            )
        elif known is not None and known.unit != rule.unit:
            problems.append(
                f"rule {rule.id}: unit {rule.unit} differs from the canon unit {known.unit} of {ref.slug}"
            )
    return problems


def shipped_rule_table() -> RuleTable:
    """Load the rule table shipped with the package (``rule_table.json``).

    It is generated from ``_reversa_sdd/calculations/evaluation/drela.yaml`` by
    ``python -m aero_kernel.importer.rule_table`` and never edited by hand.

    Returns:
        The validated table.
    """
    path = Path(__file__).resolve().parent / "rule_table.json"
    return RuleTable.model_validate_json(path.read_text(encoding="utf-8"))
