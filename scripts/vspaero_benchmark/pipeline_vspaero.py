"""VSPAERO side of the cross-validation benchmark.

Runs a VLM α-sweep on a .vsp3 file through the standard two-step
VSPAERO workflow (ComputeGeometry → Sweep) and emits a canonical CSV.

VSPAERO writes sidecar files (.vspaero, .vspgeom, .csf, .vkey, .polar,
.history, …) next to the .vsp3 — so we copy the source into a per-run
working directory first to keep components/aircraft/vsp/ clean.

Output CSV columns:
    alpha_deg, mach, re_cref, CLtot, CDtot, CDi, CMy, eff_e

Where eff_e is the span efficiency back-computed from CDi:
    e = CL² / (π · AR · CDi)   with AR = bref² / Sref
"""

from __future__ import annotations

import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import openvsp as vsp


@dataclass(frozen=True)
class FlightCondition:
    """A single Mach/Re/atmosphere point. α is swept separately."""

    name: str
    vinf_mps: float
    mach: float
    re_cref: float
    rho_kgm3: float


@dataclass(frozen=True)
class ReferenceQuantities:
    """All values in SI (m, m², m). Source: the .vsp3 Vehicle/Wing block."""

    s_ref_m2: float
    b_ref_m: float
    c_ref_m: float
    x_cg_m: float
    y_cg_m: float = 0.0
    z_cg_m: float = 0.0


@dataclass(frozen=True)
class SweepConfig:
    alpha_start_deg: float = -2.0
    alpha_end_deg: float = 12.0
    alpha_npts: int = 15
    num_wake_nodes: int = 20
    wake_num_iter: int = 5
    # 0 = no further mirroring (geometry is already full, e.g. Wing
    #     has Sym_Planar_Flag=2). 1 = mirror across XZ (for true
    #     half-model inputs like NASA's BertinSmith test wing).
    symmetry: int = 0


# Result-vector field names per per-α sub-result (verified against a
# converged DG-101G run). Each is a vector of length = WakeNumIter+1;
# we take [-1] (converged). NOTE the exact VSPAERO spellings:
#   moment   → "CMytot"   (not "CMy")
#   Reynolds → "FC_ReCref_" (not "ReCref")
# VSPAERO also exposes "L/D" and "E" (span efficiency) directly.
RESULT_FIELDS = (
    "Alpha",
    "Mach",
    "FC_ReCref_",
    "CLtot",
    "CDtot",
    "CDo",
    "CDi",
    "CMytot",
    "L/D",
    "E",
)

# Lifting-surface set: VSPAERO meshes a Fuselage as a degenerate thin
# VLM surface, which diverges the GMRES solve (verified on DG-101G).
# We run VLM on WING-type geoms only. The ASB side must mirror this
# (wings-only) for an apples-to-apples inviscid comparison.
LIFTING_SURFACE_SET = vsp.SET_FIRST_USER  # = 3
WING_TYPE_NAME = "Wing"


def _set_int(name: str, key: str, value: int) -> None:
    vsp.SetIntAnalysisInput(name, key, [value], 0)


def _set_double(name: str, key: str, value: float) -> None:
    vsp.SetDoubleAnalysisInput(name, key, [value], 0)


def _set_string(name: str, key: str, value: str) -> None:
    vsp.SetStringAnalysisInput(name, key, [value], 0)


def _stage_vsp_file(src: Path, workdir: Path) -> Path:
    """Copy .vsp3 to workdir so VSPAERO sidecars don't pollute components/."""
    workdir.mkdir(parents=True, exist_ok=True)
    dst = workdir / src.name
    shutil.copy2(src, dst)
    return dst


def _select_lifting_surfaces() -> int:
    """Flag all WING-type geoms into a dedicated set; return its index.

    Fuselages (and any non-wing geom) are excluded so VSPAERO's VLM only
    sees genuine lifting surfaces. Must be called after ReadVSPFile.
    """
    wing_names: list[str] = []
    for gid in vsp.FindGeoms():
        is_wing = vsp.GetGeomTypeName(gid) == WING_TYPE_NAME
        vsp.SetSetFlag(gid, LIFTING_SURFACE_SET, is_wing)
        if is_wing:
            wing_names.append(vsp.GetGeomName(gid))
    print(f"[vspaero] lifting surfaces (set {LIFTING_SURFACE_SET}): {wing_names}", flush=True)
    if not wing_names:
        raise RuntimeError("no WING-type geoms found — nothing to mesh")
    return LIFTING_SURFACE_SET


