# mass-and-balance — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contract: [`contracts.md`](contracts.md).
> Use cases: [`weight-items`](weight-items/design.md) ·
> [`cg-mass-computation`](cg-mass-computation/design.md) ·
> [`component-tree-mass-sync`](component-tree-mass-sync/design.md).

## Interface

### Service surface — `app/services/mass_cg_service.py` 🟢

| Symbol | Signature | Line | Note |
|---|---|---|---|
| `GRAVITY` | `9.81` | 20 | 🟡 collapses into one physical-constants module (`Q-MB-8`) |
| `CG_TOLERANCE_M` | `0.01` | 21 | the `within_tolerance` threshold, metres |
| `WeightItemData` | `TypedDict{mass_kg, x_m, y_m, z_m}` | 24 | the aggregation's input shape — deliberately not the ORM row |
| `compute_recommended_cg` | `(np_x, mac, target_static_margin) -> float` | 36 | pure; 🟢 becomes the single authority with a production caller (`Q-MB-2`) |
| `compute_design_metrics` | `(mass_kg, s_ref, cl_max, rho, velocity) -> DesignMetricsResponse` | 41 | pure; validates all five inputs |
| `aggregate_weight_items` | `(Sequence[WeightItemData]) -> (m_tot?, cg_x?, cg_y?, cg_z?)` | 78 | pure; no rounding |
| `_get_aeroplane` | `(db, uuid) -> AeroplaneModel` | 105 | `NotFoundError(entity="Aeroplane")` |
| `get_effective_assumption_value` | `(db, uuid, param) -> float` | 112 | local ESTIMATE/CALCULATED resolver; **raises** when the row is absent |
| `sync_component_tree_to_mass` | `(db, uuid) -> None` | 131 | producer B |
| `sync_weight_items_to_assumptions` | `(db, uuid) -> None` | 174 | producer A |
| `get_cg_comparison` | `(db, uuid) -> CGComparisonResponse` | 224 | |
| `get_s_ref_for_aeroplane` | `(db, uuid) -> float` | 252 | builds the ASB airplane to read one number |
| `get_design_metrics_for_aeroplane` | `(db, uuid, velocity, altitude) -> DesignMetricsResponse` | 271 | route entry point |

### Service surface — `app/services/weight_items_service.py` 🟢

| Symbol | Signature | Line |
|---|---|---|
| `list_weight_items` | `(db, uuid) -> WeightSummary` | 36 |
| `create_weight_item` | `(db, uuid, WeightItemWrite) -> WeightItemRead` | 67 |
| `get_weight_item` | `(db, uuid, item_id) -> WeightItemRead` | 83 |
| `update_weight_item` | `(db, uuid, item_id, WeightItemWrite) -> WeightItemRead` | 95 |
| `delete_weight_item` | `(db, uuid, item_id) -> None` | 120 |
| `_try_sync_assumptions` | `(db, uuid) -> None` | 57 |

### REST surface 🟢

| Method | Path | In | Out | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/weight-items` | — | `WeightSummary` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/weight-items` | `WeightItemWrite` | `WeightItemRead` | **201** · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | — | `WeightItemRead` | 200 · 404 · 500 |
| PUT | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | `WeightItemWrite` | `WeightItemRead` | 200 · 404 · 422 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | — | — | **204** · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/design_metrics` | `DesignMetricsRequest` | `DesignMetricsResponse` | 200 · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/cg_comparison` | — | `CGComparisonResponse` | 200 · 404 · 500 |

`{aeroplane_id}` is the **UUID**, typed `UUID4` on the path. `{item_id}` is the
weight item's integer PK, always scoped to the aeroplane in the query.

### Persistence 🟢

`weight_items` — `aeroplane_id` (int FK `ON DELETE CASCADE`, indexed), `name`,
`mass_kg` (kg), `x_m` / `y_m` / `z_m` (metres, default `0.0`), `description`,
`category` (default `"other"`). Nothing else in the module persists anything:
the CG, the comparison and the metrics are all derived per request.

## Main Flow

### F1 — Aggregation (`aggregate_weight_items`, l.78-97) 🟢

```
if not items:                    -> (None, None, None, None)
m_tot = Σ mᵢ
if m_tot <= 0:                   -> (None, None, None, None)
cg_k  = Σ (mᵢ · kᵢ) / m_tot      for k ∈ {x, y, z}
                                 -> (m_tot, cg_x, cg_y, cg_z)
```

