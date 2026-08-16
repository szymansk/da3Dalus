# Code ↔ Spec Traceability Matrix

> Global artefact of the Reversa Writer. Maps every significant legacy source file
> to the spec unit(s) that cover it, so a reimplementation can be checked for gaps.
> Companion to [`spec-impact-matrix.md`](spec-impact-matrix.md) (Architect), which maps
> the reverse direction: spec change → impacted code.

## How coverage was determined

Coverage is **evidence-based, not asserted**. Every `.md` under a unit folder in
`_reversa_sdd/<module>/` (and its nested use-case folders) was scanned for source-file
paths cited in backticks, quotes, brackets or parentheses. A file counts as covered only
if a unit document actually names it.

| Symbol | Meaning |
|---|---|
| 🟢 | The file is **cited by path** in at least one unit's `requirements.md` / `design.md` / `tasks.md` / `contracts.md`. Its behaviour is documented. |
| 🟡 | The file falls under a module's declared `paths` in `.reversa/context/surface.json`, so it is **owned** by that module's spec, but no unit document names it individually. Behaviour is covered at module granularity only. |
| n/a | **No unit covers it.** Candidate for further analysis. |

## Summary

- **1156** source files scanned (`.py`, `.ts`, `.tsx` under `app/`, `cad_designer/`, `frontend/`, `alembic/`, `scripts/`).
- Split into **629** production files, **516** test files and **11** `__init__.py` package markers.

| Scope | Files | 🟢 cited | 🟡 module-owned | n/a | Mapped to some unit |
|---|---:|---:|---:|---:|---:|
| **Production source** | 629 | 261 | 346 | 22 | **96.5%** |
| Test files | 516 | — | — | — | _excluded, see below_ |
| `__init__.py` package markers | 11 | — | — | — | _excluded, no behaviour_ |

> **Estimated coverage: 96.5% of production source is mapped to a spec unit**, of which 41.5% is individually cited (🟢) and 55.0% is covered at module granularity (🟡).


> ### ⚠ Recomputed after the specification-validation interview (2026-08-15)
>
> The figures above predate the interview. **Eleven production files are now slated
> for deletion**, so they are neither covered nor uncovered — they leave the
> denominator rather than moving between columns:
>
> | Deleted by | Files |
> |---|---|
> | `Q-CG-4` — wing-tessellation subsystem | `tessellation_cache.py`, `tessellation_cache_service.py`, `tessellation_hooks.py`, `tessellation_service.py`, the cache migration, `frontend/hooks/useTessellation.ts` |
> | `Q-MB-1` — `weight_items` retired | `weight_items.py` (endpoint), `weight_item.py` (schema), `weight_items_service.py` |
> | `Q-AV-3`/`Q-AV-4` — parse, don't cache | `avl_artefact.py`, `avl_artefact_service.py` |
> | `Q-CC-6` / `Q-CC-16` — `P-DEAD-0` | `endpoints/aeroplane.py`, `db/exceptions.py`, `services/example.py` |
>
> **Effect on the headline:** the two `n/a` rows in *Unreferenced* disappear
> (22 → 20 uncovered), and the production denominator drops from 629 to ~615.
> Recomputed coverage is therefore **≈96.7 %**, essentially unchanged — the
> deletions remove covered and uncovered files in roughly equal proportion.
>
> **One row was mis-filed and is corrected, not regressed.**
> `cad_designer/airplane/creator/wing/WingLoftCreator.py` was listed as owned only
> by `cad-generation/wing-tessellation/`. Measured: it is a regular
> `AbstractShapeCreator`; `cad_service.py:238` writes
> `wing_node["creator"]["$TYPE"] = "WingLoftCreator"` into the generated plan JSON,
> and **4 stored `construction_plans` reference it by name**. Its real owners are
> `construction-plans/plan-execution/` (consumes the `$TYPE`) and
> `cad-generation/wing-export-task/` (writes it). The tessellation assignment was
> the error; the deletion merely exposed it.
>
> **This makes it a live instance of CS-4**: deleting it would invalidate 4 stored
> plans, which is exactly the hazard the `$TYPE` dialect carries.
>
> The percentages are **not** re-derived line by line here; they are estimates
> consistent with the deletions listed. Re-run the coverage scan before quoting
> them as measured.

Test files are listed separately at the end: they are evidence *about* the units rather
than behaviour to reimplement, so they are excluded from the headline percentage.

11 files carried neither a citation nor a declared module prefix but were
resolved to an unambiguous owner from the **import graph** — every `app/` module that
imports them belongs to a single Reversa module. Those rows are marked
*(owner resolved from import graph)*.

## Coverage by module

| Module | Files | 🟢 | 🟡 | n/a |
|---|---:|---:|---:|---:|
| [`aeroplane-core`](../aeroplane-core/) | 17 | 16 | 1 | 0 |
| [`wing-design`](../wing-design/) | 15 | 10 | 5 | 0 |
| [`fuselage-design`](../fuselage-design/) | 6 | 4 | 2 | 0 |
| [`airfoil-catalog`](../airfoil-catalog/) | 11 | 10 | 1 | 0 |
| [`cad-generation`](../cad-generation/) | 14 | 13 | 1 | 0 |
| [`cad-designer-topology`](../cad-designer-topology/) | 95 | 30 | 65 | 0 |
| [`aero-analysis`](../aero-analysis/) | 36 | 31 | 5 | 0 |
| [`avl-integration`](../avl-integration/) | 12 | 11 | 1 | 0 |
| [`mass-and-balance`](../mass-and-balance/) | 8 | 6 | 2 | 0 |
| [`powertrain`](../powertrain/) | 32 | 29 | 3 | 0 |
| [`mission-and-sizing`](../mission-and-sizing/) | 35 | 31 | 4 | 0 |
| [`construction-plans`](../construction-plans/) | 14 | 14 | 0 | 0 |
| [`versioning`](../versioning/) | 5 | 4 | 1 | 0 |
| [`openvsp-import`](../openvsp-import/) | 17 | 17 | 0 | 0 |
| [`ai-copilot`](../ai-copilot/) | 14 | 13 | 1 | 0 |
| [`mcp-server`](../mcp-server/) | 1 | 1 | 0 | 0 |
| [`platform-core`](../platform-core/) | 65 | 7 | 58 | 0 |
| [`frontend-workbench`](../frontend-workbench/) | 210 | 14 | 196 | 0 |
| _(no module)_ | 22 | 0 | 0 | 22 |

## Matrix

### `aeroplane-core`

