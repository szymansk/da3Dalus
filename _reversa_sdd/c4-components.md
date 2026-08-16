# C4 Level 3 — Components

> Produced by the **Reversa Architect** (`doc_level = completo`).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Notation: Mermaid `flowchart` with C4 stereotype labels — see the note in
> [`c4-context.md`](c4-context.md).
>
> Three containers are decomposed here:
> **C-A** the FastAPI application's service layer (the 18 modules),
> **C-B** the aerodynamic solver stack,
> **C-C** the CAD / geometry stack.

---

## C-A — FastAPI application: the 18 modules

The request flow is uniform and enforced by convention plus
`.claude/rules/python-conventions.md`:

```
endpoint (thin: validate → delegate → return a Pydantic schema)
   → service (business logic, external tools, orchestration)
      → model (SQLAlchemy) | schema (Pydantic) | converter (schema ↔ model ↔ CAD ↔ ASB)
```

The 18 modules fall into five concentric rings. Ring membership predicts blast
radius: a change in ring 1 or 2 reaches almost everything; a change in ring 5
reaches almost nothing.

| Ring | Modules | Why here |
|---|---|---|
| **1 — Platform** | `platform-core` | App composition, `get_db()`, exceptions, event bus, job tracker, capability probes. Everything imports it. |
| **2 — Domain core** | `aeroplane-core`, `wing-design`, `fuselage-design`, `airfoil-catalog` | The aggregate root and its geometry. The converter hub (`model_schema_converters.py`) lives here and is imported by four other rings. |
| **3 — Analysis & intent** | `aero-analysis`, `avl-integration`, `mission-and-sizing`, `mass-and-balance` | Produce and consume the single-source aero context. |
| **4 — Fabrication & parts** | `cad-generation`, `cad-designer-topology`, `construction-plans`, `openvsp-import`, `powertrain` | Turn the design into geometry, files and a BoM. |
| **5 — Change & interfaces** | `versioning`, `ai-copilot`, `mcp-server`, `frontend-workbench` | Wrap the whole thing in history and two API surfaces. |

