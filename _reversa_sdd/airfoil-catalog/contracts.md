# airfoil-catalog — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module:
> airfoil-catalog. All routes are mounted at the **application root** — there is
> no `/api/v2` segment. 🟢 Unlike every other Cluster-A module, these routes are
> **not** nested under an aeroplane: the catalogue is aircraft-independent. 🟢

## Global error contract 🟢

The shared domain→HTTP mapping applies:

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` | 500 | `internal_error` |
| bare `ServiceException` | 500 | `service_error` |

```json
{ "error": { "code": "not_found", "message": "…", "details": { "name": "…" } } }
```

## Unit and semantic contract 🟢

| Quantity | Unit / range | Note |
|---|---|---|
| `coordinates` | chord-normalised `0–1`, Selig order | `list[[x, y]]` |
| `max_thickness_pct`, `max_camber_pct` | **percent of chord** | not a fraction |
| `camber_at_te` | camber value **at x = 0.9** | not at the trailing edge (gh-834) |
| `reynolds` | absolute Reynolds number | one of the 13 grid values, 40 k → 750 k |
| `chord_m` | metres | |
| `speed_ms`, `v_cruise_mps`, `v_md_mps`, `v_min_sink_mps` | m/s | |
| `stall_gentleness` | `dCL/dα` just past the peak | **raw slope**, not normalised; ≈0 gentle, negative abrupt |
| `drag_bucket_width` | ΔCL where `CD ≤ 1.15·CD_min` | |
| all lens scores | `[0, 1]` | `null` when no component is available |
| `cl_max_margin` | `cl_max − max(target CLs)` | **negative = stall risk** |

Query Re is derived at sea level:

```
Re = ρ·V·c / μ      ρ = 1.225 kg/m³ ,  μ = 1.81e-5 Pa·s
```

(`suitability_service.py:74-75, 119-121`.) 🟢

## Frozen literal types 🟢

| Type | Values | Source |
|---|---|---|
| `AirfoilFamily` | `flat_bottom` \| `semi_symmetric` \| `symmetric` \| `cambered` \| `reflexed` | `app/schemas/airfoil.py:69` |
| `ActiveLens` | `re_agnostic` \| `mission` \| `target_cl_cruise` | `app/schemas/airfoil.py:84` — **glide points are never an `active_lens`** |
| `TargetClProvenance` | `estimated` \| `calculated` \| `mixed` | `app/schemas/airfoil.py:93` |
| role tags | `v_stabilizer` \| `h_stabilizer` \| `acro` \| `winglet` \| `low_re` \| `high_re` | `app/services/airfoil_tags.py:62-64` |
| mission types | `trainer` \| `sport` \| `aerobatic` \| `glider` \| `flying_wing` \| `slope_soarer` | `app/settings.py:19-56` |

## Routes — `app/api/v2/endpoints/airfoils.py` (1086 l.) 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `/airfoils` | list airfoils available on the filesystem | 200 · 500 |
| GET | `/airfoils/db` | list airfoils in the database | 200 · 500 |
| GET | `/airfoils/db/{name}` | read one airfoil (`AirfoilRead`) | 200 · 404 · 500 |
| GET | `/airfoils/db/suitability` | ranked suitability query (`SuitabilityResponse`) | 200 · 422 · 500 |
| POST | `/airfoils/import` | import a directory of `.dat` files | 200 · **422 outside `components`** · 500 |
| GET | `/airfoils/{airfoil_name}/known` | is this name known? | 200 · 500 |
| POST | `/airfoils/datfile` | upload a `.dat` file | 201 · 422 · 500 |
| GET | `/airfoils/{airfoil_name}/datfile` | download the `.dat` file | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/geometry-stats` | thickness / camber / family | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/coordinates` | raw Selig coordinates | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/neuralfoil/analysis` | interactive NeuralFoil sweep, **`model_size="large"`** (l.111) | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/neuralfoil/analysis/diagrams` | rendered diagrams for the sweep | 200 · 404 · 500 |

⚠ **Route-ordering hazard.** `/airfoils/db/suitability` must be declared before
`/airfoils/db/{name}`, otherwise `"suitability"` is captured as a name. 🟡
INFERRED from the path shapes; the declaration order was not read.

## Schemas 🟢

### `AirfoilSummary` (`app/schemas/airfoil.py:28`)

| Field | Type |
|---|---|
| `id` | `int` |
| `name` | `str` |

### `AirfoilRead` (l.37)

| Field | Type | Default |
|---|---|---|
| `id` | `int` | — |
| `name` | `str` | — |
| `coordinates` | `list[list[float]]` | — |
| `source_file` | `str \| None` | `None` |
| `created_at` | `datetime` | — |

### `AirfoilImportResult` (l.51)

| Field | Type | Default | Note |
|---|---|---|---|
| `imported` | `int` | `0` | newly inserted |
| `skipped` | `int` | `0` | already present (case-insensitive match) |
| `errors` | `int` | `0` | files whose parse or insert failed |
| `error_files` | `list[str]` | `[]` | the failing filenames |
| `imported_names` | `list[str]` | `[]` | **`exclude=True`** — internal only, not serialised |

### `SuitabilityQuery` (l.141) — echoed back in the response

| Field | Type | Note |
|---|---|---|
| `chord_m` | `float` | metres |
| `speed_ms` | `float` | m/s |
| `reynolds` | `float` | the **effective** Re after clamping |
| `re_clamped` | `bool` | `true` when the requested Re fell outside `[40 k, 750 k]` |
| `mission_type` | `str \| None` | one of the six mission bands |
| `target_cl_cruise` | `float \| None` | may drive the ranking |
| `target_cl_best_glide` | `float \| None` | **display only** |
| `target_cl_min_sink` | `float \| None` | **display only** |
| `target_cl_provenance` | `estimated \| calculated \| mixed` | default `estimated` |
| `active_lens` | `ActiveLens` | never a glide point |
| `v_cruise_mps` / `v_md_mps` / `v_min_sink_mps` | `float \| None` | m/s |

### `SuitabilityItem` (l.96) — one per ranked airfoil

| Field | Type | Note |
|---|---|---|
| `airfoil_name` | `str` | |
| `family` | `AirfoilFamily` | |
| `re_agnostic` | `float [0,1]` | Lens 1 |
| `mission` | `float \| None [0,1]` | Lens 2 |
| `target_cl_cruise` | `float \| None [0,1]` | Lens 3 |
| `target_cl_best_glide` | `float \| None [0,1]` | display only |
| `target_cl_min_sink` | `float \| None [0,1]` | display only |
| `stall_gentleness` | `float \| None` | **raw slope**, not normalised |
| `cl_max_margin` | `float \| None` | `cl_max − max(target CLs)`; negative = stall risk |
| `min_analysis_confidence` | `float [0,1]` | **windowed** over the attached-flow range |
| `tip_re_flag` | `bool` | see the threshold rule below |
| `caveat` | `str` | per-item note |
| `tags` | `list[str]` | role tags, **sorted** |

### `SuitabilityCaveat` (l.174)

| Field | Type | Default | Note |
|---|---|---|---|
| `relative_ranking_only` | `bool` | `True` | the scores rank, they do not predict |
| `no_hysteresis_modelling` | `bool` | `True` | |
| `ignores_tip_re_clmax_collapse` | `bool` | `True` | **always true** — the score treats section CL as whole-wing CL (ideal elliptic, untwisted) |
| `recommend_xfoil_validation` | `bool` | — | |
| `text` | `str` | — | human-readable summary |

### `SuitabilityResponse` (l.190)

`{ query: SuitabilityQuery, caveat: SuitabilityCaveat, results: list[SuitabilityItem] }` 🟢

## Ranking contract 🟢

1. `active_lens` selects the ranking score; it may only be `re_agnostic`,
   `mission` or `target_cl_cruise`. Glide points are display-only, so the default
   sort is never driven by an engine-out or min-sink contingency point
   (`app/schemas/airfoil.py:71-84`).
2. Results are sorted by **`(confidence tier, −score)`** — the confidence tier is
   the **primary** key, so a high-scoring low-confidence airfoil never outranks a
   trustworthy one (`suitability_service.py:629, 632`).
3. `tip_re_flag` fires when `Re_tip < low_re_tip_re_abs_floor = 80 000` **or** the
   root→tip Re drop exceeds `low_re_tip_re_rel_drop = 50 000`
   (`app/settings.py:109-114`).
4. An out-of-range query Re is **clamped** to the nearest grid endpoint and
   `re_clamped` is set; it is never extrapolated
   (`suitability_service._clamp_re_to_grid`, l.124-133).

## Scoring contract (behavioural, reproducible without the source) 🟢

```
Lens 1 — score_re_agnostic                                     (l.831-891)
  ld_max            → min(ld_max / 60.0, 1)            weight 0.35
  cl_max            → min(cl_max / 1.5,  1)            weight 0.25
  drag_bucket_width → min(bucket / 0.8,  1)            weight 0.20
  stall_gentleness  → clamp(1 + stall/0.15, 0, 1)      weight 0.10
  cd_min            → min(0.008 / cd_min, 1)           weight 0.10
  score = Σ(v·w) / Σw  clamped to [0,1];  None if no component is available

