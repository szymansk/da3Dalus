"""Canon-model types (ARCHITECTURE ch. 8.9): the interpreted canon the kernel runs on.

Every field mirrors the canon README section "Machine-readable fields" one to one, normalised as
ch. 8.9 says. All models are frozen, reject unknown fields and carry their invariants themselves:
they are canon-model types, not input types.
"""

from collections.abc import Iterator, Mapping
from typing import Annotated, Literal, Self

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
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

__all__ = [
    "DEFAULT_NAMESPACE",
    "Application",
    "Binding",
    "CanonModel",
    "Check",
    "ConstBinding",
    "CostClass",
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

# Text the canon must state (a symbol, a source, a regime): at least one non-blank character.
NonBlank = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]

# Numbers in the model are finite (a model with NaN would not survive its JSON form).
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]

QuantityRole = Literal["input", "target", "derived", "output"]
QuantityType = Literal["scalar", "airplane", "components", "curve", "polar", "curve_pair"]

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
    "Pa",
    "kg/m^3",
    "W",
    "V",
    "A",
    "ohm",
    "Wh",
    "Wh/kg",
    "rpm/V",
]

_MODEL_CONFIG = ConfigDict(extra="forbid", frozen=True)


class Default(BaseModel):
    """A value the canon states for a supplied quantity, with its unit, source and regime.

    Attributes:
        value: The value, in ``unit``.
        unit: The unit of ``value``; it must equal the unit of the quantity.
        source: Citation of where the value comes from (ADR 0028).
        regime: The flight regime the value is valid for (ADR 0028).
    """

    model_config = _MODEL_CONFIG

    value: FiniteNumber
    unit: Unit
    source: NonBlank
    regime: NonBlank


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
    """

    model_config = _MODEL_CONFIG

    symbol: NonBlank
    unit: Unit
    role: QuantityRole
    type: QuantityType
    uncertainty: Literal["interval"] | None = None
    positive: Literal[True] | None = None

    @model_validator(mode="after")
    def _check_positive(self) -> Self:
        """Allow ``positive`` only on supplied scalars."""
        if self.positive is None:
            return self
        if self.role not in ("input", "target"):
            msg = f"positive is only allowed on role input or target, not {self.role}"
            raise ValueError(msg)
        if self.type != "scalar":
            msg = f"positive is only allowed on a scalar quantity, not {self.type}"
            raise ValueError(msg)
        return self


# --- formulas -------------------------------------------------------------------------------

FormulaKind = Literal["law", "procedure", "optimization", "fit", "rating"]
Tool = Literal["APP", "ATM", "GEO", "AB", "AVL", "OPT", "KAT", "APC"]
CostClass = Literal["instant", "seconds", "minutes"]
WhenTerm = Literal[
    "has_aileron", "has_horizontal_tail", "has_separate_flap_and_aileron", "has_vertical_tail"
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


Binding = QualifiedSlug | ConstBinding


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
    """

    model_config = _MODEL_CONFIG

    id: Identifier
    bind: dict[Parameter, Binding]
    produce: dict[Parameter, QualifiedSlug | None]
    when: WhenTerm | None = None
    given: Annotated[tuple[QualifiedSlug, ...], Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _check_given_is_bound(self) -> Self:
        """Require every ``given`` slug to be bound by this application."""
        bound = {value for value in self.bind.values() if isinstance(value, str)}
        for slug in self.given or ():
            if slug not in bound:
                msg = f"application {self.id}: given {slug} is not bound by the application"
                raise ValueError(msg)
        return self


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
        for application in self.applications:
            if application.bind.keys() != self.inputs.keys():
                msg = f"application {application.id}: bind must name exactly the input parameters"
                raise ValueError(msg)
            if application.produce.keys() != self.outputs.keys():
                msg = (
                    f"application {application.id}: produce must name exactly the output parameters"
                )
                raise ValueError(msg)
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
    """

    model_config = _MODEL_CONFIG

    quantities: dict[SlugKey, Quantity]
    formulas: dict[SlugKey, Formula]
    defaults: dict[SlugKey, Default] = {}


def compute_content_hash(namespaces: Mapping[str, Namespace]) -> str:
    """Hash the canon's content: ``"sha256:"`` plus the hex SHA-256 of the canonical JSON.

    Only the namespaces enter; provenance (``source_commit``, ``importer_version``) and the hash
    itself do not, so identical content hashes alike whatever commit it was imported from.

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


def _references(formula: Formula) -> Iterator[tuple[str, str]]:
    """Yield every ``(kind, reference)`` the formula holds: ``quantity``, ``given`` or ``embed``."""
    for default in (*formula.inputs.values(), *formula.outputs.values()):
        if default is not None:
            yield "quantity", default
    for application in formula.applications:
        for binding in application.bind.values():
            if isinstance(binding, str):
                yield "quantity", binding
        for produced in application.produce.values():
            if produced is not None:
                yield "quantity", produced
        for slug in application.given or ():
            yield "given", slug
    for slug in formula.variables:
        yield "quantity", slug
    for item in (*formula.embeds, *formula.embeds_closure):
        yield "embed", item


class CanonModel(BaseModel):
    """The interpreted canon the kernel runs on (ch. 8.9); the content of ``canon_model.json``.

    Attributes:
        schema_version: Version of this model shape; ``1``.
        content_hash: Hash of ``namespaces`` (see :func:`compute_content_hash`).
        source_commit: Commit of the canon document the model was imported from.
        importer_version: Version of the importer that wrote the model.
        namespaces: Quantities and formulas per namespace; every reference inside is qualified.
    """

    model_config = _MODEL_CONFIG

    schema_version: Literal[1]
    content_hash: Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
    source_commit: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    importer_version: str = Field(min_length=1)
    namespaces: Annotated[dict[NamespaceKey, Namespace], Field(min_length=1)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _reject_bool_version(cls, value: object) -> object:
        """Reject ``true``: Python reads it as ``1``, JSON Schema does not."""
        if isinstance(value, bool):
            msg = "schema_version must be the integer 1, not a boolean"
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
        problems: list[str] = []
        for namespace, content in self.namespaces.items():
            for slug, default in content.defaults.items():
                quantity = content.quantities.get(slug)
                where = f"{namespace}:{slug}"
                if quantity is None:
                    problems.append(f"default of unknown quantity {where}")
                elif quantity.role not in ("input", "target"):
                    problems.append(
                        f"default of {where}: role must be input or target, not {quantity.role}"
                    )
                elif quantity.type != "scalar":
                    problems.append(
                        f"default of {where}: quantity must be a scalar, not {quantity.type}"
                    )
                elif default.unit != quantity.unit:
                    problems.append(
                        f"default of {where}: unit {default.unit} differs from the quantity's {quantity.unit}"
                    )
                elif quantity.positive and default.value <= 0:
                    problems.append(f"default of positive quantity {where} must be > 0")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        """Require every reference of every formula to resolve."""
        problems: list[str] = []
        for namespace, content in self.namespaces.items():
            for slug, formula in content.formulas.items():
                for kind, reference in _references(formula):
                    if kind == "embed":
                        problem = self._check_embed(reference)
                    elif kind == "given":
                        problem = self._check_given(reference)
                    else:
                        problem = (
                            None if self.quantity(reference) else f"unknown quantity {reference}"
                        )
                    if problem is not None:
                        problems.append(f"{namespace}:{slug}: {problem}")
        if problems:
            raise ValueError("; ".join(dict.fromkeys(problems)))
        return self
