# airfoil-catalog — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists: [`suitability-search/tasks.md`](suitability-search/tasks.md),
> [`low-re-polar-backfill/tasks.md`](low-re-polar-backfill/tasks.md),
> [`neuralfoil-analysis/tasks.md`](neuralfoil-analysis/tasks.md).

## Prerequisites

- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). The import path is the one place
      that calls `db.rollback()` deliberately, per file.
- [ ] `app/core/exceptions.py` hierarchy plus the shared error envelope.
- [ ] `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"` — **absolute**, not
      CWD-relative (`app/core/config.py:6-14`).
- [ ] The 1 665 `.dat` files present under `components/airfoils/`.
- [ ] **AeroSandbox / NeuralFoil optionally** installed. Absent (e.g.
      `linux/aarch64`) the sweep must return `[]` with a warning and the API must
      still start (ADR 0017).
- [ ] `app/settings.py` (`pydantic-settings`, `.env`) carrying every `low_re_*`
      knob. 🟢 Decided (`Q-CC-4`): they move into the one merged `Settings` class, alongside
      `app/core/config.py`.
- [ ] NumPy / SciPy for the metric extraction and the parabolic fit.

## Tasks

### Persistence

- [ ] **T-01 — `airfoils` table and `AirfoilModel`.**
  `id` PK, `name` (**unique, indexed** — the natural key, derived from the
  `.dat` **file stem**), `coordinates` (JSON `list[[x, y]]`, Selig order,
  chord-normalised 0–1), `source_file` (nullable), `created_at` (tz-aware,
  default `now()`).
  - Legacy origin: `app/models/airfoil.py:6`; data-dictionary §Table `airfoils`
  - Definition of done: two files whose stems differ only in case cannot both
    insert; the name is the stem, never the Selig header line.
  - Confidence: 🟢

- [ ] **T-02 — `airfoil_geometry` table (1:1).**
  `airfoil_name` FK → `airfoils.name` `ON DELETE CASCADE`, **unique + indexed**;
  `max_thickness_pct`, `max_camber_pct`, `camber_at_te`, `family`,
  `computed_at`. All metrics are **percent of chord**, not fractions.
  - Legacy origin: `app/models/airfoil_low_re.py:33`
  - Definition of done: a second geometry row for the same airfoil is rejected at
    the DB level; deleting the airfoil removes it.
  - Confidence: 🟢

- [ ] **T-03 — `airfoil_low_re_polar` table (1:N) with the idempotence key.**
  `airfoil_name` FK (indexed, `ON DELETE CASCADE`), `reynolds` (indexed),
  `UniqueConstraint("airfoil_name", "reynolds")`; nullable metrics `ld_max`,
  `cl_max`, `alpha_attached_lo/hi`, `drag_bucket_width`, `cd_min`,
  `stall_gentleness`, `cd0`, `k`, `cl0`, `cl_valid_lo`, `cl_valid_hi`,
  `min_analysis_confidence`; non-null provenance `neuralfoil_model_size`
  (default `"xxxlarge"`), `n_crit` (default `9.0`), `computed_at`.
  - Legacy origin: `app/models/airfoil_low_re.py:65, 88-105`
  - Definition of done: re-running the backfill inserts nothing new; a conflicting
    `(name, Re)` pair raises at the DB level.
  - Confidence: 🟢

- [ ] **T-04 — Deliberately omit the ORM relationships.**
  `AirfoilModel` has **no** relationship to `AirfoilGeometryModel` or
  `AirfoilLowRePolarModel`; the services join by name.
  - Legacy origin: `app/models/airfoil.py`, `airfoil_low_re.py`
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
    file raises; a file with one junk line still imports.
  - Confidence: 🟢 (the absence of Lednicer detection is 🔴)