Lens 2 — score_mission = re_agnostic × family_bonus × thickness_match × cl_bonus   (l.894-940)
  family_bonus    = 1.0 if family ∈ preferred_families else 0.7
  thickness_match = 1.0 inside [t_min, t_max]; outside: max(0, 1 − gap/5.0)
  cl_bonus        = (1 − cl_max_weight) + cl_max_weight · min(cl_max/1.5, 1)

Lens 3 — score_target_cl = Match × Efficiency                  (l.943-1009)
  cl_star   = sqrt(cl0² + cd0/k)          (None when cd0 ≤ 0 or k ≤ 0)
  r         = CD(cl_target) / cd0
  r_poor    = 2.5
  tolerance = (drag_bucket_width / 0.6) × 0.5
  Match     = 1.0                      if r ≤ 1
            = 1 − (r−1)/(r_poor−1)     within tolerance
            = 0.0                      if r ≥ r_poor, unless the fallback applies
  fallback  = clamp((cl_max − cl_target) / 0.30, 0, 1)   when r ≥ r_poor and cl_max exists
  Efficiency = min(re_cd0_reference / cd0, 1.0)
  Final      = clamp(Match × Efficiency, 0, 1)

Fleet reference — compute_re_cd0_reference(..., percentile = 20.0)   (l.771-823)
  interpolate every airfoil to re_query, take the 20th percentile of finite cd0
  fallback _CD0_REFERENCE_FALLBACK = 0.020 on an empty fleet

