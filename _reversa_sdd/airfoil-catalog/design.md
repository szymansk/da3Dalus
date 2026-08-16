# airfoil-catalog — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`suitability-search/`](suitability-search/),
> [`low-re-polar-backfill/`](low-re-polar-backfill/),
> [`neuralfoil-analysis/`](neuralfoil-analysis/).

## Interface

### Ingestion — `app/services/airfoil_service.py` 🟢

| Symbol | Signature | Returns | Line |
|---|---|---|---|
| `_parse_dat_file` | `(path)` | `(name, [[x, y], …])` | l.57-87 |
| `import_directory` | `(db, directory)` | `AirfoilImportResult` | l.90-154 |

### Geometry, polars and scoring — `app/services/airfoil_low_re_service.py` (1086 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `classify_family` | `coords → AirfoilFamily` | l.120 |
| reflex rules (Signals A + B) | gh-834 detection | l.46-88 |
| `compute_airfoil_low_re` | NeuralFoil sweep over the Re grid | l.406-521 |
| `_windowed_min_confidence` | attached-window confidence minimum | l.524-566 |
| `interpolate_polar_at_re` | linear in `ln(Re)` | l.304-311 |
| `_level_flight_cl` | `CL = m·g / (0.5·ρ·V²·S)` | l.686-707 |
| `best_ld_cl` | `cl_star = sqrt(cl0² + cd0/k)` | l.715-760 |
| `compute_re_cd0_reference` | 20th-percentile fleet `cd0` | l.771-823 |
| `score_re_agnostic` | Lens 1 | l.831-891 |
| `score_mission` | Lens 2 | l.894-940 |
| `score_target_cl` | Lens 3 | l.943-1009 |

Shared physical constants, kept in sync with `endurance_service` by comment:
`G = 9.80665`, `RHO = 1.225` (l.39-40). 🟢

### Query orchestration — `app/services/suitability_service.py` (709 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| query Re from chord and speed | `Re = ρ·V·c / μ` | l.74-75, 119-121 |
| `_clamp_re_to_grid` | clamp + `re_clamped` flag | l.124-133 |
| ranking | sort by `(confidence tier, −score)` | l.629, 632 |

### Role tags — `app/services/airfoil_tags.py` 🟢

Computed at query time; the literal tag set lives at l.62-64. Constants:
`LOW_RE_UPPER_BOUND = 150 000`, `HIGH_RE_LOWER_BOUND = 500 000`,
`LOW_RE_CONFIDENCE_GATE = 0.85`.

### Data model 🟢

```
airfoils.name ──FK (natural key, ondelete=CASCADE, no ON UPDATE)──┬─▶ airfoil_geometry     (1:1)
                                                                  └─▶ airfoil_low_re_polar (1:N)
```

`airfoils` (`app/models/airfoil.py:6`): `id` PK, `name` (**unique, indexed** —
the natural key, derived from the `.dat` **file stem**), `coordinates`
(JSON `list[[x, y]]`, Selig order, chord-normalised 0–1), `source_file`
(nullable), `created_at`.

`airfoil_geometry` (`airfoil_low_re.py:33`): `airfoil_name` FK
(**unique + indexed**, enforcing 1:1), `max_thickness_pct`, `max_camber_pct`,
`camber_at_te` (**the camber value at x = 0.9**, gh-834), `family`,
`computed_at`.

`airfoil_low_re_polar` (`airfoil_low_re.py:65`): one row per
`(airfoil_name, reynolds)` with `UniqueConstraint("airfoil_name", "reynolds")`.
Metrics (all nullable): `ld_max`, `cl_max`, `alpha_attached_lo/hi`,
`drag_bucket_width` (ΔCL where `CD ≤ 1.15·CD_min`), `cd_min`,
`stall_gentleness` (**raw** `dCL/dα` just past the peak, not normalised),
plus the parabolic fit `cd0`, `k`, `cl0` with its validity window
`cl_valid_lo` / `cl_valid_hi`, and `min_analysis_confidence`. Provenance
(non-null): `neuralfoil_model_size` (default `"xxxlarge"`), `n_crit` (default
`9.0`), `computed_at`. 🟢

There is **no ORM relationship** from `AirfoilModel` to either child; the
services join by name. 🟡 INFERRED deliberate — it avoids loading
1 665 × 13 polar rows — but undocumented.

## Main Flow

### F1 — Parse a `.dat` file (`_parse_dat_file`, l.57-87) 🟢

1. **Selig format only.** Skip the first line as a header.
2. Every subsequent line must yield two parseable floats; anything else is
   **silently skipped**.
