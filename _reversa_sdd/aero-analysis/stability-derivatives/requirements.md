# stability-derivatives

> Use-case specification, nested under the module
> [`aero-analysis`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aero-analysis
> (Stability results), `_reversa_sdd/data-dictionary.md`
> §`stability_results`, `_reversa_sdd/state-machines.md` §8.

## Overview

`stability-derivatives` turns one solver run at one operating point into the
aircraft's **static stability verdict**: neutral point, static margin, a
three-way stability class, the CG range that the margin bounds imply, and the
three sign tests on `Cma` / `Cnb` / `Clb`. The result is persisted **once per
solver per aircraft**, stamped with a geometry hash so a later read can tell
whether it still describes the current airframe. 🟢

## Responsibilities

- Run the requested solver at a given operating point and extract the stability
  quantities from the solver-agnostic `AnalysisModel`. 🟢
- Compute static margin, `static_margin_pct` and the three-way stability class.
  🟢
- Compute the forward and aft CG range from the margin bounds. 🟢
- Evaluate the three sign tests: `Cma < 0`, `Cnb > 0`, `Clb < 0`. 🟢
- Extract the trim α and the trim elevator deflection for reporting. 🟢
- Hash the **stability-relevant** geometry and store it on the row. 🟢
- Upsert one row per `(aeroplane_id, solver)` and serve the cached result,
  preferring `CURRENT` over `DIRTY`. 🟢

**Explicitly NOT this use case's responsibility:** producing `x_np` for the
cached aero context (that is the recompute pipeline's
`_stability_run_at_cruise` → [`../aero-context-single-source/`](../aero-context-single-source/requirements.md)),
the CG / loading envelope and the SM classification thresholds
(→ `mission-and-sizing`), and the dynamic modes / eigenvalues (**not
implemented anywhere**, 🔴).

## Business Rules

- **BR-AA14 — The stability summary is derived, persisted and hash-keyed.** 🟢
  `get_stability_summary` (`stability_service.py:289-362`):

  ```
  static_margin           = (Xnp − Xcg) / MAC        Xcg = operating_point.xyz_ref[0]
  static_margin_pct       = 100 · static_margin
  stability_class         = stable  (> 5 %)
                          | neutral (0–5 %)
                          | unstable (< 0)
  cg_range_forward        = Xnp − (max_margin / 100) · MAC      default 25 %
  cg_range_aft            = Xnp − (min_margin / 100) · MAC      default  5 %
  is_statically_stable    = Cma < 0
  is_directionally_stable = Cnb > 0
  is_laterally_stable     = Clb < 0
  ```

  `Xnp` is `result.reference.Xnp`, `MAC` is `result.reference.Cref` — both read
  from the envelope, so the rule is solver-independent (BR-AA1).
- **BR-SD1 — The geometry hash covers only what changes stability.** 🟢
  `compute_geometry_hash` (`:102-141`) hashes per-wing
  `x_le / y_le / z_le / chord / twist` and per-fuselage `x_c / width / height`
  into `sha256[:16]`. Spars, servos, turbulators, materials and construction
  data are deliberately **excluded** — they cannot move the neutral point.
- **BR-SD2 — One row per solver per aircraft.** 🟢
  `persist_stability_result` upserts on
  `uq_stability_aeroplane_solver (aeroplane_id, solver)`. Comparing AeroBuildup
  against AVL is therefore a supported workflow: both rows coexist.
- **BR-AA15 — The cached read prefers `CURRENT` by string ordering.** 🟡
  `get_cached_stability` orders by `status ASC, computed_at DESC`; `CURRENT`
  precedes `DIRTY` **alphabetically**. Correct today, but it relies on the
  spelling of the status values rather than an explicit rank.
- **BR-SD3 — A geometry write marks the stability row `DIRTY`.** 🟢 The
  `after_insert/update/delete` listeners in `stability_events.py` on
  `WingModel` / `WingXSecModel` / `FuselageModel` mark the table dirty, call
  `mark_ops_dirty` and publish `GeometryChanged`.
  🟡 **Factor the shared listener out so a geometry write publishes `GeometryChanged` once** (`Q-AA-4`, derived; ADR 0022 applied to invalidation paths). The same three models are attached **again** in `avl_geometry_events.py`, so
  every geometry write fires the chain twice.
- 🔴 **BR-AA16 — The CG-range bounds are unreachable configuration.**
  `_get_margin_bounds` (`:225-254`) queries the design assumptions
  `min_static_margin` / `max_static_margin`, but neither name exists in
  `VALID_PARAMETERS` / `PARAMETER_DEFAULTS`, so `seed_defaults` never creates
  them and the query always returns empty. The 5 % / 25 % defaults are therefore
  **effectively hard-coded** while presenting as configurable.
- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged. Previously the trim-elevator extraction missed gh-772 mixing names (bug
  #955).** `_find_trim_elevator` picks the **first** deflection whose name
  contains `"elevator"` (case-insensitive). A V-tail's control variable is
  `[ruddervator]pitch_htail_1`, which never matches, so `trim_elevator_deg`
  stays `NULL` on exactly the aircraft where the pitch authority question
  matters most.
- 🔴 **BR-AA17 — `_auto_populate_cd0` violates BR-14 / ADR 0004.**
  (`:257-281`) When the tool is AeroBuildup it writes `result.CD` — the
  **total** CD at the operating point — into the `cd0` assumption's
  `calculated_value` with source `"stability_analysis"`. That is precisely the
  quantity gh-924 removed from the authoritative path, and because it runs on a
  different trigger the stored `cd0` can be overwritten with a total-drag value
  between recomputes.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Compute a stability summary at a given OP with a caller-selected solver | Must | `POST …/stability_summary/{tool}` → 200 for all three tools |
| RF-02 | Derive static margin from `(Xnp − Xcg)/MAC` with `Xcg = xyz_ref[0]` | Must | Moving `xyz_ref[0]` aft reduces the margin proportionally |
| RF-03 | Classify stability three ways | Must | `>5 %` → `stable`; `0–5 %` → `neutral`; `<0` → `unstable` |
| RF-04 | Derive the CG range from the margin bounds | Must | `cg_range_forward = Xnp − 0.25·MAC`, `cg_range_aft = Xnp − 0.05·MAC` by default |
| RF-05 | Evaluate the three sign tests | Must | `Cma = −0.8` → statically stable; `Cnb = −0.02` → not directionally stable |
| RF-06 | Extract trim α and trim elevator deflection | Should | Both appear on the persisted row when the OP carries deflections |
| RF-07 | Hash the stability-relevant geometry into `sha256[:16]` | Must | Changing a chord changes the hash; adding a spar does not |
| RF-08 | Upsert one row per `(aeroplane_id, solver)` | Must | Two AeroBuildup runs leave one row; adding an AVL run makes two |
| RF-09 | Serve the cached result, preferring `CURRENT` over `DIRTY` | Must | With both present, the `CURRENT` row is returned |
| RF-10 | Return 404 when no cached result exists | Must | A fresh aircraft → `GET …/stability` 404 |
| RF-11 | Mark the stability row `DIRTY` on any geometry write | Must | Editing a wing station flips `status` to `DIRTY` |
| RF-12 | Never write the `cd0` assumption from this path | **Must (open)** | 🔴 the legacy does; `cd0` must have exactly one writer (BR-14) |
| RF-13 | Match the trim control by its gh-772 mixing name | **Must (open)** | 🔴 a V-tail must report a non-null trim deflection |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The summary reads only envelope fields, so it is identical in shape for all three solvers | `AnalysisModel.reference/derivatives` | 🟢 |
| Correctness | The geometry hash excludes non-stability data, so unrelated edits do not invalidate a valid result | `compute_geometry_hash:102-141` | 🟢 |
| Correctness | Exactly one row per solver — no unbounded history growth, no ambiguity about "the" result | `uq_stability_aeroplane_solver` | 🟢 |
| Performance | The cached read is a single indexed query; no solver runs on `GET …/stability` | `get_cached_stability` | 🟢 |
| Availability | A `DIRTY` row is still served (with its status) rather than 404 — a stale answer beats no answer, and the status says so | ordering `status ASC, computed_at DESC` | 🟡 |
| Traceability | `cg_x_used`, `computed_at`, `solver` and `geometry_hash` make every row self-describing | `stability_results` columns | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Static stability summary

  Scenario: A stable aircraft is classified stable
    Given a neutral point at 0.30 m, a CG at 0.26 m and a MAC of 0.20 m
    When the stability summary is computed
    Then static_margin is 0.20
    And static_margin_pct is 20.0
    And stability_class is "stable"

  Scenario: A neutral aircraft
    Given a static margin of 0.03
    Then stability_class is "neutral"

  Scenario: An unstable aircraft
    Given a CG aft of the neutral point
    Then static_margin_pct is negative
    And stability_class is "unstable"

  Scenario: The three sign tests
    Given Cma -0.8, Cnb 0.05 and Clb -0.02
    Then is_statically_stable, is_directionally_stable and is_laterally_stable
         are all true
    And flipping the sign of Cnb makes is_directionally_stable false

  Scenario: The CG range follows the margin bounds
    Given a neutral point at 0.30 m and a MAC of 0.20 m
    When the summary is computed with the default bounds
    Then cg_range_forward is 0.25 m
    And cg_range_aft is 0.29 m

Feature: Caching and invalidation

  Scenario: One row per solver
    Given two AeroBuildup stability runs on the same aircraft
    Then exactly one stability_results row exists for solver "aerobuildup"
    And an AVL run adds a second row rather than replacing it

  Scenario: The geometry hash tracks only stability-relevant geometry
    Given a stored stability result
    When I change a wing chord
    Then the recomputed geometry hash differs
    But adding a spar to that wing leaves the hash unchanged

  Scenario: A geometry edit dirties the cached result
    Given a CURRENT stability result
    When a wing cross-section is updated
    Then the row status becomes DIRTY

  Scenario: The cached read prefers CURRENT
    Given a CURRENT row and a DIRTY row for the same aeroplane
    When I GET the cached stability
    Then the CURRENT row is returned

  Scenario: No cached result is a 404
    Given an aeroplane that has never been analysed
    When I GET the cached stability
    Then the response status is 404

Feature: Known defects (documented behaviour)

  Scenario: A V-tail reports no trim deflection
    Given an aircraft whose only pitch control is "[ruddervator]pitch_htail_1"
    When the stability summary is computed
    Then trim_elevator_deg is null
    # 🟢 resolved via the mixing resolver (Q-WD-1); the substring match cannot match

  Scenario: The margin bounds cannot be configured
    Given a user who sets min_static_margin to 8 percent
    When the stability summary is computed
    Then cg_range_aft is still derived from 5 percent
    # 🟡 **Drop the dead lookup and promote the 5 % / 15 % band** (`Q-AA-2`, derived).

  Scenario: A stability run overwrites the parasite cd0
    Given a cached context whose cd0 is the parasite value 0.021
    When an AeroBuildup stability summary runs and reports CD 0.048
    Then the cd0 assumption's calculated_value becomes 0.048
    # 🟢 **`_auto_populate_cd0` is deleted** (`Q-AA-1`, maintainer-answered) — it wrote *total* CD into the parasite-CD0 assumption, a confirmed BR-14 / ADR 0004 violation that collapsed (L/D)max from ≈24 to ≈17.
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Static margin + classification (RF-02, RF-03) | Must | The primary safety verdict shown in the workbench and read by the copilot |
| Sign tests (RF-05) | Must | The only directional/lateral stability check in the system |
| Persistence + geometry hash (RF-07, RF-08) | Must | Without the hash a cached verdict silently describes an older airframe |
| Cached read + `CURRENT` preference (RF-09, RF-10) | Must | The workbench's default read path |
| CG range (RF-04) | Must | Consumed by the CG envelope in `mission-and-sizing` |
| Dirty marking (RF-11) | Must | Otherwise a stale verdict presents as current |
| Removing `_auto_populate_cd0` (RF-12) | **Must (open)** | Confirmed BR-14 violation with silent numeric consequences |
| Mixing-name trim match (RF-13) | **Must (open)** | Bug #955; today a null on every dual-role aircraft |
| Trim α / elevator extraction (RF-06) | Should | Reporting only; the trim itself lives in `operating-point-solve` |
| Explicit enum rank instead of string ordering | Should | Correct today, fragile by construction |
| Dynamic modes / eigenvalues | Won't | Not implemented anywhere; AVL could supply them but no path does |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/stability_service.py` | `get_stability_summary` (`:289-362`), `compute_geometry_hash` (`:102-141`), `persist_stability_result`, `get_cached_stability`, `_get_margin_bounds` (`:225-254`), `_find_trim_elevator`, `_auto_populate_cd0` (`:257-281`) | 🟢 |
| `app/models/stability_result.py` | `StabilityResultModel`, `uq_stability_aeroplane_solver` | 🟢 |
| `app/models/stability_events.py` | `after_insert/update/delete` listeners on `WingModel`, `WingXSecModel`, `FuselageModel` | 🟢 |
| `app/api/v2/endpoints/aeroanalysis.py` | `get_stability_summary` (`POST …/stability_summary/{analysis_tool}`), `get_cached_stability` (`GET …/stability`) | 🟢 |
| `cad_designer/.../models/analysis_model.py` | `reference.Xnp`, `reference.Cref`, `derivatives.Cma/Cnb/Clb` | 🟢 read-only (ADR 0002) |
