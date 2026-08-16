# low-re-polar-backfill

> Use-case specification, nested under [`airfoil-catalog`](../requirements.md).
> Focuses on WHAT this slice does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: airfoil-catalog,
> `_reversa_sdd/data-dictionary.md` §Module: airfoil-catalog.

## Overview

`low-re-polar-backfill` is the **write side** of the catalogue: it turns a
directory of Selig `.dat` files into persisted rows — the airfoil itself, its
Re-independent geometry classification, and thirteen NeuralFoil polar rows per
airfoil across the absolute 40 k–750 k Reynolds grid. Everything it produces is
aircraft-independent and precomputed; the query side
([`suitability-search`](../suitability-search/requirements.md)) only reads it. 🟢

## Responsibilities

- Parse Selig `.dat` files into `(name, coordinates)`, naming by **file stem**. 🟢
- Import a directory of `.dat` files recursively, idempotently and resiliently,
  confined to `<project_root>/components`. 🟢
- Classify each airfoil into one of five frozen families from its geometry,
  in a fixed, load-bearing evaluation order. 🟢
- Detect reflex from camber-line **shape** (gh-834) and store `camber_at_te` as
  the camber value at **x = 0.9**. 🟢
- Sweep NeuralFoil across the 13-point absolute Re grid and extract the persisted
  polar metrics per `(airfoil, Re)`. 🟢
- Compute `min_analysis_confidence` as the **windowed** minimum over the
  attached-flow α range (gh-825). 🟢
- Stay idempotent and re-runnable through `(airfoil_name, reynolds)` uniqueness
  plus provenance columns, with an explicit `--force` escape for semantic
  re-backfills. 🟢
- Degrade to `[]` with a warning when AeroSandbox is unavailable. 🟢

**Explicitly NOT this slice's responsibility:** scoring, ranking, interpolation
to an arbitrary query Re, role tags or the caveat block
(→ [`suitability-search`](../suitability-search/requirements.md)); the
interactive single-airfoil endpoints
(→ [`neuralfoil-analysis`](../neuralfoil-analysis/requirements.md)); the
**aircraft-level** speed-band Re table (→ `polar_re_table_service`, gh-493 — a
different Re concept entirely).

## Business Rules

> Rule ids are inherited from [`../requirements.md`](../requirements.md); the
> "derives from" column names the module-level rule each row refines.

### The Reynolds concept this slice owns

- **BR-C1 — This slice is 2D per-airfoil, absolute Re.** 🟢 *(module BR-C1.)*
  Polars are computed over an **absolute Re grid 40 k–750 k** straight from
  NeuralFoil, independent of any aircraft. The aircraft-level speed-band table
  (`polar_re_table_service`, gh-493) is a **different concept** in which "Re" is
  a speed proxy at the main wing's MAC for a specific flight condition. Both
  `app/models/airfoil_low_re.py:8-14` and
  `app/services/airfoil_low_re_service.py:3-9` state this explicitly. **Do not
  conflate them.**

### Ingestion

- **BR-C2 — Selig format only.** 🟢 *(module BR-C2.)* `_parse_dat_file`
  (`app/services/airfoil_service.py:57-87`) skips the first line as a header;
  every subsequent line must yield two parseable floats or it is **silently
  skipped**; fewer than 3 lines **or** fewer than 3 valid coordinates raises
  `ValueError`. No normalisation and no re-panelling is performed.
  🟡 There is **no format sniffing** — a Lednicer-format file, whose first data
  line is a pair of surface-point counts rather than a coordinate, would be
  mis-parsed as coordinates rather than rejected.
- **BR-C3 — The canonical name is the file stem, not the Selig header.** 🟢
  *(module BR-C3.)* This matches how the CadQuery plugin looks airfoils up
  (`airfoil_service.py:57-87`).
- **BR-C4 — The airfoil directory is absolute and CWD-independent.** 🟢
  *(module BR-C4.)* `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`
  (`app/core/config.py:6-14`). The comment records the motivating bug:
  procedurally generated airfoils written by the OpenVSP importer landed outside
  a CWD-relative read directory and appeared missing.
- **BR-C5 — Import is confined to `<project_root>/components`.** 🟢
  *(module BR-C5.)* `import_directory` resolves the requested directory and
  raises `ValidationError` if it is not inside `components`
  (`airfoil_service.py:97-106`) — a directory-traversal guard. The check happens
  **before** any file is read.
