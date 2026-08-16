# powertrain-sizing — Technical Design

> Use-case design, nested under the module [`powertrain`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Solution space — `powertrain_solution_space_service.py` 🟢

| Symbol | Line | Role |
|---|---|---|
| `G_DEFAULT` / `RHO_DEFAULT` | 64-65 | `9.80665` / `1.225`, both overridable |
| `CELL_V_NOM` / `CELL_V_SAG` | 68-69 | `3.7` / `3.5` V |
| `_PHASE1_PROP_DIAMETER_M` | 72 | 🟢 removed — KV from the APC polar database (`Q-PT-3`) |
| `_HYPERBOLA_SAMPLES` | 75 | `40` |
| `_p_aero(rho, v, mass, g, cd0, e, ar, s_ref)` | 83 | level-flight aerodynamic power |
| `_p_elec(p_aero, η_prop, η_motor, η_esc)` | 108 | battery power |
| `_per_cell(...)` | 116 | the per-cell-count spec dict |
| `_build_hyperbola(i_peak, cap_floor, n=40)` | 172 | the feasible region |
| `_catalog_motor_match` / `_battery_` / `_esc_` | 192-231 | availability flags |
| `compute_solution_space(db, plane, assumptions)` | 239 | entry point |

### Catalog sweep — `powertrain_sizing_service.py` 🟢

| Symbol | Line | Role |
|---|---|---|
| `_DEFAULT_CD0 / _E_OSWALD / _AR / _S_REF_M2` | 44-47 | `0.03 / 0.8 / 8.0 / 0.5` |
| `_required_power_w` | 55 | **raises `NotImplementedError` by design** |
| `_evaluate_motor_battery_combo` | 230 | one candidate or `None` |
| `_find_matching_esc` | — | 🟢 all-of gate on peak current (`Q-PT-1`) |
| `_compute_confidence` | — | `min(t/t_target, 1.0)` |
| `_resolve_aero_params` | — | the 3-tier priority with warnings |
| `size_powertrain(db, uuid, request)` | 275 | entry point |

### Shared physics — `endurance_service.py` 🟢

```
_power_required(rho, v, cd0, e, ar, mass, s_ref, eta_total) -> W
    v <= 0            -> inf
    q   = ½·ρ·v²
    C_L = m·G / (q·s_ref)          G = 9.80665
    C_D = cd0 + C_L²/(π·e·ar)
    return q·s_ref·C_D·v / eta_total
DEFAULT_ETA_PROP / MOTOR / ESC = 0.65 / 0.85 / 0.94
```

### REST 🟢

| Method | Path |
|---|---|
| GET | `/aeroplanes/{aeroplane_id}/powertrain/solution-space` (15 optional query params) |
| POST | `/aeroplanes/{aeroplane_id}/powertrain/sizing` |
| GET | `/aeroplanes/{aeroplane_id}/powertrain/sizing-modal-params` |

## Main Flow

### F1 — Solution space (`compute_solution_space`, l.239-345) 🟢

```
ctx = plane.assumption_computation_context or {}

# 1. aero invariants — each fallback appends a NAMED warning (ADR 0004/0012)
s_ref_m2  = ctx["s_ref_m2"]                        or 0.25   + warning
e_oswald  = ctx["e_oswald"]                        or 0.75   + warning
ar        = ctx["aspect_ratio"]                    or 7.0    + warning
v_cruise  = ctx["v_cruise_mps"] or ctx["v_md_mps"] or 15.0   + warning

# 2. mass and cd0 — cd0 is the only two-tier read
mass = get_effective_assumption(db, plane.id, "mass")  or PARAMETER_DEFAULTS 1.5 + warning
cd0  = ctx["cd0"]  →  get_effective_assumption(…, "cd0")  →  0.03 + warning

# 3. mission validation
t_target_min <= 0        -> ValidationDomainError    (422)
v_top = assumptions.v_top_mps or 1.4·v_cruise
v_top <= v_cruise        -> ValidationDomainError    (422)

# 4. per η (mid, lo, hi) and per cell count S
P_cruise_elec = _p_elec(_p_aero(…, v_cruise), η_prop, η_motor, η_esc)
P_top_elec    = _p_elec(_p_aero(…, v_top),    η_prop, η_motor, η_esc)
E_Wh          = P_cruise_elec · (t_target_min/60) / dod
row           = _per_cell(S, P_top_elec, E_Wh, esc_margin, c_margin,
                          load_rpm_factor, v_top, prop_pd)
motor_peak_shaft_w = _p_aero(…, v_top)    / η_prop_mid
motor_cont_shaft_w = _p_aero(…, v_cruise) / η_prop_mid

# 5. decoration
feasible_regions = _build_hyperbola(i_peak, cap_floor)
shopping_specs   = one per row
has_*_match      = the three catalogue probes
```

The three-fold evaluation is what produces the `_lo` / `_hi` band, and the
`SolutionRow` docstring records the inversion: `_lo` uses `eta_prop_hi`, because
a more efficient propeller needs *less* power. 🟢

### F2 — `_per_cell` (l.116-169) 🟢

```
v_nom  = S · 3.7
v_sag  = S · 3.5
i_peak = p_top_elec_w / v_sag            # p_top_elec is ALREADY battery power
                                         # dividing again by η double-counts (gh-978)
cap_mah = energy_wh / v_nom · 1000
raw_c   = i_peak / (cap_mah/1000)  if cap_mah > 0 else inf
c_min   = raw_c · c_margin
esc_min = i_peak · esc_margin

prop_d     from the APC polar database (Q-PT-3)  🟢
rpm_target = (v_top_mps / (prop_d · prop_pd)) · 60
kv_approx  = rpm_target / (v_nom · load_rpm_factor)   if v_nom > 0 else 0.0
```

The `v_nom > 0` guard is defensive only — `S ≥ 1` makes it unreachable, and the
code says so. 🟢

### F3 — `_build_hyperbola` (l.172-184) 🟢

```
cap_floor <= 0 or i_peak <= 0  ->  ([], [])
cap_max = cap_floor · 4
caps    = 40 points linearly spanning [cap_floor, cap_max]
c_rates = [i_peak / (c/1000) for c in caps]
```

The curve is the *iso-current* line: every point on it draws the same peak
current, so the designer can trade capacity against C-rate along it. 🟡

### F4 — Catalogue availability (l.192-231) 🟢

Three independent full-table scans, each returning a boolean on the first
match:

```
motor:   any max_power_w | max_continuous_power_w  >= motor_peak_SHAFT_w
battery: any capacity_mah >= cap_floor AND (c_rating | discharge_c) >= c_min
esc:     any max_current_a | continuous_current_a  >= esc_min_a
```

The motor comparison is shaft-vs-shaft **by construction** — the docstring at
`:195-197` explains that `motor_shaft_peak_w` is `P_aero/η_prop`, not `P_aero`,
precisely so the catalogue rating is comparable. 🟢

### F5 — Catalog sweep (`size_powertrain`, l.275-318) 🟢

```
aeroplane by UUID                                   missing -> NotFoundError (404)
motors    = components WHERE type = 'brushless_motor'
batteries = components WHERE type = 'battery'
escs      = components WHERE type = 'esc'

not motors or not batteries:
    return PowertrainSizingResponse([], warnings naming each missing category)

cd0, e, ar, s_ref, warnings = _resolve_aero_params(request, ctx)   # 3-tier, gh-960

for motor in motors:
  for battery in batteries:
      candidate = _evaluate_motor_battery_combo(...)   # None -> skipped
      candidates.append(candidate)

candidates.sort(key=confidence, reverse=True)
return candidates[:10], warnings
```

### F6 — `_evaluate_motor_battery_combo` (l.230-273) 🟢

```
capacity_mah <= 0 or voltage <= 0        -> None
total_mass = airframe + motor.mass_g/1000 + battery.mass_g/1000
             ← propeller weight_g IS included (Q-PT-2)  🟢
η_total    = η_prop · η_motor · η_esc

P_cruise   = _combo_required_power_w(...)   →  endurance_service._power_required
I_cruise   = P_cruise / voltage   (999 when voltage is 0)
max_current_draw_a and I_cruise > it      -> None

t_flight_h   = (cap_Ah / I_cruise) · 0.8            ← 80 % usable
t_flight_min = t_flight_h · 60
esc          = all-of gate on PEAK current (Q-PT-1) 🟢
confidence   = min(t_flight_min / target, 1.0)      ← gh-992, continuous

PowertrainCandidate(..., estimated_top_speed_ms = round(request.target_top_speed_ms, 1))
                                                    ← ECHOES the input 🟡
```

### F7 — Sizing modal 🟢

Same context-with-warnings pattern for `cd0` and `s_ref_m2`; motors sorted by
name with `efficiency_pct` defaulting to 85; `eta_prop 0.65`, `eta_motor 0.85`,
`altitude_m 0.0`. The KV shown is the **raw** `kv_rpm_per_volt` — the single
documented exception to BR-65. 🟢

## Alternative Flows

- **Empty computation context:** four warned fallbacks (`s_ref`, `e`, `AR`,
  `V_cruise`) plus two more for `mass` and `cd0`; the request still returns 200.
  🟢
- **`cd0` present in the context but zero/negative:** falls through to the design
  assumption, then to `0.03`. 🟢
- **`t_target_min ≤ 0` / `v_top ≤ v_cruise`:** `ValidationDomainError` → 422,
  mapped through `HTTP_422_UNPROCESSABLE_CONTENT` on this router only. 🟡
- **`v ≤ 0` inside `_p_aero`:** returns `inf` rather than raising; the row's
  numbers become `inf` and serialise as invalid JSON. 🟡 Unreachable through the
  API (`v_cruise` falls back to 15 and `v_top > v_cruise`), but the guard is a
  return, not a raise.
- **`η ≤ 0` inside `_p_elec`:** likewise `inf`; the schema bounds
  (`ge=0.01`) prevent it from the API. 🟡
- **`cap_mah = 0`:** `raw_c` becomes `inf`; the row is still emitted. 🟡
- **Degenerate hyperbola:** two empty lists. 🟢
- **Empty component catalogue (solution space):** all three `has_*_match` flags
  are `false`; the required specs are unaffected. 🟢
- **Empty motor or battery catalogue (sweep):** `recommendations: []` plus a
  warning naming the remedy. 🟢
- **No ESC fits:** the candidate is returned with `esc_id = None`, unflagged. 🟡
- **Battery with no resolvable voltage:** the four-key walk ends at `11.1 V`;
  only a literal `voltage ≤ 0` skips the combination. 🟢
- **Motor or battery with `mass_g = NULL`:** the mass term is missing from
  `total_mass`. 🟡 Behaviour not explicitly guarded.
- **Unknown aeroplane:** `NotFoundError` → 404 on all three routes. 🟢

## Dependencies

- **`aero-analysis` (gh-924 context, ADR 0004)** — `s_ref_m2`, `e_oswald`,
  `aspect_ratio`, `v_cruise_mps` / `v_md_mps`, `cd0`. The **single source**; both
  paths warn on every fallback rather than defaulting quietly.
- **`mission-and-sizing`** — `design_assumptions_service.get_effective_assumption`
  for `mass` and `cd0`; `PARAMETER_DEFAULTS`; and
  `endurance_service._power_required` + the three efficiency constants.
- **[`cots-powertrain-components`](../cots-powertrain-components/design.md)** —
  the motor / battery / ESC rows and their `specs`. Note the **three distinct
  key vocabularies** between this use case, the solution space's matchers and
  `BatterySpec`.
- **`aeroplane-core`** — the aeroplane row (resolved by UUID; the sweep reads its
  `assumption_computation_context`).
- **No NumPy dependency in the solution space** — it is plain Python `math`
  (`math.pi`, `math.sqrt`), which is what keeps it in the CI fast tier. 🟢

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Two sizing questions get two services rather than one parametrised one | the two modules | 🟢 |
| The solution space is deliberately dependency-free so it runs in the fast tier | module docstring | 🟢 |
| Battery current is derived from battery power, without a second efficiency division | `_per_cell:129-139`; gh-978 | 🟢 |
| Motor requirements are published as shaft power for catalogue comparability | `_catalog_motor_match:195-197` | 🟢 |
| Uncertainty is expressed as a **band** over η_prop rather than a single number | `SolutionRow` docstring; BR-PT25 | 🟢 |
| The feasible region is an iso-current hyperbola, sampled for plotting | `_build_hyperbola` | 🟢 |
| Every defaulted input produces a named warning instead of a silent value | `compute_solution_space:265-325`; ADR 0012 | 🟢 |
| The drag polar lives in exactly one place; the local shim raises rather than duplicating it | `_required_power_w:55`; BR-PT30 | 🟢 |
| Confidence is continuous so near-misses stay visible | gh-992 | 🟢 |
| An empty catalogue is explained, not returned bare | gh-992 | 🟢 |
| The modal shows raw KV — the one deliberate exception to the gear-aware rule | `powertrain_sizing_modal_service` | 🟢 |
| KV is approximated from a fixed 0.30 m propeller pending #615 | `_PHASE1_PROP_DIAMETER_M:72` | 🟢 removed (`Q-PT-3`) (approximation) |
| 🟢 No RC-typical defaults remain to unify (`Q-PT-8`) | previously `0.03/0.75/7.0/0.25` vs `0.03/0.8/8.0/0.5` | 🟢 (a 🔴 inconsistency) |

## Internal State

None. Both services are read-only: they resolve the aeroplane, read the context
and the catalogue, compute, and return. Nothing is persisted, nothing is cached,
and no event is published. 🟢

The only state that affects the answer is external — the gh-924 context (written
by `aero-analysis`), the `mass` assumption (written by `mass-and-balance`) and
the component catalogue. A stale context therefore produces a stale sizing with
**no** warning, because the fallback warnings only fire when a value is
*missing*, not when it is *old*. 🟢 Staleness becomes detectable (`Q-PT-8`).

## Observability

- `warnings[]` on both responses is the primary channel and is unusually
  thorough: one entry per defaulted input, per missing catalogue category. 🟢
- `logger.exception` on the defensive 500 in the solution-space and modal
  routers; the sizing router does **not** log. 🟢 One envelope and one handler (`Q-CC-3`).
- `has_motor_match` / `has_battery_match` / `has_esc_match` give the UI a
  machine-readable "you cannot buy this yet" signal. 🟢
- Nothing counts how often a sweep returns zero candidates, how often the
  Phase-1 KV approximation is used, or how stale the context was. 🟡

## Risks and Gaps

- 🟢 **The first-match rule is replaced by an all-of gate on *peak* current** (`Q-PT-1`, expert consensus endorsed by the maintainer), so the choice stops depending on query order.
  `db.query(...).all()` has no `ORDER BY`, so the recommended ESC is arbitrary
  and can differ between two databases holding the same catalogue.
- 🟢 **The selected propeller's `weight_g` is added to `total_mass`** (`Q-PT-2`, expert consensus endorsed by the maintainer). Motor and battery
  masses are added to `airframe_mass_kg`; the propeller's — known since
  gh-1000/1017 — is not.
- 🟢 **KV comes from the APC polar database; the fixed `_PHASE1_PROP_DIAMETER_M` is removed** (`Q-PT-3`) — the blocker is resolved. Previously a fixed 0.30 m propeller: while the complete
  APC database sits in the same service layer.
- 🟡 **`estimated_top_speed_ms` echoes the request** — the field name promises a computed achievable speed. The field name promises a
  computed achievable speed and returns the target verbatim.
- 🟢 **There are no RC-typical defaults left to unify** (`Q-PT-8`), and staleness becomes detectable. Previously the two paths disagreed: — `e 0.75 / AR 7.0 /
  S 0.25` in the solution space versus `e 0.8 / AR 8.0 / S 0.5` in the sweep —
  so the same context-less aircraft is sized differently by the two endpoints.
- 🟢 **The Pydantic spec-model spellings are canonical; the importers normalise** (`Q-PT-4`, maintainer-answered). Previously three vocabularies: `c_rate` (BatterySpec) vs `c_rating` /
  `discharge_c` (solution space) vs `continuous_current_a` /
  `max_continuous_a` (sweep). A valid battery or ESC can be invisible to one
  consumer.
- 🟢 **Staleness becomes detectable** (`Q-PT-8`). Previously indistinguishable: The warnings
  fire on *missing* values only; nothing checks whether the context predates the
  current geometry.
- 🟡 **`inf` can reach the response** through `_p_aero`, `_p_elec` or a zero
  capacity, and none of these routers uses `NonFiniteSafeJSONResponse`.
- 🟢 **One error envelope and one handler** (`Q-CC-3`), so per-router catch-alls disappear.
- 🟡 **The sweep is an unbounded cross-product.** A large catalogue is
  `O(motors × batteries)` with a linear ESC scan per pair, all in one request.
- 🟡 **A candidate with no ESC is unflagged**, so the UI cannot distinguish
  "no ESC needed" from "no ESC fits".
- 🟡 **A `NULL` `mass_g` on a motor or battery silently drops that mass term**
  from the total rather than rejecting the combination.
- 🟡 **`HTTP_422_UNPROCESSABLE_CONTENT` vs `..._ENTITY`** — the same code under
  two spellings across the module's routers.
</content>
