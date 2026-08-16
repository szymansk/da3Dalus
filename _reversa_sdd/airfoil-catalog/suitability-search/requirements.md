# suitability-search

> Use-case specification, nested under [`airfoil-catalog`](../requirements.md).
> Focuses on WHAT this slice does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: airfoil-catalog,
> `_reversa_sdd/data-dictionary.md` §Module: airfoil-catalog.

## Overview

`suitability-search` is the **read side** of the catalogue: given a chord, a
speed and an optional mission and target CLs, it interpolates every airfoil's
precomputed polars to the query Reynolds number, scores them through one of
three lenses, tags them, ranks them confidence-first, and returns the list
together with an explicit caveat block. Nothing here is persisted — every score,
tag and flag is computed per request. 🟢

## Responsibilities

- Derive the query Reynolds number from chord and speed at sea level. 🟢
- Interpolate a polar to an arbitrary Re **linearly in `ln(Re)`**, clamping
  out-of-range queries and reporting the clamp. 🟢
- Score airfoils through the three lenses — `re_agnostic`, `mission`,
  `target_cl_cruise` — reproducing every weight, threshold and fallback. 🟢
- Compute the fleet `cd0` reference as a robust 20th percentile. 🟢
- Rank by confidence tier first, score second. 🟢
- Compute role tags at query time from stored geometry and polars. 🟢
- Emit the always-on caveat block, `tip_re_flag` and `cl_max_margin`. 🟢
- Guarantee that a glide contingency point can never drive the ranking. 🟢

**Explicitly NOT this slice's responsibility:** parsing, importing, classifying
or computing the polars
(→ [`low-re-polar-backfill`](../low-re-polar-backfill/requirements.md)); the
interactive single-airfoil endpoints
(→ [`neuralfoil-analysis`](../neuralfoil-analysis/requirements.md)); the
**aircraft-level** speed-band Re table (→ `polar_re_table_service`, gh-493 — a
different Re concept entirely).

## Business Rules

> Rule ids are inherited from [`../requirements.md`](../requirements.md); the
> "derives from" note names the module-level rule each row refines.

### The Reynolds concept this slice queries

- **BR-C1 — This slice queries the 2D per-airfoil, absolute Re grid.** 🟢
  *(module BR-C1.)* The polars it reads were computed over an **absolute Re grid
  40 k–750 k** independent of any aircraft (gh-821). The aircraft-level
  speed-band table (`polar_re_table_service`, gh-493) is a **different concept**
  in which "Re" is a speed proxy at the main wing's MAC for a specific flight
  condition. Both `app/models/airfoil_low_re.py:8-14` and
  `app/services/airfoil_low_re_service.py:3-9` say so explicitly. **Do not
  conflate them** — this slice's `reynolds` field is an absolute Reynolds number.

### Query Reynolds number

- **BR-C17 — Query Re uses standard sea-level air.** 🟢 *(module BR-C17.)*

  ```
  Re = ρ·V·c / μ    with  ρ = 1.225 kg/m³,  μ = 1.81e-5 Pa·s
  ```

  (`app/services/suitability_service.py:74-75, 119-121`.) Physical constants
  shared with `endurance_service` and kept in sync **by comment only**:
  `G = 9.80665`, `RHO = 1.225`
  (`app/services/airfoil_low_re_service.py:39-40`). 🟡 A duplicated constant with
  no shared import.
- **BR-C16 — Interpolation is linear in `ln(Re)`; out-of-range is clamped and
  reported.** 🟢 *(module BR-C16.)* `interpolate_polar_at_re(polar_rows,
  re_query, re_grid)` interpolates linearly in `ln(Re)` to match NeuralFoil's
  training encoding (`airfoil_low_re_service.py:304-311`). Out-of-range queries
  are **clamped** to the nearest grid endpoint and the response reports
  `re_clamped = True` (`suitability_service._clamp_re_to_grid`, l.124-133).
  It is never extrapolated.

### Scoring

- **BR-C19 — Only three lenses may drive the ranking.** 🟢 *(module BR-C19.)*
  `active_lens ∈ {re_agnostic, mission, target_cl_cruise}`. **Glide points never
  auto-rank** — `target_cl_best_glide` and `target_cl_min_sink` are computed and
  displayed but can never be the `active_lens`, so the default sort is never
  driven by an engine-out / min-sink contingency point
  (`app/schemas/airfoil.py:71-84`).
- **BR-C20 — Lens 1, `score_re_agnostic`** (l.831-891): a weighted sum of
  normalised metrics, **renormalised by the weights actually present**. 🟢
  *(module BR-C20.)*

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

  A missing component is dropped from **both** numerator and denominator — it is
  never treated as a zero. When none remains the score is `None`, not `0`.