> Aeroplane/project aggregate root: CRUD, component tree wiring, total mass, base entity lifecycle.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane.py` | `aeroplane-core/aeroplane-crud/` | 🗑 **slated for deletion** (`Q-CC-6`, `P-DEAD-0`) — shadowed by the `aeroplane/` package, never imported |
| `app/api/v2/endpoints/aeroplane/base.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `aeroplane-core/airplane-configuration-export/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `mass-and-balance/`, `wing-design/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/component_tree.py` | `aeroplane-core/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/` | 🟢 |
| `app/converters/model_schema_converters.py` | `aeroplane-core/`, `aeroplane-core/airplane-configuration-export/`, `avl-integration/control-surface-naming/`, `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `cad-generation/`, `cad-generation/wing-export-task/`, `construction-plans/plan-execution/`, `mission-and-sizing/flight-envelope/`, `mission-and-sizing/operating-point-sweep/`, `openvsp-import/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/` | 🟢 |
| `app/core/config.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `ai-copilot/`, `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/`, `cad-generation/`, `cad-generation/artifact-serving/`, `construction-plans/construction-parts/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `platform-core/`, `platform-core/config-and-settings/`, `wing-design/` | 🟢 |
| `app/core/exceptions.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `aeroplane-core/airplane-configuration-export/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/`, `ai-copilot/`, `ai-copilot/copilot-turn-loop/`, `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/`, `cad-designer-topology/`, `cad-generation/`, `cad-generation/artifact-serving/`, `construction-plans/`, `construction-plans/construction-parts/`, `construction-plans/plan-template-lifecycle/`, `fuselage-design/`, `fuselage-design/step-slicing/`, `fuselage-design/superellipse-xsecs/`, `mass-and-balance/`, `mass-and-balance/cg-mass-computation/`, `platform-core/`, `platform-core/transaction-and-error-handling/`, `powertrain/cots-powertrain-components/`, `versioning/`, `versioning/branch-model/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/` | 🟢 |
| `app/db/session.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `aeroplane-core/airplane-configuration-export/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/`, `ai-copilot/`, `ai-copilot/copilot-turn-loop/`, `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/`, `construction-plans/`, `construction-plans/construction-parts/`, `construction-plans/spar-plan/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `mass-and-balance/`, `mass-and-balance/component-tree-mass-sync/`, `mcp-server/rest-mcp-reuse/`, `platform-core/`, `platform-core/config-and-settings/`, `platform-core/transaction-and-error-handling/`, `powertrain/`, `powertrain/cots-powertrain-components/`, `powertrain/propeller-polars/`, `versioning/`, `versioning/aeroplane-clone-subgraph/`, `versioning/branch-model/`, `versioning/snapshot-immutability/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `app/models/aeroplanemodel.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `ai-copilot/`, `construction-plans/spar-plan/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `mass-and-balance/`, `mission-and-sizing/design-assumptions/`, `versioning/`, `versioning/branch-model/`, `versioning/copilot-provenance/`, `versioning/snapshot-immutability/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/`, `wing-design/spar-sizing/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `app/models/component_tree.py` | `aeroplane-core/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/` | 🟢 |
| `app/schemas/aeroplaneschema.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `avl-integration/control-surface-naming/`, `fuselage-design/`, `fuselage-design/step-slicing/`, `fuselage-design/superellipse-xsecs/`, `openvsp-import/`, `openvsp-import/vsp3-import-pipeline/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `app/schemas/component_tree.py` | `aeroplane-core/` *(owner resolved from import graph)* | 🟡 |
| `app/services/aeroplane_service.py` | `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `aeroplane-core/airplane-configuration-export/`, `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `mcp-server/rest-mcp-reuse/`, `openvsp-import/step-export-and-sewing/`, `versioning/`, `versioning/copilot-provenance/` | 🟢 |
| `app/services/component_tree_service.py` | `aeroplane-core/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/`, `mass-and-balance/`, `mass-and-balance/component-tree-mass-sync/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/services/fuselage_service.py` | `aeroplane-core/component-tree/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `wing-design/`, `wing-design/cross-section-crud/` | 🟢 |
| `app/services/mass_cg_service.py` | `aeroplane-core/weight-rollup/`, `mass-and-balance/`, `mass-and-balance/cg-mass-computation/`, `mass-and-balance/component-tree-mass-sync/`, `mission-and-sizing/design-assumptions/`, `mission-and-sizing/flight-envelope/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/services/openvsp_step_export_service.py` | `aeroplane-core/aeroplane-crud/`, `openvsp-import/`, `openvsp-import/step-export-and-sewing/` | 🟢 |
| `app/services/wing_service.py` | `aeroplane-core/component-tree/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/`, `wing-design/turbulator-optimizer/` | 🟢 |

### `wing-design`

> Wings, cross-sections, spars, trailing-edge devices, servos, turbulators, section geometry and thickness.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/turbulator_optimizer.py` | `wing-design/turbulator-optimizer/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/wings.py` | `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `app/api/v2/endpoints/section_aoa.py` | `wing-design/` | 🟢 |
| `app/schemas/Servo.py` | `wing-design/`, `wing-design/control-surface-mixing/`, `wing-design/cross-section-crud/` | 🟢 |
| `app/schemas/spar_sizing.py` | `wing-design/`, `wing-design/spar-sizing/` | 🟢 |
| `app/schemas/turbulator_optimizer.py` | `wing-design/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/wing.py` | `wing-design/` | 🟡 |
| `app/services/create_wing_configuration.py` | `wing-design/` | 🟡 |
| `app/services/section_aoa_service.py` | `wing-design/turbulator-optimizer/` | 🟢 |
| `app/services/section_geometry_service.py` | `wing-design/` | 🟡 |
| `app/services/section_thickness.py` | `wing-design/` | 🟡 |
| `app/services/spar_sizing.py` | `wing-design/`, `wing-design/spar-sizing/` | 🟢 |
| `app/services/turbulator_optimizer_service.py` | `wing-design/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/TrailingEdgeDevice.py` | `wing-design/control-surface-mixing/` | 🟢 |
| `cad_designer/airplane/geometry/section_geometry.py` | `wing-design/`, `wing-design/spar-sizing/` | 🟢 |

### `fuselage-design`

> Fuselages, superellipse cross-sections, slicing, STEP-based precise geometry.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/fuselages.py` | `fuselage-design/`, `fuselage-design/superellipse-xsecs/` | 🟢 |
| `app/api/v2/endpoints/fuselage_slice.py` | `fuselage-design/`, `fuselage-design/step-slicing/` | 🟢 |
| `app/schemas/fuselage_slice.py` | `fuselage-design/` | 🟡 |
| `app/services/fuselage_slice_service.py` | `fuselage-design/`, `fuselage-design/step-slicing/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/fuselage/FuselageConfiguration.py` | `fuselage-design/`, `fuselage-design/step-slicing/`, `fuselage-design/superellipse-xsecs/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/fuselage/__init__.py` | `fuselage-design/` | 🟡 |

### `airfoil-catalog`

> Airfoil library (1665 .dat files), geometry ingestion, low-Re polar backfill, NeuralFoil cd/cl surrogate, suitability scoring, tags.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/airfoils.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/models/airfoil.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/` | 🟢 |
| `app/models/airfoil_low_re.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/schemas/airfoil.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/services/airfoil_low_re_service.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/services/airfoil_service.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/` | 🟢 |
| `app/services/airfoil_tags.py` | `airfoil-catalog/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/services/neuralfoil_cdcl_service.py` | `airfoil-catalog/`, `airfoil-catalog/neuralfoil-analysis/`, `avl-integration/`, `avl-integration/avl-geometry-generation/` | 🟢 |
| `app/services/suitability_service.py` | `airfoil-catalog/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/settings.py` | `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/suitability-search/`, `mcp-server/`, `platform-core/`, `platform-core/config-and-settings/` | 🟢 |
| `scripts/backfill_airfoil_low_re.py` | `airfoil-catalog/` | 🟡 |

### `cad-generation`

