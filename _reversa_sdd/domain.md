# Domain Model — da3Dalus / cad-modelling-service

> Produced by the **Reversa Detective** (`doc_level = completo`).
> Confidence markers: 🟢 CONFIRMED (read from code, a migration, or a commit
> body) · 🟡 INFERRED (pattern-based, or a plausible reading of intent that the
> code does not state) · 🔴 GAP (not determinable from the repository).
>
> Sources: `_reversa_sdd/code-analysis.md`, `_reversa_sdd/data-dictionary.md`,
> `_reversa_sdd/inventory.md`, the Git history (1 495 commits, 2022-07 →
> 2026-07), `CLAUDE.md` / `app/CLAUDE.md` / `cad_designer/CLAUDE.md`, and
> `docs/decisions/`.
>
> Companion documents: `state-machines.md` (lifecycles), `permissions.md`
> (trust boundary), `adrs/` (17 retroactive Architecture Decision Records).

---

## 0. What the system is, in domain terms

**da3Dalus** is a *conceptual and preliminary aircraft design workbench* for
**RC model aircraft and small UAVs**. It is not a CAD program with an aero
plug-in, and not an aero tool with a geometry importer — it is a single
**design loop** in which one parametric aircraft description simultaneously
drives:

1. **manufacturable geometry** (CadQuery solids, STEP/STL/3MF export, 3-D
   printed wings, carbon spar layout),
2. **aerodynamic prediction** (AeroSandbox AeroBuildup / VLM, a vendored AVL,
   NeuralFoil airfoil surrogates),
3. **classical preliminary sizing** (matching chart, V-n envelope, CG envelope,
   field length, endurance, powertrain),
4. **a bill of materials** (COTS component library, mass and CG roll-up).

Two audiences are served by the same model 🟢 (`user_target_audience`, and
visible in the code): non-professional hobbyists *and* professional RC/UAV
designers. That duality is why the domain vocabulary mixes academic terms
(neutral point, Oswald factor, Reynolds band) with hobby terms (wing cube
loading, hand launch, 3-D acro), and why almost every computed number carries a
*provenance* and a *confidence* alongside it.

---

## 1. Domain glossary

### 1.1 The aircraft aggregate

| Term | Meaning in this system | Confidence |
|---|---|---|
| **Aeroplane** | The aggregate root. One row in `aeroplanes`; owns wings, fuselages, weight items, design assumptions, loading scenarios, the component tree and the copilot thread. Addressed publicly by **UUID**, internally by integer PK. Since gh-903 it is *also* a versioning node. | 🟢 |
| **Airplane configuration** | The CAD-side export payload (`AirplaneConfiguration`) assembled from wings + fuselages + total mass. Requires a mass or the request is rejected with 422. | 🟢 |
| **Wing** | A lifting surface — main wing, horizontal tail, vertical tail, canard, winglet are *all* `wings` rows. There is no `surface_role` column; the "main wing" is derived as the **largest planform area** (gh-788). | 🟢 |
| **Main wing** | The wing with the largest `area()`. Supplies `s_ref`, `c_ref` (MAC), `b_ref` to every aerodynamic run. Before gh-788 this was `wings[0]`, which made every coefficient ≈8× wrong on a tail-first OpenVSP import. | 🟢 |
| **Fuselage** | A body. `symmetric` defaults to **False** (opposite of wings) because the main fuselage sits on the symmetry plane; paired sub-fuselages (gear struts, cowlings, wheel fairings) are stored once and mirrored `y → −y` downstream (gh-715). | 🟢 |
| **X-section / xsec / station** | A defining cross-section. For wings these are **stations** along the span; for fuselages they are superellipse sections along x. | 🟢 |
| **Segment** | The span of wing between two consecutive stations. **N stations ⇒ N−1 segments.** All segment-scoped data hangs off the *inboard* station. | 🟢 |
| **Terminal station** | The last station of a wing. Carries **geometry only** — no spar, TED, turbulator, `x_sec_type` or `tip_type`. Enforced in three independent layers (schema validator, `WingModel.from_dict`, service guard). | 🟢 |
| **Airfoil** | A 2-D section, stored as a Selig-format `.dat` file under `components/airfoils/` (1 665 files). The **file stem is the canonical name**, not the Selig header line. | 🟢 |
| **Airfoil family** | One of five frozen labels: `flat_bottom`, `semi_symmetric`, `symmetric`, `cambered`, `reflexed`. Classified from geometry; evaluation order is load-bearing (reflexed → symmetric → flat_bottom → semi_symmetric → cambered). | 🟢 |
| **Spar / "Spare"** | A structural spanwise member inside a wing segment. The code spells it **`Spare`** throughout (`wing_xsec_spares`, `Spare`, `spare_vector`) — a long-standing misspelling of *spar* that is now part of the schema contract. | 🟢 |
| **Spar mode** | `standard` / `normal` / `follow` (+ `*_backward` variants). Only `normal` spars with a fully explicit 3-component origin **and** vector are preserved verbatim across a model→config conversion; everything else is recomputed (gh-1053). | 🟢 |
| **TED — Trailing Edge Device** | A movable trailing-edge surface: aileron, elevator, rudder, flap, elevon, flaperon, ruddervator, stabilator, spoiler, `other`. Leading-edge devices are explicitly out of scope. | 🟢 |
| **Control-surface role** | The *function* of a TED. Drives the control-axis decomposition (gh-772), the trim solver's pitch-control search, and the OP generator's capability gating. | 🟢 |
| **Control axis** | `pitch`, `lift`, `roll`, `yaw`. `pitch`/`lift` are **primary** (symmetric, `SgnDup=+1`); `roll`/`yaw` are **secondary** (antisymmetric, `SgnDup=−1`). | 🟢 |
| **Dual-role surface** | A TED that serves two axes: `elevon` (pitch+roll), `flaperon` (lift+roll), `ruddervator` (pitch+yaw). Emits **two** control variables. | 🟢 |
| **Turbulator** | An optional per-segment boundary-layer trip (gh-934). Modelled as a forced-transition location `x/c` whose effect is a section-drag delta computed with NeuralFoil, **not** XFOIL. The one approved extension to the frozen topology classes. | 🟢 |
| **Servo** | The actuator inside a TED. Either an embedded `wing_xsec_ted_servos` row or an integer index into the component library — the schema type is `Servo \| int` and which is canonical is undocumented. | 🟢 / 🔴 |
| **Component tree** | A hierarchical BoM per aeroplane. Three node types: `group` (structural), `cad_shape` (Creator output or uploaded part), `cots` (catalogue component). Weights roll up post-order. | 🟢 |
| **Weight item** | A *flat* mass inventory entry (`mass_kg`, `x_m/y_m/z_m`, category). A **second, independent** mass producer alongside the component tree. | 🟢 |

