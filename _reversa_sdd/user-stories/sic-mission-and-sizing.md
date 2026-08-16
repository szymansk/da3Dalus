# Define the Mission and Size the Aircraft

> **Personas:** RC/UAV designer · Hobbyist · AI-copilot user · MCP-agent client
> **Modules:** `mission-and-sizing` (+ `aero-analysis`, `mass-and-balance`
> neighbours)
> **Primary surface:** `app/api/v2/endpoints/aeroplane/{design_assumptions,
> mission_objectives, matching_chart, field_lengths, sm_suggestions,
> tail_sizing}.py`, `app/api/v2/endpoints/flight_profiles.py`

## Context

Before an aircraft's geometry is trusted for anything, the designer states
**what it is for** (a mission preset), **what they assume about it** (mass,
`cd0`, `cl_max`, …, each with an estimate and — once physics can supply one —
a calculated value), and **how it will be flown** (a flight profile). This
design-intent layer feeds the classical sizing surfaces built on top of it:
the T/W-vs-W/S matching chart, tail-volume-coefficient sizing, static-margin
suggestions, and takeoff/landing field lengths. Unlike `aero-analysis`, this
module has **no single error envelope** — seven different local mappers
return FastAPI's bare `{"detail": "…"}` body, and two of them (matching chart,
field lengths) deliberately map a bare `ServiceException` to 422 instead of
500 for "your aircraft is not ready yet."

## US-SIC-01 — Pick a mission preset and see its estimates flow into the design

**As a** hobbyist, **I want** to choose a mission type from a curated preset
list, **so that** sensible starting estimates (g-limit, static margin,
`cl_max`, power loading) are filled in without me having to know their values.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/mission-presets` | List the nine seeded presets |
| GET | `/aeroplanes/{uuid}/mission-objectives` | Read the current objective (or its default) |
| PUT | `/aeroplanes/{uuid}/mission-objectives` | Upsert the objective, applying the preset on a mission change |

**Acceptance criteria**

- **AC-1 — Choosing a preset rewrites only the estimates**
  - **Given** an aircraft with `cl_max` calculated `1.32` (`active_source: CALCULATED`) and `mission_type: "trainer"`
  - **When** `PUT .../mission-objectives` sets `mission_type: "sailplane"`
  - **Then** the response is 200 and `design_assumptions.estimate_value` for `g_limit`, `target_static_margin`, `cl_max`, `power_to_weight` and `prop_efficiency` are rewritten to the sailplane preset's `suggested_estimates`
  - **And** `calculated_value` (still `1.32`), `calculated_source` and `active_source` (still `CALCULATED`) are byte-identical afterwards (BR-MS4)
- **AC-2 — A missing objective returns a default without persisting it**
  - **Given** a freshly created aeroplane with no `mission_objectives` row
  - **When** `GET .../mission-objectives`
  - **Then** the response is 200 with `mission_type: "trainer"`, `target_cruise_mps: 18.0`, `target_stall_safety: 1.8`, … and **no row is created** by the GET — the 404 is reserved for an unknown aeroplane UUID
- **AC-3 — Known gap: an unknown mission type is a silent no-op**
  - **Given** any aircraft
  - **When** `PUT .../mission-objectives` sets `mission_type: "spaceplane"`
  - **Then** the response is 200, no estimate changes, no warning is returned, **and** no `AssumptionChanged` is published — the preset writer creates missing assumption rows directly, bypassing `update_assumption`, so the write is invisible to the retrim/invalidation chain even when it would otherwise be effective (🔴 BR-MS4)

**Confidence:** 🟢 CONFIRMED

## US-SIC-02 — Track mission KPIs on the Ist/Soll radar

**As an** RC/UAV designer, **I want** a seven-axis comparison of where the
aircraft actually sits versus the mission's target polygon, **so that** I can
see at a glance which dimension (stall safety, glide, climb, cruise,
maneuver, wing loading, field friendliness) is under- or over-delivering.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{uuid}/mission-kpis?missions=<id>&missions=<id>` | Compute the Ist polygon and one Soll polygon per requested mission id |

**Acceptance criteria**

