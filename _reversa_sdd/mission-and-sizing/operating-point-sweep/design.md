# operating-point-sweep — Technical Design

> Use-case design, nested under the module
> [`mission-and-sizing`](../design.md).
> Focuses on HOW this use case is built, read from the legacy code.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`tasks.md`](tasks.md), [`../contracts.md`](../contracts.md) §D.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `generate_default_set_for_aircraft` | `(db, aircraft_uuid, replace_existing=False, profile_id_override=None)` | `GeneratedOperatingPointSetRead` | **sequential** by design 🟢 |
| `generate_default_set_stream_for_aircraft` | same | `Iterator[str]` (SSE) | process pool + incremental commit 🟢 |
| `trim_operating_point_for_aircraft` | `(db, aircraft_uuid, request)` | `TrimmedOperatingPointRead` | single ad-hoc target, same solver 🟢 |
| `_prepare_generation` | `(db, aircraft_uuid, profile_id_override)` | `_GenerationContext` | the whole resolution pipeline 🟢 |
| `_estimate_reference_speeds` | `(profile, cached_context)` | `{vs_clean, vs_to, vs_ldg, provenance}` | 🟢 |
| `_build_target_definitions` | `(profile, refs)` | `list[dict]` — 15 entries | 🟢 |
| `_clip_flap_to_ted_limit` | `(target, deflection_limits)` | `dict` | returns the original object when there is nothing to clip 🟢 |
| `_stamp_stale_no_polar` | `(targets, refs)` | `list[dict]` | copies; no-op unless `provenance == "cold_start"` 🟢 |
| `_detect_control_capabilities` | `(asb_airplane)` | `dict` | four booleans + `available_controls` 🟢 |
| `_validate_target_capability` | `(target, capabilities)` | `(bool, str)` | the `str` names the missing capability 🟢 |
| `_solve_trim_candidate_with_opti` | `(…)` | `dict \| None` | `None` on **any** exception 🟢 |
| `_grid_search_trim` | `(…)` | `(score, α, β, V, controls)` | `controls` is always `{}` 🔴 |
| `_apply_limit_warnings` | `(α, β, score, constraints, warnings)` | `OperatingPointStatus` | mutates `warnings` 🟢 |
| `_trim_or_estimate_point` | `(…)` | `TrimmedPoint` | the two-stage orchestration 🟢 |
| `_persist_point_set` | `(db, aircraft, points, profile_id, replace_existing, design_cg_x)` | `(opset, rows)` | 🟢 |
| `_solve_targets_in_parallel` | `(ctx, targets)` | `Iterator[(target, point \| None)]` | `as_completed` order 🟢 |
| `shutdown_opg_executor` | `()` | `None` | FastAPI lifespan teardown 🟢 |

HTTP surface: see [`../contracts.md`](../contracts.md) §D — two routes on the
operating-point router.

## Main Flow

