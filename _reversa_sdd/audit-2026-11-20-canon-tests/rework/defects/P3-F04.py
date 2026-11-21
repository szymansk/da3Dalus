"""P3-F04 reproduction: endurance-and-range-optimum does not return for a stall speed <= 0.

Run:  cd <frozen copy> && PY <this file>
The formula is called directly with the fast tests' doubles (endurance_builders.SpeedOpti stands in
for AeroBuildup; no real solver). Each case runs in a child process under a hard 20 s timeout; the
child wraps the call in asyncio.timeout(2 s) (the engine's time-budget mechanism, engine.py:1558)
and, after 5 s, a SIGALRM handler prints the state of the scan loop. Changes nothing on disk.
"""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

HARD_TIMEOUT_S = 20
CASES = {
    # name: (stall speed, the stub's lowest speed with a level-flight solution)
    "control_v_s_6": (6.0, 0.0),
    "v_s_0": (0.0, 1.0),
    "v_s_minus_3": (-3.0, 1.0),
    "v_s_nan": (float("nan"), 1.0),
}


def child(name: str) -> None:
    import aero_kernel
    from aero_kernel.build import shipped_build
    from aero_kernel.errors import FormulaError
    from aero_kernel.formulas.endurance_and_range_optimum import endurance_and_range_optimum
    from aero_kernel.tests.endurance_builders import SpeedOpti, bound, context_of

    slug = "endurance-and-range-optimum"
    v_s, min_speed = CASES[name]
    print("  aero_kernel imported from:", Path(aero_kernel.__file__).parent)
    print("  canon preconditions of the entry:",
          [c.id for c in shipped_build().model.formula(f"calc:{slug}").preconditions])
    opti = SpeedOpti(min_speed=min_speed)

    def report(signum, frame):  # where is the process after 5 s?
        while frame is not None and frame.f_code.co_name != "scan":
            frame = frame.f_back
        if frame is None:
            print("  after 5 s: not inside _Domain.scan", flush=True)
            return
        domain = frame.f_locals["self"]
        print(f"  after 5 s: still inside _Domain.scan, line {frame.f_lineno}; v = {frame.f_locals['v']!r}; "
              f"scan speeds so far = {len(domain.grid)}; first = {domain.grid[:3]}; last = {domain.grid[-1]!r}; "
              f"solver calls = {len(opti.speeds)}; speeds inside the domain = "
              f"{sum(domain.inside(g) is not None for g in set(domain.grid))}", flush=True)

    signal.signal(signal.SIGALRM, report)
    signal.alarm(5)

    async def call():
        async with asyncio.timeout(2.0):  # what the engine does with the request's time budget
            return await endurance_and_range_optimum(bound(slug, {"stall-speed": v_s}), context_of(slug, opti))

    started = time.monotonic()
    try:
        result = asyncio.run(call())
        print(f"  returned after {time.monotonic() - started:.2f} s: {result}")
    except FormulaError as error:
        print(f"  declared FormulaError after {time.monotonic() - started:.2f} s: "
              f"{error.category.value}/{error.code}")
    except TimeoutError:
        print(f"  asyncio.timeout fired after {time.monotonic() - started:.2f} s")
    except Exception as error:  # noqa: BLE001 - not a declared failure: the engine would call it internal
        print(f"  undeclared {type(error).__name__} after {time.monotonic() - started:.2f} s "
              f"({len(opti.speeds)} solver calls, last speed {opti.speeds[-1] if opti.speeds else None!r}): {error}")
    signal.alarm(0)


def reachability() -> None:
    """Can a caller hand the kernel a stall speed of 0? (engine validation only, no solver)"""
    import logging

    from aero_kernel.build import shipped_build
    from aero_kernel.engine import evaluate
    from aero_kernel.schema import AircraftInput, ComputeRequest
    from aero_kernel.tests.formula_builders import StubAtmosphere, solvers_with
    from aero_kernel.tests.test_stall_speed_engine import document

    logging.disable(logging.CRITICAL)
    build = shipped_build()
    print("  canon role of stall-speed:", build.model.quantity("calc:stall-speed").role)
    aircraft = AircraftInput.model_validate(
        {"airplane": document(), "values": {"aircraft-mass": 1.5, "altitude": 0.0, "stall-speed": 0.0}}
    )
    result = asyncio.run(evaluate(build, aircraft, ComputeRequest(quantities=("max-endurance",)),
                                  solvers=solvers_with(atmosphere=StubAtmosphere({0.0: 1.225}))))
    print("  compute with values['stall-speed'] = 0.0 -> input_errors:",
          [(e.category.value, e.code) for e in result.input_errors], "| quantities:", len(result.quantities))


def parent() -> None:
    for name, (v_s, min_speed) in CASES.items():
        print(f"\n[{name}] stall-speed = {v_s} m/s, stub solves level flight from {min_speed} m/s", flush=True)
        started = time.monotonic()
        try:
            done = subprocess.run([sys.executable, __file__, name], timeout=HARD_TIMEOUT_S,
                                  capture_output=True, text=True)
            print(done.stdout.rstrip())
            if done.returncode:
                print("  child exit code", done.returncode, "|", done.stderr.strip().splitlines()[-1:])
        except subprocess.TimeoutExpired as expired:
            out = expired.stdout.decode() if isinstance(expired.stdout, bytes) else (expired.stdout or "")
            print(out.rstrip())
            print(f"  DID NOT RETURN: killed by the hard timeout after {time.monotonic() - started:.1f} s "
                  f"(the 2 s asyncio.timeout never fired)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        child(sys.argv[1])
    else:
        parent()
        print("\n[reachability through the engine]")
        reachability()
