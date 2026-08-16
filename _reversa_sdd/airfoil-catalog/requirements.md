# airfoil-catalog

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: airfoil-catalog,
> `_reversa_sdd/data-dictionary.md` §Module: airfoil-catalog.

## Overview

`airfoil-catalog` owns the airfoil library — 1 665 Selig `.dat` files under
`components/airfoils/` — plus everything derived from it: geometry ingestion and
family classification, precomputed low-Reynolds polars from NeuralFoil over an
absolute 40 k–750 k Re grid, three independent suitability-scoring lenses, and
query-time role tags. It is the aircraft-independent half of the airfoil story:
nothing in this module knows about a specific aeroplane. 🟢

## Responsibilities

- Parse Selig `.dat` files and import a directory of them idempotently. 🟢
- Classify each airfoil into one of five frozen families from its geometry. 🟢
- Compute and persist per-`(airfoil, Re)` polar metrics from NeuralFoil across
  the 13-point absolute Re grid. 🟢
- Interpolate a polar to an arbitrary query Re, linearly in `ln(Re)`, clamping
  out-of-range queries and reporting the clamp. 🟢
- Rank a fleet of airfoils through the three scoring lenses and return a ranked
  list with an explicit caveat block. 🟢
- Compute role tags at query time from stored geometry and polars. 🟢
- Serve interactive NeuralFoil analysis and diagram endpoints for a single
  airfoil. 🟢

**Explicitly NOT this module's responsibility:** the *aircraft-level* speed-band
Re table (→ `polar_re_table_service`, gh-493, a different Re concept); wing
geometry or station airfoil assignment (→ `wing-design`); running the 3D
aerodynamic solvers (→ `aero-analysis`).

## Business Rules

### The two Reynolds concepts

- **BR-C1 — Do not conflate the two Re concepts.** 🟢 Stated explicitly in both
  `app/models/airfoil_low_re.py:8-14` and
  `app/services/airfoil_low_re_service.py:3-9`:
  - **This module (gh-821)** is *2D per-airfoil*: polars over an **absolute Re
    grid 40 k–750 k** straight from NeuralFoil, independent of any aircraft.
  - **`polar_re_table_service` (gh-493)** is *aircraft-level*: it re-bins
    aircraft fine-sweep data into speed-band labels where "Re" is a speed proxy
    at the main wing's MAC for a specific flight condition.

### Ingestion

- **BR-C2 — Selig format only.** 🟢 `_parse_dat_file`
  (`app/services/airfoil_service.py:57-87`) skips the first line as a header;
  every subsequent line must yield two parseable floats or it is **silently
  skipped**; fewer than 3 lines or fewer than 3 valid coordinates raises
  `ValueError`. No normalisation, no re-panelling.
  🟡 There is **no format sniffing** — a Lednicer-format file would be
  mis-parsed as coordinates. **Measured (`Q-AF-1`):** a scan replicating
`_parse_dat_file` exactly over all **1 665 bundled files found 0 Lednicer
candidates**, 0 files with `|y| > 1.0` and 0 files with fewer than 3 parsable
points — the bundled set is entirely Selig, so the risk is theoretical for
shipped data. It remains real for **uploaded** files, where a Lednicer header
row would be read as a coordinate pair.
- **BR-C3 — The canonical name is the file stem, not the Selig header.** 🟢
  This matches how the CadQuery plugin looks airfoils up
  (`airfoil_service.py:57-87`).
- **BR-C4 — The airfoil directory is absolute and CWD-independent.** 🟢
  `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`
  (`app/core/config.py:6-14`). The comment records the motivating bug:
  procedurally generated airfoils written by the OpenVSP importer landed outside
  a CWD-relative read directory and appeared missing.
- **BR-C5 — Import is confined to `<project_root>/components`.** 🟢
  `import_directory` resolves the requested directory and raises
  `ValidationError` if it is not inside `components`
  (`airfoil_service.py:97-106`) — a directory-traversal guard.
- **BR-C6 — Import is resilient and case-insensitively deduplicated.** 🟢
  Recursive `rglob("*.dat")`; existing names are skipped case-insensitively; a
  per-file `try/except` increments `errors` and calls `db.rollback()` so the loop
  continues (`airfoil_service.py:90-154`).

