# component-tree-mass-sync — Technical Design

> Use-case design, nested under the module [`mass-and-balance`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> The tree-side roll-up it consumes:
> [`../../aeroplane-core/weight-rollup/design.md`](../../aeroplane-core/weight-rollup/design.md).

## Interface

### The two producers 🟢

| Symbol | Signature | Line | Aggregate source | `calculated_source` |
|---|---|---|---|---|
| `sync_weight_items_to_assumptions` | `(db, aeroplane_uuid) -> None` | 174 | `aggregate_weight_items` over `weight_items` | `"weight_items"` |
| `sync_component_tree_to_mass` | `(db, aeroplane_uuid) -> None` | 131 | `component_tree_service.get_aircraft_total_weight_kg` | `"component_tree"` |

Both return `None`, raise only `NotFoundError`, and are invoked exclusively from
a best-effort wrapper.

### The two call sites 🟢

| Wrapper | File | Catches | Log | Triggers |
|---|---|---|---|---|
| `_try_sync_assumptions` | `weight_items_service.py:57-64` | `(NotFoundError, SQLAlchemyError)` | `logger.warning` | weight-item create / update / delete |
| `_sync_aircraft_mass` | `component_tree_service.py:362-378` | bare `Exception` | `logger.exception` | tree create / update / delete / move |

### The write target 🟢

`design_assumptions` row `(aeroplane_id, parameter_name="mass")`:

| Column | Written by this use case | Note |
|---|---|---|
| `calculated_value` | **yes** | kg, or `None` when the producer is empty |
| `calculated_source` | **yes** | `"weight_items"` \| `"component_tree"` \| `None` |
| `active_source` | **once**, ESTIMATE → CALCULATED | via `auto_switch_source=True` |
| `estimate_value` | never | the user's design intent (ADR 0010) |
| `divergence_pct` / `divergence_level` | indirectly | recomputed by `update_calculated_value` |
| `cg_x` (a different row) | **never** | ADR 0011 / gh-465 |

## Main Flow

### F1 — Producer A: weight items (`sync_weight_items_to_assumptions`, l.174-221) 🟢

```
aeroplane = _get_aeroplane(db, aeroplane_uuid)                    # NotFoundError

mass_row_exists = SELECT parameter_name FROM design_assumptions
                  WHERE aeroplane_id = aeroplane.id AND parameter_name = 'mass'
                  LIMIT 1
if mass_row_exists is None:
    return                                                        # unseeded: no-op

rows  = SELECT * FROM weight_items WHERE aeroplane_id = aeroplane.id
items = [{"mass_kg":…, "x_m":…, "y_m":…, "z_m":…} for r in rows]
total_mass, _cg_x, _cg_y, _cg_z = aggregate_weight_items(items)   # CGs DISCARDED

from app.core.events import AssumptionChanged, event_bus          # local imports
from app.services.design_assumptions_service import update_calculated_value
from app.services.invalidation_service import mark_ops_dirty

source = "weight_items" if total_mass is not None else None
update_calculated_value(db, aeroplane_uuid, "mass", total_mass, source,
                        auto_switch_source=True)
mark_ops_dirty(db, aeroplane.id)
event_bus.publish(AssumptionChanged(aeroplane_id=aeroplane.id,
                                    parameter_name="mass"))
```

The probe (step 2) selects a single column, so it is an existence check rather
than a row load. The three discarded CG bindings are the code's literal
statement of ADR 0011. 🟢

### F2 — Producer B: component tree (`sync_component_tree_to_mass`, l.131-171) 🟢

Identical skeleton, three substitutions:

```
from app.services.component_tree_service import get_aircraft_total_weight_kg
...
total_kg = get_aircraft_total_weight_kg(db, aeroplane_uuid)       # None for empty
source   = "component_tree" if total_kg is not None else None
```

and no CG at all — the roll-up publishes a scalar. Note the import list here
sits at the **top of the function** (`:143-146`) rather than mid-body as in F1;
functionally equivalent, stylistically inconsistent. 🟡

### F3 — The `None` contract 🟢

```
producer empty  ->  aggregate is None
                ->  source is None
                ->  update_calculated_value(..., None, None, auto_switch_source=True)
                ->  calculated_value = NULL, calculated_source = NULL
                ->  effective_value falls back to estimate_value
```

This is why both aggregates were written to return `None` rather than `0.0`
(`get_aircraft_total_weight_kg:381-403`, `aggregate_weight_items:86-91`). A `0.0`
here would assert a zero-mass aircraft to every downstream sizing surface. 🟢

### F4 — Auto-switch (BR-25, delegated) 🟢

`update_calculated_value(..., auto_switch_source=True)` flips `active_source`
from ESTIMATE to CALCULATED **only** on the first calculated value and never for
a design-choice parameter. `mass` is not a design choice, so the flip applies.
The logic lives in `design_assumptions_service`; this use case only opts in.

### F5 — Propagation (step 5) 🟢

```
mark_ops_dirty(db, aeroplane.id)                     # operating points -> DIRTY
event_bus.publish(AssumptionChanged(aeroplane.id, "mass"))
```

`AssumptionChanged(mass)` is consumed by `assumption_compute_service`, which
retrims and recomputes V_stall. Both side effects fire unconditionally at the
end of a successful sync — including the sync that wrote `None`. 🟡 So deleting
the last weight item triggers the same full recompute as adding one.

### F6 — The two wrappers 🟢

```
# component_tree_service.py:362-378
def _sync_aircraft_mass(db, aeroplane_uuid):
    try:
        from app.services import mass_cg_service          # lazy: breaks the cycle
        mass_cg_service.sync_component_tree_to_mass(db, aeroplane_uuid)
    except Exception:
        logger.exception(...)                             # swallowed by design

# weight_items_service.py:57-64
def _try_sync_assumptions(db, aeroplane_uuid):
    try:
        from app.services.mass_cg_service import sync_weight_items_to_assumptions
        sync_weight_items_to_assumptions(db, aeroplane_uuid)
    except (NotFoundError, SQLAlchemyError) as exc:
        logger.warning("Skipped assumption sync: %s", exc)
```

Same intent, different blast radius: a `TypeError` inside the assumption service
is swallowed on the tree path and **propagates** on the weight-item path,
failing that write with a 500. 🟡

## Alternative Flows

- **Unknown aeroplane UUID:** `NotFoundError` from `_get_aeroplane`; both
  wrappers catch it (it is in the narrow tuple), so the CRUD succeeds and a
  warning is logged. 🟢
- **Aircraft not seeded:** step 2 returns; nothing is written, no event fires.
  🟢 Note the *absence* of an event here — a mass change on an unseeded aircraft
  is invisible until `seed_defaults` runs.
- **Producer empty:** F3 — value and source cleared, event still published. 🟢
- **Both producers populated:** whichever sync ran last wins; the other's number
  is gone with no warning. 🟢 One producer (`Q-MB-1`) — BR-MB4 resolved.
- **`update_calculated_value` raises:** on the tree path swallowed; on the
  weight-item path swallowed only if it is a `SQLAlchemyError`. 🟡
- **`mark_ops_dirty` or `event_bus.publish` raises:** same asymmetry, and the
  `calculated_value` write has already happened — the assumption is updated but
  🟡 the recompute never fires, leaving operating points silently stale. 🔴
- **Caller's transaction rolls back afterwards:** the assumption write rolls back
  with the CRUD (ADR 0009), but the **event has already been published**.
  🟡 Whether the event bus is transactional is not visible from this module. 🔴
- **Concurrent syncs (two requests, same aircraft):** no locking; SQLite's
  `busy_timeout=30000` and WAL make it unlikely to error, but the last writer
  still wins. 🟡

## Dependencies

- **`mission-and-sizing` (`design_assumptions_service.update_calculated_value`)**
  — the single write path into the assumption, including the auto-switch and the
  divergence recomputation.
- **`mission-and-sizing` (`invalidation_service.mark_ops_dirty`)** — operating
  point invalidation.
- **`platform-core` (`app.core.events`)** — `event_bus`, `AssumptionChanged`.
- **`aeroplane-core` (`component_tree_service`)** — supplies
  `get_aircraft_total_weight_kg` **and** hosts the reverse call
  `_sync_aircraft_mass`. The mutual dependency is resolved by function-local
  imports on both sides. 🟢
- **[`weight-items`](../weight-items/design.md)** — the other call site.
- **[`cg-mass-computation`](../cg-mass-computation/design.md)** — supplies
  `aggregate_weight_items`.
- **ADR 0010** (estimate/calculated duality), **ADR 0011** (`cg_x` untouched),
  **ADR 0012** (`None` not `0.0`), **ADR 0009** (transaction boundary).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Two producers write one column with no arbitration | `:162-169` vs `:212-219` | 🟢 (a 🔴 consequence) |
| The sync is a best-effort side effect, never a transactional partner of the CRUD | `component_tree_service.py:362-378`, `weight_items_service.py:57-64` | 🟢 |
| An unseeded aircraft is a no-op rather than an error | `:149-158, 189-198` | 🟢 |
| An empty producer clears both value and source instead of writing zero | `:161, 211` | 🟢 |
| `auto_switch_source=True` is a documented UX opinion, not a technical necessity | docstring `:174-186` | 🟢 |
| The aggregate CG is computed and deliberately discarded | `:205` | 🟢 |
| Both service↔service cycles are broken by function-local imports | `:143-146, 207-209`, `component_tree_service.py:364` | 🟢 |
| The event fires even when the written value is `None` | `:170-171, 220-221` | 🟢 |
| The two wrappers catch different exception sets | `except Exception` vs `except (NotFoundError, SQLAlchemyError)` | 🟢 (a 🟡 inconsistency) |

## Internal State

This use case owns **no** table. Its entire effect is three columns of one row
in another module's table, plus two fire-and-forget side effects:

```
design_assumptions[aeroplane_id, "mass"]
    calculated_value   <- producer aggregate  (kg | NULL)
    calculated_source  <- "weight_items" | "component_tree" | NULL
    active_source      <- CALCULATED, once

operating_points   -> marked DIRTY
event_bus          -> AssumptionChanged(aeroplane_id, "mass")
```

The value is therefore **not idempotent across producers**: replaying the same
sequence of edits in a different order yields a different `calculated_source`
and possibly a different `calculated_value`. 🟡

## Observability

- `logger.exception(...)` in `_sync_aircraft_mass` — the only trace of a
  swallowed tree-side failure. 🟢
- `logger.warning("Skipped assumption sync: %s", exc)` in
  `_try_sync_assumptions` — the inventory-side equivalent, at a lower level. 🟢
- No log line at all on the **success** path, so there is no way to reconstruct
  which producer last won from the logs — only from `calculated_source` in the
  database. 🟡
- No counter, metric or user-visible warning for: a swallowed failure, a
  producer collision, or an event published on a transaction that later rolled
  back. 🟡

## Risks and Gaps

- 🟢 **One producer: the component tree** (`Q-MB-1`). Previously a silent collision: Two bottom-up estimates of the same
  aircraft overwrite each other; only `calculated_source` records the winner and
  nothing surfaces it. This is the single most consequential gap in the module —
  it can change the mass driving every sizing surface without any user action on
  the mass itself.
- 🟢 **Moot with the retirement** (`Q-MB-1`): `weight_items` has no `component_id`,
  so the same battery can appear in both producers; whichever wins reports its
  own partial total as *the* aircraft mass.
- 🟡 **A failing sync emits a `DesignWarning`** (`Q-AC-7`, derived from `P-WARN-0`); previously invisible outside the log — which sits
  awkwardly beside ADR 0012's "design warnings, not silent fallbacks".
- 🟡 **A failure *after* `update_calculated_value`** (in `mark_ops_dirty` or the
  publish) leaves the assumption updated and the recompute unfired, so operating
  points stay stale while the mass has changed.
- 🟡 **The event is published inside a transaction that may roll back.** Nothing
  in this module ties the publish to the commit.
- 🟢 **The tree carries position** (`component_tree.pos_x/y/z`; consumed by `Q-MB-3`/`Q-MB-4`) — what is missing is data, not schema. Previously:, so an aircraft built entirely
  in the component tree has no aggregate CG and the comparison endpoint returns
  `null` with no explanation.
- 🟡 **The two wrappers are not symmetric**, so identical faults produce
  different outcomes depending on which producer triggered them.
- 🟡 **An empty-producer sync triggers a full downstream recompute** — deleting
  the last weight item is as expensive as adding one.
- 🟡 **No concurrency control.** Two simultaneous edits on one aircraft race for
  the same column.
</content>