3. Fewer than 3 lines, or fewer than 3 valid coordinates → `ValueError`.
4. The canonical name is the **file stem**, not the Selig header — this matches
   how the CadQuery plugin resolves airfoils.
5. No normalisation and no re-panelling is performed.

🟡 There is **no format sniffing**: a Lednicer-format file (which begins with two
surface-point counts rather than coordinates) would be mis-parsed as coordinates
rather than rejected. **Measured (`Q-AF-1`):** a scan replicating
`_parse_dat_file` exactly over all **1 665 bundled files found 0 Lednicer
candidates**, 0 files with `|y| > 1.0` and 0 files with fewer than 3 parsable
points — the bundled set is entirely Selig, so the risk is theoretical for
shipped data. It remains real for **uploaded** files, where a Lednicer header
row would be read as a coordinate pair.

### F2 — Import a directory (`import_directory`, l.90-154) 🟢

1. Resolve the directory and assert it is **inside `<project_root>/components`**;
   otherwise raise `ValidationError` (l.97-106) — the traversal guard.
2. Recursive `rglob("*.dat")`.
3. Case-insensitive dedup against existing names → `skipped`.
4. Per file, a `try/except` that increments `errors`, records the filename in
   `error_files` and calls `db.rollback()` so the loop can continue.
5. Return `AirfoilImportResult(imported, skipped, errors, error_files,
   imported_names)`. `imported_names` carries `exclude=True` — internal only.

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

**Reflex detection (gh-834)**, the most heavily documented rule in the file
(l.46-88): the original code tested the camber-line **endpoint** `camber[-1]`,
which is ≈0 for *every* sharp-TE airfoil, so only blunt/open-TE supercritical
shapes were labelled reflexed while real flying-wing sections (MH60, E184, EH
series) were missed. The replacement uses camber-line **shape** over the aft
chord:

```
Signal A (sharp-TE reflex):     camber(x = 0.9) / max_camber  <  0.06
                                NACA 4412 → 0.31 ;  Clark Y → 0.28
Signal B (open/upturned TE):    quadratic coeff of the camber line over
                                x ∈ [0.5, 1]  >  +0.015, and only above 2 % camber
                                Clark YH ≈ +0.039 ;  NACA 4412 ≈ −0.11
```

`camber_at_te` is consequently **stored as the camber value at x = 0.9**, not at
the TE. Stored `family` values change after this fix, so a `--force` re-backfill
is required post-merge.

### F4 — NeuralFoil sweep (`compute_airfoil_low_re`, l.406-521) 🟢

```python
compute_airfoil_low_re(name, coords, re_grid, *,
                       model_size="xxxlarge", n_crit=9.0,
                       confidence_gate=0.90,
                       alpha_start=-5.0, alpha_end=18.0,
                       alpha_step=0.2) -> list[dict]
```

1. Build the α grid from `alpha_start` / `alpha_end` / `alpha_step`.
2. Per Re grid point call
   `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=α_grid, Re=re, mach=0.0,
   n_crit=n_crit, model_size=model_size)`.
3. Keep only α points with `analysis_confidence ≥ 0.90` for metric extraction.
4. Extract `ld_max`, `cl_max`, `alpha_attached_lo/hi`, `drag_bucket_width`
   (ΔCL where `CD ≤ 1.15·CD_min`), `cd_min`, `stall_gentleness` (`dCL/dα` just
   past the peak; ≈0 = gentle, negative = abrupt), and fit
   `CD = cd0 + k·(CL − cl0)²` with its validity window
   `[cl_valid_lo, cl_valid_hi]`.
5. `min_analysis_confidence` = `_windowed_min_confidence` (F5).
6. Import-guarded: returns `[]` with a warning when AeroSandbox is unavailable
   (l.458-462, ADR 0017).

**Two model sizes coexist intentionally.** The backfill uses `"xxxlarge"`; the
interactive endpoint (`app/api/v2/endpoints/airfoils.py:111`) uses `"large"`.
The docstring says **"do NOT collapse"** (l.428-431).

### F5 — Windowed confidence (`_windowed_min_confidence`, l.524-566) 🟢

`min_analysis_confidence` is the minimum over the attached-flow window
`[alpha_attached_lo, alpha_attached_hi]`, **not** the whole-sweep minimum —
deep-stall confidence is irrelevant to operating-point performance. It falls
back to the whole-sweep minimum when the window is undefined or has fewer than
4 points. Changing this semantics also required a re-backfill (l.445-456).

### F6 — Re grid and interpolation 🟢

```
low_re_grid = [40k, 50k, 60k, 75k, 90k, 110k, 130k, 160k,
               200k, 250k, 350k, 500k, 750k]      # 13 points
```