```mermaid
flowchart TB
    subgraph R5["Ring 5 — Change management and interfaces"]
        direction LR
        M_VER["versioning<br/>«Component»<br/>aeroplane_version_service, aeroplane_clone_service<br/>DAG of aeroplane rows. 17 cloned tables,<br/>18 excluded with mandatory reasons. ADR 0006"]
        M_COP["ai-copilot<br/>«Component»<br/>copilot_service, copilot_tools, copilot_apply_service<br/>6-tool registry, 7-op edit DSL,<br/>writes ONLY to a proposal branch. ADR 0007"]
        M_MCP["mcp-server<br/>«Component»<br/>mcp_server.py, 1552 lines<br/>76 tools re-entering v2 endpoint functions.<br/>Writes never commit. TD-01"]
        M_FE["frontend-workbench<br/>«Component»<br/>Next.js SPA. 48 SWR hooks,<br/>129 workbench components."]
    end

    subgraph R4["Ring 4 — Fabrication and parts"]
        direction LR
        M_CADG["cad-generation<br/>«Component»<br/>cad_service, tessellation_service,<br/>tessellation_cache_service, artifact_service<br/>Process pool + export blueprint. ADR 0005"]
        M_TOPO["cad-designer-topology<br/>«Component»<br/>cad_designer/ 22k LOC.<br/>FROZEN topology + 29 Creators.<br/>Unlinted, unmeasured. ADR 0002"]
        M_PLAN["construction-plans<br/>«Component»<br/>construction_plan_service,<br/>construction_part_service<br/>DOLLAR-TYPE plan trees, SSE execution"]
        M_VSP["openvsp-import<br/>«Component»<br/>openvsp_importer + 4 handlers,<br/>openvsp_import_service, sewing, STEP export.<br/>ADR 0018"]
        M_PWR["powertrain<br/>«Component»<br/>component_service, component_type_service,<br/>prop polar import, performance,<br/>solution space, sizing sweep. ADR 0013"]
    end

    subgraph R3["Ring 3 — Analysis and design intent"]
        direction LR
        M_AERO["aero-analysis<br/>«Component»<br/>analysis_service, vlm_strip_forces,<br/>stability_service, retrim_service,<br/>trim_enrichment_service, invalidation_service"]
        M_AVL["avl-integration<br/>«Component»<br/>app/avl geometry emitter, avl_runner,<br/>avl_strip_forces, neuralfoil_cdcl_service,<br/>control_surface_mixing. ADR 0003"]
        M_MIS["mission-and-sizing<br/>«Component»<br/>assumption_compute_service,<br/>design_assumptions_service, flight_envelope,<br/>matching_chart, OP generator. ADR 0010"]
        M_MASS["mass-and-balance<br/>«Component»<br/>mass_cg_service, weight_items_service.<br/>CG is top-down, never a raw sum. ADR 0011"]
    end

    subgraph R2["Ring 2 — Domain core"]
        direction LR
        M_AERC["aeroplane-core<br/>«Component»<br/>aeroplane_service, component_tree_service<br/>The aggregate root."]
        M_WING["wing-design<br/>«Component»<br/>wing_service 1585 l., spar_sizing,<br/>spar_plan_service, turbulator_optimizer<br/>THE mm-to-m conversion boundary. ADR 0001"]
        M_FUS["fuselage-design<br/>«Component»<br/>fuselage_service, fuselage_slice_service<br/>Superellipse xsecs + STEP roles."]
        M_AF["airfoil-catalog<br/>«Component»<br/>airfoil_service, airfoil_low_re_service,<br/>suitability_service, airfoil_tags<br/>1665 dat files, 13-point Re grid."]
        M_CONV["converters<br/>«Component: app/converters»<br/>model_schema_converters.py 1104 l.<br/>THE HUB. schema to model to WingConfig to ASB."]
    end

    subgraph R1["Ring 1 — Platform"]
        M_PLAT["platform-core<br/>«Component»<br/>main.py create_app + lifespan,<br/>db/session.py get_db ADR 0009,<br/>core/exceptions, core/events, core/background_jobs,<br/>core/platform probes ADR 0017, core/json_safe"]
    end

    DBX[("35 tables<br/>SQLite WAL / PostgreSQL")]

    M_FE -->|"REST + SSE"| R4
    M_FE -->|"REST + SSE"| R3
    M_MCP --> M_AERC
    M_MCP --> M_WING
    M_MCP --> M_FUS
    M_MCP --> M_AERO
    M_MCP --> M_MIS
    M_COP --> M_VER
    M_COP --> M_WING
    M_COP --> M_MIS
    M_COP --> M_AERO
    M_VER --> M_AERC

    M_CADG --> M_TOPO
    M_CADG --> M_WING
    M_PLAN --> M_TOPO
    M_PLAN --> M_WING
    M_PLAN --> M_PWR
    M_VSP --> M_WING
    M_VSP --> M_FUS
    M_VSP --> M_AF
    M_VSP --> M_MASS
    M_PWR --> M_MIS

    M_AERO --> M_CONV
    M_AERO --> M_AVL
    M_AERO --> M_MIS
    M_AVL --> M_CONV
    M_MIS --> M_AERO
    M_MIS --> M_MASS
    M_MASS --> M_AERC

    M_WING --> M_CONV
    M_FUS --> M_CONV
    M_AERC --> M_CONV
    M_WING --> M_AF
    M_CONV --> M_TOPO

    R2 --> M_PLAT
    R3 --> M_PLAT
    R4 --> M_PLAT
    M_PLAT --> DBX

    classDef ring1 fill:#FF8400,stroke:#111,color:#111,font-weight:bold
    classDef ring2 fill:#3A2000,stroke:#FF8400,color:#fff
    classDef ring3 fill:#1A1A1A,stroke:#FF8400,color:#fff
    classDef ring4 fill:#17171A,stroke:#7A7B78,color:#fff
    classDef ring5 fill:#2E2E2E,stroke:#7A7B78,color:#fff
    class M_PLAT ring1
    class M_AERC,M_WING,M_FUS,M_AF,M_CONV ring2
    class M_AERO,M_AVL,M_MIS,M_MASS ring3
    class M_CADG,M_TOPO,M_PLAN,M_VSP,M_PWR ring4
    class M_VER,M_COP,M_MCP,M_FE ring5
```

### The three structural hubs 🟢

1. **`app/converters/model_schema_converters.py` (1 104 lines)** — every wing,
   fuselage and airplane conversion passes through it. `cad-generation`,
   `aero-analysis`, `avl-integration`, `openvsp-import`, `construction-plans`
   and `ai-copilot` all depend on it. It is also where the gh-788 "main wing =
   largest planform" rule lives.
