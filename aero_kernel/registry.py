"""Registry of formula implementations and checks (ARCHITECTURE ch. 8.12).

Implementations and checks are linked to the canon model by decorator: ``@formula(slug,
interface=...)``, ``@precondition(slug, id)`` and ``@postcondition(slug, id)``.
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
from aero_kernel.canon.model import DEFAULT_NAMESPACE, CanonModel, Check, Formula
from aero_kernel.canonical import sha256_of
from aero_kernel.errors import SLUG_REGEX
from pydantic import BaseModel, ConfigDict, Field, JsonValue

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_REGISTRY",
    "CheckResult",
    "Implementation",
    "RegistrationError",
    "Registry",
    "RegistryFinding",
    "TraceabilityReport",
    "formula",
    "interface_fingerprint",
    "main",
    "postcondition",
    "precondition",
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


class RegistrationError(Exception):
    """A programming error at registration: duplicate, non-coroutine, malformed name, frozen.

    Raised at import; it never becomes a computation result.
    """


FindingKind = Literal[
    "unknown_formula", "unknown_check", "check_kind_mismatch", "stale_implementation"
]


class RegistryFinding(BaseModel):
    """A mismatch between the registry and the canon model; a test or CI finding, not a result error.

    Attributes:
        kind: What is wrong.
        slug: Qualified slug of the formula concerned.
        check_id: Id of the check concerned, if any.
        message: The mismatch, in natural language.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: FindingKind
    slug: str
    check_id: str | None = None
    message: str = Field(min_length=1)


