"""Two-stage approval of the canon, derived (canon README "Two-stage approval", #1251).

Stage 1 is the formula's own ``status``, set by the maintainer. Stage 2 is derived here and never
set by hand, and it is transitive (maintainer, 2026-10-25: the whole chain must hold, or the value
cannot be computed): every input of the formula is either a supplied quantity with a ``data:`` source,
or produced by formulas that satisfy **both** stages themselves, recursively, embedded formulas
included. A quantity produced by a pure data read (a formula of tool ``KAT``) also needs a source
naming the catalogue field. A cause that blocks a formula is reported at its root, with the formulas
it passes through.
"""

from dataclasses import dataclass

from aero_kernel.canon.model import CanonModel, Namespace
from aero_kernel.errors import DEFAULT_NAMESPACE

__all__ = ["Approval", "FormulaApproval", "InputState", "derive_approval"]

_PREFIX = f"{DEFAULT_NAMESPACE}:"
UNMAPPED = "unmapped"


@dataclass(frozen=True)
class InputState:
    """One input of a formula and where its approval comes from.

    Attributes:
        quantity: The input's slug.
        mapped: Whether stage 2 holds for it.
        basis: What makes it hold (``produced by <formula>`` or the ``data`` sources), or what is
            missing (the draft producer, or ``no data source``).
    """

    quantity: str
    mapped: bool
    basis: str


@dataclass(frozen=True)
class FormulaApproval:
    """Both approval stages of one formula.

    Attributes:
        formula: The formula's slug.
        stage1: The formula's own status as written in its entry.
        inputs: Every input quantity with its stage-2 state, ordered by slug.
        embed_blockers: What blocks the formula through the formulas it embeds, as root causes.
    """

    formula: str
    stage1: str
    inputs: tuple[InputState, ...]
    embed_blockers: tuple[str, ...] = ()

    @property
    def mapped(self) -> int:
        """The number of inputs for which stage 2 holds."""
        return sum(state.mapped for state in self.inputs)

    @property
    def total(self) -> int:
        """The number of inputs."""
        return len(self.inputs)

    @property
    def missing(self) -> tuple[InputState, ...]:
        """The inputs for which stage 2 does not hold."""
        return tuple(state for state in self.inputs if not state.mapped)

    @property
    def fully_approved(self) -> bool:
        """Both stages hold: the formula is a test oracle."""
        return self.stage1 == "approved" and not self.missing and not self.embed_blockers


@dataclass(frozen=True)
class Approval:
    """The derived approval of a whole canon.

    Attributes:
        formulas: One row per formula, ordered by slug.
        quantity_status: Derived status of every quantity: ``approved``, ``draft`` or ``unmapped``.
        unmapped: The supplied quantities that have no ``data`` source, ordered by slug.
    """

    formulas: tuple[FormulaApproval, ...]
    quantity_status: dict[str, str]
    unmapped: tuple[str, ...]


def _bare(reference: str) -> str:
    return reference.removeprefix(_PREFIX)


def _producers(content: Namespace) -> dict[str, set[str]]:
    """Return, per quantity, the formulas that produce it."""
    producers: dict[str, set[str]] = {}
    for slug, formula in content.formulas.items():
        for application in formula.applications:
            for quantity in application.produce.values():
                if quantity is not None:
                    producers.setdefault(_bare(quantity), set()).add(slug)
    return producers


def _inputs(content: Namespace, formula: str) -> list[str]:
    """Return the quantities any application of ``formula`` reads, ordered by slug."""
    read: set[str] = set()
    for application in content.formulas[formula].applications:
        read.update(_bare(value) for value in application.bind.values() if isinstance(value, str))
        read.update(_bare(given) for given in application.given or [])
    return sorted(read)


def _is_read(content: Namespace, makers: list[str] | set[str]) -> bool:
    """Whether every producer is a pure data read: a formula of tool ``KAT``, the parts catalogue."""
    return all(content.formulas[maker].tool == "KAT" for maker in makers)


# A root cause: the quantity or formula at fault, what is wrong, and the formulas it passes through.
_Cause = tuple[str, str, tuple[str, ...]]


def _text(cause: _Cause, own: str | None = None) -> str:
    """Render a cause; ``own`` is the input it is shown on, whose name is then left out."""
    root, reason, via = cause
    head = reason if root == own else f"{root}: {reason}"
    return f"{head} via {', '.join(via)}" if via else head


def _unique(causes: list[_Cause]) -> list[_Cause]:
    """Keep one path per root cause, so that diamonds of embeds stay linear."""
    first: dict[tuple[str, str], _Cause] = {}
    for cause in causes:
        first.setdefault((cause[0], cause[1]), cause)
    return list(first.values())


