# weight-rollup — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `component_tree` table and the assembled tree available — see
      [`../component-tree/tasks.md`](../component-tree/tasks.md) T-01…T-03. This
      use case decorates that structure; it does not build it.
- [ ] `components` table available with `mass_g` (COTS parts) and
      `density_kg_m3` (materials).
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy and the global error-envelope handler.
- [ ] `mass_cg_service.sync_component_tree_to_mass` available (module
      `mass-and-balance`) — or stubbed, since the sync is best-effort and the use
      case must work when it raises.

## Tasks

- [ ] **T-01 — `_calculate_own_weight` precedence chain.**
  First match wins, and each branch fixes the reported source:
  `weight_override_g → ("override")`, COTS `component.mass_g × quantity →
  ("cots")`, CAD-shape density formula `→ ("calculated")`, otherwise
  `(None, "none")`.
  - Legacy origin: `app/services/component_tree_service.py:461-474`, COTS branch
    `:432-439`
  - Definition of done: one unit test per branch of the chain, plus a test that
    an override beats a COTS mass on the same node.
  - Confidence: 🟢

- [ ] **T-02 — The two print formulas and the 0.4 default.**

  ```
  surface: area_mm2   * print_resolution_mm * density_kg_m3 / 1e6 * scale_factor
  volume:  volume_mm3                       * density_kg_m3 / 1e6 * scale_factor
  print_resolution_mm defaults to 0.4
  ```

  Result unit: grams.
  - Legacy origin: `app/services/component_tree_service.py:442-458`
  - Definition of done: a volume print of 1 000 000 mm³ at 1 200 kg/m³ with
    `scale_factor` 1.0 yields exactly 1 200 g; a surface print with no
    `print_resolution_mm` computes as if 0.4 were supplied.
  - Confidence: 🟢

- [ ] **T-03 — Pre-compute own weights before the recursion.**
  One `id → (grams, source)` dict built ahead of the traversal so the roll-up
  issues no queries.
  - Legacy origin: `app/services/component_tree_service.py:133-137`
  - Definition of done: a tree of N nodes triggers a constant number of SQL
    statements, verified by a query counter.
  - Confidence: 🟢

- [ ] **T-04 — `_roll_up_weights` post-order traversal with the status ladder.**
  `total = (own or 0) + Σ children`; status
  `valid` / `partial` / `invalid` per the rule in [`design.md`](design.md) §F3.
  - Legacy origin: `app/services/component_tree_service.py:82-120`
  - Definition of done: table-driven tests over leaf-valid, leaf-invalid,
    parent-all-valid, parent-all-invalid **with** and **without** own weight, and
    mixed, reproducing the exact status values.
  - Confidence: 🟢

- [ ] **T-05 — `get_aircraft_total_weight_kg`.**
  Sum own + recursive children over all `parent_id IS NULL` roots in grams,
  divide by 1000, and return **`None`** for an empty tree.
  - Legacy origin: `app/services/component_tree_service.py:381-403`
  - Definition of done: empty tree ⇒ `null`; a 350 g tree ⇒ `0.35`. A test must
    fail if the empty case ever returns `0` or `0.0`.
  - Confidence: 🟢

- [ ] **T-06 — `_sync_aircraft_mass` fire-and-forget.**
  Lazy-import `mass_cg_service.sync_component_tree_to_mass` **inside** the
  function (breaking the `component_tree_service ↔ mass_cg_service` cycle) and
  swallow every exception with a log line.
  - Legacy origin: `app/services/component_tree_service.py:362-378`
  - Definition of done: with the sync patched to raise, every tree CRUD route
    still returns its success status and the node is persisted; the failure is
    logged. A module-level import must not reintroduce the cycle — verify with an
    import-order test.
  - Confidence: 🟢

- [ ] **T-07 — Decorate the tree read with the computed fields.**
  Attach `own_weight_g`, `weight_source`, `total_weight_g` and `weight_status` to
  every node of the response; none of them is persisted.
  - Legacy origin: `app/services/component_tree_service.py:82-120, 123-160`
  - Definition of done: a read returns all four fields on every node, and a
    second read after no writes returns identical values without any UPDATE
    statement being issued.
  - Confidence: 🟢

