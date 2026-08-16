# suitability-search — Technical Design

> Use-case design, nested under [`airfoil-catalog`](../design.md).
> Focuses on HOW this slice is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`../contracts.md`](../contracts.md).

## Interface

### Query orchestration — `app/services/suitability_service.py` (709 l.) 🟢

| Symbol | Purpose | Line |
|---|---|---|
| query Re from chord and speed | `Re = ρ·V·c / μ` | l.74-75, 119-121 |
| `_clamp_re_to_grid` | clamp to the nearest grid endpoint + set `re_clamped` | l.124-133 |
| ranking | sort by `(confidence tier, −score)` | l.629, 632 |

### Scoring — `app/services/airfoil_low_re_service.py` (1086 l.) 🟢

| Symbol | Signature / purpose | Line |
|---|---|---|
| `interpolate_polar_at_re` | `(polar_rows, re_query, re_grid)` → interpolated metrics, linear in `ln(Re)` | l.304-311 |
| `_level_flight_cl` | `CL = (m·g) / (0.5·ρ·V²·S)`; `ValueError` for `V ≤ 0` or `S ≤ 0` | l.686-707 |
| `best_ld_cl` | `(cd0, k, cl0)` → `sqrt(cl0² + cd0/k)`; `None` for `cd0 ≤ 0` or `k ≤ 0` | l.715-760 |
| `compute_re_cd0_reference` | `(polars_by_name, re_query, percentile=20.0)` → robust fleet `cd0` | l.771-823 |
| `score_re_agnostic` | Lens 1 | l.831-891 |
| `score_mission` | Lens 2 | l.894-940 |
| `score_target_cl` | Lens 3 | l.943-1009 |

Shared physical constants, kept in sync with `endurance_service` **by comment
only**: `G = 9.80665`, `RHO = 1.225` (l.39-40). 🟡

### Role tags — `app/services/airfoil_tags.py` 🟢

Computed at query time; the literal tag set lives at l.62-64. Constants:
`LOW_RE_UPPER_BOUND = 150 000`, `HIGH_RE_LOWER_BOUND = 500 000`,
`LOW_RE_CONFIDENCE_GATE = 0.85`.

### Routes owned by this slice 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `/airfoils/db/suitability` | ranked suitability query (`SuitabilityResponse`) | 200 · 422 · 500 |
| GET | `/airfoils/{airfoil_name}/known` | is this name known? | 200 · 500 |

⚠ `/airfoils/db/suitability` must be declared **before** `/airfoils/db/{name}`,
otherwise `"suitability"` is captured as a name. 🟡 INFERRED from the path
shapes; the declaration order was not read.

### Data read (never written) 🟢

| Table | Used for |
|---|---|
| `airfoils` | the candidate set and the `known` lookup |
| `airfoil_geometry` | `family`, `max_thickness_pct`, `max_camber_pct` — Lens 2 and every tag rule |
| `airfoil_low_re_polar` | the 13 rows per airfoil interpolated to the query Re |

This slice performs **no writes**. Every score, tag, flag and interpolated value
is computed per request and discarded.

## Main Flow

### F1 — Build the query 🟢

1. Take `chord_m` and `speed_ms` from the request.
2. Compute the query Reynolds number at standard sea level:

   ```
   Re = ρ·V·c / μ      ρ = 1.225 kg/m³ ,  μ = 1.81e-5 Pa·s
   ```

   (`suitability_service.py:74-75, 119-121`.)
3. `_clamp_re_to_grid` (l.124-133) clamps an out-of-range value to the nearest
   endpoint of the 13-point grid `[40 k … 750 k]` and sets `re_clamped = True`.
   It is **never** extrapolated.
4. Resolve `active_lens`, `mission_type` and the three `target_cl_*` values, and
   echo the whole thing back as `SuitabilityQuery` — with `reynolds` holding the
   **effective** (post-clamp) value.

> This `reynolds` is an **absolute** Reynolds number from the 2D per-airfoil grid
> (gh-821), not the aircraft-level speed-band proxy of `polar_re_table_service`
> (gh-493). 🟢 Both `app/models/airfoil_low_re.py:8-14` and
> `airfoil_low_re_service.py:3-9` warn against conflating them.

