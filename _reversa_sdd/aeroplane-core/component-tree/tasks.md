# component-tree — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] Persistence layer available with the `get_db()` request-scoped session that
      **owns the transaction** (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`) and
      the global error-envelope handler.
- [ ] `aeroplanes` table available with its public `uuid` column — the tree keys
      off that UUID (see [`../aeroplane-crud/tasks.md`](../aeroplane-crud/tasks.md) T-01).
- [ ] `components` table available for `component_id` / `material_id` references.
- [ ] Construction parts available (module `construction-plans`) for the snapshot
      on create; the snapshot degrades to a no-op without them.
- [ ] [`weight-rollup`](../weight-rollup/tasks.md) available — `get_tree`
      decorates the assembled tree with its computed fields, and every write
      triggers its fire-and-forget mass sync.

## Tasks

- [ ] **T-01 — `component_tree` table and `ComponentTreeNodeModel`.**
  `aeroplane_id` as an **indexed String** holding the aeroplane UUID (note: not
  an FK — see Pending Gaps), `parent_id`, `sort_index`, `node_type`,
  `weight_override_g`, `component_id`, `quantity`, `construction_part_id`,
  `volume_mm3`, `area_mm2`, `material_id`, `print_type`, `print_resolution_mm`,
  `scale_factor`, `synced_from`.
  - Legacy origin: `app/models/component_tree.py:12-16`
  - Definition of done: nodes can be created for an aeroplane UUID and queried by
    it in one indexed lookup.
  - Confidence: 🟢

- [ ] **T-02 — `_build_tree` (orphan-tolerant assembly).**
  Pass 1 builds `id → node`; pass 2 attaches each node to its `parent_id`; a node
  whose parent is absent from the map becomes a **root**. Sort children and roots
  by `sort_index`.
  - Legacy origin: `app/services/component_tree_service.py:58-79`
  - Definition of done: a node pointing at a deleted parent still appears, as a
    root, in the response; siblings come back in `sort_index` order.
  - Confidence: 🟢

- [ ] **T-03 — `get_tree` single-query load.**
  Load every node for the aeroplane UUID in one indexed query, then assemble in
  memory. No per-node queries during traversal.
  - Legacy origin: `app/services/component_tree_service.py:123-160`
  - Definition of done: a tree of N nodes triggers a constant number of SQL
    statements, verified by a query counter.
  - Confidence: 🟢

- [ ] **T-04 — Node create (`POST ``) with type discrimination.**
  Accept `node_type` ∈ `{group, cad_shape, cots}` as a free-text column, persist
  `parent_id` and `sort_index`, answer **201** with the new node id.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/component_tree.py:52-128`
  - Definition of done: a `group` node with no `parent_id` appears as a root on
    the next read; the response status is 201.
  - Confidence: 🟢

- [ ] **T-05 — `_snapshot_construction_part_fields`.**
  Copy `volume_mm3` / `area_mm2` / `material_id` from the referenced construction
  part **only** for fields absent from `data.model_dump(exclude_unset=True)`.
  - Legacy origin: `app/services/component_tree_service.py:162-187`
  - Definition of done: an explicitly supplied `volume_mm3` survives the
    snapshot; an omitted one is filled from the part.
  - Confidence: 🟢

- [ ] **T-06 — Partial node update (`PUT /{node_id}`).**
  Apply only the fields present in the payload; omitted fields are untouched.
  Answer **200**; unknown node → **404**.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/component_tree.py:52-128`
  - Definition of done: patching `quantity` alone leaves `weight_override_g`
    unchanged.
  - Confidence: 🟢

- [ ] **T-07 — Node delete (`DELETE /{node_id}`) with subtree removal.**
  Remove the node; descendants follow via the relationship cascade. Answer
  **200**; unknown node → **404**.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/component_tree.py:52-128`
  - Definition of done: deleting a parent removes its children in the same
    transaction.
  - Confidence: 🟡 — the cascade is inferred from the relationship
    configuration, not from explicit service code.

- [ ] **T-08 — `move_node` + `_is_descendant` cycle guard.**
  Walk the target parent's ancestor chain; if the moved node appears, raise
  `ValidationError` (→ **422**) **before** any mutation. Otherwise reassign
  `parent_id` and `sort_index`.
  - Legacy origin: `app/services/component_tree_service.py:324-325, 339-359`
  - Definition of done: moving A under its own descendant B returns 422 and
    leaves the tree byte-identical; a valid move returns 200.
  - Confidence: 🟢

- [ ] **T-09 — Group auto-sync hooks.**
  Expose `sync_group_for_wing` / `sync_group_for_fuselage` and
  `delete_synced_nodes("<kind>:<name>")` for `wing_service` / `fuselage_service`
  to call, using the `synced_from` prefix convention `wing:<name>` /
  `fuselage:<name>`. Import lazily inside the functions to break the cycle.
  - Legacy origin: `wing_service.create_wing:298-300`,
    `fuselage_service.delete_fuselage:179-181` (gh#108)
  - Definition of done: creating a wing yields a group node with
    `synced_from = "wing:<name>"`; deleting the wing removes it.
  - Confidence: 🟢

- [ ] **T-10 — REST layer for the five structural routes.**
  GET/POST ``, PUT/DELETE `/{node_id}`, POST `/move` exactly as listed in
  [`design.md`](design.md) §Interface, with the domain→HTTP mapping and a
  defensive `except Exception → 500` on every handler.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/component_tree.py:52-128`
  - Definition of done: contract tests assert every status code, including the
    201 on create and the 422 on a descendant move target.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path: build a tree.** Create a root group, two children and
      a grandchild; read the tree and assert the nesting and `sort_index`
      ordering (see [`requirements.md`](requirements.md) Acceptance Criteria).
