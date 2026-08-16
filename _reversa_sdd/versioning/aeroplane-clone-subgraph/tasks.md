# aeroplane-clone-subgraph — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] Every cloned model exists with its relationships:
      `AeroplaneModel`, `WingModel`, `WingXSecModel`, `WingXSecDetailModel`,
      `WingXSecSpareModel`, `WingXSecTurbulatorModel`,
      `WingXSecTrailingEdgeDeviceModel`, `WingXSecTedServoModel`,
      `FuselageModel`, `FuselageXSecSuperEllipseModel`, `WeightItemModel`,
      `MissionObjectiveModel`, `DesignAssumptionModel`,
      `AircraftComputationConfigModel`, `StabilityResultModel`,
      `LoadingScenarioModel`, `ComponentTreeNodeModel`.
- [ ] `component_tree.aeroplane_id` is a **String** holding the aeroplane UUID
      (not an integer FK) — module `aeroplane-core`.
- [ ] `get_db()` request-scoped session (ADR 0009). The clone flushes, never
      commits.
- [ ] A test harness able to introspect SQLAlchemy `ForeignKey` objects, for the
      coverage test.

## Tasks

- [ ] **T-01 — `CLONED_TABLES` (17).**
  `aeroplanes`, `wings`, `wing_xsecs`, `wing_xsec_details`, `wing_xsec_spares`,
  `wing_xsec_trailing_edge_devices`, `wing_xsec_turbulators`,
  `wing_xsec_ted_servos`, `fuselages`, `fuselage_xsecs`, `weight_items`,
  `mission_objectives`, `design_assumptions`, `aircraft_computation_config`,
  `stability_results`, `loading_scenarios`, `component_tree`.
  - Legacy origin: `app/services/aeroplane_clone_service.py:70-92`
  - Definition of done: a `frozenset[str]`; each entry carries the inline
    comment explaining **how** the table is owned (which FK), because that is
    what tells the next contributor whether their new table belongs here.
  - Confidence: 🟢

- [ ] **T-02 — `EXCLUDED_TABLES` (18) with mandatory reasons.**
  A `dict[str, str]` grouped as: shared library (`rc_flight_profiles`,
  `rc_flight_profile_entries`, `components`, `component_types`, `airfoils`,
  `airfoil_low_re`, `mission_presets`), transient (`operating_points`,
  `operating_pointsets`, `flight_envelopes`), conversation
  (`copilot_messages`), versioning meta (`branches`), construction
  (`construction_plans`, `construction_parts`), caches (`tessellation_cache`,
  `avl_geometry_files`), non-tables (`avl_geometry_events`, `stability_events`,
  `alembic_version`).
  - Legacy origin: `app/services/aeroplane_clone_service.py:95-132`
  - Definition of done: a `dict`, not a `set`, so a reason cannot be omitted;
    every reason is non-empty and states **why**, not just *that*.
  - Confidence: 🟢

- [ ] **T-03 — The blind-spot comment.**
  Reproduce the block above `CLONED_TABLES` explaining that the coverage test
  introspects `ForeignKey` objects and therefore cannot see string-FK tables,
  naming the three that exist today.
  - Legacy origin: `app/services/aeroplane_clone_service.py:56-69`
  - Definition of done: the comment sits **immediately above** the constant a
    contributor would edit. This is documentation as a control, not decoration.
  - Confidence: 🟢

- [ ] **T-04 — The coverage test.**
  Discover every table transitively related to `aeroplanes` by introspecting
  SQLAlchemy `ForeignKey` objects; assert each discovered table is in exactly
  one set; assert the sets are disjoint; assert every exclusion reason is
  non-empty.
  - Legacy origin: `app/tests/test_aeroplane_clone_coverage.py`
  - Definition of done: adding a throwaway model with an FK to `aeroplanes`
    makes the test fail; removing it makes it pass. The failure message names
    the offending table.
  - Confidence: 🟢

- [ ] **T-05 — `clone_aeroplane_subgraph` group 1 — the root row.**
  New `uuid4`; copy `name` and `total_mass_kg`; **keep** `flight_profile_id`;
  `copy.deepcopy` for `xyz_ref` and `assumption_computation_context`; take
  `is_immutable`, `branch_id`, `predecessor_id` and `root_id` from the caller;
  set the five version-metadata columns to `None`.
  - Legacy origin: `app/services/aeroplane_clone_service.py:184-206`
  - Definition of done: mutating the clone's context does not affect the
    source's (proves the deep copy); the five metadata columns are `None`
    regardless of the source's values.
  - Confidence: 🟢