### F2 — Interpolate every candidate to the query Re 🟢

`interpolate_polar_at_re(polar_rows, re_query, re_grid)` interpolates **linearly
in `ln(Re)`** (l.304-311), matching NeuralFoil's training encoding. A query at
the *geometric* mean of two grid points therefore returns the *arithmetic* mean
of the metric — a linear-in-Re implementation would not.

### F3 — Compute the fleet reference (`compute_re_cd0_reference`, l.771-823) 🟢

```
interpolate every airfoil to re_query
take the 20th percentile of the finite cd0 values      (percentile = 20.0)
fall back to _CD0_REFERENCE_FALLBACK = 0.020 on an empty fleet
```

A robust "best achievable at this Re" reference rather than the absolute
minimum, so one freak airfoil cannot deflate everyone else's Lens 3 Efficiency.

### F4 — Lens 1, `score_re_agnostic` (l.831-891) 🟢

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

A missing component is dropped from **both** numerator and denominator. It is
never treated as a zero — that would systematically punish sparsely analysed
airfoils. When none remains the score is `None`, not `0`.

### F5 — Lens 2, `score_mission` (l.894-940) 🟢

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

Lens 2 **multiplies** Lens 1, so it inherits Lens 1's `None` when no component
was available.

### F6 — Lens 3, `score_target_cl` (l.943-1009) 🟢

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

`best_ld_cl` returns `None` for `cd0 ≤ 0` or `k ≤ 0` — the derivation is written
out in full in the docstring (l.715-760).

**Why the CL_max fallback exists** (l.977-997): glider min-sink CLs
(`CL ≈ √3 · CL_md`) sit far above `cl_star`, so the pure drag-rise Match
collapses to 0 even for excellent glider sections. The fallback rescues them by
scoring the remaining CL_max margin instead of the drag rise.

### F7 — Level-flight CL helper (`_level_flight_cl`, l.686-707) 🟢

```
CL = (m·g) / (0.5·ρ·V²·S)      raises ValueError for V ≤ 0 or S ≤ 0
```

Used to derive the `target_cl_*` values when the caller supplies mass, speed and
area rather than CLs directly. 🟡 The exact call sites were not read.

### F8 — Rank and assemble the response 🟢

1. **Only three lenses may rank.** `active_lens ∈ {re_agnostic, mission,
   target_cl_cruise}`. `target_cl_best_glide` and `target_cl_min_sink` are
   computed and returned per item but are **display-only**, so the default sort
   is never driven by an engine-out / min-sink contingency point
   (`app/schemas/airfoil.py:71-84`).
2. **Tie-breaking.** Sort by `(confidence tier, −score)` — the confidence tier is
   the **primary** key, so a high-scoring low-confidence airfoil never outranks a
   trustworthy one (`suitability_service.py:629, 632`).
3. **Tip-stall caveat.** The score treats section CL as whole-wing CL (ideal
   elliptic, untwisted), ignoring the tip-Re CL_max collapse that governs
   tip-stall onset on tapered wings. The contract therefore **always** sets
   `ignores_tip_re_clmax_collapse = True` and exposes:

   ```
   tip_re_flag    = Re_tip < low_re_tip_re_abs_floor (80 000)
                    OR (Re_root − Re_tip) > low_re_tip_re_rel_drop (50 000)
   cl_max_margin  = cl_max − max(target CLs)          negative = stall risk
   ```

   (`app/schemas/airfoil.py:6-17, 174-187`; `app/settings.py:109-114`.)
4. Return `SuitabilityResponse{ query, caveat, results }`.

### F9 — Role tags (gh-835, `app/services/airfoil_tags.py`) 🟢

Computed **at query time** from stored geometry + polars — no DB column, no
migration, no backfill. Constants: `LOW_RE_UPPER_BOUND = 150 000`,
`HIGH_RE_LOWER_BOUND = 500 000`, `LOW_RE_CONFIDENCE_GATE = 0.85`.

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

