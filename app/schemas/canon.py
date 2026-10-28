"""Schemas of the Expert View's canon endpoints (gh-1282, ADR 0030).

The kernel's own result types (``aero_kernel.schema``, ``aero_kernel.evaluation``) are the response
contract for values, warnings, errors and verdicts: the endpoint adds no second description of them.
"""

from __future__ import annotations

from aero_kernel.evaluation import RuleVerdict
from aero_kernel.schema import KernelError, Provenance, QuantityResult
from pydantic import BaseModel, ConfigDict, Field


class CanonFleetEntry(BaseModel):
    """An aircraft of the kernel's reference fleet."""

    id: str = Field(description="Stable identifier of the aircraft, used in compute requests.")
    name: str = Field(description="Name a person reads.")
    mass_kg: float = Field(description="The mass the fleet fixes for this aircraft, in kg.")
    flap_deflections: dict[str, float] = Field(
        description="Flap deflections in degrees by canon input slug; empty for an aircraft without flaps."
    )


class CanonAircraftRef(BaseModel):
    """The aircraft of a compute request."""

    model_config = ConfigDict(extra="forbid")

    fleet: str = Field(description="Identifier of a reference-fleet aircraft.")


class CanonComputeRequest(BaseModel):
    """What to compute for which aircraft."""

    model_config = ConfigDict(extra="forbid")

    aircraft: CanonAircraftRef
    quantities: list[str] = Field(
        min_length=1, description="Canon quantity slugs; each quantity at most once."
    )
    values: dict[str, float] = Field(
        default_factory=dict,
        description="Input values by canon slug in the quantity's SI unit; they replace the fleet's own.",
    )
    include_long_runs: bool = Field(
        default=False, description="Whether quantities that take minutes (AVL, mass envelope) run."
    )


class CanonLogRecord(BaseModel):
    """One kernel log record of the request."""

    time: str = Field(description="UTC time of the record, ISO 8601 with milliseconds.")
    level: str
    logger: str = Field(description="The kernel logger that wrote the record.")
    message: str
    formula: str | None = Field(default=None, description="The formula the record belongs to.")
    quantity: str | None = Field(default=None, description="The quantity the record belongs to.")


class CanonComputeResponse(BaseModel):
    """The kernel's answer to a compute request, with the evaluation and the request's logs."""

    quantities: list[QuantityResult] = Field(
        description="One result per requested slug, in request order."
    )
    input_errors: list[KernelError] = Field(
        description="Rejected input; when present, nothing was computed."
    )
    provenance: Provenance
    verdicts: list[RuleVerdict] = Field(
        description="Drela's design rules judged for the requested quantities."
    )
    needs_confirmation: list[str] = Field(
        description="Requested quantities skipped because they take minutes; "
        "repeat the request with include_long_runs to run them."
    )
    logs: list[CanonLogRecord] = Field(description="The kernel's log records of this request.")