"Dense below 250 k where the laminar-separation bubble governs; coarser above"
(`app/settings.py:58-74`).

`interpolate_polar_at_re(polar_rows, re_query, re_grid)` interpolates **linearly
in `ln(Re)`**, matching NeuralFoil's training encoding (l.304-311). Out-of-range
queries are clamped to the nearest endpoint and the response reports
`re_clamped = True` (`suitability_service._clamp_re_to_grid`, l.124-133).

Query Re uses standard sea-level air:

```
Re = ρ·V·c / μ    with  ρ = 1.225 kg/m³,  μ = 1.81e-5 Pa·s
```

(`suitability_service.py:74-75, 119-121`.)

### F7 — Lens 1, `score_re_agnostic` (l.831-891) 🟢

Weighted sum of normalised metrics, **renormalised by the weights actually
present**:

| Component | Normalisation | Weight |
|---|---|---|
| `ld_max` | `min(ld_max / 60.0, 1)` | 0.35 |
| `cl_max` | `min(cl_max / 1.5, 1)` | 0.25 |
| `drag_bucket_width` | `min(bucket / 0.8, 1)` | 0.20 |
| `stall_gentleness` | `clamp(1 + stall/0.15, 0, 1)` → 0 at `stall ≤ −0.15` | 0.10 |
| `cd_min` | `min(0.008 / cd_min, 1)` | 0.10 |

```
score = Σ(v·w) / Σw,  clamped to [0,1];  None when no component is available
```

### F8 — Lens 2, `score_mission` (l.894-940) 🟢

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

### F9 — Lens 3, `score_target_cl` (l.943-1009) 🟢

`Match × Efficiency`:

```
cl_star   = best_ld_cl(cd0, k, cl0) = sqrt(cl0² + cd0/k)      (closed form, l.715-760)
r         = CD(cl_target) / cd0                                (relative drag rise)
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

`best_ld_cl` returns `None` for `cd0 ≤ 0` or `k ≤ 0`; the derivation is written
out in full in the docstring (l.715-760). The CL_max fallback exists because
glider min-sink CLs (`CL ≈ √3 · CL_md`) sit far above `cl_star`, so a pure
drag-rise Match collapses to 0 even for excellent glider sections (l.977-997).

**Fleet reference.** `compute_re_cd0_reference(polars_by_name, re_query,
percentile=20.0)` (l.771-823) interpolates every airfoil to `re_query` and
returns the **20th percentile** of the finite `cd0` values — a robust "best
achievable at this Re" reference rather than the absolute minimum. Falls back to
`_CD0_REFERENCE_FALLBACK = 0.020` on an empty fleet.

**Level-flight CL helper.** `CL = (m·g) / (0.5·ρ·V²·S)`, raising `ValueError`
for non-positive `V` or `S` (`_level_flight_cl`, l.686-707).

### F10 — Ranking and the caveat block 🟢

- **Only three lenses may rank.** `active_lens ∈ {re_agnostic, mission,
  target_cl_cruise}`. `target_cl_best_glide` and `target_cl_min_sink` are
  **display-only**, so the default sort is never driven by an engine-out /
  min-sink contingency point (`app/schemas/airfoil.py:71-84`).
- **Tie-breaking.** Sort by `(confidence tier, −score)` — the confidence tier is
  the **primary** key, so a high-scoring low-confidence airfoil never outranks a
  trustworthy one (`suitability_service.py:629, 632`).
- **Tip-stall caveat.** The score treats section CL as whole-wing CL (ideal
  elliptic, untwisted), ignoring the tip-Re CL_max collapse that governs
  tip-stall onset on tapered wings. The contract therefore **always** sets
  `ignores_tip_re_clmax_collapse = True` and exposes `tip_re_flag` plus
  `cl_max_margin = cl_max − max(target CLs)` (negative = stall risk)
  (`app/schemas/airfoil.py:6-17, 174-187`). `tip_re_flag` fires when
  `Re_tip < low_re_tip_re_abs_floor = 80 000` or the root→tip drop exceeds
  `low_re_tip_re_rel_drop = 50 000` (`app/settings.py:109-114`).

### F11 — Role tags (gh-835) 🟢

Computed **at query time** from stored geometry + polars — no DB column, no
migration, no backfill (`app/services/airfoil_tags.py`).

| Tag | Rule |
|---|---|
| `v_stabilizer` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `6 ≤ t ≤ 15 %` |
| `h_stabilizer` | identical gate — kept separate for UX filtering |
| `acro` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `7 ≤ t ≤ 12 %` |
| `winglet` | `t ≤ 10 %` ∧ `family ∈ {symmetric, semi_symmetric, reflexed}` ∧ `camber ≤ 3 %` ∧ ≥ 1 confident polar at `Re ≤ 150 k` |
| `low_re` | ≥ 1 polar row `Re ≤ 150 k` with confidence ≥ 0.85 |
| `high_re` | ≥ 1 polar row `Re ≥ 500 k` with confidence ≥ 0.85 — **explicitly marked approximate** (the grid tops out at 750 k) |

Tags are returned **sorted** for determinism.

## Alternative Flows

- **Malformed `.dat` line:** silently skipped; only a total below 3 valid
  coordinates raises. 🟢
- **Malformed file during a directory import:** `errors += 1`, filename recorded,
  `db.rollback()`, loop continues. 🟢
- **Import directory outside `components`:** `ValidationError` → 422 before any
  file is read. 🟢
- **Duplicate airfoil name on import:** skipped case-insensitively; not an
  error. 🟢
- **AeroSandbox unavailable:** `compute_airfoil_low_re` returns `[]` with a
  warning; nothing raises (ADR 0017). 🟢
- **Undefined or too-short attached window:** `min_analysis_confidence` falls
  back to the whole-sweep minimum. 🟢
- **Query Re outside `[40 k, 750 k]`:** clamped to the nearest endpoint,
  `re_clamped = True` in the response. Never extrapolated. 🟢
- **A scoring component is missing:** it is dropped from both numerator and
  denominator; if none remain the score is `None`, not `0`. 🟢
- **`cd0 ≤ 0` or `k ≤ 0`:** `best_ld_cl` returns `None`, so Lens 3 has no
  `cl_star` for that airfoil. 🟢
- **Empty fleet:** `compute_re_cd0_reference` falls back to
  `_CD0_REFERENCE_FALLBACK = 0.020`. 🟢
- **Non-positive `V` or `S`:** `_level_flight_cl` raises `ValueError`. 🟢
- **`r ≥ r_poor` with a known `cl_max`:** the CL_max safety fallback replaces the
  zero Match rather than discarding the airfoil. 🟢

## Dependencies

- **AeroSandbox / NeuralFoil** (optional, absent on `linux/aarch64`) — the only
  aerodynamic engine in this module; import-guarded (ADR 0017).
- **`app/settings.py`** — every low-Re knob (`pydantic-settings`, `.env`).
- **`app/core/config.py`** — `AIRFOILS_DIR`. 🟢 The project convention names
  `core/config.py` as the single configuration home, yet the low-Re knobs live in
  `app/settings.py`; which is canonical is unresolved.
- **`components/airfoils/`** — 1 665 `.dat` files, the source of truth for
  geometry.
- **`wing-design`** — the consumer: station `airfoil` values resolve to these
  file stems.
- **`endurance_service`** — shares `G` and `RHO`, kept in sync by comment only.
  🟡 A duplicated constant with no shared import.
- **`polar_re_table_service`** — explicitly **not** a dependency; it implements
  the other, aircraft-level Re concept (gh-493).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The 2D per-airfoil Re grid and the aircraft-level speed-band table are kept as separate concepts, documented in both files | `airfoil_low_re.py:8-14`, `airfoil_low_re_service.py:3-9` | 🟢 |
| Airfoils are named by **file stem**, matching the CadQuery plugin's lookup | `airfoil_service.py:57-87` | 🟢 |
| The airfoil directory is absolute, not CWD-relative | `app/core/config.py:6-14` | 🟢 |
| Family classification order is fixed and documented as load-bearing | `airfoil_low_re_service.py:102-105` | 🟢 |
| Reflex is detected from camber-line **shape**, and `camber_at_te` therefore means "camber at x = 0.9" | gh-834; `airfoil_low_re_service.py:46-88` | 🟢 |
| Two NeuralFoil model sizes coexist: `"xxxlarge"` for the backfill, `"large"` interactively — explicitly "do NOT collapse" | `airfoil_low_re_service.py:428-431`; `endpoints/airfoils.py:111` | 🟢 |
| Confidence is windowed to the attached-flow range | `airfoil_low_re_service.py:524-566` | 🟢 |
| Interpolation is linear in `ln(Re)` to match NeuralFoil's training encoding | `airfoil_low_re_service.py:304-311` | 🟢 |
| Out-of-range Re is clamped **and the clamp is reported**, never extrapolated | `suitability_service.py:124-133` | 🟢 |
| Glide points are display-only and can never be the `active_lens` | `app/schemas/airfoil.py:71-84` | 🟢 |
| Ranking puts the confidence tier ahead of the score | `suitability_service.py:629, 632` | 🟢 |
| The tip-Re CL_max limitation is declared in every response rather than modelled or hidden | `app/schemas/airfoil.py:6-17, 174-187`; ADR 0012 | 🟢 |
| The fleet `cd0` reference is a 20th percentile, not a minimum | `airfoil_low_re_service.py:771-823` | 🟢 |
| Role tags are computed at query time — no column, no migration, no backfill | gh-835; `app/services/airfoil_tags.py` | 🟢 |
| The backfill is idempotent through `(airfoil_name, reynolds)` uniqueness plus provenance columns | `app/models/airfoil_low_re.py:65` | 🟢 |
| Child tables key on the natural name rather than the integer id | `app/models/airfoil_low_re.py:33, 65` | 🟢 — renaming is forbidden by convention (`Q-AF-7`), which is what makes the natural key safe |
| No ORM relationship from `AirfoilModel` to its children | `app/models/airfoil.py` | 🟡 |

## Internal State

The module is stateless between requests. Persistent state:

- `airfoils` — name, Selig coordinates, provenance filename.
- `airfoil_geometry` — one Re-independent row per airfoil: thickness, camber,
  `camber_at_te` (at x = 0.9), `family`.
- `airfoil_low_re_polar` — 13 rows per airfoil, one per Re grid point, with the
  extracted metrics, the parabolic fit and its validity window, the windowed
  confidence, and the provenance (`neuralfoil_model_size`, `n_crit`).
- `components/airfoils/*.dat` — the filesystem source of truth; the DB is a
  cache of it.

Computed at query time and never persisted: role tags, all three lens scores,
`cl_star`, the fleet `cd0` reference, `cl_max_margin`, `tip_re_flag`,
`re_clamped`, and every interpolated polar value.

## Observability

- `logger.warning` when AeroSandbox is unavailable and the sweep returns `[]`
  (`airfoil_low_re_service.py:458-462`). 🟢
- The import result is itself the observability surface: `imported` / `skipped` /
  `errors` / `error_files` (`AirfoilImportResult`,
  `app/schemas/airfoil.py:51`). 🟢
- The suitability response carries `SuitabilityCaveat`
  (`relative_ranking_only`, `no_hysteresis_modelling`,
  `ignores_tip_re_clmax_collapse`, `recommend_xfoil_validation`, `text`) plus
  per-item `min_analysis_confidence` and `tip_re_flag` — trust is reported in
  band, not logged. 🟢
- The code documents twice that a semantic change (gh-834 reflex, gh-825
  windowed confidence) requires a `--force` re-backfill; there is no automatic
  staleness detection beyond `neuralfoil_model_size` / `n_crit`. 🟡
- No metrics or traces. 🟢

## Risks and Gaps

- 🟡 **No Lednicer-format detection.** `_parse_dat_file` assumes Selig. A
  Lednicer file's leading surface-point counts would be read as coordinates,
  producing a silently wrong airfoil rather than an error.
- 🟢 **Two settings modules merge into one** (`Q-CC-4`, maintainer-answered).
  `app/settings.py` holds the airfoil/low-Re knobs plus `base_url` and
  `openai_api_key`; `app/core/config.py` holds `ARTIFACTS_BASE_DIR`, the copilot
  credentials and `AIRFOILS_DIR`. The project convention names
  `core/config.py` as the single place for configuration. Which is canonical?
- 🟢 **The child tables use `ForeignKey("airfoils.name")` with `ondelete=CASCADE`
  but no `ON UPDATE CASCADE`.** Renaming an airfoil would orphan its geometry
  and polars. Is renaming forbidden by convention, or is this a latent defect?
- 🟡 **No ORM relationship to the children** — deliberate for performance
  (1 665 × 13 rows), but nowhere stated, so a future contributor may "fix" it and
  reintroduce the load.
- 🟡 **`high_re` is knowingly approximate.** The grid tops out at 750 k, so the
  tag asserts something the data cannot fully support; it is marked approximate
  in the rule but the flag itself is boolean.
- 🟡 **`G` and `RHO` are duplicated** between `airfoil_low_re_service` and
  `endurance_service`, kept in sync by comment rather than by a shared import.
- 🟡 **Semantic re-backfills are manual.** Two documented cases (gh-834 family,
  gh-825 windowed confidence) changed the meaning of stored columns; only
  `neuralfoil_model_size` and `n_crit` are recorded as provenance, so a semantic
  change is invisible to the skip logic.
- 🟡 **The scoring lenses are relative rankings, not absolute predictions.** The
  caveat block says so (`relative_ranking_only = True`,
  `recommend_xfoil_validation`), but the numbers are still `[0,1]` scores that
  read as absolute.
