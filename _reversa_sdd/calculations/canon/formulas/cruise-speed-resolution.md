---
canon: cruise-speed-resolution
entry: formula
kind: substitution
shape: law
status: draft
output: cruise-speed
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/substitution
  - status/draft
  - flag/conflict
---

# Resolution of the cruise speed when no mission goal supplies it

**Canonical form**

```
V_cruise := V_md   (substitution, not a physical law)
```

**Produces** [[cruise-speed]]  ·  **from** [[minimum-drag-speed]] · [[max-level-speed]] · [[dive-speed]]



ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. Not a procedure and not a law — three priority ladders that assign one already-computed quantity to the name of a different quantity. No equation is solved: operating_point_generator_service.py:271-284 returns ctx['v_md_mps'] as the cruise speed; matching_chart_service.py:786-800 is an if/elif chain ending in a literal; flight_envelope_service.py:190 is a division by a constant that the same module put there.

> 🔴 **An assumption of this entry is broken in the code.**
>
> Three, all real:
> (1) app/services/matching_chart_service.py:796 — `_v_md(500.0, ...)` pins the estimate to W/S = 500 N/m^2. The service's own sweep spans _WS_MIN=10 .. _WS_MAX=1500 N/m^2 (lines 71-72), and the 0.5-15 kg RC/UAV band this app targets sits near 30-150 N/m^2. Since V_md ~ sqrt(W/S), the estimated cruise speed is roughly 1.8-4x too high for a real RC model, and is IDENTICAL for every aircraft sharing cd0/e/AR regardless of mass or size. The emitted warning says only 'estimated from polar', hiding the constant. Also ADR 0023: a constant with no source, not validated at RC/UAV scale.
> (2) app/services/flight_envelope_service.py:190 sets v_c = v_dive/1.4 while flight_envelope_service.py:315 (and assumption_compute_service.py:956, `_compute_v_dive`) sets v_dive = 1.4*v_max. The two cancel exactly: V_C == V_max identically. Consequence: the gust-line interpolation between U_vc = 15.24 m/s and U_vd = 7.62 m/s (lines 232-236) has its low-speed anchor at V_max, so the constant U_vc is applied over the whole envelope from V_stall to V_max and the interpolation only ever runs on [V_max, 1.4*V_max]. `_compute_v_dive`'s own docstring (assumption_compute_service.py:951-953) records that the audit prefers anchoring V_D on V_C — i.e. the circularity is known internally and invisible externally.
> (3) app/services/operating_point_generator_service.py:277 — the terminal literal 18.0 m/s is returned as a cruise speed for an aircraft with no profile and no cached V_md, undeclared, and is then written into the profile goals (line 1101) where it drives every operating point.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🔴 NO SOURCE FOUND

> No source substitutes V_md for a mission cruise speed. The proposal is right to label it "substitution, not a physical law". The sources actively point the other way: Scholz 05_PreliminarySizing §5.7 tabulates best-range cruise at V/V_md = 1.316 (89.6% of E_max), and Sadraey §4.3.3.2 notes cruise is flown at 75-80% power with V_max ~ 1.2-1.3 V_C.

**The source writes it as**

```
Scholz's parametric table is the closest thing to a rule: V/V_md = 1.0 gives 100% of E_max, 1.316 gives 89.6%, 1.5 gives 81.7%, 2.0 gives 63.4% - i.e. real cruise sits above V_md and the efficiency penalty for doing so is initially small.
```

**Validity at 0.5–15 kg.** Scholz's remark that "prop aircraft cruise much closer to (L/D)max speed than jets do" (because power scales with V^3 for props) makes V_md a defensible LOWER BOUND for an electric RC model - closer to truth at RC scale than it would be for a jet. But it is still a floor, not an identity, and substituting it silently biases every downstream number (endurance up, dive speed down, stall-margin ratio down). Under ADR 0020 this substitution must emit a DesignWarning naming which of the three resolution paths was taken.

## ⚠️ Conflict

Three incompatible definitions of V_cruise coexist. (1) A mission goal read from the flight profile -- the only definition the rest of the chain assumes. (2) operating_point_generator_service:277 and matching_chart_service:785 substitute V_md when no goal exists. V_md is by definition the maximum-L/D speed, i.e. the best-endurance / best-rate-of-climb speed and explicitly NOT a cruise speed; the sizing literature puts cruise at V_max/1.2 to V_max/1.3, well above V_md. Because vs_clean can in turn derive V_S1 from V_cruise, this closes a loop in which the stall speed is a function of the minimum-drag speed and the cruise speed is a function of the stall speed. (3) flight_envelope_service:190 back-derives the gust envelope's V_C as V_D/1.4, and since V_D := 1.4*V_max upstream, V_C is identically V_max -- so the gust envelope's 'cruise speed' is the maximum level speed, the one speed at which the aircraft is certainly not cruising. Three different numbers carry the label cruise speed in one application.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cruise_speed_resolved]] | DEVIATES | 🟢 | Returns the cached V_md as the cruise speed when the aeroplane has no flight profile, sile |
| [[v_cruise_resolved]] | DEVIATES | 🟢 | Same substitution, plus a worse cold-start branch: it evaluates the V_md closed form at a  |
| [[fe_v_c]] | DEVIATES | 🔴 mismapped | Back-derives V_C = V_D/1.4 from a dive speed that was itself defined as 1.4*V_max, so the  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

