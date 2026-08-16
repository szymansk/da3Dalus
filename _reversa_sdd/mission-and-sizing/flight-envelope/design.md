# flight-envelope — Technical Design

> Use-case design, nested under the module
> [`mission-and-sizing`](../design.md).
> Focuses on HOW this use case is built, read from the legacy code.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`tasks.md`](tasks.md), [`../contracts.md`](../contracts.md) §E.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `compute_vn_curve` | `(mass_kg, cl_max, g_limit, wing_area_m2, rho=1.225, v_max_mps=28.0, b_ref_m=None, cl_alpha_per_rad=None, gust_u_vc_mps=15.24, gust_u_vd_mps=7.62)` | `VnCurve` | **pure** — no DB, no solver 🟢 |
| `derive_performance_kpis` | `(stall_speed_mps, v_max_mps, g_limit, markers, v_md_polar_mps=None, v_min_sink_polar_mps=None)` | `list[PerformanceKPI]` | **pure**; exactly six 🟢 |
| `_helmbold_cl_alpha` | `(ar)` | `float` | `2π·AR/(AR+2)` 🟢 |
| `_compute_mu_g` | `(mass_kg, s_ref, c_mgc, cl_alpha, rho=1.225, g=9.81)` | `float` | `c_mgc = S/b`, **not** the MAC 🟢 |
| `_compute_k_g` | `(mu_g)` | `float` | logs a WARNING outside `[3, 200]` 🟡 |
| `_compute_delta_n` | `(rho, v, cl_alpha, u_gust, k_g, mass_kg, s_ref, g=9.81)` | `float` | 🟢 |
| `_extract_cl_alpha_from_context` | `(ctx)` | `float \| None` | rejects non-numeric, non-finite and `≤ 0` 🟢 |
| `_build_gust_lines` | `(…, n_points=60)` | `(pos[], neg[], warnings[])` | 🟢 |
| `_load_assumptions` | `(db, aeroplane_uuid)` | `{mass, cl_max, g_limit}` | catalogue fallback on `NotFoundError` 🟢 |
| `_get_wing_area_m2` | `(db, aeroplane)` | `float` | raises `InternalError` when `s_ref ≤ 0` 🟢 |
| `_get_b_ref` | `(db, aeroplane)` | `float \| None` | bare `except` → `None` 🟡 |
| `_get_v_max` | `(db, aeroplane)` | `float` | profile goal, else a bare `28.0` 🟡 |
| `_load_operating_point_markers` | `(db, aeroplane, mass_kg, wing_area_m2)` | `list[VnMarker]` | `mass` and `area` are accepted but **unused** 🔴 |
| `compute_flight_envelope` | `(db, aeroplane_uuid)` | `FlightEnvelopeRead` | seven steps, upsert 🟢 |
| `get_flight_envelope` | `(db, aeroplane_uuid)` | `FlightEnvelopeRead \| None` | `None` ⇒ the endpoint 404s 🟢 |

HTTP surface: see [`../contracts.md`](../contracts.md) §E — two routes.

## Main Flow

```
compute_flight_envelope(db, uuid)
 1. aeroplane   = _get_aeroplane                     → NotFoundError → 404
 2. assumptions = _load_assumptions                  {mass, cl_max, g_limit}
 3. wing_area   = _get_wing_area_m2                  ASB conversion #1 → s_ref
    b_ref       = _get_b_ref                         ASB conversion #2 → b_ref | None
    v_max       = _get_v_max                         profile goal else 28.0
 4. ctx         = aeroplane.assumption_computation_context or {}
    cl_alpha    = _extract_cl_alpha_from_context(ctx)          may be None
 5. vn_curve    = compute_vn_curve(mass, cl_max, g_limit, wing_area,
                                   v_max_mps=v_max, b_ref_m=b_ref,
                                   cl_alpha_per_rad=cl_alpha)
 6. markers     = _load_operating_point_markers(...)
 7. kpis        = derive_performance_kpis(vn_curve.stall_speed_mps, v_max,
                                          g_limit, markers,
                                          v_md_polar_mps=ctx["v_md_mps"],
                                          v_min_sink_polar_mps=ctx["v_min_sink_mps"])
 8. upsert flight_envelopes (one row per aeroplane):
        vn_curve_json / kpis_json / markers_json  = model_dump(mode="json")
        assumptions_snapshot = assumptions
        computed_at = utcnow()
 9. return _model_to_read(row)
```