- [ ] **T-06 — Group 2 — weight items and `weight_id_map`.**
  Copy each item; flush; record `weight_id_map[str(old.id)] = str(new.id)`.
  - Legacy origin: `app/services/aeroplane_clone_service.py:207-225`
  - Definition of done: the map's keys and values are **strings** — a test must
    fail if they are ints, because `component_overrides` stores stringified ids.
  - Confidence: 🟢

- [ ] **T-07 — Group 3 — the five-level wing hierarchy.**
  `wings → wing_xsecs → wing_xsec_details → {spares, turbulators (1:1,
  gh-1069), TEDs → ted_servos}`, flushing between levels so each child can
  reference its new parent. `ted_servo.component_id` is **kept**.
  - Legacy origin: `app/services/aeroplane_clone_service.py:226-338`
  - Definition of done: a fixture with all five levels round-trips with the same
    shape; the servo still points at the same component id.
  - Confidence: 🟢

- [ ] **T-08 — Group 4 — fuselages with nulled STEP paths.**
  `fuselages → fuselage_xsecs`; `step_path` and `solid_step_path` → `None`.
  - Legacy origin: `app/services/aeroplane_clone_service.py:339-361`
  - Definition of done: a source fuselage with both paths set yields a clone
    with both `None` — a test must fail if either is copied.
  - Confidence: 🟢

- [ ] **T-09 — Groups 5-8 — the flat owned tables.**
  `mission_objectives` (1:1), `design_assumptions` (estimate + calculated +
  `active_source` + divergence), `aircraft_computation_config` (1:1),
  `stability_results` (**including `computed_at` and `geometry_hash`**).
  - Legacy origin: `app/services/aeroplane_clone_service.py:362-438`
  - Definition of done: the assumption triple survives intact (ADR 0010); the
    stability result keeps its original timestamp and hash — reproduce this and
    record the ambiguity for mutable branch heads as a gap.
  - Confidence: 🟢

- [ ] **T-10 — `_remap_component_overrides`.**
  Deep-copy; walk `toggles`, `mass_overrides`, `position_overrides`; rewrite
  each `component_uuid` via `weight_id_map.get(old, old)`; skip non-dict
  entries; short-circuit on empty overrides or an empty map.
  - Legacy origin: `app/services/aeroplane_clone_service.py:463-491`
  - Definition of done: a weight-item id is re-keyed, a COTS uuid is untouched,
    `None` and `{}` are handled, and a non-dict list entry does not raise. The
    `.get(old, old)` fallback must be explicit — replacing it with `map[old]`
    would raise on every COTS reference.
  - Confidence: 🟢

- [ ] **T-11 — Group 9 — loading scenarios.**
  Copy each scenario with the remapped overrides.
  - Legacy origin: `app/services/aeroplane_clone_service.py:439-450`
  - Definition of done: a scenario referencing weight item `"7"` points at the
    clone's copy of it — assert against the clone's actual weight-item ids, not
    a literal.
  - Confidence: 🟢

- [ ] **T-12 — `_clone_component_tree` — pass 1.**
  Fetch by `aeroplane_id == str(source.uuid)` ordered by `id`; insert each node
  with `parent_id=None` and `aeroplane_id=str(clone.uuid)`; flush per node;
  collect `id_map[old] = new`. Keep `component_id`, `construction_part_id` and
  `material_id` unchanged.
  - Legacy origin: `app/services/aeroplane_clone_service.py:494-554`
  - Definition of done: **every** column of `ComponentTreeNodeModel` is copied —
    verify field-by-field against the model, not against the legacy call list,
    because a column added later and forgotten here is lost on every version.
  - Confidence: 🟢

- [ ] **T-13 — `_clone_component_tree` — pass 2 and the warning.**
  For each source node with a parent, `UPDATE` the cloned node's `parent_id` via
  `id_map`; an unmappable parent leaves `None` and logs a warning naming the
  cloned id, the source id, the source `parent_id` and both aeroplane ids.
  - Legacy origin: `app/services/aeroplane_clone_service.py:556-580`
  - Definition of done: a three-level tree keeps its shape; a node whose parent
    belongs to another aeroplane becomes a root **and** produces the warning.
  - Confidence: 🟢

- [ ] **T-14 — Flush discipline and the return contract.**
  A `db.flush()` after each group; a final flush before returning; **no**
  `db.commit()` anywhere. The function returns the clone with all children
  already added to the session.
  - Legacy origin: `app/services/aeroplane_clone_service.py:454-455`
  - Definition of done: a rollback after a clone leaves nothing persisted; a
    grep-style test asserts the module contains no `db.commit()` /
    `db.begin()`.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Coverage:** exhaustive, disjoint, reasons non-empty; a new FK
      table fails the test.
