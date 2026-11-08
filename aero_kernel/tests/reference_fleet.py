"""The reference fleet moved to :mod:`aero_kernel.reference_fleet` (public, ADR 0030).

This module re-exports it so the tests keep one import path.
"""

from typing import Any

import pytest
from aero_kernel.body_axis import AeroBuildupBodies
from aero_kernel.geometry import AirplaneGeometry
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
    "MVP_FLEET",
    "PLAN_BATCH",
    "REFERENCE_DIR",
    "TAILLESS",
    "WITH_PITCH_TAIL",
    "FleetMember",
    "aircraft_input",
    "bryan_as_the_prototype",
    "convert_with_the_true_body_axes",
    "flap_values",
    "fleet_values",
    "read_selig_coordinates",
    "reference_document",
]

# The six aircraft whose goldens the per-quantity fleet tests pin (test_*_fleet.py) and whose AVL
# files are snapshots; the 28 plan models of #1372 have their goldens in test_plan_batch_fleet.py,
# one compute each.
MVP_FLEET = (
    FleetMember.BRYAN,
    FleetMember.JAGUAR,
    FleetMember.CHEKKER,
    FleetMember.BELEMNITOS,
    FleetMember.WIESEL,
    FleetMember.RV7,
)
PLAN_BATCH = tuple(member for member in FleetMember if member not in MVP_FLEET)
# The flying wings of the batch: a main wing and a fin, no surface that trims the pitch.
TAILLESS = (FleetMember.VOODOO, FleetMember.WINDFREAK)
WITH_PITCH_TAIL = tuple(member for member in FleetMember if member not in TAILLESS)


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


def convert_with_the_true_body_axes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hand AeroBuildup the bodies with their true section centres, as the prototype did.

    The prototype (ERGEBNISSE_STABILITAET.md) converted every body with its stepped centres; the
    kernel straightens each body's axis for AeroBuildup (#1358). The tests that reproduce the
    prototype's numbers run the worker in this process with the straightening switched off;
    every other test sees the straight axes.
    """
    from aero_kernel.solver_bodies import solver_bodies
    from aero_kernel.solvers import asb_airplane

    def true_axes(airplane: AirplaneGeometry) -> AeroBuildupBodies:
        return AeroBuildupBodies(solver_bodies(airplane), ())

    monkeypatch.setattr(asb_airplane, "aerobuildup_bodies", true_axes)
