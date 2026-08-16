# Spec Impact Matrix

> Produced by the **Reversa Architect** (`doc_level = completo`).
> Grounded in the `dependencies` field of `.reversa/context/modules.json`, the
> per-module *Coupling* and *🔴 GAPs* sections of
> [`../code-analysis.md`](../code-analysis.md), and the clone/invalidation
> registries.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

**How to read it.** A row is *"I am changing this"*. A column is *"this is what
I will have to re-verify"*. The matrix is **directed and asymmetric** — many
pairs are coupled in exactly one direction.

| Symbol | Meaning |
|---|---|
| **●** | **Direct** — an import, a shared table, a shared schema or a call. A change here can break the target at build/run time. |
| **○** | **Indirect** — coupled through a shared contract (the computation context, the `$TYPE` dialect, the unit boundary, an event). Breaks show up as *wrong numbers*, not as errors. |
| **◐** | **Latent** — the coupling exists in a dormant, dead or unwired path. It will not break today, but it will resurrect the moment the path is used. |
| **·** | No meaningful coupling. |

---

## ⚠ Re-derived cells after the specification-validation interview (2026-08-15)

The grid **shape** is unchanged — §1 and §2 are module-granular, so deleting a
*unit* removes no row. But several coupling justifications rested on units that
no longer exist, and those cells now mean something different:

| Cell | Was justified by | Now |
|---|---|---|
| `CG ↔ FW` ● | largely the wing-tessellation path | the live 3D path is **construction-plan execution only** (`Q-CG-4`); the coupling survives but through `_tessellate_shapes` and the export/zip path, not the deleted cache |
| `cad-generation` I-3 / I-8 | tessellation of wing geometry | same — re-read as plan execution |
| `MB → AC` / `MS` / `PT` ● | `weight_items` as a mass source | the **component tree is the sole mass authority** (`Q-MB-1`); the arrows hold, the producer changed |
| `AV` row | included the artefact-replay path | that path is **withdrawn** (`Q-AV-3`/`Q-AV-4`) — the index→name map is parsed per run, so the coupling is to AVL's *output format*, not to a persisted artefact |
| **CS-4** `$TYPE` dialect | referenced `WingLoftCreator.py` | **unchanged, and now a measured example.** The file is a regular `AbstractShapeCreator` emitted as a `$TYPE` by `cad_service.py:238`; **4 stored `construction_plans` reference it by name**, so deleting or renaming it would invalidate them — the precise hazard CS-4 describes. Its former listing under `wing-tessellation` was a mis-filing, corrected in `code-spec-matrix.md` |

**Not re-derived:** the ● / ○ / ◐ / · symbols themselves. Every arrow above still
points the same way; only the reason changed. Re-run the dependency scan before
treating the grid as measured rather than inherited.

---

## 1. Module × Module

Codes: **AC** aeroplane-core · **WD** wing-design · **FD** fuselage-design ·
**AF** airfoil-catalog · **CG** cad-generation · **CT** cad-designer-topology ·
**CP** construction-plans · **VI** openvsp-import · **AA** aero-analysis ·
**AV** avl-integration · **MS** mission-and-sizing · **MB** mass-and-balance ·
**PT** powertrain · **VS** versioning · **CO** ai-copilot · **MC** mcp-server ·
**PC** platform-core · **FW** frontend-workbench

