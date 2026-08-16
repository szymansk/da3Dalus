# aeroplane-crud — Technical Design

> Use-case design, nested under the module [`aeroplane-core`](../design.md).
> Focuses on HOW the use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module-level endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/aeroplane_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `list_all_aeroplanes` | `(db: Session)` | `List[AeroplaneModel]` | ordered by `name` (l.47) |
| `create_aeroplane` | `(db: Session, name: str)` | `AeroplaneModel` | creates the row **and** the versioning lineage (l.61) |
| `get_aeroplane_by_uuid` | `(db, aeroplane_uuid)` | `AeroplaneModel` | raises `NotFoundError(entity="Aeroplane", resource_id=uuid)` (l.106) |
| `get_aeroplane_schema` | `(db, aeroplane_uuid)` | `AeroplaneSchema` | full nested read model (l.129) |
| `delete_aeroplane` | `(db, aeroplane_uuid)` | `None` | ORM cascade + best-effort STEP cleanup (l.169) |
| `get_aeroplane_mass` | `(db, aeroplane_uuid)` | `float` | raises `NotFoundError` (l.201) |
| `set_aeroplane_mass` | `(db, aeroplane_uuid, total_mass_kg: float)` | `bool` | `True` when newly created (l.218) |

### REST surface — `app/api/v2/endpoints/aeroplane/base.py` 🟢

Routes are mounted at the **application root** — there is no `/api/v2` segment.
`{aeroplane_id}` is always the public UUID.

| Method | Path | Handler | Status codes |
|---|---|---|---|
| GET | `/aeroplanes` | `get_aeroplanes` (l.76) | 200 · 500 |
| POST | `/aeroplanes` | `create_aeroplane` (l.130) | **201** · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}` | `get_aeroplane` (l.154) | 200 · 404 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}` | `delete_aeroplane` (l.176) | 200 · 404 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/total_mass_kg` | `get_aeroplane_total_mass_in_kg` (l.200) | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/total_mass_kg` | `create_aeroplane_total_mass_kg` (l.226) | **201 create · 200 update** · 404 · 422 · 500 |

`GET /aeroplanes` carries one query parameter: `heads_only: bool = True`.
`GET /aeroplanes/{id}/airplane_configuration` is deliberately **out of scope** —
see [`../airplane-configuration-export/design.md`](../airplane-configuration-export/design.md).

### Data model 🟢

`aeroplanes` (`AeroplaneModel`, `app/models/aeroplanemodel.py:662`) — the columns
this use case reads or writes:

| Column | Type | Meaning |
|---|---|---|
| `id` | Integer PK | internal identity |
| `uuid` | GUID, unique | **the public identifier** |
| `name` | String | display name; **no unique constraint** |
| `total_mass_kg` | Float, nullable | the design total mass, kilograms |
| `xyz_ref` | JSON `[x,y,z]` | reference point, **metres**, default `[0,0,0]` |
| `branch_id` / `predecessor_id` / `root_id` | FK, `use_alter=True` | versioning pointers written at birth |
| `is_immutable` | Boolean | snapshot flag, read by the `heads_only` projection |
| `created_by` | String | free text; `"human"` on the branch created here |

Cascading relations (`cascade="all, delete-orphan"`): `wings`, `fuselages`,
`weight_items`, `copilot_messages`, `design_assumptions`, `computation_config`
(1:1), `stability_results`, `loading_scenarios`, `mission_objective` (1:1).
`flight_profile` is many-to-one **without** cascade — the shared
`rc_flight_profiles` row survives a delete.
🟢 (`app/models/aeroplanemodel.py:718-795`)

## Main Flow

### F1 — List aeroplanes (`get_aeroplanes`, `base.py:76-95`) 🟢

1. Read the `heads_only` query flag (default `True`).
2. Load all aeroplanes ordered by `name` (`list_all_aeroplanes`, l.47).
3. When `heads_only` is true, keep only nodes that are the `head_id` of some
   branch — immutable version snapshots drop out.
4. Wrap in `GetAeroplaneResponse`.

