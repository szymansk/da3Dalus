"""A real reference-fleet compute twice through ``CachedKernel`` (ARCHITECTURE ch. 8.4, #1332).

Aero tier: real AeroSandbox, NeuralFoil and IPOPT. The second call must be served from the cache
node by node, with values bit-identical to the first and the run times measured by the first.
"""

import struct

import pytest
from aero_kernel import CachedKernel
from aero_kernel.schema import AircraftInput, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import FleetMember, flap_values, reference_document

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]


def bits(value: float | None) -> bytes:
    assert value is not None
    return struct.pack("<d", value)


async def test_bryan_stall_speed_is_served_from_the_cache_the_second_time() -> None:
    member = FleetMember.BRYAN
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {"aircraft-mass": member.mass_kg, "altitude": 0.0, **flap_values(member)},
        }
    )
    kernel = CachedKernel(max_entries=64)
    first = await kernel.compute(aircraft, request("stall-speed"))
    second = await kernel.compute(aircraft, request("stall-speed"))
    (computed,), (served,) = first.quantities, second.quantities
    assert computed.status is QuantityStatus.OK, computed.error
    assert not computed.from_cache
    assert served.from_cache
    assert bits(served.value) == bits(computed.value)
    assert served.model_dump_json(exclude={"from_cache"}) == computed.model_dump_json(
        exclude={"from_cache"}
    )
    assert second.provenance == first.provenance
