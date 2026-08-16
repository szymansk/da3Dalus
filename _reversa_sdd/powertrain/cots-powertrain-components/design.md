# cots-powertrain-components — Technical Design

> Use-case design, nested under the module [`powertrain`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Tables 🟢

**`components`** — the single hardware table.

| Column | Type | Req. | Default | Note |
|---|---|---|---|---|
| `name` | String | yes | — | half of the COTS upsert key |
| `component_type` | String INDEXED | yes | — | discriminator, validated against `component_types.name` |
| `manufacturer` | String | no | `NULL` | the other half of the upsert key |
| `description` | String | no | `NULL` | |
| `mass_g` | Float | no | `NULL` | **grams**; `NULL` = unknown, never a silent 0 |
| `bbox_x_mm` / `_y_` / `_z_` | Float | no | `NULL` | **mm** |
| `model_ref` | String | no | `NULL` | 3D-model key **and** the join to `propeller_polars.model_ref` |
| `specs` | JSON | yes | `{}` | type-specific + `source_url` / `source_version` |
| `created_at` / `updated_at` | DateTime(tz) | yes | now / onupdate | |

**`component_types`** — the schema registry.

| Column | Type | Req. | Default | Note |
|---|---|---|---|---|
| `name` | String UNIQUE INDEXED | yes | — | the discriminator value; **immutable** |
| `label` | String | yes | — | UI label — 🟢 Translated to English (`Q-CC-5`). |
| `description` | String | no | `NULL` | |
| `schema` | JSON | yes | `[]` | **mapped as `schema_def`** in Python |
| `deletable` | Boolean | yes | `True` (`server_default="1"`) | `False` for all 12 seeded types |

`PropertyDefinition`: `name`, `label`, `type ∈ {number, string, boolean}`,
`unit?`, `required`, `min?`, `max?`, `options?`.

### Services 🟢

| Symbol | File | Purpose |
|---|---|---|
| `list_components(db, component_type, q)` | `component_service` | filtered list + batch polar resolution |
| `create/get/update/delete_component` | `component_service` | CRUD; both writes call `validate_specs` |
| `_resolve_polar_id` | `component_service` | `model_ref` → `polar_id`, batched |
| `validate_specs(db, component_type, specs)` | `component_type_service:240` | the integrity gate |
| `list_type_names(db)` | `component_type_service` | the legacy `/components/types` payload |
| type CRUD | `component_type_service` | with the immutability and deletion guards |
| `seed_default_types(db)` | `component_type_service:682` | 12 types, idempotent |
| `_patch_schema_fields` | `component_type_service:710` | additive property merge |
| `import_components(...)` | `cots_import` | snapshot upsert on `(manufacturer, name)` |

## Main Flow

### F1 — The write path 🟢

```
POST /components  or  PUT /components/{id}
        │
        ├─ ComponentWrite validated by Pydantic
        │     component_type is a FREE string (gh#83) — no enum here
        │
        ├─ validate_specs(db, body.component_type, body.specs)
        │     └─ unknown type → ValidationError("… use GET /component-types")
        │     └─ per PropertyDefinition:
        │          required and absent          → ValidationError("missing_required")
        │          type mismatch                → ValidationError
        │          number outside [min, max]    → ValidationError   (inclusive)
        │          options present, value ∉ set → ValidationError
        │     └─ keys NOT in the schema         → ignored, stored as-is
        │
        └─ persist, then resolve has_polar / polar_id for the response
```

The gh#83 decision — a free string on the wire, a registry check in the service
— is what lets a **user-created** type be used the moment it exists, without a
schema regeneration or an enum rebuild. 🟢

### F2 — Seeding and patching 🟢

```
startup / test fixture
   └─ seed_default_types(db)                       # idempotent
        for each of the 12 DEFAULT_SEED_TYPES:
            missing → INSERT with deletable=False
            present → _patch_schema_fields(row, seed_schema)
                         add properties that are declared in the seed
                         but absent from the stored schema   (additive only)
```

`_patch_schema_fields` never removes or rewrites an existing property, which is
why an operator who edited a seeded type's `label` keeps that edit while still
receiving new fields such as gh-1006's `rm_ohm`. 🟢

### F3 — Deletion guards 🟢

```
DELETE /component-types/{id}
   ├─ row.deletable is False              → ConflictError → 409
   ├─ COUNT(components WHERE component_type = row.name) > 0
   │                                      → ConflictError → 409 (count in the message)
   └─ otherwise delete
```

`update_type` reads `label`, `description` and `schema` from the body and
**ignores** `name` and `deletable` — a PUT attempting to change them succeeds
with the old values retained rather than erroring. 🟡 Silent, not loud.

### F4 — The polar bridge 🟢

```
list_components:
    rows        = SELECT * FROM components WHERE …
    model_refs  = {r.model_ref for r in rows if r.model_ref}
    polar_map   = SELECT id, model_ref FROM propeller_polars
                  WHERE model_ref IN model_refs           # ONE query
    for r in rows:
        r.polar_id  = polar_map.get(r.model_ref)
        r.has_polar = r.polar_id is not None
```

One extra statement for the whole page, not one per row. 🟢

### F5 — Snapshot ingestion 🟢

```
scripts/import_cots.py  →  cots_import.import_components(db, records)
    for record in snapshot:
        record["component_type"] not in _VALID_COMPONENT_TYPES
              → ImportResult.errors, continue
        row = SELECT … WHERE manufacturer = ? AND name = ?
        row is None → INSERT   (imported += 1)
        else        → UPDATE   (updated += 1)   or   skip (skipped += 1)
```

The upsert identity is `(manufacturer, name)` — **different** from the
`(component_type='propeller', model_ref)` identity used by the propeller mirror.
Two importers, two identities, one table. 🟡

## Alternative Flows

- **Unknown `component_type` on a write:** 422 with the remediation. 🟢
- **A component of a type that was created after startup:** works immediately —
  the registry is read live on every write. 🟢
- **Unknown key in `specs`:** accepted and stored. 🟢 Load-bearing: the
  propeller mirror writes `variant`, which no schema declares.
- **`min`/`max` boundary value:** accepted — the bounds are inclusive. 🟢
- **A boolean supplied for a `number` property:** rejected. 🟢 Python's
  `bool` is an `int` subclass, so this check must be explicit.
- **Deleting a type that is seeded *and* referenced:** the `deletable` guard
  fires first; the message names the seed, not the references. 🟡
- **`PUT` attempting to change `name` / `deletable`:** silently ignored, 200. 🟡
- **Snapshot record with an unknown type:** collected into `errors`; the import
  continues with the remaining records. 🟢
- **Component deleted while referenced** by `component_tree.component_id` or
  `wing_xsec_ted_servos.component_id`: there is no guard in this use case — the
  FK behaviour decides. 🟡 Not audited here.
- **Model download for a component with no `model_ref`:** 404. 🟢

## Dependencies

- **[`propeller-polars`](../propeller-polars/design.md)** — supplies the rows
  that `_resolve_polar_id` joins against, and writes propeller components
  through `prop_component_seed` — 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`).
- **[`performance-model`](../performance-model/design.md)** and
  **[`powertrain-sizing`](../powertrain-sizing/design.md)** — read `specs` by
  key; the key names are not unified (BR-CC4).
- **`aeroplane-core` component tree** — reads `components.mass_g` (COTS branch)
  and `specs.density_kg_m3` + `specs.print_resolution_mm` (material branch of
  the weight ladder). Note that `print_resolution_mm` is a **material component
  spec**, not a tree-node column
  (`component_tree_service.py:454`, `component_type_service.py:347`). 🟢
- **`wing-design`** — the `servo` type and `wing_xsec_ted_servos.component_id`.
- **`construction-plans`** — the five wood/tube types.
- **`versioning`** — both tables are in `EXCLUDED_TABLES`; `component_id`
  references survive a clone unchanged.
- **`app/db/session.py` (`get_db`)** — the transaction (ADR 0009); the reimport
  CLI commits once at the end.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One table for every hardware type, discriminated by a string column | ADR 0013 | 🟢 |
| The per-type contract is a database row, not code | `component_types.schema_def` | 🟢 |
| The wire type is a free string; the registry check lives in the service (gh#83) | `component.py:11-15` | 🟢 |
| Unknown `specs` keys are accepted — the schema is a floor | `validate_specs` | 🟢 |
| Seeded types are undeletable; referenced types are protected | `deletable=False`, count → 409 | 🟢 |
| `name` and `deletable` are immutable, and an attempt to change them is ignored rather than rejected | `update_type` | 🟢 |
| Schema evolution is additive so operator edits survive | `_patch_schema_fields:710` | 🟢 |
| `mass_g = NULL` means unknown, distinct from `0` | `component.py` + the weight ladder | 🟢 |
| The polar bridge is resolved per page, not per row | `_resolve_polar_id` | 🟢 |
| Ingestion is offline, from a committed snapshot, upserting on `(manufacturer, name)` | ADR 0014, `cots_import` | 🟢 |
| The library is global and exempt from versioning | `EXCLUDED_TABLES` | 🟢 |

## Internal State

Both tables are **global and long-lived**: they are not per-aircraft, not
cloned, and not invalidated. The only derived values are `has_polar` /
`polar_id`, computed per request from `model_ref`. 🟢

Startup mutates state: `seed_default_types` runs unconditionally, so an empty or
partially-seeded registry repairs itself on the next boot — which is also the
mechanism by which a schema addition reaches an existing database. 🟢

## Observability

- `ImportResult{imported, updated, skipped, errors[]}` — the ingestion path is
  the best-instrumented part of the use case. 🟢
- `validate_specs` raises with a structured reason (`missing_required`), which
  reaches the client in the 422 message. 🟢
- 🟢 One error envelope and one handler (`Q-CC-3`); per-router catch-alls disappear.
- Nothing counts how many components carry a `NULL` `mass_g`, how many `specs`
  keys are undeclared, or how often a type-deletion guard fires. 🟡

## Risks and Gaps

- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). Previously two taxonomies: `DEFAULT_SEED_TYPES` and
  `cots_import._VALID_COMPONENT_TYPES` list the same 12 names independently; a
  new type added to one is invisible to the other.
- 🟡 **Two upsert identities for one table.** `(manufacturer, name)` for
  `cots_import`, `(component_type='propeller', model_ref)` for the propeller
  mirror. A propeller could in principle be duplicated by the two paths.
- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). Previously `prop_component_seed` bypassed `validate_specs`,, so the mirror can
  write rows that violate their own type schema — they 422 on the first API
  `PUT`.
- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). Undeclared keys are therefore rejected, not tolerated. Previously:, which means the
  type schema can never be used as a complete contract for code generation or
  for a UI form.
- 🟢 Translated to English (`Q-CC-5`). Previously German on all 12 seeded types, rendered directly in the editor.
- 🟢 The Pydantic spec-model spellings are canonical; importers normalise (`Q-PT-4`). Previously: `c_rate` / `c_rating` / `discharge_c` and
  `continuous_current_a` / `max_continuous_a` / `max_current_a` are read under
  different names by different consumers, so a valid component can be invisible
  to one of them.
- 🟢 **A referenced component cannot be deleted, only changed** (`Q-PT-7`, maintainer-answered). Previously unguarded:
  here; `component_tree` and `wing_xsec_ted_servos` hold FKs to it.
- 🟡 **Immutability is silent.** A client that PUTs a new `name` gets a 200 and
  no indication that the change was dropped.
- 🟡 **Model upload validation is not visible** in this use case — size, type
  and path handling are not audited.
</content>