### F2 — Create aeroplane (`create_aeroplane`, `aeroplane_service.py:61-104`) 🟢

1. Instantiate `AeroplaneModel(name=name)` and `db.add()`.
2. `db.flush()` — the id is now assigned but nothing is committed.
3. Set `aeroplane.root_id = aeroplane.id` (a lineage root points at itself).
4. Create `BranchModel(root_id=id, head_id=id, name="main", is_main=True,
   created_by="human")`, `db.add()`, `db.flush()`.
5. Back-fill `aeroplane.branch_id = branch.id`.
6. Return the model. The commit happens in `get_db()` when the request succeeds.
7. The endpoint answers **201** with `CreateAeroplaneResponse` carrying the UUID.

The `flush()` sequence is mandatory: the two FKs are mutually circular, declared
with `use_alter=True` so the DDL emits them as separate `ALTER TABLE` constraints
rather than an unsatisfiable inline pair (`aeroplanemodel.py:629-638, :691-706`).

### F3 — Read nested aircraft (`get_aeroplane_schema`, l.129-167) 🟢

1. Resolve the aeroplane by UUID (`NotFoundError` → 404 if absent).
2. **Materialise** — iterate

   ```
   for wing in aeroplane.wings:
       for xsec in wing.x_secs:
           detail = xsec.detail
           _ = detail.spares
           ted = detail.trailing_edge_device
           _ = ted.servo_data
   for fuselage in aeroplane.fuselages:
       _ = fuselage.x_secs
   ```

   touching each attribute so SQLAlchemy issues the SELECTs while the session is
   still open (l.141-149).
3. Build `AeroplaneSchema.model_validate(aeroplane)` (`from_attributes=True`).
4. Return; FastAPI serialises **after** `get_db()` has closed the session, which
   is exactly why step 2 exists.

### F4 — Delete aeroplane (`delete_aeroplane`, l.169-199) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. `db.delete(aeroplane)` — the ORM cascade removes every child collection.
3. Call `openvsp_step_export_service.cleanup_aeroplane_step_files()` inside a
   bare `try/except` that logs and swallows (l.191-198).
4. Return; the commit happens in `get_db()`.

### F5 — Mass read and upsert (l.201-250, `base.py:200, 226`) 🟢

```
get_aeroplane_mass(db, uuid) -> float          # 404 when the aeroplane is absent
set_aeroplane_mass(db, uuid, total_mass_kg) -> bool
    returns True  when total_mass_kg was previously None  -> HTTP 201
    returns False when an existing value was replaced      -> HTTP 200
```

The unit is **kilograms** on both the wire and the column.

## Alternative Flows

- **Aeroplane not found (any route):** the service raises `NotFoundError`; the
  endpoint's `_raise_http_from_domain` (`base.py:52-67`) maps it to **404** with
  `{"error": {"code": "not_found", "message": …, "details": {…}}}`.
- **STEP cleanup failure on delete:** caught by a bare `except`, logged, the
  delete still succeeds. Orphaned artefacts are accepted. 🟢
- **Duplicate name:** there is no uniqueness constraint on `aeroplanes.name`, so
  the create simply succeeds and the two rows are distinguished by UUID.
  🟡 INFERRED from the absence of a unique index.
- **Any `IntegrityError` reaching the global handler:** mapped to **409** with
  the German message `"name existiert bereits"` regardless of which constraint
  actually failed. 🔴
- **Unexpected exception in any handler:** each handler carries a defensive
  `except Exception → 500` in addition to the domain mapping. 🟢

## Dependencies

- **`app/db/session.py` (`get_db`)** — owns the transaction; this use case never
  commits (ADR 0009).
- **`versioning` (`BranchModel`)** — the lineage row created at birth; every
  further branch/snapshot operation lives in that module. This use case only
  writes the *first* branch.
- **`openvsp_step_export_service`** — best-effort artefact cleanup on delete.
- **`wing-design` / `fuselage-design`** — supply the `WingModel` /
  `FuselageModel` rows that `get_aeroplane_schema` materialises and serialises.
