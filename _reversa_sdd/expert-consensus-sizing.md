# Expert consensus — sizing, performance, stability, mass & CG

Rulings on the open engineering questions in `questions.md` that are decidable
by domain expertise rather than maintainer preference.

**Scope framing (governs every answer below).** The product is a design tool for
**hobby RC and small UAV** aircraft: roughly **0.5–15 kg**, 3D-printed or
wood-built, hand-, bungee- or ground-launched, **no wheel brakes on the vast
majority of airframes**, flown line-of-sight by one private pilot. It is
explicitly *not* transport-category preliminary design. Methods calibrated on
certified aircraft (Roskam's Cessna-172 constants, CS-25 field-length rules,
FAR-25 gust criteria) are judged here on whether they are *valid at this scale*
— not on whether they are standard in that literature.

**Authority hierarchy used** (from `CLAUDE.md`):

1. **Scholz / Sadraey** (`aircraft-design-scholz`) — lead. Academic, citable.
2. **Anderson** (`aerodynamics-expert`) — physics ground truth, used where the
   mechanism decides the answer.
3. **RC practice** (`rc-aircraft-designer`: Lennon 1996 + rcplanedesigner.com +
   RC-Network Wiki) — **hobbyist-level, lower authority**, valid for RC models,
   *not* for UAV. Where it conflicts with Scholz, Scholz wins and the conflict
   is named.

Source labels are explicit throughout: **[Scholz/Sadraey]** = academic,
**[RC]** = hobbyist practice, **[Anderson]** = physics text,
**[derived]** = arithmetic done here from a cited quantity.

### Unit conversions used repeatedly (all [derived], exact)

| From | To | Factor |
|---|---|---|
| 1 g/dm² (mass loading) | N/m² (weight loading) | **0.981** |
| 1 N/m² | g/dm² | **1.019** |
| 1 oz/ft² | N/m² | **2.994** |
| 1 oz/ft² | g/dm² | **3.052** |
| 1 oz/ft³ (WCL) | N/m³ | **9.818** |
| 1 oz/ft³ (WCL) | kg/m³ | **1.0012** |

The last row is the useful one: **WCL in oz/ft³ is numerically the same as WCL
in kg/m³ to within 0.12 %.** Any conversion constant other than ~1.0 (mass form)
or ~9.82 (force form) is wrong.

---

## Q-MS-2 — Which landing-distance model should the UI trust? And which `t_static_N`?

**Question.** Two landing distances are computed for the same aircraft: Roskam
§3.4 (`GET /field-lengths` → `s_ldg_50ft_m`) and the gh-477 energy balance
(`assumption_computation_context.landing_field_length_m`). Which is authoritative
at RC/UAV scale? Separately, `t_static_N` exists both on `mission_objectives`
(gh-548, read by the field-length endpoint) and as a same-named design
assumption (read by the matching chart) — which wins?

**What the code does today.**
`field_length_service._compute_s_ldg_ground` (`app/services/field_length_service.py:233`)
uses `K_LDG = 0.5847 · (μ_brake_hard/μ_brake)`, then multiplies by
`_K_LDG_50FT = 2.73` — a constant explicitly calibrated against a *Cessna 172N
POH* (`field_length_service.py:75-82`). `assumption_compute_service._compute_landing_field_length`
(`:1797`) instead does `s = 1.5 · (15 m + V_TD²/(2·g·μ_eff))` with
`V_TD = 1.15·V_S0` and a per-surface `μ_eff`. The matching-chart endpoint reads
`get_effective_assumption(db, plane_id, "t_static_N")`
(`app/api/v2/endpoints/aeroplane/matching_chart.py:83`); the field-length wrapper
reads `objective.t_static_N` (`field_length_service.py:531`).

**Scholz/Sadraey view.** The landing constraint in preliminary sizing is a
*regulatory* construct: CS 25.125 requires the distance from **50 ft** at an
approach speed **≥ 1.3 V_S**, and CS-OPS 1.515 then divides by 0.6 (jet) or 0.7
(turboprop) to give `s_LFL` ([[landing-field-length-constraint]],
*05_PreliminarySizing §5.1*). Every element of that chain — the 50 ft obstacle,
the 1.3 V_S approach, the 0.6/0.7 operator factor, and Roskam's braked ground
roll — is a **certification artefact with no counterpart at RC/UAV scale**.
Sadraey's own alternative for this regime is the **stall-speed constraint**
(Eq. 4.31, `(W/S)_Vs = ½ρV_s²C_Lmax`), which he explicitly recommends "when the
customer or regulation specifies a maximum permissible stall speed" — i.e. for
non-Part-25 aircraft ([[landing-field-length-constraint]] §1). Sadraey also
warns that the Loftin/Roskam single-empirical-constant treatment is the *fast*
method and the physics-explicit one (friction μ made visible) is the *accurate*
one once μ is known ([[takeoff-field-length-constraint]], note after Eq. 4.71).
That is precisely the trade here.

**RC practice view.** No RC model in the 0.5–15 kg class has wheel brakes as
standard; most land on grass, many belly-land. Lennon's landing treatment is
about touchdown speed and centrifugal load, not about a certified field length
([[lennon-landing-speed-and-centrifugal-load]]). RC pilots quote *rollout*, not
"distance from 50 ft".

**Physics note.** `K_LDG = 0.5847` is derived in the code from
`V_TD = 1.3·V_S` **and `μ_brake = 0.4`** — a *braking* coefficient. Sadraey
Table 4.15 gives **rolling** friction of 0.03–0.05 (dry concrete), 0.05–0.1
(grass), 0.1–0.3 (soft ground) ([[takeoff-field-length-constraint]]). An
unbraked RC model decelerates at roughly a quarter of the assumed rate, so
Roskam's landing roll is **structurally optimistic by ~4×** before the 2.73
obstacle factor partially masks it. Worked example (1.5 kg trainer,
S = 0.30 m², CL_max,ldg = 1.8) [derived]: Roskam gives `s_ldg_50ft ≈ 35.5 m`;
the energy balance on short grass gives `52.5 m`. **48 % apart, same aircraft,
both labelled "landing distance".**

**CONSENSUS.**
1. **The gh-477 energy balance is authoritative for the RC/UAV landing number.**
   It is dimensionally honest, mass-independent (mass cancels), and its single
   free parameter (`μ_eff`) is exactly the quantity that differs between a
   braked C172 and an unbraked foamie. Publish `landing_field_length_m` as
   *the* landing distance.
2. **Roskam §3.4 stays only for `ga_runway` mode** (where its calibration is
   valid), or is deleted. In every RC/UAV mode `GET /field-lengths` must
   **delegate its landing branch to the energy balance** so one producer feeds
   both surfaces. The takeoff side of `field_length_service` is unaffected —
   Roskam's `_C_TO = 1.21` is a ground-roll energy constant, not a braking one.
3. **Fix the touchdown-speed inconsistency while merging.** Roskam's path uses
   `V_TD = 1.3·V_S`, the energy balance uses `1.15·V_S0`. Both are defensible at
   their own point in the trajectory — 1.3 V_S is the **approach** speed at the
   50 ft gate [Scholz, CS 25.125], 1.15 V_S0 is the **touchdown** speed after
   flare — but they differ by (1.3/1.15)² = **1.28× in energy**. Keep
   `V_TD = 1.15·V_S0` for the ground roll and `V_app = 1.3·V_S0` for the air
   phase; never use one for both.
