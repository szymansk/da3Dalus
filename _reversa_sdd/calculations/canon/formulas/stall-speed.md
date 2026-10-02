---
canon: stall-speed
entry: formula
kind: optimization
shape: law
status: draft
output: stall-speed, max-lift-coefficient, stall-speed-landing, stall-speed-takeoff
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
  - flag/conflict
tex: \begin{aligned}V_S = \min_{V,\,\alpha}\; & V \\ \text{u.d.N.}\; & L(V,\alpha) = n\,m\,g\end{aligned}
---

# Stall speed from the lift balance at C_L,max

**Canonical form**

```
minimize over V, alpha:   V
subject to:               L(V, alpha) = n * m * g
```

**Produces** [[stall-speed]] · [[max-lift-coefficient]] · [[stall-speed-landing]] · [[stall-speed-takeoff]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[load-factor]] · [[air-density]]

**One relation, two directions.** This entry is the lift balance solved for the speed at the named condition C_L = C_L,max. [[lift-coefficient-required]] is the same relation, `n·m·g = ½·ρ·V²·S_ref·C_L`, solved the other way. Every time the sources solve it for a speed, the C_L belongs to a named condition (Sadraey Eq. 4.30, 4.55, 4.85; Scholz Eq. 5.30, 5.40) — there is no generic lift-balance speed, which is why `lift-balance-speed` was deleted on 2026-10-01.

**Kind: an optimisation problem.** The value is the solution of a stated optimisation, solved by IPOPT through `asb.Opti` with AeroBuildup inside the constraint. The coupling through Reynolds number is not drawn as a cycle: it sits inside the constraint, because AeroBuildup forms the Reynolds number from `V` per wing section. Approval asks, on top of source and scale: **no bound active at the optimum**, and **what is returned when the solver fails** — never a value.

**Dimensional check.** ⚪ procedural — an optimisation problem, not an expression

**Source.** 🟢 SOURCED

> Sadraey §4.3.2 Eq. 4.30: L = W = 0.5*rho*V_s^2*S*C_L,max. Scholz 05_PreliminarySizing §5.1 for the landing-configuration instance. Anderson FoA 6e §4.13 for the underlying statement V_stall proportional to 1/sqrt(c_l,max).

**Validity at 0.5–15 kg.** The EQUATION is exact; the INPUT is where 0.5-15 kg scale bites hardest, and this is the most important qualification in the whole register. Lennon (Basics of R/C Model Aircraft Design, Ch. 1-3, 'Reynolds Number and Scale Effect') documents NACA 0012 C_L,max falling from 1.55 at high model Rn to 0.83 at low model Rn - a 46% loss - with stall AoA dropping 17 deg to 10 deg and profile drag nearly doubling. Since V_S scales as C_L,max^-0.5, a handbook or 2D C_L,max makes V_S optimistic by up to ~35%. The 3D wing value is lower again than the section value. Any V_S the app reports must carry the Reynolds number it was evaluated at, or it is not a safety number.


## Rebuilt 2026-10-01 — an optimisation problem, not a closed form

**The stall speed is the smallest speed at which the aircraft still carries its weight.**
Written that way it needs no fixed point: the optimiser chooses `V` and `alpha` together,
and the Reynolds dependence of the polar is inside the constraint.

**The approved relation survives as the optimality condition — and as the Probe.** At the
optimum, `V_S = sqrt(2·n·m·g / (rho·S_ref·C_L))` with `C_L` the lift coefficient there.
Plugging the optimiser's `C_L` into the closed form must return its `V_S`; a mismatch is a
defect. Sadraey Eq. 4.30 is unchanged — what changed is how it is evaluated at low Re.

**Second output: `C_L,max,stall`.** The lift coefficient at the optimum *is* the maximum
lift coefficient at the stall condition — exactly the quantity the precondition below
asks for, and exactly what A2 says its name must carry. It replaces `clmax-from-polar`,
which took a maximum over a velocity grid and so returned the value at the wrong speed.
One authority for C_L,max.

