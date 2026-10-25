"""Canon-model types (ARCHITECTURE ch. 8.9): the interpreted canon the kernel runs on.

Every field mirrors the canon README section "Machine-readable fields" one to one, normalised as
ch. 8.9 says. All models are frozen, reject unknown fields and carry their invariants themselves:
they are canon-model types, not input types.
"""

from collections.abc import Iterator, Mapping
from typing import Annotated, Literal, NamedTuple, Self, TypedDict

from aero_kernel.canon.taxonomy import NonBlank, Slug, Taxonomy, Tool
from aero_kernel.canonical import sha256_of
from aero_kernel.errors import (
    DEFAULT_NAMESPACE,
    IDENTIFIER_REGEX,
    NAMESPACE_REGEX,
    SLUG_REGEX,
    WORLD_NAME_REGEX,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    StringConstraints,
    Tag,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

__all__ = [
    "BINDING_TAGS",
    "DATA_KINDS",
    "DEFAULT_NAMESPACE",
    "Application",
    "Binding",
    "CanonModel",
    "CanonProblem",
    "Check",
    "ConstBinding",
    "CostClass",
    "DataSource",
    "Default",
    "Formula",
    "FormulaKind",
    "Namespace",
    "OnViolation",
    "Quantity",
    "QuantityRole",
    "QuantityType",
    "Tool",
    "Unit",
    "WhenTerm",
    "compute_content_hash",
]

# Numbers in the model are finite (a model with NaN would not survive its JSON form).
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]

QuantityRole = Literal["input", "target", "derived", "output"]
QuantityType = Literal[
    "scalar",
    "airplane",
    "components",
    "curve",
    "polar",
    "curve_pair",
    "per_control_surface",
]

# The canon's unit symbols after normalisation (ch. 8.9 stage 2); ``1`` is dimensionless and also
# stands for the not-a-number ``airplane`` types. A new unit is a model change.
Unit = Literal[
    "1",
    "m",
    "m^2",
    "kg",
    "s",
    "deg",
    "deg/s",
    "m/s",
    "m/s^2",
    "1/s",
    "1/rad",
    "1/rad^2",
    "N",
    "N/m^2",
    "N*m",
    "N/m",
    "Pa",
    "Pa*s",
    "kg/m^3",
    "W",
    "V",
    "A",
    "ohm",
    "Wh",
    "Wh/kg",
    "rpm/V",
    "mAh",
    "1/h",
]

_MODEL_CONFIG = ConfigDict(extra="forbid", frozen=True)


DefaultBasis = Literal["definition", "standard", "sourced", "convention"]
"""What kind of value a default is; ``convention`` marks a chosen value without a published source."""


class Default(BaseModel):
    """A value the canon states for a supplied quantity, with its unit, basis, source and regime.

    Attributes:
        value: The value, in ``unit``.
        unit: The unit of ``value``; it must equal the unit of the quantity.
        basis: ``definition`` (true by definition), ``standard`` (a published standard value),
            ``sourced`` (taken from a cited source) or ``convention`` (chosen, no published source,
            adopted on the maintainer's word).
        source: Citation of where the value comes from (ADR 0028).
        regime: The flight regime the value is valid for (ADR 0028).
    """

    model_config = _MODEL_CONFIG

    value: FiniteNumber
    unit: Unit
    basis: DefaultBasis
    source: NonBlank
    regime: NonBlank


DATA_KINDS = ("geometry", "component", "default", "app", "evaluation")
"""The five kinds of data source a supplied quantity can have (canon README, "Two stages", #1251)."""

DataSource = Annotated[str, StringConstraints(pattern=rf"^({'|'.join(DATA_KINDS)}):\S+$")]
"""``<kind>:<location>``, e.g. ``geometry:total_mass_kg``; the importer checks the location."""