```
_prepare_generation(db, uuid, profile_id_override)
 1. aircraft            = _get_aircraft_or_raise                       → NotFoundError
 2. profile, source_id  = _load_effective_flight_profile(db, aircraft, override)
                          no assignment ⇒ (_default_profile(), None)
 3. cruise_resolved     = _resolve_cruise_speed_with_md_fallback(
                              aircraft, profile.goals, source_id)
    profile["goals"]["cruise_speed_mps"] = cruise_resolved      ← WRITTEN BACK
 4. effective_mass_kg   = _load_effective_mass_kg(db, id, aircraft.total_mass_kg)
    design_cg_x         = _load_design_cg_x(db, id)
 5. refs                = _estimate_reference_speeds(profile, ctx)
 6. targets             = _build_target_definitions(profile, refs)      → 15
 7. plane_schema        = aeroplane_model_to_aeroplane_schema_async(aircraft)
    asb_airplane        = aeroplane_schema_to_asb_airplane_async(plane_schema)
    flap_limits         = build_deflection_limits_from_schema(plane_schema)
    targets             = [_clip_flap_to_ted_limit(t, flap_limits) for t in targets]
    targets             = _stamp_stale_no_polar(targets, refs)
    asb_airplane.xyz_ref = [design_cg_x, 0, 0]                  ← BEFORE any solve
 8. return _GenerationContext(aircraft, targets, asb_airplane,
        capabilities=_detect_control_capabilities(asb_airplane),
        deflection_limits=build_deflection_limits_from_schema(plane_schema),
        plane_schema, constraints=profile["constraints"],
        effective_mass_kg, design_cg_x, source_profile_id, refs)

batch path  (generate_default_set_for_aircraft)
 9. points = [p for t in ctx.targets if (p := _solve_and_enrich(ctx, t)) is not None]
        ← SEQUENTIAL on purpose
10. _persist_point_set(...);  flush;  refresh;  return the read schema

stream path (generate_default_set_stream_for_aircraft)
 9'. supported = [t for t in ctx.targets if _validate_target_capability(t, caps)[0]]
        ← capability filter happens HERE, before any event   🔴 BR-MS39
10'. clear (optional) → insert an EMPTY opset → flush → COMMIT
11'. yield event: targets  {opset_id, [{name, config, status:"COMPUTING"}, …]}
12'. for target, point in _solve_targets_in_parallel(ctx, supported):
         point is None → yield event: skip {name}
         else          → insert the row, flush, append the id to
                         opset.operating_points, COMMIT, refresh,
                         yield event: op <StoredOperatingPointRead JSON>
13'. yield event: done {opset_id, count}
```

## Resolution details 🟢

```
_load_effective_flight_profile(db, aircraft, override)
    override given      → _get_profile_or_raise(override)          source_id = override
    aircraft.flight_profile assigned → that profile                source_id = its id
    otherwise           → _default_profile()                       source_id = None

_resolve_cruise_speed_with_md_fallback(aircraft, goals, source_profile_id)
    source_profile_id is None  →  ctx["v_md_mps"]  when > 0        (BR-MS7)
    otherwise                  →  goals["cruise_speed_mps"]

_default_profile()
    environment  altitude_m 0 · wind_mps 0
    goals        cruise 18 · V_max 28 · margins 1.20 / 1.25 / 1.30
                 target_turn_n 2.0 · loiter_s 600
    constraints  max_alpha_deg 25 · max_beta_deg 30
```

The resolved cruise speed is **written back into the profile dict** before the
targets are built, so the `V_md` substitution propagates into every velocity
derived from `V_cruise` — not only into the `cruise` target. 🟢

## The fifteen targets 🟢

Each target is a plain dict with `name`, `config`, `velocity`, `altitude`,
`beta_target_deg`, `n_target`, and optionally `flap_deflection_deg`,
`bank_deg`, `warnings`. The table is in
[`requirements.md`](requirements.md) BR-MS9. Details visible only in the code:

- `n_target` for a turn is `round(1.0 / cos(radians(bank)), 4)` → `turn_20`
  1.0642 · `turn_40` 1.3054 · `turn_60` 2.0. 🟢
- `dutch_role_start` is pre-stamped with `warnings: ["NO_CONTROL_TRIM_MVP"]` at
  definition time — the only target that carries a warning before it is
  solved. 🟢
- `altitude` is the same for all fifteen: `profile.environment.altitude_m`. 🟢
- `stall_with_flaps` has an absolute floor of `2.0 m/s`, unlike every other
  target, which floors only through the reference speeds. 🟢
- `profile.goals.target_turn_n` and `loiter_s` are validated on the profile but
  **never read** by the target builder — the turns are hard-coded at 20/40/60°
  and the loiter point is a speed, not a duration. 🔴

## Reference speeds 🟢

```
_estimate_reference_speeds(profile, cached_context)
    cruise           = goals["cruise_speed_mps"]           default 18.0
    min_margin_clean = max(1.05, goals["min_speed_margin_vs_clean"])   default 1.20
    _pick(key)       = float(ctx[key]) when numeric and > 0, else None

    vs_clean_ctx = _pick("v_s1_mps") or _pick("v_stall_mps")
    None  → vs_clean = vs_to = vs_ldg = max(3.0, cruise / min_margin_clean)
            provenance = "cold_start"
    else  → vs_clean = vs_clean_ctx
            vs_to    = _pick("v_s_to_mps") or vs_clean
            vs_ldg   = _pick("v_s0_mps")   or vs_clean
            provenance = "polar"

    return {vs_clean: max(3.0, vs_clean),
            vs_to:    max(2.5, vs_to),
            vs_ldg:   max(2.0, vs_ldg),
            provenance}
```

