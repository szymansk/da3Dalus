# VSPAERO Cross-Validation Benchmark — Plan

**Status:** draft (not yet executed)
**Owner:** marc.szymanski@mac.com
**Created:** 2026-05-27

## Purpose

Offline, **one-shot** validation exercise: do our da3Dalus aerodynamic
calculations (AeroSandbox AeroBuildup + VLM) agree with the equivalent
VSPAERO CLI run on the same `.vsp3` geometry, and where reference data
exists, with **real wind-tunnel / flight-test values**?

Goal is **confidence**, not a permanent app feature. Lives in
`scripts/`, not in `app/`. No CI integration. No DB. No frontend.

## Out of scope

- Permanent VSPAERO dependency in the toolchain
- Building a VSPAERO comparator into the app UI
- Reverse-importing VSPAERO results into our DB
- Anything in `app/` or `frontend/`
- Validating the OpenVSP **importer** (geometric ±1 % checks already
  cover that — see `feedback_openvsp_import_rc_scope.md`)

## Reference aircraft (4-way set)

All four `.vsp3` files already live in `components/aircraft/vsp/`.

| # | Aeroplane | File | Hard anchors | Topology stress-test |
|---|---|---|---|---|
| 1 | **DG-101G** | `dg101g.vsp3` | Akaflieg flight polar, L/D = 38.3 @ 105 km/h, Re ≈ 1.5 × 10⁶ | High-AR sailplane |
| 2 | **Cessna 172** | `cessna172.vsp3` | WT-reports CD₀ = 0.0376, induced-factor 0.0607, max L/D ≈ 10.5 @ M = 0.32, Vs ≈ 30 m/s | Conventional GA |
| 3 | **Spitfire** | `spitfire.vsp3` | Shenstone "Aerodynamics of the Spitfire" (RAeS), CL_max ≈ 1.36 known | **Elliptical wing → e ≈ 1.0?** |
| 4 | **Ligeti Stratos** | `Stratos_UL_2025-11-29T11_54_22.123Z.vsp3` | Open-source spec sheet: L/D = 20, Vs = 58–61 km/h → **CL_max ≈ 1.45**, S = 7.52 m², MTOW 188 kg | **Closed-tandem / joined-tip Boxwing** |

> **Stratos caveat:** ATSB report on Ligeti's 1987 fatal crash flagged that
> production modifications were never wind-tunnel tested. Make sure the
> `.vsp3` represents the 1985 *prototype* (open-source release geometry),
> not the modified variant.

## Pipelines

Both run on the **same `.vsp3`** as single source of truth.

### Pipeline A — da3Dalus / AeroSandbox

```
.vsp3
  → app.services.openvsp_import (existing importer)
  → Aeroplane (DB-style schema)
  → app.services.aerosandbox_integration (build asb.Airplane)
  → AeroBuildup + VLM sweep (α ∈ [-2°, +12°], β = 0°)
  → CL, CD, CD_i, CM, x_np, e, stability derivatives
```

### Pipeline B — VSPAERO CLI

```
.vsp3
  → vspaero --setup ... → .vspaero file
  → vspaero --analysis ... → polar/.stab/.history output
  → parse → CL, CD, CD_i, CM, x_np, e, stability derivatives
```

Both pipelines must use **identical reference quantities** (S_ref,
c_ref, b_ref, x_cg). The single source of truth for these is the
ASB-side computation; we feed the exact same numbers into VSPAERO.

## Common test conditions (per aircraft)

| Aeroplane | Mach | Re (target chord) | α-sweep | β | Altitude |
|---|---|---|---|---|---|
| DG-101G | 0.085 (≈ 105 km/h) | 1.5 × 10⁶ | -2° … +12° (1° step) | 0 | 1500 m ISA |
| Cessna 172 | 0.20 (cruise) | ≈ 4 × 10⁶ | -2° … +14° (1° step) | 0 | sea level ISA |
| Spitfire | 0.30 | ≈ 8 × 10⁶ | -2° … +14° (1° step) | 0 | sea level ISA |
| Ligeti Stratos | 0.15 (cruise 180 km/h) | ≈ 1.5 × 10⁶ | -2° … +12° (1° step) | 0 | sea level ISA |

Per `feedback_aerobuildup_resolution.md`: if any polar fit looks
suspect, **increase α-resolution**, never loosen thresholds.

## Metrics compared per aircraft

| Metric | Source | Note |
|---|---|---|
| CL(α) curve | both | slope, abs value, CL₀ |
| CL_α (1/rad) | both, fit | small-α slope |
| CD(α), CD(CL²) polar | both | parasite + induced |
| CD₀ | both, fit | zero-lift drag |
| CD_i (Trefftz) | both | induced drag |
| Oswald e | both | from k = 1/(πARe) |
| CM(α), CM_α | both | pitching moment slope |
| x_np / static margin | both | from CM_α / CL_α |
| Stability derivatives | both (asb stab + .stab) | CL_q, CM_q where available |
| max L/D | both | and α at max L/D |

For the **two anchor cases** (DG-101G, Cessna 172) we also compare
to real data:

- **DG-101G**: L/D = 38.3 ± ? at the cruise point
- **Cessna 172**: CD₀ = 0.0376, max L/D = 10.5, Vs ≈ 30 m/s → CL_max ≈ 1.5
- **Spitfire**: CL_max ≈ 1.36, e ≈ 0.95–1.0 expected (elliptical)
- **Ligeti**: L/D = 20, CL_max ≈ 1.45 (from Vs)

## Deliverables