### Classification

- **BR-C7 — Five frozen family labels.** 🟢
  `flat_bottom | semi_symmetric | symmetric | cambered | reflexed`
  (`app/schemas/airfoil.py:69`).
- **BR-C8 — Evaluation order is load-bearing.** 🟢
  **reflexed → symmetric → flat_bottom → semi_symmetric → cambered**. The
  symmetric test must fire before flat_bottom because a perfectly symmetric
  section also passes the lower-surface linearity test
  (`airfoil_low_re_service.py:102-105, 120`).
- **BR-C9 — The classifier thresholds are fixed constants.** 🟢

  | Threshold | Value | Meaning |
  |---|---|---|
  | `_SYMMETRIC_MAX_CAMBER_PCT` | `0.5` | below → `symmetric` |
  | `_SEMI_SYMMETRIC_MAX_CAMBER_PCT` | `2.0` | below → `semi_symmetric` |
  | `_FLAT_BOTTOM_Y_THRESHOLD` | `0.002` | strict legacy lower-surface flatness |
  | `_FLAT_BOTTOM_AFT_X_LO` | `0.30` | start of the aft linearity window |
  | `_FLAT_BOTTOM_QUAD_THRESHOLD` | `0.005` | max quadratic coeff of the aft lower-surface fit → flat |
  | `_REFLEX_AFT_CAMBER_RATIO_MAX` | `0.06` | Signal A: `camber(x=0.9)/max_camber` below → reflexed |
  | `_REFLEX_AFT_CONCAVITY_MIN` | `0.015` | Signal B: min positive quadratic coeff of the camber line over `x ∈ [0.5, 1]` |
  | `_REFLEX_B_MIN_CAMBER_PCT` | `2.0` | Signal B guard — only fires above 2 % camber |

- **BR-C10 — Reflex is detected from camber-line *shape*, not the endpoint
  (gh-834).** 🟢 The original code used `camber[-1]`, which is ≈0 for **every**
  sharp-TE airfoil, so only blunt/open-TE supercritical shapes were labelled
  reflexed while real flying-wing sections (MH60, E184, EH series) were missed.
  The fix uses Signal A (sharp-TE reflex, ratio `< 0.06` — NACA 4412 scores 0.31,
  Clark Y 0.28) **plus** Signal B (open/upturned TE, positive quadratic
  coefficient `> 0.015` — Clark YH ≈ +0.039, NACA 4412 ≈ −0.11).
  `camber_at_te` is therefore stored as the camber value **at x = 0.9**, not at
  the TE (`airfoil_low_re_service.py:46-88`). Consequence recorded in the code:
  stored `family` values change after this fix, so a `--force` re-backfill is
  required post-merge.

### Polar computation

- **BR-C11 — The NeuralFoil sweep signature is part of the contract.** 🟢

  ```python
  compute_airfoil_low_re(name, coords, re_grid, *,
                         model_size="xxxlarge", n_crit=9.0,
                         confidence_gate=0.90,
                         alpha_start=-5.0, alpha_end=18.0,
                         alpha_step=0.2) -> list[dict]      # l.406-521
  ```

  Per Re grid point: `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=α_grid,
  Re=re, mach=0.0, n_crit=n_crit, model_size=model_size)`. Only α points with
  `analysis_confidence ≥ 0.90` feed metric extraction.
- **BR-C12 — Two model sizes coexist deliberately.** 🟢 The backfill uses
  `"xxxlarge"`; the interactive endpoint (`app/api/v2/endpoints/airfoils.py:111`)
  uses `"large"`. The docstring says **"do NOT collapse"** (l.428-431).
- **BR-C13 — `min_analysis_confidence` is windowed, not whole-sweep.** 🟢 It is
  the minimum over the attached-flow window
  `[alpha_attached_lo, alpha_attached_hi]`, because deep-stall confidence is
  irrelevant to operating-point performance. It falls back to the whole-sweep
  minimum when the window is undefined or has `< 4` points
  (`_windowed_min_confidence`, l.524-566). Changing this semantics also required
  a re-backfill (l.445-456).