The historical `0.95 · V_s1` (takeoff) and `0.90 · V_s1` (landing) multipliers
are **deliberately absent** — epic gh-525 finding C1 / audit §5.5 records that
they have no physical basis. When the per-configuration values are missing, the
**clean** value is reused unchanged for all three. 🟢

## Flap clipping 🟢

```
_clip_flap_to_ted_limit(target, deflection_limits)
    raw = target["flap_deflection_deg"];  None → return target unchanged
    collect (max_pos, max_neg) from every deflection_limits entry whose
        parse_role_tag(name).role ∈ FLAP_ROLES
    no flap-role entry  → return target UNCHANGED     ← no limit is manufactured
    flap_limits = (min(all max_pos), min(all max_neg))               gh-536
    limit   = max_pos if requested >= 0 else max_neg
    clipped = max(-max_neg, min(requested, max_pos))
    if abs(requested) > limit + 1e-6:
        append FLAP_DEFLECTION_CLIPPED (idempotent) and log a WARNING
```

Rationale recorded in the docstring 🟢: AVL has no internal hinge clamp and
NeuralFoil silently extrapolates τ(x_h/c) past its training range, so an
out-of-bound target produced physically wrong (over-attached) flow **with no
warning at all**. gh-536 added the multi-flap `min` so an inboard/outboard pair
with different authorities is governed by the smaller surface.

🟡 The function returns the **same object** when there is nothing to clip and a
**copy** when there is — callers must not rely on identity.

## Capability gating 🟢

```
_detect_control_capabilities(asb_airplane)
    walk wings → xsecs → control_surfaces, collect non-empty names
    role, _ = parse_role_tag(name)
    → {has_pitch_control: roles & PITCH_ROLES,
       has_roll_control:  roles & ROLL_ROLES,
       has_yaw_control:   roles & YAW_ROLES,
       has_flap:          roles & FLAP_ROLES,
       available_controls: sorted(set(names))}

_validate_target_capability(target, capabilities)
    name.startswith("turn_")   → has_roll_control OR has_yaw_control
                                 (an explicit disjunction, checked first)
    name == "dutch_role_start" → has_yaw_control
    name == "stall_with_flaps" → has_flap
    otherwise                  → always supported
    → (False, "<missing capability names>")
```

`PITCH_ROLES = {elevator, stabilator, elevon, ruddervator}`,
`ROLL_ROLES = {aileron, elevon, flaperon}`,
`YAW_ROLES = {rudder, ruddervator}`, `FLAP_ROLES = {flap}` — the overlap is
deliberate: an elevon counts as both pitch and roll, a ruddervator as both pitch
and yaw. 🟢
🟡 `has_pitch_control` is computed but no target requires it. An aircraft with
no pitch surface generates all fifteen targets and simply trims with an empty
control set.

## The two-stage trim 🟢

### Stage 1 — `asb.Opti`

```
α        = opti.variable(init = min(max(3.0, α_lo), α_hi),
                         lower = -8.0, upper = max(-7.0, max_alpha_deg))
pitch δ  = opti.variable(0.0, -25, 25)      when a PITCH_ROLES name exists
roll δ   = opti.variable(0.0, -20, 20)      turn targets only, ROLL_ROLES
yaw δ    = opti.variable(0.0, -25, 25)      turn + dutch targets, YAW_ROLES
flap     = the clipped FIXED value, applied via with_control_deflections,
           NEVER an optimiser variable

op   = asb.OperatingPoint(velocity, alpha=α, beta=β_target,
                          p, q, r from _op_turn_rates,
                          atmosphere=asb.Atmosphere(altitude))
res  = asb.AeroBuildup(airplane, op, xyz_ref=airplane.xyz_ref)
           .run_with_stability_derivatives()

objective = 50·Cm² + 3·CY²
            [+ 15·(CL − CL_target)²]      when CL_target is not None
            [+ 2·Cl² + 2·Cn²]             turn targets
            + Σ 0.001·δ²                  control-effort regulariser

opti.solve(verbose=False, max_iter=120, max_runtime=0.35,
           behavior_on_failure="return_last")

any exception  →  log at DEBUG and return None   ← the run continues
```

