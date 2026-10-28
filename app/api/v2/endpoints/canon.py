"""Expert View endpoints (gh-1282, ADR 0030): compute canon quantities with the kernel.

A development view for experts: the kernel's values stand beside the app's own and are never
written back.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.canon import CanonComputeRequest, CanonComputeResponse, CanonFleetEntry
from app.services import canon_service

router = APIRouter()


@router.get(
    "/canon/fleet",
    response_model=list[CanonFleetEntry],
    operation_id="list_canon_fleet",
    summary="List the reference aircraft of the canon/kernel view",
)
def list_canon_fleet() -> list[CanonFleetEntry]:
    """The aircraft the canon/kernel view (development, experts only) can load."""
    return canon_service.list_fleet()


@router.post(
    "/canon/compute",
    response_model=CanonComputeResponse,
    operation_id="compute_canon_quantities",
    summary="Compute canon quantities of a reference aircraft with the kernel",
    description=(
        "Computes the requested quantities and their subtrees with the aero kernel and judges "
        "them against Drela's design rules. Quantities that take minutes are skipped unless "
        "`include_long_runs` is set; they are then listed in `needs_confirmation`. The kernel's "
        "log records of the request are returned in `logs`. Canon/kernel view (development), "
        "experts only (ADR 0030)."
    ),
)
async def compute_canon_quantities(request: CanonComputeRequest) -> CanonComputeResponse:
    """Compute canon quantities for a reference aircraft."""
    return await canon_service.compute_canon(request)
