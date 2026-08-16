# low-re-polar-backfill — Technical Design

> Use-case design, nested under [`airfoil-catalog`](../design.md).
> Focuses on HOW this slice is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`../contracts.md`](../contracts.md).

## Interface

### Ingestion — `app/services/airfoil_service.py` 🟢

| Symbol | Signature | Returns | Line |
|---|---|---|---|
| `_parse_dat_file` | `(path)` | `(name, [[x, y], …])` | l.57-87 |
| `import_directory` | `(db, directory)` | `AirfoilImportResult` | l.90-154 |

### Classification and sweep — `app/services/airfoil_low_re_service.py` (1086 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `classify_family` | `coords → AirfoilFamily` | l.120 |
| evaluation order | reflexed → symmetric → flat_bottom → semi_symmetric → cambered | l.102-105 |
| reflex Signals A + B | gh-834 detection | l.46-88 |
| `compute_airfoil_low_re` | NeuralFoil sweep over the Re grid | l.406-521 |
| model-size note | "do NOT collapse" | l.428-431 |
| re-backfill note | windowed-confidence semantics change | l.445-456 |
| ASB import guard | returns `[]` with a warning | l.458-462 |
| `_windowed_min_confidence` | attached-window confidence minimum | l.524-566 |

Shared physical constants, kept in sync with `endurance_service` by comment:
`G = 9.80665`, `RHO = 1.225` (l.39-40). 🟢 This slice does not use them; they are
consumed by [`suitability-search`](../suitability-search/design.md).

### Route owned by this slice 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| POST | `/airfoils/import` | import a directory of `.dat` files | 200 · **422 outside `components`** · 500 |

The batch polar sweep itself has **no HTTP route** — it is a CLI/backfill
operation over `compute_airfoil_low_re`. 🟡 INFERRED from the absence of a sweep
route in `app/api/v2/endpoints/airfoils.py` and the `--force` flag referenced in
the code comments; the CLI entry point was not read directly.

### Data model 🟢

```
airfoils.name ──FK (natural key, ondelete=CASCADE, no ON UPDATE)──┬─▶ airfoil_geometry     (1:1)
                                                                  └─▶ airfoil_low_re_polar (1:N, 13 rows)
```

`airfoils` (`app/models/airfoil.py:6`): `id` PK, `name` (**unique, indexed** —
the natural key, derived from the `.dat` **file stem**), `coordinates`
(JSON `list[[x, y]]`, Selig order, chord-normalised 0–1), `source_file`
(nullable, the original filename), `created_at` (tz-aware, default `now()`).

`airfoil_geometry` (`airfoil_low_re.py:33`): `id` PK (redeclared on the model),
`airfoil_name` FK (**unique + indexed**, enforcing the natural 1:1),
`max_thickness_pct`, `max_camber_pct` (both **percent of chord**),
`camber_at_te` (**the camber value at x = 0.9**, gh-834; positive → reflexed),
`family`, `computed_at`. All required.

`airfoil_low_re_polar` (`airfoil_low_re.py:65`): one row per
`(airfoil_name, reynolds)` with `UniqueConstraint("airfoil_name", "reynolds")`.
Nullable metrics: `ld_max`, `cl_max`, `alpha_attached_lo`, `alpha_attached_hi`,
`drag_bucket_width`, `cd_min`, `stall_gentleness`, `cd0`, `k`, `cl0`,
`cl_valid_lo`, `cl_valid_hi`, `min_analysis_confidence`. Non-null provenance:
`neuralfoil_model_size` (default `"xxxlarge"`), `n_crit` (default `9.0`),
`computed_at`. 🟢

There is **no ORM relationship** from `AirfoilModel` to either child; the
services join by name. 🟡 INFERRED deliberate — it avoids loading
1 665 × 13 polar rows — but undocumented.

## Main Flow

### F1 — Parse a `.dat` file (`_parse_dat_file`, l.57-87) 🟢

1. **Selig format only.** Skip the first line as a header.
2. Every subsequent line must yield two parseable floats; anything else is
   **silently skipped**.
