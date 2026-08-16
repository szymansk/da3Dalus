# weight-items

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


> Use-case specification, nested under the module
> [`mass-and-balance`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🟢 (moot — retired, `Q-MB-1`) GAP.
> Sources: `app/services/weight_items_service.py`,
> `app/api/v2/endpoints/aeroplane/weight_items.py`,
> `app/schemas/weight_item.py`, `app/models/aeroplanemodel.py:798`,
> `_reversa_sdd/data-dictionary.md` §Module: mass-and-balance.
> Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

`weight-items` is the **flat mass inventory**: a list of named point masses with
a position, owned by one aeroplane. It is the simple-aircraft alternative to the
hierarchical component tree — no nesting, no COTS references, no CAD geometry,
just *"185 g of battery at x = 0.08 m"*. It is also the only source of the
**aggregate centre of gravity** in the system. 🟢

## Responsibilities

- CRUD the `weight_items` rows of one aeroplane, addressed by the aeroplane's
  UUID and the item's integer PK. 🟢
- Serve the inventory together with an inline mass + 3-axis CG summary. 🟢
- Trigger the best-effort mass sync after every write. 🟢
- Enforce the category vocabulary and the non-negative mass at the schema
  boundary. 🟢

**NOT this use case:** the aggregation maths and the CG comparison
(→ [`cg-mass-computation`](../cg-mass-computation/requirements.md)), the write
into the `mass` assumption
(→ [`component-tree-mass-sync`](../component-tree-mass-sync/requirements.md)),
and the hierarchical bill of materials (→ `aeroplane-core`'s component tree).

## Business Rules

> Global ids (`BR-*`) come from [`../../domain.md`](../../domain.md); `BR-MB*`
> from [`../requirements.md`](../requirements.md). `BR-WI*` are new here.

- **BR-MB16 — Kilograms and metres.** 🟢 `mass_kg` in kg with `ge=0`; `x_m`,
  `y_m`, `z_m` in metres, each defaulting to `0.0`. The component tree next door
  works in grams and millimetres — this use case never converts.
- **BR-MB15 — The category set is Pydantic-only.** 🟢
  `WEIGHT_CATEGORIES = electronics | battery | structural | payload | other`
  (`app/schemas/weight_item.py:8`), default `"other"`; the column is a plain
  `String`. 🟢 (moot — retired, `Q-MB-1`) A direct SQL insert or a future importer can store anything, and
  the read path would serve it back unvalidated.
- **BR-WI1 — Items are always scoped by aeroplane, never by id alone.** 🟢 Every
  single-item query filters `aeroplane_id == aeroplane.id AND id == item_id`
  (`weight_items_service.py:85-89, 100-104, 123-127`). An item id belonging to a
  different aeroplane is therefore a **404**, not a 403 and not a silent
  cross-tenant read.
- **BR-WI2 — Update is a full replacement.** 🟢 `update_weight_item` iterates
  `data.model_dump().items()` — the *complete* dump, not
  `exclude_unset=True` — so an omitted `x_m` is written back as its schema
  default `0.0` (`:107-108`). There is no PATCH route. Contrast with the
  component tree, which uses `exclude_unset` semantics (BR-33).
- **BR-WI3 — The summary is computed inline and rounded to 6 decimals.** 🟢
  `list_weight_items` (`:36-54`) does not call
  `mass_cg_service.aggregate_weight_items`; it repeats the arithmetic over the
  mapped read objects and rounds `total_mass_kg` and all three CGs to 6 dp. 🟡
  A second, independent implementation of the same formula.
- **BR-WI4 — An empty inventory has a mass but no centre of gravity.** 🟢 The
  guard is `if total > 0`, so an empty (or zero-mass) inventory returns
  `total_mass_kg = 0` with `cg_x_m = cg_y_m = cg_z_m = None`. The mass is
  reported as `0`, not `None` — the opposite convention to the component tree's
  `get_aircraft_total_weight_kg`. 🟢 (moot — retired, `Q-MB-1`) Two "empty" conventions in one module.
- **BR-WI5 — Every write ends with a best-effort sync.** 🟢 `create`, `update`
  and `delete` call `_try_sync_assumptions` after their `flush()`; the read
  paths do not (`:74, 111, 132`).
- **BR-30 — The sync never blocks the CRUD.** 🟢 `_try_sync_assumptions` catches
  `NotFoundError` and `SQLAlchemyError` and logs a warning (`:57-64`). 🟡 Note
  the narrower catch compared with the component tree's bare `except Exception`
  — an unexpected exception type inside the assumption service *would* fail a
  weight-item write.
- **BR-WI6 — A database error becomes a 500 carrying the driver message.** 🟢
  `create`/`update`/`delete` wrap `SQLAlchemyError` as
  `InternalError(message=f"Database error: {exc}")` (`:78-80, 115-117, 135-137`)
  while re-raising `NotFoundError` untouched. 🟢 (moot — retired, `Q-MB-1`) Raw DB text reaches the client.
- **BR-MB17 — Deletion cascades from the aeroplane.** 🟢 FK `ON DELETE CASCADE`
  plus `cascade="all, delete-orphan"` on `AeroplaneModel.weight_items`, ordered
  by `id`.
- **BR-40 — Cloning re-keys weight-item references.** 🟢 `versioning` copies
  `weight_items` and builds a `weight_id_map: str(old id) → str(new id)`, which
  is then applied to `loading_scenarios.component_overrides`. A weight item's
  **integer PK, stringified, is a public identifier** inside that JSON — which is
  why the ids cannot be renumbered casually. See
  [`../../versioning/aeroplane-clone-subgraph/design.md`](../../versioning/aeroplane-clone-subgraph/design.md).
- 🟢 (moot — retired, `Q-MB-1`) **No `component_id`.** A weight item cannot reference a COTS component, so
  the same battery placed in both the inventory and the component tree is two
  unrelated rows.
- 🟢 (moot — retired, `Q-MB-1`) **No uniqueness on `name`.** Two items called "battery" are legal and
  indistinguishable in the UI list.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List the inventory of an aeroplane, ordered by id | Must | `GET .../weight-items` → 200; items appear in insertion order |
| RF-02 | Include `total_mass_kg` and 3-axis CG, all rounded to 6 dp | Must | A 0.4 kg @ 0.10 m + 0.6 kg @ 0.20 m inventory reports `total 1.0`, `cg_x_m 0.16` |
| RF-03 | Report `cg_*` as `null` and `total_mass_kg` as `0` for an empty inventory | Must | No items ⇒ `{total_mass_kg: 0, cg_x_m: null, cg_y_m: null, cg_z_m: null}` |
| RF-04 | Create an item and return it with its id | Must | `POST .../weight-items` → **201** `WeightItemRead` |
| RF-05 | Reject an invalid body before touching the database | Must | `mass_kg = -0.5` → 422; `name = ""` → 422; `category = "fuel"` → 422; no row is created |
| RF-06 | Read one item, scoped to its aeroplane | Must | An id from a different aeroplane → 404 |
| RF-07 | Replace an item wholesale | Must | `PUT` with `x_m` omitted resets it to `0.0` |
| RF-08 | Delete an item with an empty 204 response | Must | `DELETE .../weight-items/{id}` → **204**, empty body; the row is gone |
| RF-09 | Report a missing aeroplane as 404 on every route | Must | Unknown UUID → 404 on all five routes |
| RF-10 | Trigger the mass sync after create, update and delete | Must | A spy records exactly one sync attempt per write, zero per read |
| RF-11 | Never fail a write because the sync failed | Must | Sync patched to raise `SQLAlchemyError` ⇒ the write still returns 201/200/204 |
| RF-12 | Cascade-delete the inventory with its aeroplane | Must | Deleting the aeroplane leaves no `weight_items` rows |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Cross-aeroplane access is structurally impossible — the aeroplane scope is part of every item query | `weight_items_service.py:85-89, 100-104, 123-127` | 🟢 |
| Correctness | Published numbers are rounded once, at the boundary, to 6 dp | `:44-51` | 🟢 |
| Availability | A failed assumption sync degrades the mass model, never the inventory write | `:57-64` | 🟢 |
| Performance | One indexed query per request; the summary is pure Python over already-loaded rows — no N+1 | `:38-46` | 🟢 |
| Reliability | The request-scoped transaction rolls back the row **and** any partial sync effect together (ADR 0009) | `app/db/session.py:55-64` | 🟢 |
| Security | Raw `SQLAlchemyError` text is interpolated into the 500 body — a leak of schema details | `:78-80` | 🟢 (moot — retired, `Q-MB-1`) |
| Portability | The use case never imports AeroSandbox or CadQuery; it works on every platform | whole module | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Weight-item inventory CRUD

  Scenario: Creating the first item
    Given an aeroplane with an empty inventory
    When I POST a weight item {name: "RX", mass_kg: 0.012, x_m: 0.05, category: "electronics"}
    Then the response status is 201
    And the response contains an integer id
    And y_m and z_m are 0.0

  Scenario: Listing reports the mass-weighted CG
    Given weight items 0.4 kg at x=0.10 and 0.6 kg at x=0.20
    When I GET the inventory
    Then total_mass_kg is 1.0
    And cg_x_m is 0.16

  Scenario: An empty inventory has zero mass and no CG
    Given an aeroplane with no weight items
    When I GET the inventory
    Then total_mass_kg is 0
    And cg_x_m is null
    And cg_y_m is null
    And cg_z_m is null

  Scenario: Update replaces every field
    Given a weight item with x_m 0.30
    When I PUT {name: "RX", mass_kg: 0.012} without x_m
    Then the response status is 200
    And the stored x_m is 0.0

  Scenario: Delete answers 204 with no body
    Given a weight item
    When I DELETE it
    Then the response status is 204
    And the response body is empty
    And a subsequent GET of that item returns 404

  Scenario: An item of another aeroplane is not found
    Given aeroplane A with item 7 and aeroplane B with no items
    When I GET /aeroplanes/{B}/weight-items/7
    Then the response status is 404
    And the item is not disclosed

  Scenario: A negative mass is rejected before persistence
    Given an aeroplane
    When I POST a weight item with mass_kg -0.5
    Then the response status is 422
    And the inventory is still empty

  Scenario: An unknown category is rejected
    Given an aeroplane
    When I POST a weight item with category "fuel"
    Then the response status is 422

  Scenario: A failing assumption sync does not fail the write
    Given sync_weight_items_to_assumptions raises SQLAlchemyError
    When I POST a valid weight item
    Then the response status is 201
    And the item is persisted
    And a warning is logged

  Scenario: Deleting the aeroplane removes its inventory
    Given an aeroplane with three weight items
    When the aeroplane is deleted
    Then no weight_items rows remain for it
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| CRUD with aeroplane-scoped lookups (RF-01, RF-04, RF-06…RF-09) | Must | The inventory is one of only two mass producers; the scoping is the module's sole access control |
| Summary with total + CG (RF-02/RF-03) | Must | The aggregate CG exists nowhere else in the system |
| Schema validation (RF-05) | Must | The database column set is unconstrained — Pydantic is the only gate |
| Post-write sync trigger (RF-10/RF-11) | Must | Without it the mass assumption silently goes stale; without the best-effort wrapper an assumption bug breaks the inventory |
| Cascade delete (RF-12) | Must | Orphaned weight items would be invisible and would still be cloned by `versioning` |
| Full-replacement PUT semantics (RF-07) | Should | Legacy behaviour; a PATCH would be friendlier but nothing depends on the reset |
| 6-decimal rounding (RF-02) | Should | Cosmetic stability of the displayed number; the unrounded aggregate is used for the sync |
| `component_id` on a weight item | Won't | 🟢 (moot — retired, `Q-MB-1`) not implemented — the reason double-counting with the component tree is undetectable |
| PATCH / bulk import routes | Won't | No such routes exist |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/weight_items_service.py` | `list_weight_items`, `create_weight_item`, `get_weight_item`, `update_weight_item`, `delete_weight_item`, `_try_sync_assumptions`, `_get_aeroplane`, `_item_to_schema` | 🟢 |
| `app/api/v2/endpoints/aeroplane/weight_items.py` | 5 routes, `_raise_http`, `_call` | 🟢 |
| `app/schemas/weight_item.py` | `WEIGHT_CATEGORIES`, `WeightItemWrite`, `WeightItemRead`, `WeightSummary` | 🟢 |
| `app/models/aeroplanemodel.py:798` | `WeightItemModel` | 🟢 |
| `app/services/aeroplane_clone_service.py:207-225` | weight-item clone + `weight_id_map` | 🟢 covered by `versioning` |
</content>
