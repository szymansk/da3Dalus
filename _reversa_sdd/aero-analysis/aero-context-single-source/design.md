# aero-context-single-source — Technical Design

> Focuses on HOW this use case is built, read from the legacy code.
> Parent module design: [`../design.md`](../design.md).
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `recompute_assumptions` | `(db, aeroplane_uuid)` | `None` — writes the context | **sync**; async callers must `asyncio.to_thread` 🟢 |
| `_parasite_cd0` | `(cd_total, cl, ar, e)` | `float \| None` | `None` when the inputs are not sane or the result ≤ 0 🟢 |
| `_fit_parabolic_polar` | `(cl[], cd[], ar, cl_max, cd0_stability)` | `ParabolicPolar` | six gates 🟢 |
| `_fit_parabolic_polar_with_refinement` | `(…, config)` | `ParabolicPolar` | retries two gates, max 2 attempts 🟢 |
| `_e_oswald_from_sweep` | `(cl[], cdi[], q, s_ref, ar)` | `float \| None` | clipped to `0 < e ≤ 1.10` 🟢 |
| `_coarse_alpha_sweep` / `_fine_sweep_cl_max` | `(airplane, config, …)` | arrays | **one** `AeroBuildup.run()` each 🟢 |
| `_extract_cl_alpha_from_linear_sweep` | `(alpha[], cl[])` | `(cl_alpha, alpha_0) \| (None, None)` | `R² ≥ 0.995` gate 🟢 |
| `_picard_iterate_speed` | `(v0, re_table, solver_fn)` | `float` | exactly one pass 🟢 |
| `apply_turbulator_delta_to_cd0` | `(cd0, sections, s_ref, symmetric)` | `(cd0_adjusted, raw_cd0)` | area-weighted, ×2 symmetric 🟢 |
| `_cache_context` | `(db, aeroplane, context)` | `None` | the **only** writer of the JSON column 🟢 |
| `build_re_table` | `(samples, v_cruise, v_max, mac)` | `list[PolarReTableRow]` | re-bins existing samples 🟢 |
| `lookup_cd0_at_v` / `lookup_e_oswald_at_v` | `(table, v)` | `float` | `cd0` linear in `1/sqrt(Re)`; `e` a constant mean 🟢 |

HTTP surface (owned by `mission-and-sizing`'s design-assumptions router, read
here): `GET /aeroplanes/{id}/assumptions/computation-context`,
`POST /aeroplanes/{id}/recompute` (202),
`GET /aeroplanes/{id}/assumptions/recompute-status`. 🟢

## Main Flow — the 13-step pipeline

```
0.  build the ASB airplane; skip SILENTLY if it has no wings
1.  main_wing = argmax(wing.area())
        s_ref / c_ref / b_ref  OVERRIDDEN from it            # gh-788 / F1 bug class
2.  seed_defaults()  +  _load_or_create_config()             # both idempotent
3.  _stability_run_at_cruise
        → x_np, MAC, cd0_parasite, S_ref                     # AeroBuildup
4.  _coarse_alpha_sweep         → stall_alpha = argmax(CL)   # ONE solver call
5.  _fine_sweep_cl_max          → CL_max, cl[], cd[], v[], cdi[]   # ONE solver call
6.  cg_x = x_np − target_SM · MAC     → written back as CALCULATED  (BR-28)
7.  parabolic fit (+ auto-refinement) → cd0_fit, e_fit, R²
8.  e from AeroBuildup Trefftz        → e_oswald_ab           (preferred)
9.  per-config polars {clean, takeoff, landing}               # each in its own try
10. Re-band table (gh-493)            → polar_re_table
        + gh-924 backfill of fallback rows
11. V-speeds, CG / loading / stability envelopes, landing field length
12. _cache_context()  →  aeroplanes.assumption_computation_context
```

Each step is guarded by the three-layer error policy described below; the
pipeline never writes a partial context.