- [ ] **T-08 — `GET /component-tree/weight` route.**
  200 with `total_weight_kg` (nullable), 404 for an unknown aeroplane UUID,
  defensive `except Exception → 500`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/component_tree.py:52-128`
  - Definition of done: contract tests assert 200 + `null` for an empty tree,
    200 + a number for a populated one, and 404 for an unknown UUID.
  - Confidence: 🟢

- [ ] **T-09 — Wire the sync into every structural write.**
  Create, update, delete and move in
  [`component-tree`](../component-tree/tasks.md) all call
  `_sync_aircraft_mass` after their mutation.
  - Legacy origin: `app/services/component_tree_service.py:324` (move) and the
    surrounding CRUD functions
  - Definition of done: each of the four write paths triggers exactly one sync
    attempt, verified with a spy.
  - Confidence: 🟡 — the call sites are inferred from the module-level
    description; confirm each against the legacy CRUD functions.

## Test Tasks

- [ ] **TT-01 — Own-weight precedence matrix:** override > cots > calculated >
      none, both print types, `print_resolution_mm` default 0.4, `scale_factor`
      applied in both formulas.
- [ ] **TT-02 — Failure: a node with no usable source** reports
      `own_weight_g = null` and `weight_source = "none"` without raising.
- [ ] **TT-03 — Weight roll-up matrix:** leaf valid/invalid; parent all-valid,
      all-invalid with and without own weight, mixed. Assert both
      `total_weight_g` and `weight_status` (see
      [`requirements.md`](requirements.md) Acceptance Criteria).
- [ ] **TT-04 — Missing own weight contributes zero but degrades status:** a
      parent with one 100 g child and one `none` child totals 100 and reports
      `partial`.
- [ ] **TT-05 — Empty tree weight is `null`**, not `0`.
- [ ] **TT-06 — Kilogram conversion:** a 350 g tree reports `0.35`.
- [ ] **TT-07 — Best-effort sync:** patch `mass_cg_service` to raise; create,
      update, delete and move all still succeed.
- [ ] **TT-08 — Query-count guard** on the tree read: constant statements for N
      nodes (guards T-03).
- [ ] **TT-09 — Nothing is persisted:** a tree read issues no `UPDATE` or
      `INSERT`; `total_weight_g` and `weight_status` are absent from the table.
- [ ] **TT-10 — Import-cycle guard:** importing `component_tree_service` at
      module load must not import `mass_cg_service`.
- [ ] **TT-11 — COTS edge cases:** a component with `mass_g = 0` reports `0 g`
      with source `"cots"` and status `valid`; a COTS node whose component is
      missing falls through to `"none"`. 🟡 confirm against the legacy branch.

## Data Migration Tasks

None. This use case persists nothing of its own — `total_weight_g` and
`weight_status` are computed at read time and have never had columns
(`BR-WR8`). 🟢

## Suggested Order

1. **T-01 → T-02** first: the precedence chain and the formulas are pure
   functions and are testable against hand-built nodes with no tree at all.
2. **T-04** next, driven by the dict from T-03 — but T-04 can be developed
   against a hand-built `own` dict before T-03 exists, so the two are only
   loosely coupled.
3. **T-03** once T-01 is stable, since the dict is populated by it. T-03 blocks
   the query-count guarantee (TT-08), not correctness.
4. **T-05** after T-04 — the aircraft total is the same traversal reduced over
   the roots.
5. **T-06** independently at any point; it has no dependency on the arithmetic.
   **T-09** follows T-06 and needs the `component-tree` CRUD paths to exist.
6. **T-07, T-08** last — the response decoration and the route are thin over
   everything above.

## Resolved by the validation interview (2026-08-15)

- 🟢 **Read-side depth limiting** with a `DesignWarning` (`Q-AC-3`,
  maintainer-answered). The `move_node` write guard
  ([`../component-tree/tasks.md`](../component-tree/tasks.md)) is explicitly not
  the intended level of protection on its own.
- 🟢 **Negative `scale_factor` / `quantity` are rejected at the schema**
  (`Q-AC-4`, maintainer-answered) — they would subtract from the aircraft total.
- 🟡 **A failing mass sync emits a `DesignWarning`** rather than only logging
  (`Q-AC-7`), without blocking tree CRUD. Derived from `P-WARN-0`.
- 🟡 **`GET /weight` declares incompleteness through the shared `warnings`
  channel**, not a bespoke coverage field (`Q-AC-8`). Derived from `P-WARN-0`
  with `Q-MB-1`.