> CadQuery orchestration: creator gallery, CAD build process pool, STEP/STL/3MF/IGES exports, artifacts. *(Tessellation + cache removed — `Q-CG-4`.)*

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `alembic/versions/04b8c856eab9_add_tessellation_cache_table.py` | `cad-generation/wing-tessellation/` | 🗑 **slated for deletion** (`Q-CG-4`) — needs a down-migration, not a spec |
| `app/api/v2/endpoints/cad.py` | `cad-generation/`, `cad-generation/wing-export-task/` | 🟢 |
| `app/api/v2/endpoints/construction_plans.py` | `cad-generation/artifact-serving/`, `construction-plans/`, `construction-plans/creator-catalog/`, `construction-plans/plan-execution/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/models/tessellation_cache.py` | `cad-generation/wing-tessellation/` | 🗑 **slated for deletion** (`Q-CG-4`) |
| `app/schemas/AeroplaneRequest.py` | `cad-generation/`, `cad-generation/wing-export-task/` | 🟢 |
| `app/schemas/Printer3dSettings.py` | `cad-generation/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/api_responses.py` | `cad-generation/`, `cad-generation/wing-export-task/` | 🟢 |
| `app/schemas/construction_plan.py` | `cad-generation/`, `cad-generation/artifact-serving/`, `construction-plans/`, `construction-plans/creator-catalog/`, `construction-plans/plan-execution/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/services/artifact_service.py` | `cad-generation/`, `cad-generation/artifact-serving/`, `construction-plans/`, `construction-plans/construction-parts/`, `construction-plans/plan-execution/` | 🟢 |
| `app/services/tessellation_cache_service.py` | `cad-generation/wing-tessellation/` | 🗑 **slated for deletion** (`Q-CG-4`) |
| `app/services/tessellation_hooks.py` | `cad-generation/wing-tessellation/` | 🗑 **slated for deletion** (`Q-CG-4`) |
| `app/services/tessellation_service.py` | `cad-generation/wing-tessellation/` | 🗑 **slated for deletion** (`Q-CG-4`). ⚠ The former owner list named `construction-plans/plan-execution/` and `frontend-workbench/cad-viewer-integration/` — **measured 2026-08-16, that was wrong**: the only production importers are `cad.py:31` (an endpoint being deleted) and a *comment* in `tessellation_hooks.py:54` (also deleted). `construction_plan_service._tessellate_shapes` is a **local function** (`:930`) and imports nothing from here. The file is fully deletable |
| `cad_designer/airplane/creator/export_import/ExportTo3mfCreator.py` | `cad-generation/`, `cad-generation/wing-export-task/` | 🟢 |
| `cad_designer/airplane/creator/wing/WingLoftCreator.py` | `construction-plans/plan-execution/`, `cad-generation/wing-export-task/` | 🟢 — **re-owned**: it is a regular `AbstractShapeCreator` emitted as a `$TYPE` into generated plan JSON (`cad_service.py:238`), and **4 stored `construction_plans` reference it by name**. Its former assignment to `wing-tessellation` was the mis-filing, not its purpose |

### `cad-designer-topology`