- **`app/core/exceptions.py`** — the `ServiceException` hierarchy
  (`NotFoundError`, `ValidationError`, `ConflictError`, `InternalError`).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Public identity is a UUID, internal identity an integer PK | `AeroplaneModel.uuid` unique + every v2 route takes `aeroplane_id` as UUID | 🟢 |
| Versioning is by row copy, not JSON snapshots — hence every aeroplane is a lineage node from birth | ADR 0006; `create_aeroplane:75-100` | 🟢 |
| Exactly one main branch is a **database** invariant, not an application check | partial unique index `uq_branches_one_main_per_root`, `aeroplanemodel.py:616-624` | 🟢 |
| Circular FKs are resolved with `use_alter=True` plus a manual flush dance, rather than by making one side nullable-and-deferred | `aeroplanemodel.py:629-638, :691-706`; `aeroplane_service.py:75-100` | 🟢 |
| Lazy loads are forced manually rather than by `selectinload` eager options | `aeroplane_service.py:141-149` | 🟢 |
| Best-effort side effects never fail the primary operation | `aeroplane_service.py:191-198` | 🟢 |
| `created_by` is a free-text column, not an enum — `"human"` here, `"ai"` / `"copilot"` elsewhere | `aeroplanemodel.py:641, :710` | 🟢 |
| Snapshot hiding is a **read-time projection**, not a stored flag on the list query | `base.py:78-95` | 🟢 |

## Internal State

The use case is stateless between requests. Persistent state it owns:

- the `aeroplanes` row — identity, `name`, `total_mass_kg`, `xyz_ref`, and the
  versioning pointers written at birth;
- the **first** `branches` row of each lineage (`main`, `is_main=true`), which
  `versioning` subsequently evolves.

`heads_only` is the only read-time projection of versioning state into this use
case.

## Observability

- `logger.exception` on 5xx and on the swallowed STEP-cleanup failure; 4xx are
  logged at INFO by the global handler (`app/main.py` error handlers). 🟢
- No metrics, traces or structured event emission. 🟢
- No domain event is published on create or delete — the event bus
  (`GeometryChanged`, `AssumptionChanged`) is driven by `wing-design` and
  `mission-and-sizing`, not here. 🟢

## Risks and Gaps

- 🟢 **The `IntegrityError` handler is removed from the aeroplane path and its
  message translated.** It claimed a name collision for any integrity violation,
  on a column with no unique constraint, so it could only ever misreport the
  cause (`Q-AC-2`); the German strings are translated (`Q-CC-5`).
- 🟡 **Dead legacy router — to be deleted.** `app/api/v2/endpoints/aeroplane.py`
  is shadowed by the package `aeroplane/`; it wires only 3 of 24 sub-routers and
  is never imported. Disposition is *delete* under `P-DEAD-0` rule 3 (`Q-CC-6`),
  but that is a derivation from policy rather than a maintainer decision, so it
  stays INFERRED until the deletion lands.
- 🟡 **`SQLALCHEMY_DATABASE_URL` folds into the merged settings class**
  (`Q-CC-4`, maintainer-answered) — with one conditional exception: it **may**
  remain a bare `os.getenv` read in `app/db/session.py:8-11` **if** Alembic
  requires it before the settings object can be constructed. That condition is
  to be verified during implementation, so the outcome is not yet determined.
- 🟡 **`AeroplaneSchema.wings` is an `OrderedDict` whose first entry is not
  necessarily the main wing.** The main wing is derived as the largest planform
  area (gh-788 / gh-1092); consumers must not assume `wings[0]`.
- 🟡 **Delete does not reach the component tree.** `component_tree.aeroplane_id`
  is a plain indexed String rather than an FK, so tree rows survive the cascade
  — see [`../component-tree/design.md`](../component-tree/design.md).
- 🟡 **`heads_only` semantics depend on `versioning`.** If a lineage's branch
  rows were ever lost, the aeroplane would silently disappear from the default
  list while remaining readable by UUID.