- **Query Re outside `[40 k, 750 k]`:** clamped to the nearest endpoint,
  `re_clamped = True` in the response. Never extrapolated. 🟢
- **A scoring component is missing:** dropped from both numerator and
  denominator; if none remain the score is `None`, not `0`. 🟢
- **Lens 1 returns `None`:** Lens 2 multiplies it, so it is `None` too. 🟡
  INFERRED from the multiplicative form; the null-propagation branch was not read
  directly.
- **`cd0 ≤ 0` or `k ≤ 0`:** `best_ld_cl` returns `None`, so Lens 3 has no
  `cl_star` for that airfoil. 🟢
- **`r ≥ r_poor` with a known `cl_max`:** the CL_max safety fallback replaces the
  zero Match rather than discarding the airfoil. 🟢
- **`r ≥ r_poor` with no `cl_max`:** Match is `0.0` and the airfoil ranks last
  within its confidence tier. 🟢
- **Empty fleet:** `compute_re_cd0_reference` falls back to
  `_CD0_REFERENCE_FALLBACK = 0.020`. 🟢
- **Non-positive `V` or `S`:** `_level_flight_cl` raises `ValueError`. 🟢
- **Glide lens requested:** rejected at validation — `ActiveLens` admits only
  three values. 🟢
- **Airfoil with no polar rows at all:** 🟡 it cannot be interpolated; whether it
  is omitted from `results` or returned with `null` scores was not read.
- **Route collision:** if `/airfoils/db/{name}` is declared first,
  `/airfoils/db/suitability` resolves to a lookup for an airfoil literally named
  `"suitability"` and returns 404. 🟡 INFERRED hazard.

## Dependencies

- **[`low-re-polar-backfill`](../low-re-polar-backfill/design.md)** — the
  producer of every row this slice reads: `airfoils`, `airfoil_geometry` and the
  13 `airfoil_low_re_polar` rows per airfoil. This slice is **read-only** over
  them.
- **`app/settings.py`** — the mission bands (l.19-56), `low_re_score_r_poor`,
  `low_re_bucket_tolerance_ref`, `low_re_score_cl_max_safety_band`, and the
  tip-Re thresholds (l.109-114). 🟢 The project convention names
  `app/core/config.py` as the single configuration home; which module is
  canonical is unresolved.
- **`endurance_service`** — shares `G = 9.80665` and `RHO = 1.225`, kept in sync
  **by comment only**, with no shared import. 🟡
- **NumPy** — percentile and interpolation arithmetic.
- **`polar_re_table_service`** — explicitly **not** a dependency; it implements
  the other, aircraft-level Re concept (gh-493).
- **AeroSandbox** — **not** required. This slice reads persisted polars only, so
  it works unchanged on a platform without a solver. 🟡 INFERRED from the absence
  of any ASB import in the scoring path.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Interpolation is linear in `ln(Re)` to match NeuralFoil's training encoding | `airfoil_low_re_service.py:304-311` | 🟢 |
| Out-of-range Re is clamped **and the clamp is reported**, never extrapolated | `suitability_service.py:124-133` | 🟢 |
| A missing scoring component is renormalised away rather than treated as zero | `airfoil_low_re_service.py:831-891` | 🟢 |
| Lens 2 multiplies Lens 1 rather than re-weighting from scratch | `airfoil_low_re_service.py:894-940` | 🟢 |
| Lens 3 separates "does this airfoil like this CL" (Match) from "is it a good airfoil at this Re" (Efficiency) | `airfoil_low_re_service.py:943-1009` | 🟢 |
| A CL_max safety fallback rescues high-CL glider points that the drag-rise Match would zero | `airfoil_low_re_service.py:977-997` | 🟢 |
| The fleet `cd0` reference is a 20th percentile, not a minimum | `airfoil_low_re_service.py:771-823` | 🟢 |
| `best_ld_cl` has a closed form and returns `None` rather than defaulting on a degenerate fit | `airfoil_low_re_service.py:715-760` | 🟢 |
| Glide points are display-only and can never be the `active_lens` | `app/schemas/airfoil.py:71-84` | 🟢 |
| Ranking puts the confidence tier ahead of the score | `suitability_service.py:629, 632` | 🟢 |
| The tip-Re CL_max limitation is declared in every response rather than modelled or hidden | `app/schemas/airfoil.py:6-17, 174-187`; ADR 0012 | 🟢 |
| The scores are declared `relative_ranking_only`, not absolute predictions | `app/schemas/airfoil.py:174` | 🟢 |
| Role tags are computed at query time — no column, no migration, no backfill | gh-835; `app/services/airfoil_tags.py` | 🟢 |
| `h_stabilizer` duplicates `v_stabilizer`'s gate but is kept separate for UX filtering | `app/services/airfoil_tags.py` | 🟢 |
| Tags are sorted for deterministic output | `app/services/airfoil_tags.py` | 🟢 |