Level-flight CL — CL = (m·g) / (0.5·ρ·V²·S) ;  ValueError for V ≤ 0 or S ≤ 0   (l.686-707)
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

## Role-tag contract (gh-835) 🟢

Computed at query time; never persisted. Constants:
`LOW_RE_UPPER_BOUND = 150 000`, `HIGH_RE_LOWER_BOUND = 500 000`,
`LOW_RE_CONFIDENCE_GATE = 0.85`.

| Tag | Rule |
|---|---|
| `v_stabilizer` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `6 ≤ t ≤ 15 %` |
| `h_stabilizer` | identical gate — kept separate for UX filtering |
| `acro` | `family == symmetric` ∧ `camber ≤ 0.5 %` ∧ `7 ≤ t ≤ 12 %` |
| `winglet` | `t ≤ 10 %` ∧ `family ∈ {symmetric, semi_symmetric, reflexed}` ∧ `camber ≤ 3 %` ∧ ≥ 1 confident polar at `Re ≤ 150 k` |
| `low_re` | ≥ 1 polar row `Re ≤ 150 k` with confidence ≥ 0.85 |
| `high_re` | ≥ 1 polar row `Re ≥ 500 k` with confidence ≥ 0.85 — **approximate**: the grid tops out at 750 k |

Tags are returned **sorted** for determinism. 🟢

## Configuration surface — `app/settings.py` 🟢

| Setting | Default | Meaning |
|---|---|---|
| `low_re_grid` | 13 values, 40 000 → 750 000 | absolute Re grid |
| `low_re_neuralfoil_model_size` | `"xxxlarge"` | backfill model; the interactive endpoint uses `"large"` — **do not collapse** |
| `low_re_n_crit` | `9.0` | e^N transition criterion |
| `low_re_confidence_gate` | `0.90` | α points below this are excluded from metric extraction |
| `low_re_low_confidence_flag` | `0.85` | UI trust badge threshold |
| `low_re_score_r_poor` | `2.5` | drag-rise ratio at which Match → 0 |
| `low_re_bucket_tolerance_ref` | `0.6` | wide-bucket reference for the tolerance band |
| `low_re_score_cl_max_safety_band` | `0.30` | CL_max-margin fallback band |
| `low_re_tip_re_abs_floor` | `80 000` | `Re_tip` below this → `tip_re_flag` |
| `low_re_tip_re_rel_drop` | `50 000` | root→tip Re drop above this → `tip_re_flag` |
| `low_re_mission_weights` | 6 mission profiles | the table above |

