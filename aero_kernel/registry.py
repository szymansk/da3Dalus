"""Registry of formula implementations and checks (ARCHITECTURE ch. 8.12).

Implementations and checks are linked to the canon model by decorator: ``@formula(slug,
interface=...)``, ``@relation(slug)``, ``@precondition(slug, id)`` and ``@postcondition(slug, id)``.
The registry holds code only, never call state: it is filled at import of ``aero_kernel.formulas``
and then frozen.
"""

import argparse
import inspect
import logging
import re
import sys
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from aero_kernel.canon.load import CanonLoadError, load_canon_model
from aero_kernel.canon.model import DEFAULT_NAMESPACE, Formula
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
