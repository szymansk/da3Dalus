"""Registry of formula implementations and checks (ARCHITECTURE ch. 8.12).

Implementations and checks are linked to the canon model by decorator: ``@formula(slug,
interface=...)``, ``@relation(slug)``, ``@precondition(slug, id)`` and ``@postcondition(slug, id)``.
The registry holds code only, never call state: it is filled at import of ``aero_kernel.formulas``
and then frozen.
"""

import argparse
import ast
import inspect
import logging
import re
import sys
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from aero_kernel.canon.load import CanonLoadError, load_canon_model
from aero_kernel.canon.model import DEFAULT_NAMESPACE, CanonModel, Check, Formula
from aero_kernel.canonical import sha256_of
from aero_kernel.errors import SLUG_REGEX
from pydantic import BaseModel, ConfigDict, Field, JsonValue

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_REGISTRY",
    "CheckResult",
    "Implementation",
    "Registry",
    "RegistryError",
    "RegistryFinding",
    "check_registry",
    "formula",
    "interface_fingerprint",
    "main",
    "postcondition",
    "precondition",
    "relation",
]


class CheckResult(BaseModel):
    """The outcome of a pre- or postcondition (ch. 8.5).

    Attributes:
        state: ``held``, ``violated`` or ``unchecked``.
        message: What was found, for the warning or error the engine builds.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["held", "violated", "unchecked"]
    message: str = Field(min_length=1)


# ``object`` stands for the engine's value types (ch. 8.12): the registry never looks at a value, and
# a narrower parameter annotation on a formula must stay assignable.
FormulaFunction = Callable[..., Coroutine[object, object, Mapping[str, object]]]
_FormulaT = TypeVar("_FormulaT", bound=FormulaFunction)
_FunctionT = TypeVar("_FunctionT", bound=Callable[..., object])
_CheckT = TypeVar("_CheckT", bound=Callable[..., CheckResult])
CheckKind = Literal["pre", "post"]

_SLUG_PATTERN = re.compile(rf"(?:(?P<namespace>[a-z][a-z0-9_]*):)?(?P<slug>{SLUG_REGEX})")
_CHECK_ID_PATTERN = re.compile(r"[a-z][a-z0-9]*([_-][a-z0-9]+)*")
_FINGERPRINT_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


class RegistryError(Exception):
    """A programming error at registration: duplicate, non-coroutine, malformed name, frozen.

    Raised at import; it never becomes a computation result.
    """


@dataclass(frozen=True)
class Implementation:
    """A registered formula implementation.

    Attributes:
        slug: Qualified formula slug, ``<namespace>:<slug>``.
        func: The coroutine ``f(x, ctx) -> dict``.
        interface: Interface fingerprint of the canon formula the code was written against.
    """

    slug: str
    func: FormulaFunction
    interface: str


def _qualify(slug: str) -> str:
    """Return the qualified form of a formula slug; a bare slug belongs to ``calc``."""
    match = _SLUG_PATTERN.fullmatch(slug)
    if match is None:
        msg = f"malformed formula slug {slug!r}: expected '[<namespace>:]<kebab-case-slug>'"
        raise RegistryError(msg)
    return f"{match['namespace'] or DEFAULT_NAMESPACE}:{match['slug']}"


def interface_fingerprint(formula: Formula) -> str:
    """Fingerprint the interface of a canon formula: what an implementation is written against.

    Args:
        formula: A formula of the canon model.

    Returns:
        ``"sha256:"`` plus the hex digest of the sorted input names, output names and ``optional``
        parameters. The value goes into ``@formula(slug, interface=...)``.
    """
    interface: dict[str, JsonValue] = {
        "inputs": list[JsonValue](sorted(formula.inputs)),
        "outputs": list[JsonValue](sorted(formula.outputs)),
        "optional": list[JsonValue](sorted(formula.optional)),
    }
    return sha256_of(interface)


class Registry:
    """The implementations and checks of a kernel, linked to the canon model by slug."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._implementations: dict[str, Implementation] = {}
        self._relations: dict[str, Callable[..., object]] = {}
        self._checks: dict[tuple[str, CheckKind], dict[str, Callable[..., CheckResult]]] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        """Whether the registry is frozen: no further registration is possible."""
        return self._frozen

    def freeze(self) -> None:
        """Freeze the registry: any later registration raises ``RegistryError``.

        Called by ``aero_kernel.formulas`` once every formula module is imported. Freezing again
        does nothing.
        """
        if self._frozen:
            return
        self._frozen = True
        logger.info(
            "registry frozen: %s formulas, %s checks",
            len(self._implementations),
            sum(len(checks) for checks in self._checks.values()),
        )

    def _ensure_open(self) -> None:
        """Raise ``RegistryError`` if the registry is frozen."""
        if self._frozen:
            msg = (
                "the registry is frozen; formulas are registered at import of aero_kernel.formulas"
            )
            raise RegistryError(msg)

    def formula(self, slug: str, interface: str) -> Callable[[_FormulaT], _FormulaT]:
        """Register the decorated coroutine as the one implementation of a formula.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.
            interface: Interface fingerprint of the canon formula (see ``interface_fingerprint``).

        Returns:
            The decorator; it returns the function unchanged.

        Raises:
            RegistryError: If the slug or fingerprint is malformed.
        """
        self._ensure_open()
        qualified = _qualify(slug)
        if _FINGERPRINT_PATTERN.fullmatch(interface) is None:
            msg = f"malformed interface fingerprint {interface!r} for {qualified}"
            raise RegistryError(msg)

        def register(func: _FormulaT) -> _FormulaT:
            self._ensure_open()
            if not inspect.iscoroutinefunction(func):
                msg = f"implementation of {qualified} must be a coroutine function (async def)"
                raise RegistryError(msg)
            if qualified in self._implementations:
                msg = f"formula {qualified} already has an implementation"
                raise RegistryError(msg)
            self._implementations[qualified] = Implementation(qualified, func, interface)
            logger.debug("registered formula %s", qualified)
            return func

        return register

    def slugs(self) -> frozenset[str]:
        """Return the qualified slugs of every formula with any registration."""
        return frozenset(
            [*self._implementations, *self._relations, *(slug for slug, _ in self._checks)]
        )

    def implementation(self, slug: str) -> Implementation | None:
        """Look the implementation of a formula up.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.

        Returns:
            The implementation, or ``None`` (the engine answers ``not_implemented``).
        """
        return self._implementations.get(_qualify(slug))

    def relation(self, slug: str) -> Callable[[_FunctionT], _FunctionT]:
        """Register the decorated function as the embeddable relation of a formula (ch. 8.5).

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.

        Returns:
            The decorator; it returns the function unchanged.

        Raises:
            RegistryError: If the slug is malformed or the registry is frozen.
        """
        self._ensure_open()
        qualified = _qualify(slug)

        def register(func: _FunctionT) -> _FunctionT:
            self._ensure_open()
            if qualified in self._relations:
                msg = f"formula {qualified} already has a relation"
                raise RegistryError(msg)
            self._relations[qualified] = func
            logger.debug("registered relation %s", qualified)
            return func

        return register

    def relation_function(self, slug: str) -> Callable[..., object] | None:
        """Look the embeddable relation of a formula up.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.

        Returns:
            The relation function, or ``None``.
        """
        return self._relations.get(_qualify(slug))

    def precondition(self, slug: str, check_id: str) -> Callable[[_CheckT], _CheckT]:
        """Register a check on the formula's inputs, run before the implementation.

        Decorators stack: one function can serve several ``(slug, id)`` pairs.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.
            check_id: Id of the precondition in the canon model.

        Returns:
            The decorator for ``def check(x) -> CheckResult``; it returns the function unchanged.
        """
        return self._check_decorator(slug, "pre", check_id, arity=1)

    def postcondition(self, slug: str, check_id: str) -> Callable[[_CheckT], _CheckT]:
        """Register a check on the formula's outputs, run after the implementation.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.
            check_id: Id of the postcondition in the canon model.

        Returns:
            The decorator for ``def check(x, y) -> CheckResult``; it returns the function unchanged.
        """
        return self._check_decorator(slug, "post", check_id, arity=2)

    def checks(self, slug: str, kind: CheckKind) -> Mapping[str, Callable[..., CheckResult]]:
        """Return the registered checks of one kind of a formula.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.
            kind: ``pre`` or ``post``.

        Returns:
            Check function per check id; empty if none is registered.
        """
        return dict(self._checks.get((_qualify(slug), kind), {}))

    def _check_decorator(
        self, slug: str, kind: CheckKind, check_id: str, *, arity: int
    ) -> Callable[[_CheckT], _CheckT]:
        """Build the decorator that registers a check of ``kind`` taking ``arity`` parameters."""
        self._ensure_open()
        qualified = _qualify(slug)
        if _CHECK_ID_PATTERN.fullmatch(check_id) is None:
            msg = f"malformed check id {check_id!r} for {qualified}: expected kebab- or snake-case"
            raise RegistryError(msg)
        label = "precondition" if kind == "pre" else "postcondition"

        def register(func: _CheckT) -> _CheckT:
            self._ensure_open()
            if inspect.iscoroutinefunction(func):
                msg = f"{label} {qualified}/{check_id} must be a plain function, not a coroutine"
                raise RegistryError(msg)
            if len(inspect.signature(func).parameters) != arity:
                msg = f"{label} {qualified}/{check_id} must take exactly {arity} parameter(s)"
                raise RegistryError(msg)
            registered = self._checks.setdefault((qualified, kind), {})
            if check_id in registered:
                msg = f"{label} {check_id} of {qualified} is already registered"
                raise RegistryError(msg)
            registered[check_id] = func
            logger.debug("registered %s %s/%s", label, qualified, check_id)
            return func

        return register


