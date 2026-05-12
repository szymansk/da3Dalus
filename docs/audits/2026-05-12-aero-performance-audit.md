# Aerodynamic Performance Calculations — Devil's-Advocate Audit

**Date:** 2026-05-12
**Auditor:** Claude (Opus 4.7) acting as devil's advocate
**Reference:** Anderson, *Fundamentals of Aerodynamics*, 6e
(via the `aerodynamics-expert` skill vault)
**Scope:** Backend services that derive pilot-relevant performance
quantities — `V_s`, `V_md`, `V_min_sink`, `(L/D)_max`, V-n diagram —
from AVL / AeroSandbox coefficient output.

---

## 1. Executive Summary

The **core physics** — stall speed, V-n boundaries, required `C_L`,
wing loading, dynamic pressure — is **correct and well-tested**. The
**performance-KPI fallback layer** silently substitutes rule-of-thumb
multipliers (`1.4·V_s` for best L/D, `1.2·V_s` for min sink) instead
of using the polar data that `analysis_service.py` already extracts
correctly. These heuristics happen to be ~5 % accurate for a Cessna-class
trainer but are **~15 % wrong for a high-AR sailplane** — half of this
project's stated target audience.

| Bucket | Count | Items |
|---|---|---|
| **CORRECT** | 10 | V_s, W/S, V-n, required C_L, polar extraction, (L/D)_max via raw polar, ASB ISA atmosphere |
| **DEFECT** | 4 | best_ld fallback, min_sink fallback, op-point seed speeds, cross-service inconsistency |
| **HEURISTIC** | 3 | V_dive=1.4·V_max, C_L_min=−0.8·C_L_max, n_neg≥−0.4·g_limit |
| **LIMITATION** | 3 | viscous-stall via inviscid model, no Re-dependent C_D0, C_L_max semantics ambiguous |
| **TODO / PLACEHOLDER** | 2 | powertrain hardcodes; powertrain exponential atmosphere |

Test coverage exists, but the failing-mode tests pin the *heuristics*,
not the *physics* — so the suite would not catch any of the defects.

---

## 2. Reference Formulas

### 2.1 Lift and dynamic pressure (Anderson §1.5)
- `q = ½ρV²`
- `L = q·S·C_L` ⇒ 1g level flight `W = ½ρV²·S·C_L`
- `S` = wing **planform** area (Anderson §6.7.1 allows the wing-body
  combination to be approximated by the full wing planform, including
  area masked by the fuselage)

### 2.2 Parabolic drag polar (Anderson §6.7.2 — `[[airplane-drag-polar]]`)
```
C_D = C_D0 + C_L² / (π · e · AR)
```
- `e` is the **Oswald efficiency factor**, typical 0.70 – 0.85.
- `e` is **not** the same as VLM span efficiency `e_span` (0.9 – 1.0);
  Oswald additionally bundles the lift-dependent parasite-drag growth.

### 2.3 Stall speed
```
V_s = √( 2W / (ρ·S·C_L_max) )       with W = m·g
V_s(n) = V_s · √n                   (load-factor scaling)
```
`C_L_max` here is the **3-D airplane** maximum, not the 2-D airfoil
`c_l_max`. Typically `C_L_max ≈ 0.85–0.95 · c_l_max`.

### 2.4 Minimum-drag / best-L/D speed (Anderson §6.7.2 — `[[maximum-lift-to-drag-ratio]]`)
At `(L/D)_max`, parasite drag equals induced drag:
```
C_D0  =  C_L² / (π·e·AR)        ⇒        C_L* = √(π·e·AR·C_D0)
(L/D)_max = ½ · √(π·e·AR / C_D0)
V_md = √( 2W / (ρ·S·C_L*) )  ≡  V_s · √(C_L_max / C_L*)
```
`(L/D)_max` depends **only** on `C_D0`, `e`, `AR` — *not* on weight
or wing area.

### 2.5 Minimum-power / minimum-sink speed
For a glider's best loiter (and a prop airplane's best endurance):
```
C_L_mp = √( 3 · π · e · AR · C_D0 )           ⇒    3·C_D0 = C_Di
V_mp   = V_md / 3^(1/4)  ≈  0.760 · V_md
```
For a sailplane: `V_bg = V_md`, `V_ms = V_mp`.