- [ ] **TT-02 — Failure: move-node cycle rejection** returns 422 with
      `error.code == "validation_error"` and mutates nothing.
- [ ] **TT-03 — Orphan tolerance:** a node whose `parent_id` refers to a missing
      row is returned as a root, not dropped and not an error.
- [ ] **TT-04 — Partial update semantics:** patching one field leaves every other
      field untouched.
- [ ] **TT-05 — Construction-part snapshot** respects explicitly supplied fields
      and fills only omitted ones (both directions).
- [ ] **TT-06 — Subtree delete:** deleting a parent removes all descendants.
- [ ] **TT-07 — Query-count guard** on the tree read: constant statements for N
      nodes.
- [ ] **TT-08 — Unknown ids:** unknown aeroplane UUID and unknown `node_id` both
      return 404 with the `not_found` envelope on every route that takes them.
- [ ] **TT-09 — Group auto-sync round-trip:** creating a wing yields
      `synced_from = "wing:<name>"`; deleting the wing removes exactly that node
      and no sibling.
- [ ] **TT-10 — Sibling ordering** is by `sort_index`, applied to roots as well
      as children.

## Data Migration Tasks

- [ ] **TM-01 — Reconcile orphaned `component_tree` rows, then add the FK.**
      `aeroplane_id` becomes a real foreign key to `aeroplanes.uuid` (`Q-CC-7`),
      so pre-existing rows belonging to deleted aeroplanes must be reconciled
      before the migration can apply. Such rows are currently invisible — no
      aeroplane resolves them — yet still occupy the index. 🟢
- [ ] **TM-02 — Audit for pre-existing cycles.** Scan `component_tree` for a
      `parent_id` chain that revisits a node before enabling read-side depth
      limiting (`Q-AC-3`); a single cycle hangs every read of that aeroplane. 🟢
- [ ] **TM-03 — Backfill `node_type` NULLs, then add the CHECK constraint**
      (`Q-CC-9`). The constraint cannot be added while unconstrained values
      remain. 🟢

## Suggested Order

1. **T-01** first — nothing can be read or written without the table.
2. **T-02 → T-03** next: the assembly and the single-query load are the read
   path and are independently testable with hand-built rows.
3. **T-04 → T-07** are the write paths. T-05 blocks T-04 only for nodes carrying
   `construction_part_id`, so T-04 can land first with the snapshot stubbed.
4. **T-08** after T-02, because the cycle guard is only meaningful once the
   hierarchy exists; it is independent of T-04…T-07.
5. **T-09** after both `wing-design` and `fuselage-design` exist (bidirectional
   dependency, broken by lazy imports).
6. **T-10** last — the REST layer is thin and only wires what is already tested.

`weight-rollup` T-01…T-03 can proceed in parallel from T-02 onward, since it
consumes the assembled tree rather than the query.

## Resolved by the validation interview (2026-08-15)

- 🟢 **Read-side depth limiting** with a `DesignWarning` (`Q-AC-3`). The
  `move_node` write guard is not the intended level of protection on its own.
- 🟢 **`aeroplane_id` becomes a real FK** to `aeroplanes.uuid` (`Q-CC-7`),
  migrated now under SQLite because the orphaned-row defect exists today.
- 🟢 **`node_type` gains a DB CHECK constraint** (`Q-CC-9`).
- 🟢 **Negative `scale_factor` / `quantity` rejected at the schema** (`Q-AC-4`).
- 🟢 **A node with children cannot be deleted** (`Q-AC-10`) — a behaviour change:
  RF-12 previously read *"deleting a node removes its subtree"* and now reads
  *"a node with children cannot be deleted"* (409).
- **Is subtree deletion contractual or incidental?** Today it follows from the
  relationship cascade rather than explicit service logic; confirm it is intended
  behaviour before relying on it.
