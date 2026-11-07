"""Expert View endpoints (gh-1282, ADR 0030): compute canon quantities with the kernel.

A development view for experts: the kernel's values stand beside the app's own and are never
written back.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.canon import CanonAircraftList, CanonComputeRequest, CanonComputeResponse
from app.services import canon_service

router = APIRouter()


@router.get(
    "/canon/aircraft",
    operation_id="list_canon_aircraft",
    summary="List the aircraft of the canon/kernel view",
    description=(
        "The kernel's reference fleet and, separately, the stored aeroplanes, each in its current "
        "state (the head of its main branch) with the mass the kernel gets for it. Canon/kernel "
        "view (development), experts only (ADR 0030)."
    ),
)
def list_canon_aircraft(db: Annotated[Session, Depends(get_db)]) -> CanonAircraftList:
    """The aircraft the canon/kernel view (development, experts only) can load."""
    return canon_service.list_aircraft(db)


@router.post(
    "/canon/compute",
    operation_id="compute_canon_quantities",
    summary="Compute canon quantities of an aircraft with the kernel",
    description=(
        'Computes, for a reference-fleet aircraft (`{"fleet": "<id>"}`) or a stored '
        'aeroplane in its stored state (`{"aeroplane": "<id>"}`), the requested quantities and their subtrees with the aero kernel and judges '
        "them against Drela's design rules. Quantities that take minutes are skipped unless "
        "`include_long_runs` is set; they are then listed in `needs_confirmation`. The kernel's "
        "log records of the request are returned in `logs`. Each computation step whose inputs "
        "did not change since an earlier request is served from the kernel's cache "
        "(`from_cache`, with the run time measured when it was computed); `fresh` recomputes "
        "everything. Canon/kernel view (development), experts only (ADR 0030)."
    ),
)
async def compute_canon_quantities(
    request: CanonComputeRequest, db: Annotated[Session, Depends(get_db)]
) -> CanonComputeResponse:
    """Compute canon quantities for a reference aircraft or a stored aeroplane."""
    return await canon_service.compute_canon(request, db)