### 2.6 ISA (Anderson §3.4)
Sea-level: `ρ₀ = 1.225 kg/m³`, `T₀ = 288.15 K`, `p₀ = 101 325 Pa`.
Troposphere (h < 11 km): `T = T₀ − 0.0065·h`,
`ρ = ρ₀·(T/T₀)^4.2561`. The isothermal exponential `ρ₀·exp(−h/H)`
with `H ≈ 8500 m` is an **approximation** that diverges from ISA
above ~1 km.

---

## 3. Per-Hypothesis Verdicts

The audit was structured around 14 hypotheses an aerodynamicist would
attack a performance-calculation library with. Verdicts below.

| H | Hypothetical defect | Verdict |
|---|---|---|
| H1 | Mass used in place of weight (`m` instead of `m·g`) | **CORRECT** — `weight = mass_kg * GRAVITY` (`GRAVITY = 9.81`) used consistently in `flight_envelope_service.py:50` and `mass_cg_service.py:62`. |
| H2 | 2-D airfoil `c_l_max` substituted for 3-D wing `C_L_max` | **UNVERIFIABLE** — `C_L_max` is read from `design_assumptions` (`PARAMETER_DEFAULTS["cl_max"] = 1.4`). The semantics (airfoil vs wing vs airplane) are not enforced in the schema. Labeling defect, not a formula defect. |
| H3 | Wrong reference area (wetted vs planform) | **CORRECT** in the main path (uses `s_ref` from wing geometry). **PLACEHOLDER** in powertrain (hardcoded `S = 0.5 m²`). |
| H4 | mm/m unit mixing (project deliberately mixes mm in `WingConfig` and m in DB / ASB) | **CORRECT** — every audited computation in the service layer is fully SI. mm is confined to `WingConfig` and `cad_designer/`. |
| H5 | Density not ISA-correct or hardcoded sea-level | TODO in `powertrain_sizing_service` (isothermal exponential, see §6). ASB-based trim path uses `asb.Atmosphere(altitude=...)` correctly. |
| H6 | `V_md` from heuristic instead of from polar | **DEFECT** — see §4.1. |
| H7 | `V_md` (min drag) confused with `V_mp` (min power / min sink) | **DEFECT** — see §4.1; the fallback ratios `1.2·V_s` and `1.4·V_s` happen to approximate `V_mp/V_s` and `V_md/V_s` for typical GA, but the canonical identity `V_mp ≈ 0.76·V_md` is nowhere in code. |
| H8 | Oswald `e` taken from VLM span efficiency instead of true Oswald | OK in the main path (uses raw polar so `e` is never required). **PLACEHOLDER** in powertrain (hardcoded `e = 0.9`). |
| H9 | Wrong `C_D0` fit (e.g. CD at α=0 instead of CD at CL=0) | **CORRECT** — `analysis_service._interpolate_zero_crossing` finds the `C_L=0` crossing and linearly interpolates `C_D`. Good practice for cambered airfoils where `α(C_L=0) ≠ 0`. |
| H10 | Parabolic polar assumed valid into stall | **CORRECT** in `analysis_service` — uses raw polar, not a parabolic fit. The fallback heuristics in `flight_envelope_service` are *worse* than a parabolic fit because they ignore the polar entirely. |
| H11 | Load-factor scaling missing | **CORRECT** — `n = q·S·C_L_max/W` is computed pointwise on the V-n curve; no separate `V_s·√n` shortcut needed. |
| H12 | `g = 9.81` vs `9.80665` | DOCUMENT — 0.04 % effect on `V_s`. Not worth a fix; just note the standard value. |
| H13 | `(L/D)_max` and `best_ld_speed` are computed independently and disagree | **DEFECT** — see §4.2. |
| H14 | Reynolds-number dependence of `C_D0` ignored | LIMITATION — the polar is computed once and reused across the full speed envelope. For small-RC scales where `Re ∈ [50k, 500k]`, laminar bubbles can shift `C_D0` by 30 %+. Document and consider Re-dependent polar later. |

---

## 4. Defect Details

### 4.1 KPI fallback uses heuristic multipliers instead of polar

