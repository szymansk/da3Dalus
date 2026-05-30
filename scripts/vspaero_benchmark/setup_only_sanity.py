"""DG-101G VSPAERO setup-only sanity check.

Drives VSPAERO through the standard two-step workflow but sets
StopBeforeRun=1 so the solver writes the .vspaero setup file and
DegenGeom mesh, then exits without solving.

Verifies:
- .vsp3 reads cleanly
- Wing GeomID is discoverable
- Reference quantities pass through to VSPAERO
- Output files land where expected
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import openvsp as vsp

REPO_ROOT = Path(__file__).resolve().parents[2]
VSP_FILE = REPO_ROOT / "components" / "aircraft" / "vsp" / "dg101g.vsp3"
WORK_DIR = Path(__file__).parent / "results" / "_sanity_dg101g"
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Reference quantities — DG-101G, read from the .vsp3 Vehicle/Wing block.
S_REF = 11.064      # m^2
B_REF = 15.000      # m
C_REF = 0.7087      # m (TotalChord = Cave)
X_CG  = 2.0         # m, approx 25% MAC behind nose — placeholder for sanity check

# Akaflieg flight condition (Luka's OpenVSP-groups comparison point):
# 105 km/h, 1500 m ISA, Re_c ≈ 1.5e6
V_INF  = 29.17      # m/s (= 105 km/h)
MACH   = 0.087
RE_C   = 1.5e6
RHO    = 1.0581     # kg/m^3 (ISA 1500 m)

# Sweep
ALPHA_START = -2.0
ALPHA_END   = 12.0
ALPHA_NPTS  = 15


def main() -> int:
    os.chdir(WORK_DIR)
    print(f"working dir: {WORK_DIR}")
    print(f"reading:     {VSP_FILE}")
    if not VSP_FILE.exists():
        print("ERROR: vsp3 file not found", file=sys.stderr)
        return 2

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(VSP_FILE))

    # Find the main wing by name
    wing_ids = vsp.FindGeomsWithName("Wing")
    print(f"FindGeomsWithName('Wing') → {list(wing_ids)}")
    if not wing_ids:
        print("ERROR: no Wing geom found", file=sys.stderr)
        return 3

    # Step 1: VSPAEROComputeGeometry — VLM mode (thin)
    vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet",     [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL],  0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "Symmetry",    [1],            0)
    print("\nexec VSPAEROComputeGeometry …")
    cg_rid = vsp.ExecAnalysis("VSPAEROComputeGeometry")
    print(f"  result id: {cg_rid}")

    # Step 2: VSPAEROSweep — but STOP before solve
    vsp.SetAnalysisInputDefaults("VSPAEROSweep")

    # Geometry set
    vsp.SetIntAnalysisInput("VSPAEROSweep", "GeomSet",     [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "ThinGeomSet", [vsp.SET_ALL],  0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "Symmetry",    [1],            0)

    # Reference quantities — manual
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "RefFlag", [0],     0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Sref",    [S_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "bref",    [B_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "cref",    [C_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Xcg",     [X_CG],  0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Ycg",     [0.0],   0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Zcg",     [0.0],   0)

    # Atmosphere — SI override
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Rho",  [RHO],   0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Vinf", [V_INF], 0)

    # Single-point Mach / Re
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachStart", [MACH], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachEnd",   [MACH], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "MachNpts",  [1],    0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Machref",   [MACH], 0)

    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "ReCref",     [RE_C], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "ReCrefEnd",  [RE_C], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "ReCrefNpts", [1],    0)

    # α-sweep
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaStart", [ALPHA_START], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaEnd",   [ALPHA_END],   0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "AlphaNpts",  [ALPHA_NPTS],  0)

    # Solver
    vsp.SetIntAnalysisInput("VSPAEROSweep", "NumWakeNodes", [20], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "WakeNumIter",  [5],  0)

    # STOP before solve — sanity dry-run
    vsp.SetIntAnalysisInput("VSPAEROSweep", "StopBeforeRun", [1], 0)
    vsp.SetStringAnalysisInput("VSPAEROSweep", "RedirectFile",
                                ["vspaero_setup.log"], 0)

    print("\nexec VSPAEROSweep (StopBeforeRun=1) …")
    sw_rid = vsp.ExecAnalysis("VSPAEROSweep")
    print(f"  result id: {sw_rid}")

    print("\nfiles in work dir:")
    for f in sorted(WORK_DIR.iterdir()):
        print(f"  {f.name:<60} {f.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