## Algorithms

### Parasite CD0 🟢

```
CD_induced = CL² / (π · AR · e)          # e = AeroBuildup's oswalds_efficiency
CD0        = CD_total − CD_induced
guard: only when CL, AR and e are finite and positive AND CD0 > 0, else None
```

Rationale (Anderson §6.7.2): a cambered wing lifts at α = 0, so `coefficients.CD`
at the cruise point already contains induced drag. Publishing it as CD0
double-counts and collapses `(L/D)max` — the measured regression is 17 instead
of 24 on a high-AR glider.

### `(L/D)max` 🟢

```
E_max       = ½ · sqrt(π · AR · e / CD0)          # Scholz eq. 5.39
CL_at_E_max = sqrt(CD0 · π · AR · e)
```

Fallback: the measured `argmax(CL/CD)` over the sweep, **only** when `CD0` or `e`
is unavailable. The raw argmax mixes Reynolds bands and lands on a spurious
high-CL sample (eHawk: 18.8 @ CL 0.98 vs 23.4 @ CL 0.55).

### Parabolic fit and the six gates 🟢

```
window : CL ∈ [max(0.10, 0.10 · CL_max), 0.85 · CL_max]
fit    : CD = CD0 + k · CL²      by OLS
e      : 1 / (π · AR · k)

gate                     accept                                    category
insufficient_points      ≥ 6 samples in the window (or AR ≤ 0)     sweep
non_monotonic_polar      dCD/d(CL²) ≥ −1e-6                         data
negative_slope_k         k > 0                                      design
non_positive_cd0         cd0_fit > 0                                consistency
unphysical_e_oswald      0.4 < e ≤ 1.0                              design
cd0_stability_mismatch   |cd0_fit − cd0_stability| / cd0_stability ≤ 0.20   consistency
```

`PolarRejection` carries `gate`, `category`, `fitted_value`, `threshold`,
`hint`, and a **model validator enforces the canonical gate→category pair** so a
rejection cannot be mis-categorised into visibility. Only `design` is shown to
the user (ADR 0012).

Refinement (`_fit_parabolic_polar_with_refinement`):

```
refinable = {insufficient_points, non_monotonic_polar}
per attempt (max 2):  alpha_step /= 2 ;  margin *= 1.5
auto_refined = True only when an attempt actually produced a fit
thresholds:  UNCHANGED, always
```

### Oswald provenance 🟢

```
1. aerobuildup_trefftz   e from AeroBuildup's own oswalds_efficiency   ← preferred
2. fit                   e = 1/(π·AR·k) from the parabolic fit
3. fallback              e_oswald_effective = 0.8

derived-from-sweep form:
    e   = CL² / (π · AR · CDi)     at the (L/D)max sample
    CDi = D_induced / (q · S_ref)  # collected during the fine sweep — zero extra calls
clip: reject unless 0 < e ≤ 1.10
```

`e_oswald_provenance` is stored per configuration; `e_oswald_fallback_used`
mirrors it at context level so a consumer can tell at a glance whether any
number in the context rests on the 0.8 default (gh-956 / ADR 0012 argue this
should also be a **design warning**, not just a flag).

### Vectorised sweeps 🟢

```
v_stall_approx = max(0.5 · V_cruise, 3.0)
velocities     = linspace(v_stall_approx, v_max, fine_velocity_count)   # default 8
alphas         = arange(stall_α − margin, stall_α + margin, step)       # 5°, 0.5°
grid           = np.meshgrid(alphas, velocities, indexing="xy")
                 # V-outer / α-inner ravel order — downstream indexes against it
```

One `AeroBuildup.run()` per sweep over the array-shaped `OperatingPoint`
(gh-690, commit `803b0236`; previously ~150 calls per polar configuration).

### Lift-curve regression 🟢

