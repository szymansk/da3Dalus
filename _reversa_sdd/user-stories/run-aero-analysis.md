# Run an Aerodynamic Analysis

> **Personas:** RC/UAV designer · Hobbyist · AI-copilot user · MCP-agent client
> **Modules:** `aero-analysis` (+ `avl-integration`, `mission-and-sizing` neighbours)
> **Primary surface:** `app/api/v2/endpoints/aeroanalysis.py`,
> `app/api/v2/endpoints/operating_points.py`,
> `app/api/v2/endpoints/aeroplane/speed_polar.py`

## Context

A designer (or an agent acting on their behalf) wants a numeric answer at a
flight condition: will the aircraft trim, is it stable, how hard does the
spar work, how far does the drag polar carry it. This flow covers the whole
operating-point lifecycle — generating the aircraft's standard 15-point
envelope, trimming a single custom point through three different solvers,
running one-off analyses, sweeping angle of attack, reading cached stability
and speed-polar results, and watching a stale trim heal itself after the
underlying geometry changes. Every route here is mounted at the application
root (no `/api/v2` prefix) and, on the `aeroanalysis.py` router, serialises
`NaN`/`Inf` as `null` rather than as invalid JSON (ADR 0012).

## US-AERO-01 — Generate the default operating-point set for a new design

**As an** RC/UAV designer, **I want** the system to generate a standard
15-point operating envelope from my flight profile, **so that** I get a
usable trim baseline (cruise, climb, turns, stall corners) without hand-
building every flight condition.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default` | Generate and persist the 15-target default set |

**Acceptance criteria**

- **AC-1 — Full envelope from an assigned profile**
  - **Given** an aircraft with a flight profile assigned and full pitch/roll/yaw/flap control capability
  - **When** `POST .../operating-pointsets/generate-default` is called with an empty body
  - **Then** the response is 200 `GeneratedOperatingPointSetRead` named `default_operating_point_set`, with exactly 15 `operating_points` including `turn_20`/`turn_40`/`turn_60` (load factors `1.0642`/`1.3054`/`2.0`) and `dutch_role_start` (β = 2°, pre-stamped with a `NO_CONTROL_TRIM_MVP` warning)
  - **And** every persisted row has `xyz_ref = [design_cg_x, 0, 0]` and stores `alpha`/`beta` in **radians** (the schema reports degrees only on read)
- **AC-2 — Capability gating skips silently, it does not fail**
  - **Given** an aircraft with neither a rudder nor an aileron
  - **When** the same endpoint is called
  - **Then** the response is still 200, but the three turn targets and `dutch_role_start` are simply absent — no `targets`/`skip` reasoning is surfaced on this non-streaming path, the count is just 11 (BR-21)
- **AC-3 — `replace_existing` resets the whole aircraft, not just this set**
  - **Given** an aeroplane with one manually created operating point plus an existing generated set
  - **When** `POST .../generate-default` is called with `{"replace_existing": true}`
  - **Then** every `operating_pointsets` row **and** every `operating_points` row belonging to the aircraft is deleted first — the manually created point is gone too (BR-MS41, aircraft-wide not set-scoped)

**Confidence:** 🟢 CONFIRMED

## US-AERO-02 — Watch the operating-point set build live over SSE

**As an** AI-copilot user, **I want** to see each trimmed flight condition
appear as soon as it solves, **so that** the workbench shows progress
instead of blocking on a 15-point batch solve.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default/stream` | Stream the same generation over Server-Sent Events |

**Acceptance criteria**

- **AC-1 — Incremental commit, not batch-then-flush**
  - **Given** an aircraft ready to generate
  - **When** `POST .../generate-default/stream` is called
  - **Then** the response is `text/event-stream` (`Cache-Control: no-cache`, `X-Accel-Buffering: no`) that emits `targets` (after the empty point-set row is committed) → one `op` event per solved point, **committed before** its event, in `as_completed` order (not target order) → `done` with `{opset_id, count}`
  - **And** if the connection drops after three `op` events, exactly three operating points are persisted and the point set references exactly those three
- **AC-2 — A `skip` event and a silent gap look identical to the client**
  - **Given** an aircraft with no rudder (so `dutch_role_start` is capability-gated) **and** one other target whose worker solve raises an exception
  - **When** the stream runs
  - **Then** the capability-gated target appears in neither `targets` nor `skip` — it is filtered out before `targets` is emitted and leaves no trace — while the failed target produces a `skip` event carrying only `{"name": "<target>"}`
  - **And** a client cannot distinguish "your aircraft has no rudder" from "this target failed to solve" from the stream alone (🔴 gh-865/BR-MS39, open)