2. **`aeroplanes.assumption_computation_context` (a JSON column)** — the
   *data* hub. ~40 keys produced once by `recompute_assumptions` and read by the
   speed polar, V-n envelope, matching chart, mission KPIs, endurance, spar
   sizing, powertrain solution space and the copilot. ADR 0004.
3. **`app/services/invalidation_service.py`** — the *control* hub. Every
   geometry-mutating path must route through it or its operating points go
   stale silently.

### Two dependency cycles, broken by lazy imports 🟢

* `wing_service` / `fuselage_service` → `component_tree_service`
  (auto-sync of `wing:<name>` / `fuselage:<name>` groups, gh-108) →
  `mass_cg_service` → back into the assumption layer. Broken by
  function-local imports inside `_sync_aircraft_mass`.
* `aeroplanes ↔ branches` at the **DDL** level (`aeroplanes.branch_id →
  branches.id` and `branches.root_id/head_id → aeroplanes.id`). Broken with
  `use_alter=True` on all four constraints, so Alembic emits them as separate
  `ALTER TABLE` statements, plus a three-step flush dance in
  `create_aeroplane`.

---

## C-B — The aerodynamic solver stack

Two invariants govern the whole stack (ADR 0003, ADR 0004):

1. **AeroSandbox is the default; AVL is the exception.** Every default path
   (α sweep, simple sweep, strip forces, retrim, assumption recompute, OP
   generation, streamlines) runs AeroBuildup or the in-process VLM.
2. **One aero truth per aircraft.** `cd0` (parasite, *not* total CD),
   `e_oswald`, `(L/D)max` and `x_np` are produced once at the cruise point and
   cached. No consumer re-derives them.

```mermaid
flowchart TB
    subgraph Entry["Entry points"]
        direction LR
        EP1["REST: alpha_sweep, simple_sweep,<br/>strip_forces, stability_summary,<br/>streamlines, spanwise_loads"]
        EP2["Background: retrim_service,<br/>assumption_compute_service"]
        EP3["Copilot tool: run_analysis<br/>60 s cap"]
        EP4["OP generator: 15 targets,<br/>two-stage trim"]
    end

    DISP["analyse_aerodynamics<br/>«Component: app/api/utils.py»<br/>THE ONLY solver dispatcher.<br/>Always returns AnalysisModel plus optional Figure.<br/>Sets xyz_ref to the operating point CG,<br/>applies with_control_deflections."]

    subgraph Solvers["Solver implementations"]
        direction LR
        S1["AeroBuildup<br/>«External: aerosandbox 4.2.9»<br/>run_with_stability_derivatives.<br/>DEFAULT. Vectorised over array alpha."]
        S2["VortexLatticeMethod<br/>«External: aerosandbox»<br/>Preceded by remesh_uniform_density:<br/>40 panels per half, distributed by span.<br/>Inviscid, so cdv and cm are emitted as 0."]
        S3["AVLRunner<br/>«Component: app/services/avl_runner.py»<br/>Subprocess. Rejects array alpha or beta.<br/>Native indirect constraints, per-section CDCL,<br/>roll and yaw of mixed surfaces."]
    end

    subgraph Geom["Geometry supply"]
        direction LR
        G1["aeroplane_schema_to_asb_airplane<br/>«Component: converters»<br/>main wing = largest planform, gh-788.<br/>Overrides s_ref, c_ref, b_ref."]
        G2["build_avl_geometry_file<br/>«Component: avl_geometry_service»<br/>repr of the dataclass tree IS the .avl file.<br/>Panel spacing heuristics, CDCL injection."]
        G3["control_surface_mixing<br/>«Component»<br/>role to control-axis decomposition, gh-772.<br/>Single source shared by AVL, ASB and enrichment."]
        G4["NeuralFoil<br/>«External: neuralfoil 0.3.2»<br/>2-D surrogate. 3-point CDCL polar,<br/>low-Re airfoil backfill, turbulator xtr sweep."]
    end

    RES["AnalysisModel<br/>«Component: cad_designer analysis_model.py»<br/>Solver-agnostic envelope.<br/>from_avl_dict and from_abu_dict.<br/>reference.Xnp, coefficients, derivatives,<br/>control_surfaces, flight_condition."]

    subgraph Ctx["The single aero truth — ADR 0004"]
        RECOMP["recompute_assumptions<br/>«Component: assumption_compute_service, 809 lines»<br/>12-step pipeline: stability run, coarse sweep,<br/>fine sweep, parabolic fit, Trefftz e,<br/>per-config polars, Re-band table, V-speeds,<br/>CG and stability envelopes, landing field."]
        CTXJ[("assumption_computation_context<br/>JSON on aeroplanes<br/>~40 keys: speeds, geometry, aero,<br/>polars, stability and CG, envelope, provenance")]
    end

    subgraph Cons["Consumers — all READ, none re-derive"]
        direction LR
        C1["speed polar"]
        C2["V-n and gust envelope"]
        C3["matching chart"]
        C4["mission KPIs, endurance"]
        C5["spar sizing"]
        C6["powertrain solution space"]
        C7["copilot drag breakdown"]
    end

    EP1 --> DISP
    EP2 --> DISP
    EP3 --> DISP
    EP4 --> S1
    DISP --> S1
    DISP --> S2
    DISP --> S3
    G1 --> DISP
    G3 --> G1
    G3 --> G2
    G2 --> S3
    G4 --> G2
    G4 --> S1
    S1 --> RES
    S2 --> RES
    S3 --> RES
    RES --> RECOMP
    RECOMP --> CTXJ
    CTXJ --> C1
    CTXJ --> C2
    CTXJ --> C3
    CTXJ --> C4
    CTXJ --> C5
    CTXJ --> C6
    CTXJ --> C7

    BAD["stability_service._auto_populate_cd0<br/>writes TOTAL CD into the cd0 assumption<br/>on a different trigger.<br/>VIOLATES ADR 0004. TD-08"]
    RES -.->|"contamination path"| BAD
    BAD -.-> CTXJ

    classDef hub fill:#FF8400,stroke:#111,color:#111,font-weight:bold
    classDef bad fill:#5A1417,stroke:#E5484D,color:#fff
    classDef norm fill:#1A1A1A,stroke:#7A7B78,color:#fff
    class DISP,CTXJ hub
    class BAD bad
    class S1,S2,S3,G1,G2,G3,G4,RES,RECOMP,EP1,EP2,EP3,EP4,C1,C2,C3,C4,C5,C6,C7 norm
```