Pure, DB-free and unrounded. It takes `WeightItemData` dicts rather than ORM
rows, which is what makes it directly unit-testable and reusable for a
non-weight-item mass source. 🟡

### F2 — The summary route (`list_weight_items`, l.36-54) 🟢

The route does **not** call F1. It re-derives the same arithmetic inline over
the already-mapped `WeightItemRead` objects and rounds every published number to
**6 decimals**:

```
total = Σ mᵢ
if total > 0:
    cg_k = round(Σ(mᵢ·kᵢ)/total, 6)     k ∈ {x,y,z}
else:
    cg_k = None
return WeightSummary(items, round(total, 6), cg_x, cg_y, cg_z)
```

Two consequences: `total_mass_kg` is `0` (not `None`) for an empty inventory
while the CGs are `None`; and any future change to F1 will not reach this route.

### F3 — Producer A: weight items → mass (`sync_weight_items_to_assumptions`, l.174-221) 🟢

```
1. aeroplane = _get_aeroplane(db, uuid)               # NotFoundError
2. probe design_assumptions WHERE parameter_name = "mass"
   none -> return                                     # unseeded aircraft: no-op
3. rows  = weight_items WHERE aeroplane_id = aeroplane.id
   items = [{mass_kg, x_m, y_m, z_m}, …]
   total_mass, _cg_x, _cg_y, _cg_z = aggregate_weight_items(items)
                                                      # CGs deliberately dropped
4. source = "weight_items" if total_mass is not None else None
   update_calculated_value(db, uuid, "mass", total_mass, source,
                           auto_switch_source=True)
5. mark_ops_dirty(db, aeroplane.id)
   event_bus.publish(AssumptionChanged(aeroplane_id=…, parameter_name="mass"))
```

Step 3's discarded CG **is** ADR 0011 in code: the aggregate is computed and
thrown away because writing it into `cg_x` would invert the design loop.

Every import in steps 4–5 (`AssumptionChanged`, `event_bus`,
`update_calculated_value`, `mark_ops_dirty`) is **function-local**, breaking the
`mass_cg_service ↔ design_assumptions_service ↔ invalidation_service` cycle. 🟢

### F4 — Producer B: component tree → mass (`sync_component_tree_to_mass`, l.131-171) 🟢

Structurally identical to F3, with three substitutions: the aggregate comes from
`component_tree_service.get_aircraft_total_weight_kg(db, uuid)` (also a
function-local import), the source label is `"component_tree"`, and there is no
CG at all — the tree carries positions but the roll-up publishes only mass.

### F5 — CG comparison (`get_cg_comparison`, l.224-249) 🟢

```
design_cg_x = get_effective_assumption_value(db, uuid, "cg_x")   # raises 404 if absent
total, cg_x, cg_y, cg_z = aggregate_weight_items(items)

if cg_x is not None:
    delta_x          = design_cg_x - cg_x
    within_tolerance = abs(delta_x) < CG_TOLERANCE_M          # 0.01 m
else:
    delta_x = within_tolerance = None
```

The sign convention matters: **positive `delta_x` means the design CG is aft of
the component CG**, i.e. the built aircraft is nose-heavy relative to the
requirement. 🟡 (Derived from the subtraction order; not stated in the code.)

### F6 — Design metrics (`get_design_metrics_for_aeroplane`, l.271-282) 🟢

```
import aerosandbox as asb                      # lazy, ADR 0017

mass_kg = get_effective_assumption_value(db, uuid, "mass")
cl_max  = get_effective_assumption_value(db, uuid, "cl_max")
s_ref   = get_s_ref_for_aeroplane(db, uuid)
rho     = asb.Atmosphere(altitude=altitude).density()
return compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
```

`get_s_ref_for_aeroplane` (l.252-268) is the expensive step: it resolves the
whole `AeroplaneSchema`, runs `aeroplane_schema_to_asb_airplane_async` and reads
one attribute. A conversion failure is logged and re-raised as `InternalError`;
`s_ref ≤ 0` becomes a `ValidationError` carrying the remediation *"add wings
first"*.

`compute_design_metrics` then validates five inputs and evaluates BR-MB10.

## Alternative Flows

- **Unknown aeroplane UUID:** `_get_aeroplane` raises `NotFoundError` → **404**
  with a bare `{"detail": "…"}` body. 🟢
