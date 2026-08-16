# flight-envelope

> Use-case specification, nested under the module
> [`mission-and-sizing`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mission-and-sizing
> (Flight envelope — V-n and gust), `_reversa_sdd/data-dictionary.md`
> §`flight_envelopes`, `_reversa_sdd/domain.md` §2.5, ADR 0012.

## Overview

`flight-envelope` answers **what the aircraft must survive**: the manoeuvre V-n
boundary the pilot can command, the Pratt-Walker discrete-gust boundary the
atmosphere can impose, six headline performance numbers each labelled with how
confident it is, and the operating points plotted as markers on the diagram. It
persists one row per aeroplane with a snapshot of the three assumptions it was
computed from. 🟢

Its two hardest requirements are aerodynamic honesty, not arithmetic: the gust
model must use the **mean geometric** chord and a **finite-span** `CL_α` (the
textbook shortcuts overestimate gust loads by tens of percent at RC aspect
ratios), and the Pratt-Walker formula is routinely **outside its validity range**
for RC models — which the user must be told rather than shielded from. 🟢

## Responsibilities

- Compute the manoeuvre V-n boundary over 60 points from `V_stall` to
  `V_dive`. 🟢
- Compute the Pratt-Walker gust boundary over the same 60 points, or omit it
  entirely when its inputs are missing. 🟢
- Emit structured gust warnings — critical (gust-sized structure) and validity
  (`μ_g` outside `[3, 200]`) — to the **API**, not only to the log. 🟢
- Derive exactly six performance KPIs with an explicit confidence tier. 🟢
- Plot the aircraft's operating points as markers. 🟢
- Upsert one `flight_envelopes` row per aeroplane with an assumptions
  snapshot. 🟢
- Serve the cached row, distinguishing "not computed yet" from "no such
  aeroplane". 🟢

**Explicitly NOT this use case's responsibility:** producing the operating
points it plots (→ [`../operating-point-sweep/`](../operating-point-sweep/requirements.md)),
the polar and the V-speeds it reads (→ `aero-analysis`), the CG envelope
(→ [`../design.md`](../design.md) §Loading, CG and field length), and the
matching chart.

## Business Rules

> Global ids (`BR-*`) are inherited verbatim from
> [`../../domain.md`](../../domain.md); `BR-MS*` from
> [`../requirements.md`](../requirements.md). `BR-MS43`…`BR-MS45` are new,
> discovered while writing this specification.

- **BR-MS15 — The V-n manoeuvre envelope, 60 points.** 🟢

  ```
  W        = mass_kg · 9.81
  V_stall  = sqrt(2·W / (ρ·S·CL_max))          ρ = 1.225 (fixed, sea level)
  V_dive   = 1.4 · V_max
  CL_min   = −0.8 · CL_max
  for 60 evenly spaced V from V_stall to V_dive:
      q      = ½·ρ·V²
      n⁺(V)  = min(q·S·CL_max / W,  g_limit)
      n⁻(V)  = max(q·S·CL_min / W, −0.4·g_limit)
  every emitted value is round(x, 6)
  ```

  The parabolic branch and the structural cap are produced by one `min` / `max`
  rather than by a piecewise construction, so the corner point is implicit. 🟡
  `mass_kg`, `cl_max`, `wing_area_m2` or `v_max_mps` ≤ 0 raises a `ValueError`
  before any point is computed. 🟢

- **BR-MS16 — Pratt-Walker gust with the *mean geometric* chord.** 🟢
  (NACA TN 2964; `K_g` per FAR-25.341(a)(2) / CS-VLA.333)

  ```
  c̄    = S_ref / b_ref                # MEAN GEOMETRIC chord, NOT the MAC
  μ_g  = 2·(W/S) / (ρ · c̄ · CL_α · g)
  K_g  = 0.88·μ_g / (5.3 + μ_g)
  Δn   = ½·ρ·V·CL_α·U_gust·K_g / (W/S)
  n±   = 1 ± Δn                        over the same 60 points

  V_C  = V_D / 1.4                     # by construction V_C == V_max
  U_gust = 15.24 m/s (50 ft/s)          for V ≤ V_C          (conservative)
         = linear taper to 7.62 m/s (25 ft/s) at V_D
  CL_α  : context["cl_alpha_per_rad"] when finite and > 0
          else Helmbold-Diederich 2π·AR/(AR+2) with AR = b_ref²/S_ref
  ```

  Explicitly **not** the thin-airfoil `2π` limit, which overestimates `CL_α` at
  AR = 6 by ≈ 39 % and inflates gust loads (Anderson 6e §5.3).

- **BR-MS43 — The gust envelope is absent, not zeroed, when it cannot be
  computed.** 🟢 Gust lines require **both** a `CL_α` and a `b_ref`. Without
  `b_ref` the Helmbold fallback cannot even derive an aspect ratio, so
  `gust_lines_positive` / `gust_lines_negative` stay **empty lists** and no gust
  warning is emitted. A consumer must treat "empty" as "unknown", never as
  "no gust load". `b_ref` comes from the ASB airplane and degrades to `None` on
  **any** exception in the conversion. 🟡

- **BR-MS17 — Two structured gust warnings reach the API, not just the log.** 🟢

  | Warning | Condition | Cardinality |
  |---|---|---|
  | `GustCriticalWarning` | the **first** `V` where `1+Δn > g_limit` | at most **one** positive |
  | `GustCriticalWarning` | the **first** `V` where `1−Δn < −0.4·g_limit` | at most **one** negative |
  | `GustValidityWarning` | `μ_g < 3` (optimistic) or `μ_g > 200` (conservative) | at most **one**, emitted before the sweep |

  `μ_g < 3` is the **normal** case for low-W/S RC models (gh-497), which is
  exactly why the warning is a structured API object and not a log line — a
  server-side log was invisible to the user it concerns.
  🟡 On the negative warning the `g_limit` field carries `−0.4·g_limit`, not
  `g_limit`; the field name misdescribes its content.
  🟡 `_compute_k_g` **also** logs the out-of-range condition, so the same event
  is reported twice through two channels.

- **BR-MS18 — Six KPIs with an explicit confidence ladder.** 🟢

  ```
  best_ld_speed:
    1. a marker labelled "best_ld"            → confidence "trimmed"
    2. ctx["v_md_mps"] when > 0               → confidence "computed"
    3. 1.4 · V_stall                          → confidence "estimated"
  min_sink_speed:
    1. a marker labelled "min_sink"           → "trimmed"
    2. ctx["v_min_sink_mps"] when > 0         → "computed"
    3. 1.2 · V_stall                          → "estimated"
  max_load_factor:
    1. a marker labelled "max_turn"           → "trimmed" (its load_factor)
    2. g_limit                                → "limit"
  stall_speed = V_stall · max_speed = V_max · dive_speed = 1.4·V_max  → "limit"
  ```

  Exactly six, always, in that order, each rounded to 4 decimals. The heuristic
  tier is documented as wrong by up to 15 % for high-AR airframes (gh-475 audit
  §4.1) and exists **only** for the pre-polar case — which is why the confidence
  label is part of the contract (ADR 0012).

- **BR-MS45 — 🟢 An explicit `role` field replaces name matching, and the `trimmed` tier is gated on `status == TRIMMED` plus polar proximity (`Q-MS-7`).** Previously unreachable through the standard flow.
  `_load_operating_point_markers` sets `label = op.name`, and the KPI lookup is
  `markers_by_label.get("best_ld")` / `"min_sink"` / `"max_turn"`. The generator
  ([`../operating-point-sweep/`](../operating-point-sweep/requirements.md))
  produces `max_range`, `loiter_endurance`, `turn_60`, … — never those three
  names. Consequences:
  1. `best_ld_speed` and `min_sink_speed` can only ever reach the `computed`
     tier, and `max_load_factor` only the `limit` tier;
  2. if a user *did* name a point `best_ld`, the marker is accepted with
     confidence `"trimmed"` **without checking its status** — a `NOT_TRIMMED`
     row would be labelled trimmed;
  3. `max_load_factor` from a `max_turn` marker would read `1.0`, because of
     BR-MS19.

- **BR-MS19 — 🟢 Fixed by `Q-MS-6`: persist `n_target` and `cl_trimmed`, place the marker at the real load factor.** Previously every operating
  point with `velocity > 0` becomes a marker, regardless of status, with the
  load factor hard-coded to `1.0` and an in-code note that *"without stored CL
  we cannot derive actual load factor"*. Turn operating points therefore plot on
  the 1-g line — exactly where they are not.

- **BR-MS44 — The snapshot is exactly three numbers.** 🟢
  `assumptions_snapshot = {mass, cl_max, g_limit}`, read through
  `mass_cg_service.get_effective_assumption_value` with a
  `NotFoundError → PARAMETER_DEFAULTS[param]` fallback. Those three are also the
  only assumptions the whole computation consumes.
  🟡 The V-n envelope does not react to `target_static_margin`,
  `cd0`, `e_oswald` or the polars, while the KPI tier does read `v_md_mps` and
  `v_min_sink_mps` from the context — so the row can be stale with respect to
  the context that produced half of it, and the snapshot does not record which
  context version was used.

- **BR-MS-open — `V_max` is resolved differently here than in the sweep.** 🟡
  `_get_v_max` reads `aeroplane.flight_profile.goals["max_level_speed_mps"]` and
  otherwise returns a bare **28.0 m/s**. The operating-point generator uses
  `max(1.35·V_cruise, V_cruise + 8)` for the same quantity (BR-MS8). Two
  fallbacks for one number, and `V_dive`, `max_speed` and `dive_speed` all
  depend on it.

- **BR-14 — The envelope reads the single-source context.** 🟢
  `cl_alpha_per_rad`, `v_md_mps`, `v_min_sink_mps` — nothing here re-derives a
  polar. `_extract_cl_alpha_from_context` guards against a corrupted cache by
  rejecting non-numeric, non-finite and non-positive values.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Compute the manoeuvre envelope over exactly 60 points | Must | Both arrays have 60 entries from `V_stall` to `V_dive` |
| RF-02 | Cap `n⁺` at `g_limit` and floor `n⁻` at `−0.4·g_limit` | Must | `g_limit = 3.0` ⇒ no value above 3.0 or below −1.2 |
| RF-03 | Use `CL_min = −0.8·CL_max` | Must | The negative branch scales with it |
| RF-04 | Reject non-positive mass, `CL_max`, area or `V_max` | Must | `ValueError` before any point is computed |
| RF-05 | Compute the gust envelope with the **mean geometric** chord | Must | `S_ref = 0.30`, `b_ref = 2.0` ⇒ the chord used is `0.15` |
| RF-06 | Prefer the context `CL_α`, else Helmbold-Diederich | Must | The thin-airfoil `2π` is never used |
| RF-07 | Reject a non-finite or non-positive cached `CL_α` | Must | A corrupted cache falls through to Helmbold |
| RF-08 | Hold `U_gust` at 15.24 m/s up to `V_C` and taper linearly to 7.62 at `V_D` | Must | `V_C = V_D/1.4` |
| RF-09 | Omit the gust lines entirely when `CL_α` or `b_ref` is unavailable | Must | Empty lists, no warnings, no zeros |
| RF-10 | Emit at most one positive and one negative `GustCriticalWarning`, at the first crossing | Must | Naming the velocity and the gust load factor |
| RF-11 | Emit a `GustValidityWarning` when `μ_g ∉ [3, 200]` | Must | With the value, both bounds and a direction-specific message |
| RF-12 | Surface the warnings at the top level of the response as well | Should | `FlightEnvelopeRead.gust_warnings` mirrors `vn_curve.gust_warnings` |
| RF-13 | Return exactly six KPIs, in order, each with a confidence label | Must | `stall_speed`, `best_ld_speed`, `min_sink_speed`, `max_speed`, `max_load_factor`, `dive_speed` |
| RF-14 | Apply the three-tier ladder for `best_ld_speed` and `min_sink_speed` | Must | Marker ⇒ `trimmed`; context ⇒ `computed`; heuristic ⇒ `estimated` |
| RF-15 | Fall back to `g_limit` for `max_load_factor` | Must | Confidence `limit` |
| RF-16 | Round every KPI to four decimals | Should | |
| RF-17 | Plot every operating point with `velocity > 0` as a marker | Must | Points with a null or non-positive velocity are dropped |
| RF-18 | Upsert one `flight_envelopes` row per aeroplane | Must | A second compute updates rather than inserts |
| RF-19 | Store an assumptions snapshot `{mass, cl_max, g_limit}` | Must | The effective values at compute time |
| RF-20 | Fall back to the catalogue default for a missing assumption | Should | A missing `g_limit` row ⇒ `3.0` |
| RF-21 | Distinguish "no envelope yet" from "no such aeroplane" | Must | Both 404, with different messages |
| RF-22 | Recompute unconditionally on `POST …/compute` | Must | No caching short-circuit |
| RF-23 | Round every emitted V-n value to six decimals | Should | Stable JSON across runs |
| RF-24 | Validate `velocity_mps ≥ 0` on every point | Must | Schema-level |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The gust chord is the **mean geometric** chord, not the MAC — for a double-trapezoid wing the difference is material | `_build_gust_lines`, gh-487 | 🟢 |
| Correctness | `CL_α` uses Helmbold-Diederich rather than the thin-airfoil `2π` (≈ 39 % high at AR 6) | `_helmbold_cl_alpha` docstring | 🟢 |
| Correctness | A corrupted `cl_alpha_per_rad` cache cannot poison the gust load | `_extract_cl_alpha_from_context` | 🟢 |
| Correctness | Non-positive inputs raise before any point is produced | `compute_vn_curve` guard | 🟢 |
| Correctness | The polar-derived `V_md` / `V_min_sink` outrank the 1.4/1.2 heuristics (gh-475, ≈ 15 % error at high AR) | `derive_performance_kpis` | 🟢 |
| Transparency | Every KPI carries a confidence tier so a heuristic cannot be mistaken for a measurement (ADR 0012) | `PerformanceKPI.confidence` | 🟢 |
| Transparency | Gust warnings are structured API objects, deliberately not log-only (gh-497) | `GustCriticalWarning`, `GustValidityWarning` | 🟢 |
| Robustness | A failed ASB conversion degrades `b_ref` to `None` and drops the gust lines rather than failing the request | `_get_b_ref` bare `except` | 🟡 |
| Robustness | A missing assumption row falls back to the catalogue default | `_load_assumptions` | 🟢 |
| Auditability | `assumptions_snapshot` records the three inputs at compute time | table column | 🟢 |
| Determinism | Every emitted number is rounded (6 dp for V-n, 4 dp for KPIs and warnings) | throughout | 🟢 |
| Performance | The whole computation is closed-form except one ASB conversion for `s_ref` / `b_ref` | `_get_wing_area_m2`, `_get_b_ref` | 🟢 |
| Performance | Two independent ASB conversions run per compute (one for `s_ref`, one for `b_ref`) | same | 🟡 |

## Acceptance Criteria

```gherkin
Feature: The manoeuvre envelope

  Scenario: The envelope is capped
    Given g_limit 3.0
    Then no positive load factor exceeds 3.0
    And no negative load factor is below -1.2

  Scenario: Sixty points from stall to dive
    Given v_max 28 m/s
    Then both boundary arrays have 60 points
    And the first velocity is V_stall and the last is 39.2

  Scenario: Non-positive inputs are refused
    Given cl_max of 0
    When the V-n curve is computed
    Then a ValueError is raised
    And no point is produced

Feature: The gust envelope

  Scenario: The gust chord is geometric, not the MAC
    Given S_ref 0.30 and b_ref 2.0
    Then the gust calculation uses a chord of 0.15

  Scenario: Helmbold is used when the context has no CL_alpha
    Given b_ref 2.0 and S_ref 0.5, so AR is 8
    Then CL_alpha is 2*pi*8/10, about 5.03 per radian
    And it is not 2*pi

  Scenario: A corrupted cached CL_alpha is ignored
    Given a context whose cl_alpha_per_rad is "NaN"
    Then the Helmbold value is used instead

  Scenario: The gust envelope is absent without a span
    Given an aeroplane whose ASB conversion yields no b_ref
    Then gust_lines_positive and gust_lines_negative are empty
    And no gust warning is emitted

  Scenario: The gust speed tapers above V_C
    Given v_dive 39.2, so V_C is 28.0
    Then U_gust is 15.24 at 20 m/s
    And 7.62 at 39.2 m/s
    And a linearly interpolated value between them

  Scenario: A gust-sized structure is flagged once
    Given a velocity where 1 plus delta-n exceeds g_limit
    Then exactly one positive GustCriticalWarning names that velocity
    And a later crossing adds no second warning

  Scenario: A low wing loading warns about validity
    Given an RC model whose mu_g is 1.63
    Then a GustValidityWarning is returned to the API
    And it states that the gust loads may be optimistic
    And it carries the value and both validity bounds

  Scenario: A heavy aircraft warns in the other direction
    Given mu_g of 250
    Then the validity warning says the loads may be conservative

Feature: Performance KPIs

  Scenario: Exactly six, always
    Then the KPI list has six entries with the documented labels

  Scenario: The confidence ladder
    Given no context and no matching marker
    Then best_ld_speed is 1.4 times V_stall with confidence "estimated"
    And with v_md_mps in the context it becomes that value with "computed"
    And with a marker labelled best_ld it becomes that marker with "trimmed"

  Scenario: Max load factor falls back to the limit
    Given no marker labelled max_turn
    Then max_load_factor equals g_limit with confidence "limit"

  Scenario: Dive speed is 1.4 times max speed
    Then dive_speed is 1.4 * v_max with confidence "limit"

  Scenario: The trimmed tier is unreachable in practice
    Given a generated operating point set
    Then no marker is labelled best_ld, min_sink or max_turn
    And best_ld_speed can only be "computed" or "estimated"
    # 🟢 an explicit role field replaces the name (Q-MS-7)

Feature: Markers

  Scenario: Every point with a positive velocity is plotted
    Given four operating points, one with a null velocity
    Then three markers are returned

  Scenario: Markers are all at 1 g
    Given a turn_60 operating point
    Then its marker load factor is 1.0
    # 🟢 cl_trimmed and n_target are persisted (Q-MS-6)

Feature: Persistence and retrieval

  Scenario: One row per aeroplane
    When the envelope is computed twice
    Then exactly one flight_envelopes row exists
    And computed_at advanced

  Scenario: The snapshot records the inputs
    Then assumptions_snapshot holds mass, cl_max and g_limit at compute time

  Scenario: A missing assumption falls back to the default
    Given an aeroplane with no g_limit row
    Then the snapshot records 3.0

  Scenario: Not computed yet is distinguishable
    Given an aeroplane with no envelope row
    When I GET the flight envelope
    Then the status is 404
    And the message says no envelope has been computed yet
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The manoeuvre envelope and its caps (RF-01…RF-04) | Must | The structural sizing input a builder reads off the chart |
| The geometric chord and Helmbold `CL_α` (RF-05…RF-07) | Must | Both textbook shortcuts inflate gust loads by tens of percent at RC aspect ratios |
| The `U_gust` schedule (RF-08) | Must | The regulatory basis of the whole gust line |
| Absent-not-zero gust lines (RF-09) | Must | An empty gust envelope means "unknown"; a zeroed one would read as "safe" |
| Structured gust warnings (RF-10…RF-12) | Must | `μ_g < 3` is the **normal** RC case — silence here misleads every RC user |
| Six KPIs with a confidence tier (RF-13…RF-15) | Must | ADR 0012; distinguishes a computed number from a 15 %-wrong heuristic |
| Upsert with a snapshot (RF-18, RF-19) | Must | One row per aeroplane, auditable |
| Distinguishing "not computed" from "not found" (RF-21) | Must | The cold-start UX depends on it |
| Markers (RF-17) | Should | A display overlay on a diagram that is complete without it |
| Assumption default fallback (RF-20) | Should | Degradation |
| Rounding and validation (RF-16, RF-23, RF-24) | Should | Stable payloads |
| Plotting turn OPs at their real load factor | **Must** | 🟢 decided (`Q-MS-6`); markers were hard-coded to 1.0 g |
| Making the `trimmed` KPI tier reachable | **Must** | 🟢 decided (`Q-MS-7`); previously the marker label was the OP name, which never matches |
| Checking a marker's status before claiming `trimmed` | **Must** | 🟢 decided (`Q-MS-7`); previously a `NOT_TRIMMED` row named `best_ld` would be labelled trimmed |
| Unifying the `V_max` fallback with the sweep's | Should | 🟡 28.0 here, `max(1.35·V_c, V_c+8)` there |
| Recording the context version in the snapshot | Should | 🟡 half the row depends on a context the snapshot does not identify |
| Suppressing the duplicate `μ_g` log line | Could (open) | 🟡 the same event is reported twice |
| Deriving a real load factor without a stored CL | Won't (today) | BR-MS19 — the data is not there |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/flight_envelope_service.py` | `GRAVITY` (`:40`), `GUST_U_VC_MPS` / `GUST_U_VD_MPS` (`:43-44`), `_MU_G_MIN` / `_MU_G_MAX` (`:47-48`), `_helmbold_cl_alpha` (`:56`), `_compute_mu_g` (`:70`), `_compute_k_g` (`:92`), `_compute_delta_n` (`:115`), `_extract_cl_alpha_from_context` (`:139`), `_build_gust_lines` (`:157`), `compute_vn_curve` (`:283`), `derive_performance_kpis` (`:371`), `_get_aeroplane` (`:538`), `_load_assumptions` (`:546`), `_get_wing_area_m2` (`:562`), `_get_v_max` (`:577`), `_load_operating_point_markers` (`:589`), `_get_b_ref` (`:620`), `_model_to_read` (`:636`), `compute_flight_envelope` (`:657`), `get_flight_envelope` (`:757`) | 🟢 |
| `app/schemas/flight_envelope.py` | `VnPoint`, `GustCriticalWarning`, `GustValidityWarning`, `VnCurve`, `PerformanceKPI`, `VnMarker`, `FlightEnvelopeRead`, `ComputeEnvelopeRequest` (dead) | 🟢 / 🟡 |
| `app/models/flight_envelope_model.py` | `FlightEnvelopeModel` (`:11`) — unique FK, upserted | 🟢 |
| `app/api/v2/endpoints/aeroplane/flight_envelope.py` | `_raise_http_from_domain`, `get_flight_envelope`, `compute_flight_envelope_endpoint` | 🟢 |
| `app/services/mass_cg_service.py` | 🟡 one resolver — the raising one (`Q-MS-9`) — `get_effective_assumption_value`, the reader used here | 🟢 / 🔴 |
| `app/converters/model_schema_converters.py` | `aeroplane_model_to_aeroplane_schema_async`, `aeroplane_schema_to_asb_airplane_async` — for `s_ref` and `b_ref` | 🟢 |
