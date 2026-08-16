# aeroplane-crud

> Use-case specification, nested under the module [`aeroplane-core`](../requirements.md).
> Focuses on WHAT the use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aeroplane-core,
> `_reversa_sdd/data-dictionary.md` §Table `aeroplanes`, `_reversa_sdd/domain.md` §1.1.

## Overview

`aeroplane-crud` is the lifecycle of the **`Aeroplane` aggregate root**: list,
create, read, delete, and the design total mass. Every operation is addressed by
the public **UUID**, never by the integer PK. Creation is deliberately *not* a
single-row insert — since gh-903 an aeroplane is also the root of a versioning
lineage, so the create path writes three coupled rows in one transaction. 🟢

## Responsibilities

- List aeroplanes ordered by `name`, projecting away version snapshots by
  default (`heads_only`). 🟢
- Create an aeroplane **and** bootstrap its lineage — root pointer plus the
  `main` branch — atomically. 🟢
- Read the full nested aircraft (`AeroplaneSchema`: wings + fuselages + mass +
  `xyz_ref`) in one call, pre-materialising every lazy relation inside the
  session. 🟢
- Delete an aeroplane, cascading all owned rows, and attempt STEP artefact
  cleanup as a best-effort side effect. 🟢
- Read and upsert `total_mass_kg`, distinguishing create from update by HTTP
  status code. 🟢
- Translate domain exceptions into the module's HTTP error envelope. 🟢

**Explicitly NOT this use case's responsibility:** the `AirplaneConfiguration`
export (→ [`airplane-configuration-export`](../airplane-configuration-export/requirements.md)),
the component tree (→ [`component-tree`](../component-tree/requirements.md),
[`weight-rollup`](../weight-rollup/requirements.md)), and every branch/snapshot
operation after the birth of the lineage (→ module `versioning`).

## Business Rules

- **BR-AC1 — Every new aeroplane is born as a complete versioning node.** 🟢
  *(refines module rule BR-A1.)* `create_aeroplane` performs a three-step flush
  dance to satisfy the circular `aeroplanes ↔ branches` FK pair:

  ```
  1. aeroplane = AeroplaneModel(name=name); db.add(aeroplane)
  2. db.flush()                       # id assigned, nothing committed
  3. aeroplane.root_id = aeroplane.id # a lineage root points at itself
  4. branch = BranchModel(root_id=aeroplane.id, head_id=aeroplane.id,
                          name="main", is_main=True, created_by="human")
     db.add(branch); db.flush()
  5. aeroplane.branch_id = branch.id
  ```

  (`app/services/aeroplane_service.py:75-100`). The `flush()` calls are
  mandatory, not stylistic — the two FKs are mutually circular and are declared
  with `use_alter=True` so the DDL emits them as separate `ALTER TABLE`
  constraints (`app/models/aeroplanemodel.py:629-638, :691-706`).
- **BR-AC2 — Exactly one main branch per lineage, enforced by the schema.** 🟢
  *(refines BR-A2.)* The partial unique index
  `uq_branches_one_main_per_root` over `(root_id) WHERE is_main` makes a second
  main branch impossible to insert (`app/models/aeroplanemodel.py:616-624`).
  This is a **database** invariant, not an application check.
- **BR-AC3 — Eager materialisation before serialisation.** 🟢
  *(refines BR-A3.)* `get_aeroplane_schema` walks
  `wing.x_secs → detail → spares` and
  `detail.trailing_edge_device.servo_data`, plus the fuselages, purely to force
  the lazy loads *inside* the session — FastAPI serialises the response after
  the `get_db()` generator has closed
  (`app/services/aeroplane_service.py:141-149`). This is a deliberate
  workaround, **not** dead code; removing it produces `DetachedInstanceError`.
- **BR-AC4 — `GET /aeroplanes` hides snapshots by default.** 🟢
  *(refines BR-A7.)* `heads_only: bool = True` restricts the result to
  branch-head nodes so immutable version snapshots stay out of the picker
  (`app/api/v2/endpoints/aeroplane/base.py:78-95`).
- **BR-AC5 — Delete is cascade plus a best-effort side effect.** 🟢
  *(refines BR-A6.)* The ORM cascade removes wings, fuselages, weight items,
  assumptions, copilot messages, loading scenarios and stability results;
  afterwards `openvsp_step_export_service.cleanup_aeroplane_step_files()` runs
  inside a bare `try/except` that only logs
  (`app/services/aeroplane_service.py:191-198`). Orphaned STEP files are
  tolerated rather than blocking the delete.
- **BR-AC6 — Mass write is an upsert whose status code carries the outcome.** 🟢
  `set_aeroplane_mass` returns `True` when the value was newly created; the
  endpoint answers **201** in that case and **200** on update
  (`aeroplane_service.py:218`, `base.py:226`).