- **BR-C6 — Import is resilient and case-insensitively deduplicated.** 🟢
  *(module BR-C6.)* Recursive `rglob("*.dat")`; existing names are skipped
  case-insensitively; a per-file `try/except` increments `errors`, records the
  filename in `error_files` and calls `db.rollback()` so the loop can continue
  (`airfoil_service.py:90-154`). `AirfoilImportResult.imported_names` carries
  `exclude=True` — internal only, never serialised
  (`app/schemas/airfoil.py:51`).

### Classification

- **BR-C7 — Five frozen family labels.** 🟢 *(module BR-C7.)*
  `flat_bottom | semi_symmetric | symmetric | cambered | reflexed`
  (`app/schemas/airfoil.py:69`).
- **BR-C8 — Evaluation order is load-bearing.** 🟢 *(module BR-C8.)*

  ```
  reflexed → symmetric → flat_bottom → semi_symmetric → cambered
  ```

  The symmetric test **must** fire before flat_bottom, because a perfectly
  symmetric section also passes the lower-surface linearity test
  (`airfoil_low_re_service.py:102-105, 120`). Reordering silently mislabels
  every symmetric section.
- **BR-C9 — The classifier thresholds are fixed constants.** 🟢
  *(module BR-C9.)*

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
  (gh-834).** 🟢 *(module BR-C10.)* The original code used `camber[-1]`, which is
  ≈0 for **every** sharp-TE airfoil, so only blunt/open-TE supercritical shapes
  were labelled reflexed while real flying-wing sections (MH60, E184, EH series)
  were missed. The replacement uses two signals over the aft chord
  (`airfoil_low_re_service.py:46-88`):

  ```
  Signal A (sharp-TE reflex):   camber(x = 0.9) / max_camber  <  0.06
                                NACA 4412 → 0.31 ;  Clark Y → 0.28
  Signal B (open/upturned TE):  quadratic coeff of the camber line over
                                x ∈ [0.5, 1]  >  +0.015,
                                guarded to airfoils above 2 % camber
                                Clark YH ≈ +0.039 ;  NACA 4412 ≈ −0.11
  ```

  Consequently `camber_at_te` is **stored as the camber value at x = 0.9**, not
  at the TE.
- **BR-C10a — The gh-834 fix changes stored data.** 🟢 Recorded in the code:
  stored `family` values change after this fix, so a `--force` re-backfill is
  required post-merge.

### Polar computation

- **BR-C11 — The NeuralFoil sweep signature is part of the contract.** 🟢
  *(module BR-C11.)*

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
- **BR-C12 — The backfill model size is `"xxxlarge"` and must not be
  collapsed.** 🟢 *(module BR-C12.)* The interactive endpoint uses `"large"`
  (`app/api/v2/endpoints/airfoils.py:111`, owned by
  [`neuralfoil-analysis`](../neuralfoil-analysis/requirements.md)). The docstring
  says **"do NOT collapse"** (l.428-431).
- **BR-C13 — `min_analysis_confidence` is windowed, not whole-sweep.** 🟢
  *(module BR-C13.)* It is the minimum over the attached-flow window
  `[alpha_attached_lo, alpha_attached_hi]`, because deep-stall confidence is
  irrelevant to operating-point performance. It falls back to the whole-sweep
  minimum when the window is undefined or has **fewer than 4** points
  (`_windowed_min_confidence`, l.524-566). Changing this semantics also required
  a re-backfill (l.445-456).
- **BR-C14 — The sweep degrades to `[]` without AeroSandbox.** 🟢
  *(module BR-C14.)* Import-guarded; returns an empty list with a warning on e.g.
  `linux/aarch64` (l.458-462, ADR 0017). It never raises.
- **BR-C15 — The Re grid is denser where the laminar bubble governs.** 🟢
  *(module BR-C15.)*

  ```
  low_re_grid = [40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k,
                 200k, 250k, 350k, 500k, 750k]      # 13 points
  ```

  "Dense below 250 k where the laminar-separation bubble governs; coarser above"
  (`app/settings.py:58-74`).
- **BR-C18 — `(airfoil_name, reynolds)` is unique, making the backfill
  idempotent.** 🟢 *(module BR-C18.)*
  `UniqueConstraint("airfoil_name", "reynolds")`
  (`app/models/airfoil_low_re.py:65`). `neuralfoil_model_size` and `n_crit` are
  stored as provenance so the backfill can skip up-to-date rows.
  🟡 A **semantic** change (gh-834 family, gh-825 windowed confidence) is *not*
  detectable this way and needs a manual `--force`.