> Read-only CadQuery topology library: Airfoil, WingSegment, WingConfiguration, Spare, TrailingEdgeDevice, Turbulator, Servo, shape creators, cq_plugins, spar solver. Excluded from ruff and SonarCloud by policy.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/services/cad_service.py` | `cad-designer-topology/json-polymorphic-roundtrip/`, `cad-generation/`, `cad-generation/wing-export-task/`, `construction-plans/`, `construction-plans/plan-execution/` | 🟢 |
| `app/services/construction_plan_service.py` | `cad-designer-topology/json-polymorphic-roundtrip/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `cad-generation/`, `cad-generation/artifact-serving/`, `cad-generation/wing-export-task/`, `construction-plans/`, `construction-plans/creator-catalog/`, `construction-plans/plan-execution/`, `construction-plans/plan-template-lifecycle/`, `platform-core/config-and-settings/` | 🟢 |
| `cad_designer/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/aerosandbox/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/aerosandbox/aerodynamic_calculations.py` | `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/aerosandbox/classification.py` | `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/aerosandbox/convert2aerosandbox.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/aerosandbox/slicing.py` | `cad-designer-topology/`, `fuselage-design/`, `fuselage-design/step-slicing/`, `fuselage-design/superellipse-xsecs/`, `openvsp-import/` | 🟢 |
| `cad_designer/aerosandbox/wing_roundtrip.py` | `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/aerosandbox/wing_roundtrip_cases.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/AbstractConstructionStep.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/` | 🟢 |
| `cad_designer/airplane/AbstractShapeCreator.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-generation/`, `construction-plans/creator-catalog/` | 🟢 |
| `cad_designer/airplane/ConstructionRootNode.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-designer-topology/json-polymorphic-roundtrip/` | 🟢 |
| `cad_designer/airplane/ConstructionStepNode.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-designer-topology/json-polymorphic-roundtrip/` | 🟢 |
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` | `cad-designer-topology/`, `cad-designer-topology/json-polymorphic-roundtrip/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `cad-generation/wing-export-task/`, `construction-plans/plan-execution/` | 🟢 |
| `cad_designer/airplane/JSONStepNode.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-designer-topology/json-polymorphic-roundtrip/` | 🟢 |
| `cad_designer/airplane/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/Position.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py` | `cad-designer-topology/`, `cad-designer-topology/json-polymorphic-roundtrip/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/airplane/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/components/ComponentInformation.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/components/EngineInformation.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/components/Servo.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/components/ServoInformation.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/components/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/models/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/printer3d/Printer3dSettings.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/printer3d/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/wing/Airfoil.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py` | `cad-designer-topology/`, `cad-designer-topology/json-polymorphic-roundtrip/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/Spare.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/wing/Turbulator.py` | `cad-designer-topology/`, `wing-design/turbulator-optimizer/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/WingConfiguration.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `wing-design/cross-section-crud/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/WingSegment.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/aircraft_topology/wing/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/__init__.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-designer-topology/json-polymorphic-roundtrip/` | 🟢 |
| `cad_designer/airplane/creator/_creator_template.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/`, `cad-designer-topology/json-polymorphic-roundtrip/`, `construction-plans/`, `construction-plans/creator-catalog/` | 🟢 |
| `cad_designer/airplane/creator/cad_operations/AddMultipleShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/Cut2ShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/CutMultipleShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/Fuse2ShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/FuseMultipleShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/Intersect2ShapesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/RepairFacesShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/ScaleRotateTranslateCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/SimpleOffsetShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/cad_operations/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/components/ComponentImporterCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/components/ServoImporterCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/components/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/ExportToIgesCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/ExportToStepCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/ExportToStlCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/IgesImportCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/StepImportCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/export_import/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/EngineCapeShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/EngineCoverAndMountPanelAndFuselageShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/EngineMountShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/FuselageElectronicsAccessCutOutShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/FuselageReinforcementShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/FuselageShellShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/FuselageWingSupportShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/WingAttachmentBoltCutoutShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/WingReinforcementShapeCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/fuselage/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/wing/StandWingSegmentOnPrinterCreator.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/wing/VaseModeWingCreator.py` | `cad-designer-topology/creator-execution-model/` | 🟢 |
| `cad_designer/airplane/creator/wing/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/creator/wing/ted_sketch_creators.py` | `cad-designer-topology/`, `cad-designer-topology/creator-execution-model/` | 🟢 |
| `cad_designer/airplane/geometry/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/geometry/segment_split.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/geometry/spar_cad_insertion.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/airplane/types.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/cq_plugins/__init__.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/cq_plugins/display/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/display/display.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/fix_shape/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/fix_shape/fix_shape.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/offest3D/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/offest3D/offset3D.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/scaleXyz/__init__.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/cq_plugins/scaleXyz/scaleXyz.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/` | 🟢 |
| `cad_designer/cq_plugins/segmentToEdge/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/segmentToEdge/segmentToEdge.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/sew_fix_shape/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/sew_fix_shape/sew_fix_shape.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/wing/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/wing/airfoil.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/wing/airfoil_old.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/wing/wing_root_segment.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/cq_plugins/wing/wing_segment.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/decorators/__init__.py` | `cad-designer-topology/` | 🟡 |
| `cad_designer/decorators/general_decorators.py` | `cad-designer-topology/`, `cad-designer-topology/wingconfiguration-coordinate-system/`, `construction-plans/`, `construction-plans/plan-execution/` | 🟢 |

### `aero-analysis`

> Aerodynamic analysis pipeline: VLM/AeroBuildup, operating points and sets, trim/retrim, stability, strip forces, spanwise loads, speed polar, flight envelope, turn kinematics, invalidation-driven recompute.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/utils.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `avl-integration/avl-run-and-parse/` | 🟢 |
| `app/api/v2/endpoints/aeroanalysis.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `aero-analysis/stability-derivatives/`, `platform-core/`, `platform-core/transaction-and-error-handling/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/design_assumptions.py` | `aero-analysis/aero-context-single-source/`, `mission-and-sizing/`, `mission-and-sizing/design-assumptions/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/speed_polar.py` | `aero-analysis/` | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `avl-integration/`, `avl-integration/avl-run-and-parse/`, `mission-and-sizing/`, `mission-and-sizing/operating-point-sweep/` | 🟢 |
| `app/core/background_jobs.py` | `aero-analysis/retrim-invalidation/`, `mission-and-sizing/design-assumptions/`, `platform-core/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/core/events.py` | `aero-analysis/retrim-invalidation/`, `mission-and-sizing/design-assumptions/`, `platform-core/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/core/json_safe.py` | `aero-analysis/`, `platform-core/`, `platform-core/transaction-and-error-handling/` | 🟢 |
| `app/main.py` | `aero-analysis/`, `aeroplane-core/`, `aeroplane-core/aeroplane-crud/`, `aeroplane-core/airplane-configuration-export/`, `aeroplane-core/component-tree/`, `aeroplane-core/weight-rollup/`, `ai-copilot/`, `avl-integration/`, `cad-generation/`, `cad-generation/wing-export-task/`, `mass-and-balance/`, `mcp-server/`, `mcp-server/rest-mcp-reuse/`, `mcp-server/tool-registration/`, `mission-and-sizing/`, `platform-core/`, `platform-core/app-bootstrap-lifespan/`, `platform-core/background-jobs-invalidation/`, `platform-core/config-and-settings/`, `platform-core/transaction-and-error-handling/`, `powertrain/`, `versioning/` | 🟢 |
| `app/models/analysismodels.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `aero-analysis/retrim-invalidation/`, `mission-and-sizing/operating-point-sweep/` | 🟢 |
| `app/models/avl_geometry_events.py` | `aero-analysis/`, `aero-analysis/retrim-invalidation/`, `aero-analysis/stability-derivatives/`, `avl-integration/`, `avl-integration/avl-geometry-generation/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/models/computation_config.py` | `aero-analysis/`, `aero-analysis/aero-context-single-source/`, `aero-analysis/retrim-invalidation/`, `mission-and-sizing/`, `mission-and-sizing/design-assumptions/` | 🟢 |
| `app/models/stability_events.py` | `aero-analysis/`, `aero-analysis/retrim-invalidation/`, `aero-analysis/stability-derivatives/`, `avl-integration/`, `avl-integration/avl-geometry-generation/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/models/stability_result.py` | `aero-analysis/`, `aero-analysis/stability-derivatives/` | 🟢 |
| `app/schemas/aeroanalysisschema.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `avl-integration/`, `avl-integration/avl-geometry-generation/`, `avl-integration/avl-run-and-parse/`, `mission-and-sizing/operating-point-sweep/` | 🟢 |
| `app/schemas/polar_by_config.py` | `aero-analysis/aero-context-single-source/` | 🟢 |
| `app/schemas/polar_re_table.py` | `aero-analysis/aero-context-single-source/` | 🟢 |
| `app/schemas/spanwise_loads.py` | `aero-analysis/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/stability.py` | `aero-analysis/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/strip_forces.py` | `aero-analysis/` | 🟢 |
| `app/services/add_turn_service.py` | `aero-analysis/` *(owner resolved from import graph)* | 🟡 |
| `app/services/aerobuildup_trim_service.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/` | 🟢 |
| `app/services/analysis_service.py` | `aero-analysis/` | 🟢 |
| `app/services/assumption_compute_service.py` | `aero-analysis/`, `aero-analysis/aero-context-single-source/`, `mission-and-sizing/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/services/design_assumptions_service.py` | `aero-analysis/retrim-invalidation/`, `mission-and-sizing/`, `mission-and-sizing/design-assumptions/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/services/invalidation_service.py` | `aero-analysis/`, `aero-analysis/aero-context-single-source/`, `aero-analysis/retrim-invalidation/`, `fuselage-design/`, `fuselage-design/superellipse-xsecs/`, `mission-and-sizing/design-assumptions/`, `platform-core/`, `platform-core/background-jobs-invalidation/`, `wing-design/`, `wing-design/cross-section-crud/` | 🟢 |
| `app/services/operating_point_generator_service.py` | `aero-analysis/`, `avl-integration/control-surface-naming/`, `mission-and-sizing/`, `mission-and-sizing/operating-point-sweep/` | 🟢 |
| `app/services/operating_point_resolver.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/` | 🟢 |
| `app/services/polar_re_table_service.py` | `aero-analysis/`, `aero-analysis/aero-context-single-source/`, `airfoil-catalog/`, `airfoil-catalog/low-re-polar-backfill/`, `airfoil-catalog/neuralfoil-analysis/`, `airfoil-catalog/suitability-search/` | 🟢 |
| `app/services/retrim_service.py` | `aero-analysis/`, `aero-analysis/retrim-invalidation/`, `avl-integration/control-surface-naming/`, `wing-design/control-surface-mixing/` | 🟢 |
| `app/services/spanwise_loads.py` | `aero-analysis/` | 🟡 |
| `app/services/speed_polar_service.py` | `aero-analysis/` | 🟡 |
| `app/services/stability_service.py` | `aero-analysis/`, `aero-analysis/retrim-invalidation/`, `aero-analysis/stability-derivatives/`, `avl-integration/control-surface-naming/`, `wing-design/control-surface-mixing/` | 🟢 |
| `app/services/trim_enrichment_service.py` | `aero-analysis/`, `aero-analysis/operating-point-solve/`, `avl-integration/control-surface-naming/`, `mission-and-sizing/operating-point-sweep/`, `wing-design/control-surface-mixing/` | 🟢 |
| `app/services/vlm_strip_forces.py` | `aero-analysis/` | 🟢 |
| `cad_designer/airplane/aircraft_topology/models/analysis_model.py` | `aero-analysis/` | 🟢 |

### `avl-integration`