**File:** `app/services/flight_envelope_service.py`

**Defective code** (lines 119–128, 144–153):
```python
# best_ld_speed fallback
kpis.append(PerformanceKPI(
    label="best_ld_speed",
    value=round(1.4 * stall_speed_mps, 4),
    confidence="estimated",
    ...
))

# min_sink_speed fallback
kpis.append(PerformanceKPI(
    label="min_sink_speed",
    value=round(1.2 * stall_speed_mps, 4),
    confidence="estimated",
    ...
))
```

**Why it's wrong:** `V_md` depends on `C_D0`, `e`, and `AR` — not on
`V_s`. The textbook formula is
`V_md = V_s · √(C_L_max / √(π·e·AR·C_D0))`. The ratio `V_md/V_s`
varies from ~1.4 (Cessna-class) to ~1.2 (high-AR sailplane) depending
on `C_D0` and `AR`. A fixed `1.4·V_s` over-estimates `V_md` by **~15 %**
for a sailplane (see cross-checks in §5).

Similarly `V_min_sink / V_s` is **not** a constant 1.2 — it ranges from
~1.05 (sailplane) to ~1.15 (trainer). And canonically
`V_mp ≈ 0.76·V_md`, never simply `0.86·V_md` as `1.2/1.4 = 0.857`
implies.

**Correct approach:** `analysis_service.py:104–115` already finds the
true `(L/D)_max` point from the raw polar:
```python
i = int(np.nanargmax(ld))
points["maximum_lift_to_drag_ratio_point"] = {
    "alpha_deg": ..., "CL": ..., "CD": ...,
    "lift_to_drag_ratio": float(ld[i]),
}
```
The fallback in `flight_envelope_service.py` should **consume**
`maximum_lift_to_drag_ratio_point.CL` (call it `C_L*`) and compute
```
V_md = √( 2·m·g / (ρ·S·C_L*) )
```
For `V_min_sink`, find the polar point where `3·C_D0 = C_Di`
(equivalent: maximize `C_L^(3/2)/C_D`) and apply the same
`V = √(2W/(ρ·S·C_L))` rule.

**Impact:** Mis-reported V-speeds in the KPI panel whenever no
`best_ld` / `min_sink` operating-point marker exists (which is the
default state before the user runs a trim sweep).

**Vault citation:** `[[maximum-lift-to-drag-ratio]]`,
Anderson §6.7.2.

---

### 4.2 `(L/D)_max` and `best_ld_speed` computed in two services without cross-check

**Files:**
- `app/services/analysis_service.py:104–115` — extracts the correct
  `(L/D)_max` α and `C_L` from the raw polar.
- `app/services/flight_envelope_service.py:119–128` — emits the
  `best_ld_speed` KPI from a `1.4·V_s` fallback.

These two never reconcile. The first service knows the right answer;
the second service ignores it. Same root cause as 4.1 — the
data-flow connection is missing.

**Fix sketch:** Pass the alpha-sweep characteristic points into
`derive_performance_kpis(...)` as an additional parameter, and use
`(L/D)_max.CL` to compute `V_md = √(2W/(ρ·S·C_L*))` before falling
back to the heuristic.

---

### 4.3 Operating-point seed speeds derived from cruise/margin, not physics

**File:** `app/services/operating_point_generator_service.py:137–150`

**Defective code:**
```python
def _estimate_reference_speeds(profile: dict[str, Any]) -> dict[str, float]:
    goals = profile["goals"]
    cruise = float(goals.get("cruise_speed_mps", 18.0))
    min_margin_clean = max(1.05, float(goals.get("min_speed_margin_vs_clean", 1.20)))

    vs_clean = max(3.0, cruise / min_margin_clean)
    vs_to    = max(2.5, vs_clean * 0.95)
    vs_ldg   = max(2.0, vs_clean * 0.90)
    ...
```

**Why it's wrong:** `V_s` is determined by `W`, `S`, `C_L_max`, and
`ρ` (textbook §2.3). Defining it as `V_cruise / 1.20` inverts the
physical causality — cruise speed is a *consequence* of having a
sensible margin above the *physically-computed* stall, not the other
way around. For a slow-cruise / high-margin design (e.g. STOL aircraft
where `V_cruise / V_s ≈ 3`), this method produces an artificial
"`V_s_clean`" that is 2.5× higher than the real stall speed and
therefore seeds the trim solver to wildly wrong α.

