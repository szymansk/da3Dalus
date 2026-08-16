# wing-tessellation — Implementation Tasks

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


> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`cad-generation`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Tasks marked **DO NOT REPRODUCE** describe a confirmed legacy defect that a
> re-implementation must fix rather than copy.

## Prerequisites

- [ ] Module-level tasks **T-01 → T-04** (the spawned pool, picklable worker
      entry points, the schema hop, the task registry) are in place — this use
      case submits into that pool and registers into that registry.
- [ ] `wing-design` supplies a persisted `WingModel` and calls the invalidation
      hook from its write paths.
- [ ] `app/converters/model_schema_converters.py` provides
      `wing_model_to_asb_wing_schema` and `asb_wing_schema_to_wing_config`.
- [ ] `cad_designer.WingLoftCreator` importable (millimetre world, frozen —
      ADR 0002).
- [ ] `ocp_tessellate` available: `to_ocpgroup`, `tessellate_group`,
      `combined_bb`.
- [ ] A `SessionLocal` factory usable **outside** a request, for the completion
      callback (ADR 0009 covers request scope only).

## Tasks

### Request path

- [ ] **T-WT-01 — The tessellation endpoint.**
  `POST /aeroplanes/{aeroplane_id}/wings/{wing_name}/tessellation` → **202**.
  Resolve the aeroplane (404), resolve the wing (404), convert with
  `wing_model_to_asb_wing_schema`, `pickle.dumps`, hand to
  `start_tessellation_task`.
  - Legacy origin: `app/api/v2/endpoints/cad.py:150`
  - Definition of done: unknown aeroplane and unknown wing both answer 404; a
    valid request answers 202 with `{aeroplane_id, href}`.
  - Confidence: 🟢

- [ ] **T-WT-02 — Register under the tessellation key.**
  `f"{aeroplane_id}:tessellation:{wing_name}"`, status `PENDING`, submitted to
  the shared pool.
  - Legacy origin: `app/services/tessellation_service.py:180`
  - Definition of done: the registry entry exists immediately after the 202, and
    `GET /status?task_type=tessellation&wing_name=…` resolves the same key.
  - Confidence: 🟢

- [ ] **T-WT-03 — Guard concurrent tessellations of the same wing.**
  **DO NOT REPRODUCE** the legacy omission: `check_task_available` is not called
  on this path, so a second POST overwrites the registry entry and the first
  task's completion writes into a slot nobody polls. The route even declares a
  `409` it can never return.
  - Legacy origin: `tessellation_service.py:180` (no guard);
    `cad.py:138-149` (declared 409); `state-machines.md` §11
  - Definition of done: a second POST for the same wing either returns 409 or is
    de-duplicated onto the running future; the declared status codes match
    reality.
  - Confidence: 🟢 (the defect) / 🟢 (moot — deleted, `Q-CG-4`) (which behaviour is wanted)

- [ ] **T-WT-04 — Make `href` point at the status resource.**
  **DO NOT REPRODUCE**: the response carries `href = "/aeroplanes/{id}"` while
  the handler docstring says the result is retrieved via `GET /status`.
  - Legacy origin: `cad.py:150` (response construction)
  - Definition of done: following `href` reaches the poll URL for this task,
    including the `task_type` and `wing_name` query parameters.
  - Confidence: 🟢

### Worker

- [ ] **T-WT-05 — The tessellation worker body.**
  Unpickle → `asb_wing_schema_to_wing_config(schema, scale=1000.0)` →
  `WingLoftCreator(creator_id="tessellation", wing_index=wing_name,
  wing_side="BOTH", wing_config={wing_name: wing_config})` → produce shapes →
  `to_ocpgroup(names=[wing_name], colors=["#FF8400"], alphas=[1.0])` →
  `tessellate_group(params={"deviation": 0.1, "angular_tolerance": 0.2})` →
  `shapes["bb"] = combined_bb(shapes).to_dict()` → assemble the envelope.
  - Legacy origin: `tessellation_service.py:53-165`, constants at l.108, 113
  - Definition of done: a two-station wing tessellates end to end in a worker
    process and the envelope's `count` matches `part_group.count_shapes()`.
  - Confidence: 🟢