Steps 5 and 7 are **pure functions** and are unit-testable without a database
or a solver; steps 1–4, 6 and 8 are the DB-aware shell. The module is
deliberately split with a `# Pure computation helpers (no DB)` /
`# DB-aware helpers` boundary comment. 🟢

## The manoeuvre envelope 🟢

```python
if mass_kg <= 0 or cl_max <= 0 or wing_area_m2 <= 0 or v_max_mps <= 0:
    raise ValueError("mass_kg, cl_max, wing_area_m2, and v_max_mps must be positive")

weight  = mass_kg * 9.81
v_stall = sqrt(2 * weight / (rho * wing_area_m2 * cl_max))     # rho = 1.225 fixed
v_dive  = 1.4 * v_max_mps
cl_min  = -0.8 * cl_max

n_points = 60                      # "> 50 as required"
for i in range(60):
    v = v_stall + (v_dive - v_stall) * i / 59
    q = 0.5 * rho * v**2
    n_pos = min(q * S * cl_max / weight,  g_limit)
    n_neg = max(q * S * cl_min / weight, -0.4 * g_limit)
    → VnPoint(round(v, 6), round(n, 6))
```

The aerodynamic branch and the structural cap are produced by a single
`min` / `max` per point, so the corner speed `V_A` is implicit in the data
rather than emitted as a named point. 🟡 `ρ` is a hard-coded sea-level `1.225`
— the flight profile's `altitude_m` is **not** consulted here, unlike in the
operating-point sweep. 🟡

## The gust envelope 🟢

```python
c_mgc = wing_area_m2 / b_ref_m          # MEAN GEOMETRIC chord — NOT the MAC
mu_g  = 2 * (W/S) / (rho * c_mgc * cl_alpha * g)
k_g   = 0.88 * mu_g / (5.3 + mu_g)
v_c   = v_dive / 1.4                    # ⇒ V_C == v_max by construction

# ONE validity warning, before the sweep
if   mu_g < 3.0:   GustValidityWarning("… may be optimistic for this light/small aircraft")
elif mu_g > 200.0: GustValidityWarning("… may be conservative for this heavy aircraft")

for the same 60 velocities:
    u = 15.24                                     if v <= v_c
        15.24 + (v - v_c)/(v_dive - v_c) * (7.62 - 15.24)   otherwise
    delta_n = 0.5 * rho * v * cl_alpha * u * k_g / (W/S)
    n_pos, n_neg = 1 + delta_n, 1 - delta_n
    first v with n_pos >  g_limit        → ONE positive GustCriticalWarning
    first v with n_neg < -0.4 * g_limit  → ONE negative GustCriticalWarning
```

Gating in `compute_vn_curve` 🟢:

```
effective_cl_alpha = cl_alpha_per_rad
if effective_cl_alpha is None and b_ref_m:      # AR = b²/S
    effective_cl_alpha = _helmbold_cl_alpha(b_ref_m**2 / wing_area_m2)

if effective_cl_alpha is not None and b_ref_m:  → build the lines
else                                            → EMPTY lists, no warnings
```

So `b_ref` is required **twice over**: once for the chord and once (when the
context has no `CL_α`) for the aspect ratio. Without it the gust envelope is
absent, not zero (BR-MS43). 🟢

Sources recorded in the docstrings 🟢: FAR-25.341(a), CS-VLA.333/341,
FAR-23.333(c), NACA TN 2964 (Pratt & Walker, 1953), Anderson *Introduction to
Flight* 6e §5.3 and §6.5.

🟡 On the **negative** `GustCriticalWarning` the `g_limit` field is populated
with `round(-0.4 * g_limit, 4)` — the field name says `g_limit` but the value is
the negative limit.
🟡 `_compute_k_g` logs the same out-of-range condition that
`_build_gust_lines` reports structurally, so one event travels two channels.

## The KPI ladder 🟢

```
markers_by_label = {m.label: m for m in markers}     # label == the OP name

1 stall_speed     V_stall                                        "limit"
2 best_ld_speed   markers["best_ld"].velocity_mps                "trimmed"
                  else v_md_polar_mps if > 0                     "computed"
                  else 1.4 * V_stall                             "estimated"
3 min_sink_speed  markers["min_sink"].velocity_mps               "trimmed"
                  else v_min_sink_polar_mps if > 0               "computed"
                  else 1.2 * V_stall                             "estimated"
4 max_speed       v_max                                          "limit"
5 max_load_factor markers["max_turn"].load_factor                "trimmed"
                  else g_limit                                   "limit"
6 dive_speed      1.4 * v_max                                    "limit"

every value round(x, 4);  source_op_id set only on the marker branches
```