### Solver-selection reality 🟢

| Path | Default | AVL reachable? |
|---|---|---|
| `analyze_wing` / `analyze_airplane` | caller-selected | yes — `analysis_tool=avl` |
| `get_stability_summary` | caller-selected | yes |
| strip forces / spanwise loads | `solver="vlm"` (ASB) | yes — `?solver=avl` |
| streamlines / four-view | `VORTEX_LATTICE`, hard-coded | **no** |
| α sweep / simple sweep | `AEROBUILDUP`, hard-coded | **no** — AVL rejects array sweeps |
| `recompute_assumptions` | `AEROBUILDUP` | **no** |
| OP generation + background retrim | AeroBuildup / `asb.Opti` | **no** |
| `trim_with_avl` | — | this endpoint *is* the AVL path |

🔴 **AVL runs are wing-only.** `AvlBody` / `BFIL` exist in the emitter but
nothing constructs one, so fuselages are never sent to AVL.

---

## C-C — The CAD / geometry stack

```mermaid
flowchart TB
    subgraph AppSide["app/ — orchestration (editable, linted, measured)"]
        direction TB
        O1["cad_service<br/>«Component»<br/>build_wing_blueprint, export worker,<br/>task registry, ProcessPoolExecutor 4x spawn"]
        O2["tessellation_service + _cache_service + _hooks<br/>«Component»<br/>2 s debounce, cancels in-flight futures,<br/>discards a stale result on hash mismatch"]
        O3["construction_plan_service<br/>«Component»<br/>Creator catalog by introspection,<br/>execute_plan and execute_plan_streaming"]
        O4["artifact_service<br/>«Component»<br/>ARTIFACTS_BASE_DIR guardrails:<br/>resolve then relative_to, symlink rejection"]
        O5["converters: wing_model_to_wing_config,<br/>asb_wing_schema_to_wing_config<br/>scale 1000.0 = metres to millimetres"]
    end

    subgraph CD["cad_designer/ — 22k LOC, excluded from ruff and SonarCloud. ADR 0002"]
        direction TB
        subgraph Frozen["FROZEN — read-only by policy"]
            F1["aircraft_topology/<br/>WingConfiguration 1050 l., WingSegment,<br/>Airfoil, Spare, TrailingEdgeDevice, Turbulator,<br/>Servo, CoordinateSystem, AirplaneConfiguration,<br/>FuselageConfiguration, Printer3dSettings"]
            F2["GeneralJSONEncoderDecoder<br/>DOLLAR-TYPE dialect. Resolves classes with getattr<br/>on its own module namespace, so topology<br/>classes can NEVER appear in a plan JSON."]
        end
        subgraph Open["OPEN — new code allowed"]
            N1["creator/ — 29 Creators in 5 categories:<br/>wing 3, fuselage 9, cad_operations 9,<br/>export_import 6, components 2"]
            N2["geometry/ — spar_solver, section_geometry,<br/>segment_split, spar_cad_insertion.<br/>Actively developed, still unlinted. TD-36"]
            N3["cq_plugins/ — Workplane monkey patches:<br/>fix_shape, offset3D, display, sewAndFix,<br/>airfoil, wing_root_segment, wing_segment"]
            N4["aerosandbox/ — slicing 1339 l.,<br/>convert2aerosandbox, wing_roundtrip 857 l."]
        end
    end

    KERNEL["CadQuery 2.7 / cadquery-ocp 7.8 / OCCT<br/>«External System»<br/>NOT thread-safe. Global BRepCheck messaging,<br/>memory pools, interrupt handlers."]

    OUT1[("STEP / STL / IGES / 3MF<br/>tmp/exports then zipped")]
    OUT2[("tessellation JSON<br/>ocp_tessellate, cached per component")]
    OUT3[("spar plan: rod and tube pieces,<br/>joints, utilisation, feasibility<br/>CAD-FREE decision logic")]

    O5 --> F1
    O1 --> O5
    O1 -->|"pickled AsbWingSchema over spawn"| N1
    O2 -->|"pickled AsbWingSchema over spawn"| N1
    O3 -->|"IN THE REQUEST PROCESS. Contradicts ADR 0005. TD-10"| F2
    F2 --> N1
    N1 --> N3
    N1 --> KERNEL
    N3 --> KERNEL
    N2 -->|"analytic mode avoids the 13 s loft"| F1
    N2 --> OUT3
    N4 --> KERNEL
    O1 --> OUT1
    O2 --> OUT2
    O3 --> O4
    O4 --> OUT1

    classDef frozen fill:#5A1417,stroke:#E5484D,color:#fff
    classDef open fill:#1A1A1A,stroke:#30A46C,color:#fff
    classDef app fill:#FF8400,stroke:#111,color:#111
    class F1,F2 frozen
    class N1,N2,N3,N4 open
    class O1,O2,O3,O4,O5 app
```