The 12 downstream operating-point targets (`stall_near_clean`,
`takeoff_climb`, `best_angle_climb_vx`, `best_rate_climb_vy`,
`loiter_endurance`, `max_range`, `approach_landing`,
`stall_with_flaps`, `turn_n2`, `dutch_role_start`) all use these
fake `V_s` values as their base.

**Correct approach:** Compute `V_s_clean` via
`√(2·m·g / (ρ·S·C_L_max_clean))` and `V_s_ldg` with
`C_L_max_landing`. Both `C_L_max` values are already in the design
assumptions or can be derived from the alpha sweep.

**Impact:** Trim solver is seeded with the wrong velocity; result
is either non-convergence or convergence to an off-design α. The
displayed `velocity_mps` for each operating point is then a function
of the cruise speed margin, not the airframe's physics.

---

### 4.4 Stall detection via inviscid model

**File:** `app/services/analysis_service.py:164–181`

**Defective code (limitation, not formula error):**
```python
def _find_stall_point(alpha, cl, cd, n: int) -> dict:
    """Find the stall point after CLmax."""
    i_clmax = int(np.argmax(cl))
    i_stall = i_clmax
    if i_clmax < n - 1:
        for i in range(i_clmax + 1, n):
            if cl[i] < cl[i - 1] and cd[i] > cd[i - 1]:
                i_stall = i
                break
        else:
            i_stall = min(i_clmax + 1, n - 1)
    ...
```

**Why it's a limitation:** Stall is a viscous phenomenon (Anderson
§4.13, `[[airfoil-stall-aerodynamic-phenomena]]`). AVL is purely
inviscid — its `C_L(α)` curve never actually peaks; it grows linearly
forever. ASB's `AeroBuildup` uses a **fitted post-stall model** based
on 2-D airfoil polars; whether the fit reflects 3-D wing reality at
your wing's specific `Re`, twist distribution, and taper is unverified.

So `maximum_lift_coefficient_point` and `stall_point` from this
service report whatever the analytical curve does at high α, not what
the wing physically does. The numbers may be plausible, may be
optimistic, may be pessimistic — the audit cannot tell from code
alone.

**Recommendation:** Add a `provenance` field to these characteristic
points indicating the source ("inviscid_extrapolation",
"asb_aerobuildup_fit", "user_assumption"), and surface this label in
the UI so a professional user can decide whether to trust it.

**Vault citation:** `[[airfoil-stall-aerodynamic-phenomena]]`,
Anderson §4.13.

---

## 5. Cross-Checks: Reference Aircraft

Hand calculations using the textbook formulas, compared to what the
current fallback heuristic would emit. Both use ISA sea-level
(`ρ = 1.225 kg/m³`) and `g = 9.81 m/s²`.

### 5.1 Cessna 172 (typical GA trainer)

| Input | Value | Source |
|---|---|---|
| Weight `W` | 10 231 N (m = 1043 kg) | Pilot's Operating Handbook |
| Wing area `S` | 16.2 m² | POH |
| Aspect ratio `AR` | 7.32 | POH |
| `C_L_max` | ≈ 1.6 | Roskam (clean) |
| `C_D0` | ≈ 0.031 | Roskam |
| Oswald `e` | ≈ 0.75 | Raymer empirical |

**Computed:**
- `V_s = √(2·10 231 / (1.225 · 16.2 · 1.6)) ≈ **24.3 m/s** (≈ 47 KCAS)`
- `C_L* = √(π · 0.75 · 7.32 · 0.031) ≈ 0.731`
- `V_md = √(2·10 231 / (1.225 · 16.2 · 0.731)) ≈ **33.5 m/s** (≈ 65 KCAS)`
- `(L/D)_max = ½·√(π·0.75·7.32 / 0.031) ≈ **11.8**`

**Fallback would emit:** `best_ld_speed = 1.4 · 24.3 ≈ 34.0 m/s`
→ **+1.5 % vs textbook** for this airframe. Defect masked by lucky
parameter values.