| change ↓ / affects → | AC | WD | FD | AF | CG | CT | CP | VI | AA | AV | MS | MB | PT | VS | CO | MC | PC | FW |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **AC** aeroplane-core | — | ● | ● | · | ● | ○ | ● | ● | ● | ● | ● | ● | ○ | ● | ● | ● | ○ | ● |
| **WD** wing-design | ● | — | ○ | ● | ● | ● | ● | ● | ● | ● | ● | ○ | · | ● | ● | ● | · | ● |
| **FD** fuselage-design | ● | ○ | — | · | ● | ● | ● | ● | ● | ◐ | ○ | ○ | · | ● | ○ | ● | · | ● |
| **AF** airfoil-catalog | · | ● | · | — | ○ | ● | ○ | ● | ● | ● | ● | · | · | ○ | ○ | ● | · | ● |
| **CG** cad-generation | ○ | ● | ○ | · | — | ● | ● | · | · | · | · | · | · | ○ | · | ● | ○ | ● |
| **CT** cad-designer-topology | ○ | ● | ● | ○ | ● | — | ● | ○ | ● | ● | ○ | · | · | · | ○ | ● | · | ● |
| **CP** construction-plans | ● | ● | ○ | · | ● | ● | — | · | · | · | · | ○ | ● | ○ | · | · | · | ● |
| **VI** openvsp-import | ● | ● | ● | ● | ● | ○ | · | — | ○ | ○ | ○ | ● | · | ● | ○ | · | ○ | ● |
| **AA** aero-analysis | ○ | ● | ○ | ● | · | · | · | · | — | ● | ● | ○ | ○ | ○ | ● | ● | ○ | ● |
| **AV** avl-integration | · | ● | ◐ | ● | · | · | · | · | ● | — | ○ | · | · | · | · | ● | · | ● |
| **MS** mission-and-sizing | ○ | ● | ○ | ● | · | · | · | · | ● | — | — | ● | ● | ○ | ● | ● | ○ | ● |
| **MB** mass-and-balance | ● | ○ | · | · | · | · | ○ | ● | ○ | · | ● | — | ● | ● | ● | ● | ○ | ● |
| **PT** powertrain | ○ | ● | · | · | · | · | ● | · | ○ | · | ● | ● | — | · | · | · | · | ● |
| **VS** versioning | ● | ● | ● | · | ○ | · | ○ | ○ | ○ | ○ | ○ | ● | · | — | ● | · | · | ● |
| **CO** ai-copilot | ○ | ● | · | · | · | · | · | · | ● | · | ● | ○ | · | ● | — | · | · | ● |
| **MC** mcp-server | ● | ● | ● | ● | ● | · | · | · | ● | ○ | ● | · | · | · | · | — | ● | · |
| **PC** platform-core | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | — | ● |
| **FW** frontend-workbench | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | — |

### Reading the asymmetries 🟢

* **`PC` platform-core is a full row of ●, and an almost empty column.** Nothing
  in the domain reaches back into the platform. Changing `get_db()`, the
  exception hierarchy, `NonFiniteSafeJSONResponse`, the event bus or the
  capability probes touches all 17 other modules; changing a domain module never
  touches the platform.
* **`FW` frontend-workbench has an empty row.** The frontend is a pure consumer
  — it owns no persistent entity and no backend module imports it. The reverse
  is the point: **every** backend module's contract change lands on it, and
  because backend types are hand-mirrored (only `types/versioning.ts` and
  `types/versionGraph.ts` are shared, nothing is generated from
  `/openapi.json`), the failure surfaces at `npx tsc --noEmit` against
  hand-written fixtures rather than at the boundary itself. 🟡 (**TD-30**) —
  `Q-CC-11` schedules TypeScript client generation, which moves the failure to
  the boundary. **Ordering constraint:** it must land *after* the ADR 0019
  cleanups (`Q-AF-4` airfoil route merge, `Q-VS-8` UUID routes, `Q-WD-2`
  description clarification, `Q-FD-1`/`Q-CC-6` status and prefix fixes), or the
  leaks are baked into generated code and become materially harder to remove.
* **`AC` aeroplane-core is the aggregate root**, so it is dense in both
  directions. But its column entries are mostly "resolve the aeroplane" —
  cheaper to satisfy than its row entries.
* **`FD` → `AV` is ◐, not ●.** `AvlBody` / `BFIL` exist in the AVL emitter but
  nothing constructs one — fuselages are never sent to AVL, so AVL runs are
  wing-only. A fuselage change cannot affect an AVL result *today*.
* **`AA` → `MS` and `MS` → `AA` are both ●** — they are a genuine mutual
  dependency, mediated entirely by `assumption_computation_context`.
  `assumption_compute_service.py` is physically listed under `mission-and-sizing`
  but is documented in both modules for exactly this reason.
* **`MC` mcp-server's row is dense but its column is empty.** It imports 9
  endpoint modules directly; nothing imports it back except `main.py`. Any
  endpoint signature change silently breaks an MCP tool — FastMCP derives the
  tool's input schema from the **handler signature**, so a renamed parameter is
  a contract break with no compile-time signal. 🟢 **ADR 0025 removes this
  coupling entirely:** the MCP surface is rebuilt on `copilot_tools` and stops
  tracking the REST contract, so an endpoint signature change no longer reaches
  a tool. That is deliberate — the two have different consumers, and coupling
  them is what produced a 76-tool surface nobody designed (`Q-MC-2`).

---

## 2. Module × External integration

Integration ids follow [`../c4-context.md`](../c4-context.md) §4.

