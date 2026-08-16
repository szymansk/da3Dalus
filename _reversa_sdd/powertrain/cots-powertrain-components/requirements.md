# cots-powertrain-components

> Use-case specification, nested under the module
> [`powertrain`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/models/component.py`, `app/models/component_type.py`,
> `app/services/component_service.py`, `component_type_service.py`,
> `cots_import.py`, `app/api/v2/endpoints/components.py`, `component_types.py`,
> ADR 0013, ADR 0014. Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

The **COTS hardware library**: one `components` table for every physical part
the designer can buy — motors, ESCs, batteries, propellers, servos, receivers,
materials, spars, wood — discriminated by `component_type`, with all
type-specific fields in a JSON `specs` blob whose contract is itself a database
row. Adding a new hardware type is a **data** operation, not a migration. 🟢

The library is **global**: it is shared by every aircraft and is explicitly
excluded from the versioning clone (`EXCLUDED_TABLES`, reason *"global COTS
component library; shared reference"*). 🟢

## Responsibilities

- Own `components` and `component_types`. 🟢
- Validate every component write against its type's `PropertyDefinition` list.
  🟢
- Seed 12 undeletable default types idempotently at startup and patch newly
  declared properties onto existing rows. 🟢
- Guard the taxonomy: seeded and referenced types cannot be deleted; `name` and
  `deletable` are immutable. 🟢
- Resolve the propeller-polar bridge (`has_polar`, `polar_id`) without an N+1.
  🟢
- Ingest the non-propeller COTS snapshots. 🟢
- Serve component 3D-model upload and download. 🟢

**NOT this use case:** the polar dataset itself and its mirror
(→ [`propeller-polars`](../propeller-polars/requirements.md)), the physics that
reads the specs (→ [`performance-model`](../performance-model/requirements.md),
[`powertrain-sizing`](../powertrain-sizing/requirements.md)), and the placement
of a component into an aircraft (→ `aeroplane-core`'s component tree,
`wing-design`'s servos).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-PT*` from
> [`../requirements.md`](../requirements.md); `BR-CC*` are new here.

- **BR-59 — One table, a data-driven per-type schema (ADR 0013).** 🟢 Fixed
  columns are only what every type shares: `name`, `component_type` (indexed
  discriminator), `manufacturer`, `description`, `mass_g`, `bbox_{x,y,z}_mm`,
  `model_ref`, `specs`. Everything else is `specs`.
- **BR-CC1 — The `schema` column is mapped as `schema_def`.** 🟢
  (`component_type.py:28`) The Python attribute name `schema` collides with a
  Pydantic attribute; the **column** is still `schema`. Getting this wrong
  breaks every serialisation of the model.
- **BR-CC2 — `component_type` is a free string on the wire.** 🟢 (gh#83)
  `ComponentWrite.component_type` is `str(min_length=1)`; the closed-set check
  happens in the **service**, against the live registry — which is what makes a
  user-created type usable immediately.
- **BR-60 — `validate_specs` rejects bad values, accepts unknown keys.** 🟢
  (`component_type_service.py:240-271`)
  ```
  unknown component_type              -> ValidationError ("use GET /component-types")
  required property missing           -> ValidationError (reason "missing_required")
  number: non-numeric / bool          -> ValidationError
  number: < min or > max              -> ValidationError   (inclusive bounds)
  string / boolean: wrong python type -> ValidationError
  options present, value not in       -> ValidationError
  unknown keys in specs               -> ACCEPTED
  ```
  The schema is a **floor**, not a complete contract.
- **BR-61 — Seeded and referenced types cannot be deleted.** 🟢
  `deletable=False` → 409; referenced by ≥ 1 component → 409 with the count.
  `update_type` may change `label`, `description`, `schema` — never `name` or
  `deletable`.
- **BR-PT1 — Twelve seeded types, idempotently.** 🟢 `material`, `servo`,
  `brushless_motor`, `battery`, `esc`, `propeller`, `receiver`, `spar_tube`,
  `veneer`, `strip`, `triangular_strip`, `grooved_strip`
  (`DEFAULT_SEED_TYPES:331`, `seed_default_types:682`). Only four are
  powertrain; the rest belong to `wing-design` and `construction-plans`.
- **BR-PT2 — Schema fields are patched additively.** 🟢
  `_patch_schema_fields:710` merges newly declared properties onto already-seeded
  rows, so an existing database gains e.g. `rm_ohm` (gh-1006) without a rebuild.
- **BR-PT4 — `mass_g = NULL` means unknown, never zero.** 🟢 The component
  tree's weight ladder then reports `weight_source = "none"` rather than 0 g.
- **BR-62 / ADR 0014 — Ingestion is snapshot-driven and network-free.** 🟢
  `cots_import` reads committed JSON (`dpower.json`, `generic_batteries.json`,
  `spektrum_avian.json`, `carbon_tubes.json`, `hoellein_wood.json`) and upserts
  on **`(manufacturer, name)`**.
- **BR-CC3 — The library is global and version-exempt.** 🟢 `components` and
  `component_types` are in `EXCLUDED_TABLES`; a cloned aircraft points at the
  same rows, and `component_tree.component_id` /
  `wing_xsec_ted_servos.component_id` are preserved as **shared references**
  during a clone.
- **BR-PT12 — `has_polar` / `polar_id` are batch-resolved.** 🟢
  `component_service._resolve_polar_id` joins on `model_ref`;
  `list_components` resolves the whole page in one pass.
- **BR-CC4 — Specs keys are read by name, and the names are not unified.** 🟢
  ```
  brushless_motor : kv_rpm_per_volt|kv, gear_ratio, efficiency_pct,
                    cells_lipo_max, io_no_load_a, max_current_a,
                    continuous_current_a, rm_ohm, max_power_w,
                    max_continuous_power_w
  battery         : cells, capacity_mah, c_rate|c_rating|discharge_c,
                    voltage_v|voltage|nominal_voltage
  esc             : continuous_current_a|max_continuous_a|max_current_a
  propeller       : diameter_in, pitch_in, blades, variant
  material        : density_kg_m3, print_resolution_mm
  ```
  🟢 The Pydantic spec-model spellings are canonical; importers normalise (`Q-PT-4`).
- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). Previously `_VALID_COMPONENT_TYPES` (`cots_import.py:26-40`) was a second copy of
  the 12-name taxonomy, maintained by hand.
- 🟢 Translated to English (`Q-CC-5`). Previously German: in an otherwise English API and are
  rendered directly in the component editor.
- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). `variant` is either declared in the schema or rejected. Previously undeclared: — written by
  [`propeller-polars`](../propeller-polars/requirements.md)'s mirror and accepted
  only because unknown keys pass.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List components with `component_type` and `q` filters | Must | `GET /components?component_type=esc` → 200 with only ESCs and a correct `total` |