- **BR-C21 — Lens 2, `score_mission`** (l.894-940): 🟢 *(module BR-C21.)*

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

- **BR-C22 — Lens 3, `score_target_cl`** (l.943-1009) is `Match × Efficiency`:
  🟢 *(module BR-C22.)*

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
  out in full in the docstring (l.715-760).
- **BR-C22a — Why the CL_max fallback exists.** 🟢 Glider min-sink CLs
  (`CL ≈ √3 · CL_md`) sit far above `cl_star`, so the pure drag-rise Match
  collapses to 0 even for excellent glider sections. The fallback rescues them by
  scoring the remaining CL_max margin instead (l.977-997).
- **BR-C23 — The fleet reference is a robust percentile, not a minimum.** 🟢
  *(module BR-C23.)* `compute_re_cd0_reference(polars_by_name, re_query,
  percentile=20.0)` (l.771-823) interpolates every airfoil to `re_query` and
  returns the **20th percentile** of the finite `cd0` values — a robust "best
  achievable at this Re" reference rather than the absolute minimum, so one freak
  airfoil cannot deflate everyone else's Efficiency. Falls back to
  `_CD0_REFERENCE_FALLBACK = 0.020` on an empty fleet.
- **BR-C24 — Level-flight CL helper.** 🟢 *(module BR-C24.)*
  `CL = (m·g) / (0.5·ρ·V²·S)`, raising `ValueError` for non-positive `V` or `S`
  (`_level_flight_cl`, l.686-707).

### Ranking and honesty

- **BR-C25 — Confidence outranks score.** 🟢 *(module BR-C25.)* Ranking sorts by
  `(confidence tier, −score)` — the confidence tier is the **primary** key, so a
  high-scoring low-confidence airfoil never outranks a trustworthy one
  (`suitability_service.py:629, 632`).
- **BR-C26 — The tip-stall caveat is always on.** 🟢 *(module BR-C26.)* The score
  treats section CL as whole-wing CL (ideal elliptic, untwisted), ignoring the
  tip-Re CL_max collapse that governs tip-stall onset on tapered wings. The
  contract therefore **always** sets `ignores_tip_re_clmax_collapse = True` and
  exposes `tip_re_flag` plus `cl_max_margin = cl_max − max(target CLs)`
  (**negative = stall risk**) (`app/schemas/airfoil.py:6-17, 174-187`).
  `tip_re_flag` fires when `Re_tip < low_re_tip_re_abs_floor = 80 000`
  **or** the root→tip drop exceeds `low_re_tip_re_rel_drop = 50 000`
  (`app/settings.py:109-114`).
- **BR-C26a — The caveat block declares four limitations.** 🟢
  `SuitabilityCaveat` (`app/schemas/airfoil.py:174`) carries
  `relative_ranking_only = True`, `no_hysteresis_modelling = True`,
  `ignores_tip_re_clmax_collapse = True`, `recommend_xfoil_validation` and a
  human-readable `text`. The scores **rank**, they do not predict — this is
  reported in band rather than logged (ADR 0012 in spirit).

### Role tags

- **BR-C27 — Tags are computed at query time, never persisted.** 🟢
  *(module BR-C27.)* No DB column, no migration, no backfill
  (`app/services/airfoil_tags.py`, gh-835). Constants:
  `LOW_RE_UPPER_BOUND = 150 000`, `HIGH_RE_LOWER_BOUND = 500 000`,
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

### Routing

- **BR-S1 — Route-ordering hazard.** 🟡 `/airfoils/db/suitability` must be
  declared **before** `/airfoils/db/{name}`, otherwise `"suitability"` is
  captured as an airfoil name. INFERRED from the path shapes; the declaration
  order in `app/api/v2/endpoints/airfoils.py` was not read.

## Functional Requirements

> "Refines" names the module RF in [`../requirements.md`](../requirements.md).