- **Weight item id belonging to a different aeroplane:** the query filters on
  both `aeroplane_id` and `id`, so it is a **404**, not a 403. 🟢
- **Unseeded aircraft on a sync:** silent no-op (BR-MB1); the CRUD still
  succeeds. 🟢
- **Empty producer:** `calculated_value` and `calculated_source` are both set to
  `None`; `active_source` is untouched by the auto-switch because there is no
  value to switch to. 🟡
- **Sync raises inside a weight-item write:** `_try_sync_assumptions` catches
  `NotFoundError` and `SQLAlchemyError` only — any *other* exception type would
  propagate and fail the request. 🟡 Narrower than
  `component_tree_service._sync_aircraft_mass`, which catches bare `Exception`.
- **`SQLAlchemyError` inside a weight-item write:** re-raised as `InternalError`
  with the DB message interpolated → **500**. 🟢 One envelope everywhere (`Q-CC-3`). The raw driver message reaches
  the client.
- **Missing `cg_x` / `mass` / `cl_max` assumption row:** `NotFoundError` →
  **404**, even though the sibling resolver in `design_assumptions_service`
  would have returned a `PARAMETER_DEFAULTS` fallback. 🟡
- **ASB unavailable (`linux/aarch64`):** the import inside
  `get_design_metrics_for_aeroplane` raises `ImportError`, which is not a
  `ServiceException`, so `_call` reports **500** *"Unexpected error: …"*. 🟡
- **Non-finite metric result:** none of this module's routers uses
  `NonFiniteSafeJSONResponse`, so a NaN would serialise as invalid JSON. 🟡
  Not reachable with the current validation, since every input is guarded.

## Dependencies

- **`mission-and-sizing` (`design_assumptions_service`)** —
  `update_calculated_value` is the only writer path into the assumption; both
  syncs go through it. Imported **inside** the functions.
- **`mission-and-sizing` (`invalidation_service.mark_ops_dirty`)** — marks
  operating points DIRTY after a mass change.
- **`app.core.events` (`event_bus`, `AssumptionChanged`)** — the propagation
  trigger for retrim and the V_stall recompute.
- **`aeroplane-core` (`component_tree_service`)** — supplies
  `get_aircraft_total_weight_kg`; the reverse direction (`_sync_aircraft_mass`)
  calls back into this module. The cycle is broken on **both** sides by
  function-local imports.
- **`aero-analysis` (`analysis_service.get_aeroplane_schema_or_raise`) +
  `app/converters/model_schema_converters`** — used only to obtain `s_ref`.
- **AeroSandbox** — `asb.Atmosphere` for ρ and the airplane builder for `s_ref`;
  both behind lazy imports (ADR 0017).
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Mass is bottom-up, CG is top-down; the aggregate CG is computed and discarded | `sync_weight_items_to_assumptions:174-186, 205`; ADR 0011 | 🟢 |
| The aggregation takes plain dicts, not ORM rows, so it is pure and reusable | `WeightItemData:24`, `aggregate_weight_items:78` | 🟢 |
| Absent is `None`, never `0.0` — for mass, CG and the verdict alike | `:86-91, 161, 211, 235-239`; ADR 0012 | 🟢 |
| The sync is a best-effort side effect of CRUD, not a transactional partner | `_try_sync_assumptions:57-64`; BR-30 | 🟢 |
| The component tree is the sole producer; `weight_items` is retired | `:162-169` vs `:212-219` | 🟢 (`Q-MB-1`) |
| Import cycles are broken by function-local imports rather than by extracting a mediator | `:143-146, 207-209` | 🟢 |
| Design-metric inputs are rejected, never clamped | `compute_design_metrics:49-58` | 🟢 |
| A whole ASB airplane is built to obtain one scalar | `get_s_ref_for_aeroplane:252-268` | 🟢 |
| The summary route rounds to 6 dp; the pure aggregation does not | `weight_items_service.py:44-51` vs `aggregate_weight_items` | 🟢 |
| The error envelope here is FastAPI's bare `{"detail": …}`, not the `{"error": {code, message, details}}` envelope used by `aeroplane-core` | `weight_items.py:25-35`, `mass_cg.py:32-43` | 🟢 |

## Internal State

The module owns exactly one table, `weight_items`, and one derived write target
that lives in another module's table:

| State | Where | Lifecycle |
|---|---|---|
| The inventory rows | `weight_items` | created/updated/deleted by the CRUD routes; cascade-deleted with the aeroplane; cloned by `versioning` (and their ids remapped into `loading_scenarios.component_overrides`) |
| `mass.calculated_value` + `calculated_source` | `design_assumptions` (owned by `mission-and-sizing`) | overwritten by whichever producer ran last; cleared to `None` when that producer is empty |
| `active_source` | same row | flipped `ESTIMATE → CALCULATED` **once**, by the first sync carrying a value |
| Total mass, CG, Δx, verdict, metrics | nowhere | computed per request and discarded |

## Observability

- `logger.warning("Skipped assumption sync: %s")` in `_try_sync_assumptions` —
  the **only** signal that a weight-item-driven sync failed. 🟢
- `logger.error("DB error in create/update/delete_weight_item: %s")` before the
  `InternalError` re-raise. 🟢
- `logger.error("Error building ASB airplane for s_ref: %s")` in
  `get_s_ref_for_aeroplane`. 🟢
- `logger.error("Unexpected error in mass_cg: %s", exc_info=True)` in the
  `mass_cg` router's `_call`; the `weight_items` router's `_call` does **not**
  log its catch-all branch. 🟢 One envelope and one handler (`Q-CC-3`).
- No metrics, traces or counters. In particular, nothing counts how often the
  two producers overwrite each other, and nothing records that a CG comparison
  came back outside tolerance. 🟡

## Risks and Gaps

- 🟢 **Resolved by `Q-MB-1` (maintainer-answered): the component tree is authoritative and `weight_items` is retired.** Previously two mass producers overwrote one another silently: adding a weight item
  to an aircraft whose mass came from the component tree replaces the tree's
  number without warning, and vice versa. `calculated_source` is the only trace.
- 🟢 **Moot — `weight_items` is retired** (`Q-MB-1`). The same physical battery could be
  counted once in the inventory and once in the tree; nothing detects it.
- 🟡 **Two resolvers for one effective value** — one raising, one defaulting; ADR 0022 requires one (`Q-MB-9` context).
  `mass_cg_service.get_effective_assumption_value` raises `NotFoundError` for a
  missing row; `design_assumptions_service.get_effective_assumption` falls back
  to `PARAMETER_DEFAULTS` and returns `None`. The same aircraft answers
  differently depending on which resolver the caller picked.
- 🟡 **One physical-constants module** (`Q-MB-8`, derived): `g` and `ρ` stop existing in four copies kept in sync by comment. Today `9.81` here, `9.80665` in the powertrain and
  endurance stack.
- 🟢 **The duplicated aggregation disappears with the retirement** (`Q-MB-9`, derived from `Q-MB-1`). It was implemented twice, once rounded (route) and once not
  (pure helper); they are not tested against each other.
- 🟢 **`compute_recommended_cg` becomes the single authority for the top-down CG rule** (`Q-MB-2`, expert consensus endorsed by the maintainer): the formula is exactly Sadraey Eq. 11.18 rearranged and needs no change — it gains the production caller it lacks, and the duplicate implementations are removed. The
  project's central CG rule exists in three places and is read from none of them
  here.
- 🟢 **`cg_y` / `cg_z` gain consumers** (`Q-MB-3`): aileron-trim band and thrust-line arm respectively. Explicitly rejected: feeding `cg_z` into `C_lβ` (30 mm ≙ 0.17° of dihedral — 20× smaller than the wing-position geometry effect already modelled) and pendulum stability (a free body rotates about its own CG, so gravity exerts zero moment there). Previously no consumer read
  the lateral or vertical CG, so a laterally unbalanced aircraft produces no
  signal anywhere.
- 🟢 **One error envelope everywhere** (`Q-CC-3`, maintainer-answered); the per-module mappers are deleted, so raw DB text stops reaching the client through
  `InternalError(message=f"Database error: {exc}")` and the routers'
  `f"Unexpected error: {exc}"`.
- 🟡 **A persistently failing sync has no alerting path** — by design it only
  logs, which sits awkwardly beside ADR 0012's "design warnings, not silent
  fallbacks".
- 🟡 **`_try_sync_assumptions` catches a narrower exception set** than its
  component-tree counterpart, so a `TypeError` inside the assumption service
  would fail a weight-item write but not a tree write.
- 🟡 **`category` is unconstrained in the database.** Only Pydantic enforces the
  five-value set; a direct SQL insert or a future bulk import can store anything.
</content>