**Verified** on a 1.5 kg trainer (NACA 2412, 1.4 m span): optimiser 8.4888 m/s at
alpha = 15.8°, C_L = 1.191; fixed-point iteration 8.4891 m/s after three sweeps —
0.004 % apart. A fleet comparison is outstanding before approval of the method.

**Configuration bindings** (take-off, landing) are the same problem with the configured
aircraft inside the constraint — the flap is in the geometry, not a factor on C_L,max.
**If the geometry has flaps, they are used as constructed for that configuration; if it has
none, there is no configuration** (maintainer, 2026-10-02): the landing and take-off
stall speeds are then the clean stall speed — the same aircraft, not a fallback. The
multiplicative flap factor `C_L,max,cfg = f · C_L,max,clean` (`high-lift-clmax`) and its
`flap-clmax-factor` are deleted.

## ⚠️ Conflict

(a) TWO LIFT-BALANCE IMPLEMENTATIONS THAT DISAGREE ON DENSITY. flight_envelope_service:314 and analysis_service:524 both apply this law, but the first receives rho from a parameter defaulted to 1.225 that its only caller never passes, while the second uses rho at the requested altitude. Above sea level the same aircraft gets two stall speeds. Verified.

(b) NOT A CONFLICT — a declared cold start. operating_point_generator_service:346 sets V_S1 = max(3.0, V_cruise / 1.20) when the context carries no polar. The extraction called this a third law; it is not. It sets provenance = 'cold_start' (:351), and _stamp_stale_no_polar (:367, invoked at :1115) appends STALE_NO_POLAR to every target. It declares itself, as ADR 0020 requires. It needs renaming, not deciding — it is currently indistinguishable by name from a computed stall speed.

(c) THE REAL ONE — the configuration fallback. field_length_service:367-368 and operating_point_generator_service:355-356 substitute the clean V_S when the per-configuration value is absent, asserting C_L,max,LDG := C_L,max,clean. Seven lines earlier, at field_length_service:361, the same function multiplies C_L,max by up to 1.6 for that same configuration. One function assumes the flaps work and do not work at once; on the fallback branch the approach speed is up to 26 % too high while the landing distance is computed with the raised C_L,max. Verified.

The applications above dissolve (c) structurally rather than by correction: v_stall_landing_mps does not exist when there is no flap, and when there is one it comes from this law with cl_max_landing bound. What remains to decide is only (a): which density.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Applications (3)

One law, bound differently. Each application is approved separately, **after** the formula.

| application | binds | exists when | implementations |
|---|---|---|---|
| `v_stall_clean_mps` | `cl_max` = [[cl_max_clean]], `rho` = [[air_density_at_altitude]] | always | [[fe_v_stall]] · [[v-stall]] |
| `v_stall_takeoff_mps` | `cl_max` = [[cl_max_takeoff]], `rho` = [[air_density_at_altitude]] | the wing carries a flap | [[v-stall-to-fl]] |
| `v_stall_landing_mps` | `cl_max` = [[cl_max_landing]], `rho` = [[air_density_at_altitude]] | the wing carries a flap | [[v-stall-ldg-fl]] |

## Preconditions on the bindings

The formula is exact. These are the conditions its **inputs** must satisfy for an
application of it to mean what it claims. A violated precondition is a defect of the
path, not of the law.

### `cl_max` — ⚪

**Requirement.** Evaluated at the Reynolds number of the stall condition itself, not at cruise and not from a 2D table at Re ~ 1e6.

**Why it decides the answer.** C_L,max is a function of Reynolds number, steeply so in the model range: at low Re the boundary layer stays laminar further aft, separates against the adverse gradient and forms a laminar separation bubble that caps the suction peak. Lennon (Basics of R/C Model Aircraft Design, ch. 1-3) documents NACA 0012 falling from C_L,max 1.55 to 0.83 across the model Re range, with the stall angle dropping 17 deg to 10 deg. Since V_S ~ C_L,max^-0.5, the binding decides the answer.