4. **`t_static_N`: `mission_objectives` wins.** Two arguments agree. (a) gh-548
   migrated it there, so the assumption row is the residue. (b) Domain: static
   thrust is a **propulsion/mission input** — measured, or produced by the
   powertrain model the app already owns — not a design *assumption* with an
   estimate/calculated duality. On the matching chart, T/W is an **output** (the
   design point) per Scholz §5.8 ([[matching-chart-optimization]]); the
   aircraft's actual T/W is only the "Ist" marker, and that marker must read the
   same `t_static_N` the field-length endpoint reads. Change
   `matching_chart.py:83` to read the mission objective and delete the
   `t_static_N` design-assumption row.

**Disagreement.** None between the authorities — Scholz/Sadraey and RC practice
both point away from the certified-transport method at this scale. The conflict
is between the code's two implementations, not between the sources.

**Confidence: high.** The 48 % worked example is reproducible; the
`μ_brake = 0.4` provenance is in the code's own docstring. What would raise it
further: one measured RC rollout (video + tape measure) at a known touchdown
speed to pin `μ_eff` — see Q-MS-3.

---

## Q-MS-3 — What are `LANDING_SURFACE_MU` and the WCL constant calibrated against?

**Question.** `LANDING_SURFACE_MU` is documented as coming from "operational
RC/UAV practice … explicitly not from a cited source", yet it drives a
user-facing "field sufficient" verdict. `_wcl_constraint` admits its
lb/ft^4.5 → SI mapping is "a numerical stand-in awaiting calibration". What are
defensible values?

**What the code does today.**
`assumption_compute_service.py:1782` — `{grass_short: 0.15, grass_long: 0.22,
hard_paved: 0.07, soft_soil: 0.30, belly_grass: 0.40, net_recovery: 0.0}`, plus
`_LANDING_FLARE_M = 15.0` (a fixed 15 m regardless of size or speed) and
`_LANDING_SAFETY_DEFAULT = 1.5`. `matching_chart_service.py:497` — `W/S_max =
(WCL_lb · 47.88)^(2/3) · AR^0.25`, with `_WCL_UPPER_BY_PROFILE_LB_FT45 =
{trainer: 6.0, sport: 12.0}` and an unused `g` parameter.

### Part A — the surface friction table

**Scholz/Sadraey view.** Sadraey Table 4.15 gives **rolling** friction
coefficients: dry concrete/asphalt **0.03–0.05**, wet 0.05, icy 0.02, turf
**0.04–0.07**, grass **0.05–0.1**, soft ground **0.1–0.3**
([[takeoff-field-length-constraint]], *16_Sadraey §4.3.4*). Braking on dry
paved is 0.3–0.5. So the table's grass value (0.15) is **1.5–3× above**
Sadraey's rolling range, and `belly_grass = 0.40` is above any tyre-rolling
value at all.

**Physics note (this is what resolves it).** The energy balance
`s = V_TD²/(2·g·μ_eff)` is constant-deceleration kinematics: **`μ_eff` is not a
tyre friction coefficient, it is the mean deceleration expressed in g**.
The real balance is `m·a = D + μ_roll·(W − L)` — aerodynamic drag `D` and the
residual wing lift `L` are both first-order at RC scale and neither appears in
the code. So `μ_eff = μ_roll + Δ_aero`, where `Δ_aero ≈ 0.05–0.10` for a typical
RC model rolling out with the wing still at high α. Once read that way, **the
existing numbers are defensible** — they are just mislabelled.

**RC practice view.** RC-Network's rollout material is procedural (taxi tests,
ground-loop behaviour), not quantitative — the vault has **no measured RC
rollout distances**. This is a genuine gap, not a suppressed citation.

**CONSENSUS.** Keep the energy-balance form and **keep four of the six values**,
but rename the constant and re-derive each entry as `μ_roll` (Sadraey Table
4.15) `+ Δ_aero = 0.06`:

| Surface | Recommended `μ_eff` | Basis [derived from Sadraey T.4.15 + Δ_aero 0.06] |
|---|---|---|
| `hard_paved` (no brakes) | **0.10** ⬆ (was 0.07) | 0.04 rolling + 0.06 aero |
| `hard_paved_braked` | **0.40** (new) | Sadraey/Roskam braked dry paved |
| `grass_short` | **0.15** ✔ unchanged | 0.09 + 0.06 |
| `grass_long` | **0.22** ✔ unchanged | 0.16 + 0.06 |
| `soft_soil` | **0.30** ✔ unchanged | 0.24 + 0.06 |
| `belly_grass` | **0.40** ✔ unchanged | ~0.34 sliding fuselage + 0.06 |
| `net_recovery` | **special-cased, s_ground = 0** ✔ | correct as written |

Three accompanying changes:

- **Rename** `LANDING_SURFACE_MU` → `LANDING_DECEL_COEFF` (or keep the name and
  document it as `a/g`, *not* a friction coefficient). The present name invites
  a future reader to "correct" 0.15 down to Sadraey's 0.09 and silently make
  every landing 60 % longer.
- **Raise `hard_paved` from 0.07 to 0.10.** 0.07 is below any plausible
  unbraked deceleration once drag is counted, and it makes paved the *longest*
  rollout of any surface — physically correct but so counter-intuitive that a
  user will read it as a bug. Keeping it correct *and* explaining it in the UI
  ("smooth surface, no brakes → longest roll") is the right fix; adding the
  braked variant gives the user the lever they expect.
- **Replace the fixed 15 m flare** with a scaling air distance.
  `_LANDING_FLARE_M = 15.0` is simultaneously too long for a 0.5 kg foamie at
  6 m/s and too short for a 15 kg UAV at 20 m/s. Use
  **`s_air = h_obstacle · (L/D)_approach`** with `h_obstacle = 3 m` (an
  RC-realistic hedge/fence, user-settable) and `(L/D)_app` from the landing
  polar (typically 5–8 flaps-and-gear-down). For the 1.5 kg trainer this gives
  `3 × 6 = 18 m` — same order as today's 15 m, but it now scales [derived from
  the standard glide-path relation `s_air = h/tan γ`, `tan γ = 1/(L/D)`].
- **Keep the 1.5 safety factor** and keep it user-visible. It is the honest
  place to absorb the uncertainty that `μ_eff` still carries.

### Part B — the WCL conversion (this one is genuinely wrong)

**Three independent defects, all confirmable by dimensional analysis [derived]:**

1. **The unit label is not a unit.** `WCL = W/S^1.5` with `W` in oz and `S` in
   ft² has units **oz/ft³**, not `lb/ft^4.5`. There is no exponent arrangement
   that produces ft^4.5.
2. **The conversion constant is the wrong physical constant.** `47.88` is the
   **lb/ft² → N/m² pressure** factor. Applied to a `W/S^1.5` quantity it is
   simply the wrong dimension. The correct factors are
   **1 oz/ft³ = 9.818 N/m³** (force form) or **= 1.0012 kg/m³** (mass form).