### 5.2 ASW-27 (high-performance sailplane)

| Input | Value | Source |
|---|---|---|
| Weight `W` | 2 943 N (m = 300 kg, dry+pilot) | Schleicher data sheet |
| Wing area `S` | 9.0 m² | Data sheet |
| Aspect ratio `AR` | 28.5 | Data sheet |
| `C_L_max` | ≈ 1.3 | Sailplane handbook |
| `C_D0` | ≈ 0.011 | Sailplane handbook |
| Oswald `e` | ≈ 0.80 | Engineering estimate |

**Computed:**
- `V_s = √(2·2 943 / (1.225 · 9.0 · 1.3)) ≈ **19.7 m/s** (≈ 38 KCAS)`
- `C_L* = √(π · 0.80 · 28.5 · 0.011) ≈ 0.890`
- `V_md = √(2·2 943 / (1.225 · 9.0 · 0.890)) ≈ **23.9 m/s** (≈ 46 KCAS)`
- `(L/D)_max = ½·√(π·0.80·28.5 / 0.011) ≈ **45.4**`

**Fallback would emit:** `best_ld_speed = 1.4 · 19.7 ≈ 27.6 m/s`
→ **+15 % vs textbook**. A pilot trusting this would fly the
sailplane 4 m/s above best L/D and lose substantial glide range.

### 5.3 The asymmetry

The `1.4·V_s` heuristic is a Cessna-friendly approximation that does
not generalize to high-AR wings. Since the project explicitly serves
**both** "non-professional hobbyists" (often RC trainers — close to
Cessna behaviour) **and** "professional RC/UAV designers" (often
high-AR sailplane / long-endurance — close to ASW-27 behaviour),
this defect bites half the user base.

---

## 6. TODO / Placeholders (flagged per user direction, not defects)

### 6.1 `powertrain_sizing_service.py` hardcodes

**File:** `app/services/powertrain_sizing_service.py:21–22, 41–42`
```python
DRAG_COEFF_ESTIMATE   = 0.04           # hardcoded C_D0
WING_AREA_ESTIMATE_M2 = 0.5            # hardcoded S
...
aspect_ratio  = 8.0                    # hardcoded AR
induced_drag  = (cl**2) / (math.pi * aspect_ratio * 0.9)   # hardcoded e=0.9
```

The user has confirmed these are **known placeholder values**
pending a real implementation that pulls actual aircraft geometry
from the DB. Action: leave the report's audit row marked TODO and
ensure the **frontend / API surface clearly labels powertrain sizing
output as "estimate — not airframe-derived"** until the proper
implementation lands.

### 6.2 `powertrain_sizing_service.py` exponential atmosphere

**File:** `app/services/powertrain_sizing_service.py:27–29`
```python
def _air_density(altitude_m: float) -> float:
    """ISA air density approximation."""
    return AIR_DENSITY_SEA_LEVEL * math.exp(-altitude_m / 8500.0)
```

This is an **isothermal exponential**, not ISA. At sea level both
agree (1.225 kg/m³). At 1 km: ISA → 1.112, exp → 1.089 (~2 % low).
At 3 km: ISA → 0.909, exp → 0.853 (~6 % low). Power-required
estimates are therefore optimistic at altitude.

The proper fix (when this service is implemented for real) is to
reuse `asb.Atmosphere(altitude=altitude_m).density()` — the same
call already used in `operating_point_generator_service.py:599`.

---

## 7. Open Questions for the User

These are questions the audit cannot resolve from code alone; they
need a product-level decision:

1. **`C_L_max` semantics.** `design_assumption.py` defines
   `PARAMETER_DEFAULTS["cl_max"] = 1.4`. Is this the **3-D wing**
   `C_L_max`, the **airplane** `C_L_max` (incl. flaps), or the **2-D
   airfoil** `c_l_max`? The schema docs should make this explicit and
   the UI tooltip should match. Currently 1.4 is plausibly the
   airplane clean `C_L_max` — but a hobbyist filling in `c_l_max` for
   a Selig SD7037 (which is ~1.4) would silently produce a 1.0 wing
   `C_L_max` worth of stall speed (-15 % error).

