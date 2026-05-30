"""Single-α VSPAERO test — WING + TAILS, fuselage removed.

Confirms whether the fuselage (meshed as a thin VLM surface) is the
sole cause of the full-model divergence. Also dumps the full list of
available result field names so the pipeline uses correct keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

import openvsp as vsp

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_VSP = REPO_ROOT / "components" / "aircraft" / "vsp" / "dg101g.vsp3"
WORKDIR = Path(__file__).parent / "results" / "_debug_no_fuselage"

ALPHA_DEG, MACH, RE_C, VINF, RHO = 2.0, 0.087, 1.5e6, 29.17, 1.0581
S_REF, B_REF, C_REF, X_CG = 11.064, 15.000, 0.7087, 2.0


def main() -> int:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    staged = WORKDIR / SRC_VSP.name
    staged.write_bytes(SRC_VSP.read_bytes())

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(staged))

    for gid in list(vsp.FindGeoms()):
        if vsp.GetGeomName(gid) == "Fuselage":
            print(f"  deleting Fuselage ({gid})", flush=True)
            vsp.DeleteGeom(gid)
    vsp.Update()
    vsp.WriteVSPFile(str(staged), vsp.SET_ALL)
    print(f"  remaining: {[vsp.GetGeomName(g) for g in vsp.FindGeoms()]}", flush=True)

    vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet",     [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL],  0)
    vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "Symmetry",    [0], 0)
    print("[vspaero] ComputeGeometry (no fuselage) …", flush=True)
    vsp.ExecAnalysis("VSPAEROComputeGeometry")

    vsp.SetAnalysisInputDefaults("VSPAEROSweep")
    vsp.SetIntAnalysisInput("VSPAEROSweep", "GeomSet",     [vsp.SET_NONE], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "ThinGeomSet", [vsp.SET_ALL],  0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "Symmetry",    [0], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "RefFlag", [0], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Sref", [S_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "bref", [B_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "cref", [C_REF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Xcg",  [X_CG], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Rho",  [RHO], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Vinf", [VINF], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachStart", [MACH], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachEnd",   [MACH], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "MachNpts",  [1], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "ReCref",     [RE_C], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "ReCrefNpts", [1], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaStart", [ALPHA_DEG], 0)
    vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaEnd",   [ALPHA_DEG], 0)
    vsp.SetIntAnalysisInput   ("VSPAEROSweep", "AlphaNpts",  [1], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "NumWakeNodes", [20], 0)
    vsp.SetIntAnalysisInput("VSPAEROSweep", "WakeNumIter",  [3], 0)
    vsp.SetStringAnalysisInput("VSPAEROSweep", "RedirectFile",
                                [str(WORKDIR / "no_fuselage.log")], 0)
    print(f"[vspaero] Sweep single α={ALPHA_DEG}° …", flush=True)
    rid = vsp.ExecAnalysis("VSPAEROSweep")

    rid_vec = vsp.GetStringResults(rid, "ResultsVec")
    print(f"  ResultsVec length: {len(rid_vec)}", flush=True)
    if rid_vec:
        sub = rid_vec[0]
        names = vsp.GetAllDataNames(sub)
        print(f"\n  === available result fields ({len(names)}) ===", flush=True)
        print("  " + ", ".join(sorted(names)), flush=True)
        print("\n  === values ===", flush=True)
        for field in ("Alpha", "CLtot", "CDtot", "CDi", "CMytot", "L/D", "E"):
            if field in names:
                vec = vsp.GetDoubleResults(sub, field)
                print(f"    {field:8} = {vec[-1] if vec else 'EMPTY'}", flush=True)
            else:
                print(f"    {field:8} = <not a field>", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
