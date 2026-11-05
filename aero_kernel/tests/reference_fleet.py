"""The reference fleet moved to :mod:`aero_kernel.reference_fleet` (public, ADR 0030).

This module re-exports it so the tests keep one import path.
"""

from typing import Any

from aero_kernel.reference_fleet import (
    FLAP_DEFLECTIONS_DEG,
    REFERENCE_DIR,
    FleetMember,
    aircraft_input,
    flap_values,
    fleet_values,
    read_selig_coordinates,
    reference_document,
)

__all__ = [
    "FLAP_DEFLECTIONS_DEG",
    "REFERENCE_DIR",
    "FleetMember",
    "aircraft_input",
    "bryan_as_the_prototype",
    "flap_values",
    "fleet_values",
    "read_selig_coordinates",
    "reference_document",
]


def bryan_as_the_prototype() -> dict[str, Any]:
    """BRYAN as the CRRCSim prototype computed it: the canopy ``Haube`` a body of its own.

    The prototype (ERGEBNISSE_STABILITAET.md) had no canopy merge, so the tests that reproduce its
    numbers drop the copy's ``role`` / ``attached_to`` additions (#1355 slice 2, reference README);
    every other test uses the copy as it is, the canopy merged into ``Rumpf``.
    """
    document = reference_document(FleetMember.BRYAN)
    for body in document["fuselages"].values():
        body.pop("role", None)
        body.pop("attached_to", None)
    return document