### 1.2 Design intent and sizing

| Term | Meaning | Confidence |
|---|---|---|
| **Design assumption** | A named design parameter carrying **two** values — an `estimate_value` (the designer's guess) and a `calculated_value` (what the tools derived) — plus an `active_source` selector. 15 catalogued parameters. | 🟢 |
| **Design choice** | An assumption that can *never* be calculated: `target_static_margin`, `g_limit`, `battery_capacity_wh`, `battery_specific_energy_wh_per_kg`, `propulsion_eta_motor`, `propulsion_eta_esc`, `motor_continuous_power_w`. | 🟢 |
| **Divergence** | `|estimate − calculated| / |calculated| × 100`, banded none <5 % · info <15 % · warning ≤30 % · alert above. The UI's "your guess vs physics" signal. | 🟢 |
| **Mission objective** | One row per aeroplane: the seven performance targets plus field-performance inputs (runway length/type, static thrust, takeoff mode, landing surface and safety factor). | 🟢 |
| **Mission preset** | A seeded library of nine archetypes — `trainer`, `sport`, `sailplane`, `wing_racer`, `acro_3d`, `stol_bush`, `slope_soarer`, `motor_glider`, `flying_wing`. Each carries a 7-axis `target_polygon`, `axis_ranges` and `suggested_estimates`. | 🟢 |
| **Mission KPI axes** | `stall_safety`, `glide`, `climb`, `cruise`, `maneuver`, `wing_loading`, `field_friendliness` — the spider chart the design is scored against. | 🟢 |
| **RC flight profile** | A **global, shared library** entry (not per-aeroplane) describing environment, goals, handling and constraints. Optionally assigned to an aeroplane. Its absence is load-bearing: with no profile, cruise speed is *replaced* by `V_md` and flagged `v_cruise_auto`. | 🟢 |
| **Computation context** | `aeroplanes.assumption_computation_context` — the JSON blob that is the **single source of aerodynamic truth** for the aircraft (gh-924). ~40 keys grouped into speeds, geometry, aero, polars, stability/CG, envelope, provenance. | 🟢 |
| **Operating point (OP)** | A trimmed flight condition: velocity, α, β, body rates, altitude, configuration, control deflections, moment reference. 15 are generated by the default sweep. α and β are stored in **radians** and converted to degrees at the schema boundary. | 🟢 |
| **Operating point set** | A named collection whose members are a **JSON array of OP ids**, not an association table. | 🟢 |
| **Loading scenario** | A named CG loadout (toggles, mass overrides, position overrides, ad-hoc items). The min/max CG across all scenarios is the **Loading Envelope**, which must fit inside the **Stability Envelope**. | 🟢 |
| **Flight envelope** | The V-n diagram (manoeuvre + Pratt-Walker gust) plus six performance KPIs, each with an explicit confidence tier (`trimmed` > `computed` > `estimated` > `limit`). | 🟢 |
| **Matching chart** | The classical Loftin/Scholz T/W-vs-W/S constraint diagram, extended (gh-613) with five RC-additive constraints and a per-profile applicability table. | 🟢 |

### 1.3 Aerodynamics vocabulary as used *here*

| Term | The system's specific meaning | Confidence |
|---|---|---|
| **cd0** | **Parasite** drag coefficient — `CD_total − CL²/(π·AR·e)` — *not* total CD at α = 0. This distinction is the whole of gh-924. | 🟢 |
| **e / Oswald factor** | Span efficiency. Provenance chain `aerobuildup_trefftz` → `fit` → `fallback`; a rejected fit surfaces as a **design warning**, not a silent `0.8`. | 🟢 |
| **(L/D)max** | Published from the self-consistent closed form `½·√(π·AR·e / CD0)` (Scholz eq. 5.39), **not** from `argmax(CL/CD)` over a flattened sweep. | 🟢 |
| **x_np / neutral point** | One value per aircraft, evaluated at the **cruise design point**. α-independent in the linear range, so an off-design evaluation is treated as a bug, not a variant. | 🟢 |
| **Static margin (SM)** | `(x_np − x_cg) / MAC`. Classified per Scholz §4.2: `<0.02` error, `<target` warn, `≤0.20` ok, `≤0.30` warn, else error. | 🟢 |
| **Reynolds number — two distinct concepts** | (a) *2-D per-airfoil*, on an absolute grid 40 k–750 k straight from NeuralFoil, aircraft-independent (gh-821). (b) *aircraft-level*, a speed-band **label** at the main wing MAC (gh-493). Both modules carry a docstring warning not to conflate them. | 🟢 |
| **Suitability lens** | One of three airfoil ranking modes: `re_agnostic`, `mission`, `target_cl_cruise`. Glide points (`target_cl_best_glide`, `target_cl_min_sink`) are **display-only and never auto-rank**. | 🟢 |
| **Confidence tier** | The primary sort key in airfoil ranking — a high-scoring low-confidence airfoil never outranks a trustworthy one. | 🟢 |
| **Strip forces** | Per-spanwise-strip lift/drag distribution, in AVL's `FS` output shape. Since gh-674 the default producer is the **in-process VLM** (~58 ms) reconstructing an AVL-equivalent table; AVL is `?solver=avl`. | 🟢 |
| **Trim / trim score** | Solving for the control deflection (and α, V) that zeroes the moment residual. `trim_score = |Cm| + 0.5·|CY| [+ 0.3·|CL − CL_target|]`; `< 0.35` ⇒ TRIMMED. | 🟢 |
| **Retrim** | The background re-solve of all `DIRTY` operating points after a geometry or mass change. | 🟢 |
| **Provenance** | An explicit label on a derived number saying where it came from: `polar` / `cold_start`, `aerobuildup_trefftz` / `fit` / `fallback`, `weight_items` / `component_tree`, `trimmed` / `computed` / `estimated`. Pervasive design idiom. | 🟢 |

### 1.4 CAD and construction vocabulary

| Term | Meaning | Confidence |
|---|---|---|
| **Creator** | A subclass of `AbstractShapeCreator` — one geometry operation (loft a wing, cut a bolt hole, export a STEP). 29 registered across five categories. Adding new Creators is the sanctioned way to extend `cad_designer/`. | 🟢 |
| **Construction plan** | A serialised `ConstructionRootNode` tree — a build recipe. `plan_type` is `template` (reusable, `aeroplane_id` NULL) or `plan` (a deep copy bound to one aeroplane). No version chain and **no back-link** between the two. | 🟢 |
| **`$TYPE` dialect** | The JSON serialisation contract of the plan tree. `$TYPE` is the class name; the decoder resolves it against exactly what `GeneralJSONEncoderDecoder` imports, so **topology classes never appear in a plan JSON** and renaming a Creator invalidates every stored plan referencing it. | 🟢 |
| **Construction part** | An uploaded STEP/STL file scoped to an aeroplane, with extracted volume/area/bbox and a `locked` flag that blocks deletion. Unrelated to a construction *plan*. | 🟢 |
| **Artefact** | An execution output directory `<ARTIFACTS_BASE_DIR>/<aeroplane>/<plan>/<execution_id>/`. Template runs go to `_template_runs/` and **wipe the previous run**. | 🟢 |
| **Tessellation** | The three-cad-viewer scene payload for a wing, cached per `(aeroplane, component_type, component_name)` with a 16-hex geometry hash and an `is_stale` flag. | 🟢 |
| **Superellipse xsec** | `|y/a|ⁿ + |z/b|ⁿ = 1` with **half-axes** `a` (lateral) and `b` (vertical) and shape exponent `n ∈ [0.5, 8]`. The only *parametric* fuselage description. | 🟢 |
| **Surface STEP vs solid STEP** | `step_path` is the per-geom surface STEP written at OpenVSP-import time; `solid_step_path` is the sewn/healed closed solid. Both are kept on purpose: the surface STEP is the reliable slicing source, the solid is what the construction pipeline cuts against. | 🟢 |
| **Spar plan / spar piece** | The output of the CAD-free `spar_solver`: a buildable layout of straight rod/tube pieces per half-span, with telescoping splits, joint type (`continuous` / `reinforcement+joiner` / `bent-pin`), utilisation and feasibility. | 🟢 |

### 1.5 Versioning and AI vocabulary

| Term | Meaning | Confidence |
|---|---|---|
| **Lineage** | All aeroplane rows sharing a `root_id`. The root points at **itself**. | 🟢 |
| **Node** | A single `aeroplanes` row inside a lineage. Every aeroplane is a node — there is no "unversioned" aircraft since gh-903. | 🟢 |
| **Head** | The mutable node a branch currently points at (`branches.head_id`, `is_immutable = False`). | 🟢 |
| **Snapshot** | An **immutable** node inserted *behind* the head. Counter-intuitive but deliberate: the head keeps its id, UUID and every inbound reference, so the UI never has to re-point. | 🟢 |
| **Branch** | `(root_id, head_id, name, is_main, created_by)`. Exactly one `is_main` per lineage, enforced by a **partial unique index**. | 🟢 |
| **Adopt** | Promote a branch to `is_main` (demoting the old main first, in that order, so the partial index never sees two). | 🟢 |
| **Restore** | Create a new branch from an **immutable** node. Restoring from a live head is just `create_branch`. | 🟢 |
| **Provenance (versioning)** | `created_by` on both nodes and branches. Four writers, three vocabularies: `"human"`, `"ai"` (documented) and `"copilot"` (what the AI actually writes). | 🟢 / 🔴 |
| **Proposal branch** | A single open `copilot-proposal` branch per aeroplane, `created_by='copilot'`, `is_main=False`. The copilot's entire write surface. | 🟢 |
| **Edit op** | One member of the copilot's 7-member discriminated union DSL (`SetAssumption`, `SetXsec`, `SetSegment`, `AddXsec`, `RemoveXsec`, `SetWingParam`, `ReplaceWingConfig`). Millimetres and degrees. | 🟢 |
| **Read-retargeting** | While a proposal is open, the copilot's *read* tools resolve to the proposal head so the model sees its own edits (gh-938). Write tools and `get_version_tree` always target the live node. | 🟢 |
| **MCP tool** | One of 76 FastMCP tools that re-enter a v2 endpoint function in-process, for **external** AI agents. Distinct from the 6-tool in-app copilot registry. | 🟢 |

---

## 2. Business rules and invariants

Numbered `BR-n` so other documents can reference them. Each rule states where
it is enforced, because *where* is the interesting part in this codebase — most
domain rules are enforced in more than one layer, and several are enforced only
in prose.

### 2.1 Units and coordinates

**BR-1 — The unit duality.** 🟢
The database and AeroSandbox speak **metres**; `WingConfig` and every
`cad_designer` topology class speaks **millimetres**. Conversion happens only in
`app/converters/` and in the `_convert_spare_to_*` helpers of `wing_service`
(`scale = 0.001` mm→m, `scale = 1000.0` m→mm).
*Enforced by:* convention plus a small set of named conversion functions. There
is no type-level unit. See [ADR 0001](adrs/0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md).

**BR-2 — The `wing_xsec_spares` exception.** 🟢
All six dimensional spar columns (`width`, `height`, `length`, `start`,
`spare_origin`) are stored in **millimetres inside the metre database**
(gh-402, commit `3785057c`). `spare_vector` is a **dimensionless unit direction
vector**. The API contract is unchanged — every spar endpoint still delivers
metres.
*Consequence (🔴):* `WingUnitsSchema` still advertises `detail_length: "m"`, so
a consumer reading the self-describing units block alone is misled about
storage.

**BR-3 — Wing-local frame.** 🟢
`cad_designer` geometry is expressed in a wing-local frame: origin at the root
leading edge, z up.

### 2.2 Wing topology

**BR-4 — N stations describe N−1 segments.** 🟢
Segment-scoped data (spars, TED, turbulator, `x_sec_type`, `tip_type`,
`number_interpolation_points`) hangs off the **inboard** station in the 1:1
`wing_xsec_details` side table.

**BR-5 — The terminal station carries geometry only.** 🟢
Enforced in **three** layers: the Pydantic validator
`validate_last_xsec_has_no_segment_details`, the model factory
`WingModel.from_dict` (which blanks the six fields), and the service guard
`_assert_non_terminal_xsec_or_raise`. Triple enforcement is a deliberate
defence-in-depth choice for the rule that most often breaks round-trips.

**BR-6 — A segment's root chord is not independently settable.** 🟢
Chord continuity means a segment's root chord *is* the previous segment's tip
chord. Tapering is expressed by setting `chord_tip_mm`. The copilot's
`get_wing_geometry` carries this as a free-text `note` because the schema cannot
express it.

**BR-7 — Terminal dihedral must be persisted explicitly.** 🟢 (gh-951)
The last rib's local-x rotation moves no outboard station, so it leaves no trace
in `xyz_le` and cannot be reconstructed from positions. It is stored in
`wing_xsecs.dihedral`; `NULL` on legacy rows means "derive from geometry".

**BR-8 — A wing knows how it was authored.** 🟢
`wings.design_model` is `'wc'` (created from a `WingConfiguration`, CAD-capable)
or `'asb'` (created from bare AeroSandbox geometry); `NULL` for legacy rows.

### 2.3 Control surfaces

**BR-9 — A role decomposes into control axes.** 🟢 (gh-772)
`elevon → (pitch, roll)`, `flaperon → (lift, roll)`,
`ruddervator → (pitch, yaw)`. A dual-role surface emits **two** control
variables on the same section: primary symmetric (`SgnDup=+1`, gain
`mix_gain_primary`, baseline = the surface's deflection) and secondary
antisymmetric (`SgnDup=−1`, gain `mix_gain_secondary`, baseline **0.0**).

**BR-10 — `SgnDup` is a sign flag, never a magnitude.** 🟢
`differential_ratio` is a **reporting-only kinematic** applied *after* trim for
left/right display. It never alters the aero or trim solution.

**BR-11 — Control-variable names must be globally unique.** 🟢
AVL silently collapses identically-named `CONTROL` variables into one DOF, which
would couple unrelated surfaces. `assert_unique_control_names` raises on any
cross-surface collision; duplication *within* one surface (panel replication) is
legitimate and deduped separately.

**BR-12 — Mixing fields are role-gated.** 🟢
`differential_ratio ≠ 1.0` is legal only for
`{aileron, elevon, flaperon, ruddervator}`; `mix_gain_secondary ≠ 1.0` only for
`{elevon, flaperon, ruddervator}`. Compared with `math.isclose(rel_tol=1e-9,
abs_tol=1e-9)`; a `None` role (partial patch) skips the check.

**BR-13 — The canonical control name is the gh-772 mixing name.** 🟢 / 🔴
`[{role}]{axis}_{wing_key}_{xsec_index}`, e.g. `[ruddervator]pitch_htail_1`.
**Open bug #955:** `trim_enrichment_service`, `retrim_service` and
`stability_service` still key on the raw DB TED name, so on a dual-role aircraft
the deflection limits fall back to a hard-coded ±25° and a phantom 0° surface is
reported.

### 2.4 Aerodynamic truth

**BR-14 — One aero truth per aircraft.** 🟢 (gh-924, commit `8847b13d`)
`cd0` (parasite), `e_oswald`, `(L/D)max` and `x_np` are produced **once** by
`recompute_assumptions` at the cruise point and cached on
`assumption_computation_context`. Every downstream consumer — speed polar, V-n
envelope, matching chart, mission KPIs, endurance, spar sizing, powertrain,
copilot — **reads that context**. None re-derives its own.
*Known violation (🔴):* `stability_service._auto_populate_cd0` writes the
**total** CD into the `cd0` assumption on a different trigger.
See [ADR 0004](adrs/0004-one-aero-truth-per-aircraft.md).

**BR-15 — AeroSandbox is the default solver; AVL is the exception.** 🟢
All defaults (α sweep, simple sweep, strip forces, retrim, assumption recompute,
OP generation, streamlines) run AeroBuildup or the in-process VLM. AVL is
reached only on explicit request (`analysis_tool=avl`, `?solver=avl`) or via the
dedicated AVL trim endpoint. AVL's genuine remaining advantages are native
indirect constraints, per-section CDCL viscous polars, and the roll/yaw axis of
mixed surfaces. See [ADR 0003](adrs/0003-aerosandbox-default-avl-exception.md).

**BR-16 — Resolution goes up; thresholds never move.** 🟢 (gh-672)
The parabolic polar fit has six rejection gates. Only two of them
(`insufficient_points`, `non_monotonic_polar`) are refinable, and refinement
halves the α step and widens the margin — it never loosens a threshold.

**BR-17 — An unphysical result is a design warning, not a fallback.** 🟢 (gh-956)
A `k ≤ 0` or an out-of-range Oswald `e` is surfaced to the user as a *design*
warning. Only rejections categorised `design` are shown; `sweep`, `data` and
`consistency` categories stay internal. `NonFiniteSafeJSONResponse` embodies the
same philosophy for NaN/Inf: `null` is "an honest no value, never a fabricated
fallback number that would hide the underlying design problem".
See [ADR 0012](adrs/0012-design-warnings-instead-of-silent-fallbacks.md).

**BR-18 — Turbulator deltas never poison the fit gate.** 🟢 (gh-935)
When a turbulator is enabled, the stored `cd0` gains `ΔCD0`, but `raw_cd0` (the
natural-transition baseline) is preserved and passed as `cd0_stability` to every
fit — otherwise a meaningful ΔCD0 would spuriously trip the 20 % consistency
gate.

**BR-19 — Trim must reflect one coherent state.** 🟢 (gh-577)
A Trefftz/streamline/strip-force run bound to an `operating_point_id` loads the
row **constrained to the aircraft** (no cross-aeroplane injection), requires
status `TRIMMED` unless explicitly waived, and picks deflections as: a non-empty
manual `control_deflections` override wins; otherwise the solver's `controls`.
An **empty** override dict is a no-op so it cannot erase a fresh trim.

**BR-20 — Unknown deflection names are a 422, not a silent drop.** 🟢
`Airplane.with_control_deflections` silently ignores unknown keys, which would
let a renamed surface run clean while the UI labelled the plot "trimmed".
`validate_deflections_against_airplane` raises instead.

**BR-21 — Capability gating skips, never fails.** 🟢
An OP target whose control requirement is unmet is *skipped*: turns need roll or
yaw, Dutch-roll needs yaw, flapped stall needs a flap. `PITCH_ROLES`,
`ROLL_ROLES`, `YAW_ROLES`, `FLAP_ROLES` are the role sets.

**BR-22 — Flap targets clip to the real hinge limit.** 🟢 (gh-527/gh-536)
Clipped to the **most restrictive** flap-role TED so the smallest surface never
over-deflects. With no flap TED present, no limit is manufactured. AVL has no
internal hinge clamp and NeuralFoil silently extrapolates past its training
range, so an unclipped target would produce over-attached flow with no warning.

**BR-23 — Stall speeds come from physics, not from 0.95/0.90.** 🟢
`v_s1` / `v_s_to` / `v_s0` are read from the computation context
(`provenance="polar"`). With only a legacy `v_stall_mps` the clean value is used
for all three configurations — the historical multipliers are *deliberately not*
applied. With no context at all, `provenance="cold_start"` and every generated
OP is stamped with a `STALE_NO_POLAR` warning.

### 2.5 Mass, CG and assumptions

**BR-24 — Every parameter has an estimate and a calculation.** 🟢
`effective_value = calculated_value if active_source == "CALCULATED" and it
exists else estimate_value`.

**BR-25 — Auto-switch happens once.** 🟢
`update_calculated_value(auto_switch_source=True)` flips `active_source` to
`CALCULATED` **only** on the first calculated value, only from `ESTIMATE`, and
never for a design choice. After that the user's manual choice sticks.

**BR-26 — Design choices can never be calculated.** 🟢
The seven `DESIGN_CHOICE_PARAMS` never receive a `calculated_value` and cannot
be switched to `CALCULATED`.

**BR-27 — Events fire only when the *effective* value changes.** 🟢
`update_assumption` publishes `AssumptionChanged` only when
`active_source == "ESTIMATE"` — editing an estimate while the calculated value
is active changes nothing effective, so the retrim chain must not fire.

**BR-28 — CG is a top-down design target, not a bottom-up sum.** 🟢 (gh-465)
`cg_x` is *CG_aero* — the CG that stability demands, `x_np − SM·MAC` — written
by `assumption_compute_service`. The aggregated CG from mass items (`CG_agg`) is
**never** written back into `cg_x`; it is exposed for comparison only, with a
1 cm tolerance verdict. See [ADR 0011](adrs/0011-cg-is-a-top-down-design-target.md).

**BR-29 — Mass starts as an estimate and becomes bottom-up.** 🟢
A new aircraft seeds `mass = 1.5 kg` (estimate). Both mass producers write only
the CALCULATED side. An empty tree yields `None`, not `0.0`, so the caller
*clears* the calculated value rather than asserting a 0 kg aircraft.

**BR-30 — Mass sync never blocks the CRUD that triggered it.** 🟢
Both `_try_sync_assumptions` and `_sync_aircraft_mass` swallow their exceptions
by design. *Trade-off:* a persistently failing sync is invisible except in the
log.
*Consequence (🔴):* two producers (`weight_items`, `component_tree`) write the
same `calculated_value` **last-write-wins**; `calculated_source` records which
one won but nothing warns that the other estimate was discarded.

**BR-31 — Component-tree weight resolution is a strict precedence chain.** 🟢
`weight_override_g` (source `override`) → COTS `mass_g × quantity` (`cots`) →
CAD shape volume/area × material density (`calculated`) → `(None, "none")`.
Surface prints use `area_mm2 × print_resolution_mm` (default **0.4 mm**);
volume prints use `volume_mm3`.

**BR-32 — Roll-up status is three-valued.** 🟢
A leaf is `valid` when its own source ≠ `none`. A non-leaf is `valid` when all
children are valid, `invalid` when all are invalid and it has no own weight, and
`partial` otherwise.

**BR-33 — Explicit values win over snapshots.** 🟢
When a tree node is created with a `construction_part_id`, geometry fields are
copied from the part **only for fields the caller did not explicitly set**,
detected via `model_dump(exclude_unset=True)`.

**BR-34 — Wings and fuselages auto-create component-tree groups.** 🟢 (gh#108)
Creating a wing or fuselage creates a matching group; deleting removes nodes by
the `synced_from` prefix (`wing:<name>` / `fuselage:<name>`).

### 2.6 Versioning

**BR-35 — Every aeroplane is a versioning node.** 🟢
`create_aeroplane` performs a three-step flush dance to satisfy the circular
`aeroplanes ↔ branches` FK pair: insert → flush → `root_id = self.id` → create
`BranchModel(name="main", is_main=True, created_by="human")` → flush →
back-fill `branch_id`. The gh-903 migration backfilled the same shape for every
pre-existing row.

**BR-36 — Exactly one `is_main` branch per lineage.** 🟢
Enforced at DB level by a **partial unique index**
(`uq_branches_one_main_per_root`), declared identically in the model and the
migration so `create_all` (tests) and a migrated production DB agree.
`adopt_branch` must **demote first and flush** before promoting.

**BR-37 — An immutable node can never be mutated.** 🟢
`_guard_immutable` → 422. The mirror rule: `restore` *requires*
`is_immutable=True`.

**BR-38 — A snapshot is inserted behind the head, not in front of it.** 🟢
```
before:  [old_pred] ← [head (mutable, id=H)]
after:   [old_pred] ← [snapshot (immutable, id=S)] ← [head (id=H, unchanged)]
```
The head keeps its identity, so no inbound reference has to be re-pointed.

**BR-39 — The clone registry must be exhaustive.** 🟢
Every table with a transitive FK to `aeroplanes` appears in exactly one of
`CLONED_TABLES` (17) or `EXCLUDED_TABLES` (18), asserted by
`test_aeroplane_clone_coverage.py`. **Blind spot:** the test introspects
SQLAlchemy `ForeignKey` objects, so tables whose aeroplane reference is a plain
`String` (`component_tree`, `construction_plans`, `construction_parts`) must be
maintained by hand.

**BR-40 — Cloning re-keys internal references and keeps shared ones.** 🟢
`loading_scenarios.component_overrides` are remapped through a
`weight_id_map`; values *not* in the map pass through unchanged because they are
COTS component UUIDs (shared references). `flight_profile_id`,
`servo.component_id` and every library reference are kept; STEP paths are nulled.

**BR-41 — Never mutate destructively without a recovery point.** 🟢 (gh-1058)
A destructive spar commit (segment split or spare REPLACE) takes an automatic
immutable snapshot labelled `"Before spar insert"` *before* mutating anything,
and **aborts the whole commit if the snapshot fails**. The snapshot id is
returned so the UI can offer one-click revert.

**BR-42 — Branch names are unique per lineage — at application level only.** 🟢
`rename_branch` checks; `create_branch` does not. There is no DB constraint.

### 2.7 AI copilot

**BR-43 — The copilot proposes; only a human adopts.** 🟢 (gh-902)
Write tools operate exclusively on a `copilot-proposal` branch. There is
deliberately **no adopt tool** — adoption happens in the Versions panel.
See [ADR 0007](adrs/0007-copilot-proposes-human-adopts.md).

**BR-44 — At most one open proposal per aeroplane.** 🟢
`get_or_open_proposal` reuses the newest branch matching
`root_id=? AND is_main=False AND created_by='copilot' AND name LIKE
'copilot-proposal%'`. *(🔴 nothing prevents duplicates; if they existed, older
ones would be orphaned.)*

**BR-45 — Numbers are computed in Python, never by the model.** 🟢
`_drag_breakdown` computes the induced/parasite split server-side because "the
LLM is unreliable at this arithmetic (it has produced both physically-impossible
splits and 10× errors)". When the split is physically impossible it returns a
`note`-carrying dict with the raw inputs rather than a wrong split.

**BR-46 — A tool error is a return value, not an exception.** 🟢
Tool contract: `fn(db, aeroplane_id, **kwargs) -> dict`, JSON-serialisable,
errors returned as `{"error": …}`. `apply_edits` collects `applied` and
`rejected: [{op, error}]` so the model self-corrects instead of aborting.

**BR-47 — The advisory tool surface is curated, not the full API.** 🟢
6 tools, not the 76-tool MCP surface: "only the tools that are safe, fast, and
meaningful for an advisory interaction".

**BR-48 — Secrets never reach the browser.** 🟢
`_sanitize_error` redacts any literal occurrence of the configured API key, then
replaces auth/connectivity errors with a *category* message. The endpoint's
catch-all emits the flat string `"Internal server error"`.

**BR-49 — History replay must preserve tool-call pairing.** 🟢 (gh-922)
A turn is persisted as one assistant row carrying both `tool_calls` and
`tool_results`; `_history_to_openai` *reconstructs* the interleaved `tool`
messages, emitting `{"error": "tool result unavailable"}` as a placeholder
rather than dropping the message — the hub 400s on an orphaned `tool_use`.

### 2.8 Airfoils

**BR-50 — Selig format only.** 🟢
`_parse_dat_file` skips the first line as a header and silently skips
unparseable lines. Fewer than 3 valid coordinates raises. *(🔴 no Lednicer
detection; such a file would be mis-parsed.)*

**BR-51 — The airfoil directory is absolute, not CWD-relative.** 🟢
`AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`, with an in-code comment
recording the bug that motivated it: procedurally generated airfoils written by
the OpenVSP importer landed outside a CWD-relative read directory and appeared
"missing".

**BR-52 — Imports may only read inside `components/`.** 🟢
`import_directory` resolves the requested directory and raises `ValidationError`
if it is not inside `<project_root>/components`.

**BR-53 — Interpolate linearly in ln(Re).** 🟢
Matching NeuralFoil's training encoding. Out-of-range queries clamp to the
nearest endpoint and the response reports `re_clamped = True`.

**BR-54 — Two NeuralFoil model sizes coexist on purpose.** 🟢
The backfill uses `xxxlarge`, the interactive endpoint `large`. The docstring
says "do NOT collapse".

**BR-55 — Confidence is windowed, not whole-sweep.** 🟢
`min_analysis_confidence` is the minimum over the *attached-flow* window —
deep-stall confidence is irrelevant to operating-point performance.

**BR-56 — Scores are relative to the fleet, not absolute.** 🟢
`compute_re_cd0_reference` uses the **20th percentile** of finite `cd0` across
the whole library at the query Re — a robust "best achievable at this Re"
reference rather than the absolute minimum.

**BR-57 — Section CL is treated as whole-wing CL, and the contract says so.** 🟢
The scoring contract *always* sets `ignores_tip_re_clmax_collapse = True` and
exposes `tip_re_flag` (fires below Re 80 000 or on a >50 000 root→tip drop) plus
`cl_max_margin` (negative = stall risk).

**BR-58 — Buildability is not a selection constraint.** 🟡
The user 3-D prints wings, so airfoil thickness is not filtered for
manufacturability — only enough room for a carbon spar matters. This is a
product decision visible in what the scoring lenses *do not* penalise.

### 2.9 Components and COTS

**BR-59 — One table, a data-driven per-type schema.** 🟢
`components` is a single table for every hardware type, discriminated by
`component_type`, with type-specific fields in a JSON `specs` blob. The contract
is itself data: `component_types.schema` (mapped `schema_def`) holds a list of
`PropertyDefinition`s validated on every write.
See [ADR 0013](adrs/0013-one-components-table-with-a-data-driven-type-schema.md).

**BR-60 — `validate_specs` rejects bad values but accepts unknown keys.** 🟢
Missing required, wrong type, out-of-range, not-in-options all raise. **Unknown
keys are never rejected** — which is why `specs["variant"]` can exist on
propellers without being in the type schema. The schema is a floor, not a
complete contract.

**BR-61 — Seeded types and referenced types cannot be deleted.** 🟢
`deletable=False` → 409; any type still referenced by ≥1 component → 409 with
the reference count. `update_type` may change `label`/`description`/`schema` but
never `name` or `deletable`.

**BR-62 — COTS ingestion is network-free and snapshot-driven.** 🟢
The durable source is a **committed** snapshot (`data/cots/apc_props.json.gz`,
~8 MB, 454 propellers), never the raw vendor files (gitignored) and never a live
fetch. Reimport CLIs read the snapshot.
See [ADR 0014](adrs/0014-cots-ingestion-from-committed-snapshots.md).

**BR-63 — User-entered mass always wins.** 🟢
`prop_component_seed` populates `mass_g` from the polar `weight_g` on create,
backfills a **NULL** `mass_g` when the polar later gains a weight, and **never
clobbers a non-null** `mass_g`.

**BR-64 — Implausible parsed data is rejected, not written.** 🟢
`MIN_PLAUSIBLE_WEIGHT_G = 1.0` — a parsed propeller weight below 1 g is treated
as a kg→g conversion error and counted in `unit_warnings`. Unmatched records are
logged, never dropped silently.

**BR-65 — Battery voltage nominal is the *loaded* 3.7 V per cell.** 🟢
Not the 4.2 V peak, which would inflate power by 13 %. Motor KV is always the
**gear-aware** `output_kv = kv_rpm_per_volt / gear_ratio`, never the raw KV
(except in the sizing modal, which deliberately shows raw KV because the
designer is picking a motor, not an output shaft).

**BR-66 — Propeller efficiency is J-dependent, never a flat constant.** 🟢
`η_prop = clip(Pe, 0, 1)` interpolated at the advance ratio; `Pe` is recomputed
as `Ct·J/Cp` rather than read from the stored column. `J` is **clamped** to the
dataset range with an explicit `extrapolation_warning` — the curve never runs
off the data silently.

### 2.10 CAD and construction

**BR-67 — CAD runs in a spawned worker process.** 🟢
OCCT is not thread-safe; the same `.intersect().clean()` that takes ~100 ms on
the main thread hangs indefinitely in a worker *thread*. `spawn` is chosen for
platform consistency (`fork` is unsafe with OCCT already loaded). Everything
crossing the boundary must be picklable, so an `AsbWingSchema` pickle is shipped
and the `WingConfiguration` is rebuilt inside the worker.
See [ADR 0005](adrs/0005-cad-in-a-spawned-process-pool.md).
*Known contradiction (🔴):* construction-plan execution runs the same OCCT stack
**in the request process**.

**BR-68 — Every artefact path is traversal-guarded.** 🟢
`_ensure_within_base` resolves then `relative_to(base)`; `get_file_path`
additionally rejects symlinks; the fuselage slicer reduces the upload to its
basename and checks `is_relative_to` before writing (Sonar S2083).

**BR-69 — A construction plan and its template diverge immediately.** 🟢
`instantiate_template` deep-copies the tree into a new row; there is **no
version chain and no back-link**. After instantiation the two evolve
independently.

**BR-70 — Plan validation is deliberately thin.** 🟢
`_validate_tree_json` requires only `$TYPE` and `creator_id` at the root;
everything else fails at decode time. A legacy root whose `$TYPE` is
`ConstructionStepNode` is silently rewritten to `ConstructionRootNode` **on
every read**.

**BR-71 — Renaming a Creator invalidates every stored plan referencing it.** 🟢
The `$TYPE` decoder resolves against `getattr(module, name)`. Nine removed
Creator classes are still referenced by three shipped plan JSONs, which are
therefore undecodable today. Latent, not live — nothing under `app/` reads that
directory.

**BR-72 — Upload limits.** 🟢
Construction parts: `{.step, .stp, .stl}`, 50 MB, download as `step` or `stl`
only. A `locked` part cannot be deleted (409). STL yields no geometry metadata —
it is a triangle soup (documented MVP limitation).

### 2.11 OpenVSP import

**BR-73 — Import scope is RC-scaling inspiration.** 🟢
Geometry and mass positions only. No propulsion, no inertia, no CS-group gains,
no VSPAERO validation, no leading-edge devices.
See [ADR 0018](adrs/0018-openvsp-import-scope-is-rc-scaling-inspiration.md).

**BR-74 — Nothing aborts an import except three errors.** 🟢
Only `ImportError` (openvsp missing), `FileNotFoundError` and
`ScaleValidationError` abort. Handler failures, post-pass failures,
per-record persistence failures, undetectable units, rejected slicer output and
failed sewing all degrade into structured warnings that reach the frontend
banner.

**BR-75 — Scaling never touches angles or masses.** 🟢
`_scale_aeroplane_lengths` scales lengths only. Twist (angular) and masses are
deliberately left alone per the RC-scope decision, and a scaling run **always**
appends an `info` warning saying so.

**BR-76 — Source units are measured, not trusted.** 🟢 (gh-808)
OpenVSP 3.50 stores no in-file unit, so a feet model would import 3.28× too
large. The importer exports a fuselage to STEP (which VSP writes metric),
measures the bounding box, and snaps the implied ratio to a known unit within
2 %. No match ⇒ import unchanged.

**BR-77 — Prefer the surface STEP over the sewn solid for slicing.** 🟢 (gh-812)
The solid carries internal seam faces at sharp fillets that fragment a section
cut. Open bug #814: the CAD path still consumes the solid.

### 2.12 Platform and persistence

**BR-78 — `get_db()` owns the transaction boundary.** 🟢
Commit on success, rollback on exception, close in `finally`. Services call
`db.flush()` / `db.add()` but **never** `db.commit()` / `db.begin()`. Four paths
legitimately own their own session (two lifespan seeders, the recompute wrapper,
the job-tracker backfill).
See [ADR 0009](adrs/0009-get-db-owns-the-transaction-boundary.md).
*Known violation (🔴):* `mcp_server._call_endpoint` opens a bare
`SessionLocal()` and never commits, so **every MCP write is rolled back**.

**BR-79 — `autoflush=False`.** 🟢
Services must flush explicitly before a query can see their pending writes —
which is why `db.flush()` appears throughout the version and copilot services.

**BR-80 — SQLite runs in WAL with a 30 s busy timeout.** 🟢
Because assumption recompute holds a write transaction open for several seconds
while AeroBuildup runs; without WAL a parallel write fails with "database is
locked".

**BR-81 — Heavy dependencies are optional and probed once.** 🟢
`cad_available()` / `aerosandbox_available()` are `lru_cache(maxsize=1)` — "a
broken install detected once stays broken for the life of the process". Routers
are conditionally mounted; registered endpoints that need a capability use
`Depends(require_*)` and return a clean **503**.
See [ADR 0017](adrs/0017-optional-heavy-dependencies-probed-at-import.md).

**BR-82 — Marking dirty and publishing are separate responsibilities.** 🟢 / 🟡
`mark_ops_dirty` is called by the **publishers** (seven call sites) immediately
before `event_bus.publish(...)`; the event *handlers* only schedule jobs — yet
their log lines read "OPs marked DIRTY". A new geometry-mutating path that
publishes but forgets to mark leaves stale operating points with no warning.

**BR-83 — Recompute triggers exclude their own outputs.** 🟢
`_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}` deliberately
excludes `cg_x`, `cd0` and `cl_max`, which the recompute itself writes —
including them would create a `recompute → AssumptionChanged(cg_x) → recompute`
loop.

**BR-84 — A broken subscriber can never break the publishing request.** 🟢
`EventBus.publish` wraps every handler in `try/except` and only logs.

---

## 3. Rules that exist only in prose

Several domain rules are enforced **nowhere in code** — they live in the
copilot's ~270-line system prompt, in `CLAUDE.md`, or in module docstrings. They
are genuine business rules of this system and an architect should treat them as
such, but they carry no runtime guarantee. 🟡

| Rule | Where it lives | Enforcement |
|---|---|---|
| "Propose, never mutate the live design" | copilot `SYSTEM_PROMPT` | partly structural (no adopt tool) |
| "Never mix data sources" — snapshot `cd0` must not be combined with a polar `CD` | `SYSTEM_PROMPT` | none |
| "Lower mass ⇒ all characteristic speeds drop; a speed that rises is an artifact" | `SYSTEM_PROMPT` | none |
| "Gloss MAC / AR / Re / Oswald e / SM / NP on first use; translate L/D into a glide ratio" | `SYSTEM_PROMPT` | none |
| Static-margin bands per mission (RC trainer 15–25 %, sport 8–15 %, aerobatic 0–8 %, UAV 5–15 %) | `SYSTEM_PROMPT`, labelled *"until RAG is available"* | none |
| Proactive design warnings: winglet below ~2 m span, taper < ~0.4, `v_min_sink ≈ v_stall`, cruise < 1.2 × stall | `SYSTEM_PROMPT` | none |
| Domain-expert authority hierarchy (Scholz > Anderson > tool skills > RC hobbyist) | root `CLAUDE.md` | none (agent-facing) |
| "New Creators only" in `cad_designer/` | `cad_designer/CLAUDE.md` | Sonar/ruff exclusion, no code guard |
| "Frontend is English-only" | `CLAUDE.md`, memory | violated: German strings in `app/main.py` handlers, polar-rejection hints, and seeded component-type labels 🔴 |

---

## 4. Domain-level gaps

| # | Gap | Impact |
|---|---|---|
| G-1 | `created_by` has **no enum** and four writers disagree (`human` / `ai` / `copilot`). Any UI filter on `'ai'` misses every copilot branch. | provenance queries are unreliable |
| G-2 | `provenance_message_id` is **write-only** — nothing resolves a snapshot back to the conversation turn that produced it. | the AI audit trail is designed but inert |
| G-3 | **Two mass producers** silently overwrite one another; `weight_items` carries no `component_id`, so the same battery can be double-counted. | mass can be wrong with no warning |
| G-4 | Control-surface naming divergence (**open bug #955**) breaks reserve/authority reporting on every dual-role aircraft. | V-tails, elevons, flaperons report wrong margins |
| G-5 | `min_static_margin` / `max_static_margin` are **read but never seeded**, so the 5 %/25 % CG-range defaults are effectively hard-coded. | the "configurable" bounds are not |
| G-6 | The `design-versions` REST surface is dead but still mounted; every route raises `NotFoundError`, so callers get a plausible 404 rather than a 410/501. | silent dead API |
| G-7 | MCP **writes are silently discarded** (no commit). ~40 of the 76 tools are mutations. | the external-agent surface is read-only in fact but not in contract |
| G-8 | `openvsp_ss_control.register()` and `openvsp_validation.validate_geometry` are **never called in production** — control surfaces are not imported and the gh-647 sanity check is inert. | two shipped features do not run |
| G-9 | No **storage-growth control** on versioning: every snapshot is a full row-copy of the whole design subgraph, snapshots are taken automatically on destructive spar commits, and there is no retention, prune or size accounting. | unbounded DB growth |
| G-10 | `AirplaneConfiguration._main_wing_index = 0` is a dormant copy of the gh-788 reference-area bug on an ASB path the app does not currently use. | a future caller inherits an 8× error |
| G-11 | `mission_presets.id` is a free-text `String` PK with **no FK** from `mission_objectives.mission_type`; an unknown `mission_type` is a silent no-op. | typos silently disable preset estimates |
| G-12 | Two settings classes, **three version strings** (`1.0.0`, `0.1.0`, `2.0.0`), and `/health` reports the one nobody else uses. | no single answer to "what version is this?" |

---

*See `state-machines.md` for the lifecycles these rules govern,
`permissions.md` for who may invoke them, and `adrs/` for why they exist.*