The weights encode the priority: pitch trim (50) dominates lateral force (3);
the CL match (15) is a soft constraint, not a hard one; the roll/yaw moments (2)
matter only in a turn; the 0.001 control penalty merely breaks ties. 🟡 None of
the five weights is named or documented in the code.

### Stage 2 — the grid search

```
for candidate_velocity in _fallback_speeds(name, velocity):
    for β in beta_candidates:
        for α in np.linspace(-4.0, 20.0, 13):
            score = _evaluate_trim_candidate(..., cl_target=cl_target_fn(V))
            if score < best:  best = (score, α, β, V);  best_controls = {}   🔴

_fallback_speeds(name, base):
    factors = [1.0, 0.95, 0.90, 0.85]   when name == "max_level_speed"
              [1.0, 1.05, 1.10, 1.15]   otherwise
    return [max(2.0, base · f) for f in factors]
```

gh-528: the fallback updates **both** α and the velocity — an earlier version
moved α only and could never reach a trimmable state for a point whose target
speed was infeasible. 🟢
🔴 `best_controls` is reset to `{}` on every improvement and returned empty, so
the fallback path trims by **α, β and V only**. A target that needs a different
control deflection is unreachable by the fallback.

### Scoring and status

```
_compute_trim_score(cm, cy, cl, cl_target) = |Cm| + 0.5·|CY|
                                             [+ 0.3·|CL − CL_target|]
_cl_target_for_velocity(V, m, S_ref, ρ, n) =
    None  when m is falsy or S_ref <= 0 or q <= 1e-6
    else  m·9.81·n / (½·ρ·max(V, 1e-3)²·S_ref)

_apply_limit_warnings(α, β, score, constraints, warnings):
    TRIMMED if score < 0.35 else NOT_TRIMMED  (+ "NOT_TRIMMED" warning)
    |α| > max_alpha_deg → LIMIT_REACHED + "ALPHA_LIMIT_REACHED"
    |β| > max_beta_deg  → LIMIT_REACHED + "BETA_LIMIT_REACHED"
```

`LIMIT_REACHED` **overrides** `TRIMMED` — a converged solution outside the
declared envelope is reported as limited, not as trimmed. 🟢

### Turn kinematics and feasibility

```
_op_turn_rates(target, V):  bank_deg absent → (0, 0, 0)
                            else turn_kinematics(bank, V) → (p, q, r) rounded to 6

_apply_turn_feasibility(point, bank_deg, V, vs_clean):
    n = turn_kinematics(bank, V).n            # 1/cos φ
    V < vs_clean·√n  →  point.status = LIMIT_REACHED
                        append "STALL_IN_TURN: required CL at {bank} deg bank
                                (n={n}) exceeds CL_max — V={V} < V_stall_turn={…}"
```

🔴 That warning is a **formatted sentence**, unlike every other entry in
`warnings[]`, which is a bare token. A consumer matching on equality misses it.

## Persistence 🟢

```
_op_model_from_point(aircraft, point, design_cg_x) → OperatingPointModel(
    aircraft_id, name, description, config, status=point.status.value,
    warnings, controls, velocity,
    alpha=point.alpha_rad, beta=point.beta_rad,          ← RADIANS
    p, q, r, xyz_ref=[design_cg_x, 0.0, 0.0], altitude, trim_enrichment)

_clear_existing_op_sets(db, aircraft)                    ← replace_existing only
    DELETE FROM operating_pointsets WHERE aircraft_id = …
    DELETE FROM operating_points    WHERE aircraft_id = …      🔴 aircraft-wide

_persist_point_set(...)
    insert every point → flush (to obtain ids)
    insert ONE OperatingPointSetModel(
        name="default_operating_point_set",
        description="Auto-generated standard operating point set including
                     Dutch-roll start point.",
        aircraft_id, source_flight_profile_id,
        operating_points=[p.id for p in stored])          🟡 a JSON id list
```

## Parallelism (gh-867) 🟢