🟢 **An explicit `role` field is set by the generator** — `best_ld` ← `max_range`, `min_sink` ← `loiter_endurance`, `max_turn` ← `turn_60` (`Q-MS-7`). Previously the three labels were **names the
generator never produces** — it emits `max_range`, `loiter_endurance`,
`turn_60`, … — so the `trimmed` tier is unreachable through the standard flow
and `max_load_factor` always reports `g_limit`.
🟢 The `"trimmed"` tier is gated on `status == TRIMMED` and proximity to the polar (`Q-MS-7`); nearest-match is rejected. Previously the branch did not check `marker.status`, so a point named
`best_ld` in state `NOT_TRIMMED` would still be labelled `"trimmed"`.

The heuristic tier is documented in the docstring as *"wrong by up to 15 % for
high-AR airframes (gh-475 audit §4.1) and kept only for the cold-start case
where no polar has been computed yet"* — which is precisely why `confidence` is
part of the contract (ADR 0012). 🟢

## Markers 🟢

```python
for op in operating_points where op.velocity is not None and > 0:
    VnMarker(op_id=op.id,
             name=op.name or "unnamed",
             velocity_mps=op.velocity,
             load_factor=n_target or q*S*cl/(m*g),  # Q-MS-6 🟢
             status=op.status or "NOT_TRIMMED",
             label=op.name or "unnamed")      # 🟡 label == name
```

The in-code justification for the load factor: *"Operating points represent
level flight conditions (n=1.0). Without stored CL, we cannot derive actual load
factor."* — true for the twelve level targets, **false for `turn_20/40/60`**,
which plot on the 1-g line. 🟢 Fixed by `Q-MS-6`.
🟢 `mass_kg` and `wing_area_m2` become live inputs — `n = q·S·C_L,trim/(m·g)` (`Q-MS-6`). Previously they were parameters and never
used — the signature anticipates the CL-based load factor that was never
implemented.

## DB-aware helpers 🟢

```
_load_assumptions(db, uuid)
    for param in ("mass", "cl_max", "g_limit"):
        try:    mass_cg_service.get_effective_assumption_value(db, uuid, param)
        except NotFoundError:  PARAMETER_DEFAULTS[param]
    → this try/except re-implements design_assumptions_service
      .get_effective_assumption's own fallback                       🟡

_get_wing_area_m2(db, aeroplane)
    model → schema → asb.Airplane;  s_ref
    s_ref is None or <= 0 → InternalError("Cannot determine wing reference
                                           area — no wings defined")   → 500

_get_b_ref(db, aeroplane)
    the SAME two conversions again;  b_ref
    ANY exception → None            ← bare except                      🟡

_get_v_max(db, aeroplane)
    aeroplane.flight_profile.goals["max_level_speed_mps"]  when present
    else 28.0                                                          🟡
```

🟡 `_get_v_max` diverges from the operating-point sweep, which falls back to
`max(1.35·V_cruise, V_cruise + 8)` for the same quantity (BR-MS8). `V_dive`,
`max_speed` and `dive_speed` all ride on this number.
🟡 The two ASB conversions are performed independently, so the model→schema→ASB
pipeline runs twice per compute.

## Persistence 🟢

```
flight_envelopes — ONE row per aeroplane (unique FK), upserted
    vn_curve_json        = VnCurve.model_dump(mode="json")
    kpis_json            = [k.model_dump(mode="json") for k in kpis]
    markers_json         = [m.model_dump(mode="json") for m in markers]
    assumptions_snapshot = {"mass": …, "cl_max": …, "g_limit": …}
    computed_at          = datetime.now(timezone.utc)
existing row → fields overwritten in place;  otherwise a new row
```

🟡 The snapshot records the three **assumptions** but not the **context**
version, even though `cl_alpha_per_rad`, `v_md_mps` and `v_min_sink_mps` shape
the gust lines and two KPIs. A row can therefore be silently stale with respect
to the context that produced half of it.

## Alternative Flows

- **No wings.** `_get_wing_area_m2` raises `InternalError` → **500**. 🟡 A
  cold-start aircraft is a user condition, not an internal error; the
  matching-chart and field-length endpoints answer 422 for the analogous case.
- **ASB conversion fails for `b_ref`.** Swallowed by a bare `except`; the gust
  envelope is silently absent with no warning explaining why. 🟡
- **No `cl_alpha_per_rad` in the context.** Helmbold-Diederich is used, but only
  when `b_ref` is known. 🟢