2. **Should `stall_point` and `maximum_lift_coefficient_point` be
   displayed at all when the analysis is inviscid?** Recommend
   adding an explicit `provenance` field
   (`"inviscid_extrapolation"` vs `"asb_aerobuildup_fit"`) and
   surfacing it in the UI badge so professional users can disregard
   meaningless inviscid stall data.

3. **Should the V-n diagram blend the cert-rule `1.4·V_max` for
   `V_dive` with an airframe-driven flutter speed estimate?** For
   RC-class airframes flutter is rarely 1.4·V_max — often closer to
   `1.15·V_max`. Decision: keep cert-rule (safe over-estimate) or
   surface the rationale in UI.

4. **Reynolds-number-dependent polar.** Do we want to compute the
   polar at multiple `Re` and look up the right one per operating
   point? Costs an extra ASB run per Re but materially improves the
   numbers for small-RC scale.

---

## 8. Recommended GH Issue Titles

Suggestions — *not* auto-filed; user will decide what to ticket.

1. `fix(aero): compute best_ld_speed and min_sink_speed from polar`
   `(L/D)_max point, not 1.4·V_s heuristic`
2. `fix(aero): seed operating-point V_s from physics, not from`
   `cruise/margin`
3. `feat(aero): add provenance field to alpha-sweep characteristic`
   `points (inviscid vs asb_fit vs user)`
4. `docs(aero): clarify C_L_max semantics in design_assumption schema`
5. `feat(aero): Re-dependent polar lookup for small-RC scale`
6. `chore(powertrain): replace placeholder C_D0/S/AR/e with`
   `geometry-derived values (existing TODO)`
7. `chore(powertrain): replace exponential atmosphere with`
   `asb.Atmosphere ISA model (existing TODO)`

---

## 9. Appendix: Inventory Table (verified file:line evidence)

| # | Calculation | File:line | Verdict |
|---|---|---|---|
| 1 | `V_s = √(2W/(ρ·S·C_L_max))` for V-n diagram | `app/services/flight_envelope_service.py:50-51` | CORRECT |
| 2 | `V_s` for design-metrics endpoint | `app/services/mass_cg_service.py:62-64` | CORRECT |
| 3 | `V_dive = 1.4 · V_max` | `flight_envelope_service.py:52` | HEURISTIC |
| 4 | `C_L_min = −0.8 · C_L_max` | `flight_envelope_service.py:53` | HEURISTIC |
| 5 | Negative-g cap `n_neg ≥ −0.4·g_limit` | `flight_envelope_service.py:65` | HEURISTIC |
| 6 | `best_ld_speed` fallback = `1.4·V_s` | `flight_envelope_service.py:119-128` | **DEFECT** |
| 7 | `min_sink_speed` fallback = `1.2·V_s` | `flight_envelope_service.py:144-153` | **DEFECT** |
| 8 | (L/D)_max via `np.nanargmax(cl/cd)` | `analysis_service.py:104-115` | CORRECT |
| 9 | `C_D@C_L=0` by linear interpolation | `analysis_service.py:140-161` | CORRECT |
| 10 | Stall point from `argmax(cl)` then `cl↓ ∧ cd↑` | `analysis_service.py:164-181` | LIMITATION |
| 11 | Powertrain `C_D0=0.04`, `S=0.5 m²`, `AR=8`, `e=0.9` | `powertrain_sizing_service.py:21-22, 41-42` | TODO |
| 12 | Atmosphere `ρ = ρ₀·exp(−h/8500)` | `powertrain_sizing_service.py:27-29` | TODO |
| 13 | ASB Atmosphere for trim points | `operating_point_generator_service.py:599` | CORRECT |
| 14 | OP seed: `V_s_clean = V_cruise / 1.2` | `operating_point_generator_service.py:137-150` | **DEFECT** |
| 15 | `n = q·S·C_L_max / W`, capped at `g_limit` | `flight_envelope_service.py:64` | CORRECT |
| 16 | Required `C_L(V) = (m·g·n)/(q·S)` | `operating_point_generator_service.py:500-513` | CORRECT |
| 17 | `W/S = m·g / S` | `mass_cg_service.py:63` | CORRECT |
| 18 | Re-dependence of `C_D0` | (not modeled) | LIMITATION |
