---
canon: operating-point-speed-from-stall-margin
kind: formula
shape: approximation
status: draft
output: operating-point-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/approximation
---

# Operating-point speed as a fixed margin over a stall speed

**Canonical form**

```
V_op = k_op * V_S,cfg   (optionally floored by a fraction of V_cruise or an absolute minimum)
```

**Produces** [[operating-point-speed]]  ·  **from** [[stall-speed]] · [[cruise-speed]]

⚠️ **Shape: an approximation.** A rule of thumb standing where a law belongs. It may be the right thing to show, but it is never approved *as* the law for this quantity.

> V_x and V_y are labelled best-angle and best-rate-of-climb but contain no climb relation — no thrust, no excess power.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> The specific multipliers are regulatory and appear in Scholz/Sadraey: CS 25.125 - stabilised approach at not less than 1.3*V_s (Scholz 05_PreliminarySizing §5.1); CS 25.111 - V_2 >= 1.2*V_S (Scholz §5.2); Sadraey §4.3.4 Eq. 4.72 - V_TO = 1.1 to 1.3*V_s, with V_LOF ~ 1.2*V_S,TO and V_R ~ 1.1-1.2*V_s; FAR 23.51 - V at 50 ft >= 1.20*V_S1 single-engine.

**The source writes it as**

```
Sources give named speeds with named factors, each tied to a certification requirement. The generalised scheme V_op = k_op*V_S,cfg with an optional V_cruise-fraction floor and an absolute minimum is the app's abstraction over them; the floors have no regulatory counterpart.
```

**Validity at 0.5–15 kg.** The factors are manned-aircraft certification minima. Two RC-specific cautions. (1) A 1.3 margin over a stall speed whose C_L,max is uncertain by 30-45% at model Reynolds number (see stall-speed) is thinner than the same 1.3 on a certified aircraft with a flight-tested V_S - at model scale the margin should arguably be larger, not equal. (2) Vx/Vy for a propeller model are properly the minimum-drag and minimum-power speeds (Sadraey Eq. 4.80/4.85), not multiples of V_S; and hand-launched models have no V_LOF or ground roll at all, so takeoff-derived operating points are undefined for that launch mode.

## Implementations (5)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_approach]] | EXACT | 🟢 |  |
| [[v_stall_near_clean]] | EXACT | 🟢 |  |
| [[v_stall_with_flaps]] | DEVIATES | 🟢 | k_op = 1.05 over V_S0 leaves only a 10% load-factor margin to stall (1.05^2 = 1.10 g); the |
| [[v_best_angle_climb_vx]] | DEVIATES | 🟢 | max(1.35*V_S1, 0.85*V_cruise). Labelled best-angle-of-climb but derived from no climb quan |
| [[v_best_rate_climb_vy]] | DEVIATES | 🟢 | max(1.50*V_S1, 0.95*V_cruise). Labelled best-rate-of-climb but derived from no climb quant |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