```
scripts/vspaero_benchmark/
├── PLAN.md                    ← this file
├── README.md                  ← how to run
├── run.py                     ← orchestrator (per-aircraft subcommand)
├── pipeline_asb.py            ← da3Dalus side
├── pipeline_vspaero.py        ← VSPAERO CLI side
├── compare.py                 ← merges + computes Δ
├── results/
│   ├── dg101g/
│   │   ├── asb_polar.csv
│   │   ├── vspaero_polar.csv
│   │   ├── plots/CL_alpha.png, drag_polar.png, CM_alpha.png
│   │   └── RESULTS.md         ← Δ-table + interpretation
│   ├── cessna172/   …
│   ├── spitfire/    …
│   └── ligeti_stratos/ …
└── SUMMARY.md                 ← final 4-way comparison overview
```

## Per-aircraft `RESULTS.md` skeleton

```
# {Aeroplane} — VSPAERO vs ASB vs Reference

## Setup
- Mach, Re, α-sweep, reference quantities — exact numbers
- VSPAERO version, ASB version

## Results table (CL_α, CD₀, CD_i@CL=0.5, e, x_np, max L/D)
| Metric | ASB | VSPAERO | Reference | Δ(ASB/ref) | Δ(VSPAERO/ref) |

## Plots
- CL(α) overlay
- Drag polar overlay
- CM(α) overlay

## Interpretation
- What matches, what doesn't, hypothesis why
- Assumption-diffs that explain residual delta
  (parasite drag model, viscous correction, panel resolution)
```

Per `feedback_design_error_feedback.md`: if either tool produces
non-physical results (k ≤ 0, e > 1.1), **flag it explicitly**, do
not silently substitute defaults.

## Sequencing — recommended order

1. **DG-101G first.** Strongest external anchor, existing community
   reference run (Luka, OpenVSP groups, 30 % VSPAERO underprediction).
   Reproducing that result first calibrates our setup before touching
   anything else.
2. **Cessna 172** — second strongest anchor (multiple WT reports).
3. **Spitfire** — tool-vs-tool with weak external anchor; tests
   elliptical-wing handling.
4. **Ligeti Stratos** — tool-vs-tool on boxwing topology; uses our
   own L/D = 20 anchor from open-source spec.

Stop after step 1 if the setup itself looks broken — no point
running 4 broken comparisons.

## Open decisions — recommended defaults

These can be revisited per aircraft if a comparison goes sideways.

### 1. VSPAERO version pin
**Use the VSPAERO that ships with the `openvsp` Python wheel
(currently 3.50 — see [[project-openvsp-api-discoveries-350]]).**
That way the geometry-to-VSPAERO path is identical to what OpenVSP
itself would produce. No separate install. Record the exact version
in each `RESULTS.md`.

### 2. Panel / VLM resolution
- **Default:** VSPAERO `NumWakeNodes=20`, `WakeNumIter=5`
  (defaults are 8 / 3 — see VSPAERO_API.md). VSPAERO handles the
  chord/span tessellation from the `.vsp3`'s own `Tess_U` / `Tess_W`
  parms per WingSect, so we trust the file's own resolution.
- **ASB VLM:** match with `chordwise_resolution=6`,
  `spanwise_resolution=20`, both cosine-spaced.
- **Convergence check:** for **DG-101G only**, run a resolution
  sweep (10 / 20 / 30 `NumWakeNodes`) on both tools. If CL_α changes
  >0.5 % between 20 and 30, bump the default to 30 for all
  aircraft. Otherwise lock at 20.

### 3. Viscous correction
**Run both variants — inviscid + viscous — and report separately.**
- **Inviscid pass** (`Viscous=false` in VSPAERO; ASB VLM alone):
  apples-to-apples comparison of CD_i, e, CL_α, x_np.
- **Viscous pass** (VSPAERO `Viscous=true` + parasite buildup;
  ASB AeroBuildup): CD₀, max L/D, total CD(α). Expect larger spread
  because the parasite models differ.

Headline metric for "do they agree" is the **inviscid pair**.
Viscous is informative but not the primary judgment.

### 4. Symmetry
**Full model in both, no half-model.** Cleanest comparison.
Compute cost is negligible for these geometries. Half-model would
only help if a tool struggles with file size, which it shouldn't.
Stratos Boxwing has no Y-symmetry plane to exploit anyway (the
joined tips break it for VLM).

### 5. Reference-point convention
**Single source of truth: read `x_cg`, `S_ref`, `b_ref`, `c_ref`
from the `.vsp3` `<Vehicle>` block.** Inject identical numbers into
both pipelines:
- VSPAERO: `Sref`, `Bref`, `Cref`, `Xcg`, `Ycg`, `Zcg` in the
  `.vspaero` file.
- ASB: `Airplane(xyz_ref=...)` and pass S/b/c into the
  `OperatingPoint` / problem definition.

Document the exact 6 numbers per aircraft at the top of
each `RESULTS.md`.

## Next step

Start with **DG-101G**, inviscid + viscous, default resolution.
If our VSPAERO L/D lands within ±5 % of Luka's ≈ 26 (Google-Groups
reference), the setup is calibrated and we proceed to Cessna 172.
If not, debug setup before touching the other three.

## Memory anchors

- [[feedback-asb-over-avl]] — ASB is our primary; VSPAERO is the
  external check, not a new dependency
- [[feedback-openvsp-import-rc-scope]] — importer scope decision;
  this benchmark is a **separate** activity, not importer validation
- [[feedback-aerobuildup-resolution]] — α-resolution over threshold
  loosening if curves don't fit
- [[feedback-design-error-feedback]] — surface unphysical e/k, don't
  silently fix