- [ ] **T-06 — `import_directory` traversal guard.**
  Resolve the requested directory and raise `ValidationError` unless it is inside
  `<project_root>/components`.
  - Legacy origin: `airfoil_service.py:97-106`
  - Definition of done: importing `/etc` raises before any file is read;
    importing `components/airfoils` succeeds.
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
    `imported_names` is absent from the serialised body.
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
  0.28). Signal B: quadratic coefficient of the camber line over `x ∈ [0.5, 1]`
  `> +0.015`, guarded to airfoils above 2 % camber (Clark YH ≈ +0.039,
  NACA 4412 ≈ −0.11). Store `camber_at_te` as the camber value **at x = 0.9**,
  not at the TE.
  - Legacy origin: `airfoil_low_re_service.py:46-88` (gh-834)
  - Definition of done: MH60, E184 and an EH-series section are `reflexed`;
    NACA 4412 and Clark Y are not; a regression test pins the four reference
    ratios quoted above.
  - Confidence: 🟢

- [ ] **T-12 — Document the re-backfill requirement.**
  Stored `family` values change after T-11, so a `--force` re-backfill is
  required post-merge.
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
    proves that sub-gate α points are excluded.
  - Confidence: 🟢

- [ ] **T-14 — The 13-point Re grid.**
  `[40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k, 200k, 250k, 350k, 500k, 750k]` —
  dense below 250 k where the laminar-separation bubble governs, coarser above.
  - Legacy origin: `app/settings.py:58-74`
  - Definition of done: a full backfill produces exactly 13 rows per airfoil.
  - Confidence: 🟢

- [ ] **T-15 — Metric extraction.**
  `ld_max`, `cl_max`, `alpha_attached_lo/hi`, `drag_bucket_width` (ΔCL where
  `CD ≤ 1.15·CD_min`), `cd_min`, `stall_gentleness` (`dCL/dα` just past the
  peak — **raw slope, not normalised**), and the parabolic fit
  `CD = cd0 + k·(CL − cl0)²` with its validity window
  `[cl_valid_lo, cl_valid_hi]`.
  - Legacy origin: `app/models/airfoil_low_re.py:88-105`;
    `airfoil_low_re_service.py:406-521`
  - Definition of done: a synthetic polar with a known parabola recovers `cd0`,
    `k` and `cl0` within tolerance; `drag_bucket_width` matches the 1.15 rule.
  - Confidence: 🟢

- [ ] **T-16 — `_windowed_min_confidence`.**
  Minimum over `[alpha_attached_lo, alpha_attached_hi]`, **not** the whole
  sweep. Fall back to the whole-sweep minimum when the window is undefined or
  has fewer than **4** points.
  - Legacy origin: `airfoil_low_re_service.py:445-456, 524-566` (gh-825)
  - Definition of done: an airfoil with clean attached flow and poor deep-stall
    confidence reports a high `min_analysis_confidence`; a 3-point window falls
    back.
  - Confidence: 🟢

- [ ] **T-17 — Keep the two model sizes separate.**
  The backfill uses `"xxxlarge"`; the interactive endpoint uses `"large"`
  (`app/api/v2/endpoints/airfoils.py:111`). The docstring says
  **"do NOT collapse"**.
  - Legacy origin: `airfoil_low_re_service.py:428-431`
  - Definition of done: a test asserts the two call sites use different sizes,
    so a future refactor cannot silently unify them.
  - Confidence: 🟢

- [ ] **T-18 — Import guard for AeroSandbox.**
  Return `[]` with a warning when ASB is unavailable; never raise.
  - Legacy origin: `airfoil_low_re_service.py:458-462` (ADR 0017)
  - Definition of done: with the import patched to raise, the sweep returns `[]`,
    a warning is logged and the API still serves every other route.
  - Confidence: 🟢

- [ ] **T-19 — Backfill idempotence and provenance.**
  Skip rows whose `neuralfoil_model_size` and `n_crit` already match; expose
  `--force` for semantic re-backfills.
  - Legacy origin: `app/models/airfoil_low_re.py:65`
  - Definition of done: a second run without `--force` writes nothing; with
    `--force` it rewrites every row.
  - Confidence: 🟢 (semantic staleness is undetectable — 🟡)

### Interpolation and query Re

- [ ] **T-20 — `interpolate_polar_at_re` linear in `ln(Re)`.**
  Matching NeuralFoil's training encoding.
  - Legacy origin: `airfoil_low_re_service.py:304-311`
  - Definition of done: querying at the **geometric** mean of two grid points
    returns the arithmetic mean of the metric; a linear-in-Re implementation
    fails the test.
  - Confidence: 🟢