| ID | Refines | Requirement | Priority | Acceptance criterion |
|----|---------|-------------|----------|----------------------|
| RF-12 | RF-12 | Interpolate a polar to an arbitrary Re linearly in `ln(Re)` | Must | A query at the geometric mean of two grid points returns the arithmetic mean of the metric |
| RF-13 | RF-13 | Clamp an out-of-range Re and report `re_clamped = true` | Must | `Re = 10 000` clamps to 40 000 and sets the flag; `Re = 1 000 000` clamps to 750 000 |
| RF-14 | RF-14 | Compute the query Re from chord and speed at sea level | Must | `Re = 1.225·V·c / 1.81e-5` for the given `chord_m` and `speed_ms` |
| RF-15 | RF-15 | Rank a fleet through the selected lens and return `SuitabilityResponse` | Must | `GET /airfoils/db/suitability` → 200 with `query`, `caveat` and a ranked `results` list |
| RF-16 | RF-16 | Never let a glide point drive the ranking | Must | `active_lens` cannot take `target_cl_best_glide` or `target_cl_min_sink` |
| RF-17 | RF-17 | Sort by confidence tier first, score second | Must | A 0.95-score / low-confidence airfoil ranks below a 0.80-score / high-confidence one |
| RF-18 | RF-18 | Always emit the tip-stall caveat and `cl_max_margin` | Must | `ignores_tip_re_clmax_collapse` is `true` in every response |
| RF-19 | RF-19 | Flag a tip-Re risk from the absolute floor or the root→tip drop | Should | `Re_tip = 70 000` sets `tip_re_flag`; a 200 k → 140 k drop also sets it |
| RF-20 | RF-20 | Compute role tags at query time and return them sorted | Should | A 9 % symmetric section carries `acro`, `h_stabilizer`, `v_stabilizer` in sorted order |
| RF-25 | RF-25 | Answer whether an airfoil name is known | Could | `GET /airfoils/{name}/known` → 200 with a boolean |
| RF-S1 | RF-15 | Score through Lens 1 with weight renormalisation | Must | An airfoil missing `cl_max` scores from the remaining four weights; all missing → `None`, not `0` |
| RF-S2 | RF-15 | Score through Lens 2 across the six mission bands | Must | Each band's `t_min`, `t_max`, `cl_max_weight` and preferred families are honoured |
| RF-S3 | RF-15 | Score through Lens 3 with the CL_max safety fallback | Must | A glider min-sink CL scores non-zero via the fallback rather than collapsing to 0 |
| RF-S4 | RF-15 | Use a 20th-percentile fleet `cd0` reference with a `0.020` fallback | Must | One freak low-`cd0` airfoil does not move the reference; an empty fleet returns `0.020` |
| RF-S5 | RF-15 | Reject non-positive `V` or `S` in the level-flight CL helper | Must | `V = 0` or `S = 0` raises `ValueError`, not a division by zero |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Interpolation is linear in `ln(Re)` to match NeuralFoil's training encoding | `app/services/airfoil_low_re_service.py:304-311` | 🟢 |
| Correctness | Out-of-range Re is clamped **and reported**, never silently extrapolated | `app/services/suitability_service.py:124-133` | 🟢 |
| Correctness | The fleet `cd0` reference is a 20th percentile, robust against a single outlier airfoil | `airfoil_low_re_service.py:771-823` | 🟢 |
| Correctness | A missing scoring component is dropped from both numerator and denominator, never treated as zero | `airfoil_low_re_service.py:831-891` | 🟢 |
| Robustness | Trust is ranked above score, so a confident mediocre section beats an unreliable excellent one | `suitability_service.py:629, 632` | 🟢 |
| Robustness | The known modelling limitation (tip-Re CL_max collapse) is declared in every response rather than hidden | `app/schemas/airfoil.py:6-17, 174-187` | 🟢 |
| Robustness | A glide contingency point is structurally prevented from driving the default sort | `app/schemas/airfoil.py:71-84` | 🟢 |
| Robustness | `best_ld_cl` returns `None` for degenerate fits (`cd0 ≤ 0`, `k ≤ 0`) rather than raising or defaulting | `airfoil_low_re_service.py:715-760` | 🟢 |
| Determinism | Role tags are returned sorted | `app/services/airfoil_tags.py` | 🟢 |
| Performance | Tags and scores are computed per request with no persistence, migration or backfill | `app/services/airfoil_tags.py` (gh-835) | 🟢 |
| Configurability | Every scoring knob is a `pydantic-settings` field with an `.env` override | `app/settings.py:19-56, 109-114` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Query Reynolds number

  Scenario: Re is derived at sea level
    Given a chord of 0.2 m and a speed of 15 m/s
    When the query Reynolds number is computed
    Then it equals 1.225 * 15 * 0.2 / 1.81e-5

  Scenario: A non-positive speed is rejected by the level-flight helper
    Given a speed of 0 m/s
    When the level-flight CL is computed
    Then a ValueError is raised
    And no division by zero occurs

Feature: Interpolation and clamping

  Scenario: Interpolation is logarithmic in Re
    Given polar rows at Re 100000 and Re 200000
    When I interpolate at Re equal to their geometric mean
    Then the result is the arithmetic mean of the two metric values

  Scenario: A low out-of-range Re is clamped and reported
    Given a query Re of 10000
    When the suitability query is built
    Then the effective Re is 40000
    And re_clamped is true

  Scenario: A high out-of-range Re is clamped and reported
    Given a query Re of 1000000
    When the suitability query is built
    Then the effective Re is 750000
    And re_clamped is true