### Persisted metrics

- **BR-C11a — The extracted metric set is fixed.** 🟢
  (`app/models/airfoil_low_re.py:88-105`.)

  | Metric | Definition |
  |---|---|
  | `ld_max` | `(L/D)_max` inside the trusted range |
  | `cl_max` | `CL_max` inside the trusted range |
  | `alpha_attached_lo` / `alpha_attached_hi` | degrees, the attached-flow window |
  | `drag_bucket_width` | **ΔCL where `CD ≤ 1.15 · CD_min`** |
  | `cd_min` | minimum drag coefficient |
  | `stall_gentleness` | `dCL/dα` just past the peak — **raw slope, not normalised**; ≈0 gentle, negative abrupt |
  | `cd0`, `k`, `cl0` | the parabolic fit `CD = cd0 + k·(CL − cl0)²` |
  | `cl_valid_lo` / `cl_valid_hi` | the fit's validity window |
  | `min_analysis_confidence` | the windowed minimum (BR-C13) |

  All are **nullable**; the provenance columns `neuralfoil_model_size`
  (default `"xxxlarge"`), `n_crit` (default `9.0`) and `computed_at` are not.

### Persistence

- **BR-C28 — The child tables key on the airfoil *name*, a natural key.** 🟢
  *(module BR-C28.)* `airfoil_geometry` and `airfoil_low_re_polar` use
  `ForeignKey("airfoils.name")` with `ondelete="CASCADE"` but **no**
  `ON UPDATE CASCADE`. 🟢 Renaming an airfoil would orphan its geometry and
  polars.
- **BR-C29 — There is no ORM relationship from `AirfoilModel` to its
  children.** 🟡 *(module BR-C29.)* Joins are done by name in the services.
  INFERRED deliberate — it avoids loading 1 665 × 13 polar rows — but nowhere
  documented.

## Functional Requirements

> The Priority column repeats the module-level MoSCoW so this slice is readable
> standalone. "Refines" names the module RF in
> [`../requirements.md`](../requirements.md).