**Consequence.** V_stall is therefore an IMPLICIT equation at model scale: V_S depends on C_L,max(Re) and Re depends on V_S. (Ist finding; resolved in the Soll by the optimisation above, which carries the Reynolds coupling inside the constraint — no fixed point needed.)

**In the code.** _fine_sweep_cl_max (app/services/assumption_compute_service.py:1141-1209) sweeps a velocity x alpha grid from v_stall_approx = max(v_cruise*0.5, 3.0) to v_max and then takes cl_max = float(np.max(cl_arr)) — the maximum over ALL velocities. AeroBuildup gets its section data from NeuralFoil, which IS Reynolds dependent, so the low-speed samples genuinely carry a lower C_L. Taking the max picks the FASTEST sample and uses it to compute the speed at the SLOWEST point of the envelope.

**Direction.** UNSAFE — C_L,max too high, so V_stall is reported too low: the aircraft stalls sooner than the app says.

**Also.** MEASURED across the fleet, 2026-08-18 (scripts/measure_clmax_reynolds_spread.py, 26 aircraft): every single spread is POSITIVE — the reported stall speed is always the low one. Median 2.9 %, maximum 33.2 %, above the 2 % tolerance in 20 of 26.

The governing factor is whether the velocity grid brackets the stall point. Within the 0.5-15 kg class (18 measurements): where it brackets (7), median +2.3 %, worst +4.2 %; where it does not (11), median +4.2 %, worst +33.2 %.

And it misses often because the lower bound is not a property of the aircraft: grid_lo = max(v_cruise*0.5, 3.0) evaluated to 9.00 m/s for EVERY aircraft measured, i.e. the default cruise speed of 18 m/s. A slow model — saal_flug stalls at 3.7 m/s, negatiV at 8.2 m/s — has its stall point entirely outside the sampled range.

**Test that settles it.** Sweep C_L,max(V) instead of max-over-all and compare the value at the low end of the range against the high end. If they diverge, the fixed-point iteration is required; if they do not, today's simplification is evidenced rather than assumed.

### `rho` — 🔴 **violated**

**Requirement.** The density of the altitude the speed is evaluated at.

**Why it decides the answer.** The V-n curve and the speed polar otherwise report two different stall speeds for one aircraft above sea level.

**In the code.** compute_vn_curve(rho: float = 1.225) — the only caller never passes rho (flight_envelope_service.py:288, :689).

**Direction.** The V-n envelope is always a sea-level result, silently.

## Implementations (7)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_v_stall]] | EXACT | 🟢 |  |
| [[v-stall]] | EXACT | 🟢 |  |
| [[vs_clean]] | DEVIATES | 🟢 | Cold-start branch abandons the lift balance entirely: V_S1 = max(3.0, V_cruise / min_speed |
| [[vs_ldg]] | DEVIATES | 🟢 | Does not compute V_S0. Reads a supplied v_s0_mps, else silently returns the clean V_S1 (C_ |
| [[vs_to]] | DEVIATES | 🟢 | Does not compute V_S,TO. Reads a supplied v_s_to_mps, else silently returns the clean V_S1 |
| [[v_stall_ldg]] | DEVIATES | 🟢 | Does not compute V_S0. Reads aircraft.v_s0_mps, else falls back to the clean v_stall -- wh |
| [[v_stall_to]] | DEVIATES | 🟢 | Does not compute V_S,TO. Reads aircraft.v_s_to_mps, else falls back to the clean v_stall,  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> **The relation was approved** (Sadraey Eq. 4.30). **The method — the optimisation that
> replaced the closed form on 2026-10-01 — is not yet approved:** it waits for the
> reference-fleet comparison (ANFORDERUNGEN §3.4.1). Hence `status: draft`.