- **BR-C14 — The sweep degrades to `[]` without AeroSandbox.** 🟢 Import-guarded;
  returns an empty list with a warning on e.g. `linux/aarch64`
  (l.458-462, ADR 0017).
- **BR-C15 — The Re grid is denser where the laminar bubble governs.** 🟢

  ```
  low_re_grid = [40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k,
                 200k, 250k, 350k, 500k, 750k]      # 13 points
  ```

  "Dense below 250 k where the laminar-separation bubble governs; coarser above"
  (`app/settings.py:58-74`).
- **BR-C16 — Interpolation is linear in `ln(Re)`.** 🟢 Matching NeuralFoil's
  training encoding (`airfoil_low_re_service.py:304-311`). Out-of-range queries
  are **clamped** to the nearest endpoint and the response reports
  `re_clamped = True` (`suitability_service._clamp_re_to_grid`, l.124-133).
- **BR-C17 — Query Re uses standard sea-level air.** 🟢

  ```
  Re = ρ·V·c / μ    with  ρ = 1.225 kg/m³,  μ = 1.81e-5 Pa·s
  ```

  (`suitability_service.py:74-75, 119-121`.) Physical constants shared with
  `endurance_service` and kept in sync by comment: `G = 9.80665`, `RHO = 1.225`
  (`airfoil_low_re_service.py:39-40`).
- **BR-C18 — `(airfoil_name, reynolds)` is unique, making the backfill
  idempotent.** 🟢 `UniqueConstraint("airfoil_name", "reynolds")`
  (`app/models/airfoil_low_re.py:65`). `neuralfoil_model_size` and `n_crit` are
  stored as provenance so the backfill can skip up-to-date rows.

### Scoring

- **BR-C19 — Only three lenses may drive the ranking.** 🟢
  `active_lens ∈ {re_agnostic, mission, target_cl_cruise}`. **Glide points never
  auto-rank** — `target_cl_best_glide` and `target_cl_min_sink` are display-only,
  so the default sort is never driven by an engine-out / min-sink contingency
  point (`app/schemas/airfoil.py:71-84`).
- **BR-C20 — Lens 1, `score_re_agnostic`** (l.831-891). Weighted sum of
  normalised metrics, renormalised by the weights actually present: 🟢

  | Component | Normalisation | Weight |
  |---|---|---|
  | `ld_max` | `min(ld_max / 60.0, 1)` | 0.35 |
  | `cl_max` | `min(cl_max / 1.5, 1)` | 0.25 |
  | `drag_bucket_width` | `min(bucket / 0.8, 1)` | 0.20 |
  | `stall_gentleness` | `clamp(1 + stall/0.15, 0, 1)` → 0 at `stall ≤ −0.15` | 0.10 |
  | `cd_min` | `min(0.008 / cd_min, 1)` | 0.10 |

  `score = Σ(v·w) / Σw`, clamped to `[0,1]`; `None` when no component is
  available.
- **BR-C21 — Lens 2, `score_mission`** (l.894-940): 🟢

  ```
  score_mission = re_agnostic × family_bonus × thickness_match × cl_bonus

  family_bonus    = 1.0 if family ∈ preferred_families else 0.7
  thickness_match = 1.0 inside [t_min, t_max]; outside: max(0, 1 − gap/5.0)
  cl_bonus        = (1 − cl_max_weight) + cl_max_weight · min(cl_max/1.5, 1)
  ```

  Mission bands (`app/settings.py:19-56`):

  | mission | t_min % | t_max % | `cl_max_weight` | preferred families |
  |---|---|---|---|---|
  | trainer | 11 | 14 | 0.70 | flat_bottom, semi_symmetric |
  | sport | 9 | 13 | 0.55 | semi_symmetric, cambered |
  | aerobatic | 8 | 12 | 0.40 | symmetric |
  | glider | 10 | 14 | 0.50 | cambered, semi_symmetric |
  | flying_wing | 8 | 13 | 0.50 | reflexed, symmetric |
  | slope_soarer | 8 | 12 | 0.45 | semi_symmetric, cambered |