- **AC-1 — Seven axes, always, and no solver runs**
  - **Given** an aircraft with a cached aero context
  - **When** `GET .../mission-kpis?missions=trainer`
  - **Then** the response is 200 `MissionKpiSet` whose `ist_polygon` carries exactly 7 axes; no `AeroBuildup` call is issued (closed-form on cached data only)
  - **And** the active mission's Soll polygon is built from the objective's own editable targets (gh-767), not the static preset — raising `target_glide_ld` moves the white line without a re-seed
- **AC-2 — A cold start is holes, not zeros**
  - **Given** an aircraft with no computation context yet
  - **When** `GET .../mission-kpis`
  - **Then** every axis carries `provenance: "missing"` with `value`, `unit` and `score_0_1` all `null`; `field_friendliness` additionally carries a user-facing `warning` naming the missing input (e.g. *"Set t_static_N…"*)
- **AC-3 — An empty preset table fails loudly, not with a degenerate radar**
  - **Given** the `mission_presets` table has no rows at all (neither the requested id nor `"trainer"`)
  - **When** `GET .../mission-kpis`
  - **Then** the response is **500** — a deliberate `RuntimeError` telling the operator to run the seed; the user-controlled mission id itself is kept out of the log line (Sonar S5145)

**Confidence:** 🟢 CONFIRMED

## US-SIC-03 — Manage a design assumption's estimate vs. calculated value

**As an** RC/UAV designer, **I want** to see and edit each named parameter's
manual estimate, see how far it diverges from the computed value, and choose
which one is authoritative, **so that** I stay in control of design intent
while still benefiting from physics-derived numbers.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| GET / POST | `/aeroplanes/{aeroplane_id}/assumptions` | — | `AssumptionsSummary` (POST seeds, 201) |
| PUT | `/aeroplanes/{aeroplane_id}/assumptions/{param_name}` | `AssumptionWrite{estimate_value}` | `AssumptionRead` |
| PATCH | `/aeroplanes/{aeroplane_id}/assumptions/{param_name}/source` | `AssumptionSourceSwitch{active_source}` | `AssumptionRead` |

**Acceptance criteria**

- **AC-1 — The effective value follows the active source, and divergence is reported**
  - **Given** `mass` with `estimate_value: 1.5`, `calculated_value: 1.8`
  - **When** `PATCH .../assumptions/mass/source {"active_source": "CALCULATED"}`
  - **Then** the response is 200 `AssumptionRead` with `effective_value: 1.8`, `divergence_pct: 16.7` (rounded to one decimal), `divergence_level: "warning"` (the 15–30% band)
  - **And** `AssumptionChanged` is published and, because `mass` is OP-affecting, every non-`DIRTY` operating point flips to `DIRTY`
- **AC-2 — A design-choice parameter can never become `CALCULATED`**
  - **Given** `g_limit` (one of the seven `DESIGN_CHOICE_PARAMS`)
  - **When** `PATCH .../assumptions/g_limit/source {"active_source": "CALCULATED"}`
  - **Then** the response is **422** — *"Parameter 'g_limit' is a design choice and cannot use CALCULATED source"* (BR-26)
- **AC-3 — An unknown parameter name never reaches the service; NaN never reaches storage**
  - **Given** any aircraft
  - **When** `PUT /aeroplanes/{id}/assumptions/thrust` (not one of the 15 catalogued names)
  - **Then** the response is **422** — a FastAPI path-regex validation error, and the service function is never called (BR-MS31)
  - **And** `PUT .../assumptions/mass {"estimate_value": NaN}` is also **422** regardless of parameter name (`allow_inf_nan=False`)
- **AC-4 — Editing an estimate under an active calculation is silent by design**
  - **Given** `mass` with `active_source: CALCULATED`
  - **When** `PUT .../assumptions/mass {"estimate_value": 2.0}`
  - **Then** the response is 200, but no `AssumptionChanged` is published and no operating point becomes `DIRTY` — the effective value did not change (BR-27)

**Confidence:** 🟢 CONFIRMED

## US-SIC-04 — Trigger and monitor an assumption recompute