3. Fewer than 3 lines, **or** fewer than 3 valid coordinates → `ValueError`.
4. The canonical name is the **file stem**, not the Selig header — this matches
   how the CadQuery plugin resolves airfoils.
5. No normalisation and no re-panelling is performed; the coordinates are stored
   as read, in Selig order, chord-normalised 0–1.

🟡 There is **no format sniffing**: a Lednicer-format file, whose first data line
is a pair of surface-point counts rather than a coordinate, would be mis-parsed
as coordinates rather than rejected.

### F2 — Import a directory (`import_directory`, l.90-154) 🟢

1. Resolve the directory and assert it is **inside `<project_root>/components`**;
   otherwise raise `ValidationError` (l.97-106) — the traversal guard, evaluated
   **before** any file is read.
2. Recursive `rglob("*.dat")`.
3. Case-insensitive dedup against existing names → `skipped`.
4. Per file, a `try/except` that increments `errors`, records the filename in
   `error_files` and calls `db.rollback()` so the loop can continue. This is the
   one place in the module that rolls back deliberately, inside the
   `get_db()`-owned transaction (ADR 0009).
5. Return
   `AirfoilImportResult(imported, skipped, errors, error_files, imported_names)`.
   `imported_names` carries `exclude=True` — internal only, never serialised
   (`app/schemas/airfoil.py:51`).

The canonical directory is absolute and CWD-independent:
`AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`
(`app/core/config.py:6-14`). The comment records the motivating bug —
procedurally generated airfoils written by the OpenVSP importer landed outside a
CWD-relative read directory and appeared missing.

### F3 — Classify the family (`classify_family`, l.120) 🟢

Evaluation order is **load-bearing**:

```
reflexed → symmetric → flat_bottom → semi_symmetric → cambered
```

The symmetric test must fire **before** flat_bottom, because a perfectly
symmetric section also passes the lower-surface linearity test (l.102-105).

| Threshold | Value | Meaning |
|---|---|---|
| `_SYMMETRIC_MAX_CAMBER_PCT` | `0.5` | below → `symmetric` |
| `_SEMI_SYMMETRIC_MAX_CAMBER_PCT` | `2.0` | below → `semi_symmetric` |
| `_FLAT_BOTTOM_Y_THRESHOLD` | `0.002` | strict legacy lower-surface flatness |
| `_FLAT_BOTTOM_AFT_X_LO` | `0.30` | start of the aft linearity window |
| `_FLAT_BOTTOM_QUAD_THRESHOLD` | `0.005` | max quadratic coeff of the aft lower-surface fit → flat |
| `_REFLEX_AFT_CAMBER_RATIO_MAX` | `0.06` | Signal A |
| `_REFLEX_AFT_CONCAVITY_MIN` | `0.015` | Signal B |
| `_REFLEX_B_MIN_CAMBER_PCT` | `2.0` | Signal B guard |

### F4 — Reflex detection (gh-834, l.46-88) 🟢

The most heavily documented rule in the file. The original code tested the
camber-line **endpoint** `camber[-1]`, which is ≈0 for *every* sharp-TE airfoil,
so only blunt/open-TE supercritical shapes were labelled reflexed while real
flying-wing sections (MH60, E184, EH series) were missed. The replacement uses
camber-line **shape** over the aft chord:

```
Signal A (sharp-TE reflex):     camber(x = 0.9) / max_camber  <  _REFLEX_AFT_CAMBER_RATIO_MAX = 0.06
                                NACA 4412 → 0.31 ;  Clark Y → 0.28

Signal B (open/upturned TE):    quadratic coefficient of the camber line
                                fitted over x ∈ [0.5, 1]
                                >  _REFLEX_AFT_CONCAVITY_MIN = +0.015
                                guarded by _REFLEX_B_MIN_CAMBER_PCT = 2.0
                                (only fires above 2 % camber)
                                Clark YH ≈ +0.039 ;  NACA 4412 ≈ −0.11
```

`camber_at_te` is consequently **stored as the camber value at x = 0.9**, not at
the TE. Stored `family` values change after this fix, so a `--force` re-backfill
is required post-merge.

### F5 — NeuralFoil sweep (`compute_airfoil_low_re`, l.406-521) 🟢