- **BR-C22 — Lens 3, `score_target_cl`** (l.943-1009) is `Match × Efficiency`: 🟢

  ```
  cl_star   = best_ld_cl(cd0, k, cl0) = sqrt(cl0² + cd0/k)      (closed form, l.715-760)
  r         = CD(cl_target) / cd0                               (relative drag rise)
  r_poor    = settings.low_re_score_r_poor = 2.5
  tolerance = (drag_bucket_width / low_re_bucket_tolerance_ref = 0.6) × 0.5

  Match:  r ≤ 1        → 1.0
          within tol   → 1 − (r−1)/(r_poor−1)
          r ≥ r_poor   → 0.0, unless the CL_max fallback applies

  CL_max safety fallback (r ≥ r_poor and cl_max present):
          Match = clamp( (cl_max − cl_target) / 0.30 , 0, 1 )
          (low_re_score_cl_max_safety_band = 0.30)

  Efficiency = min( re_cd0_reference / cd0 , 1.0 )
  Final      = clamp(Match × Efficiency, 0, 1)
  ```

  `best_ld_cl` returns `None` for `cd0 ≤ 0` or `k ≤ 0` — the derivation is
  written out in full in the docstring (l.715-760). The CL_max fallback exists
  because glider min-sink CLs (`CL ≈ √3 · CL_md`) sit far above `cl_star`, so a
  pure drag-rise Match collapses to 0 even for excellent glider sections
  (l.977-997).
- **BR-C23 — The fleet reference is a robust percentile, not a minimum.** 🟢
  `compute_re_cd0_reference(polars_by_name, re_query, percentile=20.0)`
  (l.771-823) interpolates every airfoil to `re_query` and returns the **20th
  percentile** of the finite `cd0` values. Falls back to
  `_CD0_REFERENCE_FALLBACK = 0.020` on an empty fleet.
- **BR-C24 — Level-flight CL helper.** 🟢
  `CL = (m·g) / (0.5·ρ·V²·S)`, raising `ValueError` for non-positive `V` or `S`
  (`_level_flight_cl`, l.686-707).
- **BR-C25 — Confidence outranks score.** 🟢 Ranking sorts by
  `(confidence tier, −score)`, so a high-scoring low-confidence airfoil never
  outranks a trustworthy one (`suitability_service.py:629, 632`).
- **BR-C26 — The tip-stall caveat is always on.** 🟢 The score treats section CL
  as whole-wing CL (ideal elliptic, untwisted), ignoring the tip-Re CL_max
  collapse that governs tip-stall onset on tapered wings. The contract therefore
  **always** sets `ignores_tip_re_clmax_collapse = True` and exposes `tip_re_flag`
  plus `cl_max_margin = cl_max − max(target CLs)` (negative = stall risk)
  (`app/schemas/airfoil.py:6-17, 174-187`). `tip_re_flag` fires when
  `Re_tip < low_re_tip_re_abs_floor = 80 000` or the root→tip drop exceeds
  `low_re_tip_re_rel_drop = 50 000` (`app/settings.py:109-114`).

### Role tags

- **BR-C27 — Tags are computed at query time, never persisted.** 🟢 No DB
  column, no migration, no backfill (`app/services/airfoil_tags.py`, gh-835).
  Constants: `LOW_RE_UPPER_BOUND = 150 000`, `HIGH_RE_LOWER_BOUND = 500 000`,
  `LOW_RE_CONFIDENCE_GATE = 0.85`.

  | Tag | Rule |
  |---|---|
  | `v_stabilizer` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `6 ≤ t ≤ 15 %` |
  | `h_stabilizer` | identical gate — kept separate for UX filtering |
  | `acro` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `7 ≤ t ≤ 12 %` |
  | `winglet` | `t ≤ 10 %` ∧ `family ∈ {symmetric, semi_symmetric, reflexed}` ∧ `camber ≤ 3 %` ∧ ≥ 1 confident polar at `Re ≤ 150 k` |
  | `low_re` | ≥ 1 polar row `Re ≤ 150 k` with confidence ≥ 0.85 |
  | `high_re` | ≥ 1 polar row `Re ≥ 500 k` with confidence ≥ 0.85 — **explicitly marked approximate**, because the grid tops out at 750 k |

  Tags are returned **sorted** for determinism.