**As an** RC/UAV designer, **I want** to force a recompute of the cached aero
context and watch its job status, **and** tune the sweep resolution it uses,
**so that** I can refresh sizing numbers on demand and control the
cost/precision trade-off.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/recompute` | — | job envelope (**202**) |
| GET | `/aeroplanes/{aeroplane_id}/assumptions/recompute-status` | — | job envelope |
| GET | `/aeroplanes/{aeroplane_id}/assumptions/computation-context` | — | cached context dict \| `null` |
| GET / PUT | `/aeroplanes/{aeroplane_id}/computation-config` | `ComputationConfigWrite` (PUT) | `ComputationConfigRead` |

**Acceptance criteria**

- **AC-1 — A forced recompute is accepted and observable**
  - **Given** an aircraft whose recompute has never run
  - **When** `GET .../assumptions/recompute-status`
  - **Then** the response is 200 `{"status": "idle", "started_at": null, "finished_at": null, "error": null}`
  - **When** `POST .../recompute`
  - **Then** the response is **202** with the same envelope shape, transitioning through `pending`/`running` to `done` (or `failed` with an error string) on a later poll
- **AC-2 — Reading the computation config creates it, and a partial update merges**
  - **Given** an aircraft with no `aircraft_computation_config` row
  - **When** `GET .../computation-config`
  - **Then** the response is 200 with the seven documented defaults (`coarse_alpha_min_deg: -5.0` … `debounce_seconds: 2.0`) and a row now exists
  - **And** `PUT {"debounce_seconds": 5.0}` merges — every other field keeps its current value
- **AC-3 — Known gap: an inverted alpha range is silently accepted**
  - **Given** an aircraft with a computation config
  - **When** `PUT {"coarse_alpha_min_deg": 30, "coarse_alpha_max_deg": 10}`
  - **Then** the response is 200 — there is no cross-field validation, so the next recompute silently sweeps an empty α range (🔴 BR-MS32)
- **AC-4 — 202 Accepted does not guarantee the job actually started**
  - **Given** no running event loop is available to schedule the background task
  - **When** `POST .../recompute`
  - **Then** the response is still **202**, but the body reports `status: "idle"` — the client must poll `recompute-status` and notice nothing progressed (🟡)

**Confidence:** 🟢 CONFIRMED

## US-SIC-05 — Read the T/W-vs-W/S matching chart for a chosen mode

**As an** RC/UAV designer, **I want** the classical matching-chart
constraints for my launch/landing mode and mission profile, **so that** I can
see whether my current wing loading and thrust-to-weight ratio are feasible.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/matching-chart?mode=&s_runway=&v_s_target=&gamma_climb_deg=&v_cruise_mps=&flight_profile=` | Compute the T/W-vs-W/S matching chart |

**Acceptance criteria**

- **AC-1 — Mode defaults drive the constraint set**
  - **Given** an aircraft, `mode` omitted (defaults to `rc_runway`)
  - **When** `GET .../matching-chart`
  - **Then** the response is 200 `MatchingChartResponse` with `ws_range_n_m2` spanning 200 steps over `[10, 1500]` N/m², constraints for Takeoff (line), Landing (vertical), Cruise (line), Climb (line) and Stall (vertical) using the `rc_runway` defaults (50 m field / 5° climb gradient / 7 m/s stall target), a `design_point{ws_n_m2, t_w}` and a `feasibility` verdict
- **AC-2 — Profile applicability narrows what is rendered without discarding data**
  - **Given** `flight_profile=sailplane`
  - **When** `GET .../matching-chart?flight_profile=sailplane`
  - **Then** only the `stall` constraint has `applicable_for_profile: true`; every other constraint (takeoff, landing, cruise, climb, the RC-additive ones) is still present in the response with `applicable_for_profile: false` — the data stays for auditability, it is not omitted
- **AC-3 — Hand-launch removes the takeoff line and adds a wing-loading cap**
  - **Given** `mode=rc_hand_launch` (`s_runway` default `0`)
  - **When** `GET .../matching-chart?mode=rc_hand_launch`
  - **Then** the Takeoff constraint's `t_w_points` collapse to `0` (no runway constraint) and a vertical `hand_launch` constraint `W/S ≤ 80 N/m²` is added
