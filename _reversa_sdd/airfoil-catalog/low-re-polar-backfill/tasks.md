# low-re-polar-backfill — Implementation Tasks

> Executable sequence to re-implement this slice from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Module-level task list: [`../tasks.md`](../tasks.md); the module ids
> **T-01…T-03** (persistence) and **T-05…T-19** (ingestion, classification,
> polars) are refined here.

## Prerequisites

- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). This slice is the one place that
      calls `db.rollback()` deliberately, per file, inside that transaction.
- [ ] `app/core/exceptions.py` hierarchy plus the shared error envelope —
      `ValidationError` → 422 for the traversal guard.
- [ ] `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"` — **absolute**, not
      CWD-relative (`app/core/config.py:6-14`).
- [ ] The 1 665 `.dat` files present under `components/airfoils/`.
- [ ] **AeroSandbox / NeuralFoil optionally** installed. Absent (e.g.
      `linux/aarch64`) the sweep must return `[]` with a warning and the API must
      still start (ADR 0017).
- [ ] `app/settings.py` (`pydantic-settings`, `.env`) carrying `low_re_grid`,
      `low_re_neuralfoil_model_size`, `low_re_n_crit`, `low_re_confidence_gate`.
      🟢 Decided (`Q-CC-4`): they move into the one merged `Settings` class.
- [ ] NumPy / SciPy for the metric extraction and the parabolic fit.

## Tasks

### Persistence