- [ ] **T-WT-06 — The envelope shape.**
  `{"data": {"instances", "shapes"}, "type": "data",
  "config": {"theme": "dark", "control": "orbit"}, "count": n}` — exactly these
  keys, in this nesting.
  - Legacy origin: `tessellation_service.py` (worker return)
  - Definition of done: a schema test asserts the key set; the frontend contract
    test consumes it unchanged.
  - Confidence: 🟢

- [ ] **T-WT-07 — `_numpy_to_list`.**
  Recursively flatten every NumPy scalar and array in the result before it
  reaches the JSON column.
  - Legacy origin: `tessellation_service.py:36-50`
  - Definition of done: a result containing nested NumPy arrays serialises with
    the stdlib `json` module without a custom encoder.
  - Confidence: 🟢

- [ ] **T-WT-08 — Type-only failure text.**
  `{"status": "FAILURE", "error": f"Tessellation failed: {type(err).__name__}"}`.
  - Legacy origin: `tessellation_service.py:162-165`
  - Definition of done: a worker raising `ValueError("/abs/path secret")` yields
    exactly `"Tessellation failed: ValueError"` — asserted character for
    character.
  - Confidence: 🟢

- [ ] **T-WT-09 — Use the public Creator entry point.**
  The legacy worker calls the private `_create_shape` hook, bypassing
  `return_needed_shapes` and the root-logger level handling of the public
  `create_shape`. Prefer `create_shape` unless a documented reason forbids it.
  - Legacy origin: `tessellation_service.py` (worker body);
    `cad_designer/airplane/AbstractShapeCreator.py:49-61`
  - Definition of done: the path uses the public method, or a comment records
    why the private hook is required.
  - Confidence: 🟡 INFERRED — harmless today (no upstream shapes).

### Completion and caching

- [ ] **T-WT-10 — Completion callback with its own session.**
  Write the worker result into the registry under the lock, then open a
  `SessionLocal`, cache the envelope and commit. The callback runs outside any
  request, so it cannot use `get_db()`.
  - Legacy origin: `tessellation_service.py` (`_on_done`)
  - Definition of done: the row is committed and visible from a fresh session; a
    failing worker writes `FAILURE` and **no** cache row.
  - Confidence: 🟢

- [ ] **T-WT-11 — `compute_geometry_hash`.**
  `sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]`.
  - Legacy origin: `tessellation_cache_service.py:22-29`
  - Definition of done: identical content in different key order yields the same
    digest; a `datetime` value does not raise; the digest is 16 hex characters.
  - Confidence: 🟢

- [ ] **T-WT-12 — The `"manual"` sentinel.**
  Store the literal `"manual"` as `geometry_hash` when a run is triggered by the
  POST endpoint without a supplied hash.
  - Legacy origin: `tessellation_cache_service.py`; data-dictionary §Table
    `tessellation_cache`
  - Definition of done: a POST-triggered run stores `"manual"`; a background run
    stores a real digest.
  - Confidence: 🟢

- [ ] **T-WT-13 — Cache upsert on the logical key.**
  `cache_tessellation` updates the existing row for
  `(aeroplane_id, component_type, component_name)` or inserts one; `aeroplane_id`
  is the **integer PK**, resolved from the aeroplane row.
  - Legacy origin: `tessellation_cache_service.py` (`cache_tessellation`,
    `get_cached`)
  - Definition of done: a second tessellation of the same wing leaves exactly one
    row with an advanced `updated_at`.
  - Confidence: 🟢