- **AC-4 — A missing input is a 422, not a 500**
  - **Given** an aircraft whose `s_ref_m2` has never been computed (no recompute has run)
  - **When** `GET .../matching-chart`
  - **Then** the response is **422** (not 500) — this handler deliberately maps a bare `ServiceException` to 422 for "your aircraft is not ready yet," unlike every other handler in this module, which maps the same exception to 500
  - **And** the body is FastAPI's bare `{"detail": "…"}`, not the `{"error": {"code", …}}` envelope `aero-analysis` uses (🔴 two coexisting error shapes across the API)

**Confidence:** 🟢 CONFIRMED

## US-SIC-06 — Get a tail-volume-coefficient sizing recommendation

**As an** RC/UAV designer, **I want** the horizontal/vertical tail volume
coefficients compared against a target range for my aircraft class, **so
that** I know whether my tail is under- or oversized before I commit to a
layout.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/tail-sizing` | Compute `V_H`/`V_V` and recommend `S_H`/`S_V` |

**Acceptance criteria**

- **AC-1 — A conventional-tail aircraft gets a classified recommendation**
  - **Given** a conventional-tail aircraft with a computed assumption context (`mac_m`, `s_ref_m2`, `b_ref_m`, `x_np_m`) and named horizontal/vertical tail wings
  - **When** `GET .../tail-sizing`
  - **Then** the response is 200 `TailSizingResponse` with `v_h_current = S_H·l_H/(S_w·MAC)`, `v_v_current = S_V·l_V/(S_w·b)`, `classification` in `{in_range, below_range, above_range, out_of_physical_range}` per the target range for `aircraft_class_used` (e.g. `rc_trainer` V_H 0.55–0.70, Lennon Ch.5), `s_h_recommended_mm2`/`s_v_recommended_mm2` at the target-range midpoint, and `cg_aware: true` because a neutral point was available
- **AC-2 — Canard, tailless, V-tail and canard-like geometry are `not_applicable`, not an error**
  - **Given** an aircraft flagged `is_canard`, `is_tailless` or `is_v_tail`, or whose horizontal-tail AC sits ahead of the wing AC (`l_H ≤ 0`)
  - **When** `GET .../tail-sizing`
  - **Then** the response is 200 with `classification`, `classification_h` and `classification_v` all `"not_applicable"` and a `warnings` entry explaining why (e.g. *"Horizontal tail AC is ahead of wing AC (l_H ≤ 0) — canard-like configuration"*)
- **AC-3 — No context yet degrades gracefully**
  - **Given** an aircraft whose assumption context has never been computed
  - **When** `GET .../tail-sizing`
  - **Then** the response is 200 with `classification: "not_applicable"`, `cg_aware: false`, and a warning *"Recompute assumptions first to obtain reference geometry"* — not a 404 or 500
- **AC-4 — An unknown aeroplane is a 404**
  - **Given** a UUID that does not exist
  - **When** `GET .../tail-sizing`
  - **Then** the response is **404** *"Aeroplane {id} not found"*

**Confidence:** 🟢 CONFIRMED

## US-SIC-07 — Get a static-margin suggestion and apply it

**As an** RC/UAV designer, **I want** a concrete lever (move the wing, scale
the tail) to hit my target static margin, and to apply it with a dry-run
preview, **so that** I can fix a marginal or unstable CG without guessing at
a geometry change.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/sm-suggestion?at_cg=aft\|fwd` | — | `SmSuggestionResponse` |
| POST | `/aeroplanes/{aeroplane_id}/sm-suggestions/apply` | `SmApplyRequest{lever, delta_value, dry_run}` | `SmApplyResponse` |

**Acceptance criteria**

- **AC-1 — A suggestion offers a lever, with a mass-coupling caveat**
  - **Given** an aircraft whose static margin at the aft CG is below `target_static_margin`
  - **When** `GET .../sm-suggestion?at_cg=aft`
  - **Then** the response is 200 `SmSuggestionResponse` with `status: "suggestion"` and one or more `SmOption` entries (`wing_shift` in metres, `htail_scale` as a fraction e.g. `0.20` = +20%)
  - **And** when a `wing_shift` option is offered, `mass_coupling_warning` is present, noting the wing-mass CG shift is **not** modelled in the analytic formula (≈15% systematic error)