```
CasADi/IPOPT does NOT release the GIL → a thread pool benchmarked at 0.35–0.89×

_BLAS_THREAD_ENV = (OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS,
                    VECLIB_MAXIMUM_THREADS, NUMEXPR_NUM_THREADS)
_opg_mp_context  = multiprocessing.get_context("spawn")
_opg_executor    = module-level singleton behind _opg_executor_lock
_opg_worker_count() = max(1, min(4, cpu_count - 1))

pool creation: the parent's BLAS env vars are set to "1", the executor is
created (so the spawned children inherit them), a no-op task warms the pool,
then the parent's env is RESTORED. _opg_worker_init re-applies them in each
worker.

_WorkerSolveCtx  = the picklable subset: asb.Airplane (pickles cleanly),
                   constraints, capabilities, effective_mass_kg,
                   _AircraftMassOnly(total_mass_kg)      ← the SQLAlchemy model
                                                           does NOT pickle
workers NEVER open a DB session.
_solve_targets_in_parallel yields (target, point|None) in as_completed order;
an exception inside a worker is logged and yields (target, None).
shutdown_opg_executor() is wired into the FastAPI lifespan.
→ ≈ 2.9× at 4 workers
```

The **batch** path is sequential on purpose: *"gh-867 parallelism is applied
only to the streaming path (the live 'Generate Default OPs' UI flow), so the
batch contract — and the many tests that mock the solver here — are
unchanged."* 🟢

## Alternative Flows

- **No flight profile assigned.** `_default_profile()` with
  `source_profile_id = None` ⇒ the cruise speed becomes `V_md` from the cached
  context. 🟢
- **`profile_id_override` names a missing profile.** `_get_profile_or_raise`
  raises `NotFoundError` → 404 on the batch path, an SSE `error` event on the
  stream. 🟢
- **No computation context (cold start).** Reference speeds fall back to
  `max(3.0, V_cruise / margin)`; every target is stamped `STALE_NO_POLAR`. 🟢
- **No flap-role TED.** No limit is manufactured; the target passes through and
  the trim solver no-ops the missing surface. 🟢
- **Missing roll/yaw/flap capability.** The dependent targets are skipped. On
  the batch path `_solve_and_enrich` logs a WARNING naming the missing
  capability and the available controls, and returns `None`; on the stream path
  they are filtered out before any event. 🔴 Two different observability levels
  for the same condition.
- **`Opti` raises or fails to converge.** `behavior_on_failure="return_last"`
  keeps the last iterate; any exception makes the candidate `None`, and the grid
  fallback runs regardless. 🟢
- **A turn below the stall speed for its load factor.** `LIMIT_REACHED` +
  `STALL_IN_TURN`. 🟢
- **Enrichment fails.** Logged with `exc_info`; the point is returned **without**
  `trim_enrichment`. 🟢
- **A worker process dies.** `future.result()` raises, the exception is logged
  and the target yields `None` → a `skip` event. The pool is not rebuilt. 🟡
- **The client disconnects mid-stream.** Every point committed so far survives,
  and `opset.operating_points` lists exactly those. 🟢

## Dependencies

- **`aero-analysis`** — the cached context (`v_s1_mps`, `v_s_to_mps`,
  `v_s0_mps`, `v_stall_mps`, `v_md_mps`), `trim_enrichment_service`, and the
  `OperatingPointStatus` state machine.
- **`wing-design`** — TED roles and hinge limits via
  `build_deflection_limits_from_schema`, and the mixing parameters via
  `build_mix_params_from_schema`; `parse_role_tag` for the capability walk.
- **[`../design-assumptions/`](../design-assumptions/design.md)** —
  `design_cg_x` and the effective `mass`.
- **`mission-and-sizing` / flight profiles** — the goals and constraints that
  define the targets.
- **AeroSandbox** — `asb.Opti` (IPOPT/CasADi), `asb.AeroBuildup`,
  `asb.OperatingPoint`, `asb.Atmosphere`, and an `asb.Airplane` that pickles.
- **`platform-core`** — `get_db()` (BR-78, with the documented streaming
  exception), the FastAPI lifespan for `shutdown_opg_executor`, and SSE
  plumbing.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| Fifteen fixed targets rather than a user-defined sweep | `_build_target_definitions` | 🟢 |