- [ ] **T-WT-14 — Enforce the cache key in the schema.**
  **DO NOT REPRODUCE** the legacy DDL: add a unique constraint on
  `(aeroplane_id, component_type, component_name)` and express the upsert against
  it. Today `get_cached(...).first()` assumes uniqueness that nothing enforces,
  so two concurrent callbacks both insert.
  - Legacy origin: `alembic/versions/04b8c856eab9_add_tessellation_cache_table.py:24-38`
  - Definition of done: a concurrent-insert test raises on the constraint rather
    than producing duplicate rows. See module-level **TM-01** for the data
    migration that must precede it.
  - Confidence: 🟢

- [ ] **T-WT-15 — Discard a superseded result.**
  After the worker returns, re-check `is_hash_current` and drop the result when
  the stored hash changed meanwhile. Apply the gate on **both** the background
  and the POST path.
  - Legacy origin: `tessellation_service.py:366-368`
  - Definition of done: mutating the stored hash mid-run leaves the cache
    untouched; the POST path behaves the same as the background path.
  - Confidence: 🟢 (background) / 🟡 (extending it to the POST path — the legacy
    POST path skips the gate)

### Invalidation

- [ ] **T-WT-16 — `on_wing_changed`.**
  Resolve the aeroplane, `invalidate(aeroplane.id, "wing", wing_name)`, log with
  a **sanitised** wing name.
  - Legacy origin: `tessellation_hooks.py:17-56`, guard at l.44
  - Definition of done: a wing write flips `is_stale` and reports the affected
    row count; a wing name containing `\n` or ANSI escapes cannot forge a log
    line.
  - Confidence: 🟢

- [ ] **T-WT-17 — Bulk invalidation returning a count.**
  `UPDATE tessellation_cache SET is_stale = TRUE WHERE …` on the triple,
  returning the number of affected rows.
  - Legacy origin: `tessellation_cache_service.py` (`invalidate`)
  - Definition of done: invalidating a wing with no cache entry returns `0` and
    does not raise.
  - Confidence: 🟢

- [ ] **T-WT-18 — Wire background re-tessellation to the hook.**
  `_DEBOUNCE_SECONDS = 2.0`; a new trigger cancels the pending
  `threading.Timer` **and** the in-flight `Future` for
  `f"{aeroplane_id}:{wing_name}"`; the hash gate (T-WT-15) applies on
  completion. The legacy mechanism is complete but **has no caller** — the hook
  ends in a TODO referencing GH #202.
  - Legacy origin: `tessellation_service.py:237, 240-300`;
    `tessellation_hooks.py:52-56`
  - Definition of done: two wing writes within 2 s produce one worker run, and a
    stale entry becomes fresh without any client POST.
  - Confidence: 🟢 (mechanism) / 🟢 (moot — deleted, `Q-CG-4`) (whether auto-refresh is wanted — GH #202,
    and what supplies the schema pickle from a write path holding only a
    `WingModel`)

- [ ] **T-WT-19 — Invalidate fuselages too.**
  There is no `on_fuselage_changed`; `component_type = "fuselage"` is modelled
  and coloured but never written or invalidated.
  - Legacy origin: `tessellation_hooks.py` (absent hook); `cad.py:121`
  - Definition of done: a fuselage write invalidates its cache entry, once a
    fuselage producer exists.
  - Confidence: 🟢 (moot — deleted, `Q-CG-4`) GAP — blocked on the module-level fuselage decision (T-34).

### Scene assembly

- [ ] **T-WT-20 — `_merge_tessellation_entries`.**
  Deep-copy each cached `shapes`; recolour `#FF8400` for
  `component_type == "wing"` and `#888888` otherwise; rebase every `{ref: N}`
  with `_offset_refs(shapes, len(combined_instances))`; concatenate the instance
  arrays in the same order; accumulate the bounding box; emit the merged
  envelope with `version: 3`, `parts[]`, `loc: [[0,0,0],[0,0,0,1]]`, `count` and
  `is_stale`.
  - Legacy origin: `cad.py:79-88, 101-135`
  - Definition of done: two cached wings produce two parts whose `{ref}` indices
    resolve inside the merged array; the stored `tessellation_json` values are
    byte-identical afterwards.
  - Confidence: 🟢

