"""S_ref, b_ref and c_MAC of the main wing against an independent numerical integration.

The reference values are the sections' chords and leading edges as given, projected onto the x-y
plane (maintainer 2026-10-22); twist does not change them. The independent computation
integrates the piecewise-linear chord ``c(y)`` of the sections with Simpson's rule per panel,
which is exact for the quadratic ``c(y)^2`` and shares no formula with the adapter.
Tolerance: relative 1e-8.
"""

import math
from collections.abc import Callable
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = pytest.mark.asyncio

TOLERANCE = 1e-8


def simpson(f: Callable[[float], float], a: float, b: float) -> float:
    """Simpson's rule on one interval: exact for the quadratic ``c(y)^2`` of a linear chord."""
    return (b - a) / 6.0 * (f(a) + 4.0 * f((a + b) / 2.0) + f(b))


def numeric_projected(wing: dict[str, Any]) -> tuple[float, float, float]:
    """(S, b, c_MAC) projected onto x-y, by Simpson integration of c(y) and c(y)^2 per panel."""
    side_area = side_squares = side_span = 0.0
    for inner, outer in pairwise(wing["x_secs"]):
        y1, y2 = inner["xyz_le"][1], outer["xyz_le"][1]
        c1, c2 = inner["chord"], outer["chord"]

        def chord(
            y: float, y1: float = y1, y2: float = y2, c1: float = c1, c2: float = c2
        ) -> float:
            return c1 + (c2 - c1) * (y - y1) / (y2 - y1)

        low, high = min(y1, y2), max(y1, y2)
        side_area += simpson(chord, low, high)
        side_squares += simpson(lambda y: chord(y) ** 2, low, high)
        side_span += high - low
    factor = 2.0 if wing["symmetric"] else 1.0
    return factor * side_area, factor * side_span, side_squares / side_area


def planform_area(wing: dict[str, Any]) -> float:
    """The area measured along the panels (slant length times mean chord), for contrast."""
    total = 0.0
    sections = wing["x_secs"]
    for inner, outer in pairwise(sections):
        slant = math.dist(inner["xyz_le"][1:], outer["xyz_le"][1:])
        total += slant * (inner["chord"] + outer["chord"]) / 2.0
    return (2.0 if wing["symmetric"] else 1.0) * total


def dihedral_wing(degrees: float) -> dict[str, Any]:
    """A three-section symmetric wing with a constant dihedral, no twist."""
    rise = math.tan(math.radians(degrees))
    sections = [
        {"xyz_le": [0.02 * y, y, rise * y], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for y, c in ((0.0, 0.2), (0.3, 0.15), (0.7, 0.08))
    ]
    return {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}


async def properties_of(wing: dict[str, Any]) -> tuple[float, float, float]:
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    result = await GeometryAdapter(SolverRuntime()).main_wing_properties(airplane)
    return result.s_ref, result.b_ref, result.c_mac


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=TOLERANCE)


@pytest.mark.parametrize("degrees", [0.0, 8.0])
async def test_a_synthetic_wing_matches_the_numerical_integration(degrees: float) -> None:
    wing = dihedral_wing(degrees)
    expected = numeric_projected(wing)
    assert all(close(a, e) for a, e in zip(await properties_of(wing), expected, strict=True))


async def test_the_projected_and_the_planform_area_are_distinguished_at_8_degrees() -> None:
    wing = dihedral_wing(8.0)
    s_ref, _, _ = await properties_of(wing)
    ratio = planform_area(wing) / s_ref
    assert ratio > 1.009  # 1 / cos(8 deg) = 1.0098
    assert close(s_ref, numeric_projected(wing)[0])


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_fleet_main_wing_matches_the_numerical_integration(member: FleetMember) -> None:
    document = reference_document(member)
    wing = document["wings"]["Tragflaeche"]
    airplane = AirplaneGeometry.model_validate(document)
    result = await GeometryAdapter(SolverRuntime()).main_wing_properties(airplane)
    s_ref, b_ref, c_mac = numeric_projected(wing)
    assert close(result.s_ref, s_ref)
    assert close(result.b_ref, b_ref)
    assert close(result.c_mac, c_mac)


def twisted(wing: dict[str, Any], degrees: float) -> dict[str, Any]:
    """The same wing with every section twisted by ``degrees``."""
    return {**wing, "x_secs": [{**s, "twist": degrees} for s in wing["x_secs"]]}


@pytest.mark.parametrize("degrees", [0.0, 8.0])
async def test_twisting_the_sections_changes_no_reference_value(degrees: float) -> None:
    """Twist does not change the reference planform, with or without dihedral."""
    wing = dihedral_wing(degrees)
    assert await properties_of(twisted(wing, 5.0)) == await properties_of(wing)


async def test_twisting_the_reference_fleet_changes_no_reference_value() -> None:
    wing = reference_document(FleetMember.BRYAN)["wings"]["Tragflaeche"]
    assert await properties_of(twisted(wing, 0.0)) == await properties_of(wing)


async def test_a_wing_stored_on_the_negative_side_has_the_same_values() -> None:
    wing = dihedral_wing(3.0)
    mirrored = {
        **wing,
        "x_secs": [
            {**s, "xyz_le": [s["xyz_le"][0], -s["xyz_le"][1], s["xyz_le"][2]]}
            for s in wing["x_secs"]
        ],
    }
    assert await properties_of(mirrored) == await properties_of(wing)


async def test_a_wing_that_is_not_mirrored_counts_its_stored_side_once() -> None:
    wing = {**dihedral_wing(0.0), "symmetric": False}
    s_ref, b_ref, c_mac = await properties_of(wing)
    s_sym, b_sym, c_sym = await properties_of(dihedral_wing(0.0))
    assert close(s_ref, s_sym / 2)
    assert close(b_ref, b_sym / 2)
    assert close(c_mac, c_sym)


async def test_hand_values_of_a_single_trapezoid() -> None:
    """Half panel y 0..0.4 m, chord 0.2 -> 0.1 m, mirrored.

    S = 2 * 0.4 * (0.2 + 0.1) / 2 = 0.12 m^2; b = 2 * 0.4 = 0.8 m;
    c_MAC = (2 / S) * 0.4 * (0.2^2 + 0.2*0.1 + 0.1^2) / 3 = 0.155556 m.
    """
    sections = [
        {"xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"},
        {"xyz_le": [0.0, 0.4, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca2412"},
    ]
    wing = {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}
    s_ref, b_ref, c_mac = await properties_of(wing)
    assert close(s_ref, 0.12)
    assert close(b_ref, 0.8)
    assert close(c_mac, 2 / 0.12 * 0.4 * 0.07 / 3)


async def test_a_main_wing_without_projected_area_is_unsupported() -> None:
    """A vertical main wing (all sections at the same y) has no projected planform."""
    sections = [
        {"xyz_le": [0.0, 0.0, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for z in (0.0, 0.5)
    ]
    wing = {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    adapter = GeometryAdapter(SolverRuntime())
    with pytest.raises(FormulaError) as raised:
        await adapter.main_wing_properties(airplane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
