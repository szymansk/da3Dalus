"""A spinner merged into its parent for the solvers, against real AVL and AeroSandbox (#1375).

Aero tier. The reference fleet has no plan package with a separate spinner yet, so the case is built
from the Bf 109 E of the fleet: its fuselage nose up to the section at ``SPLIT`` becomes a body of
role ``spinner`` attached to the rest, the section at the cut shared by both. The joint sections are
the same, so the merge must give the solvers the original fuselage back: AVL's body starts at the
spinner tip and AeroBuildup's fuselage has the wetted area of the whole body, spinner included.
"""

import copy
import math
from typing import Any

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.avl_body import mesh_bodies
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.validate import validate_aircraft

pytestmark = pytest.mark.aero

SPLIT = 6  # the Bf 109 fuselage section at x = 0.030085 m: about the spinner's back plate
CL = 0.5  # any lift coefficient: the split and the whole aircraft run at the same one


def whole() -> dict[str, Any]:
    return reference_document(FleetMember.BF109_E)


def with_spinner() -> dict[str, Any]:
    """The Bf 109 with its nose up to section ``SPLIT`` written as a tractor spinner."""
    document = whole()
    fuselage = document["fuselages"]["fuselage"]
    sections = fuselage["x_secs"]
    spinner = {
        "name": "spinner",
        "role": "spinner",
        "attached_to": "fuselage",
        "symmetric": False,
        "x_secs": copy.deepcopy(sections[: SPLIT + 1]),
    }
    fuselage["x_secs"] = sections[SPLIT:]
    document["fuselages"]["spinner"] = spinner
    return document


def test_the_split_aircraft_is_admissible_and_declares_the_merge() -> None:
    aircraft = AircraftInput.model_validate(
        {"airplane": with_spinner(), "values": {"aircraft-mass": 2.0, "gravity": 9.80665}}
    )
    result = validate_aircraft(aircraft)
    assert result.errors == ()
    (notice,) = [w for w in result.warnings if w.code == "spinner_merged_into_body"]
    assert (notice.detail["spinner"], notice.detail["parent"]) == ("spinner", "fuselage")
    assert notice.detail["end"] == "front"
    assert notice.detail["merged_stations"] == SPLIT


def test_the_avl_body_starts_at_the_spinner_tip() -> None:
    plane = AirplaneGeometry.model_validate(with_spinner())
    tip = whole()["fuselages"]["fuselage"]["x_secs"][0]["xyz"][0]
    bodies = mesh_bodies(plane)
    assert [b.name for b in bodies] == ["fuselage", "canopy"]
    assert bodies[0].origin[0] == tip
    assert bodies == mesh_bodies(AirplaneGeometry.model_validate(whole()))


@pytest.mark.asyncio
async def test_avl_sees_the_same_aircraft_as_without_the_split() -> None:
    async with SolverRuntime() as runtime:
        adapter = AvlAdapter(runtime)
        want = await adapter.neutral_point(AirplaneGeometry.model_validate(whole()), CL)
        got = await adapter.neutral_point(AirplaneGeometry.model_validate(with_spinner()), CL)
    assert math.isfinite(got.x_np)
    assert got.x_np == want.x_np


def test_the_aerobuildup_wetted_area_includes_the_spinner() -> None:
    merged = to_asb_airplane(AirplaneGeometry.model_validate(with_spinner())).fuselages
    original = to_asb_airplane(AirplaneGeometry.model_validate(whole())).fuselages
    cut = copy.deepcopy(with_spinner())
    del cut["fuselages"]["spinner"]
    without = to_asb_airplane(AirplaneGeometry.model_validate(cut)).fuselages
    assert [f.name for f in merged] == ["fuselage", "canopy"]
    assert math.isclose(merged[0].area_wetted(), original[0].area_wetted(), rel_tol=1e-12)
    assert merged[0].area_wetted() > without[0].area_wetted()
    assert merged[0].xsecs[0].xyz_c[0] == original[0].xsecs[0].xyz_c[0]