def _configure_compute_geometry(thin_set: int, symmetry: int) -> None:
    vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
    _set_int("VSPAEROComputeGeometry", "GeomSet", vsp.SET_NONE)  # VLM
    _set_int("VSPAEROComputeGeometry", "ThinGeomSet", thin_set)
    _set_int("VSPAEROComputeGeometry", "Symmetry", symmetry)


def _configure_sweep(
    ref: ReferenceQuantities,
    flight: FlightCondition,
    sweep: SweepConfig,
    thin_set: int,
    log_path: Path,
) -> None:
    vsp.SetAnalysisInputDefaults("VSPAEROSweep")

    # Geometry mode (VLM) — lifting surfaces only
    _set_int("VSPAEROSweep", "GeomSet", vsp.SET_NONE)
    _set_int("VSPAEROSweep", "ThinGeomSet", thin_set)
    _set_int("VSPAEROSweep", "Symmetry", sweep.symmetry)

    # Reference quantities — manual
    _set_int("VSPAEROSweep", "RefFlag", 0)
    _set_double("VSPAEROSweep", "Sref", ref.s_ref_m2)
    _set_double("VSPAEROSweep", "bref", ref.b_ref_m)
    _set_double("VSPAEROSweep", "cref", ref.c_ref_m)
    _set_double("VSPAEROSweep", "Xcg", ref.x_cg_m)
    _set_double("VSPAEROSweep", "Ycg", ref.y_cg_m)
    _set_double("VSPAEROSweep", "Zcg", ref.z_cg_m)

    # Atmosphere — SI override (defaults are imperial)
    _set_double("VSPAEROSweep", "Rho", flight.rho_kgm3)
    _set_double("VSPAEROSweep", "Vinf", flight.vinf_mps)

    # Single-point Mach / Re
    _set_double("VSPAEROSweep", "MachStart", flight.mach)
    _set_double("VSPAEROSweep", "MachEnd", flight.mach)
    _set_int("VSPAEROSweep", "MachNpts", 1)
    _set_double("VSPAEROSweep", "Machref", flight.mach)

    _set_double("VSPAEROSweep", "ReCref", flight.re_cref)
    _set_double("VSPAEROSweep", "ReCrefEnd", flight.re_cref)
    _set_int("VSPAEROSweep", "ReCrefNpts", 1)

    # α-sweep
    _set_double("VSPAEROSweep", "AlphaStart", sweep.alpha_start_deg)
    _set_double("VSPAEROSweep", "AlphaEnd", sweep.alpha_end_deg)
    _set_int("VSPAEROSweep", "AlphaNpts", sweep.alpha_npts)

    # Solver
    _set_int("VSPAEROSweep", "NumWakeNodes", sweep.num_wake_nodes)
    _set_int("VSPAEROSweep", "WakeNumIter", sweep.wake_num_iter)

    _set_string("VSPAEROSweep", "RedirectFile", str(log_path))