### The frozen / editable split 🟢

`cad_designer/CLAUDE.md` is the authority. `aircraft_topology/**` and
`GeneralJSONEncoderDecoder.py` are read-only — bugs and Sonar findings there are
*deliberately* not fixed. `creator/`, `geometry/`, `cq_plugins/` and
`decorators/` are open. The one approved topology change is gh-934's
`Turbulator` plus the `turbulator` parameter on `WingSegment` and
`WingConfiguration`.

Enforcement is by **exclusion, not by code**: `sonar.exclusions = …,cad_designer/**`
and ruff `extend-exclude = [… "cad_designer" …]`. ≈22 000 LOC is neither linted
nor measured — including the actively developed `geometry/` subtree
(**TD-36**).

### The two serialisation systems 🟢

They never mix, and knowing which one you are in is load-bearing:

| System | Marker | Used for | Universe |
|---|---|---|---|
| `$TYPE` dialect (`GeneralJSONEncoder/Decoder`) | `"$TYPE": "<ClassName>"` | construction plan trees (`construction_plans.tree_json`, `build_wing_blueprint`) | exactly what `GeneralJSONEncoderDecoder` imports: `ConstructionRootNode`, `ConstructionStepNode`, and `from …creator import *` |
| `__getstate__` / `from_json_dict` | **none** | topology objects: the `/wingconfig` endpoints, `AirplaneConfiguration.to_dict()` | every topology class |

Topology objects reach a running plan only as **decoder kwargs**
(`wing_config`, `fuselage_config`, `servo_information`, `printer_settings`,
`engine_information`, `component_information`).

**Consequence:** renaming or deleting a Creator invalidates every stored plan
that references the old `$TYPE`. 🔴 Nine removed Creator classes are still
referenced by three shipped plan JSONs (**TD-22**).

---

*Next: [`erd-complete.md`](erd-complete.md) · [`architecture.md`](architecture.md)*