DEFAULT_REGISTRY = Registry()
"""The registry ``aero_kernel.formulas`` fills at import and then freezes."""

formula = DEFAULT_REGISTRY.formula
relation = DEFAULT_REGISTRY.relation
precondition = DEFAULT_REGISTRY.precondition
postcondition = DEFAULT_REGISTRY.postcondition


FindingCode = Literal[
    "unknown_formula",
    "unknown_check",
    "stale_implementation",
    "missing_relation",
    "embedded_item_not_requested",
]


class RegistryFinding(BaseModel):
    """A mismatch between the registry and the canon model; a test or CI finding, not a result error.

    Attributes:
        code: What is wrong.
        slug: Qualified slug of the formula concerned.
        check_id: Id of the check concerned, if any.
        message: The mismatch, in natural language.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: FindingCode
    slug: str
    check_id: str | None = None
    message: str = Field(min_length=1)


def _requested_items(func: Callable[..., object]) -> set[str] | None:
    """Return the qualified items a module requests via ``ctx.embedded("...")``, or ``None``.

    The scan covers the whole module of ``func``, so a helper of the formula may make the call.
    ``None`` means the module's source is not available.
    """
    try:
        source = inspect.getsource(inspect.getmodule(func) or func)
    except (OSError, TypeError):
        return None
    items: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "embedded"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            reference, _, application = node.args[0].value.rpartition(".")
            try:
                items.add(f"{_qualify(reference)}.{application}")
            except RegistryError:
                continue  # not a reference at all; it cannot match an ``embeds`` item
    return items


def _finding(
    code: FindingCode, slug: str, message: str, check_id: str | None = None
) -> RegistryFinding:
    """Build a finding."""
    return RegistryFinding(code=code, slug=slug, check_id=check_id, message=message)


def _check_embeds(
    registry: Registry, model: CanonModel, slug: str, implementation: Implementation
) -> list[RegistryFinding]:
    """Check the embeds of an implemented formula: relations registered, items requested."""
    formula = model.formula(slug)
    if formula is None or not formula.embeds:
        return []
    findings: list[RegistryFinding] = []
    for item in sorted({item.rpartition(".")[0] for item in formula.embeds_closure}):
        if registry.relation_function(item) is None:
            msg = f"{slug} embeds {item}, which has no registered relation"
            findings.append(_finding("missing_relation", slug, msg))
    requested = _requested_items(implementation.func)
    for item in formula.embeds:
        if requested is None or item not in requested:
            reason = "its module source is not available" if requested is None else "not requested"
            msg = f"{slug} embeds {item}, but its implementation does not request it via ctx.embedded ({reason})"
            findings.append(_finding("embedded_item_not_requested", slug, msg))
    return findings


def check_registry(registry: Registry, model: CanonModel) -> tuple[RegistryFinding, ...]:
    """Check the registry against the canon model (traceability, tests Q1 and Q11).

    Reports a registered slug or check id the model does not have, an implementation written
    against another interface, and, for an implemented embedder, an embedded formula without a
    registered relation or an embedded item the module never requests through ``ctx.embedded``.
    A model formula without implementation is no finding: the engine answers ``not_implemented``.

    Args:
        registry: The registry to check.
        model: The canon model.

    Returns:
        The findings, sorted by slug, code and check id; empty if the registry is consistent.
    """
    findings: list[RegistryFinding] = []
    for slug in sorted(registry.slugs()):
        formula = model.formula(slug)
        if formula is None:
            findings.append(_finding("unknown_formula", slug, f"the model has no formula {slug}"))
            continue
        sides: tuple[tuple[CheckKind, str, tuple[Check, ...]], ...] = (
            ("pre", "precondition", formula.preconditions),
            ("post", "postcondition", formula.postconditions),
        )
        for kind, label, known in sides:
            known_ids = {check.id for check in known}
            for check_id in sorted(registry.checks(slug, kind)):
                if check_id not in known_ids:
                    msg = f"{slug} has no {label} {check_id}"
                    findings.append(_finding("unknown_check", slug, msg, check_id))
        implementation = registry.implementation(slug)
        if implementation is None:
            continue
        if implementation.interface != interface_fingerprint(formula):
            msg = f"the implementation of {slug} was written against another interface than the model's"
            findings.append(_finding("stale_implementation", slug, msg))
        findings.extend(_check_embeds(registry, model, slug, implementation))
    return tuple(sorted(findings, key=lambda f: (f.slug, f.code, f.check_id or "")))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line: ``fingerprint <model.json> <slug>`` prints a formula's fingerprint.

    Args:
        argv: Arguments; ``None`` means ``sys.argv[1:]``.

    Returns:
        The exit code: 0, or 2 if the model cannot be loaded or has no such formula.
    """
    parser = argparse.ArgumentParser(prog="python -m aero_kernel.registry")
    commands = parser.add_subparsers(dest="command", required=True)
    fingerprint = commands.add_parser("fingerprint", help="print a formula's interface fingerprint")
    fingerprint.add_argument("model", help="path of a canon model JSON file")
    fingerprint.add_argument("slug", help="formula slug, bare or '<namespace>:<slug>'")
    arguments = parser.parse_args(argv)
    model_path = Path(str(arguments.model))
    slug = str(arguments.slug)
    try:
        model = load_canon_model(model_path)
    except CanonLoadError as error:
        print(error.error.message, file=sys.stderr)
        return 2
    found = model.formula(slug)
    if found is None:
        print(f"the model has no formula {slug}", file=sys.stderr)
        return 2
    print(interface_fingerprint(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