class Quantity(BaseModel):
    """A quantity of the canon vocabulary.

    Attributes:
        symbol: The quantity's symbol.
        unit: The unit of its values; ``1`` is dimensionless.
        role: ``input`` and ``target`` are supplied by the caller, ``derived`` and ``output`` computed.
        type: The kind of value.
        uncertainty: ``interval`` where the producer declares method worlds.
        positive: ``True`` where the quantity is strictly greater than zero by its definition,
            otherwise omitted (``None``); ``false`` is no spelling of the canon.
        module: The taxonomy module of an input, target or reference; ``None`` where the quantity has none.
        point: The taxonomy operating point of a final result.
        stage: The taxonomy stage of an intermediate quantity.
        group: The taxonomy group of a quantity inside its stage.
        discipline: The taxonomy discipline of a derived quantity.
        checks: The slug of the quantity this one verifies (a probe); ``None`` for any other.
        at_most: The largest admissible value of a supplied scalar (an efficiency is at most 1),
            otherwise omitted (``None``).
        data: Where the quantity comes from in our data, each ``<kind>:<location>`` (a quantity no
            formula produces; stage 2 of the approval); ``None`` while it has no demonstrated source.
    """

    model_config = _MODEL_CONFIG

    symbol: NonBlank
    unit: Unit
    role: QuantityRole
    type: QuantityType
    uncertainty: Literal["interval"] | None = None
    positive: Literal[True] | None = None
    module: Slug | None = None
    point: Slug | None = None
    stage: Slug | None = None
    group: Slug | None = None
    discipline: Slug | None = None
    checks: Slug | None = None
    at_most: FiniteNumber | None = None
    data: Annotated[list[DataSource], Field(min_length=1)] | None = None

    @field_validator("positive", mode="before")
    @classmethod
    def _positive_is_the_boolean(cls, value: object) -> object:
        """Reject 1, 1.0 and "true": Python and pydantic read them as ``True``, JSON Schema does not."""
        if value is not None and not isinstance(value, bool):
            msg = "positive must be the boolean true"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_positive(self) -> Self:
        """Allow ``positive`` and ``at_most`` only on supplied scalars."""
        for name, value in (("positive", self.positive), ("at_most", self.at_most)):
            if value is None:
                continue
            if self.role not in ("input", "target"):
                msg = f"{name} is only allowed on role input or target, not {self.role}"
                raise ValueError(msg)
            if self.type != "scalar":
                msg = f"{name} is only allowed on a scalar quantity, not {self.type}"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_data_sources_differ(self) -> Self:
        """Reject a source named twice."""
        if self.data is not None and len(set(self.data)) != len(self.data):
            msg = "data names a source twice"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        """Reject ``positive`` with an ``at_most`` of 0 or less: no value would be admissible."""
        if self.positive and self.at_most is not None and self.at_most <= 0:
            msg = f"at_most {self.at_most} leaves no value for a positive quantity"
            raise ValueError(msg)
        return self


# --- formulas -------------------------------------------------------------------------------

FormulaKind = Literal["law", "procedure", "optimization", "fit", "rating"]
CostClass = Literal["instant", "seconds", "minutes"]
WhenTerm = Literal[
    "has_aileron",
    "has_elevator",
    "has_flap",
    "has_horizontal_tail",
    "has_rudder",
    "has_separate_flap_and_aileron",
    "has_vertical_tail",
]
OnViolation = Literal["warning", "error"]

# The slug, world-name, namespace and identifier patterns are defined once, in ``errors.py``; every other pattern here
# is built from them. Parameter names, like world names, are snake_case. A reference is fully
# qualified: ``<namespace>:<slug>`` (ch. 8.9).


def _anchored(regex: str) -> StringConstraints:
    """Constrain a string to match ``regex`` completely."""
    return StringConstraints(pattern=f"^{regex}$")


Parameter = Annotated[str, _anchored(WORLD_NAME_REGEX)]
Identifier = Annotated[str, _anchored(IDENTIFIER_REGEX)]


WorldName = Annotated[str, _anchored(WORLD_NAME_REGEX)]
QualifiedSlug = Annotated[str, _anchored(f"{NAMESPACE_REGEX}:{SLUG_REGEX}")]
# An embedded application: ``<namespace>:<slug>.<application-id>``; never a bare formula slug.
QualifiedApplication = Annotated[
    str, _anchored(rf"{NAMESPACE_REGEX}:{SLUG_REGEX}\.{IDENTIFIER_REGEX}")
]


