# Implementation Plan: Neutral Point & Static Margin (#421)

## Task Structure

8 tasks in 3 batches. Batch 1 (tasks 1-3) can run in parallel.
Batch 2 (tasks 4-6) depends on batch 1. Batch 3 (tasks 7-8) depends
on batch 2.

---

## Batch 1: Foundation (parallel)

### Task 1: StabilityResultModel + Migration

**Files:** `app/models/stability_result.py` (new), `alembic/versions/...`

**RED:**
- Test `StabilityResultModel` can be created, queried, upserted
- Test unique constraint on `(aeroplane_id, solver)`
- Test cascade delete when aeroplane is deleted
- Test `AeroplaneModel.stability_results` relationship

**GREEN:**
- Create `StabilityResultModel` with all columns from spec D1
- Add `stability_results` relationship to `AeroplaneModel`
- Generate Alembic migration (down_revision: `b3c4d5e6f7a8`)

**REFACTOR:** Ensure model follows existing patterns from `DesignAssumptionModel`.

### Task 2: Pure Computation Functions

**Files:** `app/services/stability_service.py` (extend)

**RED:**
- Test `classify_stability(margin_pct)`: >5→stable, 0-5→neutral, <0→unstable, None→None
- Test `compute_cg_range(np_x, mac, min_margin, max_margin)`: forward/aft limits
- Test `compute_cg_range` with edge cases: mac=0, None inputs
- Test `compute_geometry_hash(plane_schema)` produces stable, deterministic hash
- Test hash changes when geometry changes

**GREEN:**
- `classify_stability(static_margin_pct: float | None) -> str | None`
- `compute_cg_range(np_x, mac, min_margin=5.0, max_margin=25.0) -> tuple[float, float]`
- `compute_geometry_hash(plane_schema) -> str`

**REFACTOR:** Keep functions pure — no DB access.

### Task 3: Stability Result Schemas

**Files:** `app/schemas/stability.py` (extend)

**RED:**
- Test `StabilityResultRead` round-trips from model attributes
- Test `StabilitySummaryResponse` extended fields serialize correctly
- Test `StabilityResultRead` with None optional fields

**GREEN:**
- Add `StabilityResultRead(BaseModel)` with all DB fields + `from_attributes`
- Extend `StabilitySummaryResponse` with: `static_margin_pct`, `stability_class`,
  `cg_range_forward`, `cg_range_aft`, `mac`, `status`

**REFACTOR:** Ensure field descriptions match spec.

---

## Batch 2: Integration (parallel, depends on Batch 1)

### Task 4: Persistence & Caching Service

**Files:** `app/services/stability_service.py` (extend)

**RED:**
- Test `persist_stability_result()` creates new row
- Test `persist_stability_result()` upserts existing row (same solver)
- Test `get_cached_stability()` returns latest CURRENT result
- Test `get_cached_stability()` returns None when no results
- Test `mark_stability_dirty()` sets all results to DIRTY
- Test cd0 auto-population after AeroBuildup result

**GREEN:**
- `persist_stability_result(db, aeroplane_id, solver, summary, mac, geometry_hash)`
- `get_cached_stability(db, aeroplane_id) -> StabilityResultRead | None`
- `mark_stability_dirty(db, aeroplane_id)`
- `_auto_populate_cd0(db, aeroplane_id, result)` — update design_assumptions

**REFACTOR:** Extract upsert logic to helper.

### Task 5: API Endpoints

**Files:** `app/api/v2/endpoints/aeroanalysis.py` (extend)

**RED:**
- Test `POST .../stability_summary/{tool}` returns extended response with CG range
- Test `POST .../stability_summary/{tool}` persists to stability_results
- Test `GET .../stability` returns cached result
- Test `GET .../stability` returns 404 when no cached result
- Test `GET .../stability` returns DIRTY status after geometry change

**GREEN:**
- Extend `get_stability_summary` to persist result and return extended fields
- Add `GET /v2/aeroplanes/{id}/stability` endpoint

**REFACTOR:** Keep endpoint thin — all logic in service.

### Task 6: Geometry Change Events

**Files:** `app/models/stability_events.py` (new)

**RED:**
- Test wing insert marks stability dirty
- Test wing update marks stability dirty
- Test fuselage update marks stability dirty
- Test no crash when no stability results exist (no-op)

**GREEN:**
- SQLAlchemy event listeners on WingModel, WingXSecModel, FuselageModel
- Follow `avl_geometry_events.py` pattern exactly
- Call `mark_stability_dirty()` on insert/update/delete

**REFACTOR:** Share event registration pattern with avl_geometry_events.

---

## Batch 3: External Integration (depends on Batch 2)

### Task 7: MCP Tools

**Files:** `app/mcp_server.py` (extend)

**RED:**
- Test `get_stability` MCP tool returns cached result
- Test `compute_stability` MCP tool triggers computation
- Test tools appear in MCP tool list

**GREEN:**
- `get_stability(aeroplane_id)` — calls `get_cached_stability()`
- `compute_stability(aeroplane_id, solver)` — calls `get_stability_summary()`

**REFACTOR:** Follow existing MCP tool patterns.

### Task 8: Integration Tests

**Files:** `app/tests/test_stability_integration.py` (new)

Full end-to-end flow:
1. Create aeroplane with wings
2. Seed design assumptions
3. POST stability_summary → verify persisted + extended response
4. GET stability → verify cached result matches
5. Modify wing → verify status = DIRTY
6. POST stability_summary again → verify status = CURRENT
7. Verify cd0 auto-populated (AeroBuildup only)

---

## File Impact Summary

| File | Action |
|------|--------|
| `app/models/stability_result.py` | **New** — SQLAlchemy model |
| `app/models/stability_events.py` | **New** — geometry event listeners |
| `app/models/aeroplanemodel.py` | **Edit** — add relationship |
| `app/schemas/stability.py` | **Edit** — extend schemas |
| `app/services/stability_service.py` | **Edit** — add persistence + helpers |
| `app/api/v2/endpoints/aeroanalysis.py` | **Edit** — add GET, extend POST |
| `app/mcp_server.py` | **Edit** — add 2 tools |
| `alembic/versions/...` | **New** — migration |
| `app/tests/test_stability_result_model.py` | **New** — model tests |
| `app/tests/test_stability_service.py` | **Edit** — add new tests |
| `app/tests/test_stability_endpoints.py` | **New** — endpoint tests |
| `app/tests/test_stability_events.py` | **New** — event tests |
| `app/tests/test_stability_integration.py` | **New** — e2e tests |

## Parallelization Strategy

```
Batch 1 (3 parallel subagents):
  ├─ Subagent A: Task 1 (model + migration)
  ├─ Subagent B: Task 2 (pure computation)
  └─ Subagent C: Task 3 (schemas)

Batch 2 (3 parallel subagents):
  ├─ Subagent D: Task 4 (persistence service)
  ├─ Subagent E: Task 5 (endpoints)
  └─ Subagent F: Task 6 (events)

Batch 3 (2 parallel subagents):
  ├─ Subagent G: Task 7 (MCP tools)
  └─ Subagent H: Task 8 (integration tests)
```
