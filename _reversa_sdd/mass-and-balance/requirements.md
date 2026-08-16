# mass-and-balance

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mass-and-balance,
> `_reversa_sdd/data-dictionary.md` §Module: mass-and-balance,
> `_reversa_sdd/domain.md` §2.5, ADR 0010, ADR 0011, ADR 0012, ADR 0009.

## Overview

`mass-and-balance` answers two different questions that are easy to confuse:
**how heavy is the aircraft** (a bottom-up sum) and **where must its centre of
gravity be** (a top-down requirement from stability). It owns the flat
`weight_items` inventory, the mass-weighted CG aggregation, the two independent
producers that write the `mass` design assumption's CALCULATED side, the
design-vs-component CG comparison with its 1 cm verdict, and the mass-dependent
design metrics (wing loading, stall speed, required C_L, C_L margin). 🟢

The module never writes `cg_x`. Per ADR 0011 the design CG is `x_np − SM·MAC`,
owned by `mission-and-sizing`; the aggregate CG produced here exists **only for
comparison**. 🟢

## Responsibilities

- CRUD the per-aeroplane `weight_items` inventory and serve it with an inline
  mass + 3-axis CG summary. 🟢
- Provide the pure aggregation `aggregate_weight_items` — total mass and the
  mass-weighted CG in x, y and z. 🟢
- Push the aggregated mass into `design_assumptions."mass".calculated_value`
  after every weight-item write, best-effort. 🟢
- Push the **component-tree** roll-up into the same `calculated_value`, also
  best-effort, on behalf of `aeroplane-core`. 🟢
- Compare the design CG against the aggregated component CG and publish a
  boolean tolerance verdict at `CG_TOLERANCE_M = 0.01 m`. 🟢
- Compute the mass-dependent design metrics at a requested flight condition,
  resolving `s_ref` by building the AeroSandbox airplane. 🟢
- Provide the pure `compute_recommended_cg(np_x, mac, SM) = np_x − SM·mac`
  helper. 🟢 (gains a production caller with `Q-MB-2`.)

**Explicitly NOT this module's responsibility:** the component tree itself and
its weight ladder (→ `aeroplane-core`, use case
[`weight-rollup`](../aeroplane-core/weight-rollup/design.md)); the
ESTIMATE/CALCULATED assumption machine, the CG envelope, loading scenarios and
the SM classification (→ `mission-and-sizing`); the stability solve that
produces `x_np` and `MAC` (→ `aero-analysis`); COTS component masses
(→ `powertrain`).

## Business Rules