3. **The derivation ignores weight and invents an AR dependence.** The correct
   translation of a WCL cap into a W/S cap is exact:

   ```
   WCL = W / S^1.5      and     S = W / (W/S)
   ⇒  WCL = (W/S)^1.5 / W^0.5
   ⇒  W/S_max = WCL_SI^(2/3) · W^(1/3)          [N/m², WCL_SI in N/m³, W in N]
   ```

   **AR does not appear.** WCL is a function of `W` and `S` only — at fixed `W`
   and `S`, changing AR changes nothing. The code's `AR^0.25` factor and its
   justifying comment ("higher AR → smaller chord → larger W/S allowed") are
   both incorrect. What *does* appear — and is currently missing — is the
   aircraft **weight**, which is the entire point of a cube loading: it is the
   size-corrected wing loading.

   Today's code returns **70.8 N/m² for trainer at AR = 7 for every aircraft
   regardless of mass** (and the docstring claims ~120 N/m², so the comment
   doesn't match the code either). The corrected formula gives 48.6 N/m² for a
   1.5 kg trainer and 72.7 N/m² for a 5 kg trainer — i.e. today's constant is
   accidentally calibrated for a ~5 kg model and is ~46 % too permissive for a
   small one.

**Attribution correction.** The code credits WCL to Lennon. Lennon's book
covers **wing loading in oz/ft²** (gliders <10–15, sport 15–20, pattern 23–26
— [[lennon-wing-loading]], *Ch. 4*); it does **not** cover wing cube loading.
WCL in oz/ft³ is Francis Reynolds' metric from the RC magazine literature — a
hobbyist source, and it should be labelled as one, not as Lennon.

**CONSENSUS.** Replace `_wcl_constraint` with:

```python
def _wcl_constraint(profile_key, weight_n):        # ar and g both dropped
    wcl_oz_ft3 = _WCL_UPPER_BY_PROFILE_OZ_FT3.get(profile_key)
    if wcl_oz_ft3 is None or weight_n <= 0:
        return None
    wcl_si = wcl_oz_ft3 * 9.818                    # N/m³
    return wcl_si ** (2.0 / 3.0) * weight_n ** (1.0 / 3.0)   # N/m²
```

with the standard RC bands **[RC — hobbyist, label as such]**:

| Profile | WCL upper bound [oz/ft³] | W/S at 1.5 kg | W/S at 5 kg |
|---|---|---|---|
| glider / sailplane / slope | **6** | 30.8 N/m² | 46.1 N/m² |
| trainer | **9** ⬆ (was 6) | 48.6 N/m² | 72.7 N/m² |
| sport / motor-glider | **12** ✔ | 58.9 N/m² | 88.1 N/m² |
| STOL / bush / scale warbird | **15** | 68.3 N/m² | 102 N/m² |
| wing-racer / acro-3D | **none** (unbounded) ✔ | — | — |

Cross-check against the independent RC wing-loading bands
([[wing-wing-area-wing-loading--wing-loading-as-a-practical-relation]], trainer
40–55 g/dm²): the corrected trainer bound at 1.5 kg is 48.6 N/m² = **49.6 g/dm²**
— dead centre of the band. The current code's 70.8 N/m² = 72 g/dm² is outside
it. **Raising trainer from 6 to 9 oz/ft³ is required**: 6 oz/ft³ is the
*glider* bound and at 1.5 kg it yields 37.8 N/m² = 38.5 g/dm², which would
declare every real RC trainer infeasible.

**Disagreement.** The WCL bands are hobbyist material with no academic
counterpart — Scholz/Sadraey have no cube-loading concept at all. That is not a
conflict, it is a scope boundary: **WCL is legitimate only as an RC-specific
additive constraint** (which is how `_PROFILE_CONSTRAINT_MAP` already scopes
it — trainer and sport only) and must never be applied to a UAV profile. The
current scoping is correct; keep it.

**Confidence: high** for the WCL fix (pure dimensional analysis, verifiable
without any new data). **Medium** for the friction table — the reinterpretation
is sound and the values survive it, but no measured RC rollout exists to pin
`Δ_aero = 0.06`. One instrumented landing (touchdown speed + measured roll)
would move it to high.

---

## Q-MS-11 — Are the `wing_loading` axis ranges unit-consistent?

**Question.** Mission presets use a 10–120 band; the "Ist" axis computes
`m·g/S_ref` in **N/m²**; `target_wing_loading_n_m2` defaults to **412**. Which
is in the intended unit? Also: a degenerate `axis_range` (`hi ≤ lo`) scores
`0.0` rather than `None`.

**What the code does today.**
`mission_kpi_service._kpi_wing_loading` (`:262`) returns `mass_kg · 9.81 / s_ref`
with `unit="N/m²"`. `mission_preset_seed.py` bands run 10–50 (sailplane) to
80–250 (wing_racer). `mission_objective_service._default_objective` (`:25`) sets
`target_wing_loading_n_m2=412.0`. `_normalise_score` (`:56`) maps
low→0, high→1 and returns `0.0` for `hi ≤ lo`.

**Scholz/Sadraey view.** Wing loading is the horizontal axis of the matching
chart and Sadraey's suggested plotting range is **5–100 lb/ft²** = 239–4788 N/m²
— i.e. a transport/GA range that is 5–500× above anything in this product
([[matching-chart-optimization]] step 2). Scholz/Sadraey confirm the *axis* and
the *formula* but supply no RC-scale range; the analytic content they do supply
is that the range must not start at zero (W/P terms contain 1/(W/S) and
diverge) — the code's `_WS_MIN = 10.0` already respects this.

**RC practice view [RC — hobbyist].** rcplanedesigner's own mission chart plots
**wing loading on a 10–120 g/dm² axis** against 500–2000 mm wingspan, with
bands: slowflyer ~10–45, trainer ~40–75, sport ~45–100, acrobatic ~50–95, and a
"danger zone" above ~95–110 g/dm²
([[wing-wing-area-wing-loading--wing-loading-as-a-practical-relation]]).
Lennon's oz/ft² figures convert to the same place: gliders <30–45 N/m², sport
45–60, pattern 69–78 [derived from [[lennon-wing-loading]]].

**CONSENSUS.**

1. **The unit is N/m² and the 10–120 band is correct.** Keep both. The reason
   nobody caught the ambiguity is a numerical coincidence:
   **1 g/dm² = 0.981 N/m²**, so the RC-practice band 10–120 g/dm² is
   9.8–117.7 N/m² — **the same band in both units to within 2 %**. The band is
   right either way; the formula `m·g/S_ref` fixes the unit as N/m². No change.

2. **`412` is the wrong number and it is not a unit error either** — it is a
   full-scale value that leaked in. 412 N/m² = **420 g/dm²**, roughly **4×
   above the RC "danger zone"** and in light-GA/ultralight territory. Set the
   default to **55 N/m² (≈ 56 g/dm²)**: the mid of the trainer band, matching
   `_default_objective`'s own `mission_type="trainer"`.

3. **`412` currently inverts the trainer's mission intent**, which makes this
   more than cosmetic. `_normalise_score` scores *higher* wing loading as
   *better*. With the trainer band 20–80 and a target of 412, the Soll score
   clips to **1.0** — maximum loading — while the trainer preset's declared
   `target_polygon["wing_loading"]` is **0.3**. The white Soll line and the
   orange Ist polygon are supposed to be directly comparable (gh-767); today
   the trainer's target wing-loading vertex is pinned at the wrong end of the
   axis.

4. **Show g/dm² as a secondary label.** RC modellers read g/dm², not N/m²
   [RC]. Keep N/m² as the stored/computed unit (SI, matches the formula, matches
   the matching chart's axis) and render `"55 N/m² (56 g/dm²)"`. Cheap, and it
   removes the ambiguity permanently.

5. **A degenerate `axis_range` must yield `None`, not `0.0`.** `hi ≤ lo` is a
   *configuration* fault, not a bad aircraft. Returning `0.0` renders a
   config error as a maximally-bad score on the radar — the one place in the
   system where an unknown is drawn as a failure. Return the `provenance="missing"`
   shape `_missing()` already produces, with a warning naming the offending
   axis. (This is the same principle as the `DEFAULT_E_OSWALD` ruling in
   Q-MS-4: degraded numbers must be visible, never silent.)

**Disagreement.** Scholz/Sadraey's plotting range (5–100 lb/ft²) and the RC band
(10–120 N/m²) differ by two orders of magnitude — but this is scale, not
conflict. Sadraey's range is for transports; his *method* (matching chart, W/S
axis, don't start at zero) is what transfers, and it does transfer unchanged.
Where the hierarchy would matter — a concrete RC number — Scholz is silent, so
RC practice supplies it legitimately.

**Confidence: high.** The unit is fixed by the code's own formula; the RC band
is corroborated by two independent RC sources (rcplanedesigner chart axis and
Lennon's oz/ft² figures) that agree after conversion.

---

## Q-MS-14 — Which `target_static_margin` default is authoritative?

**Question.** Three defaults coexist: `0.12` (`PARAMETER_DEFAULTS`), `0.10`
(inline in the SM-suggestion endpoint), and whatever the active mission preset
wrote. What is the right default for RC/UAV, and should it vary by mission type?

**What the code does today.**
`app/schemas/design_assumption.py:75` seeds `target_static_margin: 0.12`.
`app/api/v2/endpoints/aeroplane/sm_suggestions.py:74` does
`ctx.get("target_static_margin", 0.10)`. `mission_preset_seed.py` writes per
preset: trainer 0.15, sport 0.10, sailplane 0.10, wing_racer 0.05, **acro_3d
0.0**, stol_bush 0.15, slope_soarer 0.08, motor_glider 0.10, flying_wing 0.075.
`sm_sizing_service` uses `_SM_TAILLESS_TARGET = 0.075` for tailless.

**Scholz/Sadraey view.** `SM = (x_np − x_cg)/C̄`; static stability requires
`x_cg < x_np` as a **hard constraint** for all civil and most GA aircraft
(Sadraey Eq. 11.18, 11.22 — [[sadraey-longitudinal-stability-requirements]]).
Two quantitative anchors:

- **"A conventional aircraft becomes dynamically longitudinally unstable when
  the cg lies within roughly 2–3 % MAC of the neutral point"**
  ([[sadraey-longitudinal-cg-location]], *16_Sadraey §11.4*). This is the hard
  floor, and it is a *dynamic* statement — static stability alone is not enough.
- **"Typical stability margin requirement: 5–10 % mean aerodynamic chord"**
  ([[longitudinal-stability-cg-range]], *10_BoxWingSystematic §4.2*).

Sadraey's GA cg envelope is forward 15–20 % MAC, aft 25–30 % MAC, range 5–15 %
MAC ([[sadraey-weight-distribution-general-aviation]]) — narrower than
transports, and he notes that for **trainers and aerobatic types controllability
is deliberately emphasised over absolute static stability**, which is the
academic licence for low SM in those two missions.

**RC practice view [RC — hobbyist, two sources that disagree with each other].**

- **Lennon 1996:** power-on NP at **35 % MAC**, sport CG at **25 % MAC** ⇒
  **SM = 10 %**; stated **minimum 5 %**; CG at 33 % MAC called "dangerous"
  ([[lennon-cg-location-and-static-margin]], *Ch. 6*). Tailless: **SM = 5–10 %**
  ([[lennon-tailless-cg-static-margin]], *Ch. 23*).
- **rcplanedesigner mission table**
  ([[airplane-balance-finding-the-first-flight-cg--center-of-gravity-and-static-margin]]):

  | Mission | min | avg | max |
  |---|---|---|---|
  | Trainer | 5 % | 10 % | 15 % |
  | Sport | 3 % | 4 % | 5 % |
  | Acrobatic | 0 % | 1.5 % | 3 % |

  with the explicit caveat "for a first flight, place the CG at least 5 % of
  MAC ahead of the neutral point".

**Physics note.** `x_np` from a VLM is a **power-off, fuselage-free** neutral
point. Two effects at RC scale both push the *real* SM **lower** than computed:
the fuselage's Munk moment shifts the real NP **forward** (Sadraey ΔX_fus,
[[sadraey-longitudinal-cg-location]]), and Lennon notes the **power-on NP is
several % MAC forward of the power-off NP** — significant on a model where the
propeller slipstream covers a large fraction of the tail. A computed SM of
0.03 can therefore be a real SM near zero. This is the decisive argument
against adopting rcplanedesigner's acrobatic numbers as defaults.

**CONSENSUS.**

1. **Canonical resolver: one seeded default, and it is `0.10`, not `0.12`.**
   `0.12` matches no source in any of the three vaults. `0.10` is Lennon's sport
   value, the average of rcplanedesigner's trainer band, and the top of Scholz's
   "typical 5–10 % MAC". Change `PARAMETER_DEFAULTS["target_static_margin"]` to
   **0.10** and **delete the inline `0.10` in `sm_suggestions.py:74`** — read
   the resolver instead, so there is one place to change.

2. **Precedence is: user edit > active mission preset > seeded default.**
   The preset writing `estimate_value` on mission change (gh-549) is the correct
   mechanism; the seeded default is only the cold-start value before any mission
   is chosen. This is already the implemented behaviour — it just needs to be
   the *documented contract*, and the inline fallback removed so nothing bypasses
   it.

3. **Yes, it must differ per mission — and the seeded presets are already right
   except one.** Recommended targets, with the source for each:

   | Mission | Recommended SM | Current preset | Basis |
   |---|---|---|---|
   | trainer | **0.15** | 0.15 ✔ | rcplanedesigner max; Sadraey "conservative margins reduce training demands" |
   | stol_bush | **0.15** | 0.15 ✔ | wide payload cg travel [Sadraey, agricultural/utility] |
   | sport | **0.10** | 0.10 ✔ | Lennon sport CG 25 %/NP 35 % |
   | sailplane | **0.10** | 0.10 ✔ | Lennon; long-period stability wanted for thermalling |
   | motor_glider | **0.10** | 0.10 ✔ | as sailplane |
   | slope_soarer | **0.08** | 0.08 ✔ | between sport and sailplane |
   | flying_wing | **0.075** | 0.075 ✔ | Lennon tailless 5–10 %, mid |
   | wing_racer | **0.05** | 0.05 ✔ | Lennon's stated *minimum*; rcplanedesigner sport max |
   | **acro_3d** | **0.03** | **0.0** ✗ **change** | see below |

4. **`acro_3d = 0.0` must become `0.03`.** A target of exactly zero means "put
   the CG on the neutral point" — by Sadraey Eq. 11.17 that is `C_mα = 0`,
   neutral static stability, and by his §11.4 statement it is *inside* the
   dynamically-unstable band (within 2–3 % MAC of NP). Combined with the physics
   note above (real NP is forward of the computed one), a **0.0 target is a
   design tool instructing the user to build an unflyable aeroplane.** 0.03 is
   the top of rcplanedesigner's acrobatic band and the edge of Sadraey's
   instability band — the lowest number defensible as a *default*. Expert 3D
   pilots do fly at ~1.5 % SM; that is a deliberate override, not a default.

5. **Add a hard classification floor, matching ADR 0011's existing SM ladder:**
   **error below SM = 0.02**, **warning below SM = 0.03** — both anchored to
   Sadraey's 2–3 % MAC dynamic-instability statement, which is now the citation
   ADR 0011 corollary 4 is missing for its `<0.02 error` threshold.

6. **`_SM_TAILLESS_TARGET = 0.075` is correct — keep it.** It is exactly the mid
   of Lennon's tailless 5–10 % band and agrees with the `flying_wing` preset.

7. **On the wider duplicate-defaults problem** (`_default_profile()` vs
   `mission_preset_seed` vs `PARAMETER_DEFAULTS`, e.g. cruise 18 m/s in two
   places): the mission preset is the design-intent layer and must be the single
   author of mission-shaped defaults. `PARAMETER_DEFAULTS` should carry only
   values with **no** mission dependence (ρ, g). Cruise speed, g-limit, CL_max,
   power-to-weight and static margin are all mission-shaped and belong to the
   preset alone.

**Disagreement — genuine, and the hierarchy resolves it.**
rcplanedesigner gives **Sport avg 4 %** and **Acrobatic avg 1.5 %**. Sadraey
states a conventional aircraft is **dynamically unstable within 2–3 % MAC of the
NP**. These directly contradict each other: rcplanedesigner's acrobatic average
sits inside Sadraey's instability band and its acrobatic *minimum* is zero.
**Per the project hierarchy, Scholz/Sadraey wins.** The recommendation above
therefore sets acro at 0.03 (Sadraey's boundary, rcplanedesigner's max) rather
than 0.015 (rcplanedesigner's average), and sport at Lennon's 0.10 rather than
rcplanedesigner's 0.04. The reconciliation is real, not diplomatic: a
1 m aerobatic model flown line-of-sight has time constants short enough for a
skilled pilot to fly a marginally unstable airframe by hand — but a **default**
in a tool that also serves UAVs and first-time builders cannot assume that pilot.
Expose 0.015 as a documented expert override; never ship it as the default.

**Confidence: high** on the ordering and on rejecting 0.0 and 0.12. **Medium**
on the exact acro value (0.03 vs 0.05) — the 2–3 % MAC figure is Sadraey's
statement for *conventional* aircraft, and a small, high-thrust 3D model is not
that. A flight-test log from the maintainer's own 3D models would settle it.

---

## Q-MB-2 — Is `x_np − SM·MAC` the right top-down CG rule, and where should it live?

**Question.** ADR 0011's central rule is implemented three times, one with no
production caller. Is the formula itself correct as a top-down CG target, and
what are the caveats at this scale?

**What the code does today.** `mass_cg_service.compute_recommended_cg`
(`app/services/mass_cg_service.py:36`) is `np_x − target_static_margin · mac` —
unit-tested, **no production caller**. Production re-derives it in
`loading_scenario_service.compute_stability_envelope` and in
`assumption_compute_service` (step 6 of `recompute_assumptions`).
`RecommendedCGRequest`/`Response` (`app/schemas/mass_cg.py:8-23`) are returned by
no endpoint.

**Scholz/Sadraey view.** The formula is **exactly correct** — it is Sadraey
Eq. 11.18 rearranged: `SM = (x_np − x_cg)/C̄ ⇒ x_cg = x_np − SM·C̄`
([[sadraey-longitudinal-stability-requirements]], *§11.6.2*). The *direction* of
the design loop that ADR 0011 asserts is also Sadraey's: "one of the explicit
objectives of aircraft configuration design is to **achieve the best possible cg
location**… the ideal cg becomes a **target** for weight distribution.
Components are then placed to drive the actual cg toward the ideal"
([[sadraey-ideal-cg-location]], *§11.3.3*). ADR 0011 is not a house opinion —
it is textbook methodology, and the ADR can cite it.

**RC practice view.** Identical procedure, stated as a build workflow: Lennon's
"balancing act" places a fulcrum **at the design CG** and moves components until
the beam balances — design CG first, components second
([[lennon-balancing-act]], *Ch. 6*). Lennon's own worked instance is
`NP = 35 % MAC`, `CG = 25 % MAC`, `SM = 10 %` — the same equation.

**Caveats at this scale (all four are real, none invalidates the formula).**

1. **Units.** `x_np` and `MAC` must be in the same frame and unit. The codebase
   carries an mm/m dualism (WingConfig mm, DB/ASB m). Whichever module owns the
   rule must take metres and say so in the signature.
2. **Which `x_np`?** A VLM neutral point is **power-off and (depending on the
   model) fuselage-free**. Both corrections move the real NP **forward**, so the
   *achieved* SM is **smaller** than the computed one — the error is in the
   unsafe direction. [Scholz: Munk fuselage shift ΔX_fus,
   [[sadraey-longitudinal-cg-location]]. RC: Lennon, power-off NP is several %
   MAC aft of power-on.] The context should record which NP it used, and the
   classifier's warning bands (Q-MS-14 item 5) should be read as applying to a
   *computed* SM that is optimistic by a few % MAC.
3. **It is a target, not a limit.** `x_np − SM_target·MAC` is the design CG.
   The **aft limit** is `x_np − SM_min·MAC`; the **forward limit** comes from
   elevator authority, not from this formula. ADR 0011 corollary 3 already says
   this — it just must not be conflated in the implementation.
4. **Tailless.** For a flying wing, NP ≈ wing AC, so the formula is unchanged but
   the SM band tightens to 5–10 % and CG sensitivity is much higher: "conventional
   aircraft can tolerate CG shifts of several percent MAC; tailless aircraft
   cannot" ([[lennon-tailless-cg-static-margin]]).

**CONSENSUS.**

- **The formula is correct and needs no change.** Cite Sadraey Eq. 11.18 in
  ADR 0011 so the project's central rule stops looking like an unsourced house
  convention.
- **`mass_cg_service.compute_recommended_cg` should be the single
  implementation, and the other two must delegate to it.** It is the only one of
  the three that is a pure function of exactly the three inputs the rule needs,
  it is the one already unit-tested, and it lives in the module whose name
  matches its subject. Three implementations of one two-term formula is three
  places for a sign or unit error.
- **Do not add a `/recommended_cg` endpoint.** It is superseded: the
  stability-envelope endpoint returns the same number *plus* the aft/forward
  limits and the classification, which is strictly more useful and is what the
  UI needs. Delete `RecommendedCGRequest`/`RecommendedCGResponse` rather than
  wiring a route to satisfy them.
- **Extend the signature to carry the caveat**, not just the number — return the
  NP provenance (power-on/power-off, fuselage-included yes/no) alongside
  `x_cg`, so the caveat in item 2 reaches the user instead of living in a
  comment.

**Disagreement.** None. Scholz/Sadraey, Lennon and the ADR agree on both the
formula and the design-loop direction.

**Confidence: high** on the formula and on the delegation. **Medium** on the
magnitude of the NP correction in item 2 — quantifying the fuselage/slipstream
shift for RC-scale bodies would need either a fuselage-inclusive panel run or
flight data.

---

## Q-MB-6 — What is the sign convention of `delta_x`?

**Question.** `delta_x = cg_x_design − cg_x_components`, so a positive delta
means the design CG is aft of the components' CG. Nothing in the code says so,
and a UI can invert it silently. What convention is least error-prone for a user
being told "move the battery"?

**What the code does today.** `mass_cg_service.py:238` —
`delta_x = design_cg_x − cg_x`, `within_tolerance = abs(delta_x) < 0.01`,
serialised on `CGComparisonResponse` as a bare signed float with no documented
axis direction and no verdict token.

**Scholz/Sadraey view.** Sadraey never publishes a signed delta. He publishes
**non-dimensional positions** — `h = (x_cg − x_LE_MAC)/C̄`, with `h_for` and
`h_aft` (Eqs. 11.11–11.13, [[sadraey-longitudinal-cg-location]]) — and the
corrective action is expressed **categorically**: when the cg cannot be brought
into range by weight distribution, **ballast** is added, at a named location. He
also gives the forward-vs-aft consequence table (forward: more stable, less
controllable, more nose-wheel load, more elevator to rotate; aft: the reverse) —
i.e. the meaningful output is *which side you are on*, not a raw number.

**RC practice view.** Identical, and even more explicit. Lennon's balancing-act
procedure produces exactly two verdicts and a named action for each:
**"Tail-heavy: move power, nosewheel and possibly fuselage servos forward…
Nose-heavy: best solution is to move the wing forward"**
([[lennon-balancing-act]], *Ch. 6*). No modeller reasons about a signed
`Δx`; they reason about *nose-heavy* vs *tail-heavy*.

**CONSENSUS.** Keep the arithmetic; change what is published.

1. **State the axis convention in the contract explicitly**: *x is positive aft,
   measured from the aircraft datum.* Everything else is undefined without it.
2. **Rename the field to encode the direction.**
   `delta_x` → **`required_cg_shift_x_m`**, defined as *"the distance the
   aggregate (component) CG must move to reach the design CG; **positive = move
   mass aft**."* The value is unchanged (`cg_design − cg_agg`); the name now
   carries the meaning, so a frontend cannot get it backwards by reading the
   field name alone.
3. **Ship a categorical verdict alongside it, and make the UI drive off the
   token, not the sign** — this is the actual defence against inversion:
   `cg_verdict ∈ {NOSE_HEAVY, TAIL_HEAVY, ON_TARGET}`, where
   `NOSE_HEAVY` ⇔ `required_cg_shift_x_m > +tol` (components are forward of the
   design CG ⇒ move mass **aft**), `TAIL_HEAVY` ⇔ `< −tol`, `ON_TARGET`
   otherwise. A sign error in the frontend then produces a *contradiction*
   between token and number instead of a silently inverted instruction.
4. **Report the shift in % MAC as well as metres.** `Δx/MAC` is the number both
   authorities actually use, it is scale-free, and at RC scale a 10 mm shift is
   ~3 % MAC on a 300 mm chord but ~1 % on a 1 m chord — the metre value alone
   does not tell the user whether it matters.
5. **On the tolerance:** `CG_TOLERANCE_M = 0.01 m` is a fixed absolute. For
   consistency with item 4 it should be relative — **1 % MAC**, floored at
   5 mm for buildability. On a 300 mm MAC that is 3 mm, i.e. the current 10 mm
   is 3.3 % MAC and would pass a CG error large enough to be felt in pitch.

**Disagreement.** None — Scholz/Sadraey and RC practice independently arrive at
"publish the side, not just the signed scalar".

**Confidence: high.** This is a contract/ergonomics ruling, and both authorities
converge on it.

---

## Q-MS-6 — Should the operating point store its trimmed CL so V-n markers land correctly?

**Question.** `turn_20/40/60` operating points plot on the **1-g line** of the
V-n diagram. Should the OP store its trimmed CL (or `n_target`) so the marker is
placed correctly — and is using an untrimmed CL for V-n markers actually wrong?

**What the code does today.** `flight_envelope_service._load_operating_point_markers`
(`:589`) sets `n = 1.0` for **every** operating point with the comment
"Without stored CL, we cannot derive actual load factor". The function accepts
`mass_kg` and `wing_area_m2` and uses neither. Meanwhile
`operating_point_generator_service._build_target_definitions` (`:497`) already
computes `n_target = round(1.0/cos(radians(bank)), 4)` for banks 20/40/60 — the
exact number the marker needs — and discards it after trimming.

**Physics note (this is the whole answer).** In a steady, coordinated level
turn at bank angle φ, the vertical component of lift carries the weight:
`L·cos φ = W ⇒ n ≡ L/W = 1/cos φ` — exact, from force balance alone. So
`turn_20 → n = 1.064`, `turn_40 → n = 1.305`, `turn_60 → n = 2.000`.
Independently, from the definition of the lift coefficient
(`L = q·S·C_L`, [[airplane-drag-polar]], *Anderson §6.7.2*),
`n = q·S·C_L/W` — so a stored **trimmed** `C_L` recovers `n` exactly, and the
two routes must agree to within the trim solver's residual. **Plotting a 60°
turn point at n = 1.0 is not an approximation, it is a factor-of-two error in
the plotted quantity.** The turn markers exist for exactly one purpose — to show
how close a manoeuvre gets to the g-limit — and placing them on the 1-g line
deletes that purpose entirely.

**Scholz/Sadraey view.** Corroborates the consequence: Sadraey's `n_max` for a
remote-controlled model is **1.5–2** ([[sadraey-ultimate-load-factor-aircraft]],
*§10.4.1*). A 60° turn at `n = 2.0` therefore sits **at or above** the load
factor Sadraey assigns to the entire model-aircraft class — which is precisely
the finding the diagram should be surfacing and currently cannot.

**CONSENSUS.**

1. **Yes — persist both, they answer different questions.**
   - **`n_target`** (the commanded load factor) — persist it; it is exact for
     the marker, already computed, and costs one column.
   - **`cl_trimmed`** (the CL the solver converged on) — also persist it. It
     lets `n` be *re-derived* at a different mass or density without re-running
     the sweep, which is what makes the marker survive a mass edit. It is also
     the only way to detect that the trim solution disagrees with the commanded
     `n` (i.e. the point did not actually achieve the turn).
2. **Marker placement rule:** `n = q·S·C_L,trim/(m·g)` when `cl_trimmed` is
   present and the point is `TRIMMED`; otherwise fall back to `n_target`;
   otherwise 1.0 **with the marker flagged as unverified**, never silently.
3. **This will expose a second, real defect — that is a feature.** The generator
   sets the turn velocity to `max(cruise, 1.3·V_S)` (`:494`). The stall boundary
   at load factor `n` is `V_stall(n) = V_S·√n`, so a 60° turn requires
   `V ≥ 1.414·V_S`. At `1.3·V_S` the `turn_60` point lies **inside the stall
   boundary** — a stalled turn. Today it is hidden on the 1-g line where
   `1.3·V_S` looks perfectly safe. Once placed correctly it will visibly fall
   left of the manoeuvre boundary, which is the diagram doing its job. Either
   raise the turn velocity to `max(cruise, 1.05·V_S·√n_target)` or let the
   marker land outside and rely on the existing `STALL_IN_TURN` warning — but
   the warning must then be emitted as a **bare token**, not the formatted
   sentence noted in Q-MS-12, so a consumer can match it.

**Disagreement.** None. This is force balance; there is nothing to disagree
about.

**Confidence: high.** `n = 1/cos φ` and `n = q·S·C_L/W` are both exact for the
steady level turn, and the generator already holds the value.

---

## Q-MS-7 — What is the intended marker → KPI mapping?

**Question.** `derive_performance_kpis` looks up markers labelled `best_ld`,
`min_sink`, `max_turn`, but `VnMarker.label` is the operating point's *name* and
the generator emits `max_range`, `loiter_endurance`, `turn_60`, … so the
`"trimmed"` confidence tier is unreachable. Role field on the marker, or
nearest-match against the context's `v_md_mps`/`v_min_sink_mps`?

**What the code does today.** `flight_envelope_service.py:393` builds
`markers_by_label = {m.label: m for m in markers}` and looks up the three
literal keys at `:410`, `:446`. The generator's fifteen names
(`operating_point_generator_service.py:404-508`) contain none of them. The
marker's `status` is **not checked** before the `"trimmed"` label is applied
(`:419`), so a `NOT_TRIMMED` point named `best_ld` would still be reported as
trimmed.

**Scholz/Sadraey + physics view — what the correct mapping *is*.** For a
**propeller** aircraft (which every airframe in scope is):

- **Maximum range** occurs at **minimum drag**, i.e. at maximum L/D, i.e. at
  `V_md`. ⇒ `best_ld` ← **`max_range`**.
- **Maximum endurance** occurs at **minimum power required**, i.e. maximum
  `C_L^1.5/C_D`, i.e. at minimum sink speed ≈ `0.76·V_md`.
  ⇒ `min_sink` ← **`loiter_endurance`**.
- ⇒ `max_turn` ← **`turn_60`** (the highest-bank point generated).

(The prop-vs-jet distinction matters and is the reason this mapping is not
arbitrary: for a jet the range point would be at `V_md·3^0.25`, not `V_md`.
Scholz's KPI axis `target_climb_energy` is already defined as `C_L^1.5/C_D`
in `mission_kpi_service`, so the project already uses the prop convention
consistently.)

**Why renaming alone is the wrong fix.** The generator's speeds for those two
points are **heuristics**, not polar solutions: `max_range` is
`max(1.25·V_S, 0.95·cruise)` and `loiter_endurance` is
`max(1.15·V_S, 0.80·cruise)` (`:448-461`). Mapping by name would promote a
heuristic speed to confidence **`"trimmed"`** — strictly worse than the current
dead tier, because a heuristic would then wear the highest-confidence badge in
the system. The polar-derived `v_md_mps`/`v_min_sink_mps` in the context are the
*better* numbers today; that is why tier 2 ("computed") exists.

**Nearest-match is also wrong.** Matching the context's `v_md_mps` to the
nearest operating point is unstable — two adjacent points can swap roles when a
speed shifts by 0.1 m/s — and it would still stamp "trimmed" on a point that is
merely *near* `V_md`.

**CONSENSUS.** Three changes, all required together:

1. **Add an explicit `role` field to the operating point**, set by the
   generator: `role ∈ {best_ld, min_sink, max_turn, cruise, takeoff, approach,
   stall_clean, stall_flaps, vx, vy, v_max, dutch_roll, none}`. The KPI
   derivation keys off `role`, never off `name`. Names stay free-form and
   user-editable; roles are the contract.
2. **Gate the `"trimmed"` tier on two conditions, not one.**
   The tier applies only when **(a)** `marker.status == TRIMMED`, **and**
   **(b)** the point's velocity is within **5 %** of the polar's `v_md_mps` /
   `v_min_sink_mps`. Otherwise fall through to the polar value at confidence
   `"computed"`. The 5 % band is deliberate: L/D is a smooth maximum and stays
   within ~1 % of its peak over roughly ±10 % of `V_md`, so a 5 % speed
   tolerance costs well under 1 % in the reported KPI while excluding a point
   that is merely in the neighbourhood.
   Condition (a) alone is already a bug fix — the missing status check would
   mislabel a `NOT_TRIMMED` point as trimmed regardless of how the mapping is
   done.
3. **Better still, make the generator honest**: seed `max_range` at the
   context's `v_md_mps` and `loiter_endurance` at `v_min_sink_mps` whenever a
   polar exists, falling back to the `1.25·V_S`/`1.15·V_S` heuristics only at
   cold start. Then condition (b) is satisfied by construction, the tier becomes
   reachable for real, and the reported KPI is a genuinely trimmed value rather
   than a polar estimate.

**Disagreement.** None between authorities; the question is a design choice and
the physics decides it (prop range at `V_md`, prop endurance at min sink).

**Confidence: high** on the role mapping. **Medium** on the exact 5 % tolerance
— the flatness argument supports anything in 3–10 %; 5 % is the recommendation,
not a derived optimum.

---

## Q-MS-8 — Flight-envelope inconsistencies (bundle)

Five items. Rulings on each; items 1–3 are physics-decided, 4–5 are contract
consistency where the physics only sets the requirement.

### 8.1 — Two `V_max` fallbacks for one number

**Code today.** `flight_envelope_service._get_v_max` (`:577`) returns a bare
**`28.0`** when the flight profile has no `max_level_speed_mps`; the operating-
point generator (`:399`) uses `max(1.35·V_cruise, V_cruise + 8)`. `V_dive`,
`max_speed` and `dive_speed` all ride on whichever fires.

**Ruling.** **One source, and a bare constant is not it.** A hard-coded 28 m/s
is a 3 kg sport model's top speed asserted for a 0.5 kg slow-flyer and a 15 kg
UAV alike. The app **already computes** the physically right quantity —
`assumption_compute_service._max_level_speed` (`:1863`) solves the power balance
`P_avail·η_prop = D(V)·V`. Precedence:

1. user's declared `goals.max_level_speed_mps` (an explicit requirement);
2. **`V_H` from the context's computed power balance** (the physics answer);
3. `1.35·V_cruise` (matches typical RC `V_H/V_cruise`) **with the envelope
   flagged `V_MAX_ESTIMATED`**;
4. never a bare constant.

**Speed chain.** Define it once and cite it:
`V_C = 0.9·V_H` [CS-VLA 335(a): V_C need not exceed 0.9 V_H] and
`V_D = 1.4·V_C` [CS-23/FAR-23 §23.335(b) normal/utility minimum]. Note this
changes the *base*, not the factor — today's `v_dive = 1.4·v_max` uses `V_H`
where the regulation uses `V_C`. Also fix the internal
`v_c = v_dive/1.4` in `_build_gust_lines` (`:189`), which currently makes
`V_C ≡ V_H` and therefore anchors the gust-velocity taper at the wrong speed.
**Caveat to surface in the UI:** at RC scale nothing enforces `V_D` — a model in
a vertical dive routinely exceeds it. `V_D` is a *design reference*, not a limit
the airframe imposes, and the envelope should say so.

### 8.2 — ρ fixed at sea-level 1.225 while the profile carries `altitude_m`

**Code today.** `compute_vn_curve` (`:283`) takes `rho: float = 1.225` and is
called without an altitude-corrected value, so `profile.environment.altitude_m`
— which shapes every operating point — never reaches the envelope.

**Ruling — the fixed ρ is CORRECT, and the bug is elsewhere.** A V-n diagram is
conventionally drawn in **equivalent airspeed**, and in EAS `ρ_SL` is the only
density that may appear: `V_E` is *defined* by
`½ρ_alt·V_TAS² = ½ρ_SL·V_E²` ([[pitot-tube-airspeed]], *Anderson*), so both the
manoeuvre boundary `n = ½ρ_SL·V_E²·S·C_Lmax/W` and the Pratt-Walker gust
increment are altitude-independent when expressed in EAS. Keeping `1.225` is
what makes the diagram a single, altitude-free chart.

**The actual defect is a mixed-airspeed bug.** The operating points are trimmed
*at altitude* and their velocities are **TAS**; they are then plotted on an EAS
diagram. Fix:

- **Label the axis "EAS"** (it is currently unlabelled as to airspeed type,
  which is how the inconsistency survived).
- **Convert marker velocities:** `V_E = V_TAS·√(ρ_alt/ρ_0)`.
- Magnitude at RC altitudes [derived, ISA]: 500 m → 2.4 % low; 1000 m → 4.8 %;
  2000 m → 9.4 %. Small but silent, and it compounds with the load-factor error
  from Q-MS-6.

### 8.3 — An absent gust envelope is completely silent

**Code today.** When `b_ref` or `CL_α` is missing, `gust_lines_*` are empty with
no warning and no log line; `_get_b_ref`'s bare `except Exception: return None`
(`:632`) has already discarded the reason.

**Ruling — not acceptable, and this is the *most* important warning in the
module, not the least.** Scholz gives the gust sensitivity as
`n_α = dn/dα = ½·ρ·v²·C_Lα/(W/S)` — **inversely proportional to wing loading**
([[wing-loading-gust-response]], *07_WingDesign §7.3*). At 40–60 N/m² an RC
model is ~10× more gust-sensitive than a light GA aircraft at ~600 N/m². For
this product's class the gust envelope is frequently the **structurally sizing**
case, which is exactly what the existing `GustCriticalWarning` is designed to
detect. Silently omitting the gust lines therefore removes the one output most
likely to change the design.

The module already demonstrates it knows this regime is marginal — it emits a
`GustValidityWarning` when `μ_g < 3` because "RC/UAV with low W/S frequently
produce μ_g < 3, making gust loads potentially optimistic" (gh-497). Requirements:

- emit a structured warning naming the **specific** missing input
  (`GUST_ENVELOPE_UNAVAILABLE: b_ref` / `: cl_alpha`), never an empty array;
- replace the bare `except` with a logged, typed failure that preserves the
  reason;
- the Helmbold fallback for `C_Lα` already exists and is fine — but when *it*
  is used, the gust lines should carry a reduced-confidence marker, since
  Helmbold is a lifting-line approximation, not the aircraft's actual `C_Lα`.

### 8.4 — `assumptions_snapshot` records only `{mass, cl_max, g_limit}`

**Ruling — insufficient; a row can be silently stale with respect to half its
inputs.** The snapshot must identify **every input that shapes the stored
output**. That set is:

`mass_kg`, `cl_max`, `g_limit`, `s_ref_m2`, `b_ref_m`, `cl_alpha_per_rad`
(+ whether it was Helmbold-derived), `rho`/`altitude_m`, `v_h_mps` **and its
provenance** (declared / computed / estimated), `v_c_mps`, `v_d_mps`,
`v_md_mps`, `v_min_sink_mps`, `gust_u_vc/vd`.

Plus a **context hash**. `mission_kpi_service._hash_context` (`:392`) already
implements exactly this (stable SHA-256 over the sorted context) — reuse it
rather than writing a second one. Storing the hash makes staleness a one-line
check instead of a field-by-field comparison, and it automatically covers
context keys added later.

### 8.5 — Cold-start conditions reported as 500s

**Ruling — 422 with a remediation sentence, matching the sibling endpoints.**
A wingless aircraft and a non-positive `cl_max` are **user-state** conditions,
not server faults: the user has not finished defining the aircraft. The
matching-chart and field-length endpoints already answer 422 with a remediation
sentence for the same class of condition (`field_length_service.py:457-463` is
the model to copy: *"…is required for takeoff_mode='…'. Set t_static_N via
Design Assumptions or provide a measured value."*). Two endpoints giving
different treatment to the same mistake is the user-facing defect here; the
physics is not in dispute. Recommended messages:

- no wings → *"No wing defined — add a wing before computing the flight
  envelope."*
- `cl_max ≤ 0` → *"CL_max is not available. Run the aerodynamic analysis to
  compute the polar, or set cl_max in Design Assumptions."*

**Disagreement across the bundle.** None between authorities. Item 8.2 is the
only place where the code turns out to be right for a reason the code does not
state — worth capturing in the requirements so it is not "fixed" later.

**Confidence: high** on 8.2, 8.3, 8.5 (physics and consistency, both decidable).
**Medium** on 8.1's exact `V_C`/`V_D` factors — the CS-VLA/CS-23 numbers are
being borrowed by analogy for uncertificated models, and the honest position is
that `V_D` at RC scale is set by pilot discipline, not by structure.

---

## Summary table

| Q-id | Recommendation in one line | Confidence |
|---|---|---|
| **Q-MS-2** | The gh-477 energy balance is the authoritative landing distance; Roskam §3.4 is calibrated on a braked Cessna 172N (μ_brake = 0.4) and is invalid for unbraked 0.5–15 kg models — keep it only for `ga_runway` or delete; `t_static_N` on `mission_objectives` wins (gh-548 + it is a propulsion input, not a design assumption). | high |
| **Q-MS-3** | `LANDING_SURFACE_MU` is a **deceleration coefficient a/g**, not tyre friction — rename it, keep 0.15/0.22/0.30/0.40, raise `hard_paved` 0.07 → 0.10, add braked 0.40, replace the fixed 15 m flare with `h_obs·(L/D)_app`; the WCL constant is wrong three ways — use `W/S_max = (WCL[oz/ft³]·9.818)^(2/3)·W^(1/3)`, drop the spurious `AR^0.25`, and raise trainer from 6 to 9 oz/ft³. | high (WCL) / medium (μ) |
| **Q-MS-11** | Unit is **N/m²** and the 10–120 band is right (1 g/dm² = 0.981 N/m², so it is correct in both units to 2 %); **412 is a full-scale value — set the default to 55 N/m²**, show g/dm² as a secondary label, and return `None` not `0.0` for a degenerate axis range. | high |
| **Q-MS-14** | Seeded default **0.10** (not 0.12), delete the inline 0.10 in `sm_suggestions.py`, precedence user > preset > default; presets are already correct **except `acro_3d = 0.0`, which must become 0.03** (Sadraey: dynamically unstable within 2–3 % MAC of NP); add error < 0.02 / warning < 0.03. | high |
| **Q-MB-2** | The formula is exactly Sadraey Eq. 11.18 and is correct — cite it in ADR 0011; make `mass_cg_service.compute_recommended_cg` the single implementation and have the other two delegate; drop the dead `/recommended_cg` schemas; return the NP provenance because a VLM `x_np` is power-off and fuselage-free, so real SM is *smaller* than computed. | high |
| **Q-MB-6** | Keep `cg_design − cg_agg`, but rename to `required_cg_shift_x_m` ("positive = move mass aft"), state "x positive aft from datum" in the contract, and ship a categorical `cg_verdict ∈ {NOSE_HEAVY, TAIL_HEAVY, ON_TARGET}` that the UI drives off instead of the sign; also report Δx in % MAC and make the tolerance 1 % MAC (floor 5 mm) rather than a fixed 10 mm. | high |
| **Q-MS-6** | Yes — persist **both** `n_target` and `cl_trimmed`; `n = 1/cos φ` exactly, so `turn_60` at n = 1.0 is a factor-of-two error, not an approximation; correct placement will also expose that the turn velocity `1.3·V_S` is inside the stall boundary at 60° bank (needs `≥ 1.414·V_S`). | high |
| **Q-MS-7** | Add an explicit `role` field (`best_ld` ← `max_range`, `min_sink` ← `loiter_endurance`, `max_turn` ← `turn_60` — the prop-aircraft mapping); gate the `"trimmed"` tier on `status == TRIMMED` **and** within 5 % of the polar `v_md`/`v_min_sink`; best fix is to seed those two points at the polar speeds so the tier is genuinely reachable. Nearest-match is unstable — reject it. | high |
| **Q-MS-8** | (1) One `V_max`: declared → computed `V_H` → 1.35·V_cruise, never a bare 28.0; `V_C = 0.9·V_H`, `V_D = 1.4·V_C`. (2) **ρ = 1.225 is correct** — a V-n diagram is an EAS chart; the real bug is plotting TAS markers on it (label the axis EAS, convert with `√(ρ_alt/ρ_0)`). (3) A missing gust envelope must warn with the named missing input — gust sensitivity ∝ 1/(W/S), so it is *most* critical at this scale. (4) Snapshot every shaping input plus a context hash (reuse `_hash_context`). (5) Cold start → 422 with a remediation sentence, like the sibling endpoints. | high (8.2–8.5) / medium (8.1) |