- **AC-2 — An aerodynamically unstable margin blocks saving**
  - **Given** `SM < 0.02`
  - **Then** `block_save: true` in the response
- **AC-3 — A dry run predicts without writing anything**
  - **Given** a `wing_shift` suggestion of `+0.01` m
  - **When** `POST .../sm-suggestions/apply {"lever": "wing_shift", "delta_value": 0.01, "dry_run": true}`
  - **Then** the response is 200 `SmApplyResponse{predicted_sm, dry_run: true, warnings}`; no geometry is written and no recompute is scheduled
- **AC-4 — Non-convergence and inapplicable configurations are rejected explicitly**
  - **Given** the same request with `dry_run: false`, and the iterative solve fails to converge within 3 iterations
  - **Then** the response is **409** `conflict` (gh-509, Scholz A6)
  - **And given instead** a canard/tailless/no-neutral-point aircraft, the request is **400** regardless of `dry_run`

**Confidence:** 🟢 CONFIRMED

## US-SIC-08 — Check takeoff/landing field lengths across launch and landing modes

**As a** hobbyist, **I want** the takeoff and landing distances for my
actual launch method (runway, hand launch, bungee, catapult) and landing
surface, **so that** I know whether my aircraft fits the field I fly from.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/field-lengths?takeoff_mode=&landing_mode=&v_throw_mps=&v_release_mps=&bungee_force_N=&stretch_m=` | Compute field lengths for the given launch/landing mode |

**Acceptance criteria**

- **AC-1 — Default runway takeoff and landing**
  - **Given** an aircraft with a computed context (`s_ref_m2`, `v_stall_mps`, mass all available)
  - **When** `GET .../field-lengths` (`takeoff_mode=runway`, `landing_mode=runway`, both defaults)
  - **Then** the response is 200 `FieldLengthRead` with `s_to_ground_m`, `s_to_50ft_m`, `s_ldg_ground_m`, `s_ldg_50ft_m`, `vto_obstacle_mps = 1.2·V_S`, `vapp_mps = 1.3·V_S`, and `mode_takeoff`/`mode_landing` echoing the request
- **AC-2 — A bungee launch needs and uses its own inputs**
  - **Given** `takeoff_mode=bungee`
  - **When** `GET .../field-lengths?takeoff_mode=bungee&v_release_mps=12&bungee_force_N=40&stretch_m=15`
  - **Then** the response is 200 with the takeoff distance computed from the bungee physics instead of a ground roll
- **AC-3 — A precondition failure is a 422 with a remediation sentence, before any computation**
  - **Given** an aircraft whose assumption context has no `v_stall_mps` yet
  - **When** `GET .../field-lengths`
  - **Then** the response is **422** — *"Stall speed (v_stall_mps) is not available. Trigger an assumption recompute first."* (same 422-for-`ServiceException` pattern as the matching chart); the equivalent missing-`s_ref_m2` and missing-mass cases raise their own worded messages
- **AC-4 — Known duplication: two sources for thrust, two landing models**
  - **Given** `MissionObjective.t_static_N` and the `t_static_N` design assumption hold different values (gh-548 moved this endpoint's reader off the assumption)
  - **Then** this endpoint's takeoff distance uses `MissionObjective.t_static_N` while the matching chart still reads the design assumption of the same name (🔴 two sources for one physical quantity)
  - **And** separately, this endpoint's landing model (Roskam §3.4 ground-roll) and the gh-477 energy-balance landing model published on `assumption_computation_context` (`landing_field_length_m`/`landing_surface_used`/`landing_field_sufficient`) are two independent, uncross-checked landing-distance calculations (🔴)

**Confidence:** 🟢 CONFIRMED

## US-SIC-09 — Manage flight profiles and assign one to an aircraft

**As an** RC/UAV designer, **I want** a reusable library of flight profiles
(goals, handling preferences, constraints) that I can assign to any
aircraft, **so that** the operating envelope and cruise speed reflect how I
actually intend to fly it.

**Endpoints exercised**

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/flight-profiles?type=&skip=&limit=` | — | `RCFlightProfileRead[]` |
| POST | `/flight-profiles` | `RCFlightProfileCreate` | `RCFlightProfileRead` |
| PATCH | `/flight-profiles/{profile_id}` | `RCFlightProfileUpdate` | `RCFlightProfileRead` |
| DELETE | `/flight-profiles/{profile_id}` | — | `{status, operation}` |
| PUT | `/aeroplanes/{aeroplane_id}/flight-profile/{profile_id}` | — | `AircraftFlightProfileAssignmentRead` |
| DELETE | `/aeroplanes/{aeroplane_id}/flight-profile` | — | `AircraftFlightProfileAssignmentRead` |