> `BR-24`…`BR-34` and `BR-78` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-MB*` are module-local.

### The mass side

- **BR-29 — Mass starts as an estimate and becomes bottom-up.** 🟢 A new
  aircraft seeds `mass = 1.5 kg` (`PARAMETER_DEFAULTS["mass"]`). Both producers
  write only the CALCULATED side; the estimate is never touched.
- **BR-24 — Every parameter carries an estimate and a calculation (ADR 0010).**
  🟢 `effective_value = calculated_value if active_source == "CALCULATED" and it
  exists else estimate_value`.
- **BR-25 — Auto-switch happens once.** 🟢 Both syncs call
  `update_calculated_value(..., auto_switch_source=True)`, so the first sync
  flips `active_source` to `CALCULATED`; a user who later flips it back to
  ESTIMATE keeps that choice.
- **BR-MB1 — A sync on an unseeded aircraft is a no-op, not an error.** 🟢 Both
  `sync_component_tree_to_mass` (`mass_cg_service.py:149-158`) and
  `sync_weight_items_to_assumptions` (`:189-198`) first probe for a
  `design_assumptions` row named `"mass"` and `return` when it is absent. This
  is what makes the sync safe on a freshly created aircraft.
- **BR-MB2 — Both syncs share one five-step shape.** 🟢
  ```
  1. resolve the aeroplane by UUID                → NotFoundError
  2. no design_assumptions row named "mass"       → return (no-op)
  3. aggregate                                    → total_kg | None
  4. update_calculated_value(db, uuid, "mass", total_kg, source,
                             auto_switch_source=True)
  5. mark_ops_dirty(aeroplane.id)
     + event_bus.publish(AssumptionChanged(parameter_name="mass"))
  ```
- **BR-MB3 — The source label follows the value, not the trigger.** 🟢
  `source = "component_tree" if total_kg is not None else None` (`:161`) and
  `source = "weight_items" if total_mass is not None else None` (`:211`). An
  empty producer therefore writes `calculated_value = None` **and** clears
  `calculated_source` — the aircraft goes back to its estimate rather than
  claiming a 0 kg calculation.
- **BR-30 — Mass sync never blocks the CRUD that triggered it.** 🟢
  `weight_items_service._try_sync_assumptions` catches `NotFoundError` and
  `SQLAlchemyError` and logs a warning (`:57-64`);
  `component_tree_service._sync_aircraft_mass` catches bare `Exception`.
  *Consequence (🟡):* a persistently failing sync emits a `DesignWarning` rather than only logging (`Q-AC-7`, derived from `P-WARN-0`).
- **BR-MB4 — 🟢 **Resolved by `Q-MB-1` (maintainer-answered): the component tree is authoritative and `weight_items` is retired.** Two producers previously wrote one column with last-write-wins.** An aircraft that
  has both weight items and a component tree ends with whichever source was
  touched last. `calculated_source` records the winner; nothing warns that the
  other estimate was discarded. Confirmed by both writers targeting
  `"mass".calculated_value` with no arbitration.
- **BR-31 — The component-tree weight ladder.** 🟢 `weight_override_g`
  (`override`) → COTS `mass_g × quantity` (`cots`) → CAD-shape density
  (`calculated`) → `(None, "none")`. Owned by `aeroplane-core`; consumed here
  through `get_aircraft_total_weight_kg`.
- **BR-MB5 — An empty tree yields `None`, never `0.0`.** 🟢 (BR-29 corollary,
  ADR 0011 §5.) The caller clears `calculated_value` instead of asserting a 0 kg
  aircraft.

### The CG side

- **BR-28 — CG is a top-down design target, not a bottom-up sum (ADR 0011).**
  🟢 `cg_x` is *CG_aero* = `x_np − SM_target·MAC`, written by
  `assumption_compute_service`. `sync_weight_items_to_assumptions` computes
  `cg_x`, `cg_y`, `cg_z` and **discards all three**
  (`mass_cg_service.py:205` binds them to `_cg_x`, `_cg_y`, `_cg_z`) — the
  discard is deliberate and documented in the docstring (gh-465).
- **BR-MB6 — CG aggregation is mass-weighted in three axes and undefined for a
  zero-mass inventory.** 🟢
  ```
  m_tot = Σ mᵢ
  cg_k  = Σ (mᵢ · kᵢ) / m_tot        for k ∈ {x, y, z}
  items empty  or  m_tot ≤ 0  ⇒  (None, None, None, None)
  ```
  (`aggregate_weight_items:78-97`.) Note the guard is `≤ 0`, not `== 0`, so a
  pathological negative inventory also returns `None` rather than a signed CG.
- **BR-MB7 — The comparison is a delta with a hard 1 cm verdict.** 🟢
  ```
  Δx               = cg_x_design − cg_x_components
  within_tolerance = |Δx| < CG_TOLERANCE_M      CG_TOLERANCE_M = 0.01 m
  ```
  With no weight items, `component_*`, `delta_x` and `within_tolerance` are all
  `None` — the verdict is *absent*, never `False` (`get_cg_comparison:235-249`).
- **BR-MB8 — The design CG is read through the local resolver, which raises.**
  🟢 `get_cg_comparison` calls `get_effective_assumption_value(db, uuid, "cg_x")`
  (`:112-128`), which raises `NotFoundError` when the row is missing — unlike
  `design_assumptions_service.get_effective_assumption`, which falls back to
  `PARAMETER_DEFAULTS` and returns `None`. 🟡 Two resolvers, two behaviours — ADR 0022 requires one.

### The metrics side

- **BR-MB9 — `GRAVITY = 9.81` here.** 🟢 (`mass_cg_service.py:20`.) It diverges
  from `G = 9.80665` in `endurance_service`, `powertrain_performance` and
  `powertrain_solution_space_service`. 0.007 % — numerically irrelevant, but
  there is no single gravity constant in the codebase. 🟡 One physical-constants module (`Q-MB-8`).
- **BR-MB10 — The design-metrics formulas.** 🟢
  ```
  W          = mass_kg · GRAVITY                    [N]
  W/S        = W / s_ref                            [N/m² = Pa]
  V_stall    = sqrt(2·W / (ρ · s_ref · cl_max))     [m/s]
  q          = ½ · ρ · velocity²                    [Pa]
  CL_req     = W / (q · s_ref)                      [–]
  CL_margin  = cl_max − CL_req                      [–]   > 0 ⇒ above stall
  ```
- **BR-MB11 — Every non-positive input is rejected, never clamped.** 🟢
  `compute_design_metrics` raises `ValidationError` for `mass_kg ≤ 0`,
  `s_ref ≤ 0`, `cl_max ≤ 0`, `rho ≤ 0` and `velocity ≤ 0` **before** any
  arithmetic (`:49-58`). Consistent with ADR 0012.
- **BR-MB12 — A missing wing is an actionable message, not a divide-by-zero.**
  🟢 `get_s_ref_for_aeroplane` builds the ASB airplane purely to read `s_ref`
  and raises `ValidationError("Wing reference area (s_ref) is zero or negative
  — add wings first")` for `s_ref ≤ 0`; a conversion failure becomes
  `InternalError` with the underlying message (`:252-268`).
- **BR-MB13 — AeroSandbox is imported inside the function.** 🟢
  `import aerosandbox as asb` sits in the body of
  `get_design_metrics_for_aeroplane` (`:275`) so the module stays importable on
  platforms where ASB is excluded (`linux/aarch64`, ADR 0017). `ρ` comes from
  `asb.Atmosphere(altitude=…).density()` — the ISA model, **not** the
  exponential approximation used in `powertrain`.
- **BR-78 / ADR 0009 — Transactions belong to `get_db()`.** 🟢 The services call
  `db.add` / `db.flush` / `db.delete` and never `db.commit()`.

### The inventory

- **BR-MB14 — `list_weight_items` re-implements the aggregation inline and
  rounds to 6 decimals.** 🟢 (`weight_items_service.py:36-54`.) It does **not**
  call `aggregate_weight_items`, which does not round. Both agree numerically
  today; a change to one will not propagate. 🟡
- **BR-MB15 — The category set is enforced by Pydantic only.** 🟢
  `WEIGHT_CATEGORIES = electronics | battery | structural | payload | other`
  (`app/schemas/weight_item.py:8`), default `other`. The DB column is a plain
  `String`, so a direct SQL insert can store anything. 🟢 No CHECK is added — the table is retired (`Q-MB-10`); the closed-set question moves to `component_tree.node_type`, which does get one (`Q-CC-9`).
- **BR-MB16 — Weight items are metres and kilograms.** 🟢 `mass_kg` in kg
  (`ge=0`), `x_m` / `y_m` / `z_m` in metres, all defaulting to `0.0`. Contrast
  with the component tree, which is grams and millimetres.
- **BR-MB17 — Deletion cascades from the aeroplane.** 🟢
  `AeroplaneModel.weight_items` uses `cascade="all, delete-orphan"` and the FK
  is `ON DELETE CASCADE`; the relationship is ordered by `id`.
- 🟢 **Moot — `weight_items` is retired** (`Q-MB-1`). It carried no `component_id`, so a battery entered as a weight
  item and the same battery placed in the component tree are unrelated rows.
  Double-counting is possible and undetected.
- 🟢 **`compute_recommended_cg` gains its production caller and becomes the single authority** (`Q-MB-2`). The top-down CG rule
  is implemented and unit-tested here, but production reads it from
  `loading_scenario_service.compute_stability_envelope` and
  `assumption_compute_service`. `RecommendedCGRequest` /
  `RecommendedCGResponse` are declared (`app/schemas/mass_cg.py:8-23`) and
  returned by no endpoint.
- 🟢 **`cg_y` and `cg_z` gain consumers** (`Q-MB-3`, maintainer-answered): `cg_y` feeds an aileron-trim check (`δ_A = C_L·y_cg/(b·C_lδA)`, evaluated at approach, not cruise), `cg_z` feeds the thrust-line pitch check only. They are computed, serialised
  on `WeightSummary` and `CGComparisonResponse`, and never read by any
  downstream consumer; only `cg_x` reaches
  `assumption_computation_context.cg_agg_m`.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List the weight items of an aeroplane with total mass and 3-axis CG | Must | `GET .../weight-items` → 200 `WeightSummary`; totals rounded to 6 dp; unknown UUID → 404 |
| RF-02 | Report `cg_*` as `null` when the inventory is empty or totals ≤ 0 | Must | An aeroplane with no items returns `total_mass_kg = 0`, `cg_x_m = cg_y_m = cg_z_m = null` |
| RF-03 | Create a weight item and return it with its id | Must | `POST .../weight-items` → **201** `WeightItemRead`; `mass_kg < 0` or empty `name` → 422 |
| RF-04 | Read a single weight item scoped to its aeroplane | Must | `GET .../weight-items/{item_id}` → 200; an id belonging to another aeroplane → 404 |
| RF-05 | Update a weight item as a full replacement | Must | `PUT .../weight-items/{item_id}` → 200 with the new values persisted |
| RF-06 | Delete a weight item | Must | `DELETE .../weight-items/{item_id}` → **204** with no body; unknown id → 404 |
| RF-07 | Sync the aggregated weight-item mass into `mass.calculated_value` after every create/update/delete | Must | After a create the assumption has `calculated_value == Σ mᵢ` and `calculated_source == "weight_items"` |
| RF-08 | Sync the component-tree roll-up into the same `calculated_value` on behalf of `aeroplane-core` | Must | After a tree write the assumption has `calculated_source == "component_tree"` |
| RF-09 | Auto-switch `active_source` to CALCULATED on the first sync | Must | A freshly seeded aircraft is ESTIMATE; after the first non-empty sync it is CALCULATED |
| RF-10 | Clear the calculated value when the producing source becomes empty | Must | Deleting the last weight item leaves `calculated_value = null` and `calculated_source = null` |
| RF-11 | Never fail the triggering CRUD because of a sync failure | Must | With the sync patched to raise, the weight-item write still returns its success status |
| RF-12 | Publish `AssumptionChanged(mass)` and mark operating points dirty on every successful sync | Must | A spy on the event bus records exactly one `AssumptionChanged` per sync |
| RF-13 | Compare the design CG with the aggregated component CG, with a 1 cm verdict | Must | `GET .../cg_comparison` → 200; `within_tolerance` is `true` iff `|Δx| < 0.01` |
| RF-14 | Report the comparison as *absent*, not *failed*, when there are no weight items | Must | With no items, `component_cg_x`, `delta_x` and `within_tolerance` are all `null` |
| RF-15 | Compute the mass-dependent design metrics at a requested velocity and altitude | Must | `POST .../design_metrics` → 200 with all seven fields of `DesignMetricsResponse` |
| RF-16 | Reject non-positive metric inputs with a validation error | Must | `cl_max = 0` in the assumptions → 422 with `cl_max must be positive` |
| RF-17 | Explain a missing wing instead of dividing by zero | Must | An aeroplane without wings → 422 *"… add wings first"* |
| RF-18 | Provide `compute_recommended_cg(np_x, mac, SM) = np_x − SM·mac` as a pure function | Should | Unit test: `(0.5, 0.2, 0.12) → 0.476` |
| RF-19 | Keep `cg_x` untouched by both syncs | Must | After any sync, the `cg_x` assumption row is byte-identical to its pre-sync state |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | An absent quantity is `null`, never a fabricated `0` — for CG, for the calculated mass and for the tolerance verdict | `aggregate_weight_items:86-91`, `mass_cg_service.py:161,211`, `get_cg_comparison:235-239` | 🟢 |
| Correctness | Design inputs are validated before use, with a per-input message | `compute_design_metrics:49-58` | 🟢 |
| Correctness | The design CG is never overwritten by the aggregate (ADR 0011) | `sync_weight_items_to_assumptions:174-186, 205` | 🟢 |
| Availability | A mass-sync failure degrades the assumption, never the CRUD | `weight_items_service._try_sync_assumptions:57-64` | 🟢 |
| Portability | The module imports AeroSandbox lazily so it loads on ASB-less platforms (ADR 0017) | `get_design_metrics_for_aeroplane:275`, `get_s_ref_for_aeroplane:254-255` | 🟢 |
| Reliability | Transaction boundary is the request; services never commit (ADR 0009) | `app/db/session.py:55-64` | 🟢 |
| Performance | The inventory is one indexed query per request; the summary is computed in Python over the already-loaded rows | `weight_items_service.py:38-46` | 🟢 |
| Performance | `design_metrics` is the module's only expensive route — it builds a full ASB airplane just to read `s_ref` | `get_s_ref_for_aeroplane:252-268` | 🟡 no timing instrumentation exists |
| Security | No application-level authentication; the deployment tunnel is the trust boundary (ADR 0016) | — | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Weight-item inventory

  Scenario: Listing an inventory reports mass and CG
    Given an aeroplane with weight items 0.4 kg at x=0.10 m and 0.6 kg at x=0.20 m
    When I GET /aeroplanes/{id}/weight-items
    Then the response status is 200
    And total_mass_kg is 1.0
    And cg_x_m is 0.16

  Scenario: An empty inventory has no centre of gravity
    Given an aeroplane with no weight items
    When I GET /aeroplanes/{id}/weight-items
    Then total_mass_kg is 0
    And cg_x_m, cg_y_m and cg_z_m are all null

  Scenario: A negative mass is rejected
    Given an aeroplane
    When I POST /aeroplanes/{id}/weight-items with mass_kg -0.5
    Then the response status is 422
    And no weight item is created

  Scenario: Deleting a weight item returns no content
    Given an aeroplane with one weight item
    When I DELETE /aeroplanes/{id}/weight-items/{item_id}
    Then the response status is 204
    And the response body is empty

Feature: Mass assumption sync

  Scenario: The first sync switches the source to CALCULATED
    Given a seeded aeroplane whose mass assumption is ESTIMATE 1.5 kg
    When I add a weight item of 0.8 kg
    Then the mass assumption has calculated_value 0.8
    And calculated_source is "weight_items"
    And active_source is "CALCULATED"

  Scenario: Emptying the producer clears the calculation
    Given an aeroplane whose only weight item is 0.8 kg and whose mass is CALCULATED
    When I delete that weight item
    Then the mass assumption has calculated_value null
    And calculated_source is null

  Scenario: A sync on an unseeded aircraft is a silent no-op
    Given an aeroplane with no design_assumptions rows
    When I add a weight item
    Then the response status is 201
    And no design_assumptions row is created

  Scenario: A failing sync does not fail the write
    Given mass_cg_service.sync_weight_items_to_assumptions raises SQLAlchemyError
    When I POST a weight item
    Then the response status is 201
    And the weight item is persisted
    And a warning is logged

  Scenario: The design CG is never overwritten
    Given an aeroplane whose cg_x assumption is 0.150 m
    When weight items totalling 1 kg at x = 0.400 m are synced
    Then the cg_x assumption is still 0.150 m

Feature: CG comparison

  Scenario: Within tolerance
    Given a design cg_x of 0.150 m and weight items whose aggregate CG is 0.155 m
    When I GET /aeroplanes/{id}/cg_comparison
    Then delta_x is -0.005
    And within_tolerance is true

  Scenario: Outside tolerance
    Given a design cg_x of 0.150 m and weight items whose aggregate CG is 0.200 m
    When I GET /aeroplanes/{id}/cg_comparison
    Then within_tolerance is false

  Scenario: No components means no verdict
    Given an aeroplane with a design cg_x and no weight items
    When I GET /aeroplanes/{id}/cg_comparison
    Then component_cg_x, delta_x and within_tolerance are all null
    And design_cg_x is populated

  Scenario: A missing cg_x assumption is a 404
    Given an aeroplane with no cg_x design assumption row
    When I GET /aeroplanes/{id}/cg_comparison
    Then the response status is 404

Feature: Design metrics

  Scenario: Metrics at a cruise condition
    Given an aeroplane with mass 2.0 kg, cl_max 1.4 and a wing of s_ref 0.30 m²
    When I POST /aeroplanes/{id}/design_metrics with velocity 15 and altitude 0
    Then the response status is 200
    And wing_loading_pa equals 2.0 * 9.81 / 0.30
    And stall_speed_ms equals sqrt(2 * 2.0 * 9.81 / (1.225 * 0.30 * 1.4))
    And cl_margin equals cl_max minus required_cl

  Scenario: An aircraft without wings is refused with a remediation
    Given an aeroplane with no wings
    When I POST /aeroplanes/{id}/design_metrics with velocity 15
    Then the response status is 422
    And the message contains "add wings first"
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Weight-item CRUD + summary (RF-01…RF-06) | Must | The inventory is the simple-aircraft mass path and the only source of the aggregate CG |
| Both mass syncs into the assumption (RF-07…RF-10) | Must | The mass assumption drives retrim, V_stall, the matching chart, the solution space and endurance — every sizing surface reads it |
| Non-blocking sync (RF-11) | Must | Explicit design property (BR-30); the CRUD contract depends on it |
| `AssumptionChanged` + dirty marking (RF-12) | Must | Without the event a mass edit silently fails to propagate; the whole recompute chain hangs off it |
| CG comparison (RF-13/RF-14) | Must | The user-facing half of ADR 0011 — the design loop's feedback signal |
| Design metrics (RF-15…RF-17) | Must | The mass-dependent sanity check the workbench shows next to the assumption panel |
| `cg_x` immutability under sync (RF-19) | Must | ADR 0011's central rule; violating it inverts the design loop |
| `compute_recommended_cg` (RF-18) | **Must** | 🟢 decided (`Q-MB-2`): it becomes the single authority and gains a production caller; the duplicates elsewhere |
| 3-axis CG (`cg_y`, `cg_z`) | Could | Computed and serialised, consumed by nothing |
| `RecommendedCGRequest` / `RecommendedCGResponse` schemas | Won't | Dead — declared, never returned by any route |
| Arbitration between the two mass producers | **N/A** | 🟢 decided (`Q-MB-1`): there is only one producer — the component tree; `weight_items` is retired. No arbitration is needed. Previously last-write-wins was the contract |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/mass_cg_service.py` | `compute_recommended_cg`, `compute_design_metrics`, `aggregate_weight_items`, `get_effective_assumption_value`, `sync_component_tree_to_mass`, `sync_weight_items_to_assumptions`, `get_cg_comparison`, `get_s_ref_for_aeroplane`, `get_design_metrics_for_aeroplane`, `_get_aeroplane` | 🟢 |
| `app/services/weight_items_service.py` | `list_weight_items`, `create_weight_item`, `get_weight_item`, `update_weight_item`, `delete_weight_item`, `_try_sync_assumptions`, `_item_to_schema` | 🟢 |
| `app/api/v2/endpoints/aeroplane/weight_items.py` | 5 routes + `_raise_http` / `_call` | 🟢 |
| `app/api/v2/endpoints/aeroplane/mass_cg.py` | 2 routes + `_raise_http` / `_call` | 🟢 |
| `app/models/aeroplanemodel.py:798` | `WeightItemModel` | 🟢 |
| `app/schemas/weight_item.py` | `WeightItemWrite`, `WeightItemRead`, `WeightSummary`, `WEIGHT_CATEGORIES` | 🟢 |
| `app/schemas/mass_cg.py` | `DesignMetricsRequest/Response`, `CGComparisonResponse` | 🟢 |
| `app/schemas/mass_cg.py:8-23` | `RecommendedCGRequest`, `RecommendedCGResponse` | 🟢 gain a route with `Q-MB-2` |
| `app/services/component_tree_service.py:362-403` | `_sync_aircraft_mass`, `get_aircraft_total_weight_kg` — the competing producer | 🟢 owned by `aeroplane-core` |
</content>
</invoke>