- [ ] **T-21 — `_clamp_re_to_grid`.**
  Clamp an out-of-range query to the nearest endpoint and set
  `re_clamped = True`. Never extrapolate.
  - Legacy origin: `suitability_service.py:124-133`
  - Definition of done: `Re = 10 000` → effective `40 000`, flag set;
    `Re = 1 000 000` → `750 000`, flag set.
  - Confidence: 🟢

- [ ] **T-22 — Query Re at sea level.**
  `Re = ρ·V·c / μ` with `ρ = 1.225 kg/m³` and `μ = 1.81e-5 Pa·s`. Shared
  constants `G = 9.80665`, `RHO = 1.225`.
  - Legacy origin: `suitability_service.py:74-75, 119-121`;
    `airfoil_low_re_service.py:39-40`
  - Definition of done: a known `(c, V)` pair reproduces the reference Re; the
    constants match `endurance_service`'s values exactly.
  - Confidence: 🟢 (the duplication is 🟡)

### Scoring

- [ ] **T-23 — Lens 1, `score_re_agnostic`.**
  Weighted sum **renormalised by the weights actually present**:
  `ld_max → min(ld_max/60.0, 1)` @ 0.35; `cl_max → min(cl_max/1.5, 1)` @ 0.25;
  `drag_bucket_width → min(bucket/0.8, 1)` @ 0.20;
  `stall_gentleness → clamp(1 + stall/0.15, 0, 1)` @ 0.10 (→ 0 at
  `stall ≤ −0.15`); `cd_min → min(0.008/cd_min, 1)` @ 0.10.
  `score = Σ(v·w)/Σw` clamped to `[0,1]`; `None` when no component is available.
  - Legacy origin: `airfoil_low_re_service.py:831-891`
  - Definition of done: an airfoil missing `cl_max` scores from the remaining
    four weights, not from a zero; an airfoil missing everything scores `None`,
    not `0`.
  - Confidence: 🟢

- [ ] **T-24 — Lens 2, `score_mission`.**
  `re_agnostic × family_bonus × thickness_match × cl_bonus` with
  `family_bonus = 1.0 | 0.7`,
  `thickness_match = 1.0` inside `[t_min, t_max]` else `max(0, 1 − gap/5.0)`,
  `cl_bonus = (1 − cl_max_weight) + cl_max_weight · min(cl_max/1.5, 1)`.
  - Legacy origin: `airfoil_low_re_service.py:894-940`
  - Definition of done: each of the six mission bands is table-tested for
    `t_min`, `t_max`, `cl_max_weight` and preferred families.
  - Confidence: 🟢

- [ ] **T-25 — The six mission bands.**
  trainer 11–14 / 0.70 / {flat_bottom, semi_symmetric};
  sport 9–13 / 0.55 / {semi_symmetric, cambered};
  aerobatic 8–12 / 0.40 / {symmetric};
  glider 10–14 / 0.50 / {cambered, semi_symmetric};
  flying_wing 8–13 / 0.50 / {reflexed, symmetric};
  slope_soarer 8–12 / 0.45 / {semi_symmetric, cambered}.
  - Legacy origin: `app/settings.py:19-56`
  - Definition of done: the table is reproduced verbatim and is overridable via
    `.env`.
  - Confidence: 🟢

- [ ] **T-26 — `best_ld_cl`.**
  `cl_star = sqrt(cl0² + cd0/k)`; return `None` for `cd0 ≤ 0` or `k ≤ 0`.
  - Legacy origin: `airfoil_low_re_service.py:715-760`
  - Definition of done: the closed form matches a numeric argmax of `CL/CD` on a
    synthetic parabolic polar; the two degenerate inputs return `None` rather
    than raising or defaulting.
  - Confidence: 🟢

