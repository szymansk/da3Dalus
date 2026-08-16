# aeroplane-clone-subgraph

> Use-case specification, nested under the module
> [`versioning`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/aeroplane_clone_service.py`,
> `app/tests/test_aeroplane_clone_coverage.py`,
> `_reversa_sdd/data-dictionary.md` §Clone coverage registry, ADR 0006,
> ADR 0009. Endpoint contract: [`../contracts.md`](../contracts.md) (this use
> case has no route of its own).

## Overview

The **deep-clone engine**: `clone_aeroplane_subgraph` copies the full owned
subgraph of an aeroplane — 17 tables — into new rows with new primary keys,
re-keying every internal foreign key so the copy is a genuinely independent
aircraft, while preserving every *shared library* reference unchanged. It is the
single operation underneath snapshot, branch and restore. 🟢

Its correctness is protected by a **coverage registry**: every table with a
transitive FK to `aeroplanes` must appear in exactly one of `CLONED_TABLES` (17)
or `EXCLUDED_TABLES` (18), asserted by a test. 🟢

## Responsibilities

- Deep-copy the 17 owned tables in a fixed order, flushing after each group so
  auto-generated PKs are available for re-keying. 🟢
- Assign a fresh `uuid4` and the caller-supplied versioning metadata. 🟢
- Preserve shared library references; null artefact paths and version metadata.
  🟢
- Re-key `loading_scenarios.component_overrides` through a weight-id map. 🟢
- Re-key the component tree's `parent_id` in two passes, logging anything
  unmappable. 🟢
- Maintain the coverage registry, including the three string-FK tables the
  coverage test cannot see. 🟢
- Never commit. 🟢

**NOT this use case:** who calls it and why
(→ [`snapshot-immutability`](../snapshot-immutability/requirements.md),
[`branch-model`](../branch-model/requirements.md)), and the meaning of the
copied data (→ its owning modules).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-VR*` from
> [`../requirements.md`](../requirements.md); `BR-CL*` are new here.

- **ADR 0006 — Versioning is row copy.** 🟢 There is no serialised snapshot
  anywhere; a version is a real aircraft.
- **BR-39 — The clone registry must be exhaustive and disjoint.** 🟢
  `test_aeroplane_clone_coverage.py` discovers related tables by introspecting
  SQLAlchemy `ForeignKey` objects and asserts each appears in exactly one set,
  that the sets do not overlap, and that **every exclusion carries a non-empty
  reason string**.
- **BR-CL1 — The coverage test has a documented blind spot.** 🟢 It cannot see
  a table whose aeroplane reference is a plain `String` (no `ForeignKey`
  object). Three tables are in that category and are maintained **by hand**:
  `component_tree` (cloned), `construction_plans` and `construction_parts`
  (excluded) — 🟢 deliberate (`R2-06`): the chat follows the design only when the user says so. The source comment stays accurate.
- **BR-CL2 — `CLONED_TABLES` — 17 tables.** 🟢
  `aeroplanes`, `wings`, `wing_xsecs`, `wing_xsec_details`, `wing_xsec_spares`,
  `wing_xsec_trailing_edge_devices`, `wing_xsec_turbulators`,
  `wing_xsec_ted_servos`, `fuselages`, `fuselage_xsecs`, `weight_items`,
  `mission_objectives`, `design_assumptions`, `aircraft_computation_config`,
  `stability_results`, `loading_scenarios`, `component_tree`.
- **BR-CL3 — `EXCLUDED_TABLES` — 18 entries, each with a reason.** 🟢
  | Group | Tables | Reason |
  |---|---|---|
  | shared library | `rc_flight_profiles`, `rc_flight_profile_entries`, `components`, `component_types`, `airfoils`, `airfoil_low_re`, `mission_presets` | shared reference; the FK is kept as-is |
  | transient | `operating_points`, `operating_pointsets`, `flight_envelopes` | recomputed on demand |
  | conversation | `copilot_messages` | *"provenance captured via note + cursor"* |
  | versioning meta | `branches` | managed by the versioning service |
  | construction | `construction_plans`, `construction_parts` | soft string FK, file-backed — cloning would carry stale paths |
  | caches | `tessellation_cache`, `avl_geometry_files` | content-hash cache / stale `is_user_edited` flags |
  | non-tables | `avl_geometry_events`, `stability_events`, `alembic_version` | no own table / migration tracking |
- **BR-CL4 — The clone order is fixed and flush-separated.** 🟢
  ```
  1  aeroplanes           7  aircraft_computation_config
  2  weight_items         8  stability_results
  3  wings → xsecs →      9  loading_scenarios
     details → spares ·  10  component_tree
     turbulator · TED →
     ted_servo
  4  fuselages → xsecs
  5  mission_objective
  6  design_assumptions
  ```
  Each group flushes so the parent PKs exist before the children reference them.
- **BR-CL5 — The root row: what changes and what does not.** 🟢
  - **new**: `uuid4`;
  - **deep-copied**: `xyz_ref`, `assumption_computation_context`
    (`copy.deepcopy`, so the clone cannot mutate the source's JSON);
  - **copied**: `name`, `total_mass_kg`;
  - **kept as a shared reference**: `flight_profile_id`;
  - **caller-supplied**: `is_immutable`, `branch_id`, `predecessor_id`,
    `root_id`;
  - **nulled**: `version_label`, `version_note`, `created_by`,
    `provenance_message_id`, `preview_png` — *"the caller's responsibility"*.
- **BR-40 — Internal references are re-keyed; shared ones are kept.** 🟢
  Kept: `flight_profile_id`, `wing_xsec_ted_servos.component_id`,
  `component_tree.component_id` / `construction_part_id` / `material_id`.
  Re-keyed: `loading_scenarios.component_overrides[*].component_uuid` and
  `component_tree.parent_id`.
- **BR-CL6 — STEP paths are nulled.** 🟢 `fuselages.step_path` and
  `solid_step_path` become `NULL` on the clone, so a version never points at
  another version's artefact.
- **BR-CL7 — The weight-id map is built during group 2.** 🟢
  `weight_id_map: str(old weight_item.id) → str(new id)` — **string** keys,
  because `component_overrides` stores stringified ids.
- **BR-CL8 — Unmapped override values pass through unchanged.** 🟢
  `_remap_component_overrides` walks `toggles`, `mass_overrides` and
  `position_overrides`; a `component_uuid` absent from the map is left alone
  because it is a **COTS component UUID**, a shared reference. Empty or `None`
  overrides are deep-copied without error.
- **BR-VR13 — The component tree is cloned in two passes.** 🟢 Pass 1 inserts
  every node with `parent_id=None`, flushing per node to collect
  `old_id → new_id`; pass 2 issues an `UPDATE` per node to restore the parent.
  A parent not in the map leaves `parent_id = None` **and logs a warning naming
  both ids** — chosen explicitly over silent data loss.
- **BR-CL9 — The tree is found by its *string* `aeroplane_id`.** 🟢
  `ComponentTreeNodeModel.aeroplane_id == str(source.uuid)`, and the clone
  writes `str(clone.uuid)`. This is why the table is invisible to the coverage
  test.
- **BR-CL10 — Stability results keep `computed_at` and `geometry_hash`.** 🟢
  A cloned aircraft therefore inherits a result that appears to have been
  computed at the original time, against the original geometry hash. 🟡
- **BR-VR14 / ADR 0009 — The clone never commits.** 🟢 `db.flush()` throughout;
  `get_db()` owns the boundary.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Copy all 17 owned tables into new rows with new PKs | Must | Every table has clone rows; no row object is shared with the source |
| RF-02 | Assign a fresh `uuid4` to the clone | Must | `clone.uuid != source.uuid` |
| RF-03 | Deep-copy the JSON columns | Must | Mutating `clone.assumption_computation_context` does not affect the source |
| RF-04 | Accept `immutable`, `branch_id`, `predecessor_id` and `root_id` from the caller | Must | All four appear on the clone exactly as passed |
| RF-05 | Null the five version-metadata columns | Must | `version_label`, `version_note`, `created_by`, `provenance_message_id`, `preview_png` are all `None` |
| RF-06 | Keep `flight_profile_id` as a shared reference | Must | Identical in source and clone |
| RF-07 | Preserve the wing hierarchy through five levels | Must | wing → xsec → detail → {spare, turbulator, TED → servo} all cloned with re-keyed parents |
| RF-08 | Keep `wing_xsec_ted_servos.component_id` unchanged | Must | The servo still points at the same COTS component |
| RF-09 | Null `fuselages.step_path` and `solid_step_path` | Must | The clone carries no artefact path |
| RF-10 | Clone the 1:1 tables exactly once | Must | `mission_objectives` and `aircraft_computation_config` yield one row each |
| RF-11 | Copy `design_assumptions` including estimate, calculated, active source and divergence | Must | Every column round-trips |
| RF-12 | Copy `stability_results` including `computed_at` and `geometry_hash` | Must | Both survive the clone |
| RF-13 | Build the weight-id map and remap loading-scenario overrides | Must | A scenario referencing weight item `"7"` points at the clone's copy |
| RF-14 | Leave unmapped override values unchanged | Must | A COTS component UUID is untouched |
| RF-15 | Clone the component tree with its `aeroplane_id` set to the clone's UUID string | Must | The clone's tree is retrievable by the clone's UUID |
| RF-16 | Restore the tree's parentage in a second pass | Must | The clone's tree has the same shape as the source's |
| RF-17 | Log and null an unmappable tree parent | Must | `parent_id` is `None` and a warning names both the old and new ids |
| RF-18 | Keep the tree's `component_id`, `construction_part_id` and `material_id` unchanged | Must | All three identical in source and clone |
| RF-19 | Keep the registry exhaustive, disjoint and reasoned | Must | `test_aeroplane_clone_coverage` passes; adding a new FK table fails it |
| RF-20 | Never commit | Must | A rollback after a clone leaves nothing persisted |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Integrity | Clone completeness is a **test-enforced** invariant, not a review convention | `test_aeroplane_clone_coverage.py` | 🟢 |
| Integrity | Every exclusion must justify itself in writing | the reason string is mandatory | 🟢 |
| Correctness | Unmappable data is logged with both ids rather than dropped silently | `_clone_component_tree:565-580` | 🟢 |
| Correctness | JSON is deep-copied so two versions cannot share a mutable structure | `copy.deepcopy` on `xyz_ref` and the context | 🟢 |
| Correctness | Artefact paths are nulled so a version never points at another's files | `fuselages` group | 🟢 |
| Reliability | Flush-per-group makes PKs available for re-keying without committing (ADR 0009) | `:454` and the per-group flushes | 🟢 |
| Performance | Pass 1 of the tree clone flushes **per node**, so a large tree issues O(n) round-trips | `_clone_component_tree:552-554` | 🟡 |
| Performance | Pass 2 issues one `UPDATE` per node with a non-null parent | `:562-564` | 🟡 |
| Scalability | The whole design subgraph is copied on **every** snapshot, with no incremental or delta representation | ADR 0006 | 🟡 |
| Maintainability | The blind spot is documented at the point where a contributor would add a table | the comment above `CLONED_TABLES` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Clone completeness

  Scenario: The whole owned subgraph is copied
    Given an aircraft with 2 wings, 6 xsecs, details with spares, turbulators
      and TEDs with servos, 1 fuselage with xsecs, 3 weight items, a mission
      objective, 15 design assumptions, a computation config, 2 stability
      results, 1 loading scenario and a 10-node component tree
    When I clone it
    Then every one of those tables has new rows belonging to the clone
    And no primary key is shared with the source

  Scenario: A new table without a registry entry fails the build
    Given a new table with a ForeignKey to aeroplanes
    When the clone coverage test runs
    Then it fails until the table is added to CLONED_TABLES or EXCLUDED_TABLES

  Scenario: Every exclusion carries a reason
    When the clone coverage test runs
    Then every EXCLUDED_TABLES entry has a non-empty reason string

Feature: Identity and metadata

  Scenario: The clone gets a new identity and no inherited version metadata
    When I clone an aircraft
    Then the clone has a different uuid
    And version_label, version_note, created_by, provenance_message_id
      and preview_png are all null

  Scenario: The caller supplies the versioning columns
    When I clone with immutable true, branch_id 3, predecessor_id 9, root_id 1
    Then the clone carries exactly those four values

  Scenario: JSON columns are deep-copied
    Given an aircraft with a populated assumption_computation_context
    When I clone it and mutate the clone's context
    Then the source's context is unchanged

Feature: Shared vs internal references

  Scenario: Library references are preserved
    When I clone an aircraft
    Then flight_profile_id, ted_servo.component_id, component_tree.component_id,
      construction_part_id and material_id are identical in source and clone

  Scenario: STEP paths are cleared
    Given a fuselage with step_path and solid_step_path set
    When I clone the aircraft
    Then both are null on the clone

  Scenario: Loading-scenario overrides are re-keyed
    Given a loading scenario whose toggles reference component_uuid "7",
      the stringified id of a weight item
    When I clone the aircraft
    Then the clone's scenario references the clone's copy of that weight item

  Scenario: A COTS uuid in the overrides is untouched
    Given a mass_overrides entry whose component_uuid is a COTS component uuid
    When I clone the aircraft
    Then that value is unchanged

Feature: Component tree

  Scenario: The tree shape survives
    Given a component tree with three levels
    When I clone the aircraft
    Then the clone's tree has the same shape
    And every node's aeroplane_id is the clone's uuid string

  Scenario: An unmappable parent is logged, not dropped
    Given a component-tree node whose parent belongs to another aeroplane
    When I clone the aircraft
    Then the cloned node's parent_id is null
    And a warning names both the source node id and the cloned node id

Feature: Transaction discipline

  Scenario: The clone does not commit
    When I clone an aircraft inside a request that then raises
    Then no clone row exists after the rollback
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Full subgraph copy with new PKs (RF-01, RF-07, RF-10…RF-12) | Must | A missed table means two "independent" versions silently share state |
| The coverage registry (RF-19) | Must | The only mechanism that keeps the clone complete as the schema grows |
| Shared-vs-internal reference discipline (RF-06, RF-08, RF-13, RF-14, RF-18) | Must | Re-keying too much breaks the library; too little makes the clone reference the source |
| Override remapping (RF-13) | Must | Without it, a clone's loading scenarios silently describe the **source's** weight items |
| Two-pass tree clone with the warning (RF-15…RF-17) | Must | The tree is the only string-FK table that is cloned; a lost parent is a lost bill of materials |
| New identity + nulled metadata (RF-02, RF-05) | Must | A clone inheriting `version_label` would misrepresent its own history |
| Deep-copied JSON (RF-03) | Must | Shared mutable JSON between two versions is a latent aliasing bug |
| Nulled STEP paths (RF-09) | Must | A version pointing at another's artefact would serve stale geometry |
| No commit (RF-20) | Must | ADR 0009 |
| Batching the tree clone's flushes | Won't | 🟡 not implemented; O(n) round-trips per pass |
| Incremental / delta versioning | Won't | 🟡 explicitly out of scope (ADR 0006) |
| Automatic discovery of string-FK tables | Won't | 🟡 the blind spot is documented, not closed |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/aeroplane_clone_service.py:56-69` | the blind-spot comment | 🟢 |
| `…:70-92` | `CLONED_TABLES` (17) | 🟢 |
| `…:95-132` | `EXCLUDED_TABLES` (18, each with a reason) | 🟢 |
| `…:140-206` | `clone_aeroplane_subgraph` signature + group 1 (root row) | 🟢 |
| `…:207-225` | group 2 — weight items + `weight_id_map` | 🟢 |
| `…:226-338` | group 3 — wings → xsecs → details → spares · turbulators · TEDs → servos | 🟢 |
| `…:339-361` | group 4 — fuselages → xsecs, STEP paths nulled | 🟢 |
| `…:362-384` | group 5 — mission objective | 🟢 |
| `…:385-397` | group 6 — design assumptions | 🟢 |
| `…:398-412` | group 7 — computation config | 🟢 |
| `…:413-438` | group 8 — stability results | 🟢 |
| `…:439-450` | group 9 — loading scenarios (remapped) | 🟢 |
| `…:451-455` | group 10 — component tree + the final flush | 🟢 |
| `…:463-491` | `_remap_component_overrides` | 🟢 |
| `…:494-580` | `_clone_component_tree` (two passes + the warning) | 🟢 |
| `app/tests/test_aeroplane_clone_coverage.py` | the coverage invariant | 🟢 |
</content>