- [ ] **T-01 — `airfoils` table and `AirfoilModel.**
  `id` PK, `name` (**unique, indexed** — the natural key, derived from the
  `.dat` **file stem**), `coordinates` (JSON `list[[x, y]]`, Selig order,
  chord-normalised 0–1), `source_file` (nullable), `created_at` (tz-aware,
  default `now()`).
  - Legacy origin: `app/models/airfoil.py:6`; data-dictionary §Table `airfoils`
  - Definition of done: two files whose stems differ only in case cannot both
    insert; the stored name is the stem, never the Selig header line.
  - Confidence: 🟢

- [ ] **T-02 — `airfoil_geometry` table (1:1).**
  `id` PK (redeclared on the model), `airfoil_name` FK → `airfoils.name`
  `ON DELETE CASCADE`, **unique + indexed**; `max_thickness_pct`,
  `max_camber_pct`, `camber_at_te`, `family`, `computed_at`. All required. The
  two `*_pct` fields are **percent of chord**, not fractions.
  - Legacy origin: `app/models/airfoil_low_re.py:33`
  - Definition of done: a second geometry row for the same airfoil is rejected at
    the DB level; deleting the airfoil removes it.
  - Confidence: 🟢

- [ ] **T-03 — `airfoil_low_re_polar` table (1:N) with the idempotence key.**
  `id` PK, `airfoil_name` FK (indexed, `ON DELETE CASCADE`), `reynolds`
  (indexed), `UniqueConstraint("airfoil_name", "reynolds")`; nullable metrics
  `ld_max`, `cl_max`, `alpha_attached_lo`, `alpha_attached_hi`,
  `drag_bucket_width`, `cd_min`, `stall_gentleness`, `cd0`, `k`, `cl0`,
  `cl_valid_lo`, `cl_valid_hi`, `min_analysis_confidence`; non-null provenance
  `neuralfoil_model_size` (default `"xxxlarge"`), `n_crit` (default `9.0`),
  `computed_at`.
  - Legacy origin: `app/models/airfoil_low_re.py:65, 88-105`
  - Definition of done: re-running the backfill inserts nothing new; a
    conflicting `(name, Re)` pair raises at the DB level.
  - Confidence: 🟢

- [ ] **T-04 — Deliberately omit the ORM relationships.**
  `AirfoilModel` has **no** relationship to `AirfoilGeometryModel` or
  `AirfoilLowRePolarModel`; the services join by name.
  - Legacy origin: `app/models/airfoil.py`, `app/models/airfoil_low_re.py`
  - Definition of done: a comment records **why** (loading 1 665 × 13 polar rows
    on every airfoil read), so a future contributor does not "fix" it.
  - Confidence: 🟡 INFERRED deliberate; the rationale is not written down today.

### Ingestion

- [ ] **T-05 — `_parse_dat_file` (Selig only).**
  Skip the first line as a header; every later line must yield two parseable
  floats or it is **silently skipped**; fewer than 3 lines **or** fewer than
  3 valid coordinates raises `ValueError`. The canonical name is the **file
  stem**. No normalisation, no re-panelling.
  - Legacy origin: `app/services/airfoil_service.py:57-87`
  - Definition of done: a valid file yields ≥ 3 pairs named by stem; a 2-line
    file raises; a file with one junk line still imports the remaining
    coordinates.
  - Confidence: 🟢 (the absence of Lednicer detection is 🔴)

- [ ] **T-06 — `import_directory` traversal guard.**
  Resolve the requested directory and raise `ValidationError` unless it is inside
  `<project_root>/components`. Evaluate **before** any file is read.
  - Legacy origin: `airfoil_service.py:97-106`
  - Definition of done: importing `/etc` raises and reads no file (assert with a
    filesystem spy); importing `components/airfoils` succeeds.
  - Confidence: 🟢

- [ ] **T-07 — `import_directory` resilience and dedup.**
  Recursive `rglob("*.dat")`; case-insensitive dedup against existing names →
  `skipped`; a per-file `try/except` increments `errors`, records the filename
  in `error_files` and calls `db.rollback()` so the loop continues. Return
  `AirfoilImportResult(imported, skipped, errors, error_files, imported_names)`
  with `imported_names` marked `exclude=True`.
  - Legacy origin: `airfoil_service.py:90-154`; `app/schemas/airfoil.py:51`
  - Definition of done: 10 files with 1 corrupt yields
    `imported=9, skipped=0, errors=1`; a re-run yields `imported=0, skipped=9`;
    `imported_names` is absent from the serialised body; the 9 valid airfoils are
    committed despite the rollback on the 10th.
  - Confidence: 🟢

- [ ] **T-08 — Absolute, CWD-independent `AIRFOILS_DIR`.**
  `REPO_ROOT / "components" / "airfoils"`, with the comment recording the
  motivating bug (procedurally generated airfoils written by the OpenVSP importer
  landed outside a CWD-relative read directory and appeared missing).
  - Legacy origin: `app/core/config.py:6-14`
  - Definition of done: the directory resolves identically when the process is
    started from any working directory.
  - Confidence: 🟢

### Classification

- [ ] **T-09 — `classify_family` with the load-bearing evaluation order.**
  **reflexed → symmetric → flat_bottom → semi_symmetric → cambered.** The
  symmetric test must fire **before** flat_bottom, because a perfectly symmetric
  section also passes the lower-surface linearity test.
  - Legacy origin: `app/services/airfoil_low_re_service.py:102-105, 120`;
    `app/schemas/airfoil.py:69`
  - Definition of done: a NACA 0012 is `symmetric`, not `flat_bottom`; a test
    asserts the order explicitly so a reorder fails loudly.
  - Confidence: 🟢

- [ ] **T-10 — The eight classifier thresholds.**
  `_SYMMETRIC_MAX_CAMBER_PCT = 0.5`, `_SEMI_SYMMETRIC_MAX_CAMBER_PCT = 2.0`,
  `_FLAT_BOTTOM_Y_THRESHOLD = 0.002`, `_FLAT_BOTTOM_AFT_X_LO = 0.30`,
  `_FLAT_BOTTOM_QUAD_THRESHOLD = 0.005`,
  `_REFLEX_AFT_CAMBER_RATIO_MAX = 0.06`, `_REFLEX_AFT_CONCAVITY_MIN = 0.015`,
  `_REFLEX_B_MIN_CAMBER_PCT = 2.0`.
  - Legacy origin: `airfoil_low_re_service.py` (constant block)
  - Definition of done: each threshold has a boundary test just inside and just
    outside it.
  - Confidence: 🟢

- [ ] **T-11 — gh-834 reflex detection from camber-line shape.**
  Signal A: `camber(x = 0.9) / max_camber < 0.06` (NACA 4412 → 0.31, Clark Y →
  0.28). Signal B: quadratic coefficient of the camber line fitted over
  `x ∈ [0.5, 1]` `> +0.015`, guarded to airfoils above 2 % camber
  (Clark YH ≈ +0.039, NACA 4412 ≈ −0.11). Store `camber_at_te` as the camber
  value **at x = 0.9**, not at the TE.
  - Legacy origin: `airfoil_low_re_service.py:46-88` (gh-834)
  - Definition of done: MH60, E184 and an EH-series section are `reflexed`;
    NACA 4412 and Clark Y are not; a regression test pins the four reference
    numbers quoted above; a below-2 %-camber section never reaches Signal B.
  - Confidence: 🟢

- [ ] **T-12 — Document the re-backfill requirement.**
  Stored `family` and `camber_at_te` values change after T-11, so a `--force`
  re-backfill is required post-merge.
  - Legacy origin: `airfoil_low_re_service.py` (gh-834 note)
  - Definition of done: the CLI exposes `--force` and the change is recorded in
    the migration/runbook notes.
  - Confidence: 🟢

### Polar computation

- [ ] **T-13 — `compute_airfoil_low_re` signature and sweep.**

  ```python
  compute_airfoil_low_re(name, coords, re_grid, *,
                         model_size="xxxlarge", n_crit=9.0,
                         confidence_gate=0.90,
                         alpha_start=-5.0, alpha_end=18.0,
                         alpha_step=0.2) -> list[dict]
  ```

  Per Re point: `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=α_grid, Re=re,
  mach=0.0, n_crit=n_crit, model_size=model_size)`. Only α points with
  `analysis_confidence ≥ 0.90` feed metric extraction.
  - Legacy origin: `airfoil_low_re_service.py:406-521`
  - Definition of done: the defaults are reproduced exactly; a stubbed solver
    proves that sub-gate α points are excluded; the α grid spans `-5.0 … 18.0`
    in steps of `0.2`.
  - Confidence: 🟢

- [ ] **T-14 — The 13-point Re grid.**
  `[40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k, 200k, 250k, 350k, 500k, 750k]` —
  dense below 250 k where the laminar-separation bubble governs, coarser above.
  These are **absolute** Reynolds numbers, not the aircraft-level speed-band
  proxy of `polar_re_table_service` (gh-493).
  - Legacy origin: `app/settings.py:58-74`;
    `app/models/airfoil_low_re.py:8-14`
  - Definition of done: a full backfill produces exactly 13 rows per airfoil, and
    a comment records the two-Re-concepts distinction.
  - Confidence: 🟢

- [ ] **T-15 — Metric extraction.**
  `ld_max`, `cl_max`, `alpha_attached_lo/hi`, `drag_bucket_width` (**ΔCL where
  `CD ≤ 1.15·CD_min`**), `cd_min`, `stall_gentleness` (`dCL/dα` just past the
  peak — **raw slope, not normalised**), and the parabolic fit
  `CD = cd0 + k·(CL − cl0)²` with its validity window
  `[cl_valid_lo, cl_valid_hi]`.
  - Legacy origin: `app/models/airfoil_low_re.py:88-105`;
    `airfoil_low_re_service.py:406-521`
  - Definition of done: a synthetic polar with a known parabola recovers `cd0`,
    `k` and `cl0` within tolerance; `drag_bucket_width` matches the 1.15 rule;
    `stall_gentleness` is stored unnormalised.
  - Confidence: 🟢

- [ ] **T-16 — `_windowed_min_confidence`.**
  Minimum over `[alpha_attached_lo, alpha_attached_hi]`, **not** the whole
  sweep. Fall back to the whole-sweep minimum when the window is undefined or
  has fewer than **4** points.
  - Legacy origin: `airfoil_low_re_service.py:445-456, 524-566` (gh-825)
  - Definition of done: an airfoil with clean attached flow and poor deep-stall
    confidence reports a high `min_analysis_confidence`; a 3-point window falls
    back; a 4-point window does not.
  - Confidence: 🟢

- [ ] **T-17 — Pin the backfill model size to `"xxxlarge"`.**
  The interactive endpoint uses `"large"`
  (`app/api/v2/endpoints/airfoils.py:111`, owned by
  [`neuralfoil-analysis`](../neuralfoil-analysis/tasks.md)). The docstring says
  **"do NOT collapse"**.
  - Legacy origin: `airfoil_low_re_service.py:428-431`
  - Definition of done: a test asserts the two call sites use different sizes, so
    a future refactor cannot silently unify them.
  - Confidence: 🟢

- [ ] **T-18 — Import guard for AeroSandbox.**
  Return `[]` with a warning when ASB is unavailable; never raise.
  - Legacy origin: `airfoil_low_re_service.py:458-462` (ADR 0017)
  - Definition of done: with the import patched to raise, the sweep returns `[]`,
    a warning is logged, no row is written, and the API still serves every other
    route.
  - Confidence: 🟢

- [ ] **T-19 — Backfill idempotence and provenance.**
  Skip rows whose `neuralfoil_model_size` and `n_crit` already match; expose
  `--force` for semantic re-backfills.
  - Legacy origin: `app/models/airfoil_low_re.py:65`
  - Definition of done: a second run without `--force` writes nothing; with
    `--force` it rewrites every row.
  - Confidence: 🟢 (semantic staleness is undetectable — 🟡)

### REST layer

- [ ] **T-20 — `POST /airfoils/import`.**
  The only HTTP route this slice owns. Maps the traversal guard's
  `ValidationError` to **422**.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a path outside `components` returns 422
    `validation_error`; a valid path returns 200 with the counts.
  - Confidence: 🟢

- [ ] **T-21 — The batch sweep entry point.**
  A CLI/backfill operation over `compute_airfoil_low_re` with a `--force` flag;
  it has no HTTP route.
  - Legacy origin: `--force` referenced in the gh-834 / gh-825 notes;
    no sweep route in `app/api/v2/endpoints/airfoils.py`
  - Definition of done: the entry point is reachable from the command line, can
    target a single airfoil or the whole library, and honours `--force`.
  - Confidence: 🟡 INFERRED — the CLI module itself was not read; only its
    absence from the REST surface and the `--force` references are confirmed.

## Test Tasks

- [ ] **TT-01 — Happy path:** import `components/airfoils`, classify, backfill,
      and assert 1 airfoil row + 1 geometry row + 13 polar rows per file.
- [ ] **TT-02 — Failure:** an import path outside `components` returns 422 and
      reads no file.
- [ ] **TT-03 — Parse boundaries:** a 2-line file raises; exactly 3 valid
      coordinates passes; one junk line is skipped; the name is the stem, not the
      Selig header.
- [ ] **TT-04 — Import resilience:** 10 files with 1 corrupt →
      `imported=9, errors=1`, the filename in `error_files`, the other 9
      committed despite the rollback.
- [ ] **TT-05 — Import idempotence:** a second run reports all `skipped`,
      case-insensitively (`MH60` in the DB skips `mh60.dat`).
- [ ] **TT-06 — `imported_names` is excluded** from the serialised body.
- [ ] **TT-07 — Classification order:** NACA 0012 is `symmetric`, not
      `flat_bottom`; an explicit assertion of the five-step order.
- [ ] **TT-08 — Reflex reference set:** MH60 / E184 / EH-series → `reflexed`;
      NACA 4412 (ratio 0.31, quad −0.11) and Clark Y (0.28) → not reflexed;
      Clark YH (quad +0.039) → reflexed via Signal B.
- [ ] **TT-09 — Signal B guard:** a section below 2 % camber never evaluates
      Signal B.
- [ ] **TT-10 — `camber_at_te` is measured at x = 0.9** and is non-zero for a
      sharp-TE airfoil.
- [ ] **TT-11 — Classifier thresholds:** a boundary test just inside and just
      outside each of the eight constants.
- [ ] **TT-12 — Confidence gate:** α points below 0.90 do not contribute to any
      metric.
- [ ] **TT-13 — Windowed confidence:** clean attached flow plus poor deep stall
      scores high; a 3-point window falls back to the whole sweep; a 4-point
      window does not.
- [ ] **TT-14 — Metric extraction:** a synthetic parabolic polar recovers `cd0`,
      `k`, `cl0`; `drag_bucket_width` matches `CD ≤ 1.15·CD_min`;
      `stall_gentleness` is the raw unnormalised slope.
- [ ] **TT-15 — Re grid:** exactly 13 rows per airfoil, at the documented values.
- [ ] **TT-16 — Model-size split:** the backfill uses `"xxxlarge"`, the
      interactive endpoint `"large"`; the test fails if they are unified.
- [ ] **TT-17 — Missing AeroSandbox:** the sweep returns `[]`, warns, writes no
      row, and the API still serves.
- [ ] **TT-18 — Backfill idempotence:** a second run without `--force` writes
      nothing; `--force` rewrites all 13 rows.
- [ ] **TT-19 — DB-level uniqueness:** a duplicate `(airfoil_name, reynolds)`
      insert raises an integrity error.
- [ ] **TT-20 — Cascade:** deleting an airfoil removes its geometry row and all
      13 polar rows.
- [ ] **TT-21 — Absolute directory:** the library resolves identically from any
      working directory.

## Data Migration Tasks

- [ ] **TM-01 — Re-backfill after the gh-834 family change.** Stored `family`
      and `camber_at_te` values are wrong for every section computed under the
      old endpoint rule. Requires `--force`; the provenance columns cannot detect
      it. 🟢
- [ ] **TM-02 — Re-backfill after the gh-825 windowed-confidence change.**
      `min_analysis_confidence` changed meaning; the same `--force` run covers
      it. 🟢
- [ ] **TM-03 — Reconcile orphaned child rows.** Because
      `airfoil_geometry` / `airfoil_low_re_polar` key on `airfoils.name` with
      `ondelete=CASCADE` but **no** `ON UPDATE CASCADE`, any historical rename
      left orphans. Detect rows whose `airfoil_name` has no matching
      `airfoils.name`. 🟢 Renaming is **forbidden by convention** (`Q-AF-7`,
      maintainer-answered): the name is the airfoil's identity, referenced from
      wing cross-sections, imported `.dat` files, construction plans and the
      copilot's prompt tables. No rename route exists and none is added.
- [ ] **TM-04 — Verify the 1 665-file library is fully imported and classified.**
      Every `.dat` file should have exactly one `airfoils` row, one
      `airfoil_geometry` row and 13 `airfoil_low_re_polar` rows. 🟡
- [x] **TM-05 — Lednicer audit: clean.** 🟢 **Measured (`Q-AF-1`):** a scan
      replicating `_parse_dat_file` exactly over all **1 665 bundled files found
      0 Lednicer candidates**, 0 files with `|y| > 1.0`, 0 files with fewer than
      3 parsable points. Nothing in the shipped library is mis-parsed. The
      detection heuristic (first coordinate pair with both values > 1.0) is
      recorded so the check can be re-run against **uploaded** files, where the
      risk still exists.

## Suggested Order

1. **T-01 → T-04** first — the three tables. T-03's `UniqueConstraint` is what
   makes every later backfill re-runnable, so it must exist before any compute
   task. T-04 is a documentation decision, not code.
2. **T-05 → T-08** next — ingestion. Nothing downstream has data without it, and
   T-06's traversal guard is this slice's only client-supplied filesystem path,
   so it should land with the parser rather than after it. T-05 blocks T-07.
3. **T-09 → T-12** — classification. Pure geometry, no solver, fully testable on
   the CI **fast** tier. T-09 blocks T-11 (the reflex test runs first in the
   evaluation order, so the order must exist before the signals are wired).
   T-10 blocks T-11 (Signal A and B read two of the eight constants). T-12 is a
   runbook item, not code.
4. **T-13 → T-19** — the NeuralFoil sweep. Needs AeroSandbox and therefore
   belongs on the CI **slow** tier, except **T-18**, which must be verified
   *without* it. T-15 blocks T-16 (the attached window comes from the extracted
   metrics). T-14 blocks T-13's grid argument. This step can proceed in parallel
   with step 3 if the classifier is stubbed.
5. **T-20 → T-21** last — the REST route is thin and only wires T-06/T-07.
   T-21's CLI needs T-19's `--force` semantics settled first.

## Pending Gaps (🔴)

- **No Lednicer-format detection.** `_parse_dat_file` assumes Selig, so a
  Lednicer file's leading surface-point counts are read as coordinates and
  produce a silently wrong airfoil whose every downstream metric is then wrong
  but confidently reported. Should the parser sniff the format, or should
  non-Selig files be rejected explicitly?
- **Natural-key foreign keys without `ON UPDATE CASCADE`.**
  `airfoil_geometry` and `airfoil_low_re_polar` reference `airfoils.name`. Is
  renaming an airfoil forbidden by convention, or should the FK move to
  `airfoils.id`?
- **Two settings modules with overlapping responsibility.** `app/settings.py`
  holds this slice's `low_re_*` knobs while `app/core/config.py` holds
  `AIRFOILS_DIR`. The project convention names `core/config.py` as the single
  configuration home. Which is canonical?
- **Semantic re-backfills are invisible to the skip logic.** Only
  `neuralfoil_model_size` and `n_crit` are stored as provenance; a meaning change
  (gh-834, gh-825) needs a manual `--force`. Should a semantic version column be
  added so staleness is detectable?
- **The null-metric policy is unverified.** Every metric column is nullable,
  which implies a row is written even when no α point clears the `0.90`
  confidence gate — but the code path was not read. Is a null-metric row written,
  or is the airfoil skipped entirely at that Re?
- **The batch sweep entry point was not located.** It has no HTTP route and the
  `--force` flag is only referenced indirectly in code comments. Where does the
  backfill actually run from, and is it chunked or cancellable across the
  1 665 × 13 × 116 evaluation grid?
- **No documented rationale for the missing ORM relationships.** The omission
  looks deliberate (avoiding a 1 665 × 13 row load) but is not written down, so a
  future contributor may reintroduce it.
