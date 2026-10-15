"""Registry of formula implementations and checks (ARCHITECTURE ch. 8.12).

Implementations and checks are linked to the canon model by decorator: ``@formula(slug,
interface=...)``, ``@relation(slug)``, ``@precondition(slug, id)`` and ``@postcondition(slug, id)``.
The registry holds code only, never call state: it is filled at import of ``aero_kernel.formulas``
and then frozen.
"""

import inspect
import logging
import re
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass
from typing import TypeVar

from aero_kernel.canon.model import DEFAULT_NAMESPACE
from aero_kernel.errors import SLUG_REGEX

logger = logging.getLogger(__name__)

__all__ = ["Implementation", "Registry", "RegistryError"]

# ``object`` stands for the engine's value types (ch. 8.12): the registry never looks at a value, and
# a narrower parameter annotation on a formula must stay assignable.
FormulaFunction = Callable[..., Coroutine[object, object, Mapping[str, object]]]
_FormulaT = TypeVar("_FormulaT", bound=FormulaFunction)

_SLUG_PATTERN = re.compile(rf"(?:(?P<namespace>[a-z][a-z0-9_]*):)?(?P<slug>{SLUG_REGEX})")
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


class Registry:
    """The implementations and checks of a kernel, linked to the canon model by slug."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._implementations: dict[str, Implementation] = {}

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
        qualified = _qualify(slug)
        if _FINGERPRINT_PATTERN.fullmatch(interface) is None:
            msg = f"malformed interface fingerprint {interface!r} for {qualified}"
            raise RegistryError(msg)

        def register(func: _FormulaT) -> _FormulaT:
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
