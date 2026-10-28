"""The reference fleet moved to :mod:`aero_kernel.reference_fleet` (public, ADR 0030).

This module re-exports it so the tests keep one import path.
"""

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
    "flap_values",
    "fleet_values",
    "read_selig_coordinates",
    "reference_document",
]