### Persistence

- **BR-C28 — The child tables key on the airfoil *name*, a natural key.** 🟢
  `airfoil_geometry` and `airfoil_low_re_polar` use
  `ForeignKey("airfoils.name")` with `ondelete="CASCADE"` but **no**
  `ON UPDATE CASCADE`. 🟢 Renaming an airfoil would break the relation — is
  renaming forbidden by convention?
- **BR-C29 — There is no ORM relationship from `AirfoilModel` to its children.**
  🟡 Joins are done by name in the services. INFERRED as deliberate (it avoids
  loading 1 665 × 13 polar rows), but nowhere documented.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Parse a Selig `.dat` file into `(name, coordinates)`, naming by file stem | Must | A valid file yields ≥ 3 coordinate pairs; a 2-line file raises `ValueError` |
| RF-02 | Import a directory of `.dat` files recursively and idempotently | Must | `POST /airfoils/import` → 200 with `imported` / `skipped` / `errors` counts; a re-run reports all `skipped` |
| RF-03 | Refuse an import directory outside `<project_root>/components` | Must | A path outside `components` → 422 `validation_error` |
| RF-04 | Continue the import past a malformed file | Must | One broken file increments `errors` and appears in `error_files`; the remaining files still import |
| RF-05 | Classify an airfoil into one of the five families in the fixed evaluation order | Must | A symmetric section is labelled `symmetric`, not `flat_bottom` |
| RF-06 | Detect reflex from camber-line shape via Signals A and B | Must | MH60 / E184 are labelled `reflexed`; NACA 4412 and Clark Y are not |
| RF-07 | Store `camber_at_te` as the camber value at **x = 0.9** | Must | The stored value for a sharp-TE airfoil is non-zero |
| RF-08 | Compute per-`(airfoil, Re)` polar metrics from NeuralFoil across the 13-point grid | Must | 13 rows per airfoil; only α points with `analysis_confidence ≥ 0.90` feed the metrics |
| RF-09 | Persist `min_analysis_confidence` as the **windowed** minimum over the attached-flow window | Must | An airfoil with poor deep-stall confidence but a clean attached window scores high |
| RF-10 | Keep the backfill idempotent via `(airfoil_name, reynolds)` uniqueness and provenance columns | Must | Re-running the backfill without `--force` skips up-to-date rows |
| RF-11 | Return `[]` with a warning when AeroSandbox is unavailable | Must | On a platform without ASB the sweep does not raise and the API stays up |
| RF-12 | Interpolate a polar to an arbitrary Re linearly in `ln(Re)` | Must | A query at the geometric mean of two grid points returns the arithmetic mean of the metric |
| RF-13 | Clamp an out-of-range Re and report `re_clamped = true` | Must | `Re = 10 000` clamps to 40 000 and sets the flag |
| RF-14 | Compute the query Re from chord and speed at sea level | Must | `Re = 1.225·V·c / 1.81e-5` |
| RF-15 | Rank a fleet through the selected lens and return `SuitabilityResponse` | Must | `GET /airfoils/db/suitability` → 200 with `query`, `caveat` and a ranked `results` list |
| RF-16 | Never let a glide point drive the ranking | Must | `active_lens` cannot take `target_cl_best_glide` or `target_cl_min_sink` |
| RF-17 | Sort by confidence tier first, score second | Must | A 0.95-score / low-confidence airfoil ranks below a 0.80-score / high-confidence one |
| RF-18 | Always emit the tip-stall caveat and `cl_max_margin` | Must | `ignores_tip_re_clmax_collapse` is `true` in every response |
| RF-19 | Flag a tip-Re risk from the absolute floor or the root→tip drop | Should | `Re_tip = 70 000` sets `tip_re_flag` |
| RF-20 | Compute role tags at query time and return them sorted | Should | A 9 % symmetric section carries `acro`, `v_stabilizer`, `h_stabilizer` |
| RF-21 | Serve interactive NeuralFoil analysis for one airfoil using the `"large"` model | Should | `GET /airfoils/{name}/neuralfoil/analysis` → 200; the model size differs from the backfill's |
| RF-22 | Serve NeuralFoil diagrams for one airfoil | Could | `GET /airfoils/{name}/neuralfoil/analysis/diagrams` → 200 |
| RF-23 | Serve geometry statistics and raw coordinates for one airfoil | Should | `GET /airfoils/{name}/geometry-stats` and `/coordinates` → 200 |
| RF-24 | Accept a `.dat` upload and serve a `.dat` download | Should | `POST /airfoils/datfile` → 201; `GET /airfoils/{name}/datfile` returns the Selig text |
| RF-25 | Answer whether an airfoil name is known | Could | `GET /airfoils/{name}/known` → 200 with a boolean |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | The import directory must resolve inside `<project_root>/components` or the request is rejected | `app/services/airfoil_service.py:97-106` | 🟢 |
| Correctness | The airfoil directory is resolved absolutely, not relative to the CWD, because CWD-relative reads hid procedurally generated airfoils | `app/core/config.py:6-14` | 🟢 |
| Correctness | Interpolation is linear in `ln(Re)` to match NeuralFoil's training encoding | `airfoil_low_re_service.py:304-311` | 🟢 |
| Correctness | Confidence is windowed to the attached-flow range, not the whole sweep | `airfoil_low_re_service.py:524-566` | 🟢 |
| Correctness | Out-of-range Re is clamped **and reported**, never silently extrapolated | `suitability_service.py:124-133` | 🟢 |
| Correctness | The fleet `cd0` reference is a 20th percentile, robust against a single outlier airfoil | `airfoil_low_re_service.py:771-823` | 🟢 |
| Robustness | A malformed `.dat` file rolls back only its own insert and the import continues | `airfoil_service.py:90-154` | 🟢 |
| Robustness | Trust is ranked above score, so a confident mediocre section beats an unreliable excellent one | `suitability_service.py:629, 632` | 🟢 |
| Robustness | The known modelling limitation (tip-Re CL_max collapse) is declared in every response rather than hidden | `app/schemas/airfoil.py:6-17, 174-187` | 🟢 |
| Idempotence | `UniqueConstraint("airfoil_name", "reynolds")` plus provenance columns make the backfill re-runnable | `app/models/airfoil_low_re.py:65` | 🟢 |
| Performance | No ORM relationship from `AirfoilModel` to its children, avoiding a 1 665 × 13 row load | `app/models/airfoil.py`, `airfoil_low_re.py` | 🟡 |
| Portability | The NeuralFoil sweep is import-guarded and returns `[]` when AeroSandbox is missing | `airfoil_low_re_service.py:458-462` (ADR 0017) | 🟢 |
| Configurability | Every low-Re knob is a `pydantic-settings` field with an `.env` override | `app/settings.py` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Ingestion

  Scenario: A Selig file is parsed and named by its stem
    Given a file "components/airfoils/mh60.dat" whose first line is a title
    When it is parsed
    Then the airfoil name is "mh60"
    And the coordinates contain at least three pairs

  Scenario: A file with too few coordinates is rejected
    Given a .dat file with only two parseable coordinate lines
    When it is parsed
    Then a ValueError is raised

  Scenario: Import outside the components directory is refused
    Given a request to import "/etc"
    When the import runs
    Then a ValidationError is raised
    And no file is read

  Scenario: A malformed file does not abort the import
    Given a directory of ten .dat files of which one is corrupt
    When the import runs
    Then imported is 9
    And errors is 1
    And the corrupt filename appears in error_files

  Scenario: Re-importing the same directory skips everything
    Given a directory already fully imported
    When the import runs again
    Then skipped equals the file count
    And imported is 0