- **A corrupted `cl_alpha_per_rad`** (string, NaN, `≤ 0`). Rejected by
  `_extract_cl_alpha_from_context`; Helmbold takes over. 🟢
- **No flight profile.** `_get_v_max` returns the bare `28.0`. 🟡
- **A missing assumption row.** Falls back to `PARAMETER_DEFAULTS`. 🟢
- **No operating points.** `markers` is empty; the KPI ladder drops to the
  `computed` / `estimated` tiers. 🟢
- **Non-positive inputs.** `compute_vn_curve` raises `ValueError`, which the
  endpoint's generic handler turns into a **500 "Unexpected error: …"** rather
  than a 422. 🟡
- **No cached row on GET.** `get_flight_envelope` returns `None` and the
  endpoint raises a 404 with *"No flight envelope computed yet for this
  aeroplane."* — distinguishable from the aeroplane-not-found 404. 🟢

## Dependencies

- **[`../design-assumptions/`](../design-assumptions/design.md)** — `mass`,
  `cl_max`, `g_limit` (the only three assumptions consumed).
- **`aero-analysis`** — `cl_alpha_per_rad`, `v_md_mps`, `v_min_sink_mps` from
  `assumption_computation_context` (BR-14).
- **[`../operating-point-sweep/`](../operating-point-sweep/design.md)** — the
  `operating_points` rows plotted as markers.
- **`wing-design`** / **`fuselage-design`** — via the model→schema→ASB
  converters, for `s_ref` and `b_ref`.
- **`mission-and-sizing` / flight profiles** — `goals.max_level_speed_mps`.
- **`platform-core`** — `get_db()` (BR-78); the service only flushes.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| The pure computation is separated from the DB shell by an explicit boundary | the `# Pure computation helpers (no DB)` comment | 🟢 |
| 60 points, *"> 50 as required"* | `compute_vn_curve` | 🟢 |
| The aerodynamic branch and the cap are one `min`/`max`, so `V_A` is implicit | same | 🟡 |
| `CL_min = −0.8·CL_max` and `n⁻ ≥ −0.4·g_limit` | same | 🟢 |
| Gust uses the **mean geometric** chord, not the MAC (gh-487) | `_build_gust_lines` | 🟢 |
| `CL_α` from Helmbold-Diederich, never the thin-airfoil `2π` | `_helmbold_cl_alpha` docstring | 🟢 |
| A corrupted cached `CL_α` is rejected rather than trusted | `_extract_cl_alpha_from_context` | 🟢 |
| Gust lines are **absent** rather than zeroed when their inputs are missing | the `if` gate in `compute_vn_curve` | 🟢 |
| Gust warnings are structured API objects, not log lines (gh-497) | `GustCriticalWarning` / `GustValidityWarning` | 🟢 |
| At most one critical warning per sign, at the first crossing | `warned_positive` / `warned_negative` | 🟢 |
| The validity warning is direction-specific (optimistic vs conservative) | `_build_gust_lines` | 🟢 |
| Exactly six KPIs, always, each with a confidence tier (ADR 0012) | `derive_performance_kpis` | 🟢 |
| The polar-derived speeds outrank the 1.4/1.2 heuristics (gh-475) | same | 🟢 |
| One row per aeroplane, upserted, with an assumptions snapshot | `compute_flight_envelope` | 🟢 |
| "Not computed yet" is a distinct 404 message | the GET handler | 🟢 |
| `ρ` from one shared ISA helper (`Q-PT-9`) | `compute_vn_curve` default | 🟢 |
| `V_max` falls back to a bare 28.0 | `_get_v_max` | 🟡 |
| Markers are labelled by the operating point's name | `_load_operating_point_markers` | 🔴 |

## Internal State

| Table | Cardinality | Note |
|---|---|---|
| `flight_envelopes` | **one per aeroplane** (unique FK, `ON DELETE CASCADE`), upserted | `vn_curve_json`, `kpis_json`, `markers_json`, `assumptions_snapshot`, `computed_at` |
| `operating_points` | read-only here | plotted as markers |
| `aeroplanes.assumption_computation_context` | read-only here | `cl_alpha_per_rad`, `v_md_mps`, `v_min_sink_mps` |

## Observability

- Gust warnings are **structured API objects**, so the UI can render a banner —
  deliberately not log-only (gh-497). 🟢
- Every KPI carries `confidence`, distinguishing a measured value from a
  15 %-wrong heuristic. 🟢
- `flight_envelopes.assumptions_snapshot` and `computed_at` record the inputs
  and the moment. 🟢
