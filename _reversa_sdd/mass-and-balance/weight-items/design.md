# weight-items — Technical Design

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


> Use-case design, nested under the module
> [`mass-and-balance`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🟢 (moot — retired, `Q-MB-1`) GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/weight_items_service.py` 🟢

| Symbol | Signature | Line | Raises |
|---|---|---|---|
| `_get_aeroplane` | `(db, uuid) -> AeroplaneModel` | 16 | `NotFoundError(entity="Aeroplane")` |
| `_item_to_schema` | `(WeightItemModel) -> WeightItemRead` | 23 | — |
| `list_weight_items` | `(db, uuid) -> WeightSummary` | 36 | `NotFoundError` |
| `_try_sync_assumptions` | `(db, uuid) -> None` | 57 | never |
| `create_weight_item` | `(db, uuid, WeightItemWrite) -> WeightItemRead` | 67 | `NotFoundError`, `InternalError` |
| `get_weight_item` | `(db, uuid, item_id) -> WeightItemRead` | 83 | `NotFoundError(entity="WeightItem")` |
| `update_weight_item` | `(db, uuid, item_id, WeightItemWrite) -> WeightItemRead` | 95 | `NotFoundError`, `InternalError` |
| `delete_weight_item` | `(db, uuid, item_id) -> None` | 120 | `NotFoundError`, `InternalError` |

### REST surface 🟢

| Method | Path | Status |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/weight-items` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/weight-items` | **201** · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | 200 · 404 · 500 |
| PUT | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | 200 · 404 · 422 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}/weight-items/{item_id}` | **204** · 404 · 500 |

### Data model — `weight_items` 🟢

| Column | Type | Req. | Default | Unit |
|---|---|---|---|---|
| `id` | Integer PK | — | auto | — |
| `aeroplane_id` | Integer FK → `aeroplanes.id` `ON DELETE CASCADE`, indexed | yes | — | — |
| `name` | String | yes | — | — |
| `mass_kg` | Float | yes | — | **kg** |
| `x_m` / `y_m` / `z_m` | Float | yes | `0.0` | **metres** |
| `description` | String | no | `NULL` | — |
| `category` | String | yes | `"other"` | — |

The FK is the aeroplane's **integer PK**, while every route addresses the
aeroplane by **UUID** — which is why `_get_aeroplane` runs first on all five
paths and why an unknown UUID is always a 404 before anything else happens. 🟢

## Main Flow

### F1 — Resolve, then act 🟢

Every operation starts identically:

```
aeroplane = _get_aeroplane(db, aeroplane_uuid)     # NotFoundError -> 404
```

and every single-item operation then narrows by **both** keys:

```
item = db.query(WeightItemModel).filter(
           WeightItemModel.aeroplane_id == aeroplane.id,
           WeightItemModel.id == item_id).first()
if item is None: raise NotFoundError(entity="WeightItem", resource_id=item_id)
```

This double filter is the use case's entire access-control story: there is no
authentication layer (ADR 0016), so scoping by aeroplane is what stops one
aircraft's request from reading another's row. 🟢

### F2 — List + inline summary (`list_weight_items`, l.36-54) 🟢

```
rows  = weight_items WHERE aeroplane_id = aeroplane.id      # ordered by id
items = [_item_to_schema(r) for r in rows]
total = Σ items[i].mass_kg

if total > 0:
    cg_x = round(Σ(mᵢ·xᵢ)/total, 6)
    cg_y = round(Σ(mᵢ·yᵢ)/total, 6)
    cg_z = round(Σ(mᵢ·zᵢ)/total, 6)
else:
    cg_x = cg_y = cg_z = None

return WeightSummary(items, round(total, 6), cg_x, cg_y, cg_z)
```

Three properties worth preserving verbatim:

1. **It does not call `aggregate_weight_items`.** The same formula lives twice —
   here (rounded) and in `mass_cg_service` (unrounded, used by the sync and the
   CG comparison). 🟡
2. **`total_mass_kg` is `0`, not `None`, for an empty inventory** — while the
   CGs *are* `None`. The mass and the CG use different "empty" conventions.
3. **Rounding is applied once, at the boundary.** The unrounded values are what
   the sync and the comparison see.

### F3 — Create (l.67-80) 🟢

```
aeroplane = _get_aeroplane(...)
item = WeightItemModel(aeroplane_id=aeroplane.id, **data.model_dump())
db.add(item); db.flush(); db.refresh(item)
_try_sync_assumptions(db, aeroplane_uuid)
return _item_to_schema(item)
```

`db.flush()` populates the PK, `db.refresh()` reloads the server-side defaults,
and the sync runs **inside** the same transaction — so a rollback undoes the row
and the assumption write together. 🟢

### F4 — Update (l.95-117) 🟢

```
for key, value in data.model_dump().items():     # FULL dump — no exclude_unset
    setattr(item, key, value)
db.flush(); db.refresh(item)
_try_sync_assumptions(...)
```

`model_dump()` without `exclude_unset=True` is what makes PUT a genuine
replacement: an omitted optional field is materialised as its schema default and
written. 🟢

### F5 — Delete (l.120-137) 🟢

`db.delete(item)` → `db.flush()` → sync. The route returns **204** with no body.

### F6 — Best-effort sync (`_try_sync_assumptions`, l.57-64) 🟢

```
def _try_sync_assumptions(db, aeroplane_uuid):
    try:
        from app.services.mass_cg_service import sync_weight_items_to_assumptions
        sync_weight_items_to_assumptions(db, aeroplane_uuid)
    except (NotFoundError, SQLAlchemyError) as exc:
        logger.warning("Skipped assumption sync: %s", exc)
```

The **function-local import** breaks the `weight_items_service ↔ mass_cg_service`
cycle. The catch is deliberately narrow — `NotFoundError` covers the
"assumptions not seeded yet" case and `SQLAlchemyError` covers a DB hiccup, but
a `TypeError` or `KeyError` raised inside the assumption service **would**
propagate and fail the weight-item write. 🟡 The component tree's counterpart
catches bare `Exception`; the two are not symmetric.

## Alternative Flows

- **Unknown aeroplane UUID:** 404 on every route, before any item work. 🟢
- **Unknown item id, or an id owned by another aeroplane:** 404
  (`entity="WeightItem"`). 🟢
- **Invalid body:** FastAPI/Pydantic rejects it before the service is reached —
  422 with the framework's validation payload, not the service's `{"detail":
  str}` shape. 🟡 Two different 422 body shapes on the same route.
- **`SQLAlchemyError` during a write:** logged, then re-raised as
  `InternalError(message=f"Database error: {exc}")` → 500 with the driver text
  in the body. 🟢 (moot — retired, `Q-MB-1`)
- **`NotFoundError` raised *inside* a write's `try`:** explicitly re-raised
  before the `SQLAlchemyError` handler so it stays a 404 rather than becoming a
  500 (`:76-77, 113-114, 133-134`). 🟢
- **Assumption sync raises `NotFoundError` / `SQLAlchemyError`:** swallowed with
  a warning; the write's status code is unaffected. 🟢
- **Assumption sync raises anything else:** propagates → 500, and the
  transaction rolls back the item too. 🟡 undocumented in the legacy.
- **Zero-mass inventory (every item `mass_kg = 0`):** `total > 0` is false, so
  the CGs are `None` while `total_mass_kg` is `0`. 🟢
- **Aeroplane deleted while items exist:** ORM cascade + FK `ON DELETE CASCADE`
  remove them. 🟢

## Dependencies

- **`aeroplanes`** — resolved by UUID on every call; the FK is the integer PK.
- **[`component-tree-mass-sync`](../component-tree-mass-sync/design.md)** —
  receives every write through `_try_sync_assumptions`; imported lazily.
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009).
- **`app/core/exceptions.py`** — `NotFoundError`, `InternalError`.
- **`versioning`** — clones these rows and builds the
  `weight_id_map` that re-keys `loading_scenarios.component_overrides`; see
  [`../../versioning/aeroplane-clone-subgraph/design.md`](../../versioning/aeroplane-clone-subgraph/design.md).
  This is why a weight item's stringified integer PK is effectively a public
  identifier. 🟢

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Aeroplane scope is part of every item query, making cross-aeroplane reads a 404 | `weight_items_service.py:85-89, 100-104, 123-127` | 🟢 |
| PUT is a full replacement (`model_dump()` without `exclude_unset`) | `:107-108` | 🟢 |
| The summary is recomputed inline and rounded at the boundary | `:44-51` | 🟢 |
| Empty inventory ⇒ mass `0` but CG `None` | `:42-51` | 🟢 |
| The sync runs inside the same transaction, after the flush | `:74, 111, 132` | 🟢 |
| The import cycle is broken by a function-local import | `:60` | 🟢 |
| The sync's catch is narrow (`NotFoundError`, `SQLAlchemyError`) rather than bare | `:63` | 🟢 |
| A flat inventory is kept **alongside** the hierarchical tree rather than merged into it | ADR 0011 §Alternatives 4 | 🟢 |
| Categories are a UI vocabulary, not a database constraint | `app/schemas/weight_item.py:8` | 🟢 |