> AVL geometry file generation, vortex spacing, subprocess runner, artefact persistence, strip forces, elevator authority.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/avl_geometry.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/` | 🟢 |
| `app/avl/geometry.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/` | 🟢 |
| `app/avl/spacing.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/` | 🟢 |
| `app/models/avl_geometry_file.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/` | 🟢 |
| `app/schemas/avl_artefact.py` | `avl-integration/avl-run-and-parse/` | 🗑 **slated for deletion** (`Q-AV-3`/`Q-AV-4` — parse, don't cache) |
| `app/schemas/avl_geometry.py` | `avl-integration/` *(owner resolved from import graph)* | 🟡 |
| `app/services/avl_artefact_service.py` | `avl-integration/avl-run-and-parse/` | 🗑 **slated for deletion** (`Q-AV-3`/`Q-AV-4`). ⚠ `build_yduplicate_sign_map` is **held**, not deleted — residual **R1** |
| `app/services/avl_geometry_service.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/`, `avl-integration/control-surface-naming/` | 🟢 |
| `app/services/avl_runner.py` | `avl-integration/`, `avl-integration/avl-run-and-parse/` | 🟢 |
| `app/services/avl_strip_forces.py` | `avl-integration/`, `avl-integration/avl-run-and-parse/` | 🟢 |
| `app/services/avl_trim_service.py` | `avl-integration/`, `avl-integration/avl-run-and-parse/` | 🟢 |
| `app/services/control_surface_mixing.py` | `avl-integration/`, `avl-integration/avl-geometry-generation/`, `avl-integration/control-surface-naming/`, `mission-and-sizing/operating-point-sweep/`, `wing-design/`, `wing-design/control-surface-mixing/` | 🟢 |

### `mass-and-balance`

> Components and component types, weight items, loading scenarios and templates, mass/CG computation, forward CG, COTS/carbon-tube import.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/mass_cg.py` | `mass-and-balance/`, `mass-and-balance/cg-mass-computation/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/weight_items.py` | `mass-and-balance/weight-items/` | 🗑 **slated for deletion** (`Q-MB-1`) |
| `app/schemas/mass_cg.py` | `mass-and-balance/`, `mass-and-balance/cg-mass-computation/` | 🟢 |
| `app/schemas/weight_item.py` | `mass-and-balance/weight-items/` | 🗑 **slated for deletion** (`Q-MB-1`) |
| `app/services/aeroplane_clone_service.py` | `mass-and-balance/weight-items/`, `versioning/`, `versioning/aeroplane-clone-subgraph/`, `versioning/copilot-provenance/`, `versioning/snapshot-immutability/` | 🟢 |
| `app/services/carbon_tube_import.py` | `mass-and-balance/` | 🟡 |
| `app/services/loading_template_service.py` | `mass-and-balance/` | 🟡 |
| `app/services/weight_items_service.py` | `mass-and-balance/`, `mass-and-balance/component-tree-mass-sync/` | 🟢 |

### `powertrain`

> Motor/ESC/battery/propeller sizing, powertrain performance and solution space, propeller polars and enrichment, endurance.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/powertrain_performance.py` | `powertrain/`, `powertrain/performance-model/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing_modal.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_solution_space.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/api/v2/endpoints/component_types.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/api/v2/endpoints/components.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/api/v2/endpoints/endurance.py` | `powertrain/` | 🟡 |
| `app/models/component.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/models/component_type.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/models/prop_polar.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `app/schemas/component.py` | `powertrain/cots-powertrain-components/` | 🟢 |
| `app/schemas/component_type.py` | `powertrain/cots-powertrain-components/` | 🟢 |
| `app/schemas/endurance.py` | `powertrain/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/powertrain_sizing.py` | `powertrain/powertrain-sizing/` | 🟢 |
| `app/schemas/powertrain_sizing_modal.py` | `powertrain/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/powertrain_solution_space.py` | `powertrain/powertrain-sizing/` | 🟢 |
| `app/services/component_service.py` | `powertrain/`, `powertrain/cots-powertrain-components/`, `powertrain/propeller-polars/` | 🟢 |
| `app/services/cots_import.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `app/services/endurance_service.py` | `powertrain/powertrain-sizing/` | 🟢 |
| `app/services/powertrain_performance.py` | `powertrain/`, `powertrain/performance-model/` | 🟢 |
| `app/services/powertrain_sizing_modal_service.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/services/powertrain_sizing_service.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/services/powertrain_solution_space_service.py` | `powertrain/`, `powertrain/powertrain-sizing/` | 🟢 |
| `app/services/prop_component_seed.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `app/services/prop_polar_enrich.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `app/services/prop_polar_import.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `scripts/enrich_apc_snapshot_pe0.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `scripts/import_apc_props.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `scripts/import_cots.py` | `powertrain/`, `powertrain/cots-powertrain-components/` | 🟢 |
| `scripts/parse_apc_pe0.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `scripts/parse_apc_props.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |
| `scripts/seed_propeller_components.py` | `powertrain/`, `powertrain/propeller-polars/` | 🟢 |

### `mission-and-sizing`

> Mission objectives/presets/KPIs, flight profiles, design assumptions and recompute, matching chart, tail sizing, static-margin sizing, field length.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/field_lengths.py` | `mission-and-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/flight_envelope.py` | `mission-and-sizing/`, `mission-and-sizing/flight-envelope/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/forward_cg.py` | `mission-and-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/loading_scenarios.py` | `mission-and-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/matching_chart.py` | `mission-and-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/mission_objectives.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/sm_suggestions.py` | `mission-and-sizing/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/tail_sizing.py` | `mission-and-sizing/` | 🟡 |
| `app/api/v2/endpoints/flight_profiles.py` | `mission-and-sizing/` | 🟢 |
| `app/models/flight_envelope_model.py` | `mission-and-sizing/`, `mission-and-sizing/flight-envelope/` | 🟢 |
| `app/models/flightprofilemodel.py` | `mission-and-sizing/` | 🟢 |
| `app/models/mission_objective.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/models/mission_preset.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/schemas/computation_config.py` | `mission-and-sizing/design-assumptions/` | 🟢 |
| `app/schemas/design_assumption.py` | `mission-and-sizing/`, `mission-and-sizing/design-assumptions/` | 🟢 |
| `app/schemas/field_length.py` | `mission-and-sizing/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/flight_envelope.py` | `mission-and-sizing/`, `mission-and-sizing/flight-envelope/` | 🟢 |
| `app/schemas/forward_cg.py` | `mission-and-sizing/` | 🟢 |
| `app/schemas/loading_scenario.py` | `mission-and-sizing/` | 🟢 |
| `app/schemas/matching_chart.py` | `mission-and-sizing/` *(owner resolved from import graph)* | 🟡 |
| `app/schemas/mission_kpi.py` | `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/schemas/mission_objective.py` | `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/schemas/sm_sizing.py` | `mission-and-sizing/` | 🟢 |
| `app/services/elevator_authority_service.py` | `mission-and-sizing/` | 🟢 |
| `app/services/field_length_service.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/services/flight_envelope_service.py` | `mission-and-sizing/`, `mission-and-sizing/flight-envelope/` | 🟢 |
| `app/services/flight_profile_service.py` | `mission-and-sizing/` | 🟢 |
| `app/services/loading_scenario_service.py` | `mission-and-sizing/`, `platform-core/background-jobs-invalidation/` | 🟢 |
| `app/services/matching_chart_service.py` | `mission-and-sizing/` | 🟢 |
| `app/services/mission_kpi_service.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/services/mission_objective_service.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/`, `platform-core/app-bootstrap-lifespan/` | 🟢 |
| `app/services/mission_preset_seed.py` | `mission-and-sizing/`, `mission-and-sizing/mission-objectives-presets/` | 🟢 |
| `app/services/sm_sizing_service.py` | `mission-and-sizing/` | 🟢 |
| `app/services/tail_sizing_service.py` | `mission-and-sizing/` | 🟡 |
| `app/services/turn_kinematics.py` | `mission-and-sizing/operating-point-sweep/` | 🟢 |

### `construction-plans`

> Construction plans, parts, templates, spar plans and inserts, build artefacts for 3D printing.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `alembic/versions/4a9c81984e86_add_construction_parts_table.py` | `construction-plans/construction-parts/` | 🟢 |
| `alembic/versions/b3e2f1a4c7d9_add_construction_plans_table.py` | `construction-plans/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `alembic/versions/c4d5e6f7a8b9_add_plan_type_and_aeroplane_id.py` | `construction-plans/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/construction_parts.py` | `construction-plans/`, `construction-plans/construction-parts/` | 🟢 |
| `app/api/v2/endpoints/aeroplane_construction_plans.py` | `construction-plans/`, `construction-plans/plan-execution/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/api/v2/endpoints/construction_templates.py` | `construction-plans/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/converters/spare_origin_preservation.py` | `construction-plans/spar-plan/`, `wing-design/`, `wing-design/cross-section-crud/`, `wing-design/spar-sizing/` | 🟢 |
| `app/models/construction_part.py` | `construction-plans/`, `construction-plans/construction-parts/` | 🟢 |
| `app/models/construction_plan.py` | `construction-plans/`, `construction-plans/plan-template-lifecycle/` | 🟢 |
| `app/schemas/construction_part.py` | `construction-plans/`, `construction-plans/construction-parts/` | 🟢 |
| `app/services/construction_part_service.py` | `construction-plans/`, `construction-plans/construction-parts/` | 🟢 |
| `app/services/spar_insert_service.py` | `construction-plans/spar-plan/`, `versioning/`, `versioning/snapshot-immutability/`, `wing-design/`, `wing-design/spar-sizing/` | 🟢 |
| `app/services/spar_plan_service.py` | `construction-plans/spar-plan/`, `wing-design/`, `wing-design/spar-sizing/` | 🟢 |
| `cad_designer/airplane/geometry/spar_solver.py` | `construction-plans/spar-plan/`, `wing-design/`, `wing-design/spar-sizing/` | 🟢 |