Feature: Classification

  Scenario: A symmetric section is not mislabelled flat-bottom
    Given a NACA 0012 section
    When it is classified
    Then the family is "symmetric"
    # The symmetric test must fire before the flat_bottom test

  Scenario: A flying-wing section is recognised as reflexed
    Given an MH60 section
    When it is classified
    Then the family is "reflexed"

  Scenario: A conventional cambered section is not reflexed
    Given a NACA 4412 section
    When it is classified
    Then the family is not "reflexed"
    And camber_at_te is the camber value at x = 0.9

Feature: Polar computation

  Scenario: A backfill produces one row per grid point
    Given an airfoil with valid coordinates
    When the low-Re backfill runs
    Then thirteen airfoil_low_re_polar rows exist
    And each records neuralfoil_model_size "xxxlarge" and n_crit 9.0

  Scenario: Low-confidence alpha points are excluded
    Given a sweep in which some alpha points have analysis_confidence 0.5
    When metrics are extracted
    Then only points with confidence at least 0.90 contribute

  Scenario: Confidence is windowed to attached flow
    Given an airfoil with clean attached flow and poor deep-stall confidence
    When min_analysis_confidence is computed
    Then it reflects the attached window, not the whole sweep

  Scenario: The sweep degrades without AeroSandbox
    Given AeroSandbox is not installed
    When the sweep runs
    Then it returns an empty list
    And a warning is logged
    And no exception propagates

