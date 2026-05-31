"""Isolated single-α VSPAERO test — WING ONLY.

Root-causes the NaN divergence seen on the full DG-101G model by
deleting the fuselage and both tails, leaving only the main wing,
and running a SINGLE angle of attack.

If a bare wing converges → the divergence comes from the
fuselage/tail thin-mesh interaction. If it still NaNs → the wing
geometry itself produces a degenerate VLM mesh.

Bounded by design: 1 α, low wake-iter count. The caller wraps this
in an RSS watchdog + wall-clock timeout so a divergent solve can
never balloon memory again.
"""

from __future__ import annotations

import sys
from pathlib import Path

import openvsp as vsp

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_VSP = REPO_ROOT / "components" / "aircraft" / "vsp" / "dg101g.vsp3"
WORKDIR = Path(__file__).parent / "results" / "_debug_wing_only"

# Single flight point (Akaflieg-ish) + single alpha
ALPHA_DEG = 2.0
MACH = 0.087
RE_C = 1.5e6
VINF = 29.17
RHO = 1.0581

# Reference quantities (wing-only → use the wing's own area/span/chord)
S_REF = 11.064
B_REF = 15.000
C_REF = 0.7087
X_CG = 2.0


def main() -> int:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    staged = WORKDIR / SRC_VSP.name
    staged.write_bytes(SRC_VSP.read_bytes())

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(staged))

    # Delete everything except the main Wing
    for gid in list(vsp.FindGeoms()):
        name = vsp.GetGeomName(gid)
        if name != "Wing":
            print(f"  deleting {name} ({gid})", flush=True)
            vsp.DeleteGeom(gid)
    vsp.Update()
    vsp.WriteVSPFile(str(staged), vsp.SET_ALL)

    remaining = [(g, vsp.GetGeomName(g)) for g in vsp.FindGeoms()]
    print(f"  remaining geoms: {remaining}", flush=True)

    # Step 1: ComputeGeometry (VLM, no extra mirroring — wing has Sym=2)
    vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet", [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL], 0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "Symmetry", [0], 0)
    print("[vspaero] ComputeGeometry (wing only) …", flush=True)
    vsp.ExecAnalysis("VSPAEROComputeGeometry")

    # Step 2: single-α sweep
    vsp.SetAnalysisInputDefaults("VSPAEROSweep")
    vsp.SetIntAnalysisInput("VSPAEROSweep", "GeomSet", [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "ThinGeomSet", [vsp.SET_ALL], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "Symmetry", [0], 0)

    vsp.SetIntAnalysisInput("VSPAEROSweep", "RefFlag", [0], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Sref", [S_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "bref", [B_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "cref", [C_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Xcg", [X_CG], 0)

    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Rho", [RHO], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Vinf", [VINF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachStart", [MACH], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachEnd", [MACH], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "MachNpts", [1], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "ReCref", [RE_C], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "ReCrefNpts", [1], 0)

    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaStart", [ALPHA_DEG], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaEnd", [ALPHA_DEG], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "AlphaNpts", [1], 0)

    vsp.SetIntAnalysisInput("VSPAEROSweep", "NumWakeNodes", [20], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "WakeNumIter", [3], 0)
    vsp.SetStringAnalysisInput("VSPAEROSweep", "RedirectFile", [str(WORKDIR / "wing_only.log")], 0)

    print(f"[vspaero] Sweep single α={ALPHA_DEG}° …", flush=True)
    rid = vsp.ExecAnalysis("VSPAEROSweep")

    rid_vec = vsp.GetStringResults(rid, "ResultsVec")
    print(f"  ResultsVec length: {len(rid_vec)}", flush=True)
    if rid_vec:
        sub = rid_vec[0]
        for field in ("Alpha", "CLtot", "CDtot", "CDi", "CMy"):
            vec = vsp.GetDoubleResults(sub, field)
            val = vec[-1] if vec else "MISSING"
            print(f"    {field:8} = {val}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