### `versioning`

> Aircraft design versioning and branching: snapshots, clone, compare, geometry diff, branch/main semantics.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `alembic/versions/15f45e64a7c0_gh903_versioning_db_model.py` | `versioning/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/design_versions.py` | `versioning/` | 🟢 |
| `app/schemas/design_version.py` | `versioning/` | 🟢 |
| `app/services/design_version_service.py` | `versioning/` | 🟢 |
| `frontend/lib/versioning-api.ts` | `versioning/` | 🟡 |

### `openvsp-import`

> OpenVSP .vsp3 import pipeline: adapter probing, wing/fuselage/blank/custom handlers, control-surface mapping, airfoil generation, solid sewing, STEP export, streaming progress.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/api/v2/endpoints/openvsp_import.py` | `openvsp-import/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/converters/openvsp_adapter.py` | `openvsp-import/`, `openvsp-import/step-export-and-sewing/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/converters/openvsp_airfoil.py` | `openvsp-import/`, `openvsp-import/geom-handlers/` | 🟢 |
| `app/converters/openvsp_blank_handler.py` | `openvsp-import/`, `openvsp-import/geom-handlers/` | 🟢 |
| `app/converters/openvsp_custom_handler.py` | `openvsp-import/`, `openvsp-import/geom-handlers/` | 🟢 |
| `app/converters/openvsp_fuselage_handler.py` | `openvsp-import/`, `openvsp-import/geom-handlers/` | 🟢 |
| `app/converters/openvsp_importer.py` | `openvsp-import/`, `openvsp-import/geom-handlers/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/converters/openvsp_ss_control.py` | `openvsp-import/`, `openvsp-import/geom-handlers/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/converters/openvsp_validation.py` | `openvsp-import/`, `openvsp-import/geom-handlers/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/converters/openvsp_wing_handler.py` | `openvsp-import/`, `openvsp-import/geom-handlers/` | 🟢 |
| `app/services/openvsp_import_service.py` | `openvsp-import/`, `openvsp-import/geom-handlers/`, `openvsp-import/step-export-and-sewing/`, `openvsp-import/vsp3-import-pipeline/` | 🟢 |
| `app/services/openvsp_solid_sewing_service.py` | `openvsp-import/`, `openvsp-import/step-export-and-sewing/` | 🟢 |
| `scripts/vspaero_benchmark/build_dashboard.py` | `openvsp-import/` | 🟢 |
| `scripts/vspaero_benchmark/compare.py` | `openvsp-import/` | 🟢 |
| `scripts/vspaero_benchmark/pipeline_asb.py` | `openvsp-import/` | 🟢 |
| `scripts/vspaero_benchmark/pipeline_vspaero.py` | `openvsp-import/` | 🟢 |
| `scripts/vspaero_benchmark/run_all.py` | `openvsp-import/` | 🟢 |

### `ai-copilot`

> In-app AI copilot: LLM hub client, deterministic domain tools, conversation history, SSE streaming, proposal apply flow.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `alembic/versions/705e8e49ef47_add_copilot_messages_table.py` | `ai-copilot/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/__init__.py` | `ai-copilot/`, `mission-and-sizing/`, `platform-core/`, `versioning/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/copilot_history.py` | `ai-copilot/` | 🟢 |
| `app/api/v2/endpoints/aeroplane/copilot_stream.py` | `ai-copilot/`, `ai-copilot/copilot-turn-loop/` | 🟢 |
| `app/schemas/copilot_edits.py` | `ai-copilot/`, `ai-copilot/proposal-adopt-discard/` | 🟢 |
| `app/schemas/copilot_history.py` | `ai-copilot/`, `ai-copilot/copilot-turn-loop/` | 🟢 |
| `app/services/aeroplane_version_service.py` | `ai-copilot/`, `ai-copilot/copilot-tools/`, `ai-copilot/proposal-adopt-discard/`, `construction-plans/spar-plan/`, `versioning/`, `versioning/branch-model/`, `versioning/copilot-provenance/`, `versioning/snapshot-immutability/` | 🟢 |
| `app/services/copilot_apply_service.py` | `ai-copilot/`, `ai-copilot/proposal-adopt-discard/`, `versioning/`, `versioning/copilot-provenance/` | 🟢 |
| `app/services/copilot_history_service.py` | `ai-copilot/` | 🟢 |
| `app/services/copilot_service.py` | `ai-copilot/`, `ai-copilot/copilot-turn-loop/` | 🟢 |
| `app/services/copilot_tools.py` | `ai-copilot/`, `ai-copilot/copilot-tools/`, `ai-copilot/proposal-adopt-discard/` | 🟢 |
| `frontend/components/workbench/CopilotStrip.tsx` | `ai-copilot/` | 🟡 |
| `frontend/hooks/useCopilotProposal.ts` | `ai-copilot/proposal-adopt-discard/`, `frontend-workbench/` | 🟢 |
| `scripts/uat_copilot_driver.py` | `ai-copilot/` | 🟢 |

### `mcp-server`

> FastMCP tool surface — 76 tools plus image/data resources delegating to the v2 endpoint functions; mounted at /mcp.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/mcp_server.py` | `mcp-server/`, `mcp-server/rest-mcp-reuse/`, `mcp-server/tool-registration/`, `platform-core/transaction-and-error-handling/` | 🟢 |