| Stall speeds come from the polar, not from fixed multipliers (audit §5.5) | `_estimate_reference_speeds` | 🟢 |
| The cold-start estimate is stamped onto every target rather than blocked | `_stamp_stale_no_polar` | 🟢 |
| Flap targets clip to the **most restrictive** surface (gh-527/gh-536) | `_clip_flap_to_ted_limit` | 🟢 |
| No flap TED ⇒ no manufactured limit | same | 🟢 |
| Capability gating skips rather than fails (BR-21) | `_validate_target_capability` | 🟢 |
| The turn requirement is roll **or** yaw | same, checked before the generic path | 🟢 |
| Flap deflection is a fixed input, never an optimiser variable | `_solve_trim_candidate_with_opti` | 🟢 |
| The moment reference is set on the airplane once, in `_prepare_generation` | `asb_airplane.xyz_ref = [design_cg_x, 0, 0]` | 🟢 |
| A time-boxed `Opti` with `return_last`, then a deterministic grid | `max_runtime=0.35`, `_grid_search_trim` | 🟢 |
| The grid fallback moves velocity too (gh-528) | `_fallback_speeds` in the outer loop | 🟢 |
| A top-speed target is retried **slower** | `_fallback_speeds` branch | 🟢 |
| `LIMIT_REACHED` overrides `TRIMMED` | `_apply_limit_warnings` | 🟢 |
| Turn feasibility is checked after the solve, before persistence | `_solve_and_enrich` | 🟢 |
| The solver path lives on `trim_method`, never in the residuals (gh-627) | `TrimmedPoint` typing | 🟢 |
| Processes, not threads, because CasADi holds the GIL (gh-867) | the pool block | 🟢 |
| BLAS is pinned in the parent at spawn **and** in the initializer, then restored | `_get_opg_executor`, `_opg_worker_init` | 🟢 |
| Workers never touch the DB; only `total_mass_kg` crosses | `_WorkerSolveCtx`, `_AircraftMassOnly` | 🟢 |
| The batch path stays sequential to preserve its contract and mocks | the in-code comment | 🟢 |
| Each SSE point is committed before it is emitted (gh-865) | the streaming generator | 🟢 |
| A setup failure is an SSE `error` event, not an HTTP error | same | 🟢 |
| The point set stores a JSON id list rather than an association table | `_persist_point_set` | 🟡 |

## Internal State

| Table | Cardinality | Note |
|---|---|---|
| `operating_points` | one row per solved point | `alpha`/`beta` in **radians**; `xyz_ref = [design_cg_x, 0, 0]`; owned by `aero-analysis` |
| `operating_pointsets` | one per generation run (or one, when `replace_existing`) | `operating_points` is a **JSON id list**; `source_flight_profile_id` records the profile |
| `_opg_executor` | one module-level `ProcessPoolExecutor` per process | lock-guarded; torn down by the FastAPI lifespan |

## Observability

- Every generated OP carries `warnings[]` — `STALE_NO_POLAR`,
  `FLAP_DEFLECTION_CLIPPED`, `ALPHA_LIMIT_REACHED`, `BETA_LIMIT_REACHED`,
  `NOT_TRIMMED`, `NO_CONTROL_TRIM_MVP`, and the formatted `STALL_IN_TURN`
  sentence. 🟢
- `trim_method` and `trim_score` make the solver path auditable per point. 🟢
- The batch path logs a summary: *"Operating-point generation finished for
  aircraft %s: generated=%d / %d targets"*. 🟢
- A skipped target logs a WARNING naming the missing capability **and** the
  available controls — on the batch path only. 🔴
- A clipped flap logs a WARNING with the requested value, the clipped value and
  the limit. 🟢
- An `Opti` failure logs at **DEBUG** only, so a systematically failing stage 1
  is invisible at the default log level. 🟡
- The `refs.provenance` (`polar` / `cold_start`) is not persisted on the row —
  only its consequence (`STALE_NO_POLAR`) is. 🟡
- 🔴 The stream emits no reason with `skip`, and nothing at all for a
  capability-gated target.