```
window: α ∈ [−2°, +6°]
fit   : CL = CL_α · α + CL_0    (least squares)
reject: R² < 0.995  or  CL_α ≤ 0  or  fewer than 3 finite points  → (None, None)
α₀    = degrees(−CL_0 / CL_α)
```

Consumers (`compute_vn_curve`) fall back to Helmbold-Diederich
`2π·AR/(AR+2)` when this returns `None` — explicitly **not** the thin-airfoil
`2π`, which overestimates `CL_α` at AR = 6 by ≈ 39 %.

### Reynolds-banded polar table (gh-493) 🟢

```
Re_aircraft = ρ · V · MAC_main / μ         (ISA SL, μ = 1.81e-5)
              — a LABEL for a V-based lookup, not an ASB parameter
anchors = [ max(0.5·V_cruise, 3.0),
            V_cruise,
            min(max(1.3·V_cruise, V_max), V_sweep_max) ]
bands   = midpoints between anchors; edges extended by 50 % of the adjacent gap
degeneracy: Re_max / Re_min < 2.5  → single-row fallback, degenerate = True
per band: ≥ 6 samples required, else a fallback row

lookup cd0 : LINEAR IN 1/sqrt(Re)        # Blasius / Schlichting, cf ∝ Re^(−1/2)
lookup e   : constant MEAN over non-fallback rows
             (Hepperle / Drela: e is insensitive to Re at subsonic speed)
             extrapolation clamps and warns
```

gh-924 backfill: every row with `fallback_used or cd0 is None` is overwritten
with the single-source parasite `cd0` and the Trefftz `e`, so no consumer can
read `_FALLBACK_E_OSWALD = 0.8` / `0.03` while the context holds different
authoritative values.

### Closed-form V-speeds 🟢

See [`../design.md`](../design.md) §A6 for the full block. The three
post-processing rules:

```
Picard  : ONE pass over V_md, V_min_sink, V_max — look up cd0/e at V₀ in the
          Re-table, re-solve, accept V₁; warn when |ΔV|/V₀ ≥ 5 %
Clamp   : V_md, V_min_sink → max(V, V_stall)                       (gh-683)
Read-back: V_x, V_y come from the best_angle_climb_vx /
           best_rate_climb_vy OP rows; None before OP generation
```

## Alternative Flows

- **No wings.** Step 0 returns silently; no context, no error. 🟢
- **Fatal solver failure** (stability run / coarse sweep / fine sweep). Log and
  **return**; the previous context stays valid and readable. 🟢
- **A per-configuration polar fails.** That configuration falls back to a clone
  of the clean polar with `provenance = "aerobuildup_failed"`; the other
  configurations are unaffected (they are physically independent). 🟢
- **Flap-name parity mismatch** (the model reports a flap TED but the ASB
  conversion produced no flap-role control surface). The no-flap fallback runs
  and an explicit "investigate the converter" warning is emitted, instead of
  `_run_polar_for_deflection` raising `AssertionError` on the live path
  (gh-537). 🟢
- **The polar fit is rejected.** `cd0` / `e_oswald` on that `ParabolicPolar` are
  `None` and a `PolarRejection` is attached; only `design`-category rejections
  reach the user. 🟢
- **Re-band degeneracy** (`Re_max/Re_min < 2.5`). A single-row table with
  `degenerate = True`. 🟢
- **Cold start** (`x_np` or `MAC` still `None` on the first recompute). The
  `ValueError` from `compute_stability_envelope` is demoted to **INFO** — it is
  the documented chicken-and-egg (gh-685), not a bug. 🟢
- **No user flight profile.** `_load_flight_profile_speeds` reports
  `user_set_cruise = False`, so the pipeline **replaces** the cruise speed with
  `V_md` (best L/D = best range for a prop aircraft) and flags
  `v_cruise_auto = True`. 🟢

## Dependencies

- **AeroSandbox** — `AeroBuildup.run()` (vectorised),
  `oswalds_efficiency` (Trefftz), `Atmosphere`.