class ConstBinding(BaseModel):
    """A constant bound to an input parameter, with its source (ADR 0028).

    Attributes:
        const: The value, in the parameter's unit.
        source: Citation of where the constant comes from.
    """

    model_config = _MODEL_CONFIG

    const: FiniteNumber
    source: NonBlank


# A binding is a quantity slug or a ``{const, source}`` constant. The tags are ours, so a validation
# location names the branch with a word of this module (``BINDING_TAGS``) and not with a pydantic name.
BINDING_TAGS = ("slug", "const")


def _binding_tag(value: object) -> str:
    """Tell the two kinds of binding apart: a mapping or a constant is ``const``, all else ``slug``."""
    return "const" if isinstance(value, dict | ConstBinding) else "slug"


Binding = Annotated[
    Annotated[QualifiedSlug, Tag("slug")] | Annotated[ConstBinding, Tag("const")],
    Discriminator(_binding_tag),
]


class Application(BaseModel):
    """A formula applied to concrete quantities, written out completely (ch. 8.5).

    ``bind`` and ``produce`` hold the merged result of the formula's defaults and the application's
    own overrides, so every input parameter is bound and every output parameter is produced.

    Attributes:
        id: Name of the application, unique within its formula; ``default`` for the implicit one.
        bind: Quantity or constant per input parameter.
        produce: Quantity per output parameter; ``None`` = the application does not expose it.
        when: Condition over the geometry; ``None`` = always.
        given: Quantities that must be supplied for the application to exist; ``None`` = always.
            Each must be bound by the application, but ``Formula`` checks that, not this type: an
            ``Application`` alone does not guarantee ``given`` is a subset of its bindings. The
            check runs after the bindings and the field rules, so a ``given`` fault of a formula
            that has other faults is deferred to the next run; it is never hidden.
    """

    model_config = _MODEL_CONFIG

    id: Identifier
    bind: dict[Parameter, Binding]
    produce: dict[Parameter, QualifiedSlug | None]
    when: WhenTerm | None = None
    given: Annotated[tuple[QualifiedSlug, ...], Field(min_length=1)] | None = None


class Check(BaseModel):
    """A pre- or postcondition of a formula (ch. 8.5).

    Attributes:
        id: Name of the check, unique among the formula's checks of its kind.
        parameter: The input (precondition) or output (postcondition) parameter it concerns.
        on_violation: ``error`` withholds the value, ``warning`` returns it with a defect warning.
        applications: Ids of the applications it belongs to; ``None`` = all of them.
    """

    model_config = _MODEL_CONFIG

    id: Identifier
    parameter: Parameter
    on_violation: OnViolation
    applications: Annotated[tuple[Identifier, ...], Field(min_length=1)] | None = None


def _parameter_problems(
    application_id: str,
    side: str,
    written: Mapping[str, object],
    declared: Mapping[str, object],
    how: str,
) -> list[str]:
    """Name every parameter an application binds or produces wrongly, application included."""
    where = f"application `{application_id}`"
    fault = "bound" if how == "bind" else "produced"
    problems = [
        f"{where}: {side} parameter `{name}` is not {fault}"
        + (" (write null to leave it unexposed)" if how == "produce" else "")
        for name in declared
        if name not in written
    ]
    problems.extend(
        f"{where}: parameter `{name}` is not an {side} of the formula"
        for name in written
        if name not in declared
    )
    return problems