**Acceptance criteria**

- **AC-1 — Create, assign, and see it drive the cruise speed**
  - **Given** a new profile `{"name": "Weekend Trainer", "type": "trainer", "goals": {"cruise_speed_mps": 18}}`
  - **When** `POST /flight-profiles` then `PUT /aeroplanes/{id}/flight-profile/{profile_id}`
  - **Then** the responses are 201 then 200 `{aircraft_id, flight_profile_id}`
  - **And** subsequent operating-point generation and the assumption context use this profile's `cruise_speed_mps: 18` instead of falling back to `V_md`
- **AC-2 — No assignment substitutes best-glide cruise**
  - **Given** an aeroplane with no `flight_profile_id` set
  - **When** the assumption context is computed
  - **Then** `v_cruise_auto: true` and `v_cruise_mps` equals `v_md_mps` (best L/D = best range for a prop aircraft) — the `_default_profile()` display fallback's `cruise_speed_mps: 18` is never used to override `V_md` once a context exists (BR-MS7)
- **AC-3 — A profile still assigned cannot be deleted**
  - **Given** a profile currently assigned to an aircraft
  - **When** `DELETE /flight-profiles/{profile_id}`
  - **Then** the response is **409** `conflict` (BR-MS6, the global library's referential guarantee) — detaching first via `DELETE /aeroplanes/{id}/flight-profile`, then repeating the delete, succeeds
- **AC-4 — Cross-field validation exists on create but not on update**
  - **Given** a create payload with `max_bank_deg: 30` and `target_turn_n: 3.0` (exceeds `1/cos(30°) ≈ 1.155`)
  - **When** `POST /flight-profiles`
  - **Then** the response is **422** — *"target_turn_n is greater than what is achievable with max_bank_deg."*
  - **But** the same inconsistency introduced later via `PATCH` (lowering `max_bank_deg` below what an existing `target_turn_n` needs) is accepted with 200, because `RCFlightProfileUpdate` carries no equivalent model validator (🔴)

**Confidence:** 🟢 CONFIRMED

## Open questions 🔴

- **`mission_objectives.mission_type` has no FK to `mission_presets.id`.**
  Free text on both sides; an unknown mission type is a silent 200 no-op
  rather than a rejection.
- **Preset `power_to_weight` values are dimensionally inconsistent
  (BR-MS34).** Seven of the nine presets write a dimensionless 0.5–1.4
  T/W-shaped number into a field documented and consumed as W/kg; only the
  two glider-derived presets (`sailplane`, `slope_soarer`) write real W/kg
  (`0.0`).
- **`min_static_margin`/`max_static_margin`** are read by `stability_service`
  for the CG-range bounds but are absent from `VALID_PARAMETERS` and never
  seeded — the 5%/25% defaults are effectively hard-coded.
- **A third default for `target_static_margin`.** The seeded assumption
  default is `0.12`; `sm_suggestions.py` reads `ctx["target_static_margin"]`
  with an inline fallback of `0.10` if the key is absent — two different
  defaults for the same design choice.
- **`context_hash` on `MissionKpiSet`** is a 64-character SHA-256 the schema
  validates but nothing server-side stores or compares — a cache key with no
  cache.
- **`flight_profiles.py` handler docstrings are in German**, which surface
  verbatim in the generated OpenAPI of an otherwise English-only product.
- **Two independent landing-distance models** coexist with no cross-check:
  Roskam §3.4 ground-roll on `/field-lengths`, and the gh-477 energy-balance
  model published on `assumption_computation_context`.
- **An inverted computation-config alpha range** (`coarse_alpha_min_deg >
  coarse_alpha_max_deg`) is accepted with 200 and silently produces an empty
  sweep on the next recompute.
