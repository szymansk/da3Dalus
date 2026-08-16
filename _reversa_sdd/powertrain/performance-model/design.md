# performance-model — Technical Design

> Use-case design, nested under the module [`powertrain`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Input schemas — `app/services/powertrain_performance.py` 🟢

| Schema | Line | Fields → derived properties |
|---|---|---|
| `MotorSpec` | 82 | `kv_rpm_per_volt (>0)`, `gear_ratio (>0)`, `efficiency_pct (0-100)`, `cells_lipo_max (≥1)`, `io_no_load_a`, `max_current_a`, `continuous_current_a`, `rm_ohm` → `output_kv`, `kv_si`, `eta_motor`, `max_electrical_power_w`, **`uses_qprop_model`** |
| `BatterySpec` | 174 | `cells (≥1)`, `capacity_mah (>0)`, `c_rate` → `nominal_voltage_v`, `max_continuous_discharge_w`, `max_current_a` |
| `PowertrainPerformanceRequest` | 210 | + `propeller_diameter_in`, `polar_samples[]`, `v_min_ms (≥0)`, `v_max_ms (>0, > v_min)`, `n_points (1-500)`, `altitude_m`, `throttle (0-1]` |
| `PerformanceSample` | 234 | `velocity_ms`, `thrust_n (≥0)`, `p_shaft_w (≥0)`, `eta_prop (0-1)`, `J (≥0)`, `rpm (≥0)`, `estimated` |
| `PowertrainPerformanceResponse` | 252 | `samples[]`, `p_available_w`, `warnings[]`, `notes` |
| `QpropOperatingPoint` | 426 | `rpm`, `current_a`, `torque_nm`, `p_shaft_w`, `eta_motor` |

### Functions 🟢

| Symbol | Line | Role |
|---|---|---|
| `interpolate_ct_cp_pe` | 278 | `J → (Ct, Cp, Pe, extrapolation_warning)` |
| `_air_density` | 346 | `1.225·exp(−h/8500)` |
| `_prop_torque_demand` | — | `Q_prop(n) = Cp·ρ·n²·D⁵/(2π)` at `J = V/(n·D)` |
| the bisection | 569 | 80 iterations over the torque residual |
| `compute_prop_operating_point` | — | one `QpropOperatingPoint` at a given V |
| `compute_performance_curve` | — | the public entry point |

### Constants 🟢

`RHO_SEA_LEVEL = 1.225` · `G = 9.80665` · `_VOLTS_PER_LIPO_CELL = 3.7` ·
`_DEFAULT_ETA_MOTOR = 0.85` · bisection iterations `80`.

### REST 🟢

`POST /aeroplanes/{aeroplane_id}/powertrain/performance` — see
[`../contracts.md`](../contracts.md). The endpoint resolves the three component
references itself and raises `HTTPException` **directly** from its helpers.

## Main Flow

### F1 — Endpoint resolution 🟢

```
aeroplane by UUID                      missing -> 404   (data never read, BR-PM6)
motor   = db.get(ComponentModel, motor_component_id)
          None or type != "brushless_motor"   -> 404
battery = db.get(ComponentModel, battery_component_id)
          None or type != "battery"            -> 404
polar   = db.get(PropellerPolarModel, propeller_polar_id)
          None                                 -> 404
samples = SELECT … WHERE propeller_id = ?
          empty                                -> 422 "has no sample rows"

_resolve_motor:   kv_rpm_per_volt | kv   missing -> 422 naming id and name
                  cells_lipo_max         missing -> 422
_resolve_battery: cells, capacity_mah    missing -> 422
```

Each helper raises `HTTPException` rather than a `ServiceException`, so these
responses bypass `_raise_http`. 🟡

### F2 — Interpolation (`interpolate_ct_cp_pe`, l.278) 🟢

```
rows sorted by J
J_clamped = clip(J, J_min, J_max)
if J != J_clamped:  extrapolation_warning = True

Ct = np.interp(J_clamped, Js, Cts)
Cp = np.interp(J_clamped, Js, Cps)
Ct = max(Ct, 0.0)                       # negative tail discarded (BR-PT17)
Pe = (Ct * J_clamped / Cp) if (Cp > 0 and J_clamped > 0) else 0.0
```

`Pe` is **recomputed**, never read from the stored column. Callers that know the
RPM pre-filter the rows to the nearest RPM group first (BR-PT19); the J-only
form merges all groups because `Ct(J)` is nearly RPM-independent for standard
APC props. 🟡

### F3 — Model A, the fixed-RPM chain (gh-615) 🟢

```
V_bat      = cells · 3.7                    # LOADED nominal, not 4.2 peak
output_kv  = kv_rpm_per_volt / (gear_ratio or 1)
n          = output_kv · V_bat · throttle   # RPM is FIXED for the whole sweep
η_motor    = efficiency_pct/100  else 0.85

P_elec_max = min( max_current_a · 3.7 · cells_lipo_max ,
                  (cap_mAh/1000) · C_rate · (cells·3.7) )
             both unknown -> V_bat · 100 A  + warning
P_shaft_max = P_elec_max · η_motor
             < 0.1 W      -> infeasibility warning

for V in linspace(v_min, v_max, n_points):
    J   = V / (n · D)
    Ct, Cp, Pe = interpolate at J (nearest-RPM group)
    T   = max(Ct · ρ · n² · D⁴, 0)
    P   = clip(Cp · ρ · n³ · D⁵, 0, P_shaft_max)
    η   = clip(Pe, 0, 1)
    estimated = True
```

The defining property — and the reason `estimated` exists — is that **RPM does
not respond to load**. The model caps power after the fact rather than solving
for the operating point. 🟢

### F4 — Model B, the QPROP torque balance (gh-1006) 🟢

```
Kv_si   = output_kv · 2π/60        [rad/s per V]      Kt = 1/Kv_si  [Nm/A]
V_term  = V_bat · throttle
I₀      = io_no_load_a or 0

per velocity point:
    residual(n) = Q_motor(I(n)) − Q_prop(n)
        ω          = 2π·n/60
        I(n)       = (V_term − ω/Kv_si) / Rm            back-EMF
        Q_motor    = (I − I₀)/Kv_si
        Q_prop(n)  = Cp·ρ·n²·D⁵/(2π)     with Cp interpolated at J = V/(n·D)

    bracket:  rpm_hi = free-run  V_term·Kv_si·60/2π     (I → 0)
              rpm_lo = the back-EMF floor implied by max_current_a
    r_lo ≤ 0  -> clamp to rpm_lo
    r_hi ≥ 0  -> clamp to rpm_hi
    otherwise -> BISECTION, 80 iterations

    η_motor = (V_term − I·Rm)(I − I₀) / (V_term·I)      clipped to [0,1]
    P_shaft = Q·ω                                       estimated = False
```

Because the balance is solved **per velocity point**, RPM rises as the propeller
unloads with forward speed — the physical behaviour Model A cannot express. 🟢

### F5 — Degenerate handling 🟢

| Condition | Response |
|---|---|
| `prop_rpm ≤ 0` | all-zero curve + *"Computed RPM is zero — check motor KV and battery voltage"* |
| both power limits unknown | `V_bat × 100 A` + warning |
| `P_shaft_max < 0.1 W` | infeasibility warning |
| `J` outside the dataset | clamped + `extrapolation_warning` → a human-readable warning naming the sweep |
| `Cp ≤ 0` or `J = 0` | `Pe = 0` (silently — it is the physical value at static thrust) |
| degenerate QPROP bracket | clamped to the bracket endpoint |

Nothing in this list raises. That is the module's ADR 0012 posture: an
unanswerable configuration produces an honest curve and a warning, not a 500.
🟢

## Alternative Flows

- **Wrong component type for the id:** 404, not 422 — the endpoint treats a
  type mismatch as "not found among motors". 🟡
- **Motor with `kv` instead of `kv_rpm_per_volt`:** accepted — the resolver
  reads `specs.get("kv_rpm_per_volt") or specs.get("kv")`. 🟢
- **Battery whose C-rate is stored as `c_rating` / `discharge_c`:**
  `BatterySpec` reads only `c_rate`, so the battery power limit is `None` and
  the `min()` falls through to the motor limit — or to the 100 A fallback. 🟡
  Silent.
- **`gear_ratio` absent or 0:** treated as 1. 🟡
- **`efficiency_pct` absent:** `0.85`. 🟢
- **`throttle` < 1:** scales `V_terminal` in both models, so Model A's RPM
  scales linearly while Model B re-solves. 🟢
- **`n_points = 1`:** a single sample at `v_min`. 🟡 Legal per the schema.
- **`altitude_m` large:** density falls exponentially; the divergence from
  `asb.Atmosphere` grows. 🟢 One shared ISA helper (`Q-PT-9`).
- **Polar rows spanning several RPM groups:** the RPM-aware callers filter to
  the nearest group; a tie is resolved by the implementation's ordering. 🟡

## Dependencies

- **[`propeller-polars`](../propeller-polars/design.md)** — the sample rows.
  This use case reads `J`, `Ct`, `Cp` and `rpm` and **ignores** the stored `Pe`,
  `Torque_Nm` and `Thrust_N`.
- **[`cots-powertrain-components`](../cots-powertrain-components/design.md)** —
  the motor and battery `specs`; the key names are read here and are not unified
  with the sizing consumers (BR-CC4).
- **`aeroplane-core`** — only to resolve and 404 on the aeroplane UUID.
- **NumPy** — `linspace`, `interp`, `clip`. Nothing else.
- **ADR 0012** — the warn-don't-raise posture and the extrapolation clamp.
- **ADR 0017** — no heavy dependency: the route runs in the CI fast tier.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Two motor models coexist, selected by whether `rm_ohm` is present | `MotorSpec.uses_qprop_model`; BR-PT13 | 🟢 |
| The response tells the caller which model ran, per sample and in prose | `estimated`, `notes` | 🟢 |
| Pack voltage uses the loaded 3.7 V, not the 4.2 V peak | `:50`; BR-65 | 🟢 |
| KV is gear-aware everywhere except the sizing modal | `output_kv`; BR-PM1 | 🟢 |
| `η_prop` is interpolated per operating point, never a constant | BR-66 | 🟢 |
| `Pe` is recomputed from `Ct·J/Cp` rather than read | `interpolate_ct_cp_pe:278` | 🟢 |
| Extrapolation is clamped **and reported** | idem; ADR 0012 | 🟢 |
| `Ct` is clamped at 0 — a windmilling model is wanted (`Q-PT-10`) | idem | 🟡 |
| Torque is derived from power because the stored column is coarse | BR-PT18 | 🟢 |
| The QPROP solve is a fixed-iteration bisection, not a Newton solve | `:569` | 🟢 |
| Degenerate brackets clamp instead of raising | the two clamp branches | 🟢 |
| Every degenerate configuration returns a curve plus a warning | BR-PT20 | 🟢 |
| Air density comes from one shared ISA helper (`Q-PT-9`) | `:346` | 🟢 |
| Component resolution raises HTTP directly from the endpoint helpers | `powertrain_performance.py` (endpoint) | 🟢 (a 🟡 layering break) |
| The aeroplane UUID anchors the request without contributing data | endpoint docstring | 🟢 |

## Internal State

None. The use case is a pure function of `(motor specs, battery specs, polar
samples, sweep parameters)`. Nothing is persisted, nothing is cached, and two
identical requests produce byte-identical responses. 🟢

The only *stateful* dependency is the polar dataset, which changes only through
[`propeller-polars`](../propeller-polars/design.md)'s importers — so a curve is
reproducible as long as the snapshot version is pinned. 🟢

## Observability

- `warnings[]` on the response is the primary channel: extrapolation, zero RPM,
  the 100 A fallback and infeasibility all surface there. 🟢
- `notes` names the model that produced the curve. 🟢
- `estimated` is the machine-readable version of the same fact, per sample. 🟢
- 🟢 One error envelope and one handler (`Q-CC-3`).
- Nothing counts how often a curve is extrapolated, how often the 100 A fallback
  fires, or how often the QPROP path is taken — the last of which would
  immediately reveal that it is dormant for the shipped catalogue. 🟢 Dormant by design (`Q-PT-6`).

## Risks and Gaps

- 🟢 **`Rm` is not a prerequisite — the fixed-RPM model stays the default** (`Q-PT-6`). Investigated and closed: D-Power publishes no `rm_ohm`, and its PDFs are one-row-per-motor spec tables. Model B stays dormant by design: No seeded motor carries `rm_ohm`, so every shipped
  curve comes from the fixed-RPM approximation. The better model exists,
  is tested, and never runs in production.
- 🟢 The Pydantic spec-model spellings are canonical; importers normalise (`Q-PT-4`). `BatterySpec` reads `c_rate`
  while the catalogue matchers read `c_rating` / `discharge_c`. A battery
  imported under the wrong spelling silently loses its power limit here.
- 🟡 **Windmilling drag is a genuine gap, not deliberate scope** (`Q-PT-10`, expert consensus endorsed by the maintainer) — a windmilling model is wanted. Today `Ct` clamped at 0 means a power-off — `Ct` clamped at 0 means a power-off
  descent reports zero propeller drag, which will mislead any glide or descent
  analysis built on these curves.
- 🔴 **Air density diverges from the aero stack.** `1.225·exp(−h/8500)` here
  versus `asb.Atmosphere` in `aero-analysis`; the two disagree above a few
  hundred metres, and nothing reconciles them.
- 🔴 **The router does not log its 500s**, so an unexpected exception in the
  physics leaves no server-side trace.
- 🟡 **Endpoint helpers raise HTTP directly**, bypassing the domain-exception
  layer every other service in the repository uses — a layering break that makes
  the same failures untestable at the service level.
- 🟡 **A wrong component type reports 404, not 422**, which reads as "the id
  does not exist" when the id exists and is simply the wrong kind of part.
- 🟡 **The nearest-RPM-group choice is implicit.** A polar whose RPM blocks
  straddle the computed RPM has no documented tie-break.
- 🟡 **`n_points = 1` is legal**, producing a "curve" of one point.
- 🟡 **The aeroplane requirement is decorative** — the endpoint 404s on an
  unknown UUID while reading no aeroplane data, so the same computation cannot
  be requested without an aircraft.
</content>