Feature: Interpolation and Re

  Scenario: Interpolation is logarithmic in Re
    Given polar rows at Re 100000 and Re 200000
    When I interpolate at Re equal to their geometric mean
    Then the result is the arithmetic mean of the two metric values

  Scenario: An out-of-range Re is clamped and reported
    Given a query Re of 10000
    When the suitability query is built
    Then the effective Re is 40000
    And re_clamped is true

Feature: Suitability ranking

  Scenario: A fleet is ranked through the mission lens
    Given a fleet of airfoils with polars and a mission of "trainer"
    When I GET /airfoils/db/suitability with active_lens "mission"
    Then the response status is 200
    And each result carries re_agnostic and mission scores in [0,1]
    And the caveat block sets ignores_tip_re_clmax_collapse true

  Scenario: Confidence outranks score
    Given airfoil A with score 0.95 in a low confidence tier
    And airfoil B with score 0.80 in a high confidence tier
    When the results are ranked
    Then B precedes A

  Scenario: A glide point cannot drive the ranking
    Given a request with active_lens "target_cl_min_sink"
    When it is validated
    Then it is rejected
    # ActiveLens admits only re_agnostic, mission and target_cl_cruise

  Scenario: A tip-Re risk is flagged
    Given a wing whose tip Reynolds number is 70000
    When the suitability query is built
    Then tip_re_flag is true

  Scenario: A negative CL_max margin signals stall risk
    Given a target CL of 1.4 and an airfoil cl_max of 1.2
    When the result is built
    Then cl_max_margin is -0.2