class Formula(BaseModel):
    """A canon formula with its applications, checks, worlds and embeds (ch. 8.5, 8.13).

    Attributes:
        kind: The formula's kind.
        tool: The tool that evaluates it.
        cost: Cost class: declared in the canon, otherwise derived from ``tool`` (ch. 8.7).
        inputs: Default quantity per input parameter; ``None`` = bound per application.
        outputs: Default quantity per output parameter; ``None`` = produced per application.
        optional: Input parameters that may arrive as ``None``.
        applications: The applications, at least one.
        preconditions: Checks on inputs, run before the call.
        postconditions: Checks on outputs, run after the call.
        uncertainty: ``interval`` where the formula has method worlds.
        worlds: The method worlds, exactly with ``uncertainty``.
        embeds: Directly embedded applications, ``<ns>:<slug>.<application-id>``.
        variables: Quantities the embedder solves for or sweeps itself, exactly with ``embeds``.
        embeds_closure: Sorted, unique embeds reachable through ``embeds``, direct ones included.
        direction: The taxonomy direction (analysis or design); ``None`` only if the taxonomy has none.
    """

    model_config = _MODEL_CONFIG

    kind: FormulaKind
    tool: Tool
    cost: CostClass
    inputs: dict[Parameter, QualifiedSlug | None]
    outputs: dict[Parameter, QualifiedSlug | None]
    optional: tuple[Parameter, ...] = ()
    applications: Annotated[tuple[Application, ...], Field(min_length=1)]
    preconditions: tuple[Check, ...] = ()
    postconditions: tuple[Check, ...] = ()
    uncertainty: Literal["interval"] | None = None
    worlds: tuple[WorldName, ...] = ()
    embeds: tuple[QualifiedApplication, ...] = ()
    variables: tuple[QualifiedSlug, ...] = ()
    embeds_closure: tuple[QualifiedApplication, ...] = ()
    direction: Slug | None = None

    def application(self, application_id: str) -> Application:
        """Return the application with the given id.

        Args:
            application_id: Id of the application.

        Returns:
            The application.

        Raises:
            KeyError: If the formula has no such application.
        """
        for application in self.applications:
            if application.id == application_id:
                return application
        raise KeyError(application_id)

    @model_validator(mode="after")
    def _check_applications(self) -> Self:
        """Require unique ids, and every input bound and every output produced, nothing else."""
        ids = [application.id for application in self.applications]
        if len(set(ids)) != len(ids):
            msg = "application ids must be unique"
            raise ValueError(msg)
        problems: list[str] = []
        for application in self.applications:
            found = [
                *_parameter_problems(
                    application.id, "input", application.bind, self.inputs, "bind"
                ),
                *_parameter_problems(
                    application.id, "output", application.produce, self.outputs, "produce"
                ),
            ]
            if not found:  # a given slug is judged only once the bindings themselves are complete
                bound = {value for value in application.bind.values() if isinstance(value, str)}
                found = [
                    f"application `{application.id}`: given {slug} is not bound by the application"
                    for slug in application.given or ()
                    if slug not in bound
                ]
            problems.extend(found)
        if problems:
            raise ValueError("; ".join(problems))
        unknown = set(self.optional) - self.inputs.keys()
        if unknown:
            msg = f"optional names parameters that are no input: {sorted(unknown)}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_checks(self) -> Self:
        """Require preconditions on inputs, postconditions on outputs, unique ids, known applications."""
        ids = {application.id for application in self.applications}
        for label, checks, side in (
            ("precondition", self.preconditions, self.inputs),
            ("postcondition", self.postconditions, self.outputs),
        ):
            check_ids = [check.id for check in checks]
            if len(set(check_ids)) != len(check_ids):
                msg = f"{label} ids must be unique"
                raise ValueError(msg)
            for check in checks:
                if check.parameter not in side:
                    msg = f"{label} {check.id} names {check.parameter}, which is not on its side"
                    raise ValueError(msg)
                for application_id in check.applications or ():
                    if application_id not in ids:
                        msg = f"{label} {check.id} names unknown application {application_id}"
                        raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_worlds_and_embeds(self) -> Self:
        """Tie worlds to interval uncertainty, variables to embeds, and embeds to their closure."""
        if (self.uncertainty == "interval") != bool(self.worlds):
            msg = "worlds are required exactly with uncertainty: interval"
            raise ValueError(msg)
        if self.worlds and (len(self.worlds) < 2 or len(set(self.worlds)) != len(self.worlds)):
            msg = "worlds must be at least two and unique"
            raise ValueError(msg)
        if bool(self.variables) != bool(self.embeds):
            msg = "variables are required exactly with embeds"
            raise ValueError(msg)
        if bool(self.embeds_closure) != bool(self.embeds) or not set(self.embeds) <= set(
            self.embeds_closure
        ):
            msg = "embeds_closure must exist exactly with embeds and contain them"
            raise ValueError(msg)
        if list(self.embeds_closure) != sorted(set(self.embeds_closure)):
            msg = "embeds_closure must be sorted and unique"
            raise ValueError(msg)
        return self


