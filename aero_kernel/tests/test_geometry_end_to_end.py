"""Slice 2 end to end: the geometry quantities of BRYAN and JAGUAR through the public ``compute()``.

The main wing's S_ref, b_ref and c_MAC are checked against AeroSandbox's own values of an
``asb.Wing`` built independently (tests/test_geometry_properties.py, relative 1e-8); the derived
quantities against hand formulas of those:

- c_bar = S / b, AR = b^2 / S, W/S = m g / S with g = 9.80665 m/s^2 (the canon default) and the
  mass of the fleet member (BRYAN 0.151 kg; JAGUAR 0.160 kg, approx., maintainer 2026-10-14).

The fleet test needs AeroSandbox (the reference values are its own), so it runs in the aero tier;
the input-error tests stop before any computation and run in the fast tier.
"""

import pytest
from aero_kernel import compute
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_geometry_properties import asb_values

pytestmark = pytest.mark.asyncio

GRAVITY = 9.80665
SLUGS = (
    "wing-reference-area",
    "wing-span",
    "mean-aerodynamic-chord",
    "mean-geometric-chord",
    "aspect-ratio",
    "wing-loading",
)


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


@pytest.mark.aero
@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_geometry_quantities_of_the_fleet(member: FleetMember) -> None:
    document = reference_document(member)
    aircraft = AircraftInput.model_validate(
        {"airplane": document, "values": {"aircraft-mass": member.mass_kg}}
    )
    result = await compute(aircraft, request(*SLUGS))
    quantities = by_slug(result)
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    s_ref, b_ref, c_mac = asb_values(document["wings"]["Tragflaeche"])
    expected = {
        "wing-reference-area": (s_ref, "m^2"),
        "wing-span": (b_ref, "m"),
        "mean-aerodynamic-chord": (c_mac, "m"),
        "mean-geometric-chord": (s_ref / b_ref, "m"),
        "aspect-ratio": (b_ref**2 / s_ref, "1"),
        "wing-loading": (member.mass_kg * GRAVITY / s_ref, "N/m^2"),
    }
    for slug, (value, unit) in expected.items():
        assert close(quantities[slug].value, value, 1e-8), slug
        assert quantities[slug].unit == unit, slug
    assert quantities["wing-reference-area"].tool == "GEO"
    assert [d.slug for d in result.provenance.defaults_used] == ["gravity"]


async def test_the_input_errors_of_the_surface_types_come_back_with_their_paths() -> None:
    document = reference_document(FleetMember.JAGUAR)
    document["wings"]["Hoehenleitwerk"]["surface_type"] = "main_wing"  # two main wings
    del document["wings"]["Seitenleitwerk"]["surface_type"]  # one without a type
    aircraft = AircraftInput.model_validate({"airplane": document, "values": {}})
    result = await compute(aircraft, request("wing-loading"))
    assert result.quantities == ()
    assert [(e.code, e.input_path) for e in result.input_errors] == [
        ("missing_surface_type", 'airplane.wings["Seitenleitwerk"]'),
        ("main_wing_count", "airplane.wings"),
    ]
    assert all(e.category.value == "invalid_input" for e in result.input_errors)


async def test_an_airplane_without_wings_has_the_main_wing_count_error() -> None:
    aircraft = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await compute(aircraft, request("wing-loading"))
    assert [(e.code, e.input_path) for e in result.input_errors] == [
        ("main_wing_count", "airplane.wings")
    ]
