"""The kernel's own artefact: the validated canon model, its graph and the registry (ch. 8.4).

``canon_model.json`` ships with the package, so the kernel loads it itself, once, on first use
(``shipped_build``) and never at import. A missing or broken shipped model is our defect: it
raises :class:`CanonLoadError`, and ``compute`` answers every quantity ``internal`` and logs the
one ERROR of the call. Nothing here logs a failure.
"""

import functools
import logging
from dataclasses import dataclass
from pathlib import Path

from aero_kernel.cache import build_digest
from aero_kernel.canon.load import load_canon_model, load_failure
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import display_slug
from aero_kernel.graph import CanonGraph, GraphModelError
from aero_kernel.registry import DEFAULT_REGISTRY, Registry, TraceabilityReport
from pydantic import JsonValue

logger = logging.getLogger(__name__)

__all__ = ["Build", "load_build", "shipped_build"]

# How many traceability findings go into the error detail.
_MAX_FINDINGS = 10


@dataclass(frozen=True)
class Build:
    """A canon model with everything derived from it and the code that implements it.

    A frozen dataclass rather than a Pydantic model: it holds a graph and a registry, which are
    code and derived structure, not data crossing a module boundary.

    Attributes:
        model: The validated canon model.
        graph: The dependency graph of the model, built once.
        digest: Hash over the code and the canon model (the cache-key component).
        registry: The formula implementations and checks.
        report: The traceability of the registry against the model.
    """

    model: CanonModel
    graph: CanonGraph
    digest: str
    registry: Registry
    report: TraceabilityReport


def load_build(path: Path | None = None, registry: Registry | None = None) -> Build:
    """Load a canon model and assemble its build.

    Args:
        path: The model file; ``None`` means the packaged ``canon_model.json``.
        registry: The registry to trace against the model; ``None`` means the default registry.

    Returns:
        The build.

    Raises:
        CanonLoadError: If the model cannot be loaded, the registry does not match it, or its
            graph is not well formed (a cycle, a computed quantity nobody produces). The error
            is ``internal`` and escalates.
    """
    model = load_canon_model(path)
    used = DEFAULT_REGISTRY if registry is None else registry
    report = used.check_traceability(model)
    if not report.ok:
        findings: list[JsonValue] = [
            {
                "kind": finding.kind,
                "slug": display_slug(finding.slug),
                "check_id": finding.check_id,
            }
            for finding in report.findings[:_MAX_FINDINGS]
        ]
        raise load_failure(
            "the implementations do not match the model",
            {"finding_count": len(report.findings), "findings": findings},
        )
    try:
        graph = CanonGraph(model)
    except GraphModelError as exc:
        raise load_failure("the model is not a well-formed graph") from exc
    build = Build(model=model, graph=graph, digest=build_digest(), registry=used, report=report)
    logger.info(
        "build ready: %d formulas, %d without implementation",
        sum(len(content.formulas) for content in model.namespaces.values()),
        len(report.not_implemented),
    )
    return build


@functools.cache
def shipped_build() -> Build:
    """Return the build of the packaged model, loaded once on first use.

    The memo is an immutable package artefact, not call state. ``functools.cache`` stores only a
    returned value, never a raised exception, so a failed load is retried on every call and the
    kernel recovers after the file is fixed without a restart. The first call parses the
    model on the calling thread; ch. 8.10 forbids blocking on solver work, and parsing one JSON
    file is not that.

    Returns:
        The shipped build.

    Raises:
        CanonLoadError: As :func:`load_build`.
    """
    return load_build()