- `_compute_k_g` logs the out-of-range `μ_g` with the reference
  (NACA TN 2964 / FAR-25.341). 🟡 Duplicating the structured warning.
- 🟡 A silently absent gust envelope (no `b_ref`, no `CL_α`) must emit a `DesignWarning` (`P-WARN-0`); today it produces **no
  signal at all** — neither a warning nor a log line.
- 🟡 `_get_b_ref`'s bare `except` swallows the reason the conversion failed (`P-WARN-0`).
- 🟡 The snapshot does not identify the **context** version, although the gust
  lines and two KPIs depend on it.

## Constants 🟢

| Constant | Value | Where |
|---|---|---|
| `GRAVITY` | `9.81` | `:40` |
| `GUST_U_VC_MPS` / `GUST_U_VD_MPS` | `15.24` / `7.62` m/s (50 / 25 ft/s) | `:43-44` |
| `_MU_G_MIN` / `_MU_G_MAX` | `3.0` / `200.0` | `:47-48` |
| V-n resolution | `60` points | `compute_vn_curve` |
| `CL_min` factor | `−0.8` | same |
| negative-`n` floor | `−0.4 · g_limit` | same |
| `V_dive` factor | `1.4 · V_max` (so `V_C == V_max`) | same |
| `ρ` | `1.225` kg/m³, fixed | signature default |
| `K_g` | `0.88·μ_g / (5.3 + μ_g)` | `_compute_k_g` |
| KPI heuristics | `1.4·V_s` (best L/D) · `1.2·V_s` (min sink) | `derive_performance_kpis` |
| `V_max` fallback | `28.0` m/s | `_get_v_max` |
| marker load factor | `1.0`, hard-coded | `_load_operating_point_markers` |
| rounding | 6 dp on V-n points, 4 dp on KPIs and warnings | throughout |

## Risks and Gaps

- 🟢 Fixed by `Q-MS-6`: persist `n_target` and `cl_trimmed`, place the marker at the real load factor. Previously hard-coded because the stored
  operating point carries no CL — so `turn_20/40/60` plot on the 1-g line,
  exactly where they are not. `_load_operating_point_markers` even accepts
  `mass_kg` and `wing_area_m2` for the calculation that was never written.
- 🟢 An explicit `role` field replaces name matching, and the `trimmed` tier is gated on `status == TRIMMED` plus polar proximity (`Q-MS-7`). Previously unreachable: The lookup keys are `best_ld`,
  `min_sink` and `max_turn`; the marker label is the operating point's **name**,
  and the generator never produces those names.
- 🟢 An explicit `role` field replaces name matching, and the `trimmed` tier is gated on `status == TRIMMED` plus polar proximity (`Q-MS-7`). Previously the status was not checked before labelling
  `"trimmed"` — a `NOT_TRIMMED` row named `best_ld` would be reported as
  trimmed.
- 🟡 **`_get_v_max` returns a bare `28.0`** where the operating-point sweep uses
  `max(1.35·V_cruise, V_cruise + 8)`. `V_dive`, `max_speed` and `dive_speed`
  all depend on it.
- 🟢 **One shared ISA helper supplies `ρ`** (`Q-PT-9`). Previously fixed at sea level: The flight profile's `altitude_m` shapes
  every operating point but not the envelope.
- 🟡 **"No wings" is a 500.** `_get_wing_area_m2` raises `InternalError`, and a
  non-positive input raises a `ValueError` that the endpoint reports as
  *"Unexpected error"* — both are cold-start user conditions that the sibling
  endpoints answer with 422.
- 🟡 **An absent gust envelope must warn** (`P-WARN-0`); today silent: No warning, no log line, nothing in
  the response explains why the arrays are empty.
- 🟡 **The snapshot omits the context version**, although the gust lines and two
  KPIs are derived from it.
- 🟡 **The negative `GustCriticalWarning.g_limit` field holds `−0.4·g_limit`.**
- 🟡 **`_compute_k_g` logs what `_build_gust_lines` already reports**
  structurally.
- 🟡 **Two ASB conversions per compute** (`s_ref`, then `b_ref`).
- 🟡 **`_load_assumptions` re-implements the catalogue fallback** with a
  `try/except NotFoundError` around the UUID-keyed reader, instead of using
  `design_assumptions_service.get_effective_assumption`.
- 🟡 **`ComputeEnvelopeRequest.force_recompute` is dead surface** — the POST
  takes no body and always recomputes.
- 🟡 **The corner speed `V_A` is implicit** in the point cloud; a consumer that
  needs it must find the kink numerically.