🟢 There are **two** settings modules — `app/settings.py` (airfoil/low-Re plus
`base_url`, `openai_api_key`) and `app/core/config.py` (`ARTIFACTS_BASE_DIR`,
copilot credentials, `AIRFOILS_DIR`). The project convention names
`core/config.py` as the single configuration home. Which is canonical is
unresolved.

## Ingestion contract 🟢

| Guarantee | Evidence |
|---|---|
| **Selig format only.** The first line is skipped as a header; every later line must yield two parseable floats or it is silently skipped; fewer than 3 lines or 3 valid coordinates raises `ValueError` | `airfoil_service.py:57-87` |
| The canonical name is the **file stem**, not the Selig header — matching the CadQuery plugin's lookup | `airfoil_service.py:57-87` |
| No normalisation and no re-panelling is performed | `airfoil_service.py:57-87` |
| The import directory must resolve **inside `<project_root>/components`** or `ValidationError` is raised before any read | `airfoil_service.py:97-106` |
| Recursive `rglob("*.dat")` with case-insensitive dedup against existing names | `airfoil_service.py:90-154` |
| A per-file `try/except` increments `errors` and calls `db.rollback()` so the loop continues | `airfoil_service.py:90-154` |
| The airfoil directory is absolute and CWD-independent | `app/core/config.py:6-14` |

🟡 There is **no format sniffing** — a Lednicer-format file would be mis-parsed
as coordinates rather than rejected. **Measured (`Q-AF-1`):** a scan replicating
`_parse_dat_file` exactly over all **1 665 bundled files found 0 Lednicer
candidates**, 0 files with `|y| > 1.0` and 0 files with fewer than 3 parsable
points — the bundled set is entirely Selig, so the risk is theoretical for
shipped data. It remains real for **uploaded** files, where a Lednicer header
row would be read as a coordinate pair.

## Polar-computation contract 🟢

```python
compute_airfoil_low_re(name, coords, re_grid, *,
                       model_size="xxxlarge", n_crit=9.0,
                       confidence_gate=0.90,
                       alpha_start=-5.0, alpha_end=18.0,
                       alpha_step=0.2) -> list[dict]      # l.406-521
```

Per Re grid point: `asb.Airfoil(...).get_aero_from_neuralfoil(alpha=α_grid,
Re=re, mach=0.0, n_crit=n_crit, model_size=model_size)`. Only α points with
`analysis_confidence ≥ 0.90` feed metric extraction. Returns `[]` with a warning
when AeroSandbox is unavailable (ADR 0017).

Persisted per `(airfoil, Re)`: `ld_max`, `cl_max`, `alpha_attached_lo/hi`,
`drag_bucket_width`, `cd_min`, `stall_gentleness`, the parabolic fit
`CD = cd0 + k·(CL − cl0)²` with `[cl_valid_lo, cl_valid_hi]`, and
`min_analysis_confidence` — the **windowed** minimum over
`[alpha_attached_lo, alpha_attached_hi]`, falling back to the whole-sweep
minimum when that window is undefined or has fewer than 4 points
(`_windowed_min_confidence`, l.524-566).

Idempotence: `UniqueConstraint("airfoil_name", "reynolds")`;
`neuralfoil_model_size` and `n_crit` are stored as provenance so an up-to-date
row can be skipped (`app/models/airfoil_low_re.py:65`). A **semantic** change
(gh-834 family, gh-825 windowed confidence) is *not* detectable this way and
requires a `--force` re-backfill. 🟡

## Interpolation contract 🟢

`interpolate_polar_at_re(polar_rows, re_query, re_grid)` interpolates **linearly
in `ln(Re)`** — matching NeuralFoil's training encoding
(`airfoil_low_re_service.py:304-311`). Out-of-range queries are clamped to the
nearest grid endpoint and the response reports `re_clamped = True`.

## Not part of this contract

- The **aircraft-level** speed-band Re table → `polar_re_table_service`
  (gh-493). It re-bins aircraft fine-sweep data into speed-band labels where
  "Re" is a speed proxy at the main wing's MAC for a specific flight condition.
  **Do not conflate the two Re concepts** — both
  `app/models/airfoil_low_re.py:8-14` and
  `app/services/airfoil_low_re_service.py:3-9` say so explicitly.
- Assigning an airfoil to a wing station → `wing-design`.
- 3D aerodynamic analysis over the wing → `aero-analysis`.
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