class TraceabilityReport(BaseModel):
    """The result of checking a registry against a canon model (tests Q1, Q11).

    Attributes:
        findings: The mismatches, sorted by slug, kind and check id.
        not_implemented: Qualified slugs of the model formulas without implementation, sorted. They
            are no findings: the engine answers ``not_implemented`` for them (Q1).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: tuple[RegistryFinding, ...]
    not_implemented: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Whether the registry matches the model: there are no findings."""
        return not self.findings


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
        raise RegistrationError(msg)
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
        self._checks: dict[tuple[str, CheckKind], dict[str, Callable[..., CheckResult]]] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        """Whether the registry is frozen: no further registration is possible."""
        return self._frozen

    def freeze(self) -> None:
        """Freeze the registry: any later registration raises ``RegistrationError``.

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
        """Raise ``RegistrationError`` if the registry is frozen."""
        if self._frozen:
            msg = (
                "the registry is frozen; formulas are registered at import of aero_kernel.formulas"
            )
            raise RegistrationError(msg)

    def formula(self, slug: str, interface: str) -> Callable[[_FormulaT], _FormulaT]:
        """Register the decorated coroutine as the one implementation of a formula.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.
            interface: Interface fingerprint of the canon formula (see ``interface_fingerprint``).

        Returns:
            The decorator; it returns the function unchanged.

        Raises:
            RegistrationError: If the slug or fingerprint is malformed.
        """
        self._ensure_open()
        qualified = _qualify(slug)
        if _FINGERPRINT_PATTERN.fullmatch(interface) is None:
            msg = f"malformed interface fingerprint {interface!r} for {qualified}"
            raise RegistrationError(msg)

        def register(func: _FormulaT) -> _FormulaT:
            self._ensure_open()
            if not inspect.iscoroutinefunction(func):
                msg = f"implementation of {qualified} must be a coroutine function (async def)"
                raise RegistrationError(msg)
            if len(inspect.signature(func).parameters) != 2:
                msg = f"implementation of {qualified} must take exactly 2 parameters (x, ctx)"
                raise RegistrationError(msg)
            if qualified in self._implementations:
                msg = f"formula {qualified} already has an implementation"
                raise RegistrationError(msg)
            self._implementations[qualified] = Implementation(qualified, func, interface)
            logger.debug("registered formula %s", qualified)
            return func

        return register

    def slugs(self) -> frozenset[str]:
        """Return the qualified slugs of every formula with any registration."""
        return frozenset([*self._implementations, *(slug for slug, _ in self._checks)])

    def implementation(self, slug: str) -> Implementation | None:
        """Look the implementation of a formula up.

        Args:
            slug: Formula slug; bare means the ``calc`` namespace.

        Returns:
            The implementation, or ``None`` (the engine answers ``not_implemented``).
        """
        return self._implementations.get(_qualify(slug))

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

    def check_traceability(self, model: CanonModel) -> TraceabilityReport:
        """Check the registry against the canon model (traceability, tests Q1 and Q11).

        Reports a registered slug the model does not have, a check id the formula does not have
        (or has on the other side), and an implementation written against another interface.

        Args:
            model: The canon model.

        Returns:
            The findings, and the model formulas that have no implementation.
        """
        findings: list[RegistryFinding] = []
        for slug in sorted(self.slugs()):
            formula = model.formula(slug)
            if formula is None:
                findings.append(
                    RegistryFinding(
                        kind="unknown_formula",
                        slug=slug,
                        message=f"the model has no formula {slug}",
                    )
                )
                continue
            findings.extend(self._check_checks(slug, formula))
            implementation = self.implementation(slug)
            if implementation is not None and implementation.interface != interface_fingerprint(
                formula
            ):
                msg = f"the implementation of {slug} was written against another interface than the model's"
                findings.append(
                    RegistryFinding(kind="stale_implementation", slug=slug, message=msg)
                )
        not_implemented = sorted(
            f"{namespace}:{slug}"
            for namespace, content in model.namespaces.items()
            for slug in content.formulas
            if self.implementation(f"{namespace}:{slug}") is None
        )
        findings.sort(key=lambda f: (f.slug, f.kind, f.check_id or ""))
        return TraceabilityReport(findings=tuple(findings), not_implemented=tuple(not_implemented))

    def _check_checks(self, slug: str, formula: Formula) -> list[RegistryFinding]:
        """Find the registered checks of a formula that the model does not have on that side."""
        findings: list[RegistryFinding] = []
        sides: tuple[tuple[CheckKind, str, str, tuple[Check, ...], tuple[Check, ...]], ...] = (
            ("pre", "precondition", "postcondition", formula.preconditions, formula.postconditions),
            (
                "post",
                "postcondition",
                "precondition",
                formula.postconditions,
                formula.preconditions,
            ),
        )
        for kind, label, other_label, own, other in sides:
            own_ids = {check.id for check in own}
            other_ids = {check.id for check in other}
            for check_id in sorted(self.checks(slug, kind)):
                if check_id in own_ids:
                    continue
                if check_id in other_ids:
                    msg = f"{slug} has {check_id} as a {other_label}, not as a {label}"
                    findings.append(
                        RegistryFinding(
                            kind="check_kind_mismatch", slug=slug, check_id=check_id, message=msg
                        )
                    )
                else:
                    msg = f"{slug} has no {label} {check_id}"
                    findings.append(
                        RegistryFinding(
                            kind="unknown_check", slug=slug, check_id=check_id, message=msg
                        )
                    )
        return findings

    def _check_decorator(
        self, slug: str, kind: CheckKind, check_id: str, *, arity: int
    ) -> Callable[[_CheckT], _CheckT]:
        """Build the decorator that registers a check of ``kind`` taking ``arity`` parameters."""
        self._ensure_open()
        qualified = _qualify(slug)
        if _CHECK_ID_PATTERN.fullmatch(check_id) is None:
            msg = f"malformed check id {check_id!r} for {qualified}: expected kebab- or snake-case"
            raise RegistrationError(msg)
        label = "precondition" if kind == "pre" else "postcondition"

        def register(func: _CheckT) -> _CheckT:
            self._ensure_open()
            if inspect.iscoroutinefunction(func):
                msg = f"{label} {qualified}/{check_id} must be a plain function, not a coroutine"
                raise RegistrationError(msg)
            if len(inspect.signature(func).parameters) != arity:
                msg = f"{label} {qualified}/{check_id} must take exactly {arity} parameter(s)"
                raise RegistrationError(msg)
            registered = self._checks.setdefault((qualified, kind), {})
            if check_id in registered:
                msg = f"{label} {check_id} of {qualified} is already registered"
                raise RegistrationError(msg)
            registered[check_id] = func
            logger.debug("registered %s %s/%s", label, qualified, check_id)
            return func

        return register


DEFAULT_REGISTRY = Registry()
"""The registry ``aero_kernel.formulas`` fills at import and then freezes."""

formula = DEFAULT_REGISTRY.formula
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
