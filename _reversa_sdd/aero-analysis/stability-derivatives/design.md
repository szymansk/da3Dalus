# stability-derivatives — Technical Design

> Focuses on HOW this use case is built, read from the legacy code.
> Parent module design: [`../design.md`](../design.md).
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `get_stability_summary` | `(db, aeroplane_uuid, operating_point, analysis_tool)` | `StabilitySummaryResponse` | runs the solver **and** persists 🟢 |
| `compute_geometry_hash` | `(aeroplane_schema)` | `str` (`sha256[:16]`) | stability-relevant geometry only 🟢 |
| `persist_stability_result` | `(db, aeroplane_id, solver, values…)` | `StabilityResultModel` | upsert on the unique key 🟢 |
| `get_cached_stability` | `(db, aeroplane_uuid)` | `StabilityResultRead \| None` | `status ASC, computed_at DESC` 🟡 |
| `_get_margin_bounds` | `(db, aeroplane_id)` | `(min_pct, max_pct)` | 🔴 always returns the defaults |
| `_find_trim_elevator` | `(deflections)` | `float \| None` | 🔴 substring match on `"elevator"` |
| `_auto_populate_cd0` | `(db, aeroplane_id, result, tool)` | `None` | 🔴 writes **total** CD into `cd0` |

HTTP: `POST /aeroplanes/{id}/stability_summary/{analysis_tool}` and
`GET /aeroplanes/{id}/stability`. Full contract in
[`../contracts.md`](../contracts.md). 🟢

## Main Flow

```
1. resolve the aeroplane → ASB airplane + aeroplane schema
2. resolve_operating_point(...)                     # → operating-point-solve
3. result, _ = analyse_aerodynamics(analysis_tool, op, asb_airplane)
4. extract from the envelope (solver-agnostic by construction):
       Xnp = result.reference.Xnp
       MAC = result.reference.Cref
       Cma = result.derivatives.Cma
       Cnb = result.derivatives.Cnb
       Clb = result.derivatives.Clb
       Xcg = operating_point.xyz_ref[0]
5. min_pct, max_pct = _get_margin_bounds(db, aeroplane_id)     # 🔴 always (5, 25)
6. static_margin      = (Xnp − Xcg) / MAC
   static_margin_pct  = 100 · static_margin
   stability_class    = "stable"   if static_margin_pct > 5
                        "neutral"  if 0 ≤ static_margin_pct ≤ 5
                        "unstable" if static_margin_pct < 0
   cg_range_forward   = Xnp − (max_pct / 100) · MAC
   cg_range_aft       = Xnp − (min_pct / 100) · MAC
   is_statically_stable    = Cma < 0
   is_directionally_stable = Cnb > 0
   is_laterally_stable     = Clb < 0
7. trim_alpha_deg    = operating_point.alpha            (degrees)
   trim_elevator_deg = _find_trim_elevator(deflections) # 🟢 via mixing resolver (Q-WD-1)
8. geometry_hash = compute_geometry_hash(aeroplane_schema)
9. persist_stability_result(...)   # UPSERT on (aeroplane_id, solver), status CURRENT
10. _auto_populate_cd0(...)        # 🔴 BR-14 violation — see Risks
11. return StabilitySummaryResponse
```

## The geometry hash 🟢

```
canonical = {
  "wings":     [ {x_le, y_le, z_le, chord, twist} per x-section, per wing ],
  "fuselages": [ {x_c, width, height} per x-section, per fuselage ],
}
geometry_hash = sha256(json(canonical, sorted keys)).hexdigest()[:16]
```

Deliberately **excluded**: spars, TEDs, servos, turbulators, materials,
construction parts, mass items. None of them can move the neutral point, so
including them would invalidate a perfectly good result on every structural
edit. The 16-hex-character truncation is a storage/readability trade-off, not a
security property. 🟢

## Cached-read ordering 🟡

```sql
SELECT * FROM stability_results
 WHERE aeroplane_id = :id
 ORDER BY status ASC, computed_at DESC
 LIMIT 1
```

`'CURRENT' < 'DIRTY'` lexicographically, so a `CURRENT` row always wins. The
intent is an explicit rank; the implementation is alphabetical luck. Any future
status (`STALE`, `COMPUTING`, `ARCHIVED`) would silently reorder this query.

## Invalidation 🟢 / 🟡

```
WingModel / WingXSecModel / FuselageModel
    after_insert / after_update / after_delete
        → mark stability_results.status = 'DIRTY'
        → mark_ops_dirty(session, aeroplane_id)
        → event_bus.publish(GeometryChanged)
```

🔴 These three models are attached **twice**: once in `stability_events.py`,
once in `avl_geometry_events.py`. Every geometry write therefore publishes
`GeometryChanged` twice and calls `mark_ops_dirty` twice. The operations are
idempotent, so the effect is duplicated work and duplicated log lines rather
than wrong data — but the debounced job scheduler is triggered twice per edit.

## Alternative Flows

- **AVL selected.** The same envelope fields are read from
  `AnalysisModel.from_avl_dict`; the summary code is unchanged. AVL is the only
  solver that could also supply eigenmodes, but nothing consumes them. 🟢
- **`Xnp` is `NaN` or `MAC` is 0.** The derived values become `NaN`/`Inf` and
  are serialised as `null` by `NonFiniteSafeJSONResponse` (ADR 0012) — an honest
  no-value rather than a fabricated number. 🟡
