"""P1-F11 reproduction: flight-speed = 0 ends `lift-coefficient` as category `internal`.

Run:  cd <frozen copy> && PY <this file>
Engine run exactly as the fast test test_lift_coefficient_required.py does it (stub ATM adapter,
stand-in GEO reference values, no AeroSandbox); only the flight speed differs. Changes nothing.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import aero_kernel
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.schema import AircraftInput, ComputeRequest
from aero_kernel.tests.formula_builders import StubAtmosphere, solvers_with
from aero_kernel.tests.test_stall_speed_engine import document

print("aero_kernel imported from:", Path(aero_kernel.__file__).parent)
logging.disable(logging.CRITICAL)  # the engine logs the traceback of an internal error; keep the output short
BUILD = shipped_build()
print("canon: flight-speed positive =", BUILD.model.quantity("calc:flight-speed").positive,
      "| lift-coefficient-required preconditions =",
      [c.id for c in BUILD.model.formula("calc:lift-coefficient-required").preconditions])


async def run(speed: float) -> None:
    aircraft = AircraftInput.model_validate(
        {"airplane": document(), "values": {"aircraft-mass": 1.5, "altitude": 0.0, "flight-speed": speed}}
    )
    request = ComputeRequest(quantities=("dynamic-pressure", "lift-coefficient"))
    result = await evaluate(BUILD, aircraft, request, solvers=solvers_with(atmosphere=StubAtmosphere({0.0: 1.225})))
    print(f"\nflight-speed = {speed} m/s   input_errors = {[e.code for e in result.input_errors]}")
    for q in result.quantities:
        print(f"  {q.slug}: status={q.status.value} value={q.value}")
        if q.error is not None:
            e = q.error
            print(f"    error: category={e.category.value} code={e.code} retryable={e.retryable} "
                  f"escalate={e.escalate}")
            print(f"    message: {e.message}")
            print(f"    hint: {e.hint}")


for v in (10.0, 0.0):
    asyncio.run(run(v))