- **`mission-and-sizing`** — `design_assumptions` (`mass`, `cl_max`, `g_limit`,
  `target_static_margin`, `power_to_weight`, `prop_efficiency`,
  `design_speed_mps`), `aircraft_computation_config`, `rc_flight_profiles`,
  `loading_scenario_service.compute_cg_agg_for_aeroplane`,
  `elevator_authority_service.compute_forward_cg_limit`,
  `_compute_landing_field_length`.
- **`wing-design`** — geometry and the turbulator ΔCD0 input.
- **`mass-and-balance`** — the `mass` assumption.
- **`platform-core`** — `get_db()`, the event bus, the debounced job tracker
  (`schedule_recompute_assumptions`).
- **NumPy / SciPy** — meshgrid, OLS, root solving.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| One pipeline, one JSON column, many readers (ADR 0004) | `_cache_context` | 🟢 |
| Parasite CD0 rather than total CD | `_parasite_cd0:1098-1112` | 🟢 |
| Closed-form `(L/D)max` over the measured argmax | `:282-300` | 🟢 |
| Six gates with enforced categories; only `design` is visible (ADR 0012) | `PolarRejection` validator | 🟢 |
| Refinement raises resolution, never lowers a threshold (gh-672) | `_REFINABLE_REJECTION_GATES` | 🟢 |
| Vectorised sweeps (gh-690) | `np.meshgrid(..., indexing="xy")` | 🟢 |
| Oswald derived from data the sweep already collected (gh-636) | `_e_oswald_from_sweep` | 🟢 |
| The Re-table re-bins existing samples instead of sweeping again (gh-493) | `build_re_table` | 🟢 |
| `cd0` linear in `1/sqrt(Re)`; `e` constant in Re | Blasius/Schlichting vs Hepperle/Drela, cited in code | 🟢 |
| Fallback rows backfilled with authoritative values (gh-924) | `:444-449` | 🟢 |
| One Picard pass, not a loop (gh-493 A7) | `:2033` | 🟢 |
| Sub-stall clamp on `V_md` / `V_min_sink` (gh-683) | speed block | 🟢 |
| Fatal failures write nothing; degraded ones name their fallback | recompute error policy | 🟢 |
| Seeding is unconditional and idempotent | `seed_defaults()` at step 2 | 🟢 |
| Sync function, offloaded by async callers | `asyncio.to_thread` requirement | 🟢 |

## Internal State

`aeroplanes.assumption_computation_context` (JSON) — the contract:

| Group | Keys |
|---|---|
| speeds | `v_cruise_mps`, `v_cruise_auto`, `v_max_mps`, `v_stall_mps`, `v_s1_mps`, `v_s_to_mps`, `v_s0_mps`, `v_md_mps`, `v_min_sink_mps`, `min_sink_rate_mps`, `v_a_mps`, `v_dive_mps`, `v_x_mps`, `v_y_mps`, `is_glider` |
| geometry | `mac_m`, `s_ref_m2`, `b_ref_m`, `aspect_ratio`, `reynolds`, `mass_kg` |
| aero (gh-924) | `cd0` (**parasite**), `e_oswald`, `e_oswald_r2`, `e_oswald_quality`, `e_oswald_fallback_used`, `cl_alpha_per_rad`, `alpha_0_deg` |
| α at characteristic speeds (gh-871) | `alpha_stall_deg`, `alpha_best_glide_deg`, `alpha_min_sink_deg` |
| polars | `polar_by_config{clean,takeoff,landing}`, `polar_re_table`, `polar_re_table_degenerate`, `polar_re_table_top_band_fallback` |
| stability / CG | `x_np_m`, `target_static_margin`, `cg_agg_m`, `cg_forward_m`, `cg_aft_m`, `sm_at_fwd`, `sm_at_aft`, `cg_stability_fwd_m`, `cg_stability_aft_m`, `forward_cg_result` |
| envelope / field | `flight_envelope_n_max`, `landing_field_length_m`, `landing_surface_used`, `landing_field_sufficient` |
| provenance | `computed_at` (ISO-8601 UTC) |