```python
compute_airfoil_low_re(name, coords, re_grid, *,
                       model_size="xxxlarge", n_crit=9.0,
                       confidence_gate=0.90,
                       alpha_start=-5.0, alpha_end=18.0,
                       alpha_step=0.2) -> list[dict]
```

1. Build the α grid from `alpha_start` / `alpha_end` / `alpha_step`
   (`-5.0 … 18.0` in steps of `0.2`).
2. Per Re grid point call
   `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=α_grid, Re=re, mach=0.0,
   n_crit=n_crit, model_size=model_size)`.
3. Keep only α points with `analysis_confidence ≥ 0.90` (`confidence_gate`) for
   metric extraction.
4. Extract the fixed metric set (F6).
5. `min_analysis_confidence` = `_windowed_min_confidence` (F7).
6. Import-guarded: returns `[]` with a warning when AeroSandbox is unavailable
   (l.458-462, ADR 0017). It never raises.

**The backfill model size is `"xxxlarge"`.** The interactive endpoint uses
`"large"` (`app/api/v2/endpoints/airfoils.py:111`, owned by
[`neuralfoil-analysis`](../neuralfoil-analysis/design.md)). The docstring says
**"do NOT collapse"** (l.428-431). 🟢

### F6 — Metric extraction 🟢

| Metric | Definition |
|---|---|
| `ld_max` | `(L/D)_max` inside the trusted range |
| `cl_max` | `CL_max` inside the trusted range |
| `alpha_attached_lo` / `alpha_attached_hi` | degrees; the attached-flow window |
| `drag_bucket_width` | **ΔCL where `CD ≤ 1.15 · CD_min`** |
| `cd_min` | minimum drag coefficient |
| `stall_gentleness` | `dCL/dα` just past the peak — **raw slope, not normalised**; ≈0 = gentle, negative = abrupt |
| `cd0`, `k`, `cl0` | the parabolic fit `CD = cd0 + k·(CL − cl0)²` |
| `cl_valid_lo` / `cl_valid_hi` | the fit's validity window |

(`app/models/airfoil_low_re.py:88-105`.) All are nullable — an airfoil whose
sweep yields nothing confident persists a row with `NULL` metrics rather than no
row at all. 🟡 INFERRED from the column nullability; the exact null-row policy
was not read.

### F7 — Windowed confidence (`_windowed_min_confidence`, l.524-566) 🟢

`min_analysis_confidence` is the minimum over the attached-flow window
`[alpha_attached_lo, alpha_attached_hi]`, **not** the whole-sweep minimum —
deep-stall confidence is irrelevant to operating-point performance. It falls
back to the whole-sweep minimum when the window is undefined **or has fewer
than 4 points**. Changing this semantics also required a re-backfill
(l.445-456).

### F8 — The Re grid 🟢

```
low_re_grid = [40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k,
               200k, 250k, 350k, 500k, 750k]      # 13 points
```

"Dense below 250 k where the laminar-separation bubble governs; coarser above"
(`app/settings.py:58-74`). These are **absolute** Reynolds numbers, independent
of any aircraft — see F9.

### F9 — The two Reynolds concepts 🟢

Stated explicitly in both `app/models/airfoil_low_re.py:8-14` and
`app/services/airfoil_low_re_service.py:3-9`:

| Concept | Owner | Meaning |
|---|---|---|
| **2D per-airfoil, absolute Re** (gh-821) | **this slice** | polars over 40 k–750 k straight from NeuralFoil, independent of any aircraft |
| Aircraft-level speed band (gh-493) | `polar_re_table_service` | re-bins aircraft fine-sweep data into speed-band labels where "Re" is a speed proxy at the main wing's MAC for a specific flight condition |

**Do not conflate them.**

### F10 — Idempotence 🟢

`UniqueConstraint("airfoil_name", "reynolds")` makes the backfill re-runnable
(`app/models/airfoil_low_re.py:65`). `neuralfoil_model_size` and `n_crit` are
stored as provenance so an up-to-date row can be skipped.

🟡 A **semantic** change is *not* detectable this way. Two documented cases
changed the meaning of stored columns without changing the provenance:

| Change | Column affected | Recovery |
|---|---|---|
| gh-834 reflex from shape | `family`, `camber_at_te` | `--force` re-backfill |
| gh-825 windowed confidence | `min_analysis_confidence` | `--force` re-backfill |

## Alternative Flows

- **Malformed `.dat` line:** silently skipped; only a total below 3 valid
  coordinates raises `ValueError`. 🟢
- **File with fewer than 3 lines:** raises `ValueError` before coordinate
  counting. 🟢
- **Malformed file during a directory import:** `errors += 1`, filename recorded
  in `error_files`, `db.rollback()`, loop continues; the remaining files still
  commit. 🟢
- **Import directory outside `components`:** `ValidationError` → 422 before any
  file is read. 🟢
- **Duplicate airfoil name on import:** skipped case-insensitively; counted as
  `skipped`, not `errors`. 🟢
- **Lednicer-format file:** 🟡 **not detected.** The leading surface-point counts
  are read as a coordinate pair and the airfoil is persisted with silently wrong
  geometry.
- **AeroSandbox unavailable:** `compute_airfoil_low_re` returns `[]` with a
  warning; nothing raises and no rows are written (ADR 0017). 🟢
- **Undefined or too-short attached window:** `min_analysis_confidence` falls
  back to the whole-sweep minimum. 🟢
- **All α points below the confidence gate:** no point feeds metric extraction;
  the metrics are `NULL`. 🟡 INFERRED from the nullability of every metric
  column.
- **Perfectly symmetric section:** caught by the `symmetric` test before the
  `flat_bottom` test, which it would also pass. 🟢
- **Section below 2 % camber:** Signal B is not evaluated at all
  (`_REFLEX_B_MIN_CAMBER_PCT` guard). 🟢

## Dependencies

- **AeroSandbox / NeuralFoil** (optional, absent on `linux/aarch64`) — the only
  aerodynamic engine in this slice; import-guarded (ADR 0017).
- **`app/settings.py`** — `low_re_grid`, `low_re_neuralfoil_model_size`,
  `low_re_n_crit`, `low_re_confidence_gate`. 🟢 The project convention names
  `app/core/config.py` as the single configuration home; which module is
  canonical is unresolved.
- **`app/core/config.py`** — `AIRFOILS_DIR`.
- **`components/airfoils/`** — 1 665 `.dat` files, the filesystem source of
  truth. The database is a cache of it.
- **`app/db/session.py`** — the `get_db()` request-scoped transaction (ADR 0009);
  the import loop's per-file `db.rollback()` operates inside it.
- **NumPy / SciPy** — metric extraction and the parabolic fit.
- **`suitability-search`** — the downstream consumer of everything written here.
- **`polar_re_table_service`** — explicitly **not** a dependency; it implements
  the other, aircraft-level Re concept (gh-493).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Airfoils are named by **file stem**, matching the CadQuery plugin's lookup | `airfoil_service.py:57-87` | 🟢 |
| The airfoil directory is absolute, not CWD-relative | `app/core/config.py:6-14` | 🟢 |
| A single unparseable line is skipped rather than failing the file | `airfoil_service.py:57-87` | 🟢 |
| Import resilience is per file, with a deliberate `db.rollback()` inside the request transaction | `airfoil_service.py:90-154` | 🟢 |
| Family classification order is fixed and documented as load-bearing | `airfoil_low_re_service.py:102-105` | 🟢 |
| Reflex is detected from camber-line **shape**, and `camber_at_te` therefore means "camber at x = 0.9" | gh-834; `airfoil_low_re_service.py:46-88` | 🟢 |
| Signal B is guarded to airfoils above 2 % camber rather than applied universally | `_REFLEX_B_MIN_CAMBER_PCT` | 🟢 |
| The backfill model size is `"xxxlarge"`, explicitly not collapsed with the interactive `"large"` | `airfoil_low_re_service.py:428-431` | 🟢 |
| Confidence is windowed to the attached-flow range | `airfoil_low_re_service.py:524-566` | 🟢 |
| Only α points at or above the `0.90` gate feed metric extraction | `airfoil_low_re_service.py:406-521` | 🟢 |
| `stall_gentleness` is stored as a **raw slope**, not normalised | `app/models/airfoil_low_re.py:88-105` | 🟢 |
| The backfill is idempotent through `(airfoil_name, reynolds)` uniqueness plus provenance columns | `app/models/airfoil_low_re.py:65` | 🟢 |
| The Re grid is denser below 250 k where the laminar-separation bubble governs | `app/settings.py:58-74` | 🟢 |
| Child tables key on the natural name rather than the integer id | `app/models/airfoil_low_re.py:33, 65` | 🟢 — renaming is forbidden by convention (`Q-AF-7`), which is what makes the natural key safe |
| No ORM relationship from `AirfoilModel` to its children | `app/models/airfoil.py` | 🟡 |

