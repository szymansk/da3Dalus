# suitability-search — Implementation Tasks

> Executable sequence to re-implement this slice from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Module-level task list: [`../tasks.md`](../tasks.md); the module ids
> **T-20…T-34** (interpolation, scoring, ranking, tags) and **T-36** are refined
> here.

## Prerequisites

- [ ] [`low-re-polar-backfill`](../low-re-polar-backfill/tasks.md) complete —
      this slice reads `airfoils`, `airfoil_geometry` and the 13
      `airfoil_low_re_polar` rows per airfoil, and writes nothing.
- [ ] `get_db()` request-scoped session (`app/db/session.py:55-64`, ADR 0009).
      This slice is read-only within it.
- [ ] `app/core/exceptions.py` hierarchy plus the shared error envelope —
      `ValidationError` → 422 for a rejected `active_lens`.
- [ ] `app/settings.py` carrying the mission bands (l.19-56),
      `low_re_score_r_poor`, `low_re_bucket_tolerance_ref`,
      `low_re_score_cl_max_safety_band`, `low_re_low_confidence_flag`, and the
      tip-Re thresholds (l.109-114). 🟢 Decided (`Q-CC-4`): they move into the one merged `Settings` class, together
      or in `app/core/config.py`.
- [ ] NumPy for percentile and interpolation arithmetic.
- [ ] **AeroSandbox is NOT required.** This slice reads persisted polars only, so
      it must work unchanged on a platform without a solver. 🟡

## Tasks

### Interpolation and query Re

- [ ] **T-20 — `interpolate_polar_at_re` linear in `ln(Re)`.**
  `(polar_rows, re_query, re_grid)` → interpolated metrics, interpolating
  linearly in `ln(Re)` to match NeuralFoil's training encoding.
  - Legacy origin: `app/services/airfoil_low_re_service.py:304-311`
  - Definition of done: querying at the **geometric** mean of two grid points
    returns the arithmetic mean of the metric; a linear-in-Re implementation
    fails the test.
  - Confidence: 🟢

- [ ] **T-21 — `_clamp_re_to_grid`.**
  Clamp an out-of-range query to the nearest endpoint of the 13-point grid and
  set `re_clamped = True`. Never extrapolate.
  - Legacy origin: `app/services/suitability_service.py:124-133`
  - Definition of done: `Re = 10 000` → effective `40 000`, flag set;
    `Re = 1 000 000` → `750 000`, flag set; an in-range Re leaves the flag
    `false`.
  - Confidence: 🟢

- [ ] **T-22 — Query Re at sea level.**
  `Re = ρ·V·c / μ` with `ρ = 1.225 kg/m³` and `μ = 1.81e-5 Pa·s`. Shared
  constants `G = 9.80665`, `RHO = 1.225`. Record in a comment that this is an
  **absolute** Reynolds number from the 2D per-airfoil grid (gh-821), **not** the
  aircraft-level speed-band proxy of `polar_re_table_service` (gh-493).
  - Legacy origin: `suitability_service.py:74-75, 119-121`;
    `airfoil_low_re_service.py:39-40`; `app/models/airfoil_low_re.py:8-14`
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
  - Definition of done: an airfoil missing `cl_max` scores with a denominator of
    `0.75`, not `1.0`; an airfoil missing everything scores `None`, not `0`;
    `stall_gentleness = −0.15` normalises to exactly `0.0`.
  - Confidence: 🟢

- [ ] **T-24 — Lens 2, `score_mission`.**
  `re_agnostic × family_bonus × thickness_match × cl_bonus` with
  `family_bonus = 1.0 | 0.7`,
  `thickness_match = 1.0` inside `[t_min, t_max]` else `max(0, 1 − gap/5.0)`,
  `cl_bonus = (1 − cl_max_weight) + cl_max_weight · min(cl_max/1.5, 1)`.
  - Legacy origin: `airfoil_low_re_service.py:894-940`
  - Definition of done: each of the six mission bands is table-tested inside and
    outside the thickness window, with a preferred and a non-preferred family;
    a `None` Lens 1 propagates to a `None` Lens 2.
  - Confidence: 🟢 (the null propagation is 🟡 — confirm against the source)

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
    the fallback; an airfoil at `r ≥ r_poor` with no `cl_max` scores `0.0`.
  - Confidence: 🟢