## Constants 🟢

| Constant | Value | Where |
|---|---|---|
| role sets | `PITCH {elevator, stabilator, elevon, ruddervator}` · `ROLL {aileron, elevon, flaperon}` · `YAW {rudder, ruddervator}` · `FLAP {flap}` | `:48-51` |
| stall-speed floors | `vs_clean ≥ 3.0` · `vs_to ≥ 2.5` · `vs_ldg ≥ 2.0` | `_estimate_reference_speeds` |
| profile-goal defaults | cruise 18 · margins 1.20 / 1.25 / 1.30 · `V_max = max(1.35·V_c, V_c+8)` | `_build_target_definitions`, `_default_profile` |
| fixed flap deflections | takeoff 15° · landing 30° (before clipping) | `_build_target_definitions` |
| turn banks | 20 ° / 40 ° / 60 ° | same |
| dutch-roll β | 2.0° | same |
| trim threshold | `trim_score < 0.35` ⇒ TRIMMED | `_apply_limit_warnings` |
| Opti bounds | α ∈ [−8°, max(−7°, max_alpha)] · δ_pitch/yaw ∈ [−25, 25] · δ_roll ∈ [−20, 20] | `_solve_trim_candidate_with_opti` |
| Opti budget | `max_iter 120` · `max_runtime 0.35 s` · `behavior_on_failure "return_last"` | same |
| objective weights | `50·Cm²` · `3·CY²` · `15·ΔCL²` · `2·Cl²` · `2·Cn²` · `0.001·δ²` | same |
| grid | α = `linspace(−4°, 20°, 13)` · velocity factors `[1.0, 1.05, 1.10, 1.15]` or `[1.0, 0.95, 0.90, 0.85]` · floor `2.0 m/s` | `_grid_search_trim`, `_fallback_speeds` |
| score weights | `|Cm| + 0.5|CY| + 0.3|ΔCL|` | `_compute_trim_score` |
| gravity | `9.81` | `_cl_target_for_velocity` |
| pool | `max_workers = max(1, min(4, cpu − 1))`, spawn, five BLAS vars pinned to `1` | `:1188-1252` |
| set naming | `default_operating_point_set` + the fixed description | `:1005-1006` |

## Risks and Gaps

- 🟢 **No deflection grid — the defect is elsewhere** (`Q-MS-5`, expert consensus endorsed by the maintainer). Previously `_grid_search_trim` never varied the control surfaces:
  (`best_controls = {}` is reset on every improvement), so the fallback can only
  trim by α/β/V. A target that needs a different deflection is unreachable by
  the fallback, and the resulting point is reported `NOT_TRIMMED` rather than
  "not reachable with the available authority".
- 🔴 **A capability-gated target is invisible on the stream** (BR-MS39): it
  appears in neither `targets` nor `skip`, and `skip` itself carries no reason.
  The batch path logs a warning the stream client never sees.
- 🔴 **`replace_existing` is aircraft-wide** and deletes manually created
  operating points along with the generated ones.
- 🔴 **The `STALL_IN_TURN` warning is a formatted sentence**, while every other
  warning is a bare token — a consumer matching on equality misses it.
- 🔴 **`profile.goals.target_turn_n` and `loiter_s` are validated but never
  used.** The turns are hard-coded at 20/40/60° and the loiter point is a speed;
  a user who sets `target_turn_n = 3.0` sees no effect.
- 🟡 **`has_pitch_control` is detected but never required**, so an aircraft with
  no pitch surface generates all fifteen targets and trims with an empty control
  set.
- 🟡 **The `Opti` failure log is DEBUG-level**, so a systematically failing
  stage 1 (and the 4× slower grid path it implies) is invisible in production.
- 🟡 **None of the six objective weights is named or justified** in the code.
- 🟡 **`operating_pointsets.operating_points` is a JSON id list** with no
  referential integrity — a deleted OP leaves a dangling id.
- 🟡 **A dead worker is not detected**; the pool is reused as-is and the target
  simply yields `None`.
- 🟡 **The reference-speed `provenance` is not persisted**, only its consequence.
- 🟡 **The streaming path commits directly**, a documented but real exception to
  ADR 0009.