# --- the model ------------------------------------------------------------------------------

# Dict keys inside a namespace are bare slugs; namespace names are lower-case identifiers.
SlugKey = Annotated[str, _anchored(SLUG_REGEX)]
NamespaceKey = Annotated[str, _anchored(NAMESPACE_REGEX)]


class Namespace(BaseModel):
    """One canon of the model: its quantities, formulas and defaults, keyed by bare slug.

    Attributes:
        quantities: The quantity vocabulary.
        formulas: The formulas.
        defaults: The stated default per supplied scalar quantity; absent = the caller must supply it.
        taxonomy: The vocabulary of the tag families, with the world-to-tool mapping.
    """

    model_config = _MODEL_CONFIG

    quantities: dict[SlugKey, Quantity]
    formulas: dict[SlugKey, Formula]
    defaults: dict[SlugKey, Default] = {}
    taxonomy: Taxonomy = Taxonomy()


def _default_problem(where: str, default: Default, quantity: Quantity | None) -> str | None:
    """Return what is wrong with a default against its quantity, or ``None``."""
    if quantity is None:
        return f"default of unknown quantity {where}"
    if quantity.role not in ("input", "target"):
        return f"default of {where}: role must be input or target, not {quantity.role}"
    if quantity.type != "scalar":
        return f"default of {where}: quantity must be a scalar, not {quantity.type}"
    if default.unit != quantity.unit:
        return (
            f"default of {where}: unit {default.unit} differs from the quantity's {quantity.unit}"
        )
    if quantity.positive and default.value <= 0:
        return f"default of positive quantity {where} must be > 0"
    if quantity.at_most is not None and default.value > quantity.at_most:
        return f"default of {where} exceeds its at_most {quantity.at_most}"
    return None


def compute_content_hash(namespaces: Mapping[str, Namespace]) -> str:
    """Hash the canon's content: ``"sha256:"`` plus the hex SHA-256 of the canonical JSON.

    Only the namespaces enter; provenance (``importer_version``) and the hash itself do not, so
    identical content hashes alike whatever importer version wrote it.

    Args:
        namespaces: The namespaces of a model.

    Returns:
        The prefixed hex digest.
    """
    return sha256_of({name: ns.model_dump(mode="json") for name, ns in namespaces.items()})


def _split(reference: str) -> tuple[str, str]:
    """Split ``<namespace>:<slug>``; a bare slug belongs to the default namespace."""
    namespace, separator, slug = reference.partition(":")
    if not separator:
        return DEFAULT_NAMESPACE, reference
    return namespace, slug


class CanonProblem(TypedDict):
    """One problem of a whole-model rule, located for the importer (carried in the error context).

    Attributes:
        namespace: Namespace of the entry.
        section: ``formulas`` or ``defaults``.
        slug: Slug of the entry.
        field: Field of the entry, e.g. ``applications[1].bind.m``; empty for the whole entry.
        side: ``inputs`` or ``outputs`` for a formula-level default, ``bind`` or ``produce`` for an
            application's binding; ``None`` elsewhere.
        application: Index of the application for ``bind`` and ``produce``; ``None`` elsewhere.
        parameter: The parameter for ``side``; ``None`` elsewhere.
        text: What is wrong.
    """

    namespace: str
    section: Literal["formulas", "defaults"]
    slug: str
    field: str
    side: Literal["inputs", "outputs", "bind", "produce"] | None
    application: int | None
    parameter: str | None
    text: str


def _describe(problem: CanonProblem) -> str:
    """Render a problem as the one-line message a plain ``str(error)`` shows."""
    if problem["section"] == "defaults":
        return problem["text"]
    return f"{problem['namespace']}:{problem['slug']}: {problem['text']}"