- [ ] **T-28 — `compute_re_cd0_reference` (20th percentile).**
  Interpolate every airfoil to `re_query`, take the **20th percentile** of the
  finite `cd0` values; fall back to `_CD0_REFERENCE_FALLBACK = 0.020` on an empty
  fleet.
  - Legacy origin: `airfoil_low_re_service.py:771-823`
  - Definition of done: a single freak low-`cd0` airfoil does not move the
    reference; an empty fleet returns `0.020`; the result is a percentile, not a
    minimum.
  - Confidence: 🟢

- [ ] **T-29 — `_level_flight_cl`.**
  `CL = (m·g) / (0.5·ρ·V²·S)`; raise `ValueError` for non-positive `V` or `S`.
  - Legacy origin: `airfoil_low_re_service.py:686-707`
  - Definition of done: `V = 0` and `S = 0` both raise rather than dividing by
    zero; a known `(m, V, S)` triple reproduces the reference CL.
  - Confidence: 🟢

### Ranking, caveats and tags

- [ ] **T-30 — `ActiveLens` admits only three values.**
  `re_agnostic | mission | target_cl_cruise`. `target_cl_best_glide` and
  `target_cl_min_sink` are computed and displayed but can never rank.
  - Legacy origin: `app/schemas/airfoil.py:71-84`
  - Definition of done: a request with `active_lens = "target_cl_min_sink"` is
    rejected at validation time (→ 422); the same request with
    `active_lens = "mission"` still returns a `target_cl_min_sink` score per
    item.
  - Confidence: 🟢

- [ ] **T-31 — Confidence-first ordering.**
  Sort by `(confidence tier, −score)` with the tier as the **primary** key.
  - Legacy origin: `suitability_service.py:629, 632`
  - Definition of done: a 0.95-score low-confidence airfoil ranks below a
    0.80-score high-confidence one.
  - Confidence: 🟢 (the tier **boundaries** are 🟡 — see the gaps)

- [ ] **T-32 — The always-on caveat block.**
  `SuitabilityCaveat` with `relative_ranking_only = True`,
  `no_hysteresis_modelling = True`, **`ignores_tip_re_clmax_collapse = True`
  unconditionally**, `recommend_xfoil_validation`, and a human-readable `text`.
  - Legacy origin: `app/schemas/airfoil.py:6-17, 174-187`; ADR 0012
  - Definition of done: every response carries the block, and
    `ignores_tip_re_clmax_collapse` is `true` in all of them regardless of the
    query.
  - Confidence: 🟢

- [ ] **T-33 — `tip_re_flag` and `cl_max_margin`.**
  Flag when `Re_tip < low_re_tip_re_abs_floor = 80 000` **or** the root→tip Re
  drop exceeds `low_re_tip_re_rel_drop = 50 000`.
  `cl_max_margin = cl_max − max(target CLs)`; **negative means stall risk** and
  is reported, not clamped.
  - Legacy origin: `app/settings.py:109-114`; `app/schemas/airfoil.py:174-187`
  - Definition of done: `Re_tip = 70 000` flags; a root 200 k → tip 140 k drop
    flags independently; `cl_max 1.2` against target `1.4` yields `−0.2`.
  - Confidence: 🟢

- [ ] **T-34 — Query-time role tags (gh-835).**
  No column, no migration, no backfill. `LOW_RE_UPPER_BOUND = 150 000`,
  `HIGH_RE_LOWER_BOUND = 500 000`, `LOW_RE_CONFIDENCE_GATE = 0.85`. Rules per
  [`../contracts.md`](../contracts.md) §Role-tag contract. Return the tags
  **sorted**.
  - Legacy origin: `app/services/airfoil_tags.py:62-64`
  - Definition of done: a 9 % symmetric section with 0.1 % camber carries
    `acro`, `h_stabilizer`, `v_stabilizer` in sorted order; a 14 % symmetric
    section carries the stabiliser tags but not `acro`; each of the six rules has
    a boundary test.
  - Confidence: 🟢

