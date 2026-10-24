"""Taxonomy types (ARCHITECTURE ch. 8.9): the vocabulary of the canon's tag families.

The canon entries carry tags from six families: ``module/``, ``point/``, ``stage/``, ``group/``,
``discipline/`` (quantities) and ``direction/`` (formulas). ``taxonomy.yaml`` states every value of
every family once: its label, its explanation and its properties. The importer validates the tags
against it and carries it into the canon model, so the navigator and the kernel read one vocabulary.
The list order of a family is its display order; for ``stages`` it is the order of the calculation
chain.
"""

from typing import Annotated, Literal, Self

from aero_kernel.errors import SLUG_REGEX, WORLD_NAME_REGEX
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

__all__ = [
    "Direction",
    "Discipline",
    "Group",
    "Module",
    "NonBlank",
    "Point",
    "Slug",
    "Stage",
    "Taxonomy",
    "Tool",
    "ToolInfo",
    "World",
]

# Text the canon must state (a symbol, a source, a label): at least one non-blank character.
NonBlank = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Slug = Annotated[str, StringConstraints(pattern=f"^{SLUG_REGEX}$")]
WorldId = Annotated[str, StringConstraints(pattern=f"^{WORLD_NAME_REGEX}$")]

Tool = Literal["APP", "ATM", "GEO", "AB", "AVL", "OPT", "KAT", "APC"]

_CONFIG = ConfigDict(extra="forbid", frozen=True)


class _Value(BaseModel):
    """What every value of every family states.

    Attributes:
        id: The tag value, the part after ``<family>/``.
        label: The name shown to readers.
        explanation: What the value means, in the canon's words.
    """

    model_config = _CONFIG

    id: Slug
    label: NonBlank
    explanation: NonBlank


class Module(_Value):
    """A module groups the inputs and targets (``module/<id>``).

    Attributes:
        cross_cutting: Nearly every formula depends on the module's quantities.
        holds_targets: The module's quantities are targets (role ``target``), and only these.
    """

    cross_cutting: bool = False
    holds_targets: bool = False


class Point(_Value):
    """An operating point or configuration a final result belongs to (``point/<id>``)."""


class Stage(_Value):
    """A role in the calculation chain an intermediate quantity has (``stage/<id>``).

    Attributes:
        reference: The stage holds references: values derived from the inputs of a module. Their
            quantities carry a module and a group, and no discipline.
    """

    reference: bool = False


class Group(_Value):
    """A sub-cluster of a stage (``group/<id>``).

    Attributes:
        parent: The group this one is a part of (the powertrain holds motor, propeller and battery).
        stage: The stage whose quantities carry this group; ``None`` if the group only has children.
        module: The module a ``references`` group derives from; ``None`` otherwise.
    """

    parent: Slug | None = None
    stage: Slug | None = None
    module: Slug | None = None


class Discipline(_Value):
    """The question a derived quantity answers (``discipline/<id>``).

    Attributes:
        stability: The discipline is about static stability; its final results are shown after
            the values of their operating point.
    """

    stability: bool = False


class Direction(_Value):
    """The direction of a formula (``direction/<id>``).

    Attributes:
        default: The direction of a formula that carries no ``direction/`` tag.
    """

    default: bool = False


class ToolInfo(BaseModel):
    """A tool code with its name.

    Attributes:
        id: The tool code a formula's ``tool`` field holds.
        name: The tool's name as shown to readers.
    """

    model_config = _CONFIG

    id: Tool
    name: NonBlank


class World(BaseModel):
    """A method world with the tool that computes it.

    Attributes:
        id: The world name a formula's ``worlds`` field holds.
        tool: The tool whose version and settings the world's result depends on.
    """

    model_config = _CONFIG

    id: WorldId
    tool: Tool


def _duplicates(ids: list[str]) -> list[str]:
    """Return the ids that occur more than once, sorted."""
    return sorted({value for value in ids if ids.count(value) > 1})


class Taxonomy(BaseModel):
    """Every value of every tag family, in display order.

    A family without values is not used by the canon that carries this taxonomy: its tags are
    neither accepted nor required.

    Attributes:
        modules: Modules of inputs and targets.
        points: Operating points of final results.
        stages: Stages of intermediate quantities, in the order of the calculation chain.
        groups: Sub-clusters of the stages.
        disciplines: The questions derived quantities answer.
        directions: Formula directions.
        tools: Tool codes with names.
        worlds: Method worlds with their tool.
    """

    model_config = _CONFIG

    modules: tuple[Module, ...] = ()
    points: tuple[Point, ...] = ()
    stages: tuple[Stage, ...] = ()
    groups: tuple[Group, ...] = ()
    disciplines: tuple[Discipline, ...] = ()
    directions: tuple[Direction, ...] = ()
    tools: tuple[ToolInfo, ...] = ()
    worlds: tuple[World, ...] = ()

    def _families(self) -> dict[str, list[str]]:
        """Return the ids of every family, by family name."""
        return {
            "modules": [value.id for value in self.modules],
            "points": [value.id for value in self.points],
            "stages": [value.id for value in self.stages],
            "groups": [value.id for value in self.groups],
            "disciplines": [value.id for value in self.disciplines],
            "directions": [value.id for value in self.directions],
            "tools": [value.id for value in self.tools],
            "worlds": [value.id for value in self.worlds],
        }

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        """Reject an id that a family states twice."""
        for family, ids in self._families().items():
            if duplicates := _duplicates(ids):
                msg = f"{family}: duplicate id {duplicates}"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        """Require every id a property names to exist in its family."""
        families = self._families()
        groups = {group.id: group for group in self.groups}
        for group in self.groups:
            problems = [
                f"{name} {value!r}"
                for name, value, family in (
                    ("parent", group.parent, "groups"),
                    ("stage", group.stage, "stages"),
                    ("module", group.module, "modules"),
                )
                if value is not None and value not in families[family]
            ]
            if group.parent is not None and group.parent in groups:
                if groups[group.parent].parent is not None:
                    problems.append(f"parent {group.parent!r} is itself a part of a group")
                if group.parent == group.id:
                    problems.append("parent is the group itself")
            if problems:
                msg = f"group {group.id}: unknown or invalid " + ", ".join(problems)
                raise ValueError(msg)
        tools = set(families["tools"])
        for world in self.worlds:
            if world.tool not in tools:
                msg = f"world {world.id}: tool {world.tool!r} is not in tools"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_default_direction(self) -> Self:
        """Require exactly one default direction if there are directions."""
        defaults = [direction.id for direction in self.directions if direction.default]
        if self.directions and len(defaults) != 1:
            msg = f"directions: exactly one must be the default, found {defaults}"
            raise ValueError(msg)
        return self

    def default_direction(self) -> str | None:
        """Return the id of the default direction, or ``None`` if there are no directions."""
        return next((value.id for value in self.directions if value.default), None)