## Internal State

The slice is stateless between invocations. Persistent state it **owns**:

- `airfoils` — name (the natural key), Selig coordinates, `source_file`
  provenance, `created_at`.
- `airfoil_geometry` — one Re-independent row per airfoil: `max_thickness_pct`,
  `max_camber_pct`, `camber_at_te` (at x = 0.9), `family`, `computed_at`.
- `airfoil_low_re_polar` — 13 rows per airfoil, one per Re grid point, carrying
  the extracted metrics, the parabolic fit and its validity window, the windowed
  confidence, and the provenance triple
  (`neuralfoil_model_size`, `n_crit`, `computed_at`).

External state it **reads**: `components/airfoils/*.dat` — the filesystem source
of truth.

Nothing in this slice is computed at query time; that is entirely
[`suitability-search`](../suitability-search/design.md)'s job.

## Observability

- `logger.warning` when AeroSandbox is unavailable and the sweep returns `[]`
  (`airfoil_low_re_service.py:458-462`). 🟢
- The import result is itself the primary observability surface:
  `imported` / `skipped` / `errors` / `error_files`
  (`AirfoilImportResult`, `app/schemas/airfoil.py:51`). A caller can tell
  exactly which files failed without reading a log. 🟢
- The provenance columns `neuralfoil_model_size`, `n_crit` and `computed_at`
  make a row's origin auditable. 🟢
- The code documents twice that a semantic change (gh-834 reflex, gh-825
  windowed confidence) requires a `--force` re-backfill; there is **no automatic
  staleness detection** beyond the two provenance values. 🟡
- No metrics or traces. 🟢

## Risks and Gaps

- 🟡 **No Lednicer-format detection.** `_parse_dat_file` assumes Selig. A
  Lednicer file's leading surface-point counts would be read as coordinates,
  producing a silently wrong airfoil rather than an error. Every downstream
  metric for that airfoil would then be wrong but confidently reported.
- 🟢 **The child tables use `ForeignKey("airfoils.name")` with `ondelete=CASCADE`
  but no `ON UPDATE CASCADE`.** Renaming an airfoil would orphan its geometry and
  polars. Is renaming forbidden by convention, or is this a latent defect?
- 🟢 **Two settings modules merge into one** (`Q-CC-4`, maintainer-answered).
  `app/settings.py` holds this slice's knobs; `app/core/config.py` holds
  `AIRFOILS_DIR`. The project convention names `core/config.py` as the single
  configuration home.
- 🟡 **Semantic re-backfills are invisible to the skip logic.** Only
  `neuralfoil_model_size` and `n_crit` are provenance, so a meaning change is
  undetectable and needs a manual `--force`.
- 🟡 **No ORM relationship to the children** — deliberate for performance
  (1 665 × 13 rows), but nowhere stated, so a future contributor may "fix" it and
  reintroduce the load.
- 🟡 **The null-metric policy is unverified.** Every metric column is nullable,
  which implies a row is written even when no α point clears the confidence gate,
  but the code path was not read directly.
- 🟡 **The batch sweep has no HTTP route.** It appears to be a CLI/backfill
  operation with a `--force` flag, but the entry point was not read; only the
  `POST /airfoils/import` route is confirmed.
- 🟡 **Sweep cost is unbounded per invocation.** 1 665 airfoils × 13 Re points ×
  116 α points is a long CPU-bound run with no progress, cancellation or
  chunking surface found in the read code.