| module ↓ / integration → | I-1 ASB+NF | I-2 AVL | I-3 CadQuery | I-4 OpenVSP | I-5 VSPAERO | I-6 LLM hub | I-7 MCP | I-8 ocp-vscode | I-9 Chromium | I-10 Sonar | I-11 GitHub | I-12 ACR | I-13 COTS |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| aeroplane-core | · | · | ○ | · | · | · | ● | · | · | ○ | ○ | · | · |
| wing-design | ● | ● | ● | ○ | ○ | · | ● | · | · | ○ | ○ | · | ● |
| fuselage-design | ● | ◐ | ● | ● | · | · | ● | · | · | ○ | ○ | · | · |
| airfoil-catalog | ● | ● | · | ○ | · | · | ● | · | ● | ○ | ○ | · | · |
| cad-generation | · | · | ● | · | · | · | ● | ○ | · | ○ | ○ | ● | · |
| cad-designer-topology | ● | · | ● | · | · | · | · | ● | · | **excluded** | ○ | ● | · |
| construction-plans | · | · | ● | · | · | · | · | ● | · | ○ | ○ | · | ● |
| openvsp-import | ○ | · | ● | ● | ● | · | · | · | · | ○ | ○ | · | · |
| aero-analysis | ● | ● | · | · | ● | · | ● | · | ● | ○ | ○ | · | · |
| avl-integration | ● | ● | · | · | ● | · | ● | · | · | ○ | ○ | · | · |
| mission-and-sizing | ● | · | · | · | · | · | ● | · | · | ○ | ○ | · | · |
| mass-and-balance | ● | · | · | ○ | · | · | · | · | · | ○ | ○ | · | · |
| powertrain | ○ | · | · | · | · | · | · | · | · | ○ | ○ | · | ● |
| versioning | · | · | · | ○ | · | · | · | · | · | ○ | ○ | · | · |
| ai-copilot | ● | · | · | · | · | ● | · | · | · | ○ | ○ | · | · |
| mcp-server | ○ | ○ | ○ | · | · | · | ● | · | ● | ○ | ○ | · | · |
| platform-core | ● | ● | ● | ● | · | ● | ● | · | ● | ● | ● | ● | ● |
| frontend-workbench | · | · | · | · | · | ○ | · | · | · | ● | ● | · | ● |

Notes 🟢

* `cad-designer-topology` is **deliberately excluded** from SonarCloud
  (`sonar.exclusions`) and ruff (`extend-exclude`) — ≈22 000 LOC unlinted and
  unmeasured. That exclusion is itself a coupling: any quality-gate change that
  narrows it immediately surfaces hundreds of findings (**TD-36**).
* I-1 (AeroSandbox) and I-3 (CadQuery) are **platform-gated** on
  `linux/aarch64`. Every ● in those columns is also a `try/except ImportError`
  site: `fuselage_slice_service.py:42-48`,
  `airfoil_low_re_service.py:458-462`, `section_geometry.py:181-184`,
  `wing_service._recompute_spare_vectors:872`, and the five conditionally
  registered routers in `main.py`. ADR 0017.
* I-12 (Azure CR) is marked ● for `cad-generation` / `cad-designer-topology`
  only because the stale `azure-pipelines.yml` still builds an image containing
  them. The pipeline references a Dockerfile path that does not exist
  (**TD-38**).

---

## 3. The five contract surfaces that carry most of the coupling

Coupling in this codebase is not mostly module-to-module — it is
**artifact-mediated**. Five shared artifacts explain the majority of the ○
entries above. Change any of them and the blast radius is the whole column.

