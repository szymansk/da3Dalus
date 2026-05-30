# VSPAERO Python API — Reference for the Benchmark Pipeline

Findings from exploring the `openvsp` 3.50.2 Python wheel API and
the NASA V&V example scripts in
`~/Downloads/OpenVSP-3.50.2-MacOS/scripts/python_scripts/`.

## Two-step workflow

```python
import openvsp as vsp

vsp.ReadVSPFile("/path/to/aircraft.vsp3")

# Step 1: prepare geometry mesh for VSPAERO
vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet",     [vsp.SET_NONE], 0)   # VLM
vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL],  0)
vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "Symmetry",    [1], 0)              # XZ-symmetry
geom_rid = vsp.ExecAnalysis("VSPAEROComputeGeometry")

# Step 2: actual α-sweep
vsp.SetAnalysisInputDefaults("VSPAEROSweep")
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "GeomSet",     [vsp.SET_NONE], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "ThinGeomSet", [vsp.SET_ALL],  0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "RefFlag",     [0], 0)                     # manual ref
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Sref",        [S_ref_m2], 0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "bref",        [b_ref_m],  0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "cref",        [c_ref_m],  0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Xcg",         [x_cg_m],   0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Rho",         [1.225],    0)              # SI!
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "Vinf",        [V_inf_mps],0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaStart",  [-2.0],     0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaEnd",    [12.0],     0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "AlphaNpts",   [15],       0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachStart",   [Mach], 0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachEnd",     [Mach], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "MachNpts",    [1], 0)
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "ReCref",      [Re_cref], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "ReCrefNpts",  [1], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "WakeNumIter", [5], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "NumWakeNodes",[20], 0)
vsp.SetIntAnalysisInput   ("VSPAEROSweep", "Symmetry",    [1], 0)
sweep_rid = vsp.ExecAnalysis("VSPAEROSweep")
```

## Key inputs (relevant subset)

VSPAEROSweep has **80** inputs after `SetAnalysisInputDefaults`.
The ones we touch:

| Input | Type | Default | Set to | Note |
|---|---|---|---|---|
| `GeomSet` | INT | -1 | `SET_NONE` (VLM) / `SET_ALL` (Panel) | thick-surface set |
| `ThinGeomSet` | INT | 1 | `SET_ALL` (VLM) / `SET_NONE` (Panel) | thin-surface set |
| `RefFlag` | INT | 0 | **0** = manual ref / 1 = take from WingID | |
| `Sref` / `bref` / `cref` | DOUBLE | 100 / 1 / 1 | **per-aircraft, SI** | only used if RefFlag=0 |
| `WingID` | STRING | "" | only if RefFlag=1 | from `vsp.FindGeomsWithName(...)` |
| `Xcg` / `Ycg` / `Zcg` | DOUBLE | 0 | **per-aircraft, m** | moment reference point |
| `Rho` | DOUBLE | 0.002377 (slug/ft³ !) | **1.225** (SI) | imperial default → override |
| `Vinf` | DOUBLE | 100 | **per-aircraft, m/s** | |
| `Machref` | DOUBLE | 0.3 | per-aircraft | reference Mach |
| `MachStart`/`MachEnd`/`MachNpts` | | 0/0/1 | single value, Npts=1 | |
| `AlphaStart`/`AlphaEnd`/`AlphaNpts` | | 0/10/3 | **-2 / 12 / 15** | |
| `BetaStart`/`BetaEnd`/`BetaNpts` | | 0/0/1 | leave at defaults | β=0 |
| `ReCref`/`ReCrefEnd`/`ReCrefNpts` | | 1e7/2e7/1 | single Re, Npts=1 | |
| `Symmetry` | INT | 0 | **1** for XZ-symmetric / **0** for Stratos boxwing | enum |
| `NumWakeNodes` | INT | **8** | **20** | spanwise wake resolution |
| `WakeNumIter` | INT | 3 | 5 | wake relaxation iterations |
| `NCPU` | INT | 4 | 4 (machine has 8+) | |
| `RedirectFile` | STRING | `"stdout"` | `"./vspaero.log"` | so we can grep |
| `StopBeforeRun` | INT | 0 | **1** for dry-run debug | useful for setup-only |
| `MACFlag` | INT | 0 | 0 | use Cave (not MAC) for cref |

## Mode switch — VLM vs Panel

| Mode | `GeomSet` | `ThinGeomSet` |
|---|---|---|
| **VLM** (thin lifting surfaces) | `SET_NONE` | `SET_ALL` |
| **Panel** (thick body) | `SET_ALL` | `SET_NONE` |

For our benchmark: **VLM** is the apples-to-apples comparison with
ASB-VLM. Panel mode is an extra sanity check.

## Reading results

`ExecAnalysis("VSPAEROSweep")` returns a **top-level results ID** that
contains a vector of per-α sub-results plus aggregate metadata.

```python
# Bulk dump everything to CSV (simplest path):
vsp.WriteResultsCSVFile(sweep_rid, "/path/to/sweep.csv")

# Programmatic access:
rid_vec = vsp.GetStringResults(sweep_rid, "ResultsVec")
# rid_vec[i] is the result ID for α[i]

for sub_rid in rid_vec:
    alpha = vsp.GetDoubleResults(sub_rid, "Alpha")[-1]   # last wake-iter value
    CL    = vsp.GetDoubleResults(sub_rid, "CLtot")[-1]
    CD    = vsp.GetDoubleResults(sub_rid, "CDtot")[-1]
    CDi   = vsp.GetDoubleResults(sub_rid, "CDi")[-1]
    CM    = vsp.GetDoubleResults(sub_rid, "CMy")[-1]
    # ... see GetAllResultsNames() for full list
```