- [ ] **T-27 — Lens 3, `score_target_cl` = `Match × Efficiency`.**
  `r = CD(cl_target)/cd0`; `r_poor = 2.5`;
  `tolerance = (drag_bucket_width / 0.6) × 0.5`;
  `Match = 1.0` for `r ≤ 1`, `1 − (r−1)/(r_poor−1)` within tolerance, `0.0` at
  `r ≥ r_poor` unless the fallback applies;
  fallback `Match = clamp((cl_max − cl_target)/0.30, 0, 1)`;
  `Efficiency = min(re_cd0_reference/cd0, 1.0)`;
  `Final = clamp(Match × Efficiency, 0, 1)`.
  - Legacy origin: `airfoil_low_re_service.py:943-1009, 977-997`
  - Definition of done: the three Match branches and the CL_max fallback each
    have a test; a glider min-sink CL (`CL ≈ √3 · CL_md`) scores non-zero through
    the fallback.
  - Confidence: 🟢

- [ ] **T-28 — `compute_re_cd0_reference` (20th percentile).**
  Interpolate every airfoil to `re_query`, take the **20th percentile** of the
  finite `cd0` values; fall back to `_CD0_REFERENCE_FALLBACK = 0.020` on an empty
  fleet.
  - Legacy origin: `airfoil_low_re_service.py:771-823`
  - Definition of done: a single freak low-`cd0` airfoil does not move the
    reference; an empty fleet returns `0.020`.
  - Confidence: 🟢

- [ ] **T-29 — `_level_flight_cl`.**
  `CL = (m·g) / (0.5·ρ·V²·S)`; raise `ValueError` for non-positive `V` or `S`.
  - Legacy origin: `airfoil_low_re_service.py:686-707`
  - Definition of done: `V = 0` and `S = 0` both raise rather than dividing by
    zero.
  - Confidence: 🟢

### Ranking, caveats and tags

- [ ] **T-30 — `ActiveLens` admits only three values.**
  `re_agnostic | mission | target_cl_cruise`. `target_cl_best_glide` and
  `target_cl_min_sink` are computed and displayed but can never rank.
  - Legacy origin: `app/schemas/airfoil.py:71-84`
  - Definition of done: a request with `active_lens = "target_cl_min_sink"` is
    rejected at validation time.
  - Confidence: 🟢

- [ ] **T-31 — Confidence-first ordering.**
  Sort by `(confidence tier, −score)` with the tier as the **primary** key.
  - Legacy origin: `suitability_service.py:629, 632`
  - Definition of done: a 0.95-score low-confidence airfoil ranks below a
    0.80-score high-confidence one.
  - Confidence: 🟢

- [ ] **T-32 — The always-on caveat block.**
  `SuitabilityCaveat` with `relative_ranking_only = True`,
  `no_hysteresis_modelling = True`, **`ignores_tip_re_clmax_collapse = True`
  unconditionally**, `recommend_xfoil_validation`, and a human-readable `text`.
  - Legacy origin: `app/schemas/airfoil.py:6-17, 174-187`; ADR 0012
  - Definition of done: every response carries the block, and
    `ignores_tip_re_clmax_collapse` is `true` in all of them.
  - Confidence: 🟢

- [ ] **T-33 — `tip_re_flag` and `cl_max_margin`.**
  Flag when `Re_tip < 80 000` **or** the root→tip Re drop exceeds `50 000`.
  `cl_max_margin = cl_max − max(target CLs)`; negative means stall risk.
  - Legacy origin: `app/settings.py:109-114`; `app/schemas/airfoil.py:174-187`
  - Definition of done: `Re_tip = 70 000` flags; a root 200 k → tip 140 k drop
    flags; `cl_max 1.2` against target `1.4` yields `−0.2`.
  - Confidence: 🟢

- [ ] **T-34 — Query-time role tags (gh-835).**
  No column, no migration, no backfill. `LOW_RE_UPPER_BOUND = 150 000`,
  `HIGH_RE_LOWER_BOUND = 500 000`, `LOW_RE_CONFIDENCE_GATE = 0.85`. Rules per
  [`contracts.md`](contracts.md) §Role-tag contract. Return the tags **sorted**.
  - Legacy origin: `app/services/airfoil_tags.py:62-64`
  - Definition of done: a 9 % symmetric section with 0.1 % camber carries
    `acro`, `h_stabilizer`, `v_stabilizer` in sorted order; the six rules each
    have a boundary test.
  - Confidence: 🟢