| # | Contract surface | Where | Who depends on it | What breaks silently |
|---|---|---|---|---|
| **CS-1** | **`app/converters/model_schema_converters.py`** (1 104 l.) — schema ↔ model ↔ `WingConfiguration` ↔ AeroSandbox, including the gh-788 "main wing = largest planform" rule | `app/converters/` | `cad-generation`, `aero-analysis`, `avl-integration`, `openvsp-import`, `construction-plans`, `ai-copilot`, `mass-and-balance` | reference geometry (`s_ref`, `c_ref`, `b_ref`) silently taken from the wrong wing → every coefficient wrong by the area ratio (the original F1/gh-788 bug was ≈8×) |
| **CS-2** | **`aeroplanes.assumption_computation_context`** — the ~40-key JSON produced once at the cruise point. ADR 0004 | `assumption_compute_service._cache_context()` | speed polar, V-n envelope, matching chart, mission KPIs, endurance, spar sizing, powertrain solution space, copilot drag breakdown, copilot stability tool | a renamed or dropped key falls through to a hard-coded default (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg`) with only a log warning — the answer stays *structurally valid and physically meaningless* |
| **CS-3** | **The unit boundary** — mm in `WingConfig`/`cad_designer`, m in the DB/ASB, mm-inside-the-metre-DB for `wing_xsec_spares`, grams for `components.mass_g`, inches for propeller geometry, radians for `operating_points.alpha/beta`. ADR 0001 | `_convert_spare_to_meters/_mm`, `scale_db_origin_to_config`, `_scale_asb_wing_geometry_schema`, `operating_point_model_to_schema` | every geometry, mass and analysis path | there is **no type-level unit**. A missed conversion produces a number that is exactly 1 000× or 57.3× wrong and passes every schema validation |
| **CS-4** | **The `$TYPE` serialisation dialect** — `GeneralJSONEncoder/Decoder` resolves a class with `getattr` on its own module namespace | `cad_designer/airplane/GeneralJSONEncoderDecoder.py` | `construction_plans.tree_json` (every stored plan), `cad_service.build_wing_blueprint`, `components/constructions/*.json` | **renaming or deleting a Creator invalidates every stored plan referencing the old name.** Nine removed classes are already referenced by three shipped plan JSONs (**TD-22**) |
| **CS-5** | **The gh-772 control-axis names** — `[{role}]{axis}_{wing_key}_{xsec_index}` produced by `control_surface_mixing.axis_control_name` | `app/services/control_surface_mixing.py` | the AVL geometry builder, the AeroSandbox airplane builder, `trim_enrichment_service`, `retrim_service`, `stability_service` | 🟢 **Resolved structurally by `Q-WD-1`:** `control_surface_mixing` owns a resolver that `trim_enrichment_service`, `retrim_service` and `stability_service` are **required** to call, and the silent ±25° fallback is removed — keying on the raw DB TED name becomes impossible rather than discouraged. Measured: 7 `ruddervator` surfaces on 3 aircraft (`tdfalconv2`, `Olek`, `eHawk`) were trimmed under the old fallback and need their stored results invalidated |

Two further, narrower surfaces worth naming:

* **CS-6 — `invalidation_service`.** The geometry-change fan-out.
  `mark_ops_dirty` is called by **seven publishers by hand**, immediately before
  `event_bus.publish(...)`; the handlers do *not* call it, yet their log lines
  read "OPs marked DIRTY". A new geometry-mutating path that publishes but
  forgets to mark leaves stale operating points with no warning. 🟡 `Q-AA-4`
  factors the duplicated listeners out so a geometry write publishes once, and
  `Q-PC-4` replaces the retrim short-circuit with coalescing; **atomicity of
  mark-and-publish itself was not put to the maintainer** and remains inferred.
* **CS-7 — `aeroplane_clone_service.CLONED_TABLES` / `EXCLUDED_TABLES`.** Every
  table with a transitive FK to `aeroplanes` must appear in exactly one set,
  asserted by `test_aeroplane_clone_coverage.py`. The test discovers tables by
  introspecting SQLAlchemy `ForeignKey` objects, so the three **soft-reference**
  tables (`component_tree`, `construction_plans`, `construction_parts`) are
  invisible to it and must be registered by hand. 🟢 `Q-VS-4` and `Q-CC-7`
  migrate all three soft references to **real foreign keys**, so the coverage
  test discovers them like every other table and hand registration stops being
  necessary. `Q-CC-7`'s motivation is not PostgreSQL but a defect present today
  under SQLite: deleting an aeroplane leaves orphaned rows behind.

---

## 4. Hot files — highest fan-in

| File | Fan-in | Ripples to |
|---|---|---|
| `app/converters/model_schema_converters.py` | 7 modules | CS-1 above |
| `app/services/assumption_compute_service.py` (809 l. in one function's pipeline) | 9 consumers | CS-2 |
| `app/models/aeroplanemodel.py` | 12 modules | declares `AeroplaneModel`, `BranchModel` **and every wing/fuselage/weight/assumption model** — one file holds most of the schema |
| `app/db/session.py` (`get_db`) | all | the transaction contract; the four legitimate own-session exceptions (two lifespan seeders, `_recompute_sync`, `JobTracker._run_backfill_for_names`) and the one illegitimate one (`mcp_server._call_endpoint`) |
| `app/services/control_surface_mixing.py` | 5 consumers | CS-5 |
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` | every stored plan | CS-4 — **frozen**, so the coupling can only be worked around, never fixed |
| `app/services/wing_service.py` (1 585 l.) | 6 modules | the mm↔m boundary and all spar/TED/servo/turbulator CRUD |
| `app/main.py` | all | router registration order is load-bearing (`versioning` before `aeroplane` so `/aeroplanes/compare` wins over `/aeroplanes/{id}`) |
| `app/mcp_server.py` (1 552 l.) | 9 endpoint modules | one file *is* the whole MCP module |
| `frontend/components/workbench/AnalysisViewerPanel.tsx` (1 567 l.) | the analysis tab | one of **seven** components over 1 000 lines; the tab pages are thin, the panels are not |

---

## 5. Change recipes — what to re-verify

Derived from the coupling above plus the project's own Iron Laws.

| If you change… | You must also… |
|---|---|
| **Any SQLAlchemy model** | add an Alembic migration chained onto the real head (`d8015f98814c`) with a **uuid4-hex** revision id — implementer agents invent predictable ids that collide and produce "Cycle is detected"; register the table in `CLONED_TABLES` **or** `EXCLUDED_TABLES` with a reason; if the aeroplane reference is a plain `String`, register it *by hand* (CS-7) |
| **A key in `assumption_computation_context`** | grep all nine consumers (CS-2). A missing key does not raise — it falls back to an RC-typical default with a log warning |
| **A converter or the main-wing rule** | re-run the aero regression: `s_ref`/`c_ref`/`b_ref` must still come from the **largest-planform** wing, not `wings[0]` (gh-788 / F1) |
| **A Creator class name or its `__init__` signature** | every stored `construction_plans.tree_json` referencing the old `$TYPE` becomes undecodable, and the Creator Catalog (built by `inspect.signature` + docstring parsing) changes shape for the frontend gallery |
| **A control-surface role, axis or name** | update **all five** CS-5 consumers together; `assert_unique_control_names` must still pass (AVL silently collapses duplicate CONTROL names into one DOF) |
| **A v2 endpoint signature** | check `app/mcp_server.py` — FastMCP derives the tool input schema from the handler signature, with no compile-time link |
| **A response schema field** | run `cd frontend && npx tsc --noEmit` before pushing. vitest and eslint pass while `tsc` fails: a new required interface field breaks existing test-fixture literals. Node **22** is mandatory (Node ≥ 24 breaks jsdom `localStorage`) |
| **A `pyproject.toml` dependency** | commit the regenerated `poetry.lock` in the same change or CI install fails |
| **Anything under `cad_designer/aircraft_topology/` or `GeneralJSONEncoderDecoder.py`** | don't. It is frozen by policy (ADR 0002). New behaviour goes into a new `AbstractShapeCreator` subclass |
| **A COTS snapshot or importer** | run the matching reimport CLI (`import_cots.py` / `import_apc_props.py` / `seed_propeller_components.py`) and **restart the backend** — migrations move keys, reimports move values, and `uvicorn --reload` does not cover module-level importer state |
| **A geometry-mutating service path** | wire it through `invalidation_service` **and** call `mark_ops_dirty` yourself before publishing (CS-6) |
| **Aero-dependent service code** | add a *mocked fast* test that stubs the solver boundary — the SonarCloud `new_coverage` gate runs the CI fast tier **without** AeroSandbox/CadQuery/AVL, so unmocked aero code counts as uncovered |

---

## 6. Coupling risk summary

| Risk | Modules involved | Why it is structural, not incidental |
|---|---|---|
| **Silent numeric drift** | AA ↔ MS ↔ MB ↔ PT | The coupling medium is a schemaless JSON column with per-consumer fallback defaults. There is no contract test between producer and consumers. |
| **Unit leakage** | WD ↔ CT ↔ CG ↔ VI | Six unit systems coexist and none is expressed in the type system. Three named conversion helpers are the entire enforcement. |
| **Frozen-library gravity** | CT ← WD, FD, CG, CP, AA | ≈22 k LOC that cannot be fixed, is not linted and is not measured, but is on the critical path of every geometry operation. Known defects (dead perpendicular-spare branch, `gp_D*` singleton mutation, `_main_wing_index = 0`) are documented-and-left. |
| **Contract-free API mirroring** | FW ← all backend modules | 48 hooks each redeclare their own response types. `tsc` against hand-written fixtures is the only detector. |
| **Signature-derived tool schemas** | MC ← 9 endpoint modules | The MCP tool contract is an emergent property of Python signatures, with no test that drives a real endpoint through a real session (which is also why **TD-01** went unnoticed). |

---

*Related: [`../c4-components.md`](../c4-components.md) ·
[`../architecture.md`](../architecture.md) (technical-debt register) ·
[`../code-analysis.md`](../code-analysis.md) (per-module detail) ·
[`../questions.md`](../questions.md) (open questions)*