Feature: Lens 1 - re_agnostic

  Scenario: All five components contribute
    Given an airfoil with ld_max, cl_max, drag_bucket_width, stall_gentleness and cd_min
    When the re_agnostic score is computed
    Then it equals the weighted sum divided by 1.0
    And it lies in the range 0 to 1

  Scenario: A missing component is renormalised away
    Given an airfoil whose cl_max is null
    When the re_agnostic score is computed
    Then the denominator is 0.75, not 1.0
    And the missing component is not treated as zero

  Scenario: An airfoil with no usable metric scores null
    Given an airfoil whose polar metrics are all null
    When the re_agnostic score is computed
    Then the score is null, not zero

  Scenario: Abrupt stall zeroes its component
    Given an airfoil whose stall_gentleness is -0.15
    When the stall component is normalised
    Then it is 0.0

Feature: Lens 2 - mission

  Scenario: A trainer section inside the thickness band scores unpenalised
    Given a flat_bottom airfoil of 12 percent thickness and a trainer mission
    When the mission score is computed
    Then family_bonus is 1.0
    And thickness_match is 1.0

  Scenario: A non-preferred family is penalised
    Given a symmetric airfoil and a trainer mission
    When the mission score is computed
    Then family_bonus is 0.7

  Scenario: Thickness outside the band decays linearly
    Given an aerobatic mission with a band of 8 to 12 percent
    And an airfoil of 14 percent thickness
    When thickness_match is computed
    Then it equals max(0, 1 - 2.0/5.0)

Feature: Lens 3 - target_cl_cruise

  Scenario: A target at or below the drag bucket matches fully
    Given a target CL whose relative drag rise r is 0.9
    When the Match term is computed
    Then it is 1.0

  Scenario: A poor drag rise collapses the match
    Given a target CL whose relative drag rise r is 2.5
    And an airfoil with no cl_max recorded
    When the Match term is computed
    Then it is 0.0

  Scenario: A glider min-sink CL is rescued by the CL_max fallback
    Given a target CL whose relative drag rise r exceeds 2.5
    And an airfoil with cl_max 1.5 against a target CL of 1.3
    When the Match term is computed
    Then it equals clamp((1.5 - 1.3) / 0.30, 0, 1)
    And it is greater than zero

  Scenario: A degenerate fit yields no best-L/D CL
    Given an airfoil whose k is zero
    When best_ld_cl is computed
    Then it returns null
    And no exception is raised

Feature: Fleet reference

  Scenario: A single outlier does not move the reference
    Given a fleet of fifty airfoils and one with an implausibly low cd0
    When the fleet reference is computed at the query Re
    Then it equals the 20th percentile of the finite cd0 values
    And it is not the minimum

  Scenario: An empty fleet falls back
    Given a fleet with no finite cd0 values
    When the fleet reference is computed
    Then it is 0.020

Feature: Ranking and caveats

  Scenario: A fleet is ranked through the mission lens
    Given a fleet of airfoils with polars and a mission of "trainer"
    When I GET /airfoils/db/suitability with active_lens "mission"
    Then the response status is 200
    And each result carries re_agnostic and mission scores in the range 0 to 1
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

  Scenario: Glide points are still reported
    Given a request with a target_cl_min_sink value and active_lens "mission"
    When the results are built
    Then each item carries a target_cl_min_sink score
    And the ordering is driven by the mission score

  Scenario: A tip-Re risk is flagged by the absolute floor
    Given a wing whose tip Reynolds number is 70000
    When the suitability query is built
    Then tip_re_flag is true

  Scenario: A tip-Re risk is flagged by the relative drop
    Given a root Reynolds number of 200000 and a tip of 140000
    When the suitability query is built
    Then tip_re_flag is true

  Scenario: A negative CL_max margin signals stall risk
    Given a target CL of 1.4 and an airfoil cl_max of 1.2
    When the result is built
    Then cl_max_margin is -0.2
    And the value is reported, not clamped

