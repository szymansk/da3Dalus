"""Expert View backend (gh-1282, ADR 0030): compute canon quantities of a reference-fleet aircraft.

The kernel's values are shown beside the app's own in this view only (ADR 0030); nothing computed
here is written back. Only the kernel's public API is used: ``compute``, ``schema``, ``evaluation``
and the reference fleet.
"""

from __future__ import annotations

import asyncio

from aero_kernel import compute
from aero_kernel.evaluation import judge_result
from aero_kernel.reference_fleet import FleetMember, aircraft_input, flap_values
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityStatus,
    ReasonCode,
)
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import NotFoundError, ValidationError
from app.core.kernel_log_capture import capture_kernel_logs
from app.schemas.canon import CanonComputeRequest, CanonComputeResponse, CanonFleetEntry


def list_fleet() -> list[CanonFleetEntry]:
    """The reference-fleet aircraft the Expert View can load."""
    return [
        CanonFleetEntry(
            id=member.fleet_id,
            name=member.display_name,
            mass_kg=member.mass_kg,
            flap_deflections=flap_values(member),
        )
        for member in FleetMember
    ]


def _kernel_request(request: CanonComputeRequest) -> ComputeRequest:
    """The kernel request, or a validation error for what the kernel refuses to build."""
    try:
        return ComputeRequest(
            quantities=tuple(request.quantities), include_long_runs=request.include_long_runs
        )
    except PydanticValidationError as exc:
        raise ValidationError(
            "Invalid compute request",
            {"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


def _run_kernel(aircraft: AircraftInput, request: ComputeRequest) -> ComputeResult:
    """Run the async kernel to completion on its own event loop, in the worker thread."""
    return asyncio.run(compute(aircraft, request))


def _needs_confirmation(result: ComputeResult) -> list[str]:
    """The requested quantities the kernel skipped because they take minutes."""
    return [
        q.slug
        for q in result.quantities
        if q.status is QuantityStatus.SKIPPED
        and q.reason is not None
        and q.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
    ]


async def compute_canon(request: CanonComputeRequest) -> CanonComputeResponse:
    """Compute the requested quantities of a fleet aircraft with the kernel.

    The kernel runs in a worker thread (its own event loop and process pool for the solvers), so a
    long computation does not block the application's event loop.

    Args:
        request: The aircraft, the quantities, the caller's input values and the long-run flag.

    Returns:
        The kernel's results, Drela's verdicts for the requested quantities, the quantities that
        wait for a confirmation and the kernel's log records of this request.

    Raises:
        NotFoundError: If the fleet has no such aircraft.
        ValidationError: If the quantities cannot form a kernel request.
    """
    member = FleetMember.from_fleet_id(request.aircraft.fleet)
    if member is None:
        raise NotFoundError(entity="Fleet aircraft", resource_id=request.aircraft.fleet)
    kernel_request = _kernel_request(request)
    aircraft = aircraft_input(member, request.values)
    with capture_kernel_logs() as logs:
        result = await asyncio.to_thread(_run_kernel, aircraft, kernel_request)
        verdicts = judge_result(result, aircraft.airplane)
    requested = set(kernel_request.quantities)
    return CanonComputeResponse(
        quantities=list(result.quantities),
        input_errors=list(result.input_errors),
        provenance=result.provenance,
        verdicts=[v for v in verdicts if v.quantity in requested],
        needs_confirmation=_needs_confirmation(result),
        logs=list(logs),
    )