**Confidence:** 🟢 CONFIRMED

## US-AERO-03 — Trim a control surface to a target coefficient

**As an** RC/UAV designer, **I want** to trim my aircraft — either a custom
flight point, a specific coefficient with AeroBuildup, or an AVL indirect-
constraint case — **so that** I can check trim authority for a condition
that is not one of the 15 standard targets.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/operating-points/trim` | `TrimOperatingPointRequest{name, config, velocity, altitude, beta_target_deg, n_target, profile_id_override}` | `TrimmedOperatingPointRead{source_flight_profile_id, point}` |
| POST | `/aeroplanes/{aeroplane_id}/operating-points/aerobuildup-trim` | `AeroBuildupTrimRequest{operating_point, trim_variable, target_coefficient, target_value, deflection_bounds}` | `AeroBuildupTrimResult` |
| POST | `/aeroplanes/{aeroplane_id}/operating-points/avl-trim` | `AVLTrimRequest{operating_point, trim_constraints}` | `AVLTrimResult` |

**Acceptance criteria**

- **AC-1 — A custom point trims through the same two-stage solver as the generator**
  - **Given** an aircraft with a full control set
  - **When** `POST .../operating-points/trim` is sent `{"name": "cruise_alt_500", "velocity": 16.0, "altitude": 500.0, "n_target": 1.0}`
  - **Then** the response is 200 `TrimmedOperatingPointRead` whose `point` is persisted with `status` `TRIMMED` (`trim_score < 0.35`) or `NOT_TRIMMED` with a warning, using the same `asb.Opti` → grid-fallback engine as the 15-target generator, not the Brent solver
- **AC-2 — AeroBuildup trim reports non-convergence instead of raising**
  - **Given** an aircraft whose `Cm` has the same sign at both deflection bounds (`[-25, 25]`)
  - **When** `POST .../operating-points/aerobuildup-trim {"trim_variable": "elevator", "target_coefficient": "Cm", "target_value": 0.0}`
  - **Then** the response is **200**, not 500, with `converged: false` and a warning describing the unbracketed interval — `scipy.optimize.brentq` is never allowed to propagate an exception (BR-AA19)
- **AC-3 — AVL rejects an unknown trim variable with both valid sets**
  - **Given** an `AVLTrimRequest` whose `trim_constraints` name a `variable` that is neither an AVL axis token (`alpha`/`beta`/`roll_rate`/`pitch_rate`/`yaw_rate`) nor a real control-surface name
  - **When** `POST .../operating-points/avl-trim`
  - **Then** the response is **422** `validation_error` listing both the axis tokens and the aircraft's available control names
  - **Note:** the surface name must be the gh-772 **mixing name** for a dual-role surface (e.g. `[ruddervator]pitch_htail_1`); a raw DB TED name will not resolve (🔴 bug #955 territory)

**Confidence:** 🟢 CONFIRMED

## US-AERO-04 — Analyse the aircraft at a single flight condition with a chosen solver

**As an** MCP-agent client, **I want** to run one flight condition through
AeroBuildup, the in-process VLM, or AVL, **so that** I get a solver-agnostic
result envelope regardless of which tool I picked.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/operating_point/{analysis_tool}` | `OperatingPointSchema` | analysis result |
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}` | `OperatingPointSchema` | analysis result (single-wing pruned) |

`{analysis_tool} ∈ {avl, aerobuildup, vortex_lattice}`.

**Acceptance criteria**

- **AC-1 — One envelope, three solvers**
  - **Given** an aircraft with three lifting surfaces and `OperatingPointSchema{velocity: 12, alpha: 5.0, xyz_ref: [cg_x, 0, 0]}`
  - **When** the same body is POSTed to `.../operating_point/vortex_lattice`, `.../aerobuildup` and `.../avl`
  - **Then** all three return 200 with identical field names — only `method` differs (`"vortex_lattice"` / `"aerobuildup"` / `"avl"`)
  - **And** changing `xyz_ref[0]` alone (geometry unchanged) changes `Cm` on every solver, because the moment reference is always set from `operating_point.xyz_ref` before dispatch
- **AC-2 — The rad/deg guard catches a mistaken magnitude before any solve**
  - **Given** a request body with `alpha: 200`
  - **When** POSTed to any `analysis_tool`
  - **Then** the response is **422** `validation_error` whose message states this "almost certainly means radians were passed instead of degrees" (gh-577/gh-587)
- **AC-3 — An unknown control-deflection name is a 422, never a silent drop**
  - **Given** `control_deflections: {"aileron_typo": 5.0}` on an aircraft whose real surfaces are `elevator`/`aileron`
  - **When** POSTed to `.../operating_point/aerobuildup`
  - **Then** the response is **422** listing `aileron_typo` as unknown and both real names as available (BR-20) — `Airplane.with_control_deflections` would otherwise silently drop the unknown key and still report a clean analysis
- **AC-4 — AVL refuses an array-valued sweep**
  - **Given** `alpha: [0, 5, 10]` (a list, not a scalar)
  - **When** `analysis_tool = avl`
  - **Then** the response is **422** — `ValueError("AVL analysis does not support parameter sweeps")` (BR-AA2)

**Confidence:** 🟢 CONFIRMED

## US-AERO-05 — Sweep angle of attack and inspect the diagnostic diagram

**As a** hobbyist, **I want** an angle-of-attack sweep with the six
characteristic points and a rendered diagram, **so that** I can see the
whole drag polar and stall behaviour at a glance without reading raw numbers.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/alpha_sweep` | `AlphaSweepRequest` | sweep array + six characteristic points + optional speed polar |
| POST | `/aeroplanes/{aeroplane_id}/alpha_sweep/diagram` | `AlphaSweepRequest` | `StaticUrlResponse` |
| POST | `/aeroplanes/{aeroplane_id}/simple_sweep` | `SimpleSweepRequest` | multi-parameter sweep |