def _canon_error(problems: list[CanonProblem]) -> PydanticCustomError:
    """Build the validation error of a whole-model rule; the problems travel in its context."""
    summary = "; ".join(_describe(problem) for problem in problems)
    return PydanticCustomError(
        "canon_problems", "{summary}", {"summary": summary, "problems": problems}
    )


class _Reference(NamedTuple):
    """One reference a formula holds, with where it is written."""

    field: str
    kind: str
    reference: str
    side: Literal["inputs", "outputs", "bind", "produce"] | None = None
    application: int | None = None
    parameter: str | None = None


def _references(formula: Formula) -> Iterator[_Reference]:
    """Yield every reference the formula holds: ``quantity``, ``given`` or ``embed``."""
    for name, default in formula.inputs.items():
        if default is not None:
            yield _Reference(f"inputs.{name}", "quantity", default, "inputs", None, name)
    for name, default in formula.outputs.items():
        if default is not None:
            yield _Reference(f"outputs.{name}", "quantity", default, "outputs", None, name)
    for index, application in enumerate(formula.applications):
        where = f"applications[{index}]"
        for name, binding in application.bind.items():
            if isinstance(binding, str):
                yield _Reference(f"{where}.bind.{name}", "quantity", binding, "bind", index, name)
        for name, produced in application.produce.items():
            if produced is not None:
                yield _Reference(
                    f"{where}.produce.{name}", "quantity", produced, "produce", index, name
                )
        for position, slug in enumerate(application.given or ()):
            yield _Reference(f"{where}.given[{position}]", "given", slug)
    for position, slug in enumerate(formula.variables):
        yield _Reference(f"variables[{position}]", "quantity", slug)
    for name, items in (("embeds", formula.embeds), ("embeds_closure", formula.embeds_closure)):
        for position, item in enumerate(items):
            yield _Reference(f"{name}[{position}]", "embed", item)