- [ ] **T-WT-21 — `_offset_refs` is recursive and total.**
  Every `{ref: N}` anywhere in the sub-tree is rebased — not just the top level.
  - Legacy origin: `cad.py:79-88`
  - Definition of done: a nested `parts` tree three levels deep has every `ref`
    rebased; a fixture asserts none is missed.
  - Confidence: 🟢

- [ ] **T-WT-22 — Make the bounding box agree end to end.**
  **DO NOT REPRODUCE** the key mismatch: the worker writes
  `{xmin,xmax,ymin,ymax,zmin,zmax}` while `_expand_bounding_box` requires
  `{"min","max"}` and returns early, so the scene always answers
  `{"min":[0,0,0],"max":[0,0,0]}`.
  - Legacy origin: `tessellation_service.py` (worker `bb`); `cad.py:91-99,
    130-133`; `ocp_tessellate/ocp_utils.py:1217-1225`
  - Definition of done: for a wing of known extent the merged `bb` reproduces it;
    a regression test pins the producer's key set against the consumer's
    expectation. Decide **which side** changes — changing the producer requires
    module-level **TM-03**.
  - Confidence: 🟢 (the defect) / 🟢 (moot — deleted, `Q-CG-4`) (which side to change)

- [ ] **T-WT-23 — 404 on an empty cache.**
  `GET /aeroplanes/{id}/tessellation` answers 404 when no row exists, rather than
  an empty scene.
  - Legacy origin: `cad.py:199`
  - Definition of done: an aeroplane with no cache rows returns 404 with the
    standard error envelope.
  - Confidence: 🟢

- [ ] **T-WT-24 — Aggregate `is_stale` across contributing entries.**
  The merged scene reports stale when **any** contributing entry is stale.
  - Legacy origin: `cad.py:101-135` (scene assembly)
  - Definition of done: one stale entry among three sets `is_stale = true`; a
    test pins the aggregation rule.
  - Confidence: 🟡 INFERRED — the aggregation was not read line by line.

## Test Tasks

- [ ] **TT-WT-01 — Happy path:** POST, run the worker, assert a cache row and a
      valid envelope (`type == "data"`, non-zero `count`, the exact `config`).
- [ ] **TT-WT-02 — Failure, unknown wing:** POST for a non-existent wing → 404.
- [ ] **TT-WT-03 — Failure, worker raises:** the task ends `FAILURE` with exactly
      `"Tessellation failed: ValueError"` and no cache row is written.
- [ ] **TT-WT-04 — Envelope is JSON-clean:** no NumPy scalar or array survives
      `_numpy_to_list`, asserted with the stdlib encoder.
- [ ] **TT-WT-05 — Millimetre scale:** the worker rebuilds the configuration at
      `scale = 1000.0`; a known 1 m span appears as 1000 units in the envelope.
- [ ] **TT-WT-06 — Hash canonicality:** same content, different key order ⇒ same
      digest; a `datetime` value does not raise; length is 16.
- [ ] **TT-WT-07 — `"manual"` sentinel** is stored for a POST-triggered run.
- [ ] **TT-WT-08 — Upsert:** two tessellations of the same wing leave exactly one
      row with an advanced `updated_at`.
- [ ] **TT-WT-09 — Unique constraint:** two concurrent inserts for the same
      triple raise instead of duplicating.
- [ ] **TT-WT-10 — Superseded result discarded:** mutate the stored hash mid-run;
      the cache is untouched — asserted on both the background and the POST path.
- [ ] **TT-WT-11 — Invalidation:** a wing write flips `is_stale` and returns the
      affected count; invalidating an uncached wing returns `0`.
- [ ] **TT-WT-12 — Log injection:** a wing name containing `\n` and ANSI escapes
      cannot forge a second log record.