| ID | Refines | Requirement | Priority | Acceptance criterion |
|----|---------|-------------|----------|----------------------|
| RF-01 | RF-01 | Parse a Selig `.dat` file into `(name, coordinates)`, naming by file stem | Must | A valid file yields ≥ 3 coordinate pairs; a 2-line file raises `ValueError` |
| RF-02 | RF-02 | Import a directory of `.dat` files recursively and idempotently | Must | `POST /airfoils/import` → 200 with `imported` / `skipped` / `errors` counts; a re-run reports all `skipped` |
| RF-03 | RF-03 | Refuse an import directory outside `<project_root>/components` | Must | A path outside `components` → 422 `validation_error`, before any file is read |
| RF-04 | RF-04 | Continue the import past a malformed file | Must | One broken file increments `errors` and appears in `error_files`; the remaining files still import |
| RF-05 | RF-05 | Classify an airfoil into one of the five families in the fixed evaluation order | Must | A symmetric section is labelled `symmetric`, not `flat_bottom` |
| RF-06 | RF-06 | Detect reflex from camber-line shape via Signals A and B | Must | MH60 / E184 are labelled `reflexed`; NACA 4412 and Clark Y are not |
| RF-07 | RF-07 | Store `camber_at_te` as the camber value at **x = 0.9** | Must | The stored value for a sharp-TE airfoil is non-zero |
| RF-08 | RF-08 | Compute per-`(airfoil, Re)` polar metrics from NeuralFoil across the 13-point grid | Must | 13 rows per airfoil; only α points with `analysis_confidence ≥ 0.90` feed the metrics |
| RF-09 | RF-09 | Persist `min_analysis_confidence` as the **windowed** minimum over the attached-flow window | Must | An airfoil with poor deep-stall confidence but a clean attached window scores high; a window with < 4 points falls back to the whole sweep |
| RF-10 | RF-10 | Keep the backfill idempotent via `(airfoil_name, reynolds)` uniqueness and provenance columns | Must | Re-running the backfill without `--force` skips up-to-date rows; `--force` rewrites them |
| RF-11 | RF-11 | Return `[]` with a warning when AeroSandbox is unavailable | Must | On a platform without ASB the sweep does not raise and the API stays up |
| RF-B1 | RF-08 | Extract the full fixed metric set, including the parabolic fit and its validity window | Must | A synthetic polar with a known parabola recovers `cd0`, `k`, `cl0`; `drag_bucket_width` matches the `CD ≤ 1.15·CD_min` rule |
| RF-B2 | RF-05 | Persist one `airfoil_geometry` row per airfoil (1:1) | Must | A second geometry row for the same airfoil is rejected at the DB level |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | The import directory must resolve inside `<project_root>/components` or the request is rejected before any read | `app/services/airfoil_service.py:97-106` | 🟢 |
| Correctness | The airfoil directory is resolved absolutely, not relative to the CWD, because CWD-relative reads hid procedurally generated airfoils | `app/core/config.py:6-14` | 🟢 |
| Correctness | Confidence is windowed to the attached-flow range, not the whole sweep | `app/services/airfoil_low_re_service.py:524-566` | 🟢 |
| Correctness | Only α points at or above the `0.90` confidence gate feed metric extraction | `airfoil_low_re_service.py:406-521` | 🟢 |
| Robustness | A malformed `.dat` file rolls back only its own insert and the import continues | `airfoil_service.py:90-154` | 🟢 |
| Robustness | A single unparseable line inside an otherwise valid file is skipped rather than failing the file | `airfoil_service.py:57-87` | 🟢 |
| Idempotence | `UniqueConstraint("airfoil_name", "reynolds")` plus provenance columns make the backfill re-runnable | `app/models/airfoil_low_re.py:65` | 🟢 |
| Portability | The NeuralFoil sweep is import-guarded and returns `[]` when AeroSandbox is missing | `airfoil_low_re_service.py:458-462` (ADR 0017) | 🟢 |
| Performance | No ORM relationship from `AirfoilModel` to its children, avoiding a 1 665 × 13 row load | `app/models/airfoil.py`, `airfoil_low_re.py` | 🟡 |
| Configurability | The Re grid, model size, `n_crit` and confidence gate are `pydantic-settings` fields with `.env` overrides | `app/settings.py:58-74` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Parsing a Selig dat file

  Scenario: A Selig file is parsed and named by its stem
    Given a file "components/airfoils/mh60.dat" whose first line is a title
    When it is parsed
    Then the airfoil name is "mh60"
    And the coordinates contain at least three pairs
    And the coordinates are not normalised or re-panelled

  Scenario: A single junk line is skipped silently
    Given a .dat file with twenty coordinate lines and one line of prose
    When it is parsed
    Then twenty coordinate pairs are returned
    And no error is raised

  Scenario: A file with too few coordinates is rejected
    Given a .dat file with only two parseable coordinate lines
    When it is parsed
    Then a ValueError is raised

Feature: Importing a directory

  Scenario: A directory is imported recursively
    Given a directory under components containing ten .dat files in nested folders
    When the import runs
    Then imported is 10
    And skipped is 0
    And errors is 0

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
    And the nine valid airfoils are persisted

  Scenario: Re-importing the same directory skips everything
    Given a directory already fully imported
    When the import runs again
    Then skipped equals the file count
    And imported is 0

  Scenario: Deduplication ignores case
    Given an airfoil named "MH60" already in the database
    When a file "mh60.dat" is imported
    Then it is skipped, not inserted

  Scenario: Internal names are not serialised
    Given a completed import
    When the result is serialised to JSON
    Then imported_names is absent from the body

Feature: Family classification

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
    Then Signal A reports a ratio of about 0.31
    And Signal B reports a quadratic coefficient of about -0.11
    And the family is not "reflexed"

  Scenario: An open trailing edge triggers Signal B
    Given a Clark YH section with more than two percent camber
    When it is classified
    Then Signal B reports a quadratic coefficient of about +0.039
    And the family is "reflexed"

  Scenario: Signal B does not fire on a low-camber section
    Given a section whose max camber is below two percent
    When it is classified
    Then Signal B is not evaluated
    # _REFLEX_B_MIN_CAMBER_PCT guards it

  Scenario: camber_at_te is measured at x = 0.9
    Given a sharp trailing edge section
    When its geometry is stored
    Then camber_at_te is non-zero
    # The old endpoint rule would have stored approximately zero

Feature: NeuralFoil sweep

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

  Scenario: A short attached window falls back to the whole sweep
    Given an attached-flow window containing three alpha points
    When min_analysis_confidence is computed
    Then it equals the whole-sweep minimum

  Scenario: The sweep degrades without AeroSandbox
    Given AeroSandbox is not installed
    When the sweep runs
    Then it returns an empty list
    And a warning is logged
    And no exception propagates