### `platform-core`

> Cross-cutting infrastructure: pydantic-settings config, DB session/transaction boundary, repository helpers, exception hierarchy and HTTP mapping, domain events, invalidation, background job tracker, platform capability probes, logging.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `alembic/env.py` | `platform-core/` | 🟡 |
| `alembic/versions/011adab08ca7_gh_729_add_step_path_to_fuselages_for_.py` | `platform-core/` | 🟡 |
| `alembic/versions/09316cc77273_add_airfoils_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/0e7ea09c363d_extend_components_table_bbox_model_ref.py` | `platform-core/` | 🟡 |
| `alembic/versions/11b6fc7c9e67_add_propeller_polar_tables_gh_995.py` | `platform-core/` | 🟡 |
| `alembic/versions/1294198940a9_added_operating_point_and_operating_.py` | `platform-core/` | 🟡 |
| `alembic/versions/16cbb884a838_gh_821_airfoil_low_re_polar_and_geometry.py` | `platform-core/` | 🟡 |
| `alembic/versions/1a39e098d77e_add_file_path_format_to_construction_.py` | `platform-core/` | 🟡 |
| `alembic/versions/1bc333d5b078_merge_n1_d2_heads.py` | `platform-core/` | 🟡 |
| `alembic/versions/1f320603c2cf_extend_brushless_motor_esc_component_.py` | `platform-core/` | 🟡 |
| `alembic/versions/1f3b9c42e3aa_extend_operating_points_for_generation.py` | `platform-core/` | 🟡 |
| `alembic/versions/28a13fbeac90_add_component_types_table_and_seed.py` | `platform-core/` | 🟡 |
| `alembic/versions/294aeab71af5_seed_slope_soarer_mission_preset.py` | `platform-core/` | 🟡 |
| `alembic/versions/2f80f5c2b22f_added_total_mass_attribute_to_aeroplane.py` | `platform-core/` | 🟡 |
| `alembic/versions/3b58409a0f04_gh_477_add_landing_field_inputs_to_.py` | `platform-core/` | 🟡 |
| `alembic/versions/4705ef4e571b_add_trim_enrichment_to_operating_points.py` | `platform-core/` | 🟡 |
| `alembic/versions/4b41e90d0adb_repair_double_encoded_component_types_.py` | `platform-core/` | 🟡 |
| `alembic/versions/4b4f6929f284_add_wing_xsec_detail_tables_for_full_.py` | `platform-core/` | 🟡 |
| `alembic/versions/5a0f2c4a9b52_seed_flying_wing_mission_preset.py` | `platform-core/` | 🟡 |
| `alembic/versions/5b41e8c65a14_add_mission_objectives_and_weight_items_.py` | `platform-core/` | 🟡 |
| `alembic/versions/6063db4db84f_backfill_mission_objectives_for_.py` | `platform-core/` | 🟡 |
| `alembic/versions/6aa821735324_add_role_and_label_to_ted.py` | `platform-core/` | 🟡 |
| `alembic/versions/6d2bb7cc35f4_add_rc_flight_profiles_and_assignment.py` | `platform-core/` | 🟡 |
| `alembic/versions/6eca6229ba65_gh_934_add_wing_xsec_turbulators_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/7cc3eaf27d6b_add_construction_part_id_to_component_.py` | `platform-core/` | 🟡 |
| `alembic/versions/7fd2cf7284ce_mission_tables_presets_objectives.py` | `platform-core/` | 🟡 |
| `alembic/versions/83493febb34a_added_index_to_sort_wingxsecs.py` | `platform-core/` | 🟡 |
| `alembic/versions/84ead4fd6131_gh_715_add_symmetric_flag_to_fuselages.py` | `platform-core/` | 🟡 |
| `alembic/versions/87bb4e31e610_add_avl_geometry_files_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/93509b051fb3_renamed_total_mass_attribute_to_total_.py` | `platform-core/` | 🟡 |
| `alembic/versions/93d974f885f1_add_design_versions_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/94e41782f22d_add_components_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/9b7e11e8de24_merge_heads_for_flight_profiles.py` | `platform-core/` | 🟡 |
| `alembic/versions/a1b2c3d4e5f6_add_design_assumptions_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/a1c9f3e7b210_gh951_add_dihedral_to_wing_xsecs.py` | `platform-core/` | 🟡 |
| `alembic/versions/a3f8c1d2e4b5_gh1009_esc_schema_enrichment_english_bec_toggles.py` | `platform-core/` | 🟡 |
| `alembic/versions/a4f26dfb6c22_add_flight_envelopes_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/a6a68bfaf421_initial_schema.py` | `platform-core/` | 🟡 |
| `alembic/versions/a7f1c3d2e5b8_add_component_id_to_ted_servo.py` | `platform-core/` | 🟡 |
| `alembic/versions/a85f8972a5df_english_only_motor_glider_and_flying_.py` | `platform-core/` | 🟡 |
| `alembic/versions/b2ce6f00fe42_unify_spare_origin_vector_units_to_mm_.py` | `platform-core/` | 🟡 |
| `alembic/versions/b3c4d5e6f7a8_add_control_deflections_to_operating_points.py` | `platform-core/` | 🟡 |
| `alembic/versions/b456b2d255b9_add_component_tree_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/b5297a4b135a_gh_731_add_solid_step_path_to_fuselages.py` | `platform-core/` | 🟡 |
| `alembic/versions/b7d4e2a91c33_gh1000_add_weight_inertia_geometry_to_propeller_polars.py` | `platform-core/` | 🟡 |
| `alembic/versions/bfb7cc64edfa_add_design_model_to_wings.py` | `platform-core/` | 🟡 |
| `alembic/versions/c19d4f2e7c34_unify_ted_control_surface_ted_only.py` | `platform-core/` | 🟡 |
| `alembic/versions/c3a5992b6f25_gh_772_ted_mix_gains_differential.py` | `platform-core/` | 🟡 |
| `alembic/versions/c5d6e7f8a9b0_add_stability_results_table.py` | `platform-core/` | 🟡 |
| `alembic/versions/cdcac8fb40b5_add_computation_config_table_and_.py` | `platform-core/` | 🟡 |
| `alembic/versions/d8015f98814c_gh1083_wood_stock_types_and_abachi.py` | `platform-core/` | 🟡 |
| `alembic/versions/d89e43f1f4ef_added_operating_point_and_operating_.py` | `platform-core/` | 🟡 |
| `alembic/versions/df18c9f3ba1d_added_fuselage_xsection_sort_index.py` | `platform-core/` | 🟡 |
| `alembic/versions/e2a35c6eac69_gh1008_material_structural_fields_and_seed.py` | `platform-core/` | 🟡 |
| `alembic/versions/e7387f35f31e_seed_motor_glider_mission_preset.py` | `platform-core/` | 🟡 |
| `alembic/versions/edeb222a39a8_add_loading_scenarios_table_gh_488.py` | `platform-core/` | 🟡 |
| `alembic/versions/ee9fd32e8e90_add_variant_to_propeller_polars_gh_999.py` | `platform-core/` | 🟡 |
| `app/api/v2/endpoints/health.py` | `platform-core/`, `platform-core/config-and-settings/` | 🟢 |
| `app/api/v2/endpoints/versioning.py` | `platform-core/transaction-and-error-handling/`, `versioning/`, `versioning/branch-model/`, `versioning/copilot-provenance/`, `versioning/snapshot-immutability/` | 🟢 |
| `app/core/platform.py` | `platform-core/`, `platform-core/app-bootstrap-lifespan/` | 🟢 |
| `app/core/security.py` | `platform-core/` | 🟢 |
| `app/db/base.py` | `platform-core/`, `platform-core/transaction-and-error-handling/` | 🟢 |
| `app/db/repository.py` | `platform-core/` | 🟡 |
| `app/logging_config.py` | `platform-core/`, `platform-core/app-bootstrap-lifespan/`, `platform-core/config-and-settings/` | 🟢 |
| `app/services/component_type_service.py` | `platform-core/app-bootstrap-lifespan/`, `powertrain/`, `powertrain/cots-powertrain-components/`, `powertrain/propeller-polars/` | 🟢 |