- [ ] **TT-WT-13 — Debounce:** two triggers within 2.0 s produce one worker run;
      the pending timer and the in-flight future are both cancelled.
- [ ] **TT-WT-14 — Cancellation is best-effort:** a worker that already started
      completes and is then discarded by the hash gate, not by `Future.cancel()`.
- [ ] **TT-WT-15 — Scene merge:** two cached wings ⇒ two parts, every `{ref}`
      resolving inside the merged instance array.
- [ ] **TT-WT-16 — Deep copy:** after a scene read the stored
      `tessellation_json` values are byte-identical.
- [ ] **TT-WT-17 — Recolouring:** a `"wing"` entry is `#FF8400`, any other
      `component_type` is `#888888`.
- [ ] **TT-WT-18 — Recursive ref rebasing:** a three-level nested `parts` tree
      has every `ref` rebased.
- [ ] **TT-WT-19 — Bounding box:** a wing of known extent yields a merged `bb`
      reproducing it (regression for the key mismatch).
- [ ] **TT-WT-20 — Empty cache:** `GET .../tessellation` → 404.
- [ ] **TT-WT-21 — Staleness aggregate:** one stale entry among three sets
      `is_stale = true`.
- [ ] **TT-WT-22 — Concurrent POSTs:** the second request does not orphan the
      first task's result.

## Suggested Order

1. **T-WT-11 → T-WT-14** first — the hash, the sentinel, the upsert and the
   unique constraint have no dependency on the pool and unblock everything that
   writes. T-WT-14 must land with module-level **TM-01** (de-duplicate first,
   then constrain).
2. **T-WT-05 → T-WT-09** next — the worker and the envelope. T-WT-05 depends on
   module-level T-03 (the schema hop); T-WT-07 blocks T-WT-06 because an
   envelope with NumPy values cannot be stored at all. T-WT-09 is an independent
   contract question.
3. **T-WT-10 → T-WT-15** — completion and the hash gate. T-WT-10 depends on
   T-WT-13; T-WT-15 depends on T-WT-11.
4. **T-WT-01 → T-WT-04** — the request path, once there is something to submit.
   T-WT-03 needs the module-level decision on 409-vs-deduplicate; T-WT-04 is
   trivial and independent.
5. **T-WT-16 → T-WT-18** — invalidation. T-WT-18 is blocked on the GH #202
   decision and on T-WT-15 being in place.
6. **T-WT-20 → T-WT-24** — scene assembly, which needs T-WT-13 (rows to read)
   and T-WT-05 (envelopes to merge). T-WT-22 must be decided together with
   module-level **TM-03**, because fixing the producer invalidates every stored
   envelope.
7. **T-WT-19** last, blocked on the module-level fuselage decision (T-34).

## Pending Gaps (🟢 (moot — deleted, `Q-CG-4`))

- **Which side of the bounding-box contract changes?** Fixing the producer
  invalidates every cached envelope (TM-03); fixing the consumer keeps the
  stored format. Both are one line.
- **Is GH #202 still the plan?** The debounce/cancel/discard machinery is
  complete and unreachable. If auto-refresh is wanted, what supplies the wing
  schema pickle from a write path that holds only a `WingModel`?
- **What should a second tessellation POST for the same wing do** — answer 409
  like exports, or attach to the running future? The route already advertises a
  409 it never returns.
- **Should the POST path apply the stale-hash gate?** Today only the background
  path does, so an explicit POST can cache geometry that changed while it ran.
- **Are fuselages meant to be tessellated?** `component_type = "fuselage"` is
  modelled, coloured and invalidatable in principle, with no producer and no
  hook.
- **How should `is_stale` aggregate across a multi-part scene** — any, all, or
  per-part? The current rule was inferred, not read.
- **Should a tessellation failure leave a server-side diagnostic?** The
  type-only rule protects the client but discards the stack trace entirely,
  leaving the operator nothing to debug with.