def run(
    vsp_file: Path,
    ref: ReferenceQuantities,
    flight: FlightCondition,
    workdir: Path,
    out_csv: Path,
    sweep: SweepConfig | None = None,
) -> Path:
    """Drive a VSPAERO VLM sweep and emit a normalized CSV.

    Returns the path to the CSV.
    """
    sweep = sweep or SweepConfig()
    staged = _stage_vsp_file(vsp_file, workdir)
    log_path = workdir / "vspaero_solve.log"

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(staged))

    thin_set = _select_lifting_surfaces()

    _configure_compute_geometry(thin_set, sweep.symmetry)
    print("[vspaero] ComputeGeometry …", flush=True)
    vsp.ExecAnalysis("VSPAEROComputeGeometry")

    _configure_sweep(ref, flight, sweep, thin_set, log_path)
    print(
        f"[vspaero] Sweep α=[{sweep.alpha_start_deg}, "
        f"{sweep.alpha_end_deg}]°×{sweep.alpha_npts} "
        f"M={flight.mach} Re={flight.re_cref:.2e} …",
        flush=True,
    )
    sweep_rid = vsp.ExecAnalysis("VSPAEROSweep")

    # Bulk CSV next to the staged .vsp3 (VSPAERO's own format) — kept as
    # a forensic artifact even though we emit our normalized CSV below.
    raw_csv = workdir / f"{staged.stem}_vspaero_raw.csv"
    vsp.WriteResultsCSVFile(sweep_rid, str(raw_csv))

    # ResultsVec mixes per-α force results with auxiliary sub-results
    # (span loading, group records) that lack force fields. Keep only
    # sub-results that carry the force fields AND a real Reynolds number
    # — that cleanly selects the converged α-points and avoids the
    # "Can't Find Name" stderr spam from probing the wrong sub-results.
    rid_vec = vsp.GetStringResults(sweep_rid, "ResultsVec")

    ar = (ref.b_ref_m**2) / ref.s_ref_m2
    rows: list[dict[str, float]] = []
    for sub_rid in rid_vec:
        names = set(vsp.GetAllDataNames(sub_rid))
        if not {"CLtot", "FC_ReCref_"} <= names:
            continue
        row: dict[str, float] = {}
        for field in RESULT_FIELDS:
            vec = vsp.GetDoubleResults(sub_rid, field) if field in names else []
            row[field] = float(vec[-1]) if len(vec) else math.nan
        if not (row["FC_ReCref_"] > 0):  # drops zero/duplicate junk rows
            continue
        # Cross-check: span-efficiency back-computed from Trefftz CDi,
        # alongside VSPAERO's own "E". e = CL² / (π · AR · CDi).
        cl, cdi = row["CLtot"], row["CDi"]
        row["eff_e_calc"] = (cl * cl) / (math.pi * ar * cdi) if cdi > 1e-9 else math.nan
        rows.append(row)

    if len(rows) != sweep.alpha_npts:
        print(
            f"[vspaero] WARNING: extracted {len(rows)} α-points, expected {sweep.alpha_npts}",
            flush=True,
        )

    # A diverged sub-result yields NaN forces — flag rather than hide.
    n_nan = sum(1 for r in rows if math.isnan(r["CLtot"]))
    if n_nan:
        print(
            f"[vspaero] WARNING: {n_nan}/{len(rows)} α-points are NaN "
            f"(solver did not converge) — see {log_path}",
            flush=True,
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w") as f:
        f.write("alpha_deg,mach,re_cref,CLtot,CDtot,CDo,CDi,CMytot,LoD,eff_e_vsp,eff_e_calc\n")
        for r in rows:
            f.write(
                f"{r['Alpha']:.6f},{r['Mach']:.6f},{r['FC_ReCref_']:.6e},"
                f"{r['CLtot']:.6f},{r['CDtot']:.6f},{r['CDo']:.6f},"
                f"{r['CDi']:.6f},{r['CMytot']:.6f},{r['L/D']:.6f},"
                f"{r['E']:.6f},{r['eff_e_calc']:.6f}\n"
            )

    print(f"[vspaero] wrote {out_csv}  ({len(rows)} rows, {n_nan} NaN)", flush=True)
    return out_csv


# ---------------------------------------------------------------------------
# DG-101G entry point — Akaflieg flight point per Luka's OpenVSP-groups ref
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

DG101G_VSP = REPO_ROOT / "components" / "aircraft" / "vsp" / "dg101g.vsp3"

DG101G_REF = ReferenceQuantities(
    s_ref_m2=11.064,
    b_ref_m=15.000,
    c_ref_m=0.7087,
    x_cg_m=2.0,  # placeholder ≈ 25 % MAC; sanity-check only
)

DG101G_FLIGHT_AKAFLIEG = FlightCondition(
    name="akaflieg_105kmh_1500m",
    vinf_mps=29.17,
    mach=0.087,
    re_cref=1.5e6,
    rho_kgm3=1.0581,  # ISA 1500 m
)


def main() -> int:
    workdir = Path(__file__).parent / "results" / "dg101g" / "vspaero"
    out_csv = Path(__file__).parent / "results" / "dg101g" / "vspaero_polar.csv"
    run(
        vsp_file=DG101G_VSP,
        ref=DG101G_REF,
        flight=DG101G_FLIGHT_AKAFLIEG,
        workdir=workdir,
        out_csv=out_csv,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