> **Important:** each per-α result's vectors hold the **wake-iteration
> history**. Use `[-1]` (last value) for the converged result.

### Other latest result sets after a Sweep run

```python
load_rid    = vsp.FindLatestResultsID("VSPAERO_Load")    # span loading
history_rid = vsp.FindLatestResultsID("VSPAERO_History") # convergence
# Span loading fields: "Yavg" (spanwise position), "cl", "cdi"
```

Known result-set names (from NASA tests):
- `VSPAERO_Polar` — main sweep results
- `VSPAERO_Load` — spanwise loading
- `VSPAERO_History` — solver convergence

## Unit handling (CRITICAL)

VSPAERO defaults are **Imperial** (Rho=0.002377 slug/ft³, Vinf=100 ft/s).
The geometry from `.vsp3` is in whatever units the file declares — most
of our reference files are **metric** (DG-101G, Cessna, Spitfire, Ligeti
all in meters).

**Rule:** override `Rho=1.225` and pass `Vinf` in m/s explicitly. As long
as `Rho`/`Vinf`/`S`/`b`/`c` are all consistent SI, the **dimensionless
coefficients** (`CLtot`, `CDtot`, `CMy`, …) come out correct. `ReCref`
is set explicitly so it's independent of Rho/Vinf consistency.

## Inputs we don't touch (all 80 listed)

The defaults for these are fine for our case: noise/unsteady/ground-
effect/propeller/preconditioner/stall-model/Tecplot/2DFEM all off,
auto-time-step on (irrelevant for steady), GMRES convergence factors at
1.0, far-field auto. If a benchmark misbehaves, revisit
`NonLinearConvergenceFactor` and `WakeRelax` first.

## Output-file location (gotcha)

VSPAERO writes its sidecar files (`.vspaero`, `.vspgeom`, `.csf`,
`.vkey`, later `.polar`, `.history`, `.stab`, `.load`, …)
**next to the source `.vsp3`** — *not* in the Python process's
current working directory. `os.chdir()` does not affect this.

For the benchmark, **copy each `.vsp3` to a per-run working
directory** before invoking VSPAERO, so the sidecars stay out of
`components/aircraft/vsp/`. The `RedirectFile` input controls only
the solver log, not the sidecar location.

Dry-run verified 2026-05-28: `setup_only_sanity.py` on DG-101G
produced a valid `dg101g.vspaero` with all SI reference quantities
(Sref=11.064, Cref=0.7087, Bref=15, Rho=1.0581, Vinf=29.17,
ReCref=1.5e6, AoA=-2…12 × 15 pts) passed through correctly.

## Hard-won lessons (DG-101G first run, 2026-05-28)

### 1. Exclude the fuselage from the VLM thin set
A Fuselage geom meshed into the VLM `ThinGeomSet` becomes a degenerate
thin lifting surface → GMRES residual goes NaN from wake-iter 2 → the
whole sweep returns NaN forces. **Fix:** flag only `Wing`-type geoms
into a dedicated set (`SET_FIRST_USER` = 3) via `SetSetFlag`, and use
that as `ThinGeomSet` for both ComputeGeometry and Sweep. Verified:
- full model (wing+tails+fuselage) → diverges, NaN
- wing only → converges, CL=1.09 @ 2°
- wing+tails, no fuselage → converges, CL=1.08, L/D=27.7, E=0.81 @ 2°

The ASB side must mirror this (lifting-surfaces-only) for a fair
inviscid VLM-vs-VLM comparison.

### 2. Symmetry = 0 for our .vsp3 files
Our reference models already store full geometry (`Sym_Planar_Flag=2`
on the wing). Setting VSPAERO `Symmetry=1` mirrors again → overlapping
panels. Use `Symmetry=0`. (NASA's BertinSmith uses `Symmetry=1` only
because its test wing is a true half-model.)

### 3. Result field names (not the obvious ones)
- moment   → `CMytot`     (not `CMy`)
- Reynolds → `FC_ReCref_` (not `ReCref`)
- `L/D` and `E` (span efficiency) are exposed directly.
Full list: 66 fields via `GetAllDataNames(sub_rid)`.

### 4. ResultsVec needs filtering
`GetStringResults(sweep_rid, "ResultsVec")` returns more entries than
α-points (per-α force results + span-loading + group records). Probing
force fields on the wrong ones spams `Error Code 5: Can't Find Name`.
**Fix:** keep only sub-results whose `GetAllDataNames` contains the
force fields AND whose `FC_ReCref_ > 0`.

### 5. Memory safety — never run an unbounded sweep
A diverging solve on the full (doubled) mesh ballooned to ~40 GB RAM
and was OOM-killed (first attempt). `ulimit -v` is **not enforced on
macOS**. Always wrap VSPAERO runs in an RSS watchdog that hard-kills
any `vspaero` process exceeding ~6 GB, plus a wall-clock timeout, and
verify convergence at a single α before launching a full sweep.

## Sources

- `~/Downloads/OpenVSP-3.50.2-MacOS/scripts/python_scripts/Constants.py`
- `~/Downloads/OpenVSP-3.50.2-MacOS/scripts/python_scripts/BertinSmithTest.py`
- `~/Downloads/OpenVSP-3.50.2-MacOS/scripts/python_scripts/HersheyTest.py`
- Live introspection via `vsp.GetAnalysisInputNames` + `GetAnalysisInputDoc`