- [ ] **TT-02 — Full-fidelity clone:** a fixture exercising all 17 tables; every
      table has clone rows; no PK is shared.
- [ ] **TT-03 — Identity:** new `uuid4`; the five version columns `None`.
- [ ] **TT-04 — Deep copy:** mutating the clone's `assumption_computation_context`
      and `xyz_ref` leaves the source untouched.
- [ ] **TT-05 — Caller-supplied versioning columns** appear exactly as passed,
      including `branch_id=None` and `root_id=None`.
- [ ] **TT-06 — Shared references:** `flight_profile_id`,
      `ted_servo.component_id`, tree `component_id` / `construction_part_id` /
      `material_id` all identical.
- [ ] **TT-07 — STEP paths nulled.**
- [ ] **TT-08 — Weight-id map:** string keys and values.
- [ ] **TT-09 — Override remapping:** weight id re-keyed · COTS uuid untouched ·
      `None` / `{}` / non-dict entry handled.
- [ ] **TT-10 — Tree shape:** three levels preserved; `aeroplane_id` is the
      clone's uuid string.
- [ ] **TT-11 — Tree column completeness:** assert every column of
      `ComponentTreeNodeModel` is non-default on the clone when it was
      non-default on the source (guards the silent-drop risk).
- [ ] **TT-12 — Unmappable parent:** `parent_id` `None` + the warning naming
      both ids.
- [ ] **TT-13 — Empty cases:** no weight items · no tree · no loading scenarios
      · no wings — each clones without error.
- [ ] **TT-14 — Transaction:** a rollback leaves nothing; the module contains no
      `commit`.
- [ ] **TT-15 — Assumption triple:** estimate, calculated, `active_source` and
      divergence all survive.
- [ ] **TT-16 — Stability result (characterisation):** `computed_at` and
      `geometry_hash` are the source's, not the clone time's.
- [ ] **TT-17 — Statement count (characterisation):** a 50-node tree issues
      ~2× 50 statements, documenting the O(n) cost of the two passes.

## Data Migration Tasks

None — the clone creates rows at runtime and owns no schema of its own. 🟢

Its **inputs** carry the migration dependencies: every cloned table must exist
with its current column set, and `component_tree.aeroplane_id` must be the
aeroplane's UUID **string** (a mismatch here silently produces an empty tree on
every clone).

## Suggested Order

1. **T-01 → T-04** — the registry and its test **first**. The test is what tells
   you the table list is complete, and writing the copy code before it invites
   an incomplete clone that looks correct.
2. **T-05 → T-06** the root row and the weight-id map, in that order: group 2
   depends on `clone.id` from group 1, and group 9 depends on the map.
3. **T-07 → T-09** the bulk groups. T-07 (the five-level wing hierarchy) is the
   largest and benefits from a fixture built once and reused by every later
   test.
4. **T-10 → T-11** the override remapping. T-10 is a pure function and should be
   unit-tested against literals before T-11 wires it in.
5. **T-12 → T-13** the component tree last among the copy tasks — it is the only
   string-FK table, needs two passes, and its warning path is the module's most
   valuable log line.
6. **T-14** as a continuous constraint rather than a final step: assert the
   no-commit rule from the first test onward, because a stray `commit()` added
   mid-implementation is hard to find later.

## Pending Gaps

- **How is the coverage blind spot closed?** Any future table with a string
  aeroplane reference is invisible to the test and will silently not be cloned.
  Options: a naming convention the test can detect, an explicit registry of
  string-FK tables, or converting them to real FKs.
- **Should the copied *column* set be verified?** The registry checks tables,
  not fields; a column added to a cloned model and forgotten in the constructor
  is lost on every version, with no test failing.
- **Should `root_id=None` be rejected**, or should the clone set it to the new
  id itself, rather than trusting the caller?
- **Should the tree clone be batched?** Pass 1 flushes per node and pass 2
  issues one `UPDATE` per node — O(n) round-trips twice per snapshot.
- **Should a cloned mutable head keep the source's `computed_at` and
  `geometry_hash`** on its stability results, given it is about to diverge?
- **Should `_remap_component_overrides` be data-driven** rather than hard-coding
  three list keys, so a future override category cannot be silently missed?
- **Should the clone be bounded** by node count or time, and should it log its
  success path with a row count?
- **Should storage growth be measured**, given that every snapshot duplicates
  the whole design subgraph?
</content>
