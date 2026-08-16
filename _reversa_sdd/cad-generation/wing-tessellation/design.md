# wing-tessellation — Technical Design

> ## ⚠ This use case is DELETED
>
> **`Q-CG-4` retires the whole wing-tessellation path** — both frontend hooks,
> `ViewerPanel`, the three backend services, the `tessellation_cache` table and
> both endpoints. Measured: `frontend/hooks/useTessellation.ts` has **zero**
> consumers. The live 3D path is construction-plan execution only, which
> tessellates through `construction_plan_service._tessellate_shapes` and does not
> use this cache.
>
> Every gap recorded below is therefore **moot**. `Q-CG-5` follows from this:
> there is no cache to add a unique constraint to and no producer to write for
> the modelled `"fuselage"` component type. Retained as the record of what the
> deleted surface did. **Not** a specification of anything to be built.


> Use-case design, nested under the module [`cad-generation`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🟢 (moot — deleted, `Q-CG-4`) GAP.
> Endpoint contracts in full: [`../contracts.md`](../contracts.md) routes 1–2.
> Sibling slices: [`../wing-export-task/`](../wing-export-task/design.md),
> [`../artifact-serving/`](../artifact-serving/design.md).

## Interface

### Endpoint layer — `app/api/v2/endpoints/cad.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `start_wing_tessellation` | `(aeroplane_id: AeroPlaneID, wing_name: str, db)` | `CadTaskAcceptedResponse` | 202; pickles the schema inline; **no** `check_task_available` (l.150) |
| `get_aeroplane_tessellation` | `(aeroplane_id: AeroPlaneID, db)` | merged scene dict | 404 when the cache is empty (l.199) |
| `_offset_refs` | `(node, offset: int)` | `None` | recursive; rebases every `{ref: N}` (l.79-88) |
| `_expand_bounding_box` | `(bb_min: list[float], bb_max: list[float], shapes: dict)` | `None` | 🟢 (moot — deleted, `Q-CG-4`) early-returns unless the dict has `"min"` **and** `"max"` (l.91-99) |
| `_merge_tessellation_entries` | `(cached_entries)` | `(instances, parts, count, bb)` | deep-copy, recolour, rebase, accumulate (l.101-135) |

### Service layer — `app/services/tessellation_service.py` (385 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_numpy_to_list` | `(obj)` | JSON-safe object | recursive NumPy flattener (l.36-50) |
| `_run_tessellation_worker` | `(wing_schema_pickle, wing_name, wing_scale)` | `dict` | the worker body; runs in the spawned process (l.53-165) |
| `start_tessellation_task` | `(aeroplane_id, wing_name, wing_schema_pickle)` | `dict` | registers `f"{uuid}:tessellation:{wing_name}"` (l.180) and submits |
| `trigger_background_tessellation` | `(aeroplane_id, wing_name, …)` | `None` | 2.0 s debounce + timer/future cancellation (l.240-300); 🟢 (moot — deleted, `Q-CG-4`) no caller |
| `_start_tessellation_and_cache` | `(…)` | `None` | submits, then applies the `is_hash_current` gate (l.366-368) |

### Cache layer — `app/services/tessellation_cache_service.py` (134 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `compute_geometry_hash` | `(data)` | `str` | `sha256(json.dumps(data, sort_keys=True, default=str))[:16]` (l.22-29) |
| `cache_tessellation` | `(db, aeroplane_id, component_type, component_name, tessellation_json, geometry_hash)` | row | upsert via `get_cached(...).first()` |
| `get_cached` | `(db, aeroplane_id, component_type, component_name)` | `Query` | the logical key — 🟢 (moot — deleted, `Q-CG-4`) not unique in the DDL |
| `get_all_cached` | `(db, aeroplane_id)` | `list[row]` | feeds scene assembly |
| `invalidate` | `(db, aeroplane_id, component_type, component_name)` | `int` | bulk `UPDATE … SET is_stale = True`; returns the row count |
| `is_hash_current` | `(db, …, geometry_hash)` | `bool` | the stale-result guard |

### Hook layer — `app/services/tessellation_hooks.py` (56 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `on_wing_changed` | `(db, aeroplane_uuid, wing_name)` | `None` | resolves the aeroplane, invalidates `("wing", name)`, sanitises the name before logging (l.44); ends at the GH #202 TODO (l.52-56) |

### Persistent state

`tessellation_cache` — one row per `(aeroplane_id, component_type,
component_name)`; full column table in [`../design.md`](../design.md) §Data
model. The relevant fields here are `geometry_hash` (the freshness token),
`tessellation_json` (the envelope) and `is_stale` (the invalidation flag).

## Main Flow

### F1 — Request path (`POST .../wings/{name}/tessellation`) 🟢

1. `cad_service.get_aeroplane_with_wings(db, aeroplane_id)` → 404 on an unknown
   aeroplane.
2. `cad_service.get_wing_from_aeroplane(aeroplane, wing_name)` → 404 on an
   unknown wing.
3. `wing_model_to_asb_wing_schema(wing)` → `pickle.dumps(...)` — done **inline
   in the endpoint** (`cad.py:150`), not in the service.
4. `tessellation_service.start_tessellation_task(aeroplane_id, wing_name,
   wing_schema_pickle)` — registers `f"{uuid}:tessellation:{wing_name}"` as
   `PENDING` and submits `_run_tessellation_worker` to the shared pool.
5. Respond **202** with `{aeroplane_id, href}`.

🟢 (moot — deleted, `Q-CG-4`) Step 4 does **not** call `check_task_available`. A second POST for the same
wing overwrites the registry entry, so the first task's completion callback
writes into a slot nobody is polling. The route nevertheless declares `409` in
its `responses` block — a status it can never return.

### F2 — Worker body 🟢

```
wing_schema  = pickle.loads(wing_schema_pickle)
wing_config  = asb_wing_schema_to_wing_config(wing_schema, scale=1000.0)   # m → mm

creator      = WingLoftCreator(creator_id="tessellation",
                               wing_index=wing_name,
                               wing_side="BOTH",
                               wing_config={wing_name: wing_config})
shapes       = creator._create_shape(shapes_of_interest={}, input_shapes={})

part_group, instances = to_ocpgroup(shape,
                                    names=[wing_name],
                                    colors=["#FF8400"],
                                    alphas=[1.0])                          # l.108
params       = {"deviation": 0.1, "angular_tolerance": 0.2}                # l.113
instances, shapes, _ = tessellate_group(part_group, instances, params,
                                        progress=None)
shapes["bb"] = combined_bb(shapes).to_dict()

result = {"data":   {"instances": instances, "shapes": shapes},
          "type":   "data",
          "config": {"theme": "dark", "control": "orbit"},
          "count":  part_group.count_shapes()}
return _numpy_to_list(result)                                              # l.36-50
```

On any exception:

```
return {"status": "FAILURE",
        "error": f"Tessellation failed: {type(err).__name__}"}             # l.162-165
```

Two design notes:

- The worker calls the **private** `_create_shape` hook rather than the public
  `create_shape` template method, bypassing `return_needed_shapes` and the
  root-logger level dance defined in `AbstractShapeCreator.create_shape`
  (`cad_designer/airplane/AbstractShapeCreator.py:49-61`). Harmless today
  because there are no upstream shapes, but it means `WingLoftCreator` is used
  **off-contract** — if the template method ever gains behaviour, this path
  silently skips it. 🟡 The contract being bypassed is specified in
  [`cad-designer-topology`](../../cad-designer-topology/requirements.md).
- `_numpy_to_list` exists because `tessellate_group` returns NumPy arrays and
  scalars, which the SQLAlchemy JSON column cannot serialise. It is applied to
  the **whole** result, recursively. 🟢

### F3 — Completion, hash gate and caching 🟢

```
future.add_done_callback(_on_done)

_on_done:
  tasks[key] = worker_result                         # in-memory registry
  with SessionLocal() as db:                         # own session — outside a request
      cache_tessellation(aeroplane.id, "wing", wing_name,
                         tessellation_json = worker_result,
                         geometry_hash     = geometry_hash or "manual")
      db.commit()
```

The done-callback runs on a pool-management thread in the **parent** process,
outside any request, so it opens its own `SessionLocal` and commits explicitly
rather than relying on `get_db()` (ADR 0009 applies to request scope only). 🟢

For the background path (`_start_tessellation_and_cache`) the callback first
consults `is_hash_current(...)` and **discards** the result when the stored hash
changed while the worker ran (l.366-368) — the newer geometry wins and no row is
written. 🟢

### F4 — Geometry hash 🟢

```
geometry_hash = sha256(
    json.dumps(data, sort_keys=True, default=str).encode()
).hexdigest()[:16]                                   # 64 bits  (l.22-29)

"manual"  when the POST endpoint triggers a run without supplying a hash
```

`sort_keys=True` makes the digest independent of dictionary ordering;
`default=str` makes it tolerant of values `json` cannot encode natively (dates,
Decimals) at the cost of collapsing distinct types with equal `str()`. 🟡 The
16-hex truncation is 64 bits — ample for cache freshness, not a cryptographic
commitment.

### F5 — Cache upsert and the missing constraint 🟢 (moot — deleted, `Q-CG-4`)

```
cache_tessellation:
    row = get_cached(db, aeroplane_id, component_type, component_name).first()
    if row: update in place
    else:   insert

invalidate:
    UPDATE tessellation_cache
       SET is_stale = TRUE
     WHERE aeroplane_id = ? AND component_type = ? AND component_name = ?
    → returns the affected row count
```

The DDL (`alembic/versions/04b8c856eab9_add_tessellation_cache_table.py:24-38`)
creates the FK to `aeroplanes.id` (`ON DELETE CASCADE`) and two indexes — and
**no unique constraint** on the triple the service treats as a key. Two
concurrent `_on_done` callbacks therefore both see `.first() is None` and both
insert; every later read silently picks one of the duplicates. 🟢 (schema) /
🟡 (impact — no incident is recorded).

Note that `aeroplane_id` here is the **integer PK**, not the UUID the routes
use; the callback resolves it from the aeroplane row.

### F6 — Invalidation hook 🟢

```
on_wing_changed(db, aeroplane_uuid, wing_name):
    aeroplane = resolve(aeroplane_uuid)              # no-op when absent
    n = cache_svc.invalidate(aeroplane.id, "wing", wing_name)
    logger.info(..., sanitise(wing_name))            # log-injection guard, l.44
    # TODO(GH #202): trigger background re-tessellation here   (l.52-56)
```

The hook is called from the wing write paths in `wing-design`. It marks stale
and **stops** — there is no producer on the other side, so the entry remains
stale until a client POSTs route 1 again. 🟢 (moot — deleted, `Q-CG-4`)

### F7 — Debounce and cancellation (implemented, unreachable) 🟢/🟢 (moot — deleted, `Q-CG-4`)

```
key = f"{aeroplane_id}:{wing_name}"

trigger_background_tessellation:                     # l.240-300
    cancel pending threading.Timer[key]              # if any
    cancel in-flight Future[key]                     # if any
    Timer(_DEBOUNCE_SECONDS = 2.0, daemon=True,
          function=_start_tessellation_and_cache).start()
```

Both maps are module-level dictionaries in the parent process. Cancelling the
in-flight future is best-effort: `Future.cancel()` only succeeds while the task
is still queued, so a worker that already started runs to completion — and is
then discarded by the hash gate (F3) rather than by the cancellation. 🟡

🟢 (moot — deleted, `Q-CG-4`) Nothing calls `trigger_background_tessellation`. The full lifecycle,
including this dead edge, is in `state-machines.md` §10.

### F8 — Scene assembly 🟢

```
entries = get_all_cached(db, aeroplane.id)
if not entries: → 404

combined_instances = []
parts              = []
bb_min, bb_max     = [+inf]*3, [-inf]*3

for entry in entries:
    shapes = deepcopy(entry.tessellation_json["data"]["shapes"])
    colour = "#FF8400" if entry.component_type == "wing" else "#888888"
    recolour(shapes, colour)                                  # cad.py:121
    _offset_refs(shapes, len(combined_instances))             # cad.py:79-88
    combined_instances.extend(entry.tessellation_json["data"]["instances"])
    _expand_bounding_box(bb_min, bb_max, shapes)              # cad.py:91-99  🟢 (moot — deleted, `Q-CG-4`)
    parts.append(shapes)

scene = {"data": {"shapes": {"version": 3, "name": …, "id": …,
                             "parts": parts,
                             "loc": [[0,0,0],[0,0,0,1]],
                             "bb":  {"min": bb_min, "max": bb_max}},
                  "instances": combined_instances},
         "type": "data", "config": {...},
         "count": total, "is_stale": any(e.is_stale for e in entries)}
```

`_offset_refs` is recursive and rebases **every** `{ref: N}` in the sub-tree by
the number of instances already accumulated, which is why the instance arrays
can simply be concatenated in the same order. 🟢

### F9 — Why the bounding box is always `[0,0,0]`–`[0,0,0]` 🟢 (moot — deleted, `Q-CG-4`)

```
producer  (tessellation_service.py):
    shapes["bb"] = combined_bb(shapes).to_dict()
    → {"xmin","xmax","ymin","ymax","zmin","zmax"}
      (ocp_tessellate.ocp_utils.BoundingBox.to_dict, ocp_utils.py:1217-1225)

consumer  (cad.py:91-99):
    def _expand_bounding_box(bb_min, bb_max, shapes):
        entry_bb = shapes.get("bb")
        if not entry_bb or "min" not in entry_bb or "max" not in entry_bb:
            return                       # ← always taken
        ...

    → the ±inf sentinels are never updated
    → l.130-133 falls back to {"min": [0,0,0], "max": [0,0,0]}
```

🟢 CONFIRMED by inspection of both sides. The fix is one line on either side,
but the **choice matters**: changing the producer invalidates every stored
envelope (see [`tasks.md`](tasks.md) TM-03 at module level), while changing the
consumer keeps the stored format and only touches the merge.

## Alternative Flows

- **Unknown aeroplane or wing:** 404 before any work is scheduled. 🟢
- **Second POST for the same wing:** accepted; the registry entry is silently
  overwritten. 🟢 (moot — deleted, `Q-CG-4`)
- **Worker raises:** the registry records `FAILURE` with the exception **type
  name** only; no cache row is written. 🟢
- **Geometry changed while tessellating (background path):** the finished result
  is discarded by the hash gate; the existing row is untouched, and no error is
  surfaced. 🟢
- **Geometry changed while tessellating (POST path):** the result **is** cached —
  the gate is applied in `_start_tessellation_and_cache`, which the POST path
  does not use. 🟡 INFERRED from the call graph; means an explicit POST can
  cache slightly stale geometry.
- **Duplicate cache rows exist:** `get_cached(...).first()` picks one
  arbitrarily; the other is invisible but still returned by `get_all_cached`,
  so the scene can contain the same wing twice. 🟡
- **Empty cache on read:** 404, not an empty scene. 🟢
- **A cached entry is stale:** it is still merged and served; only the
  `is_stale` flag tells the client. 🟢
- **Debounced trigger cancelled mid-flight:** `Future.cancel()` fails once the
  worker has started; the run completes and is discarded by the hash gate. 🟡
- **Server restarts mid-task:** the registry, the timer map and the future map
  are all lost; the worker process is killed with the pool. 🟡
- **CadQuery absent:** the whole CAD router is not mounted, so neither route
  exists (ADR 0017). 🟢

## Dependencies

- **`wing-design`** — supplies the `WingModel`; its write paths call
  `tessellation_hooks.on_wing_changed`.
- **`aeroplane-core`** — resolves the aeroplane; the cache keys on the integer
  `aeroplanes.id` while the routes use the UUID.
- **`cad-designer-topology`** — `WingLoftCreator` (used through its private
  `_create_shape`), and the millimetre wing-local frame the vertices are
  expressed in.
- **`app/converters/model_schema_converters.py`** —
  `wing_model_to_asb_wing_schema` (parent side) and
  `asb_wing_schema_to_wing_config` (worker side).
- **`ocp_tessellate`** — `to_ocpgroup`, `tessellate_group`, `combined_bb`; its
  `BoundingBox.to_dict()` key set is the root cause of F9.
- **The shared process pool** — owned at [module level](../design.md) §F1.
- **`frontend-workbench`** — the consumer of both envelopes; the rendering
  contract lives there.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Tessellation runs in the shared spawned pool, never on the request thread | `tessellation_service.py` submit path; ADR 0005 | 🟢 |
| The endpoint pickles the schema inline rather than delegating to the service | `cad.py:150` | 🟢 |
| Quality is a fixed constant pair rather than a request parameter | `tessellation_service.py:113` | 🟢 |
| The wing colour is baked into the **cached** envelope and re-applied at merge | `tessellation_service.py:108`; `cad.py:121` | 🟢 |
| Worker error text is the exception type only | `tessellation_service.py:162-165` | 🟢 |
| The envelope is stored in a JSON column, not on disk | `app/models/tessellation_cache.py` | 🟢 |
| Freshness is a content hash, not a timestamp or a version counter | `tessellation_cache_service.py:22-29` | 🟢 |
| A superseded result is discarded rather than cached (background path) | `tessellation_service.py:366-368` | 🟢 |
| Invalidation marks stale; it never re-produces | `tessellation_hooks.py:52-56` (GH #202) | 🟢 |
| The done-callback owns its own session and commit | `_on_done` | 🟢 |
| The merge deep-copies so a read never mutates the cache | `cad.py:101-135` | 🟢 |
| Instance arrays are concatenated and refs rebased, rather than de-duplicated | `cad.py:79-88` | 🟢 |
| The cache's logical key is enforced in code, not in the schema | `alembic/versions/04b8c856eab9_….py:24-38` | 🟢 (intent 🟢 (moot — deleted, `Q-CG-4`)) |
| Producer and consumer of `bb` disagree on key names | `tessellation_service.py` vs `cad.py:91-99` | 🟢 (intent 🟢 (moot — deleted, `Q-CG-4`)) |

## Internal State

- **In-memory, parent process:** the task registry entry
  `f"{uuid}:tessellation:{wing_name}"`, the debounce `threading.Timer` map and
  the in-flight `Future` map, all keyed by `f"{aeroplane_id}:{wing_name}"`. Lost
  on restart; not shared across replicas.
- **Persistent:** one `tessellation_cache` row per component, carrying the
  envelope, its `geometry_hash` and `is_stale`. Lifecycle in
  `state-machines.md` §10:
  `Missing → Fresh | Discarded`, `Fresh → Stale` (hook), `Stale → Fresh`
  (explicit POST only).
- **Derived at read, never persisted:** the merged scene, its `count`, its
  `is_stale` aggregate and its (always degenerate) `bb`.

## Observability

- Task status is queryable at `GET /aeroplanes/{id}/status?task_type=tessellation&wing_name=…`
  for the life of the process. 🟢
- The invalidation hook logs at INFO with a **sanitised** wing name
  (`tessellation_hooks.py:44`). 🟢
- The status endpoint strips `\n`/`\r` from the aeroplane id before logging
  (`cad.py:341`). 🟢
- Worker failures cross the boundary as data, not exceptions, so nothing is
  logged in the worker process at all. 🟡 A failing tessellation leaves **no**
  server-side diagnostic beyond the exception class name — the stack trace dies
  with the worker.
- 🟢 (moot — deleted, `Q-CG-4`) No metrics: no tessellation duration, no cache hit/miss ratio, no count of
  discarded results. A cache that never hits, or a debounce that always
  supersedes, is invisible.

## Risks and Gaps

- 🟢 (moot — deleted, `Q-CG-4`) **The merged bounding box is always degenerate** (F9), so multi-part camera
  fitting is either wrong or silently delegated to per-part bounds.
- 🟢 (moot — deleted, `Q-CG-4`) **No unique constraint** backs the cache key while the service treats it as
  unique; duplicates make `get_cached(...).first()` non-deterministic and can put
  the same wing into a scene twice.
- 🟢 (moot — deleted, `Q-CG-4`) **Background re-tessellation is dead code.** The debounce, cancellation and
  stale-hash machinery is complete and unreachable; a stale entry never
  refreshes itself (GH #202).
- 🟢 (moot — deleted, `Q-CG-4`) **No concurrency guard on the POST path**, so a double-click silently
  orphans the first task; the route advertises a 409 it cannot return.
- 🟢 (moot — deleted, `Q-CG-4`) **Fuselages are never tessellated** — `component_type = "fuselage"` is
  modelled, coloured and invalidatable in principle, with no producer.
- 🟡 **The POST path skips the hash gate.** Only `_start_tessellation_and_cache`
  consults `is_hash_current`, so an explicit POST can cache geometry that
  changed while it ran. Inferred from the call graph, not from an explicit
  comment.
- 🟡 **`WingLoftCreator` is used off-contract** through its private
  `_create_shape`.
- 🟡 **A failing tessellation leaves no stack trace** anywhere — the type-only
  rule protects the client but also blinds the operator.
- 🟡 **Cancellation is best-effort**; a started worker always runs to
  completion and is only discarded afterwards.
- 🟡 **The envelope is millimetres** and nothing in it says so.
