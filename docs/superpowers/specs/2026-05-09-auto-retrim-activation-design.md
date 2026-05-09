# Auto-Retrim Pipeline Activation — Design Spec

**Issue:** #448  
**Epic:** #417 — Operating Point Simulation  
**Date:** 2026-05-09  
**Type:** Bug fix

## Problem

The event-driven invalidation and background auto-retrim pipeline (#438)
is architecturally complete but functionally inactive. `job_tracker.set_trim_function()`
is never called during app startup. When `_debounced_retrim()` fires after
the 2s debounce, it logs "No trim function registered" and returns. OPs
transition DIRTY → COMPUTING → FAILED without any actual retrim.

Additionally:
- `RetrimJob.dirty_op_ids/completed_op_ids/failed_op_ids` are never populated
- Stability is not recomputed after retrim completes

## Design

### Changes

| File | Action | Purpose |
|------|--------|---------|
| `app/services/retrim_service.py` | NEW | Async retrim logic |
| `app/core/background_jobs.py` | MOD | Populate tracking lists |
| `app/main.py` | MOD | Register trim function at startup |

### 1. retrim_service.py

New service module with a single public function:

```python
async def retrim_dirty_ops(aeroplane_id: int) -> None:
```

**Signature matches** `Callable[[int], Awaitable[None]]` expected by
`job_tracker.set_trim_function()`.

**Algorithm:**

1. Open `SessionLocal()` (background jobs run outside request context)
2. Query `AeroplaneModel` by PK → get UUID (trim services need UUID)
3. Query TEDs on the aeroplane's wings to find the pitch control surface
   name (elevator, elevon, or stabilator) — use direct DB query, not
   the OP generator's `_detect_control_capabilities()` (avoid coupling)
4. Query all `OperatingPointModel` where `aircraft_id == aeroplane_id`
   and `status == "DIRTY"`
5. For each dirty OP:
   a. Set `status = "COMPUTING"`, flush
   b. Build `AeroBuildupTrimRequest`:
      - `trim_variable`: detected pitch control name
      - `target_coefficient`: `"Cm"`
      - `target_value`: `0.0`
   c. Call `trim_with_aerobuildup(db, aeroplane_uuid, request)`
   d. On success (`converged=True`): set `status = "TRIMMED"`, store
      aero coefficients in `OP.computed_results` (JSON)
   e. On success (`converged=False`): set `status = "LIMIT_REACHED"`
   f. On exception: set `status = "NOT_TRIMMED"`, log error,
      **continue** with remaining OPs
6. Recompute stability: call `get_stability_summary()` with the first
   TRIMMED OP's parameters and `aerobuildup` solver, then
   `persist_stability_result()`
7. `db.commit()` and `db.close()`

**Solver choice:** Always AeroBuildup (faster, universal, per design doc).

**Edge cases:**
- No pitch control found → log warning, leave all OPs DIRTY, return
- No DIRTY OPs found → return early (no-op)
- Individual OP failure → that OP becomes NOT_TRIMMED, others continue
- Aeroplane not found → raise (caught by `_debounced_retrim()` → FAILED)

### 2. background_jobs.py — tracking list population

Modify `_debounced_retrim()` to populate `RetrimJob` tracking lists:

**Before** calling trim function:
```python
job.dirty_op_ids = [op.id for op in query_dirty_ops(aeroplane_id)]
```

**After** trim function returns successfully:
```python
for op_id in job.dirty_op_ids:
    op = db.query(OperatingPointModel).get(op_id)
    if op.status == "TRIMMED":
        job.completed_op_ids.append(op_id)
    else:
        job.failed_op_ids.append(op_id)
```

This requires `_debounced_retrim()` to open its own DB session for the
tracking queries. The trim function's session is separate (it commits
independently).

### 3. main.py — registration

In the `_combined_lifespan()` async context manager, after
`register_handlers()`:

```python
from app.services.retrim_service import retrim_dirty_ops
from app.core.background_jobs import job_tracker
job_tracker.set_trim_function(retrim_dirty_ops)
```

## Acceptance Criteria

- [ ] `retrim_dirty_ops()` registered at app startup via `set_trim_function()`
- [ ] Geometry change → OPs DIRTY → debounce 2s → OPs auto-retrimmed
- [ ] Assumption change (mass, cg_x) → affected OPs DIRTY → auto-retrim
- [ ] After all OPs trimmed: stability result recomputed and persisted
- [ ] `RetrimJob.dirty_op_ids/completed_op_ids/failed_op_ids` populated
- [ ] `GET /analysis-status` reflects retrim progress accurately
- [ ] Individual OP failure does not block other OPs
- [ ] No pitch control → OPs stay DIRTY with logged warning
- [ ] Unit test: retrim service with mocked DB and trim service
- [ ] Unit test: tracking list population in _debounced_retrim
- [ ] Integration test: geometry change → retrim → stability update

## Out of Scope

- AVL as alternative auto-retrim solver (manual trigger only)
- StabilityComputed event type (future: auto-populate cd0 assumption)
- Per-OP solver preference storage
- Frontend changes (status indicator already works via #438)