Feature: Role tags

  Scenario: A thin symmetric section earns the acro and stabiliser tags
    Given a symmetric airfoil with 9 percent thickness and 0.1 percent camber
    When tags are computed
    Then the tags include "acro", "v_stabilizer" and "h_stabilizer"
    And the tags are sorted

  Scenario: A thick symmetric section is not acro
    Given a symmetric airfoil with 14 percent thickness and 0.1 percent camber
    When tags are computed
    Then "v_stabilizer" is present
    And "acro" is absent

  Scenario: A low-confidence polar does not earn the low_re tag
    Given an airfoil whose only polar at Re 100000 has confidence 0.5
    When tags are computed
    Then "low_re" is absent

  Scenario: The high-Re tag is marked approximate
    Given an airfoil with a confident polar at Re 500000
    When tags are computed
    Then "high_re" is present
    And the contract records that the grid tops out at 750000

Feature: Route resolution

  Scenario: The suitability route is not captured as an airfoil name
    When I GET /airfoils/db/suitability
    Then the response is a SuitabilityResponse
    And it is not a 404 for an airfoil named "suitability"
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| `ln(Re)` interpolation and clamping (RF-12/RF-13) | Must | Linear-in-Re interpolation is wrong against NeuralFoil's encoding; silent extrapolation would fabricate data outside the trained range |
| Query Re from chord and speed (RF-14) | Must | Every lookup is keyed on it; a wrong Re silently selects the wrong polar |
| Suitability ranking through the three lenses (RF-15/RF-S1…RF-S3) | Must | The module's headline capability |
| Glide-point exclusion (RF-16) | Must | Prevents an engine-out or min-sink contingency point from driving the default sort |
| Confidence-first ordering (RF-17) | Must | A trustworthy result must never be displaced by an unreliable one |
| The always-on caveat block (RF-18) | Must | A declared modelling limitation, per ADR 0012 — warnings, not silent fallbacks |
| Weight renormalisation in Lens 1 (RF-S1) | Must | Treating a missing metric as zero would systematically punish sparsely analysed airfoils |
| The CL_max safety fallback in Lens 3 (RF-S3) | Must | Without it every glider section scores 0 at its min-sink CL |
| The 20th-percentile fleet reference (RF-S4) | Must | A minimum would let one freak airfoil deflate the whole fleet's Efficiency |
| `ValueError` on non-positive `V` or `S` (RF-S5) | Must | Guards a division by zero in a user-supplied path |
| Tip-Re flag (RF-19) | Should | A refinement of the caveat; the caveat itself already covers the limitation |
| Role tags (RF-20) | Should | Query-time UX filtering (gh-835); the ranking works without them |
| `known` lookup (RF-25) | Could | A diagnostic convenience |
| Persisting role tags | Won't | Deliberately query-time: no column, no migration, no backfill (gh-835) |
| Modelling the tip-Re CL_max collapse | Won't | Declared as out of scope in the caveat; the flag is the substitute |
| Absolute performance prediction | Won't | `relative_ranking_only = True` — the scores rank, they do not predict |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/suitability_service.py` (709 l.) | query Re (l.74-75, 119-121), `_clamp_re_to_grid` (l.124-133), ranking (l.629, 632) | 🟢 |
| `app/services/airfoil_low_re_service.py` (1086 l.) | `interpolate_polar_at_re` (l.304-311), `_level_flight_cl` (l.686-707), `best_ld_cl` (l.715-760), `compute_re_cd0_reference` (l.771-823), `score_re_agnostic` (l.831-891), `score_mission` (l.894-940), `score_target_cl` (l.943-1009, fallback rationale l.977-997), `G`/`RHO` (l.39-40) | 🟢 |
| `app/services/airfoil_tags.py` | the six tag rules, `LOW_RE_UPPER_BOUND`, `HIGH_RE_LOWER_BOUND`, `LOW_RE_CONFIDENCE_GATE`, tag literal set (l.62-64) | 🟢 |
| `app/schemas/airfoil.py` | `AirfoilFamily` (l.69), `ActiveLens` (l.84), `TargetClProvenance` (l.93), `SuitabilityItem` (l.96), `SuitabilityQuery` (l.141), `SuitabilityCaveat` (l.174), `SuitabilityResponse` (l.190), tip-stall note (l.6-17, 174-187) | 🟢 |
| `app/settings.py` | mission bands (l.19-56), `low_re_score_r_poor`, `low_re_bucket_tolerance_ref`, `low_re_score_cl_max_safety_band`, tip-Re thresholds (l.109-114) | 🟢 |
| `app/api/v2/endpoints/airfoils.py` (1086 l.) | `GET /airfoils/db/suitability`, `GET /airfoils/{name}/known` | 🟢 |
| `app/models/airfoil_low_re.py` | read-only consumer of `AirfoilGeometryModel` (l.33) and `AirfoilLowRePolarModel` (l.65); the two-Re note (l.8-14) | 🟢 |
| `app/services/polar_re_table_service.py` | — | n/a — a **different** Re concept (gh-493), owned elsewhere |