Feature: Idempotence

  Scenario: A second run writes nothing
    Given a fully backfilled airfoil whose rows record model size "xxxlarge" and n_crit 9.0
    When the backfill runs again without --force
    Then no row is written

  Scenario: A forced run rewrites every row
    Given the same fully backfilled airfoil
    When the backfill runs with --force
    Then all thirteen rows are recomputed

  Scenario: A duplicate grid point is rejected by the database
    Given an existing row for airfoil "mh60" at Re 100000
    When a second row for the same pair is inserted
    Then the database raises an integrity error
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| `.dat` parsing and directory import (RF-01…RF-04) | Must | Nothing in the module exists without the library; the CadQuery plugin resolves airfoils by file stem |
| The `components` traversal guard (RF-03) | Must | The only path in this slice that takes a filesystem location from the caller |
| Family classification with the fixed evaluation order (RF-05) | Must | The order is load-bearing — a reordering silently mislabels every symmetric section |
| gh-834 reflex detection and the x = 0.9 semantics (RF-06/RF-07) | Must | The previous rule missed every real flying-wing section; the `flying_wing` mission band ranks on `reflexed` |
| NeuralFoil sweep and the persisted metric set (RF-08/RF-B1) | Must | The precomputed polars are the entire basis of scoring downstream |
| Windowed confidence (RF-09) | Must | Whole-sweep confidence would reject good sections on deep-stall uncertainty that never occurs in operation |
| Backfill idempotence (RF-10) | Must | A non-idempotent backfill over 1 665 airfoils cannot be re-run safely after a semantic change |
| Graceful degradation without AeroSandbox (RF-11) | Must | The service must start on `linux/aarch64` (ADR 0017) |
| 1:1 geometry row per airfoil (RF-B2) | Must | The unique FK is what makes the classification single-valued |
| Case-insensitive dedup on import | Should | Prevents near-duplicate rows; a stricter exact match would still function |
| `imported_names` as internal-only output | Could | A convenience for the caller-side pipeline, deliberately excluded from the wire |
| Lednicer-format support | Won't | 🟡 Measured (`Q-AF-1`): all 1 665 bundled files are Selig (0 candidates), so this is theoretical for shipped data; still real for uploads — a Lednicer file is mis-parsed rather than rejected |
| Automatic semantic-staleness detection | Won't (today) | 🟡 Only `neuralfoil_model_size` and `n_crit` are provenance; meaning changes need a manual `--force` |
| Renaming an airfoil | Won't | The child tables key on the natural name without `ON UPDATE CASCADE` |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/airfoil_service.py` | `_parse_dat_file` (l.57-87), `import_directory` (l.90-154), traversal guard (l.97-106) | 🟢 |
| `app/services/airfoil_low_re_service.py` (1086 l.) | `classify_family` (l.120), evaluation order (l.102-105), reflex Signals A/B (l.46-88), `compute_airfoil_low_re` (l.406-521), model-size note (l.428-431), re-backfill note (l.445-456), `_windowed_min_confidence` (l.524-566), ASB import guard (l.458-462), `G`/`RHO` (l.39-40) | 🟢 |
| `app/models/airfoil.py` | `AirfoilModel` (l.6) | 🟢 |
| `app/models/airfoil_low_re.py` | `AirfoilGeometryModel` (l.33), `AirfoilLowRePolarModel` (l.65), metric list (l.88-105), the two-Re note (l.8-14) | 🟢 |
| `app/schemas/airfoil.py` | `AirfoilSummary` (l.28), `AirfoilRead` (l.37), `AirfoilImportResult` (l.51), `AirfoilFamily` (l.69) | 🟢 |
| `app/settings.py` | `low_re_grid` (l.58-74), `low_re_neuralfoil_model_size`, `low_re_n_crit`, `low_re_confidence_gate` | 🟢 |
| `app/core/config.py` | `AIRFOILS_DIR` (l.6-14) | 🟢 |
| `app/api/v2/endpoints/airfoils.py` | `POST /airfoils/import` | 🟢 |
| `components/airfoils/` | 1 665 `.dat` files | 🟢 confirmed by count |
| `app/services/polar_re_table_service.py` | — | n/a — a **different** Re concept (gh-493), owned elsewhere |