- [ ] **T-35 — Assemble `SuitabilityResponse`.**
  `{ query: SuitabilityQuery, caveat: SuitabilityCaveat,
  results: list[SuitabilityItem] }`, with `query.reynolds` holding the
  **effective** post-clamp value and `query.re_clamped` set accordingly.
  - Legacy origin: `app/schemas/airfoil.py:96, 141, 174, 190`
  - Definition of done: the echoed `reynolds` is post-clamp, never the raw
    request value.
  - Confidence: 🟢

### REST layer

- [ ] **T-36 — Declare `/airfoils/db/suitability` before `/airfoils/db/{name}`.**
  Otherwise `"suitability"` is captured as an airfoil name.
  - Legacy origin: route shapes in `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a test hits `/airfoils/db/suitability` and asserts it
    returns a `SuitabilityResponse`, not a 404 for an airfoil named
    `"suitability"`.
  - Confidence: 🟡 INFERRED from the path shapes; the declaration order in the
    legacy file was not read.

- [ ] **T-37 — `GET /airfoils/{airfoil_name}/known`.**
  A boolean lookup against the catalogue.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a known stem returns `true`, an unknown one `false` —
    with 200 in both cases, not a 404.
  - Confidence: 🟢 (the 200-for-unknown behaviour is 🟡 — the handler body was
    not read)

## Test Tasks

- [ ] **TT-01 — Happy path:** a fleet with polars ranked through the mission lens
      returns 200 with `query`, `caveat` and a non-empty ordered `results`.
- [ ] **TT-02 — Failure:** `active_lens = "target_cl_min_sink"` → 422.
- [ ] **TT-03 — `ln(Re)` interpolation:** the geometric-mean query returns the
      arithmetic mean; a linear-in-Re implementation fails.
- [ ] **TT-04 — Re clamping:** both ends clamp, set `re_clamped`, and the echoed
      `query.reynolds` is the post-clamp value.
- [ ] **TT-05 — Query Re:** a known `(c, V)` reproduces `ρ·V·c/μ`.
- [ ] **TT-06 — Lens 1 renormalisation:** a missing component reduces the
      denominator; all missing → `None`, not `0`.
- [ ] **TT-07 — Lens 1 stall clamp:** `stall_gentleness = −0.15` → `0.0`;
      `−0.30` → `0.0`, not negative.
- [ ] **TT-08 — Lens 2 mission table:** all six bands, inside and outside the
      thickness window, preferred and non-preferred families.
- [ ] **TT-09 — Lens 2 null propagation:** a `None` Lens 1 yields a `None`
      Lens 2.
- [ ] **TT-10 — Lens 3 branches:** `r ≤ 1`, within tolerance, `r ≥ r_poor` with
      and without `cl_max`.
- [ ] **TT-11 — CL_max fallback:** a glider min-sink CL scores non-zero via
      `clamp((cl_max − cl_target)/0.30, 0, 1)`.
- [ ] **TT-12 — `best_ld_cl` degenerates safely:** `cd0 ≤ 0` and `k ≤ 0` return
      `None`; the closed form matches a numeric argmax on a synthetic polar.
- [ ] **TT-13 — Fleet reference is robust:** one freak airfoil does not move the
      20th percentile; an empty fleet returns `0.020`.
- [ ] **TT-14 — `_level_flight_cl` guards:** `V = 0` and `S = 0` raise
      `ValueError`.
- [ ] **TT-15 — Confidence outranks score.**
- [ ] **TT-16 — Glide points are reported but never rank:** with
      `active_lens = "mission"`, each item still carries
      `target_cl_best_glide` and `target_cl_min_sink`.
- [ ] **TT-17 — Caveat always present** with
      `ignores_tip_re_clmax_collapse = true`, for every lens and every query.
- [ ] **TT-18 — Tip-Re flag:** the absolute floor and the relative drop, each
      independently sufficient.
- [ ] **TT-19 — `cl_max_margin` sign:** a negative margin is reported, not
      clamped to zero.
- [ ] **TT-20 — Role tags:** each of the six rules at its boundary; a
      low-confidence polar does not earn `low_re`; tags come back sorted.
- [ ] **TT-21 — `h_stabilizer` and `v_stabilizer` share a gate** — both present
      or both absent.
- [ ] **TT-22 — Route order:** `/airfoils/db/suitability` is not swallowed by
      `/airfoils/db/{name}`.
- [ ] **TT-23 — No writes:** a suitability query leaves every table byte
      identical (assert with a row-count and checksum guard).
- [ ] **TT-24 — Solver-free operation:** the whole slice runs with AeroSandbox
      uninstalled, on the CI **fast** tier.

## Data Migration Tasks

None. This slice writes nothing and owns no schema — all migrations belong to
[`low-re-polar-backfill`](../low-re-polar-backfill/tasks.md). 🟢

## Suggested Order

1. **T-20 → T-22** first — interpolation and the query Re. Everything downstream
   reads an interpolated polar, so nothing else can be tested meaningfully
   without them. They depend only on hand-built polar rows, not on a solver, so
   they belong on the CI **fast** tier. T-20 blocks T-28.
2. **T-26 → T-23** next in that order — `best_ld_cl` (T-26) is a standalone
   closed form and is the cheapest thing to pin, and Lens 1 (T-23) is the base
   every other lens builds on. T-23 blocks T-24.
3. **T-24 → T-25** — Lens 2 multiplies Lens 1, so it cannot be validated before
   T-23. T-25 is pure configuration and can land alongside.
4. **T-28 → T-27** — Lens 3's Efficiency term needs the fleet reference, so T-28
   must precede T-27. T-27 also depends on T-26 for `cl_star`.
5. **T-29** any time — an independent helper with no dependants inside this
   slice.
6. **T-30 → T-35** — ranking and assembly. T-31 needs a confidence value to
   exist, i.e. `min_analysis_confidence` from the backfill slice. T-34 needs both
   geometry and polars. T-35 needs T-21 for the echoed effective Re.
7. **T-36 → T-37** last — the REST layer is thin. T-36 is a route-declaration
   ordering constraint that must be **tested**, not assumed.

## Pending Gaps (🔴)

- **Two settings modules with overlapping responsibility.** `app/settings.py`
  holds every scoring knob this slice reads while the project convention names
  `app/core/config.py` as the single configuration home. Which is canonical?
- **The confidence *tier* boundaries were not read.** Ranking sorts on a tier
  derived from `min_analysis_confidence`, and `low_re_low_confidence_flag = 0.85`
  is the documented UI badge threshold — but whether the ranking tier uses that
  same value, and how many tiers exist, is unconfirmed. A re-implementation
  cannot reproduce the ordering exactly without it.
- **The `/airfoils/db/suitability` vs `/airfoils/db/{name}` declaration order is
  unverified.** If the parameterised route is declared first the suitability
  route is unreachable; the ordering must be pinned by a test.
- **The treatment of an airfoil with no polar rows is unknown.** Is it omitted
  from `results`, or returned with `null` scores?
- **Null propagation through Lens 2 is inferred.** Lens 2 multiplies Lens 1, so a
  `None` should propagate — confirm against the source before relying on it.
- **`_level_flight_cl`'s call sites were not read**, so which `target_cl_*`
  values are derived from it versus supplied directly by the caller is unclear.
- **`high_re` asserts more than the data supports.** The grid tops out at 750 k,
  so the tag is knowingly approximate but exposed as a plain boolean with no
  degraded-confidence signal of its own.
- **`G` and `RHO` are duplicated** between `airfoil_low_re_service` and
  `endurance_service`, kept in sync by comment rather than a shared import.