class _Walk:
    """The transitive walk of stage 2, memoised per formula."""

    def __init__(self, content: Namespace, stage1: dict[str, str]) -> None:
        self.content = content
        self.stage1 = stage1
        self.producers = _producers(content)
        self._memo: dict[str, list[_Cause]] = {}

    def blocked(self, formula: str) -> list[_Cause]:
        """Root causes that keep ``formula`` from satisfying both stages; empty if it does."""
        if formula in self._memo:
            return self._memo[formula]
        self._memo[formula] = []  # a cycle adds nothing; the importer rejects cycles anyway
        causes: list[_Cause] = []
        if self.stage1.get(formula, "draft") != "approved":
            causes.append((formula, "not approved", ()))
        for quantity in _inputs(self.content, formula):
            causes.extend(self.input_causes(quantity, formula))
        causes.extend(self.embed_causes(formula))
        self._memo[formula] = _unique(causes)
        return self._memo[formula]

    def input_causes(self, quantity: str, formula: str) -> list[_Cause]:
        """Root causes that keep one input of ``formula`` from being covered."""
        makers = sorted(self.producers.get(quantity, set()) - {formula})
        data = self.content.quantities[quantity].data
        if not makers:
            return [] if data else [(quantity, "no data source", ())]
        causes: list[_Cause] = []
        for maker in makers:
            for root, reason, via in self.blocked(maker):
                causes.append((root, reason, via if root == maker and not via else (maker, *via)))
        if _is_read(self.content, makers) and not data:
            causes.append(
                (quantity, "no data source (the catalogue does not carry it)", tuple(makers))
            )
        return _unique(causes)

    def embed_causes(self, formula: str) -> list[_Cause]:
        """Root causes inside the formulas ``formula`` embeds, other than its own inputs."""
        own = set(_inputs(self.content, formula))
        causes: list[_Cause] = []
        for item in self.content.formulas[formula].embeds_closure:
            embedded = _bare(item).rpartition(".")[0]
            for root, reason, via in self.blocked(embedded):
                if root not in own:
                    causes.append(
                        (root, reason, via if root == embedded and not via else (embedded, *via))
                    )
        return _unique(causes)


def _input_state(walk: _Walk, quantity: str, formula: str) -> InputState:
    """Judge one input of ``formula`` over the whole chain behind it."""
    causes = walk.input_causes(quantity, formula)
    if causes:
        return InputState(quantity, False, "; ".join(_text(c, quantity) for c in causes))
    content = walk.content
    data = content.quantities[quantity].data
    makers = sorted(walk.producers.get(quantity, set()) - {formula})
    if not makers:
        return InputState(quantity, True, ", ".join(data or []))
    if _is_read(content, makers):
        return InputState(quantity, True, f"read from {', '.join(data or [])}")
    return InputState(quantity, True, f"produced by {', '.join(makers)}")


def _quantity_status(walk: _Walk) -> dict[str, str]:
    """A produced quantity follows its producers; a supplied one is approved with a source."""
    status: dict[str, str] = {}
    for slug, quantity in walk.content.quantities.items():
        makers = walk.producers.get(slug)
        if not makers:
            status[slug] = "approved" if quantity.data else UNMAPPED
        elif _is_read(walk.content, makers) and not quantity.data:
            status[slug] = UNMAPPED
        else:
            status[slug] = "approved" if all(not walk.blocked(m) for m in makers) else "draft"
    return status


def derive_approval(model: CanonModel, stage1: dict[str, str]) -> Approval:
    """Derive stage 2 and every quantity status from the model and the formulas' own statuses.

    Args:
        model: The imported canon model.
        stage1: The ``status`` of each formula entry; a formula missing from it counts as ``draft``.

    Returns:
        The approval of every formula and quantity.
    """
    content = model.namespaces[DEFAULT_NAMESPACE]
    walk = _Walk(content, stage1)
    rows = tuple(
        FormulaApproval(
            formula=slug,
            stage1=stage1.get(slug, "draft"),
            inputs=tuple(_input_state(walk, quantity, slug) for quantity in _inputs(content, slug)),
            embed_blockers=tuple(_text(cause) for cause in walk.embed_causes(slug)),
        )
        for slug in sorted(content.formulas)
    )
    status = _quantity_status(walk)
    unmapped = tuple(sorted(slug for slug, value in status.items() if value == UNMAPPED))
    return Approval(formulas=rows, quantity_status=status, unmapped=unmapped)
