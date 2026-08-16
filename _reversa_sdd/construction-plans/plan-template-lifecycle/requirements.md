# plan-template-lifecycle

> Use-case specification, nested under the module
> [`construction-plans`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: construction-plans
> (Domain model), `_reversa_sdd/data-dictionary.md` §Table `construction_plans`,
> `_reversa_sdd/state-machines.md` §6.

## Overview

`plan-template-lifecycle` owns the **storage and shape** of a construction plan:
one table holding both reusable templates and aeroplane-bound plans, discriminated
by a free-text `plan_type`; deep-copy conversion in both directions; a
deliberately thin write-time validation; and a silent legacy-root migration that
runs on every read. There is no status column and no state machine — only a
duality. 🟢

## Responsibilities

- Store a serialised `ConstructionRootNode` tree as `construction_plans.tree_json`
  and expose CRUD over it. 🟢
- Discriminate templates (`aeroplane_id IS NULL`) from aeroplane-bound plans via
  `plan_type`. 🟢
- Instantiate a template into a plan and lift a plan into a template, both by
  `copy.deepcopy` with a derived name. 🟢
- Validate only the root of an incoming tree (`$TYPE` + `creator_id`). 🟢
- Compute `step_count` for list views, tolerating both successor encodings. 🟢
- Migrate a legacy `ConstructionStepNode` root to `ConstructionRootNode` on read. 🟢

**Explicitly NOT this use case's responsibility:** decoding or running a tree
(→ [`../plan-execution/`](../plan-execution/requirements.md)), reflecting over
Creator classes (→ [`../creator-catalog/`](../creator-catalog/requirements.md)),
the uploaded-file store (→
[`../construction-parts/`](../construction-parts/requirements.md)), the `$TYPE`
serialisation rules themselves (→ `cad-designer-topology`, frozen per ADR 0002),
and the artefact directories an execution leaves behind (→ `cad-generation`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CP1 — `plan_type` is the only discriminator; there is no status column
  and no lifecycle.** 🟢 `"template"` ⇒ reusable, `aeroplane_id IS NULL`;
  `"plan"` ⇒ bound to exactly one aeroplane. Both columns are **free text** with
  no enum and no check constraint (`app/models/construction_plan.py:11`;
  `plan_type` has `server_default "template"`). The only observable "state" is
  the set of artefact directories an execution leaves behind
  (`state-machines.md` §6).
- **BR-69 — A plan and its template diverge immediately.** 🟢
  *(module-level BR-69; this use case is its owner.)*

  ```
  instantiate_template(db, template_id, aeroplane_id, name=None):     # l.207-232
      plan = get_plan(template_id)                    # NotFoundError → 404
      assert plan.plan_type == "template"             # else ValidationError → 422
      assert aeroplane exists                         # else NotFoundError → 404
      new.tree_json    = copy.deepcopy(plan.tree_json)
      new.name         = name or f"{plan.name} — Plan"
      new.plan_type    = "plan"
      new.aeroplane_id = aeroplane_id
      # NO back-link, NO version column, NO lineage row

  to_template(db, plan_id, name=None):                               # l.235-251
      new.tree_json    = copy.deepcopy(plan.tree_json)
      new.name         = name or f"{plan.name} — Template"
      new.plan_type    = "template"
      new.aeroplane_id = None
  ```

  After either operation the two rows evolve completely independently: a fix to
  the template never reaches its instances, and the instances cannot be found
  from the template.
- **BR-70 — Plan validation is deliberately thin.** 🟢
  `_validate_tree_json` (l.72-81) raises `ValidationError` unless the **root**
  dict carries both `$TYPE` and `creator_id`. Nothing deeper is inspected — an
  unknown Creator, a malformed parameter or a broken successor is storable and
  fails only at execution time, inside `GeneralJSONDecoder`.
- **BR-71 — Renaming or deleting a Creator invalidates every stored plan that
  references it.** 🟢 A consequence of BR-70 plus `getattr`-based `$TYPE`
  resolution: the damage is invisible until the plan is run. Owned by
  `cad-designer-topology`; recorded here because this use case is what stores the
  now-dangling reference.
- 🔴 **BR-CP3 — The stored root shape is silently migrated on every read.** 🟢
  CONFIRMED behaviour / 🔴 on intent.

  ```
  _migrate_tree_json(plan):                                          # l.113-133
      if plan.tree_json.get("$TYPE") == "ConstructionStepNode":
          plan.tree_json["$TYPE"] = "ConstructionRootNode"
          plan.tree_json.pop("creator", None)
          flag_modified(plan, "tree_json")
          db.flush()
  ```

  It is called from `get_plan`, so **every** read of **every** plan can issue an
  `UPDATE`. There is no version marker, no audit trail, and no way to distinguish
  a migrated row from one that was always correct. A re-implementation should
  perform this once, as a data migration.
- **BR-CP1a — `step_count` excludes the root and accepts both successor
  encodings.** 🟢 `_count_steps` (l.38-53) reads `successors`, iterates
  `successors.values()` when it is a dict (the `GeneralJSONEncoder`
  `OrderedDict` form) or the list directly (the simplified form the frontend
  emits), counts each dict node once and recurses. A root with two children, one
  of which has one child, reports `3`.

### Persistence gaps

- 🔴 **BR-CP1b — `construction_plans.aeroplane_id` is a `String` foreign key to
  an `Integer` primary key.** 🟢 CONFIRMED. `aeroplanes.id` is `Integer`; the FK
  constraint is `fk_construction_plans_aeroplane_id` and carries **no
  `ON DELETE`**. SQLite's dynamic typing tolerates the mismatch; PostgreSQL would
  reject the constraint outright. Migrations:
  `b3e2f1a4c7d9_add_construction_plans_table.py` (base) and
  `c4d5e6f7a8b9_add_plan_type_and_aeroplane_id.py` (the two later columns).
- 🟡 **BR-CP1c — `name` is not unique.** Two plans may share a name; identity is
  the integer id alone.
- 🟡 **BR-CP1d — `PlanCreate` does not require `aeroplane_id` when
  `plan_type == "plan"`.** An unbound "plan" row is creatable and only fails when
  executed.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-PT-01 | List plans, optionally filtered by `plan_type` | Must | `GET /construction-plans?plan_type=template` → 200 returning only templates |
| RF-PT-02 | Create a plan from a `PlanCreate` payload | Must | → **201** `PlanRead`; a root without `$TYPE` or without `creator_id` → 422 |
| RF-PT-03 | Read a plan by integer id | Must | → 200 `PlanRead`; unknown id → 404 |
| RF-PT-04 | Update a plan, re-validating the root | Must | → 200; an invalidated root → 422 |
| RF-PT-05 | Delete a plan | Must | → **204**; unknown id → 404 |
| RF-PT-06 | Report `step_count` on list views | Should | A root with two children (one of which has a child) reports `3`; the dict and list successor forms agree |
| RF-PT-07 | Instantiate a template into an aeroplane-bound plan | Must | → **201**, `plan_type == "plan"`, name `"{template.name} — Plan"`, tree is a deep copy |
| RF-PT-08 | Reject instantiating a row whose `plan_type != "template"` | Must | → 422 before any row is written |
| RF-PT-09 | Reject instantiating against a non-existent aeroplane | Must | → 404 |
| RF-PT-10 | Lift a plan back into a template | Should | → **201**, `plan_type == "template"`, `aeroplane_id IS NULL`, name `"{plan.name} — Template"` |
| RF-PT-11 | Honour a `name` override on both conversions | Should | `{"name": "X"}` yields a row named exactly `X` |
| RF-PT-12 | Migrate a legacy `ConstructionStepNode` root on read | Must | The returned root has `$TYPE == "ConstructionRootNode"` and no `creator` key, and the change is persisted |
| RF-PT-13 | List a single aeroplane's plans | Must | `GET /aeroplanes/{id}/construction-plans` → 200 with only that aeroplane's plans |
| RF-PT-14 | Serve the template-only projection | Should | `GET /construction-templates` returns the same set as `?plan_type=template` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Instantiation must be a deep copy, so editing an instance never mutates its source | `construction_plan_service.py:207-232` (`copy.deepcopy`) | 🟢 |
| Correctness | The root validation must run on **both** create and update, or an invalid tree can be introduced by a `PUT` | `_validate_tree_json:72-81` | 🟢 |
| Compatibility | `step_count` must tolerate the frontend's list-shaped `successors` as well as the encoder's dict shape | `_count_steps:38-53` (docstring says so) | 🟢 |
| Compatibility | Legacy roots must remain readable without a manual migration step | `_migrate_tree_json:113-133` | 🟢 |
| Portability | 🟡 **Not met.** The `String`→`Integer` FK is valid only under SQLite's dynamic typing | `app/models/construction_plan.py` | 🟢 |
| Auditability | 🟡 **Not met.** The read-path migration mutates rows with no marker or log of what changed | `_migrate_tree_json:113-133` | 🟢 |
| Traceability | 🟡 **Not met.** No back-link from a plan to its source template | `instantiate_template:207-232` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Template and plan storage

  Scenario: A template is created and stored unbound
    Given a valid tree_json whose root has $TYPE and creator_id
    When I POST /construction-templates with it
    Then the response status is 201
    And plan_type is "template"
    And aeroplane_id is null

  Scenario: A root without creator_id is rejected at write time
    Given a tree_json whose root has $TYPE but no creator_id
    When I POST /construction-plans with it
    Then the response status is 422
    And no row is created

  Scenario: A malformed child is accepted at write time
    Given a tree_json whose root is valid but whose child references an unknown $TYPE
    When I POST /construction-plans with it
    Then the response status is 201
    # the failure is deferred to execution — BR-70

Feature: Instantiation and divergence

  Scenario: A template becomes an aeroplane-bound plan
    Given a template named "Wing recipe"
    And an aeroplane that exists
    When I POST /aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}
    Then the response status is 201
    And the new row has plan_type "plan"
    And its aeroplane_id is the aeroplane
    And its name is "Wing recipe — Plan"

  Scenario: The copy is deep
    Given a template that has been instantiated
    When I modify the instance's tree_json and save it
    Then the template's tree_json is unchanged

  Scenario: The plan keeps no reference to its template
    Given a plan created from a template
    When I read the plan
    Then no field identifies the template it came from
    # BR-69 — deliberate

  Scenario: Instantiating a plan instead of a template is rejected
    Given a row with plan_type "plan"
    When I POST from-template with that id
    Then the response status is 422

  Scenario: Instantiating against an unknown aeroplane is rejected
    Given a valid template
    When I POST from-template under an aeroplane id that does not exist
    Then the response status is 404

  Scenario: A plan is lifted back into a template
    Given a plan named "Wing recipe — Plan"
    When I POST .../to-template
    Then the response status is 201
    And the new row has plan_type "template"
    And its aeroplane_id is null
    And its name is "Wing recipe — Plan — Template"

Feature: Legacy root migration

  Scenario: A ConstructionStepNode root is rewritten on read
    Given a stored plan whose tree_json root has $TYPE "ConstructionStepNode"
    When I GET that plan
    Then the returned root has $TYPE "ConstructionRootNode"
    And the root has no "creator" key
    And re-reading the plan returns the migrated shape from the database

  Scenario: A correct root is left alone
    Given a stored plan whose root is already ConstructionRootNode
    When I GET that plan
    Then the tree_json is byte-identical to what was stored
    And no UPDATE is issued

Feature: Step counting

  Scenario: The root is not counted
    Given a root with two successors, one of which has one successor
    When I list plans
    Then step_count is 3

  Scenario: List-shaped successors count the same as dict-shaped ones
    Given the same tree encoded once with dict successors and once with list successors
    When I list plans
    Then both report the same step_count
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Plan CRUD (RF-PT-01…RF-PT-05) | Must | The substrate for every other slice; execution reads through `get_plan` |
| Root validation (RF-PT-02/RF-PT-04) | Must | The only write-time gate that exists; without it a root cannot even be decoded |
| Instantiation with a deep copy (RF-PT-07…RF-PT-09) | Must | The template's entire purpose; a shallow copy would corrupt the source |
| Legacy root migration (RF-PT-12) | Must | Without it every pre-migration plan fails at decode with a confusing error |
| Aeroplane-scoped listing (RF-PT-13) | Must | The workbench lists plans per aircraft |
| `to_template` (RF-PT-10) | Should | The reverse direction is a convenience; a template can also be authored directly |
| `step_count` (RF-PT-06) | Should | Presentation metadata for the gallery; a wrong count misleads but breaks nothing |
| Name overrides (RF-PT-11) | Should | Ergonomics; the derived name is always available |
| Template-only projection (RF-PT-14) | Could | Duplicates `?plan_type=template` |
| Template → plan back-link | **Won't** | Deliberately absent (BR-69). Adding it is a design change, not a re-implementation detail |
| A `plan_type` enum or check constraint | **Won't (today)** | Free text by construction; tightening it is a schema decision with a migration cost |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/construction_plan_service.py` | `_count_steps` (l.38-53), `_to_summary` (l.56-65), `_to_read` (l.68-69), `_validate_tree_json` (l.72-81), `_migrate_tree_json` (l.113-133), `get_plan`, `list_plans`, `create_plan`, `update_plan`, `delete_plan`, `instantiate_template` (l.207-232), `to_template` (l.235-251) | 🟢 |
| `app/api/v2/endpoints/construction_plans.py` | `list_plans`, `create_plan`, `get_plan`, `update_plan`, `delete_plan` | 🟢 |
| `app/api/v2/endpoints/aeroplane_construction_plans.py` | `list_aeroplane_plans`, `instantiate_template`, `plan_to_template` | 🟢 |
| `app/api/v2/endpoints/construction_templates.py` | `list_templates`, `create_template` | 🟢 |
| `app/models/construction_plan.py` | `ConstructionPlanModel` | 🟢 |
| `app/schemas/construction_plan.py` | `PlanCreate`, `PlanRead`, `PlanSummary`, `InstantiateRequest`, `ToTemplateRequest` | 🟢 |
| `alembic/versions/b3e2f1a4c7d9_…`, `c4d5e6f7a8b9_…` | table + `plan_type` / `aeroplane_id` columns | 🟢 |