class CanonModel(BaseModel):
    """The interpreted canon the kernel runs on (ch. 8.9); the content of ``canon_model.json``.

    Attributes:
        schema_version: Version of this model shape; ``2``.
        content_hash: Hash of ``namespaces`` (see :func:`compute_content_hash`).
        importer_version: Version of the importer that wrote the model.
        namespaces: Quantities and formulas per namespace; every reference inside is qualified.
    """

    model_config = _MODEL_CONFIG

    schema_version: Literal[2]
    content_hash: Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
    importer_version: str = Field(min_length=1)
    namespaces: Annotated[dict[NamespaceKey, Namespace], Field(min_length=1)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _reject_bool_version(cls, value: object) -> object:
        """Reject ``true``: Python reads it as ``1``, JSON Schema does not."""
        if isinstance(value, bool):
            msg = "schema_version must be the integer 2, not a boolean"
            raise ValueError(msg)
        return value

    def quantity(self, reference: str) -> Quantity | None:
        """Look a quantity up by slug.

        Args:
            reference: ``<namespace>:<slug>``, or a bare slug, which means ``calc:``.

        Returns:
            The quantity, or ``None`` if the model has none.
        """
        namespace, slug = _split(reference)
        found = self.namespaces.get(namespace)
        return None if found is None else found.quantities.get(slug)

    def formula(self, reference: str) -> Formula | None:
        """Look a formula up by slug.

        Args:
            reference: ``<namespace>:<slug>``, or a bare slug, which means ``calc:``.

        Returns:
            The formula, or ``None`` if the model has none.
        """
        namespace, slug = _split(reference)
        found = self.namespaces.get(namespace)
        return None if found is None else found.formulas.get(slug)

    @model_validator(mode="after")
    def _check_hash(self) -> Self:
        """Reject a model whose content does not match its ``content_hash``."""
        expected = compute_content_hash(self.namespaces)
        if self.content_hash != expected:
            msg = f"content_hash {self.content_hash} does not match the content ({expected})"
            raise ValueError(msg)
        return self

    def tool_of(self, reference: str, world: str | None) -> Tool:
        """Return the tool that computes a formula, or one of its method worlds (ch. 8.4).

        A formula with worlds is computed by the tool its world names in the taxonomy; the
        formula's own ``tool`` is the tool of the formula as a whole and says nothing about which
        tool a world used.

        Args:
            reference: ``<namespace>:<slug>`` of the formula, or a bare slug (``calc:``).
            world: The world of the run, or ``None`` for a formula without worlds.

        Returns:
            The tool code.

        Raises:
            ValueError: If the formula does not exist, or ``world`` is not one of its worlds
                (a world must be given exactly for a formula that has worlds).
        """
        namespace, slug = _split(reference)
        formula = self.formula(reference)
        if formula is None:
            msg = f"no formula {reference}"
            raise ValueError(msg)
        if world is None and not formula.worlds:
            return formula.tool
        if world is None or world not in formula.worlds:
            msg = f"formula {reference} has no world {world!r}"
            raise ValueError(msg)
        tools: dict[str, Tool] = {w.id: w.tool for w in self.namespaces[namespace].taxonomy.worlds}
        tool = tools.get(world)
        if tool is None:
            msg = f"world {world!r} of {namespace}:{slug} has no tool in the taxonomy"
            raise ValueError(msg)
        return tool

    @model_validator(mode="after")
    def _check_worlds(self) -> Self:
        """Require the taxonomy to state the tool of every world of every formula (ch. 8.4)."""
        problems: list[CanonProblem] = []
        for namespace, content in self.namespaces.items():
            stated = {world.id for world in content.taxonomy.worlds}
            for slug, formula in content.formulas.items():
                problems.extend(
                    CanonProblem(
                        namespace=namespace,
                        section="formulas",
                        slug=slug,
                        field=f"worlds[{position}]",
                        side=None,
                        application=None,
                        parameter=None,
                        text=f"world {world!r} has no tool in the taxonomy",
                    )
                    for position, world in enumerate(formula.worlds)
                    if world not in stated
                )
        if problems:
            raise _canon_error(problems)
        return self

    def _check_embed(self, item: str) -> str | None:
        """Return the problem with an embedded ``<ns>:<slug>.<application-id>``, if any."""
        reference, _, application_id = item.rpartition(".")
        formula = self.formula(reference)
        if formula is None:
            return f"embeds {item}, but formula {reference} does not exist"
        if all(application.id != application_id for application in formula.applications):
            return f"embeds {item}, but the formula has no such application"
        return None

    def _check_given(self, reference: str) -> str | None:
        """Return the problem with a ``given`` slug, if any: it must be a supplied, default-less one."""
        quantity = self.quantity(reference)
        if quantity is None:
            return f"unknown quantity {reference}"
        namespace, slug = _split(reference)
        if quantity.role not in ("input", "target") or slug in self.namespaces[namespace].defaults:
            return f"given {reference} must be an input or target without default"
        return None

    @model_validator(mode="after")
    def _check_defaults(self) -> Self:
        """Require every default to belong to a supplied scalar of the same unit, > 0 if positive."""
        problems: list[CanonProblem] = []
        for namespace, content in self.namespaces.items():
            for slug, default in content.defaults.items():
                quantity = content.quantities.get(slug)
                text = _default_problem(f"{namespace}:{slug}", default, quantity)
                if text is not None:
                    problems.append(
                        CanonProblem(
                            namespace=namespace,
                            section="defaults",
                            slug=slug,
                            field="",
                            side=None,
                            application=None,
                            parameter=None,
                            text=text,
                        )
                    )
        if problems:
            raise _canon_error(problems)
        return self

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        """Require every reference of every formula to resolve."""
        problems: list[CanonProblem] = []
        for namespace, content in self.namespaces.items():
            for slug, formula in content.formulas.items():
                for found in _references(formula):
                    reference = found.reference
                    if found.kind == "embed":
                        text = self._check_embed(reference)
                    elif found.kind == "given":
                        text = self._check_given(reference)
                    else:
                        text = None if self.quantity(reference) else f"unknown quantity {reference}"
                    if text is not None:
                        problems.append(
                            CanonProblem(
                                namespace=namespace,
                                section="formulas",
                                slug=slug,
                                field=found.field,
                                side=found.side,
                                application=found.application,
                                parameter=found.parameter,
                                text=text,
                            )
                        )
        if problems:
            raise _canon_error(problems)
        return self
