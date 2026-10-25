"""Two-stage approval of the canon, derived (canon README "Two stages", #1251).

Stage 1 is the formula's own ``status``, set by the maintainer. Stage 2 is derived here and never
set by hand: every input of the formula is either produced by a stage-1-approved formula, or a
supplied quantity with a ``data:`` source in our data. A quantity's status follows from the same
rule: a produced quantity has the status of its producers, a supplied one is ``approved`` exactly
when it has a source. A quantity produced by a pure data read (a formula of tool ``KAT``) needs
both: its producer approved and a source naming the catalogue field.
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
    """

    formula: str
    stage1: str
    inputs: tuple[InputState, ...]

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
        return self.stage1 == "approved" and not self.missing


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


def _input_state(
    content: Namespace,
    quantity: str,
    formula: str,
    producers: dict[str, set[str]],
    stage1: dict[str, str],
) -> InputState:
    """Judge one input of ``formula``: produced by an approved formula, or with a data source."""
    makers = sorted(producers.get(quantity, set()) - {formula})
    data = content.quantities[quantity].data
    if not makers:
        return (
            InputState(quantity, True, ", ".join(data))
            if data
            else InputState(quantity, False, "no data source")
        )
    draft = [maker for maker in makers if stage1.get(maker, "draft") != "approved"]
    if draft:
        return InputState(quantity, False, f"produced by {', '.join(draft)} (not approved)")
    if not _is_read(content, makers):
        return InputState(quantity, True, f"produced by {', '.join(makers)}")
    if data:
        return InputState(quantity, True, f"read from {', '.join(data)}")
    return InputState(quantity, False, "no data source (the catalogue does not carry it)")


def _quantity_status(
    content: Namespace, producers: dict[str, set[str]], stage1: dict[str, str]
) -> dict[str, str]:
    """A produced quantity follows its producers; a supplied one is approved with a source."""
    status: dict[str, str] = {}
    for slug, quantity in content.quantities.items():
        makers = producers.get(slug)
        if makers:
            approved = all(stage1.get(maker, "draft") == "approved" for maker in makers)
            if approved and _is_read(content, makers) and not quantity.data:
                status[slug] = UNMAPPED
            else:
                status[slug] = "approved" if approved else "draft"
        else:
            status[slug] = "approved" if quantity.data else UNMAPPED
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
    producers = _producers(content)
    rows = tuple(
        FormulaApproval(
            formula=slug,
            stage1=stage1.get(slug, "draft"),
            inputs=tuple(
                _input_state(content, quantity, slug, producers, stage1)
                for quantity in _inputs(content, slug)
            ),
        )
        for slug in sorted(content.formulas)
    )
    status = _quantity_status(content, producers, stage1)
    unmapped = tuple(sorted(slug for slug, value in status.items() if value == UNMAPPED))
    return Approval(formulas=rows, quantity_status=status, unmapped=unmapped)