| RF-02 | Resolve `has_polar` / `polar_id` in a constant number of queries | Must | Listing 100 propellers issues the same statement count as listing 1 |
| RF-03 | Create/read/update/delete a component | Must | 201 / 200 / 200 / 204; unknown id → 404 |
| RF-04 | Validate `specs` against the type schema on every write | Must | Missing required → 422 `missing_required`; out-of-range → 422; bad type → 422 |
| RF-05 | Accept unknown `specs` keys | Must | An undeclared key is stored and returned unchanged |
| RF-06 | Reject an unknown `component_type` with a remediation | Must | 422 naming `GET /component-types` |
| RF-07 | List, read, create, update and delete component types | Must | 200 / 200 / 201 / 200 / 204 |
| RF-08 | Keep `name` and `deletable` immutable on update | Must | A PUT changing either leaves them unchanged |
| RF-09 | Refuse to delete a seeded type | Must | 409 |
| RF-10 | Refuse to delete a referenced type, naming the count | Must | 409 with the number of referencing components |
| RF-11 | Seed the 12 default types idempotently | Must | Two startups leave exactly 12 rows with `deletable=false` |
| RF-12 | Patch newly declared schema properties onto existing types | Should | Adding a property to the seed makes it appear without a migration |
| RF-13 | Import the non-propeller snapshots, upserting on `(manufacturer, name)` | Must | A second import of an unchanged snapshot creates no duplicates |
| RF-14 | Report import outcomes as counts plus an error list | Must | `ImportResult{imported, updated, skipped, errors[]}` |
| RF-15 | Upload and download a component 3D model | Could | The downloaded bytes equal the uploaded bytes |
| RF-16 | Keep `mass_g` nullable and never coerce it to 0 | Must | A component created without a mass has `mass_g = null` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Extensibility | A new hardware type requires no code change and no migration (ADR 0013) | `component_types.schema_def`, `validate_specs` | 🟢 |
| Compatibility | An existing database gains new schema properties without a rebuild | `_patch_schema_fields:710` | 🟢 |
| Integrity | The type registry is the **only** integrity mechanism over `specs` — there is no column-level constraint | `validate_specs:240-271` | 🟢 |
| Integrity | The taxonomy cannot be emptied by accident: seeded types are undeletable and referenced types are protected | `deletable=False`, reference count → 409 | 🟢 |
| Performance | `has_polar` resolution is batched | `component_service._resolve_polar_id` | 🟢 |
| Reproducibility | Ingestion runs offline from a committed snapshot (ADR 0014) | `cots_import`, `data/cots/*.json` | 🟢 |
| Portability | Neither service imports AeroSandbox or CadQuery | whole use case | 🟢 |
| Security | Model upload accepts a file into the artefact store with no size or type audit recorded here | `components.py:170-245` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Data-driven component validation

  Scenario: A required property is enforced
    Given the seeded "brushless_motor" type requires kv_rpm_per_volt
    When I POST a brushless_motor whose specs omit it
    Then the response status is 422
    And the reason is "missing_required"

  Scenario: A numeric range is enforced inclusively
    Given a property with min 0 and max 100
    When I POST a component with that property set to 100
    Then the response status is 201
    When I POST one with 100.1
    Then the response status is 422

  Scenario: An options list is enforced
    Given a property with options ["A", "B"]
    When I POST a component with that property set to "C"
    Then the response status is 422

  Scenario: Unknown keys are accepted
    Given the seeded "propeller" type declares no "variant" property
    When I POST a propeller with specs.variant = "E"
    Then the response status is 201
    And the stored specs contain variant

  Scenario: An unknown component type is refused with a remediation
    When I POST a component with component_type "flux_capacitor"
    Then the response status is 422
    And the message mentions GET /component-types