Feature: Role tags

  Scenario: A thin symmetric section earns the acro and stabiliser tags
    Given a symmetric airfoil with 9 percent thickness and 0.1 percent camber
    When tags are computed
    Then the tags include "acro", "v_stabilizer" and "h_stabilizer"
    And the tags are sorted

  Scenario: The high-Re tag is marked approximate
    Given an airfoil with a confident polar at Re 500000
    When tags are computed
    Then "high_re" is present
    And the contract records that the grid tops out at 750000
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| `.dat` parsing and directory import (RF-01…RF-04) | Must | Nothing in the module exists without the library; the CadQuery plugin resolves airfoils by file stem |
| The `components` traversal guard (RF-03) | Must | The only path in the module that takes a filesystem location from the caller |
| Family classification with the fixed evaluation order (RF-05) | Must | The order is load-bearing — a reordering silently mislabels every symmetric section |
| gh-834 reflex detection (RF-06/RF-07) | Must | The previous rule missed every real flying-wing section; `flying_wing` missions rank on `reflexed` |
| NeuralFoil sweep + persisted metrics (RF-08…RF-10) | Must | The precomputed polars are the entire basis of scoring; the backfill must be idempotent or it cannot be re-run |
| Windowed confidence (RF-09) | Must | Whole-sweep confidence would reject good sections on deep-stall uncertainty that never occurs in operation |
| `ln(Re)` interpolation and clamping (RF-12/RF-13) | Must | Linear-in-Re interpolation is wrong against NeuralFoil's encoding; silent extrapolation would fabricate data |
| Suitability ranking with the three lenses (RF-15/RF-16) | Must | The module's headline capability; the glide-point exclusion prevents a contingency point from driving the default sort |
| Confidence-first ordering (RF-17) | Must | A trustworthy result must never be displaced by an unreliable one |
| The always-on tip-stall caveat (RF-18) | Must | A declared modelling limitation, per ADR 0012 (warnings, not silent fallbacks) |
| Graceful degradation without AeroSandbox (RF-11) | Must | The service must start on `linux/aarch64` (ADR 0017) |
| Tip-Re flag (RF-19) | Should | A refinement of the caveat; the caveat itself already covers the limitation |
| Role tags (RF-20) | Should | Query-time UX filtering (gh-835); the ranking works without them |
| Interactive NeuralFoil analysis with the `"large"` model (RF-21) | Should | An interactive convenience distinct from the backfill; the size split is deliberate |
| Geometry stats, coordinates, `.dat` up/download (RF-23/RF-24) | Should | Supporting surfaces for the editor and the viewer |
| Diagrams and `known` (RF-22/RF-25) | Could | Diagnostic conveniences |
| Lednicer-format support | Won't | 🟡 Measured (`Q-AF-1`): all 1 665 bundled files are Selig (0 candidates), so this is theoretical for shipped data; still real for uploads — a Lednicer file is mis-parsed rather than rejected |
| Persisting role tags | Won't | Deliberately query-time: no column, no migration, no backfill (gh-835) |
| Renaming an airfoil | Won't | The child tables key on the natural name without `ON UPDATE CASCADE` |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/airfoil_service.py` | `_parse_dat_file` (l.57-87), `import_directory` (l.90-154) | 🟢 |
| `app/services/airfoil_low_re_service.py` (1086 l.) | `classify_family` (l.120), reflex rules (l.46-88), `compute_airfoil_low_re` (l.406-521), `_windowed_min_confidence` (l.524-566), `interpolate_polar_at_re` (l.304-311), `_level_flight_cl` (l.686-707), `best_ld_cl` (l.715-760), `compute_re_cd0_reference` (l.771-823), `score_re_agnostic` (l.831-891), `score_mission` (l.894-940), `score_target_cl` (l.943-1009) | 🟢 |
| `app/services/suitability_service.py` (709 l.) | `_clamp_re_to_grid` (l.124-133), query Re (l.74-75, 119-121), ranking (l.629, 632) | 🟢 |
| `app/services/airfoil_tags.py` | tag rules, `LOW_RE_UPPER_BOUND`, `HIGH_RE_LOWER_BOUND`, `LOW_RE_CONFIDENCE_GATE`, tag literal set (l.62-64) | 🟢 |
| `app/services/neuralfoil_cdcl_service.py` | cd/cl surrogate helper | 🟡 read only at the module-summary level |
| `app/api/v2/endpoints/airfoils.py` (1086 l.) | 12 routes; interactive `model_size="large"` (l.111) | 🟢 |
| `app/models/airfoil.py` | `AirfoilModel` (l.6) | 🟢 |
| `app/models/airfoil_low_re.py` | `AirfoilGeometryModel` (l.33), `AirfoilLowRePolarModel` (l.65), metric list (l.88-105), the two-Re note (l.8-14) | 🟢 |
| `app/schemas/airfoil.py` | `AirfoilSummary` (l.28), `AirfoilRead` (l.37), `AirfoilImportResult` (l.51), `AirfoilFamily` (l.69), `ActiveLens` (l.84), `TargetClProvenance` (l.93), `SuitabilityItem` (l.96), `SuitabilityQuery` (l.141), `SuitabilityCaveat` (l.174), `SuitabilityResponse` (l.190) | 🟢 |
| `app/settings.py` | `low_re_*` knobs (l.19-56, 58-74, 109-114) | 🟢 |
| `app/core/config.py` | `AIRFOILS_DIR` (l.6-14) | 🟢 |
| `components/airfoils/` | 1 665 `.dat` files | 🟢 confirmed by count |
| `app/services/polar_re_table_service.py` | — | n/a — a **different** Re concept (gh-493), owned elsewhere |
