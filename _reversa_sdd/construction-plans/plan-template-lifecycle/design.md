# plan-template-lifecycle — Technical Design

> Use-case design, nested under the module
> [`construction-plans`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/construction_plan_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_count_steps` | `(tree_json: dict) -> int` | `int` | recursive; accepts dict **and** list `successors`; root excluded (l.38-53) |
| `_to_summary` | `(plan: ConstructionPlanModel)` | `PlanSummary` | attaches `step_count` (l.56-65) |
| `_to_read` | `(plan)` | `PlanRead` | `model_validate(..., from_attributes=True)` (l.68-69) |
| `_validate_tree_json` | `(tree_json: dict)` | `None` | raises `ValidationError` on a root missing `$TYPE` or `creator_id` (l.72-81) |
| `_migrate_tree_json` | `(db, plan)` | `None` | `ConstructionStepNode` root → `ConstructionRootNode`, drops `creator`, `flag_modified` + flush (l.113-133) |
| `get_plan` | `(db, plan_id)` | `ConstructionPlanModel` | `NotFoundError` when absent; **calls `_migrate_tree_json`** |
| `list_plans` | `(db, plan_type: str \| None = None)` | `list[PlanSummary]` | optional discriminator filter |
| `create_plan` | `(db, request: PlanCreate)` | `PlanRead` | validates the root, inserts |
| `update_plan` | `(db, plan_id, request: PlanCreate)` | `PlanRead` | validates the root, replaces every field |
| `delete_plan` | `(db, plan_id)` | `None` | hard delete; no cascade to artefacts on disk 🟡 |
| `instantiate_template` | `(db, template_id, aeroplane_id, name=None)` | `PlanRead` | template → plan (l.207-232) |
| `to_template` | `(db, plan_id, name=None)` | `PlanRead` | plan → template (l.235-251) |

### Persistence — `construction_plans` 🟢

| Column | Type | Required | Default | Note |
|---|---|---|---|---|
| `id` | Integer PK | yes | autoincrement | the only identity |
| `name` | String | yes | — | **not unique** |
| `description` | String | no | `NULL` | |
| `tree_json` | JSON | yes | — | serialised `ConstructionRootNode` (`$TYPE` dialect) |
| `plan_type` | String | yes | `"template"` (`server_default`) | `"template"` \| `"plan"` — free text, no enum, no check constraint |
| `aeroplane_id` | String FK → `aeroplanes.id` (`fk_construction_plans_aeroplane_id`) | no | `NULL` | 🟡 **type mismatch** — `aeroplanes.id` is `Integer`; no `ON DELETE` |
| `created_at` | DateTime(tz) | yes | `now()` | |
| `updated_at` | DateTime(tz) | yes | `now()`, `onupdate` | |

Migrations: `b3e2f1a4c7d9_add_construction_plans_table.py` (base table),
`c4d5e6f7a8b9_add_plan_type_and_aeroplane_id.py` (the two later columns + FK). 🟢

## Main Flow

### F1 — Create / update 🟢

```
POST /construction-plans        body: PlanCreate
PUT  /construction-plans/{id}   body: PlanCreate

  _validate_tree_json(request.tree_json):                 # l.72-81
      "$TYPE"      not in root  → ValidationError("tree_json must contain a
                                   '$TYPE' field at the root level.")   → 422
      "creator_id" not in root  → ValidationError(…)                    → 422
      # nothing below the root is inspected — BR-70

  insert / update all columns verbatim
  → 201 (create) / 200 (update)  PlanRead
```

`POST /construction-templates` is the same path with `plan_type` forced to
`"template"`. 🟢

### F2 — Read, with the silent migration 🟢

```
get_plan(db, plan_id):
    plan = db.query(ConstructionPlanModel).get(plan_id)
    if plan is None: raise NotFoundError                  → 404
    _migrate_tree_json(db, plan)                          # l.113-133
    return plan

_migrate_tree_json(db, plan):
    tree = plan.tree_json or {}
    if tree.get("$TYPE") != "ConstructionStepNode":  return          # no-op
    tree["$TYPE"] = "ConstructionRootNode"
    tree.pop("creator", None)          # a root node carries no creator
    flag_modified(plan, "tree_json")   # JSON column: SQLAlchemy needs the hint
    db.flush()
```

Two details matter for a re-implementation:

1. `flag_modified` is **required** — mutating a JSON column in place does not
   mark the attribute dirty, so without it the change would be silently lost. 🟢
2. The flush happens inside a read path, so `GET` is not a pure read. Combined
   with `get_db()`'s commit-on-success (ADR 0009), a plain `GET` can commit a
   write. 🔴

### F3 — Instantiation and its inverse 🟢

```
instantiate_template(db, template_id, aeroplane_id, name=None):     # l.207-232
    template = get_plan(db, template_id)                # 404 if absent
    if template.plan_type != "template":
        raise ValidationError(...)                      → 422
    aeroplane = <resolve by UUID>                       # 404 if absent
    row = ConstructionPlanModel(
        name         = name or f"{template.name} — Plan",
        description  = template.description,
        tree_json    = copy.deepcopy(template.tree_json),   # DEEP — BR-69
        plan_type    = "plan",
        aeroplane_id = aeroplane_id,
    )
    db.add(row); db.flush()
    → 201 PlanRead

to_template(db, plan_id, name=None):                                # l.235-251
    plan = get_plan(db, plan_id)                        # 404 if absent
    row = ConstructionPlanModel(
        name         = name or f"{plan.name} — Template",
        description  = plan.description,
        tree_json    = copy.deepcopy(plan.tree_json),
        plan_type    = "template",
        aeroplane_id = None,
    )
    → 201 PlanRead
```

Note the asymmetry: `instantiate_template` **asserts** the source type,
`to_template` does not — lifting a template into another template is legal and
simply produces a copy. 🟢

The em dash in `" — Plan"` / `" — Template"` is literal, and the derived names
compound: instantiating `"X"` yields `"X — Plan"`; lifting that yields
`"X — Plan — Template"`. 🟢

### F4 — `step_count` 🟢

```
_count_steps(tree_json):                                             # l.38-53
    successors = tree_json.get("successors")
    if not successors: return 0
    nodes = successors.values() if isinstance(successors, dict) else successors
    count = 0
    for node in nodes:
        if isinstance(node, dict):
            count += 1
            count += _count_steps(node)
    return count
```

The dict branch is the `GeneralJSONEncoder` `OrderedDict` form; the list branch
is the "frontend simplified format" named in the docstring. Non-dict entries in a
list are skipped rather than raising, so a partially typed frontend payload
degrades to a lower count instead of a 500. 🟢

## Alternative Flows

- **Unknown plan id:** `NotFoundError` → 404 on every route. 🟢
- **Root missing `$TYPE` or `creator_id`:** `ValidationError` → 422 at create
  *and* update time; no row is written. 🟢
- **Valid root, broken children:** accepted and stored; the failure appears only
  when the plan is executed (`"Failed to decode construction plan: …"` → 422).
  🟢 This is BR-70 working as designed, and it is why a stored plan is not
  evidence that it can run.
- **Instantiating a non-template:** `ValidationError` → 422 before any row is
  created. 🟢
- **Instantiating against a missing aeroplane:** `NotFoundError` → 404. 🟢
- **Legacy root on read:** rewritten and persisted transparently; the caller
  cannot tell it happened. 🔴
- **`ConflictError` from any of these paths:** would surface as **500** — the
  routers' local `status_map` has no entry for it. No path raises it today. 🔴
- **Deleting a plan:** removes the row only. Artefact directories written by its
  past executions stay on disk under `<aeroplane>/<plan_id>/`, now unreachable
  through `GET .../artifacts` (which requires a plan). 🟡

## Dependencies

- **`aeroplane-core`** — aeroplane existence check on `instantiate_template` and
  on the aeroplane-scoped listing.
- **`platform-core`** — `get_db()` (ADR 0009), the exception hierarchy.
  `sqlalchemy.orm.attributes.flag_modified` for the JSON-column mutation.
- **`cad-designer-topology`** — defines the `$TYPE` dialect this slice stores but
  never interprets. The legacy migration encodes one piece of that knowledge
  (a root node has no `creator`), which is the single place this slice reaches
  into the format.
- **`plan-execution`** (sibling) — the only consumer that actually decodes
  `tree_json`; it reads through `get_plan` and therefore inherits the migration.
- **`cad-generation`** — artefact directories keyed by `plan_id`; this slice
  neither creates nor deletes them.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One table for both kinds of row, discriminated by a string column | `construction_plan.py:11`; `state-machines.md` §6 | 🟢 |
| `plan_type` is free text rather than an enum or check constraint | no constraint in either migration | 🟢 (intent 🟡) |
| Instantiation is a deep copy with no lineage — divergence is intended | `instantiate_template:207-232` | 🟢 |
| Derived names use a literal em dash and compound on repeated conversion | `f"{name} — Plan"` / `f"{name} — Template"` | 🟢 |
| Write-time validation covers the root only | `_validate_tree_json:72-81` | 🟢 |
| 🟢 A one-off Alembic data migration replaces the lazy read-time rewrite, which is then deleted (`Q-CP-7`, `R2-02`) | `_migrate_tree_json:113-133` | 🟢 (intent 🔴) |
| `step_count` tolerates two successor encodings rather than normalising on write | `_count_steps:38-53` docstring | 🟢 |
| `to_template` does not assert the source `plan_type`, while `instantiate_template` does | l.207-232 vs l.235-251 | 🟢 (intent 🟡) |
| Deleting a plan does not touch its artefacts | no `artifact_service` call in `delete_plan` | 🟢 (intent 🟡) |

## Internal State

This slice is stateless between requests. Persistent state is the
`construction_plans` table alone.

One subtlety worth recording: because `_migrate_tree_json` runs inside `get_plan`
and `get_db()` commits on success, the *first* read of a legacy plan mutates the
database. Any consumer that assumes `GET` is side-effect-free — a read replica, a
cache, a read-only session — is wrong for this route. 🔴

## Observability

- No logging on the migration path — 🟡 `P-WARN-0` requires the migration to report what it moved.
- No logging on create / update / delete beyond the framework's request log. 🟢
- `created_at` / `updated_at` are the only forensic signal, and the read-path
  migration bumps `updated_at` through `onupdate`, so a plan's `updated_at` can
  move without any user edit. 🟡

## Risks and Gaps

- 🔴 **The read path writes.** `_migrate_tree_json` mutates and flushes inside
  `get_plan`, so a `GET` can commit. No audit trail, no marker, no log line.
- 🔴 **`aeroplane_id` is a `String` FK to an `Integer` PK**, with no
  `ON DELETE`. The schema is creatable only under SQLite's dynamic typing, and
  deleting an aeroplane leaves its plans pointing at nothing.
- 🔴 **No back-link from a plan to its template.** A template fix cannot be
  propagated, and the instances of a template cannot be enumerated.
- 🔴 **`plan_type` is unconstrained free text.** A typo produces a row that is
  neither a template (it will not instantiate) nor a plan (it may still execute,
  since `execute_plan` only special-cases `"template"`).
- 🟡 **`PlanCreate.aeroplane_id` is optional even for `plan_type == "plan"`**, so
  an unbound "plan" is storable and fails only at execution.
- 🟡 **`to_template` accepts any source type**, so a template can be duplicated
  through it — harmless, but the asymmetry with `instantiate_template` is
  undocumented.
- 🟡 **Deleting a plan orphans its artefact directories** on disk with no
  cleanup path and no way to reach them through the API afterwards.
- 🟡 **`name` is not unique**, so the derived-name convention
  (`"X — Plan"`) can produce many identical names from repeated instantiation of
  the same template — which, absent a back-link, is the only hint they are
  related.