## Internal State

`weight_items` rows only. Everything published beyond them —
`total_mass_kg`, `cg_x_m`, `cg_y_m`, `cg_z_m` — is derived per request and
persisted nowhere. The one *external* state this use case mutates is
`design_assumptions."mass"`, and it does so indirectly and best-effort. 🟢

## Observability

- `logger.warning("Skipped assumption sync: %s", exc)` — the only trace of a
  swallowed sync failure. 🟢
- `logger.error("DB error in create/update/delete_weight_item: %s", exc)` before
  each `InternalError` re-raise. 🟢
- The router's `_call` catch-all raises a 500 **without logging** — unlike the
  sibling `mass_cg` router, which logs with `exc_info=True`. 🟢 (moot — retired, `Q-MB-1`)
- No metric or counter: nothing records how large an inventory grows, how often
  a sync is skipped, or how often the CG is `None` because the mass is zero. 🟡

## Risks and Gaps

- 🟢 (moot — retired, `Q-MB-1`) **No `component_id`.** The inventory cannot reference the COTS catalogue,
  so a battery entered here and the same battery placed in the component tree
  are unrelated rows — and both feed the same `mass` assumption.
- 🟢 (moot — retired, `Q-MB-1`) **The `category` column is unconstrained.** Only Pydantic enforces the five
  values; anything written outside the API is served back unchecked.
- 🟢 (moot — retired, `Q-MB-1`) **Driver text in 500 bodies.** `f"Database error: {exc}"` exposes schema
  details on a constraint violation.
- 🟢 (moot — retired, `Q-MB-1`) **The router does not log its catch-all.** A 500 from an unexpected
  exception type leaves no server-side trace on this router.
- 🟡 **Two implementations of one formula.** The route's rounded summary and
  `aggregate_weight_items` will drift the moment either changes.
- 🟡 **Two "empty" conventions.** `total_mass_kg = 0` here versus
  `total_weight_kg = null` in the component tree, for the same situation.
- 🟡 **The narrow sync catch is asymmetric** with the component tree's bare
  `except Exception`, so the two producers fail differently under the same fault.
- 🟡 **No `name` uniqueness and no ordering control.** Items are returned in
  insertion order with no user-facing sort field, so a long inventory cannot be
  reorganised.
- 🟡 **Two 422 shapes on one route.** Pydantic's validation payload and the
  service's `{"detail": str}` both surface as 422.
</content>