Feature: Taxonomy guards

  Scenario: A seeded type cannot be deleted
    When I DELETE the "propeller" component type
    Then the response status is 409

  Scenario: A referenced type cannot be deleted
    Given a user-created type with 3 components
    When I DELETE it
    Then the response status is 409
    And the message names the count 3

  Scenario: name and deletable are immutable
    Given a user-created type named "widget"
    When I PUT it with name "gadget" and deletable false
    Then the response status is 200
    And the stored name is still "widget"
    And deletable is still true

  Scenario: Seeding is idempotent
    Given the 12 default types exist
    When seed_default_types runs again
    Then there are still exactly 12 types
    And each has deletable false

Feature: Snapshot ingestion

  Scenario: An unchanged snapshot creates no duplicates
    Given the D-Power snapshot has been imported
    When I import it again
    Then no new components are created
    And the existing rows are matched on (manufacturer, name)

  Scenario: An unknown type in a snapshot is an error, not a row
    Given a snapshot record with component_type "flux_capacitor"
    When I run the import
    Then the record appears in ImportResult.errors
    And no component is created

Feature: The polar bridge

  Scenario: A propeller with a matching polar reports it
    Given a component with model_ref "apc/10x10E"
    And a propeller polar with the same model_ref
    When I GET the component
    Then has_polar is true
    And polar_id is the polar's id

  Scenario: Listing does not degrade into N+1
    Given 100 propeller components with polars
    When I GET /components?component_type=propeller
    Then the number of SQL statements is independent of the row count
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The two tables + `schema_def` mapping (RF-03, RF-07) | Must | Everything in the module reads them; the mapping error is silent and total |
| `validate_specs` (RF-04…RF-06) | Must | The only integrity mechanism over a schemaless JSON column |
| Seeding + idempotence (RF-11) | Must | Startup relies on it; the fixture relies on it |
| Taxonomy guards (RF-08…RF-10) | Must | A deleted seeded type would orphan every component of that type |
| Snapshot ingestion + upsert identity (RF-13/RF-14) | Must | The catalogue arrives this way; a wrong upsert key duplicates the library |
| Nullable `mass_g` (RF-16) | Must | `NULL` vs `0` is the difference between "unknown" and "weightless" in the weight ladder |
| Batch polar resolution (RF-02) | Must | The list endpoint is the component picker's backing call |
| Unknown-key acceptance (RF-05) | Must | Load-bearing — the propeller mirror depends on it |
| Additive schema patching (RF-12) | Should | A manual re-seed would also work, at the cost of a rebuild |
| Model upload/download (RF-15) | Could | Peripheral to propulsion |
| A unified spec-key vocabulary | **Must** | 🟢 The Pydantic spec-model spellings are canonical; importers normalise (`Q-PT-4`). |
| English seeded labels | **Must** | 🟢 Translated to English (`Q-CC-5`). |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/component.py:8` | `ComponentModel` | 🟢 |
| `app/models/component_type.py:20, 28` | `ComponentTypeModel`, the `schema_def` mapping | 🟢 |
| `app/services/component_service.py` | CRUD, `_resolve_polar_id`, model up/download | 🟢 |
| `app/services/component_type_service.py:240-271` | `validate_specs` | 🟢 |
| `app/services/component_type_service.py:331, 682, 710` | `DEFAULT_SEED_TYPES`, `seed_default_types`, `_patch_schema_fields` | 🟢 |
| `app/services/cots_import.py:26-40` | `_VALID_COMPONENT_TYPES` + the upsert | 🟢 (removed — one binding schema, `Q-PT-5`) (taxonomy) |
| `app/api/v2/endpoints/components.py` | `/components` router (7 routes) | 🟢 |
| `app/api/v2/endpoints/component_types.py` | `/component-types` router (5 routes) | 🟢 |
| `app/schemas/component.py` | `ComponentWrite/Read/List`, `ComponentTypesResponse` | 🟢 |
| `app/schemas/component_type.py` | `PropertyDefinition` | 🟢 |
| `scripts/import_cots.py` | reimport CLI | 🟢 |
</content>