**Acceptance criteria**

- **AC-1 — The sweep is hard-coded AeroBuildup, never a subprocess**
  - **Given** an aircraft with three lifting surfaces
  - **When** `POST .../alpha_sweep`
  - **Then** the response is 200 with `method: "aerobuildup"` (AVL is unreachable on this route — BR-15) and all six characteristic points present, each `null` when its inputs are absent rather than fabricated
- **AC-2 — The diagram renders and returns a resolvable URL**
  - **Given** the same aircraft
  - **When** `POST .../alpha_sweep/diagram`
  - **Then** the response is 200 `StaticUrlResponse` pointing at a `/static/.../png/alpha_sweep_<hex>.png` file — a 3×2 matplotlib figure (coefficients, CL–CD polar, CL–Cm, L/D, `Xnp`/`Xnp_lat`, summary) with `dCm/dα` trend colouring (green `< −0.01` / amber `≤ 0.01` / red else)
- **AC-3 — Zero-lift falls back to the nearest sample when CL never crosses zero**
  - **Given** an alpha sweep whose `CL` stays positive throughout (e.g. a highly cambered wing)
  - **When** the characteristic points are computed
  - **Then** `drag_at_zero_lift_point` is taken at `argmin(|CL|)` instead of being interpolated at the (non-existent) sign change

**Confidence:** 🟢 CONFIRMED

## US-AERO-06 — Visualize streamlines and download three-view renders

**As a** hobbyist, **I want** a Trefftz-plane streamline plot and a
resolvable three-view image, **so that** I can see the flow visually instead
of only reading coefficients.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/streamlines` | `OperatingPointSchema` | Plotly figure JSON |
| POST | `/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url` | `OperatingPointSchema` | `StaticUrlResponse` |
| GET | `/aeroplanes/{aeroplane_id}/three_view/url` | — | `StaticUrlResponse` |

**Acceptance criteria**

- **AC-1 — Streamlines always run the in-process VLM**
  - **Given** any aircraft and a valid `OperatingPointSchema`
  - **When** `POST .../streamlines`
  - **Then** the response is 200 with a Plotly figure JSON — the solver is hard-coded `VORTEX_LATTICE`, never AVL, regardless of any solver query elsewhere on the API
- **AC-2 — Deflection validation blocks a plot mislabeled "trimmed"**
  - **Given** `control_deflections` referencing a control surface that no longer exists (renamed or removed)
  - **When** `POST .../streamlines`
  - **Then** the response is **422** listing unknown vs available names (BR-20) — otherwise the UI could render a plot titled "trimmed" whose deflection was silently never applied
- **AC-3 — The static three-view needs no flight condition**
  - **Given** an aircraft with a previously generated render
  - **When** `GET .../three_view/url`
  - **Then** the response is 200 `StaticUrlResponse` — this route takes no `OperatingPointSchema` body, unlike its vortex-lattice sibling

**Confidence:** 🟢 CONFIRMED

## US-AERO-07 — Read the aircraft's static-stability verdict

**As an** RC/UAV designer, **I want** to compute and re-read the aircraft's
static-margin classification, **so that** I know whether it is stable
without re-running a solver on every page view.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/stability_summary/{analysis_tool}` | `OperatingPointSchema` | `StabilitySummaryResponse` |
| GET | `/aeroplanes/{aeroplane_id}/stability` | — | `StabilityResultRead` |