### REST layer

- [ ] **T-35 — The twelve routes.**
  Exactly as listed in [`contracts.md`](contracts.md). Note these are **not**
  nested under an aeroplane.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py` (1086 l.)
  - Definition of done: contract tests assert every status code, including the
    422 on an import path outside `components`.
  - Confidence: 🟢

- [ ] **T-36 — Declare `/airfoils/db/suitability` before `/airfoils/db/{name}`.**
  Otherwise `"suitability"` is captured as an airfoil name.
  - Legacy origin: route shapes in `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a test hits `/airfoils/db/suitability` and asserts it
    returns a `SuitabilityResponse`, not a 404 for an airfoil named
    `"suitability"`.
  - Confidence: 🟡 INFERRED from the path shapes; the declaration order in the
    legacy file was not read.

- [ ] **T-37 — Interactive NeuralFoil analysis with `model_size="large"`.**
  `GET /airfoils/{name}/neuralfoil/analysis` and `.../diagrams`.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py:111`
  - Definition of done: the endpoint uses `"large"` while the backfill uses
    `"xxxlarge"`, asserted by a test (see T-17).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path:** import `components/airfoils`, classify, backfill,
      query suitability, assert a ranked non-empty list with the caveat block.
- [ ] **TT-02 — Failure:** an import path outside `components` returns 422 and
      reads no file.
- [ ] **TT-03 — Parse boundaries:** 2-line file raises; 3 valid coordinates
      passes; one junk line is skipped; the name is the stem.
- [ ] **TT-04 — Import resilience:** 10 files with 1 corrupt →
      `imported=9, errors=1`, the filename in `error_files`, the rest committed.
- [ ] **TT-05 — Import idempotence:** a second run reports all `skipped`,
      case-insensitively.
- [ ] **TT-06 — Classification order:** NACA 0012 is `symmetric`, not
      `flat_bottom`; an explicit assertion of the five-step order.
- [ ] **TT-07 — Reflex reference set:** MH60 / E184 / EH-series → `reflexed`;
      NACA 4412 (ratio 0.31, quad −0.11) and Clark Y (0.28) → not reflexed;
      Clark YH (quad +0.039) → reflexed via Signal B.
- [ ] **TT-08 — `camber_at_te` is measured at x = 0.9** and is non-zero for a
      sharp-TE airfoil.
- [ ] **TT-09 — Classifier thresholds:** a boundary test just inside and just
      outside each of the eight constants.
- [ ] **TT-10 — Confidence gate:** α points below 0.90 do not contribute to any
      metric.
- [ ] **TT-11 — Windowed confidence:** clean attached flow plus poor deep stall
      scores high; a 3-point window falls back to the whole sweep.
- [ ] **TT-12 — Model-size split:** the backfill uses `"xxxlarge"`, the
      interactive endpoint `"large"`; the test fails if they are unified.
- [ ] **TT-13 — Missing AeroSandbox:** the sweep returns `[]`, warns, and the API
      still serves.
- [ ] **TT-14 — Backfill idempotence:** a second run without `--force` writes
      nothing; `--force` rewrites all 13 rows.
- [ ] **TT-15 — `ln(Re)` interpolation:** the geometric-mean query returns the
      arithmetic mean; a linear-in-Re implementation fails.
- [ ] **TT-16 — Re clamping:** both ends clamp and set `re_clamped`.
- [ ] **TT-17 — Lens 1 renormalisation:** a missing component reduces the
      denominator; all missing → `None`, not `0`.
- [ ] **TT-18 — Lens 2 mission table:** all six bands, inside and outside the
      thickness window, preferred and non-preferred families.
- [ ] **TT-19 — Lens 3 branches:** `r ≤ 1`, within tolerance, `r ≥ r_poor`, and
      the CL_max fallback; a glider min-sink CL scores non-zero.
- [ ] **TT-20 — `best_ld_cl` degenerates safely:** `cd0 ≤ 0` and `k ≤ 0` return
      `None`.
- [ ] **TT-21 — Fleet reference is robust:** one freak airfoil does not move the
      20th percentile; an empty fleet returns `0.020`.
- [ ] **TT-22 — Confidence outranks score.**
- [ ] **TT-23 — Glide lens rejected:** `active_lens = "target_cl_min_sink"` →
      422.
- [ ] **TT-24 — Caveat always present** with
      `ignores_tip_re_clmax_collapse = true`.
- [ ] **TT-25 — Tip-Re flag:** absolute floor and relative drop, both
      independently.
- [ ] **TT-26 — `cl_max_margin` sign:** a negative margin is reported, not
      clamped.
- [ ] **TT-27 — Role tags:** each of the six rules at its boundary; tags come
      back sorted.
- [ ] **TT-28 — Route order:** `/airfoils/db/suitability` is not swallowed by
      `/airfoils/db/{name}`.

## Data Migration Tasks

- [ ] **TM-01 — Re-backfill after the gh-834 family change.** Stored `family`
      values are wrong for every reflexed section computed under the old
      endpoint rule. Requires `--force`; provenance columns cannot detect it. 🟢
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

## Suggested Order

1. **T-01 → T-04** first — the three tables. T-03's `UniqueConstraint` is what
   makes every later backfill re-runnable, so it must exist before any compute
   task. T-04 is a documentation decision, not code.
2. **T-05 → T-08** next — ingestion. Nothing downstream has data without it, and
   T-06's traversal guard is the module's only client-supplied filesystem path.
3. **T-09 → T-12** — classification. Pure geometry, no solver, fully testable on
   the CI **fast** tier. T-09 blocks T-11 (the reflex test runs first in the
   order). T-12 is a runbook item, not code.
4. **T-13 → T-19** — the NeuralFoil sweep. Needs AeroSandbox and therefore
   belongs on the **slow** tier, except T-18 which must be verified *without* it.
   T-15 blocks T-16 (the window comes from the extracted metrics). This step can
   proceed in parallel with step 3 if the classifier is stubbed.
5. **T-20 → T-22** — interpolation and query Re. Depends on T-03's rows existing
   but not on the solver; testable with hand-built polar rows.
6. **T-23 → T-29** — the three lenses. T-23 blocks T-24 (Lens 2 multiplies
   Lens 1). T-26 blocks T-27. T-28 needs T-20. All are pure functions and belong
   on the fast tier.
7. **T-30 → T-34** — ranking, caveats and tags. T-31 needs T-16's confidence to
   exist; T-34 needs both geometry and polars.
8. **T-35 → T-37** last — the REST layer is thin. T-36 is a route-declaration
   ordering constraint that must be tested, not assumed.

## Pending Gaps (🔴)

- **No Lednicer-format detection.** `_parse_dat_file` assumes Selig, so a
  Lednicer file's leading surface-point counts are read as coordinates and
  produce a silently wrong airfoil. Should the parser sniff the format, or should
  non-Selig files be rejected explicitly?
- **Two settings modules with overlapping responsibility.** `app/settings.py`
  (airfoil/low-Re, `base_url`, `openai_api_key`) versus `app/core/config.py`
  (`ARTIFACTS_BASE_DIR`, copilot credentials, `AIRFOILS_DIR`). The project
  convention names `core/config.py` as the single configuration home. Which is
  canonical?
- **Natural-key foreign keys without `ON UPDATE CASCADE`.**
  `airfoil_geometry` and `airfoil_low_re_polar` reference `airfoils.name`. Is
  renaming an airfoil forbidden by convention, or should the FK move to
  `airfoils.id`?
- **No documented rationale for the missing ORM relationships.** The omission
  looks deliberate (avoiding a 1 665 × 13 row load) but is not written down, so a
  future contributor may reintroduce it.
- **Semantic re-backfills are invisible to the skip logic.** Only
  `neuralfoil_model_size` and `n_crit` are stored as provenance; a meaning change
  (gh-834, gh-825) needs a manual `--force`. Should a semantic version column be
  added?
- **`high_re` asserts more than the data supports.** The grid tops out at 750 k,
  so the tag is knowingly approximate but exposed as a plain boolean.
- **`G` and `RHO` are duplicated** between `airfoil_low_re_service` and
  `endurance_service`, kept in sync by comment rather than by a shared import.
