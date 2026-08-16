# weight-items — Implementation Tasks

> ## ⚠ This use case is RETIRED
>
> **`Q-MB-1` (maintainer-answered) makes the component tree the sole mass
> authority; `weight_items` becomes a read-only view and is retired.** Every
> defect recorded below — the missing `component_id`, the unconstrained
> `category`, the duplicated aggregation, the two "empty" conventions, the raw
> driver text in 500 bodies — is **moot**, because the table and its routes go
> away rather than being fixed. `Q-MB-10` states this explicitly: no CHECK is
> added, and the closed-set question moves to `component_tree.node_type`, which
> does get one (`Q-CC-9`).
>
> Retained as the record of what the retired surface did, so a migration can map
> its data onto tree nodes. **Not** a specification of anything to be built.


> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `aeroplanes` table with a public `uuid` column and an integer PK.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` with `NotFoundError` and `InternalError`.
- [ ] `mass_cg_service.sync_weight_items_to_assumptions` available **or
      stubbed** — the use case must work when it raises
      ([`../component-tree-mass-sync/tasks.md`](../component-tree-mass-sync/tasks.md)).

## Tasks

- [ ] **T-01 — `weight_items` table + relationship.**
  `aeroplane_id` (Integer FK → `aeroplanes.id`, `ON DELETE CASCADE`, indexed),
  `name`, `mass_kg`, `x_m`/`y_m`/`z_m` (default `0.0`), `description`,
  `category` (default `"other"`). `AeroplaneModel.weight_items` with
  `cascade="all, delete-orphan"`, `order_by=WeightItemModel.id`.
  - Legacy origin: `app/models/aeroplanemodel.py:798`
  - Definition of done: deleting the aeroplane removes every item (assert at the
    SQL level, not only through the ORM session); the list route returns items
    in id order.
  - Confidence: 🟢

- [ ] **T-02 — Schemas and the category vocabulary.**
  `WEIGHT_CATEGORIES = {"electronics","battery","structural","payload","other"}`;
  `WeightItemWrite(name: str min_length=1, mass_kg: float ge=0, x_m/y_m/z_m:
  float = 0.0, description: str | None = None, category: str = "other")`;
  `WeightItemRead = Write + id: int`; `WeightSummary(items, total_mass_kg,
  cg_x_m, cg_y_m, cg_z_m)` with the three CG fields nullable.
  - Legacy origin: `app/schemas/weight_item.py:8`
  - Definition of done: `mass_kg=-0.5`, `name=""` and `category="fuel"` are each
    422; the DB column stays a plain `String` (reproduce the legacy — the
    constraint decision is an open gap).
  - Confidence: 🟢

- [ ] **T-03 — `_get_aeroplane` and `_item_to_schema`.**
  UUID → row with `NotFoundError(entity="Aeroplane", resource_id=uuid)`; the
  mapper builds `WeightItemRead` field by field (no `from_attributes`).
  - Legacy origin: `app/services/weight_items_service.py:16-33`
  - Definition of done: an unknown UUID raises before any item query runs.
  - Confidence: 🟢

- [ ] **T-04 — `list_weight_items` with the inline 6-dp summary.**
  Total and three CGs recomputed over the mapped read objects; `if total > 0`
  guards the CGs; `total_mass_kg = round(total, 6)` even when zero.
  - Legacy origin: `app/services/weight_items_service.py:36-54`
  - Definition of done: empty inventory ⇒ `total_mass_kg == 0` **and** three
    `null` CGs — a test must fail if the CGs ever become `0.0` or the total
    becomes `null`. A 0.4/0.6 kg fixture reproduces `cg_x_m == 0.16`.
  - Confidence: 🟢

- [ ] **T-05 — Aeroplane-scoped single-item lookup.**
  Every single-item query filters `aeroplane_id == aeroplane.id AND id ==
  item_id`; a miss raises `NotFoundError(entity="WeightItem",
  resource_id=item_id)`.
  - Legacy origin: `app/services/weight_items_service.py:85-89, 100-104, 123-127`
  - Definition of done: a test creates the same item id under two aeroplanes and
    asserts each request sees only its own; a cross-aeroplane GET is 404 and
    discloses nothing about the other row.
  - Confidence: 🟢

- [ ] **T-06 — `create_weight_item`.**
  `WeightItemModel(aeroplane_id=aeroplane.id, **data.model_dump())` → `add` →
  `flush` → `refresh` → sync → return the schema. `NotFoundError` re-raised
  first; `SQLAlchemyError` logged and re-raised as `InternalError`.
  - Legacy origin: `app/services/weight_items_service.py:67-80`
  - Definition of done: the returned object carries a populated `id`; a forced
    `SQLAlchemyError` yields `InternalError`, not a bare 500 from the router.
  - Confidence: 🟢

- [ ] **T-07 — `update_weight_item` as a full replacement.**
  `for key, value in data.model_dump().items(): setattr(item, key, value)` —
  the **complete** dump, deliberately not `exclude_unset=True`.
  - Legacy origin: `app/services/weight_items_service.py:107-108`
  - Definition of done: a PUT that omits `x_m` on an item whose `x_m` was `0.30`
    leaves `x_m == 0.0`. A test must fail if `exclude_unset` semantics creep in.
  - Confidence: 🟢

- [ ] **T-08 — `delete_weight_item`.**
  Scoped lookup → `db.delete` → `db.flush` → sync; returns `None`.
  - Legacy origin: `app/services/weight_items_service.py:120-137`
  - Definition of done: the route answers 204 with an empty body and a
    subsequent GET of the id is 404.
  - Confidence: 🟢

- [ ] **T-09 — `_try_sync_assumptions`.**
  Function-local import of `sync_weight_items_to_assumptions`; catch exactly
  `(NotFoundError, SQLAlchemyError)`; `logger.warning("Skipped assumption sync:
  %s", exc)`. Called from create, update and delete only.
  - Legacy origin: `app/services/weight_items_service.py:57-64, 74, 111, 132`
  - Definition of done: with the sync patched to raise `SQLAlchemyError`, all
    three writes still succeed and the warning is logged; a read path triggers
    **zero** sync attempts (spy). An import-order test asserts that importing
    `weight_items_service` does not import `mass_cg_service`.
  - Confidence: 🟢 · 🟡 the narrow catch is intentional legacy behaviour —
    reproduce it, then record the asymmetry with the component tree.

- [ ] **T-10 — The five routes.**
  `GET`/`POST` on `/aeroplanes/{aeroplane_id}/weight-items`,
  `GET`/`PUT`/`DELETE` on `.../{item_id}`; `aeroplane_id` typed `UUID4`,
  `item_id` typed `int`; status codes 200 / **201** / 200 / 200 / **204**;
  `operation_id`s `list_weight_items`, `create_weight_item`, `get_weight_item`,
  `update_weight_item`, `delete_weight_item`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/weight_items.py`
  - Definition of done: contract tests for every status code, including the
    empty 204 body and a malformed UUID (422 from the path validator).
  - Confidence: 🟢

- [ ] **T-11 — The router's error mapping.**
  `_raise_http`: `NotFoundError → 404`, `ValidationError` /
  `ValidationDomainError → 422`, `ConflictError → 409`, else `500`; `_call`
  wraps every service invocation and converts any non-`ServiceException` into
  `500 {"detail": f"Unexpected error: {exc}"}`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/weight_items.py:25-43`
  - Definition of done: a test asserts every error body is `{"detail": …}` and
    carries **no** `error` object (this router does not use the `aeroplane-core`
    envelope). The declared-but-unreachable 409 is documented, not implemented.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — CRUD happy path:** create → read → list → update → delete, with
      the status codes 201 / 200 / 200 / 200 / 204.
- [ ] **TT-02 — Failure: unknown aeroplane UUID** is 404 on all five routes.
- [ ] **TT-03 — Failure: unknown item id** is 404 on GET, PUT and DELETE.
- [ ] **TT-04 — Failure: cross-aeroplane item id** is 404 and leaks nothing.
- [ ] **TT-05 — Failure: invalid bodies** — `mass_kg` negative, empty `name`,
      unknown `category` — are 422 with no row created.
- [ ] **TT-06 — Summary matrix:** empty inventory · single item · multi-item
      3-axis CG · all-zero-mass inventory (CGs `null`, total `0`).
- [ ] **TT-07 — Rounding:** a fixture whose exact CG needs more than 6 decimals
      is published rounded, while the unrounded value is what the sync receives.
- [ ] **TT-08 — PUT resets omitted fields** to their schema defaults.
- [ ] **TT-09 — Sync trigger count:** exactly one attempt per write, zero per
      read, verified with a spy.
- [ ] **TT-10 — Best-effort sync:** patched to raise `SQLAlchemyError`, all
      three writes still succeed and log a warning.
- [ ] **TT-11 — Import-cycle guard:** importing `weight_items_service` must not
      import `mass_cg_service` at module load.
- [ ] **TT-12 — Cascade:** deleting the aeroplane removes every item row.
- [ ] **TT-13 — Error-envelope guard:** every 4xx/5xx body has a top-level
      `detail` and no `error` object.
- [ ] **TT-14 — Transaction atomicity:** an exception raised after the flush
      leaves neither the item nor any assumption change committed.

## Data Migration Tasks

- [ ] **TM-01 — None required.** The table stores only user-entered rows; there
      is no derived column to backfill. 🟢
- [ ] **TM-02 — If the ids are ever renumbered**, `loading_scenarios.
      component_overrides` must be re-keyed in the same transaction: it stores
      `str(weight_item.id)` as `component_uuid`. See
      [`../../versioning/aeroplane-clone-subgraph/tasks.md`](../../versioning/aeroplane-clone-subgraph/tasks.md).
      🟢 (moot — retired, `Q-MB-1`) blocked on the id-stability decision.

## Suggested Order

1. **T-01 → T-02** — the table and schemas; nothing else compiles without them.
2. **T-03 → T-05** — the resolution helpers; they are the precondition for every
   service function and carry the module's access-control property.
3. **T-04** — the list + summary. It is the only read path and is fully testable
   before any write exists.
4. **T-06 → T-08** — the three writes, in that order; each is independent once
   T-05 exists.
5. **T-09** after the writes, before wiring the real sync — build it against a
   stub that raises, so the best-effort property is proven first.
6. **T-10 → T-11** last: the routes are a thin shell over everything above, and
   the error mapping is easiest to test once the service raises real
   `ServiceException`s.

## Pending Gaps (🟢 (moot — retired, `Q-MB-1`))

- **Should a weight item be able to reference a COTS component?** Without a
  `component_id` the inventory and the component tree can count the same
  physical part twice, and both write the same `mass` assumption.
- **Should `category` become a database constraint?** It is a closed set in
  Pydantic and a free `String` in the table; deciding to constrain it requires
  knowing what is already stored.
- **Should PUT become PATCH?** The full-replacement semantics silently reset
  positions when a client sends a partial body — plausible as a source of
  "my battery jumped to x = 0" reports.
- **Should the 500 body stop carrying the driver message?**
  `InternalError(message=f"Database error: {exc}")` and the router's
  `f"Unexpected error: {exc}"` both interpolate raw exception text.
- **Should the router log its catch-all?** The sibling `mass_cg` router logs
  with `exc_info=True`; this one does not log at all.
- **Should `_try_sync_assumptions` catch bare `Exception`** like the component
  tree's `_sync_aircraft_mass`, so the two producers fail symmetrically?
- **Should the summary call `aggregate_weight_items`** instead of repeating the
  formula, accepting the change from `total_mass_kg = 0` to `null` for an empty
  inventory that would follow?
</content>
