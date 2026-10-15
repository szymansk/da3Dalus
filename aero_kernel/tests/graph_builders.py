"""Builders of small hand-made canon models for the graph tests."""

from typing import Any

# ``Any`` is the raw-JSON boundary: these are hand-written model dicts that the canon model validates.
from aero_kernel.canon.model import CanonModel
from aero_kernel.tests.canon_builders import with_hash


def quantity(role: str = "derived", **extra: Any) -> dict[str, Any]:
    """A scalar quantity of the given role."""
    return {"symbol": "x", "unit": "1", "role": role, "type": "scalar", **extra}


def formula(
    reads: dict[str, str],
    writes: dict[str, str],
    *,
    application: str = "default",
    **extra: Any,
) -> dict[str, Any]:
    """A one-application formula reading and writing quantities (bare slugs, parameter -> slug)."""
    bind = {parameter: f"calc:{slug}" for parameter, slug in reads.items()}
    produce = {parameter: f"calc:{slug}" for parameter, slug in writes.items()}
    app_extra = {key: extra.pop(key) for key in ("when", "given") if key in extra}
    return {
        "kind": "law",
        "tool": "APP",
        "cost": "instant",
        "inputs": dict(bind),
        "outputs": dict(produce),
        "applications": [{"id": application, "bind": bind, "produce": produce, **app_extra}],
        **extra,
    }


def model_of(
    quantities: dict[str, dict[str, Any]], formulas: dict[str, dict[str, Any]]
) -> CanonModel:
    """Validate a one-namespace model of the given quantities and formulas."""
    namespaces = {"calc": {"quantities": quantities, "formulas": formulas}}
    return CanonModel.model_validate(with_hash(namespaces))