### `frontend-workbench`

> Next.js 16 App Router design workbench: workbench shell + 6 domain routes (analysis, components, construction-plans, mission, powertrain, airfoil-preview), 121 components, 48 SWR hooks, three-cad-viewer 3D viewer, Plotly charts, playwright-bdd E2E.

The frontend is aggregated by directory (400+ files would drown the table).
Files individually cited by a unit document are listed in full underneath.

| Legacy area | Files | Covering unit(s) | Coverage |
|---|---:|---|---|
| `app/schemas/` | 1 | `frontend-workbench/` | 🟢 |
| `frontend/` | 1 | `frontend-workbench/` | 🟢 |
| `frontend/app/` | 2 | `frontend-workbench/` | 🟡 |
| `frontend/app/workbench/` | 8 | `frontend-workbench/` | 🟡 |
| `frontend/components/ui/` | 1 | `frontend-workbench/` | 🟡 |
| `frontend/components/workbench/` | 127 | `frontend-workbench/` | 🟡 |
| `frontend/hooks/` | 47 | `frontend-workbench/` | 🟡 |
| `frontend/lib/` | 21 | `frontend-workbench/` | 🟡 |
| `frontend/types/` | 2 | `frontend-workbench/` | 🟢 |

<details><summary>Individually cited frontend files (14)</summary>

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/schemas/versioning.py` | `frontend-workbench/`, `versioning/`, `versioning/branch-model/`, `versioning/copilot-provenance/`, `versioning/snapshot-immutability/` | 🟢 |
| `frontend/components/workbench/metrics-dashboard/metricsMock.ts` | `frontend-workbench/`, `frontend-workbench/analysis-dashboards-plotly/` | 🟢 |
| `frontend/hooks/useCopilot.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/hooks/useTessellation.ts` | `frontend-workbench/`, `frontend-workbench/cad-viewer-integration/` | 🟢 |
| `frontend/hooks/useVersioning.ts` | `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/lib/api.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/lib/fetcher.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/lib/parseApiError.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/`, `platform-core/transaction-and-error-handling/` | 🟢 |
| `frontend/lib/sseStream.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/lib/versionGraphLayout.ts` | `frontend-workbench/` | 🟢 |
| `frontend/lib/versionGraphViewState.ts` | `frontend-workbench/`, `frontend-workbench/workbench-shell-and-routing/` | 🟢 |
| `frontend/next.config.ts` | `frontend-workbench/`, `frontend-workbench/cad-viewer-integration/` | 🟢 |
| `frontend/types/versionGraph.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |
| `frontend/types/versioning.ts` | `frontend-workbench/`, `frontend-workbench/data-fetching-swr/` | 🟢 |

</details>

## Unmapped production files — candidates for further analysis

22 production files are claimed by no module prefix, cited by no unit
document, and could not be resolved from the import graph. Grouped by why:

**Build / type configuration** (4)

> Type shims and test-runner configuration. No behaviour to specify.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `frontend/next-env.d.ts` | — | n/a |
| `frontend/playwright.config.ts` | — | n/a |
| `frontend/plotly-gl3d.d.ts` | — | n/a |
| `frontend/vitest.config.ts` | — | n/a |

**Operational tooling** (11)

> One-off scripts run by a maintainer, not by the service. Data ingestion, the AVL build, and the VSPAERO cross-validation harness. Out of the runtime surface — reimplementing da3Dalus does not require them, but the COTS ingestion scripts encode real domain rules (see the owning modules' `requirements.md`).

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `scripts/build_avl.py` | — | n/a |
| `scripts/e2e_versioning.py` | — | n/a |
| `scripts/fetch_apc_props.py` | — | n/a |
| `scripts/import_carbon_tubes.py` | — | n/a |
| `scripts/openvsp_import_trace.py` | — | n/a |
| `scripts/parse_apc_xlsx.py` | — | n/a |
| `scripts/parse_dpower_pdfs.py` | — | n/a |
| `scripts/vspaero_benchmark/benchmark_config.py` | — | n/a |
| `scripts/vspaero_benchmark/debug_no_fuselage.py` | — | n/a |
| `scripts/vspaero_benchmark/debug_wing_only.py` | — | n/a |
| `scripts/vspaero_benchmark/setup_only_sanity.py` | — | n/a |

**Schema with ambiguous ownership** (5)

> A Pydantic contract imported by handlers in **more than one** module, so the import graph yields no single owner. The behaviour IS documented — in the consuming module's `contracts.md` — but the file itself has no home unit. These are the rows most worth a second pass.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/schemas/WingAnalysisRequest.py` | — | n/a |
| `app/schemas/flight_profile.py` | — | n/a |
| `app/schemas/section_geometry.py` | — | n/a |
| `app/schemas/spar_insert.py` | — | n/a |
| `app/schemas/spar_plan.py` | — | n/a |

**Unreferenced** (2)

> No importer anywhere in the tree. Likely dead or template code.

| Legacy file | Covering unit(s) | Coverage |
|---|---|---|
| `app/db/exceptions.py` | — | 🗑 **slated for deletion** (`Q-CC-16`, `P-DEAD-0`) |
| `app/services/example.py` | — | 🗑 **slated for deletion** (`Q-CC-16`, `P-DEAD-0`) |

## Test files

516 test files were found. They are evidence about the units rather than
behaviour to reimplement, and are aggregated here by area.

| Test area | Files |
|---|---:|
| `app/tests/` | 302 |
| `cad_designer/tests/` | 27 |
| `frontend/__tests__/` | 181 |
| `frontend/e2e/` | 6 |

## Known limits of this matrix

- Citation matching is **textual**. A unit that describes a file's behaviour without
  naming its path is scored 🟡, not 🟢 — the real documented coverage is therefore at
  least as good as the 🟢 number, never worse.
- Non-source assets are out of scope: the 1665 airfoil `.dat` files under
  `components/airfoils/`, the COTS snapshots under `data/cots/`, the vendored AVL Fortran
  under `Avl/`, and SQL/JSON fixtures. They are described in the owning modules'
  `requirements.md` but have no source-file row here.
- `cad_designer/` is frozen by [ADR 0002](../adrs/0002-cad-designer-is-frozen-new-creators-only.md).
  Its rows document what exists; they are **not** an invitation to modify it.

