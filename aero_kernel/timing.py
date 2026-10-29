"""Run-time arithmetic of a quantity and the chain before it (ARCHITECTURE ch. 8.3, 8.13).

Pure functions over measured node times; the engine measures, this module only adds them up.
"""

import math
from collections.abc import Hashable, Mapping, Sequence
from typing import TypeVar

from aero_kernel.schema import TimeBounds, Timing

__all__ = ["chain_timing", "run_bounds"]

N = TypeVar("N", bound=Hashable)


def run_bounds(durations: Sequence[float]) -> TimeBounds:
    """The own time of a node from its runs, one per world assignment (ch. 8.13).

    The runs of a node lie in one layer and run concurrently: the longest single run is the lower
    bound, the sum of all runs the upper one. A node run once has equal bounds.

    Args:
        durations: The measured seconds of each run.

    Returns:
        The bounds of the node's own time.

    Raises:
        ValueError: If there is no run.
    """
    if not durations:
        msg = "a node's own time needs at least one run"
        raise ValueError(msg)
    return TimeBounds(lower=max(durations), upper=math.fsum(durations))


def _ancestors(node: N, predecessors: Mapping[N, Sequence[N]]) -> set[N]:
    """Every node the node reads, transitively, without the node itself."""
    found: set[N] = set()
    pending = list(predecessors[node])
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(predecessors[current])
    return found


def _longest_path(
    node: N, own: Mapping[N, TimeBounds], predecessors: Mapping[N, Sequence[N]]
) -> float:
    """The longest path by own lower bounds that ends at a direct predecessor of the node."""
    finish: dict[N, float] = {}

    def finished(current: N) -> float:
        if current not in finish:
            start = max((finished(p) for p in predecessors[current]), default=0.0)
            finish[current] = start + own[current].lower
        return finish[current]

    return max((finished(p) for p in predecessors[node]), default=0.0)


def chain_timing(
    producer: N, own: Mapping[N, TimeBounds], predecessors: Mapping[N, Sequence[N]]
) -> Timing:
    """The timing of a quantity: its producer's own time and the time of the chain before it.

    Args:
        producer: The node that produces the quantity.
        own: The own time of the producer and of every node it reads, transitively.
        predecessors: The nodes each node reads directly; a DAG.

    Returns:
        ``before`` upper bound = the sum of the own upper bounds of the distinct ancestors;
        ``before`` lower bound = the longest path through the ancestors by own lower bounds;
        ``total`` = ``before`` + ``own``.
    """
    upper = math.fsum(own[node].upper for node in _ancestors(producer, predecessors))
    lower = _longest_path(producer, own, predecessors)
    # the longest path is a subset of the ancestors, but fsum and plain sums may differ by rounding
    before = TimeBounds(lower=min(lower, upper), upper=upper)
    return Timing.of(own=own[producer], before=before)
