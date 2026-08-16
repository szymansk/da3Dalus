# wing-tessellation

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


> Use-case specification, nested under the module [`cad-generation`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🟢 (moot — deleted, `Q-CG-4`) GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-generation
> (Tessellation, Cache, Scene assembly), `_reversa_sdd/data-dictionary.md`
> §Table `tessellation_cache`, `_reversa_sdd/state-machines.md` §10.

## Overview

`wing-tessellation` turns a persisted wing into the triangulated JSON envelope
the three-cad-viewer renders, caches it per component with a content hash,
marks it stale when the geometry changes, and merges every cached entry of one
aeroplane into a single scene. It is the read path behind the workbench's 3D
view: without the cache the viewer would re-run a multi-second CadQuery loft on
every page load. 🟢

## Responsibilities

- Accept an asynchronous tessellation request for one wing and register it in
  the task registry. 🟢
- Build the wing solid in a worker process and triangulate it with fixed
  quality parameters. 🟢
- Emit a self-contained viewer envelope carrying instances, a shapes tree, a
  render config and a shape count, with every NumPy value flattened. 🟢
- Report a failure as an exception **type name** only. 🟢
- Cache exactly one entry per `(aeroplane, component_type, component_name)`,
  stamped with a canonical geometry hash. 🟢
- Discard a finished result whose geometry changed while it was computing. 🟢
- Mark cached entries stale when a wing is written. 🟢
- Debounce and cancel background re-tessellation requests. 🟢 (unreachable
  today — no caller)
- Merge every cached entry of one aeroplane into one scene, rebasing instance
  references and recolouring by component type. 🟢

**Explicitly NOT this use case's responsibility:** the export blueprint, the
exporter mapping and the archive path (→ [`../wing-export-task/`](../wing-export-task/requirements.md));
the artefact filesystem (→ [`../artifact-serving/`](../artifact-serving/requirements.md));
the process pool itself, which is shared and specified at
[module level](../design.md) §F1; the `WingLoftCreator` geometry
(→ `cad-designer-topology`, frozen per ADR 0002); the wing persistence that
supplies the input (→ `wing-design`); the client-side rendering of the envelope
(→ `frontend-workbench`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-67 — CAD runs in a spawned worker process.** 🟢 *(module-level rule.)*
  Tessellation submits `_run_tessellation_worker` to the shared
  `ProcessPoolExecutor`; it never triangulates on the request thread.
- **BR-CG1 — Everything crossing the process boundary must be picklable.** 🟢
  The endpoint pickles an `AsbWingSchema` and the worker rebuilds
  `asb_wing_schema_to_wing_config(schema, scale=1000.0)`
  (`tessellation_service.py:81-82`).
- **BR-CG2 — The task registry is parent-process, in-memory only.** 🟢 The key
  for this path is `f"{aeroplane_id}:tessellation:{wing_name}"`
  (`tessellation_service.py:180`).
- **BR-CG3 — Export tasks are serialised per aeroplane, nothing else is.** 🟢 (moot — deleted, `Q-CG-4`)
  *This use case is where the omission bites:* `check_task_available` is **not**
  called here, so a second POST for the same wing silently overwrites the
  registry entry and the first task's result becomes unreachable.
- **BR-CG8 — The tessellation envelope is fixed and self-describing.** 🟢
  *(this use case is its owner)*

  ```
  {"data": {"instances": [...], "shapes": {...}},
   "type": "data",
   "config": {"theme": "dark", "control": "orbit"},
   "count": <part_group.count_shapes()>}
  ```

  Fixed quality parameters `deviation = 0.1`, `angular_tolerance = 0.2`
  (`tessellation_service.py:113`); colour `#FF8400`, alpha `1.0` (l.108).
  Every NumPy value passes through `_numpy_to_list` (l.36-50) because
  `tessellate_group` returns arrays the JSON column cannot store.
- **BR-CG9 — Tessellation failures report a type name only.** 🟢
  `{"status": "FAILURE", "error": f"Tessellation failed: {type(err).__name__}"}`
  (l.162-165). No message, no traceback, no filesystem path crosses the process
  boundary.
- **BR-CG10 — The geometry hash is 64 bits of canonical JSON.** 🟢
  `sha256(json.dumps(data, sort_keys=True, default=str))[:16]`
  (`tessellation_cache_service.py:22-29`); the literal `"manual"` when the POST
  endpoint triggers a run without a hash.
- **BR-CG11 — A result whose geometry changed while it computed is
  discarded.** 🟢 `is_hash_current` re-checks the stored hash after the worker
  returns and drops the result rather than caching it
  (`tessellation_service.py:366-368`). No error, no log alarm — the newer
  geometry simply wins.
- **BR-CG12 — Re-tessellation is debounced and cancellable, but nothing calls
  it.** 🟢/🟢 (moot — deleted, `Q-CG-4`) `_DEBOUNCE_SECONDS = 2.0`; a new request cancels both the pending
  `threading.Timer` and the in-flight `Future` for `f"{aeroplane_id}:{wing_name}"`
  (l.240-300). `tessellation_hooks.on_wing_changed` ends in a TODO referencing
  **GH #202** (l.52-56), so a stale entry never refreshes itself.
- **BR-CG13 — The cache key is a logical triple with nothing enforcing it.** 🟢 (moot — deleted, `Q-CG-4`)
  `get_cached(...).first()` treats `(aeroplane_id, component_type,
  component_name)` as unique; the DDL creates only the FK and two indexes
  (`alembic/versions/04b8c856eab9_….py:24-38`).
- **BR-CG14 — Invalidation is wired for wings only.** 🟢 (moot — deleted, `Q-CG-4`) No
  `on_fuselage_changed` exists; `component_type = "fuselage"` is modelled and
  coloured but has no producer. The wing name is sanitised before logging
  (log-injection guard, `tessellation_hooks.py:44`).
- **BR-CG15 — The merged scene rebases every instance reference.** 🟢
  `_merge_tessellation_entries` (`cad.py:101-135`) deep-copies each blob,
  recolours (`#FF8400` for wings, `#888888` otherwise), rebases every `{ref: N}`
  via `_offset_refs` (l.79-88) and accumulates a bounding box. Empty cache →
  **404**.
- **BR-CG16 — The merged bounding box is always degenerate.** 🟢 (moot — deleted, `Q-CG-4`) Producer writes
  `{xmin,xmax,ymin,ymax,zmin,zmax}` (`BoundingBox.to_dict()`,
  `ocp_utils.py:1217-1225`); `_expand_bounding_box` (`cad.py:91-99`) requires
  `"min"` and `"max"` and returns early, so the response falls back to
  `{"min":[0,0,0],"max":[0,0,0]}` (l.130-133).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-WT-01 | Accept a tessellation request for a named wing and answer 202 | Must | `POST /aeroplanes/{id}/wings/{name}/tessellation` → 202 + `CadTaskAcceptedResponse`; unknown aeroplane or wing → 404 |
| RF-WT-02 | Register the task under the tessellation key | Must | The registry holds `f"{uuid}:tessellation:{wing}"` with `status = PENDING` |
| RF-WT-03 | Guard against a concurrent tessellation of the same wing | Must | A second POST does not silently discard the first task (🟢 (moot — deleted, `Q-CG-4`) legacy behaviour does exactly that) |
| RF-WT-04 | Build the wing solid in a worker process at millimetre scale | Must | The worker rebuilds the configuration with `scale = 1000.0` and never receives a `WingConfiguration` |
| RF-WT-05 | Triangulate with the fixed quality pair | Must | `deviation = 0.1` and `angular_tolerance = 0.2` are used for every run |
| RF-WT-06 | Emit the documented envelope | Must | Keys `data.instances`, `data.shapes`, `type == "data"`, `config`, `count` are all present; `count` equals the group's shape count |
| RF-WT-07 | Serialise without NumPy types | Must | The stored JSON contains no NumPy scalar or array |
| RF-WT-08 | Report failures as a type name only | Must | A raising worker yields exactly `"Tessellation failed: <ExceptionClassName>"` |
| RF-WT-09 | Compute a canonical geometry hash | Must | The digest is invariant to key ordering and tolerant of non-JSON types; length is 16 hex chars |
| RF-WT-10 | Store `"manual"` when no hash is supplied | Should | A POST-triggered run stores the literal `"manual"` |
| RF-WT-11 | Upsert exactly one cache row per component | Must | A second tessellation of the same wing updates the row rather than inserting a second one |
| RF-WT-12 | Enforce the cache key at the database level | Must | Two concurrent inserts for the same triple raise instead of duplicating (🟢 (moot — deleted, `Q-CG-4`) no constraint today) |
| RF-WT-13 | Discard a superseded result | Must | With the stored hash changed mid-run, the finished result is not written |
| RF-WT-14 | Mark entries stale on a wing write | Must | `invalidate` flips `is_stale` and returns the affected row count |
| RF-WT-15 | Sanitise the wing name before logging | Must | A name containing `\n` cannot forge a second log line |
| RF-WT-16 | Debounce background re-tessellation by 2.0 s and cancel the predecessor | Should | Two triggers within the window produce one run; the pending timer and the in-flight future are both cancelled |
| RF-WT-17 | Refresh a stale entry without client action | Should | A wing write eventually produces a fresh entry (🟢 (moot — deleted, `Q-CG-4`) not wired — GH #202) |
| RF-WT-18 | Merge every cached entry into one scene | Must | Two cached wings produce two parts; every `{ref: N}` resolves inside the merged instance array |
| RF-WT-19 | Recolour by component type on merge | Must | Wings are `#FF8400`, everything else `#888888` |
| RF-WT-20 | Leave the cache rows untouched on read | Must | The merge deep-copies; the stored blobs are byte-identical afterwards |
| RF-WT-21 | Answer 404 when nothing is cached | Must | An aeroplane with no rows → 404, not an empty scene |
| RF-WT-22 | Report a usable scene bounding box | Should | `bb` reflects the parts' real extent (🟢 (moot — deleted, `Q-CG-4`) always degenerate today) |
| RF-WT-23 | Report staleness on the merged scene | Should | `is_stale` is true when any contributing entry is stale |
| RF-WT-24 | Tessellate fuselages | Won't (today) | Modelled and coloured, but no producer exists |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The viewer reads a cached envelope instead of re-running CadQuery per page load | `tessellation_cache_service.py`; `cad.py` scene assembly | 🟢 |
| Performance | Re-tessellation is debounced by 2.0 s and supersedes its predecessor rather than queueing | `tessellation_service.py:237, 240-300` | 🟢 |
| Performance | Tessellation quality is a fixed constant pair, not negotiated per request | `tessellation_service.py:113` | 🟢 |
| Correctness | A cached envelope always matches the geometry that produced it, or is not cached at all | `tessellation_service.py:366-368` | 🟢 |
| Correctness | A scene read never mutates the cache (deep copy before recolouring) | `cad.py:101-135` | 🟢 |
| Security | Worker error text is the exception **type** only — no message, path or traceback crosses the boundary | `tessellation_service.py:162-165` | 🟢 |
| Security | The wing name is sanitised before it reaches the log | `tessellation_hooks.py:44` | 🟢 |
| Robustness | A tessellation failure never propagates as an exception into the request path; it becomes task state | worker return contract | 🟢 |
| Scalability | Debounce timers and in-flight futures are per-process dictionaries — single-replica by construction | `tessellation_service.py:240-300` | 🟡 |
| Integrity | The cache's logical key is not enforced by a constraint | `alembic/versions/04b8c856eab9_….py:24-38` | 🟢 (moot — deleted, `Q-CG-4`) |

## Acceptance Criteria

```gherkin
Feature: Tessellating a wing

  Scenario: A wing is tessellated and cached
    Given an aeroplane with a wing named "main"
    When I POST /aeroplanes/{id}/wings/main/tessellation
    Then the response status is 202
    And a task is registered under "{id}:tessellation:main" with status PENDING
    When the worker finishes
    Then a cache row exists for (aeroplane, "wing", "main")
    And the stored envelope has type "data" and a non-zero count
    And config equals {"theme": "dark", "control": "orbit"}

  Scenario: The envelope carries no NumPy values
    Given a completed tessellation
    When the envelope is serialised into the JSON column
    Then every value is a plain JSON scalar, list or object

  Scenario: An unknown wing is rejected
    Given an aeroplane with no wing named "ghost"
    When I POST /aeroplanes/{id}/wings/ghost/tessellation
    Then the response status is 404

  Scenario: A failing worker leaks nothing
    Given the worker raises ValueError("/abs/path/secret.dat is missing")
    When the task completes
    Then the status is FAILURE
    And the error text is exactly "Tessellation failed: ValueError"

  Scenario: A second request for the same wing does not discard the first
    Given a tessellation task for wing "main" is already PENDING
    When I POST the same endpoint again
    Then the first task's result stays reachable
    # BR-CG3: the legacy path overwrites the registry entry silently

Feature: Cache integrity

  Scenario: The hash is canonical
    Given two dictionaries with the same content in different key order
    When I compute the geometry hash of each
    Then both digests are identical
    And each is 16 hexadecimal characters long

  Scenario: A POST-triggered run stores the manual sentinel
    Given a tessellation triggered without a geometry hash
    When the result is cached
    Then geometry_hash is the literal "manual"

  Scenario: Re-tessellating updates the existing row
    Given a cache row for (aeroplane, "wing", "main")
    When the wing is tessellated again
    Then exactly one row exists for that triple
    And its updated_at has advanced

  Scenario: A superseded result is discarded
    Given a tessellation is in flight for wing "main"
    When the wing geometry changes before the worker finishes
    Then the finished result is not written to the cache
    And the existing row is left as it was

  Scenario: Concurrent inserts cannot duplicate
    Given two workers finish simultaneously for the same triple
    When both attempt to cache
    Then one insert fails on a unique constraint
    # BR-CG13: no constraint exists today, so both rows are written

Feature: Invalidation

  Scenario: A wing write marks its tessellation stale
    Given a fresh cache entry for wing "main"
    When the wing geometry is written
    Then the entry's is_stale becomes true
    And invalidate reports one affected row

  Scenario: A hostile wing name cannot forge a log line
    Given a wing named "main\nERROR fake entry"
    When the invalidation hook logs
    Then the emitted record contains no injected newline

  Scenario: A stale entry is refreshed automatically
    Given a stale cache entry for wing "main"
    When the debounce window elapses
    Then a fresh envelope replaces it
    # BR-CG12: no caller exists today (GH #202), so it stays stale forever

Feature: Scene assembly

  Scenario: Two cached wings merge into one scene
    Given cached tessellations for wings "main" and "htail"
    When I GET /aeroplanes/{id}/tessellation
    Then both parts appear in one shapes tree
    And every {ref: N} points into the merged instance array
    And both parts are coloured #FF8400

  Scenario: A non-wing component is coloured differently
    Given a cached entry whose component_type is "fuselage"
    When the scene is assembled
    Then that part is coloured #888888

  Scenario: The merge does not mutate the cache
    Given cached tessellations for two wings
    When the scene is assembled
    Then the stored tessellation_json values are byte-identical to before

  Scenario: Nothing cached
    Given an aeroplane with no cached tessellation
    When I GET /aeroplanes/{id}/tessellation
    Then the response status is 404

  Scenario: The scene reports a real bounding box
    Given a cached wing spanning 2000 millimetres in y
    When I GET the merged scene
    Then bb.min and bb.max describe that extent
    # BR-CG16: the key mismatch always answers {min:[0,0,0],max:[0,0,0]}
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Worker build + envelope (RF-WT-04…RF-WT-07) | Must | The workbench 3D view cannot render without it, and the envelope shape is a published contract |
| Type-only failure text (RF-WT-08) | Must | A security boundary: the worker sees filesystem paths and payloads the client must not |
| Cache upsert + canonical hash (RF-WT-09/RF-WT-11) | Must | Rendering takes seconds; the cache is what makes the workbench usable and the hash is what keeps it honest |
| Superseded-result discard (RF-WT-13) | Must | Without it the cache can serve geometry that no longer exists — silently wrong, the worst failure class in this codebase |
| Invalidation on wing write (RF-WT-14) | Must | The only signal a client has that the picture is out of date |
| Scene merge + ref rebasing (RF-WT-18/RF-WT-20/RF-WT-21) | Must | The single read path the frontend uses; a wrong `ref` renders the wrong solid |
| Unique constraint on the cache key (RF-WT-12) | Must | The service already assumes it; without it `.first()` is a coin flip |
| Concurrency guard on the POST path (RF-WT-03) | Must | Today a double-click silently loses a task |
| Log sanitisation (RF-WT-15) | Must | Already implemented; a re-implementation must not drop it |
| Correct bounding box (RF-WT-22) | Should | Camera fit only — parts still render from their own bounds |
| Debounced background refresh (RF-WT-16/RF-WT-17) | Should | A convenience over the explicit POST; fully implemented but unreachable |
| Staleness on the merged scene (RF-WT-23) | Should | A UI hint, not a correctness property |
| `"manual"` sentinel (RF-WT-10) | Could | Only distinguishes hash-less runs in the stored row |
| Fuselage tessellation (RF-WT-24) | Won't (today) | Modelled and coloured, but no producer exists |
| Reproducing the `bb` key mismatch | Won't | A confirmed defect; producer and consumer must agree on one key set |
| Reproducing the missing concurrency guard | Won't | A confirmed defect; a second POST must not silently orphan the first task |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/cad.py` | `start_wing_tessellation` (l.150), `get_aeroplane_tessellation` (l.199), `_offset_refs` (l.79-88), `_expand_bounding_box` (l.91-99), `_merge_tessellation_entries` (l.101-135) | 🟢 |
| `app/services/tessellation_service.py` | `_numpy_to_list` (l.36-50), `_run_tessellation_worker` (l.53-165), `start_tessellation_task` (l.180), `trigger_background_tessellation` (l.240-300), `_start_tessellation_and_cache` (l.366-368) | 🟢 |
| `app/services/tessellation_cache_service.py` | `compute_geometry_hash` (l.22-29), `cache_tessellation`, `get_cached`, `get_all_cached`, `invalidate`, `is_hash_current` | 🟢 |
| `app/services/tessellation_hooks.py` | `on_wing_changed` (l.17-56), log guard (l.44), GH #202 TODO (l.52-56) | 🟢 |
| `app/models/tessellation_cache.py` | `TessellationCacheModel` | 🟢 |
| `alembic/versions/04b8c856eab9_add_tessellation_cache_table.py` | the DDL — FK + two indexes, **no unique constraint** | 🟢 |
| `app/converters/model_schema_converters.py` | `wing_model_to_asb_wing_schema`, `asb_wing_schema_to_wing_config` | 🟢 |
| `cad_designer/airplane/creator/wing/WingLoftCreator.py` | the solid producer, called through its **private** `_create_shape` | 🟢 read-only (ADR 0002) |
| `ocp_tessellate` | `to_ocpgroup`, `tessellate_group`, `combined_bb`, `BoundingBox.to_dict` (`ocp_utils.py:1217-1225`) | 🟢 third-party |