- **No cached row.** `GET …/stability` → 404. 🟢
- **Only a `DIRTY` row.** It is returned **with** `status = "DIRTY"`, so the
  caller can decide. 🟡
- **A dual-role aircraft.** `trim_elevator_deg` is `NULL` because no control
  variable contains the substring `"elevator"`. 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged.

## Dependencies

- **[`../operating-point-solve/`](../operating-point-solve/requirements.md)** —
  resolution, deflection validation and the solver dispatch.
- **`AnalysisModel`** — `reference.Xnp`, `reference.Cref`,
  `derivatives.Cma/Cnb/Clb` (read-only, ADR 0002).
- **`aeroplane-core`** — the aeroplane schema hashed by
  `compute_geometry_hash`.
- **`mission-and-sizing`** — consumes `x_np` and the CG range for the CG /
  stability envelope; owns the SM classification thresholds used *there*
  (which are **different** numbers from this module's `stable/neutral/unstable`
  ladder — see Risks).
- **`platform-core`** — `get_db()` transaction boundary, the event bus,
  `NonFiniteSafeJSONResponse`.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| Read only envelope fields, so the summary is solver-agnostic | `stability_service:289-362` | 🟢 |
| Hash only stability-relevant geometry | `compute_geometry_hash:102-141` | 🟢 |
| One row per `(aeroplane_id, solver)` — comparison across solvers is supported, history is not kept | `uq_stability_aeroplane_solver` | 🟢 |
| Serve a `DIRTY` row rather than 404, and label it | ordering + `status` column | 🟡 |
| Margin bounds nominally configurable | `_get_margin_bounds:225-254` | 🔴 never seeded |
| Trim control found by substring | `_find_trim_elevator` | 🔴 bug #955 |
| `cd0` written from the stability path | `_auto_populate_cd0:257-281` | 🔴 BR-14 violation |

## Internal State

`stability_results` — one row per `(aeroplane_id, solver)`:

| Column | Unit | Source |
|---|---|---|
| `solver` | — | `str(AnalysisToolUrlType)` |
| `neutral_point_x` | m | `result.reference.Xnp` |
| `mac` | m | `result.reference.Cref` |
| `cg_x_used` | m | `operating_point.xyz_ref[0]` |
| `static_margin_pct` | % | derived |
| `stability_class` | — | derived ladder |
| `cg_range_forward` / `cg_range_aft` | m | margin bounds × MAC |
| `Cma` / `Cnb` / `Clb` | — | `result.derivatives` |
| `trim_alpha_deg` / `trim_elevator_deg` | deg | OP + deflections 🔴 |
| `is_*_stable` (×3) | bool | sign tests, default `False` |
| `computed_at` | datetime(tz) | `now()` |
| `status` | `CURRENT` \| `DIRTY` | listeners |
| `geometry_hash` | str(16) | `compute_geometry_hash` |

## Observability

- `geometry_hash` + `computed_at` + `cg_x_used` make each row self-describing:
  a reader can tell **when**, **at which CG** and **against which geometry** the
  verdict was produced. 🟢
- `status` distinguishes a fresh verdict from a stale one without deleting the
  stale one. 🟢
- 🔴 There is no record of **which control** produced `trim_elevator_deg`, so a
  `NULL` is indistinguishable from "no pitch control exists" and from
  "the name did not match" (#955).
- 🔴 Nothing records that `cg_range_*` was computed from defaults rather than
  from configured bounds.

## Risks and Gaps

- 🔴 **`_auto_populate_cd0` writes total CD into the `cd0` assumption.** Direct
  BR-14 / ADR 0004 violation with silent downstream consequences: every consumer
  of `cd0` (speed polar, matching chart, V-n, endurance, spar sizing) reads a
  drag value that includes induced drag. Because it fires on a different trigger
  from the recompute, the corruption is intermittent.
- 🔴 **`_find_trim_elevator` cannot match gh-772 mixing names** (#955), so
  `trim_elevator_deg` is `NULL` on precisely the configurations (V-tail, elevon)
  where the elevator-authority question is hardest.
- 🔴 **`min_static_margin` / `max_static_margin` are never seeded**, so the
  5 % / 25 % CG-range bounds present as configurable and are not.
- 🔴 **Duplicate listener registration** fires `GeometryChanged` and
  `mark_ops_dirty` twice per geometry write.
- 🟡 **Two different SM ladders coexist.** This module classifies
  `stable > 5 % / neutral 0–5 % / unstable < 0`, while
  `loading_scenario_service` (→ `mission-and-sizing`) classifies
  `error < 2 % / warn < target / ok ≤ 20 % / warn ≤ 30 % / error above`. Both are
  legitimate for their purpose, but the same aircraft can be "stable" here and
  "warn" there. Nothing documents the relationship.
- 🟡 **The `status ASC` ordering is alphabetical**, not an explicit rank.
- 🟡 **Nothing verifies the stored `geometry_hash` on read** — it is recorded but
  the read path does not recompute and compare, so a caller must do it.
- 🔴 **No dynamic stability.** Eigenmodes / Dutch-roll / phugoid damping are not
  computed anywhere, although AVL can produce them and `dutch_role_start` exists
  as an operating-point target.
