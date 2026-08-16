# ADR 0013 — One `components` table with a user-extensible, data-driven type schema

- **Status:** Accepted — in force
- **Decided:** gh#82 / gh#83 (the "Dynamic Component Types" flow, documented as a BDD feature in `00625f98`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (models, service, seed data)

## Context

The catalogue must cover wildly different hardware — motors, ESCs, LiPo batteries,
propellers, servos, receivers, materials, carbon spar tubes, four kinds of wood
stock — each with its own properties. Two further pressures shaped the design.
**The user must be able to add types:** the audience includes hobbyists with parts
nobody anticipated, and a fixed taxonomy compiled into the backend would need a
release per category. **New COTS sources keep arriving:** in roughly three months
the catalogue absorbed six vendor sources (gh-986, gh-997, gh-999, gh-1009,
gh-1081, gh-1083), each with a different spec vocabulary.

## Decision

**One table for every hardware type, discriminated by a string, with type-specific
fields in a JSON blob whose contract is itself a database row.**

```
components:      name, manufacturer, description, mass_g,
                 bbox_{x,y,z}_mm, model_ref,
                 component_type  (indexed String discriminator),
                 specs           (JSON — everything type-specific)

component_types: name, label, description, deletable,
                 schema  (mapped as `schema_def` — `schema` collides with a
                          Pydantic attribute name)
                 → a JSON list of PropertyDefinition:
                   { name, label, type ∈ {number,string,boolean},
                     unit, required, min, max, options }
```

1. **`validate_specs` runs on every create and update** and rejects: unknown
   `component_type`, missing required property, non-numeric (or bool) where a
   number is declared, out-of-range against `min`/`max`, wrong Python type for
   string/boolean, and a value not in a declared `options` list.
2. **Unknown keys in `specs` are accepted, never rejected.** The schema is a floor,
   not a closed contract.
3. **12 types are seeded** idempotently at startup with `deletable=False`:
   `material`, `servo`, `brushless_motor`, `battery`, `esc`, `propeller`,
   `receiver`, `spar_tube`, `veneer`, `strip`, `triangular_strip`,
   `grooved_strip`.
4. **Two deletion guards:** a seeded type cannot be deleted (409); a type still
   referenced by ≥ 1 component cannot be deleted (409, with the reference count).
   `update_type` may change `label`, `description` and `schema` — never `name` or
   `deletable`.
5. **`_patch_schema_fields` additively merges newly added schema fields onto
   already-seeded rows**, so an existing database gains e.g. the gh-1006 `rm_ohm`
   field without a rebuild and without a migration.

## Consequences

- A new hardware category is data, not a release; six COTS import campaigns landed
  in three months with no `components` migration; the deletion guards keep the
  seeded taxonomy — which the spar sizer, powertrain model and construction
  pipeline depend on — from being dismantled by a user.
- 🔴 **`specs` is not queryable.** "Motors above 800 KV" means loading rows and
  filtering in Python.
- 🔴 **Two spec vocabularies for the same physical quantity coexist.** Sizing reads
  `continuous_current_a` with a `max_continuous_a` fallback; the solution space
  reads `max_current_a` with a `continuous_current_a` fallback, plus
  `c_rating`/`discharge_c`, while `BatterySpec` reads `c_rate`. **A battery
  imported with `c_rating` is invisible to the performance model.** This is the
  direct cost of "unknown keys are accepted".
- 🔴 **A seeder bypasses validation.** `prop_component_seed` writes `ComponentModel`
  rows directly, producing components that violate the seeded `propeller` schema and
  will 422 on the first API `PUT`, plus a `specs["variant"]` key that is not in the
  schema — accepted silently.
- 🔴 **The seeded schema `label`s are German** (`"Durchmesser"`, `"Steigung"`,
  `"Blätter"`, `"Dauerstrom"`, …) and are rendered directly in the component editor,
  contradicting the English-only UI rule.
- **Referential integrity is by convention** — `component_id` references from servos
  and tree nodes are plain columns checked at runtime, with no FK.

**Rejected:** one table per type and typed columns per type — both make user-defined
types impossible without runtime DDL. An EAV property table would be queryable *and*
extensible at the cost of a join per property; not chosen.

## Related

[ADR 0014](0014-cots-ingestion-from-committed-snapshots.md) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md)
(`_VALID_COMPONENT_TYPES` duplicating `DEFAULT_SEED_TYPES`) ·
domain rules BR-59 … BR-66 · [`../questions.md`](../questions.md) §Q-PT-13.
Evidence: commit `00625f98` (gh#82); `app/models/component.py`,
`app/models/component_type.py:20-28`,
`app/services/component_type_service.py:240-271, 682, 710`.