## Internal State

**None.** This slice is stateless in the strongest sense: it performs no writes
and holds nothing between requests.

Per-request transient state:

- the effective query Re and its `re_clamped` flag;
- one interpolated polar per candidate airfoil;
- the fleet `cd0` reference for this Re;
- the three lens scores, `cl_star`, `cl_max_margin`, `tip_re_flag` and the role
  tags per item.

Everything it reads (`airfoils`, `airfoil_geometry`, `airfoil_low_re_polar`) is
owned by [`low-re-polar-backfill`](../low-re-polar-backfill/design.md).

## Observability

- The **response itself** is the observability surface. `SuitabilityCaveat`
  carries `relative_ranking_only`, `no_hysteresis_modelling`,
  `ignores_tip_re_clmax_collapse`, `recommend_xfoil_validation` and a
  human-readable `text`; each `SuitabilityItem` carries
  `min_analysis_confidence`, `tip_re_flag`, `cl_max_margin` and a per-item
  `caveat`. Trust is reported in band, not logged (ADR 0012 in spirit). 🟢
- `SuitabilityQuery` echoes the **effective** Re and `re_clamped`, so a caller
  can always tell whether their request was honoured verbatim. 🟢
- `target_cl_provenance` (`estimated | calculated | mixed`) records how the
  target CLs were obtained. 🟢
- No logs, metrics or traces specific to this slice were found. 🟡

## Risks and Gaps

- 🟢 **Two settings modules merge into one** (`Q-CC-4`, maintainer-answered).
  `app/settings.py` holds every scoring knob this slice reads; the project
  convention names `app/core/config.py` as the single configuration home. Which
  is canonical?
- 🟡 **The `/airfoils/db/suitability` vs `/airfoils/db/{name}` ordering is
  unverified.** If the parameterised route is declared first, the suitability
  route is unreachable. The declaration order was not read.
- 🟡 **`high_re` asserts more than the data supports.** The grid tops out at
  750 k, so the tag is knowingly approximate but exposed as a plain boolean with
  no degraded-confidence signal of its own.
- 🟡 **`G` and `RHO` are duplicated** between `airfoil_low_re_service` and
  `endurance_service`, kept in sync by comment rather than by a shared import.
  A change in one silently diverges from the other.
- 🟡 **The scoring lenses are relative rankings, not absolute predictions.** The
  caveat block says so (`relative_ranking_only = True`,
  `recommend_xfoil_validation`), but the numbers are still `[0,1]` scores that
  read as absolute to a casual consumer.
- 🟡 **Null propagation through Lens 2 is inferred, not confirmed.** Lens 2
  multiplies Lens 1, so a `None` should propagate — but the branch was not read.
- 🟡 **The treatment of an airfoil with no polar rows is unknown.** Whether it is
  omitted from `results` or returned with `null` scores was not read.
- 🟡 **`_level_flight_cl`'s call sites were not read**, so it is unclear which
  `target_cl_*` values are derived from it versus supplied directly by the
  caller.
- 🟡 **The confidence *tier* boundaries were not read.** Ranking sorts on a tier
  derived from `min_analysis_confidence`, and `low_re_low_confidence_flag = 0.85`
  is the documented UI badge threshold, but whether the tier uses that same
  value — or how many tiers exist — is unconfirmed.
