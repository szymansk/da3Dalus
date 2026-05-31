"""Orchestrate the full benchmark for one or all reference aircraft.

For each aircraft:
  1. import .vsp3 → ASB airplane → derive S/b/c reference quantities
     and ISA atmosphere (rho, Mach, Re) so BOTH tools use identical refs
  2. run VSPAERO VLM sweep (wings-only)
  3. run ASB VortexLattice + AeroBuildup sweeps
  4. compare → comparison.json + RESULTS.md
Then build the HTML dashboard across all processed aircraft.

ALWAYS run this under run_with_watchdog.sh so a runaway VSPAERO solve
is hard-killed (see VSPAERO_API.md lesson 5):
    ./scripts/vspaero_benchmark/run_with_watchdog.sh \
        "PYTHONPATH=. poetry run python scripts/vspaero_benchmark/run_all.py [keys...]"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import aerosandbox as asb

from app.converters.openvsp_importer import import_vsp3
from app.converters.model_schema_converters import (
    aeroplane_schema_to_asb_airplane_async,
)

import pipeline_vspaero as pv
import pipeline_asb as pa
import compare as cmp
import build_dashboard as dash
from benchmark_config import AIRCRAFT, AircraftConfig, by_key


def _derive_refs_and_atmosphere(cfg: AircraftConfig):
    """Import once to read identical S/b/c and compute ISA atmosphere."""
    result = import_vsp3(cfg.vsp_path)
    airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=result.aeroplane)
    # Correct the reference to the main (largest) wing so VSPAERO and ASB
    # share identical, correct references (works around the converter's
    # first-wing-as-reference bug — see pipeline_asb.correct_reference_*).
    refs = pa.correct_reference_to_main_wing(airplane)
    s_ref = refs["s_ref"]
    b_ref = refs["b_ref"]
    c_ref = refs["c_ref"]
    # x_cg convention: wing-root LE x + 25 % c_ref (consistent for both tools)
    root_le_x = float(airplane.wings[0].xsecs[0].xyz_le[0]) if airplane.wings else 0.0
    x_cg = root_le_x + 0.25 * c_ref

    atmo = asb.Atmosphere(altitude=cfg.altitude_m)
    rho = float(atmo.density())
    a_sound = float(atmo.speed_of_sound())
    mu = float(atmo.dynamic_viscosity())
    mach = cfg.velocity_mps / a_sound
    re_cref = rho * cfg.velocity_mps * c_ref / mu
    return dict(
        s_ref=s_ref, b_ref=b_ref, c_ref=c_ref, x_cg=x_cg, rho=rho, mach=mach, re_cref=re_cref
    )


def run_one(cfg: AircraftConfig) -> None:
    print(f"\n{'=' * 70}\n{cfg.name}  [{cfg.key}]\n{'=' * 70}", flush=True)
    d = _derive_refs_and_atmosphere(cfg)
    print(
        f"  refs: S={d['s_ref']:.4f} b={d['b_ref']:.4f} c={d['c_ref']:.4f} x_cg={d['x_cg']:.4f}",
        flush=True,
    )
    print(f"  atmo: rho={d['rho']:.4f} Mach={d['mach']:.4f} Re={d['re_cref']:.3e}", flush=True)

    rdir = cfg.result_dir

    # 1) VSPAERO
    try:
        pv.run(
            vsp_file=cfg.vsp_path,
            ref=pv.ReferenceQuantities(
                s_ref_m2=d["s_ref"],
                b_ref_m=d["b_ref"],
                c_ref_m=d["c_ref"],
                x_cg_m=d["x_cg"],
            ),
            flight=pv.FlightCondition(
                name=cfg.key,
                vinf_mps=cfg.velocity_mps,
                mach=d["mach"],
                re_cref=d["re_cref"],
                rho_kgm3=d["rho"],
            ),
            workdir=rdir / "vspaero",
            out_csv=rdir / "vspaero_polar.csv",
            sweep=pv.SweepConfig(symmetry=cfg.symmetry),
        )
    except Exception as exc:
        print(f"  [vspaero] FAILED: {type(exc).__name__}: {exc}", flush=True)

    # 2) ASB (both methods)
    flight = pa.AsbFlightCondition(
        velocity_mps=cfg.velocity_mps,
        altitude_m=cfg.altitude_m,
        x_cg_m=d["x_cg"],
    )
    for method in ("vortex_lattice", "aerobuildup"):
        try:
            pa.run(
                vsp_file=cfg.vsp_path,
                flight=flight,
                method=method,
                out_csv=rdir / f"asb_{method}_polar.csv",
            )
        except Exception as exc:
            print(f"  [asb:{method}] FAILED: {type(exc).__name__}: {exc}", flush=True)

    # 3) compare
    try:
        comp = cmp.compare_aircraft(cfg)
        print(f"  [compare] {len(comp['sources'])} sources → RESULTS.md", flush=True)
    except Exception as exc:
        print(f"  [compare] FAILED: {type(exc).__name__}: {exc}", flush=True)


def main(argv: list[str]) -> int:
    keys = argv[1:]
    targets = [by_key(k) for k in keys] if keys else AIRCRAFT
    for cfg in targets:
        run_one(cfg)
    print(f"\n{'=' * 70}\nBuilding dashboard …\n{'=' * 70}", flush=True)
    dash.build_dashboard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