- **BR-AC7 — Transactions are owned by `get_db()`.** 🟢 *(refines BR-A16.)*
  The service calls `db.add()` / `db.flush()` and never `db.commit()` or
  `db.begin()` (ADR 0009, `app/db/session.py:55-64`).
- **BR-AC8 — Public identity is the UUID.** 🟢 Every route parameter named
  `aeroplane_id` is the `aeroplanes.uuid` column, never the integer PK
  (`contracts.md`, `AeroplaneModel.uuid` unique).
- 🟢 **`aeroplanes.name` is deliberately not unique.** Two aeroplanes may share a
  name and are distinguished only by UUID; UUID-only identity is the intended
  contract (`Q-AC-2`, maintainer-confirmed). It is also structurally required:
  a version is a real `aeroplanes` row (ADR 0006) and
  `aeroplane_clone_service.py:187` copies `name=source.name`, so a unique
  constraint would make every snapshot fail. Measured: 9 of 29 aircraft in the
  live database already share a name.
- 🟢 **The `IntegrityError` handler is removed from the aeroplane path, and its
  German string is translated.** It could only ever fire from a *different*
  constraint, so it reported the wrong cause (`Q-AC-2`). All German user-facing
  strings are translated to English (`Q-CC-5`, maintainer-answered); genuine
  integrity conflicts surface through the single error envelope (`Q-CC-3`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List all aeroplanes ordered by `name`; `heads_only=true` (default) restricts the result to branch-head nodes *(module RF-01)* | Must | `GET /aeroplanes` returns 200 with `aeroplanes[]`; a snapshot created by `versioning` is absent unless `heads_only=false` |
| RF-02 | Create an aeroplane by name and return its UUID, atomically creating the lineage root and the `main` branch *(module RF-02)* | Must | `POST /aeroplanes` → 201; the new row has `root_id == id`, `branch_id` set, and exactly one `branches` row with `is_main=true`, `name="main"`, `created_by="human"` |
| RF-03 | Read the full nested aircraft (wings, fuselages, mass, `xyz_ref`) by UUID *(module RF-03)* | Must | `GET /aeroplanes/{id}` → 200 `AeroplaneSchema` with every nested spar / TED / servo populated; unknown UUID → 404 |
| RF-04 | Delete an aeroplane, cascading all owned rows, and attempt STEP artefact cleanup *(module RF-04)* | Must | `DELETE /aeroplanes/{id}` → 200; the aeroplane and all children are gone; a cleanup failure does **not** fail the request |
| RF-05 | Read the design total mass *(module RF-05)* | Must | `GET /aeroplanes/{id}/total_mass_kg` → 200 with `total_mass_kg`; unknown UUID → 404 |
| RF-06 | Upsert the design total mass, distinguishing create from update by status code *(module RF-06)* | Must | First `POST .../total_mass_kg` → **201**, subsequent → **200**, stored value updated |
| RF-AC-07 | Map every domain exception onto the uniform error envelope | Must | `NotFoundError` → 404 `not_found`; `ValidationError` → 422 `validation_error`; `ConflictError` → 409 `conflict`; unexpected → 500 |
| RF-AC-08 | Preserve the wing / fuselage insertion order in the read model, while making no claim about which entry is the main wing | Should | Two wings read back in their stored order; the payload does not mark `wings[0]` as the main wing |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Response serialisation must not touch a closed session — nested relations are pre-materialised inside the request scope | `app/services/aeroplane_service.py:141-149` | 🟢 |
| Correctness | Exactly one `is_main` branch per lineage, enforced in the schema rather than only in code | `app/models/aeroplanemodel.py:616-624` | 🟢 |
| Correctness | The circular `aeroplanes ↔ branches` FK pair must be emitted as separate `ALTER TABLE` statements, otherwise the schema is unsatisfiable | `app/models/aeroplanemodel.py:629-638, :691-706` (`use_alter=True`) | 🟢 |
| Availability | Artefact cleanup on delete is best-effort: failure is logged, never propagated | `app/services/aeroplane_service.py:191-198` | 🟢 |
| Reliability | The transaction boundary is the request; a handler raising after partial writes leaves no committed partial state | `app/db/session.py:55-64` (ADR 0009) | 🟢 |
| Reliability | SQLite runs WAL + `synchronous=NORMAL` + `busy_timeout=30000` because the assumption recompute holds a write transaction for seconds | `app/db/session.py:15-52` | 🟢 |
| Security | No application-level authentication; the deployment tunnel is the trust boundary | ADR 0016 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Listing aeroplanes

  Scenario: Listing returns aeroplanes ordered by name
    Given aeroplanes named "Zephyr", "Albatross" and "Mistral"
    When I GET /aeroplanes
    Then the response status is 200
    And the names are returned in the order "Albatross", "Mistral", "Zephyr"

  Scenario: Listing hides immutable snapshots by default
    Given a lineage whose head has one immutable predecessor snapshot
    When I GET /aeroplanes
    Then only the head node is listed
    When I GET /aeroplanes?heads_only=false
    Then both nodes are listed

Feature: Creating an aeroplane

  Scenario: Creating an aeroplane also creates its lineage
    Given an empty database
    When I POST /aeroplanes with name "Trainer 1"
    Then the response status is 201
    And the response contains a UUID
    And the stored row has root_id equal to its own id
    And branch_id is not null
    And exactly one branches row exists with name "main", is_main true and created_by "human"

  Scenario: A second main branch for the same lineage is impossible
    Given an aeroplane whose lineage already has a main branch
    When a second branches row with the same root_id and is_main true is inserted
    Then the database raises an integrity error
    And the partial unique index uq_branches_one_main_per_root is the constraint named

Feature: Reading an aeroplane

  Scenario: Reading returns the fully materialised nested aircraft
    Given an aeroplane with one wing carrying a spar and a trailing-edge device with servo data
    When I GET /aeroplanes/{id}
    Then the response status is 200
    And the wing's spars are present in the payload
    And the trailing-edge device's servo data is present
    And no DetachedInstanceError is raised during serialisation

  Scenario: Reading an unknown aeroplane
    Given no aeroplane with UUID "00000000-0000-0000-0000-000000000000"
    When I GET /aeroplanes/00000000-0000-0000-0000-000000000000
    Then the response status is 404
    And the error code is "not_found"

Feature: Deleting an aeroplane

  Scenario: Deleting cascades to every owned row
    Given an aeroplane with wings, fuselages, weight items and design assumptions
    When I DELETE /aeroplanes/{id}
    Then the response status is 200
    And no wings, fuselages, weight items or design assumptions remain for that aeroplane

  Scenario: A failing artefact cleanup does not fail the delete
    Given cleanup_aeroplane_step_files raises an exception
    When I DELETE /aeroplanes/{id}
    Then the response status is 200
    And the aeroplane row is gone
    And the failure is logged

Feature: Total mass upsert

  Scenario: First write creates
    Given an aeroplane without total_mass_kg
    When I POST /aeroplanes/{id}/total_mass_kg with 2.4
    Then the response status is 201

  Scenario: Second write updates
    Given an aeroplane with total_mass_kg 2.4
    When I POST /aeroplanes/{id}/total_mass_kg with 2.6
    Then the response status is 200
    And the stored total_mass_kg is 2.6

  Scenario: Setting a mass on an unknown aeroplane
    Given no aeroplane with the requested UUID
    When I POST /aeroplanes/{id}/total_mass_kg with 2.4
    Then the response status is 404
    And the error code is "not_found"
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Read / list / delete by UUID (RF-01, RF-03, RF-04) | Must | Critical path — every other module resolves an aeroplane through this use case first |
| Lineage bootstrap on create (RF-02, BR-AC1/BR-AC2) | Must | Without it `versioning`, `ai-copilot` and the comparison UI have no anchor; the partial index makes a wrong write impossible to repair silently |
| Eager materialisation in the read model (BR-AC3) | Must | The workaround has **no fallback** — omitting it breaks every read with `DetachedInstanceError` |
| Total-mass upsert with 201/200 (RF-05, RF-06) | Must | Gate for the CAD export and input to `mass-and-balance` |
| Domain→HTTP error mapping (RF-AC-07) | Must | The uniform envelope is the frontend's only error contract |
| `heads_only` projection (BR-AC4) | Should | UX projection over `versioning` state; the data is still reachable with `heads_only=false` |
| Insertion-order preservation in the read model (RF-AC-08) | Should | Convenience for the workbench; correctness does not depend on it |
| Uniqueness on `aeroplanes.name` | Won't | Deliberately absent — UUID is the identity; adding it would break existing duplicate-named rows |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/aeroplane/base.py` | `get_aeroplanes` (l.76), `create_aeroplane` (l.130), `get_aeroplane` (l.154), `delete_aeroplane` (l.176), `get_aeroplane_total_mass_in_kg` (l.200), `create_aeroplane_total_mass_kg` (l.226), `_raise_http_from_domain` (l.52-67) | 🟢 |
| `app/services/aeroplane_service.py` | `list_all_aeroplanes` (l.47), `create_aeroplane` (l.61), `get_aeroplane_by_uuid` (l.106), `get_aeroplane_schema` (l.129), `delete_aeroplane` (l.169), `get_aeroplane_mass` (l.201), `set_aeroplane_mass` (l.218) | 🟢 |
| `app/models/aeroplanemodel.py` | `AeroplaneModel` (l.662), `BranchModel` (l.616-638), cascading relations (l.718-795) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `AeroplaneSchema` | 🟢 |
| `app/db/session.py` | `get_db` (l.55-64), SQLite PRAGMAs (l.15-52) | 🟢 |
| `app/services/openvsp_step_export_service.py` | `cleanup_aeroplane_step_files` | 🟢 (best-effort caller only) |
| `app/api/v2/endpoints/aeroplane.py` | legacy router module | 🔴 dead — never imported |
