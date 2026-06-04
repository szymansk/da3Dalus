# Low-Re Airfoil Suitability Scoring (precomputed) — Design Spec

- **Date:** 2026-06-04
- **Type:** Feature (enhancement)
- **Status:** Draft for GH Issue
- **Authority inputs:** `/aerosandbox-expert`, `/aerodynamics-expert`,
  `/rc-aircraft-designer` (hobbyist-level; defers to scholz/anderson on
  conflict)

## 1. Problem & Motivation

RC and UAV aircraft fly at **low Reynolds numbers** (Re ≈ 40k–700k), where a
"normal" model wing (chord 70–200 mm) lives mostly in the delicate **Re ≈
50k–250k** band. In this regime the laminar separation bubble dominates and an
airfoil that looks excellent in a high-Re polar can be unusable. da3Dalus
currently lets users pick an airfoil for a wing cross-section
(`AirfoilSelector`) with no guidance on whether that airfoil is actually
suitable at the chord/speed the model flies.

We want to **precompute a low-Re suitability dataset for every airfoil in the
database** using NeuralFoil, and expose a fast **search/ranking endpoint** that,
given a chord→Re (and optionally the model's mission + operating CL), returns
airfoils ranked by suitability. Precomputation runs **once** as a backfill and
again only when **new airfoils are imported**.

### Why NeuralFoil is appropriate (expert finding)

NeuralFoil was trained on ~7.9M XFoil cases; **Re 50k–1M is in the densely
sampled core** (interpolation, not extrapolation), Re is encoded as `ln(Re)`
(physically correct drag scaling), and it self-reports `analysis_confidence`
(0..1) that structurally drops when the laminar separation bubble is delicate.
Use `model_size="xxxlarge"` for scoring (CD error ~2% vs ~8% for small models;
an alpha sweep is a single batched call).

### Hard caveat (must be surfaced, not hidden)

NeuralFoil/XFoil is **steady and single-valued** — it CANNOT model hysteresis,
bubble bursting, unsteadiness, or surface roughness/turbulators. The result is a
**relative ranking instrument, not absolute truth**. Where
`min_analysis_confidence < ~0.85` across the operating range, the response must
flag "validate with XFoil / wind tunnel."

## 2. Scope

### In scope (backend vertical slice)
- Per-airfoil 2D NeuralFoil precomputation across an **absolute Re grid**.
- Compact persistence (scalar metrics + parabolic drag-polar fit) — Approach B.
- One-time **backfill** CLI + **import-time** recompute hook (new airfoils only).
- **Search/ranking endpoint** producing **three lenses**:
  1. Re-agnostic general low-Re quality (chord→Re only),
  2. Mission-weighted suitability,
  3. Target-CL suitability at one or more **operating points** (cruise +
     loiter/landing).
- Unification of the two airfoil sources (DB-backed + legacy filesystem `.dat`).

### Non-goals (explicitly deferred / out)
- **Frontend integration** (surfacing scores in `AirfoilSelector`, search UX) —
  separate follow-up ticket.
- **Automated XFoil fallback pipeline** — we only emit a confidence flag.
- Hysteresis / unsteady / roughness modelling — physically not captured.

### Distinction from existing code (avoid confusion)
The existing `app/services/polar_re_table_service.py` (gh-493) is **aircraft
level**: it rebins aircraft fine-sweep data into V-bands, where "Re" is a
speed-based *label* (Re_aircraft at the main-wing MAC). This feature is
different: **2D per-airfoil polars across an absolute Re grid**. The spec and
code docstrings must state this so the two Re concepts are not conflated. The
**OLS parabolic-polar fit** logic in `assumption_compute_service` /
`polar_re_table_service` is reused.

## 3. Data Model

Two new SQLAlchemy models + one Alembic migration. All NeuralFoil computation
happens once; only compact derived data is persisted (Approach B).

### 3.1 `airfoil_geometry` (Re-independent, 1:1 per airfoil)
| Column | Type | Notes |
|---|---|---|
| `airfoil_name` | String, unique, indexed, FK→`airfoils.name` | |
| `max_thickness_pct` | Float | reuse geometry-stats logic |
| `max_camber_pct` | Float | |
| `camber_at_te` | Float | reflex indicator (>0 → up-reflexed) |
| `family` | String (enum) | `flat_bottom` / `semi_symmetric` / `symmetric` / `cambered` / `reflexed` — heuristic classifier from coordinates |
| `computed_at` | DateTime(tz) | |

### 3.2 `airfoil_low_re_polar` (per `(airfoil_name, Re)`)
| Column | Type | Notes |
|---|---|---|
| `airfoil_name` | String, indexed, FK→`airfoils.name` | |
| `reynolds` | Float, indexed | absolute Re grid point |
| `ld_max` | Float | (L/D)_max within trusted range |
| `cl_max` | Float | within trusted range |
| `alpha_attached_lo`, `alpha_attached_hi` | Float | attached-flow α window (deg) |
| `drag_bucket_width` | Float | ΔCL where CD ≤ 1.15·CD_min |
| `cd_min` | Float | |
| `stall_gentleness` | Float | dCL/dα just past peak (≈0 gentle, very negative = abrupt) |
| `cd0`, `k`, `cl0` | Float | parabolic fit `CD = cd0 + k·(CL − cl0)²` |
| `cl_valid_lo`, `cl_valid_hi` | Float | CL range over which the fit is valid |
| `min_analysis_confidence` | Float | trust badge (0..1) |
| `neuralfoil_model_size` | String | e.g. `xxxlarge` |
| `n_crit` | Float | transition criterion used |
| `computed_at` | DateTime(tz) | for idempotent backfill |

Unique constraint on `(airfoil_name, reynolds)`.

### 3.3 Source unification
"Every airfoil in the DB" must be literally true. The backfill first imports
legacy `.dat` files from `components/airfoils/` into the `airfoils` table via
the existing `airfoil_service.import_directory()`, then scores against the DB.
After backfill, both sources are represented in `airfoils`.

## 4. Reynolds Grid

Derived from chord 60–300 mm (full RC/UAV envelope; normal-model focus 70–200
mm) at ISA-SL across RC/UAV speeds (≈8–30 m/s) → Re ≈ 40k–700k, concentrated
50k–250k. **Log-spaced grid, dense low, coarse high:**

```
{40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k, 200k, 250k, 350k, 500k, 750k}
```

13 points (~1.2–1.25× steps up to 250k, coarser above). Configurable in
`app/core/config.py`. Storage per point is tiny (Approach B) and NeuralFoil
covers the α×Re grid in one batched call per airfoil, so density is nearly free.
**Search-time interpolation is linear in `ln(Re)`** between grid points
(matches NeuralFoil's ln(Re) training); out-of-range Re clamps to the nearest
endpoint and is flagged.

## 5. Compute Service (`app/services/airfoil_low_re_service.py`)

For each airfoil and each grid Re:
1. α-sweep (e.g. −5°…+18°, fine) via
   `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=…, Re=…, mach=0,
   model_size="xxxlarge", n_crit=…)`.
2. **Gate every metric on `analysis_confidence ≥ 0.90`**; persist the minimum
   confidence over the swept range as the trust badge.
3. Extract the 7 scalar metrics (§3.2).
4. Fit the parabolic drag polar (reuse OLS from `assumption_compute_service`),
   record validity CL range.
5. Geometry (once per airfoil): thickness/camber (reuse geometry-stats logic) +
   `family` classifier from the camber line (symmetry, lower-surface flatness,
   TE reflex).

Platform guard: AeroSandbox/NeuralFoil are excluded on `linux/aarch64`
(`pyproject.toml`). The compute path must tolerate their absence (import guard);
fast tests mock the NeuralFoil boundary.

## 6. Three Runtime Lenses (computed in the search service)

The DB stores only raw/derived data; **all scoring formulae run at query time**
so weights can be tuned without recompute.

1. **Re-agnostic** — normalized low-Re quality from the scalar metrics at the
   xsec's interpolated Re. Pure ranking, mission-independent.
2. **Mission** — Re-agnostic score × mission weighting: `family` match +
   thickness-band fit + CL_max weight per mission type (trainer / sport /
   aerobatic / glider / flying-wing), driven by the model's mission preset.
   RC mappings are hobbyist heuristics (defer to scholz/anderson on conflict).
3. **Target-CL (per operating point)** — evaluated at the operating CL of one
   or more points: **cruise** and **loiter/landing**. Uses the parabolic fit for
   CD(CL_target), checks CL_target is within the attached range and inside the
   drag bucket. Operating CL derived from the model's **design assumptions**
   (CL from W/S & V at each point; exact field verified at implementation).

Each lens is returned as a separate field → "three simple displays." Cruise and
loiter/landing target-CL scores are returned separately.

## 7. Precompute / Backfill + Import Hook

- **Backfill:** idempotent CLI script under `scripts/` (Typer/Click style).
  Skips airfoils whose `computed_at` + `neuralfoil_model_size` are current.
  Progress logging; **no silent truncation** — if anything is skipped/capped it
  is logged.
- **Import hook:** after `import_directory()` in the `/airfoils/import`
  endpoint, **only newly imported** airfoils are scheduled for recompute via the
  existing `job_tracker` (debounced background job) — not the whole library.

## 8. Search / Ranking Endpoint

Thin endpoint → service → Pydantic schema (per python-conventions).

```
GET /airfoils/db/suitability
    ?chord_m=<float>&speed_ms=<float>          # → Re (required)
    [&aeroplane_id=<int>]                       # → mission preset + assumptions
    [&mission_type=<enum>]                      # explicit override / model-less
    [&target_cl_cruise=<float>]                 # explicit override / model-less
    [&target_cl_loiter=<float>]                 # explicit override / model-less
```

- No `aeroplane_id` and no overrides → **Re-agnostic lens only**.
- `aeroplane_id` → mission + target-CL lenses from the model's preset and design
  assumptions.
- Direct `mission_type` / `target_cl_*` query params allow **exploratory search
  without a saved aeroplane** (and override model-derived values).
- Returns airfoils ranked by score with: the three lenses (mission +
  per-operating-point target-CL when available), `min_analysis_confidence`,
  `family`, and a **caveat block** (§9).
- **Tip-Re < Root-Re flag** when the queried xsec belongs to a tapered wing.

## 9. Caveats in Response

Every response carries a `confidence` / `caveat` block stating: relative ranking
only; no hysteresis / bubble-bursting / roughness modelling; recommend XFoil /
wind-tunnel validation when `min_analysis_confidence < 0.85`.

## 10. Testing Strategy

- **Fast (mocked, no aero deps):** stub the NeuralFoil boundary with
  deterministic fake polars → metric extraction, parabolic fit, family
  classifier, three-lens scoring, endpoint ranking, import-hook scheduling.
  Keeps the SonarCloud `new_coverage` gate green without aero deps (the CI fast
  tier runs without AeroSandbox).
- **Slow (`@pytest.mark.slow`, real NeuralFoil):** a known low-Re airfoil (e.g.
  SD7037 / AG series) scores higher than a transonic airfoil (e.g. RAE2822) at
  Re ≈ 100k — physics sanity check.
- Reuse existing airfoil/aero test fixtures and the marker convention. Slow
  aero tests run sequentially (memory-heavy).

## 11. Acceptance Criteria

1. Backfill scores **all** DB airfoils, including legacy `.dat` migrated into
   the DB.
2. `GET /airfoils/db/suitability` returns a sensibly ranked list with the
   Re-agnostic lens; with `aeroplane_id` (or explicit params) it adds the
   mission lens and per-operating-point target-CL lenses.
3. Importing a new airfoil triggers automatic recompute of **only** that airfoil
   via the background job.
4. Every metric is gated on `analysis_confidence ≥ 0.90`; `min_analysis_confidence`
   and the caveat block are present in responses.
5. Backend coverage > 80% with at least the fast-mocked tests; one slow
   real-NeuralFoil physics-sanity test passes.
6. Code/docstrings clearly distinguish this 2D per-airfoil Re grid from the
   gh-493 aircraft-level `polar_re_table_service`.

## 12. Open Items for Implementation

- Verify the exact design-assumptions field(s) for operating CL (cruise,
  loiter/landing) when wiring the target-CL lens.
- Confirm the airfoil-family heuristic thresholds against a few known airfoils.
- Decide final mission-weight coefficients (start from RC-expert heuristics,
  tune; keep them in config so they can change without recompute).