Also written: the `cg_x` design assumption (CALCULATED, source
`assumption_compute`), the `cl_max` and `cd0` calculated values, and the
`flight_envelopes` row.

## Observability

- `computed_at` timestamps the whole context; there is **no** per-key
  provenance beyond `e_oswald_provenance` and `polar_by_config[*].provenance`.
  🟡
- `e_oswald_fallback_used` is a single boolean at context level — it tells you
  *that* a fallback was used, not *where*. 🟡
- `auto_refined` records that a rejection was recovered by refinement. 🟢
- `PolarRejection.hint` carries the human explanation. 🟢 **The German `PolarRejection.hint` strings are translated** (`Q-AA-7` / `Q-CC-5`) — they are the most user-facing strings in the module. **They are written
  in German** while the UI is English-only.
- Picard logs a warning at `|ΔV|/V₀ ≥ 5 %`; the Re-table lookup logs on
  extrapolation clamping. 🟢
- `GET …/assumptions/recompute-status` exposes the debounced job's state. 🟢

## Constants 🟢

| Constant | Value | Where |
|---|---|---|
| `CL_α` gate | `R² ≥ 0.995` over α ∈ [−2°, 6°] | `assumption_compute_service.py:1219` |
| polar-fit window | `CL ∈ [max(0.10, 0.10·CL_max), 0.85·CL_max]`, ≥ 6 points | `:1461-1468` |
| `e` clips | `0 < e ≤ 1.10` (Trefftz) / `0.4 < e ≤ 1.0` (fit) | `:1412, :1553` |
| polar quality ladder | `R² > 0.99` high · `≥ 0.95` medium · else low | `:1697-1706` |
| Picard tolerance | `5 %`, one pass | `:2033` |
| `CL_max` floor in `V_stall` | `0.5` | speed block |
| `μ` (ISA SL) | `1.81e-5` | speed block / Re-table |
| Re-table | `_RE_DEGENERACY_RATIO 2.5` · `_MIN_SAMPLES_PER_BAND 6` · `_V_BIN_HALF_WIDTH_FRACTION 0.5` · `_FALLBACK_E_OSWALD 0.8` | `polar_re_table_service.py:46-59` |
| computation config defaults | α −5…25 °, step 1 °; fine margin 5 °, step 0.5 °; 8 velocities; debounce 2 s | `app/models/computation_config.py:8-16` |

## Risks and Gaps

- 🔴 **`stability_service._auto_populate_cd0` overwrites `cd0` with total CD** on
  a different trigger — the single most damaging violation of this use case's
  entire purpose, and it is intermittent by construction.
- 🔴 **German `hint` strings** on `PolarRejection` reach an English-only UI.
- 🔴 **Dead code:** `_load_cg_agg` (`:1739`) is unused — the pipeline calls
  `loading_scenario_service.compute_cg_agg_for_aeroplane`; `_extract_scalar`
  (`:1316`) survives only for tests.
- 🟡 **`e_oswald_fallback_used` is context-wide**, so a consumer cannot tell
  which configuration fell back.
- 🟡 **The context has no schema version.** A key rename would silently produce
  `None` in every consumer; nothing validates the shape on read.
- 🟡 **No per-key provenance.** `computed_at` covers the whole blob, so a
  consumer cannot tell that (say) `v_x_mps` is older than `cd0`.
- 🟡 **`_FALLBACK_E_OSWALD = 0.8` still exists** as a last resort in the Re-table
  even after the backfill; gh-956 argues it should raise a design warning rather
  than be used silently.
- 🟡 **The pipeline is sync and long-running.** It is debounced and scheduled,
  but a caller that forgets `asyncio.to_thread` blocks the event loop.