**Acceptance criteria**

- **AC-1 — Upsert one row per solver, classified three ways**
  - **Given** an aircraft with a valid trim state
  - **When** `POST .../stability_summary/aerobuildup` is called twice
  - **Then** both calls return 200 and exactly **one** `stability_results` row exists for solver `"aerobuildup"` (unique on `(aeroplane_id, solver)`); `static_margin = (Xnp − Xcg)/MAC` classifies `stable` (>5%) / `neutral` (0–5%) / `unstable` (<0)
- **AC-2 — The cached read prefers `CURRENT` over `DIRTY`**
  - **Given** a `CURRENT` row and a `DIRTY` row exist for the aeroplane
  - **When** `GET .../stability`
  - **Then** the `CURRENT` row is returned (ordering `status ASC, computed_at DESC` — 🟡 this relies on `"CURRENT"` sorting alphabetically before `"DIRTY"`, not an explicit rank)
- **AC-3 — No cached result is a 404, not an empty body**
  - **Given** an aeroplane that has never been stability-analysed
  - **When** `GET .../stability`
  - **Then** the response is **404** `not_found`
- **AC-4 — Known defect: a V-tail reports no trim elevator deflection**
  - **Given** an aircraft whose only pitch control is `[ruddervator]pitch_htail_1` (the gh-772 mixing name)
  - **When** the stability summary is computed
  - **Then** `trim_elevator_deg` is `null` — `_find_trim_elevator`'s substring match on `"elevator"` never matches a ruddervator's mixing name (🔴 open bug #955)

**Confidence:** 🟢 CONFIRMED

## US-AERO-08 — Pull strip forces and spanwise loads for structural sizing

**As an** RC/UAV designer, **I want** per-strip aerodynamic loads and their
integrated shear/bending distribution, **so that** I can size a spar against
a real flight condition instead of a rule of thumb.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/strip_forces` | `OperatingPointSchema`, `?solver=vlm\|avl` | `StripForcesResponse` |
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/strip_forces` | same | `StripForcesResponse` |
| POST | `/aeroplanes/{aeroplane_id}/spanwise_loads` | `OperatingPointSchema`, `?solver` | `SpanwiseLoadsResponse` |
| POST | `/aeroplanes/{aeroplane_id}/spanwise_loads_with_sizing` | + `material_id`, sizing params | `SpanwiseLoadsWithSizingResponse` |

**Acceptance criteria**

- **AC-1 — The default in-process VLM is inviscid by contract, not by bug**
  - **Given** an aircraft and a valid `OperatingPointSchema`, no `?solver` override
  - **When** `POST .../strip_forces`
  - **Then** the response is 200 with `aero_model: "ASB"`; `cdv`, `cm_c/4` and `cm_LE` are always `0.0` and `C.P.x/c` is always `0.25` — the Trefftz chart shows no viscous component, and this is documented behaviour, not a defect (ADR 0003, BR-AA4)
- **AC-2 — AVL is an explicit opt-in and returns real viscous fields**
  - **Given** the same body
  - **When** `POST .../strip_forces?solver=avl`
  - **Then** the response is 200 with `aero_model: "AVL"` and real `cdv`/`cm_c/4`/`cm_LE`/`C.P.x/c` values from the subprocess run
- **AC-3 — A non-positive allowable stress is rejected before any division**
  - **Given** a `spanwise_loads_with_sizing` request whose material has `allowable_bending_stress_mpa ≤ 0`
  - **When** `POST .../spanwise_loads_with_sizing`
  - **Then** the response is **422** `validation_error`, never a division-by-zero 500
- **AC-4 — Single-wing strip forces never consult the stored `.avl` geometry**
  - **Given** an aircraft with a saved, user-edited `.avl` geometry file
  - **When** `POST .../wings/{wing_name}/strip_forces?solver=avl`
  - **Then** the airplane is pruned to that one wing before the AVL run and the stored geometry file is not read at all — only the full-airplane `strip_forces` and `analyze_airplane` paths consult it (🟡 documented divergence)

**Confidence:** 🟢 CONFIRMED

## US-AERO-09 — Watch a stale trim heal itself after a geometry edit

**As an** RC/UAV designer, **I want** every stored trim to become visibly
stale the moment I change a wing, and to see it repaired in the background,
**so that** I never read a chart that silently describes an older aircraft.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/analysis-status` | Coarse roll-up of operating-point status counts |
| GET | `/aeroplanes/{aeroplane_id}/speed-polar` | Read the cached speed polar, reflecting the healed state |

**Acceptance criteria**

- **AC-1 — A geometry edit dirties every operating point and a background job repairs it**
  - **Given** three `TRIMMED` operating points on an aircraft
  - **When** a wing cross-section is updated (any wing/x-section/fuselage write)
  - **Then** all three flip to `DIRTY` immediately (`mark_ops_dirty`, excluding rows already `DIRTY`/`COMPUTING`), `GET .../analysis-status` reports the `DIRTY` count, and `retrim_dirty_ops` — in its own DB session — claims each row through `COMPUTING` to `TRIMMED` or `LIMIT_REACHED`
  - **And** a later `GET .../analysis-status` shows the points back at `TRIMMED`
- **AC-2 — A corrupt row is never retried forever**
  - **Given** a `DIRTY` operating point whose stored row fails Pydantic validation on load
  - **When** `retrim_dirty_ops` processes it
  - **Then** its status becomes `INVALID` (terminal for retry) and the next retrim cycle skips it — a transient solver error, by contrast, reverts to `NOT_TRIMMED` and is retried
- **AC-3 — Known gap: no pitch control leaves every point dirty forever**
  - **Given** an aircraft with no TED whose role is `elevator`/`stabilator`/`elevon`/`ruddervator`
  - **When** `retrim_dirty_ops` runs
  - **Then** every operating point stays `DIRTY` indefinitely, recorded only as a server-side log warning — to the user the aircraft looks perpetually "recomputing" (🔴 BR-RI8, open)
- **AC-4 — The speed polar reflects the healed state — with one silent fallback**
  - **Given** the retrim above has completed and the aero context has also been recomputed
  - **When** `GET .../speed-polar`
  - **Then** the response is 200 `SpeedPolarResponse` with one curve per mass (base mass flagged `is_base`, `V, w ∝ sqrt(m)`), reflecting the current geometry — reads the cached aero context, it does **not** run a solver
  - **But** with no `mass` assumption at all the polar is still 200, computed at a hard-coded **1.0 kg**, with no user-visible warning (🔴 BR-AA23)

**Confidence:** 🟢 CONFIRMED

## Open questions 🔴

- **Bug #955 (control naming divergence).** `trim_enrichment_service`,
  `retrim_service._find_pitch_control_name` and
  `stability_service._find_trim_elevator` all key on the raw DB TED name or a
  substring match on `"elevator"`, while the AVL/mixing contract (gh-772) uses
  names like `[ruddervator]pitch_htail_1`. Every dual-role aircraft (V-tail,
  elevon, flaperon) gets a wrong authority verdict and a phantom 0° surface
  in the enrichment until this is fixed.
- **BR-RI8 — `DIRTY` is absorbing without a pitch control.** No structural
  signal distinguishes "still retrimming" from "can never retrim."
- **BR-RI9 — Geometry listeners registered twice** (`stability_events.py` and
  `avl_geometry_events.py` both attach to `WingModel`/`WingXSecModel`/
  `FuselageModel`), so every geometry write fires `GeometryChanged` and
  `mark_ops_dirty` twice.
- **BR-AA17 — `_auto_populate_cd0` violates BR-14/ADR 0004.** A stability run
  on AeroBuildup can overwrite the parasite `cd0` assumption with total `CD`
  between recomputes.
- **`AVLTrimResult.converged`** is inferred from `"CL" in raw` — a partially
  converged run that printed coefficients reports `true`.
- **SSE `skip` semantics (gh-865/BR-MS39).** A capability-gated target and a
  failed-solve target are indistinguishable to the client; only the latter
  produces any event at all, and it carries no reason.
- **BR-AA16 — `min_static_margin`/`max_static_margin`** are read by
  `stability_service` for the CG-range bounds but are never seeded, so the
  5%/25% defaults are effectively hard-coded while presenting as configurable.
