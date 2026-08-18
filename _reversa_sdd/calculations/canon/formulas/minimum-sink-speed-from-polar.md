---
canon: minimum-sink-speed-from-polar
kind: formula
shape: route
status: draft
output: minimum-sink-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
---

# Minimum-sink speed as the argmin of the computed sink rate

**Canonical form**

```
V_mp = V( argmin_i w_i ),  w_min = min_i w_i
```

**Produces** [[minimum-sink-speed]]  ·  **from** [[flight-speed]] · [[sink-rate]]

**Shape: a route.** This is one of several ways to the same quantity. The canon does not choose between them — it requires that they **agree**.

**Test that follows.** Both routes claim the same quantity by different means; they must agree. Where they do not, the polar is not parabolic — which is a statement about the aircraft, not a defect.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.5.2, Eq. 4.85: V for minimum power = sqrt( 2W / (rho*S*sqrt(3*C_Do/K)) ), identified as the speed for maximum rate of climb of a PROP-DRIVEN aircraft, explicitly distinguished from the jet's minimum-drag speed. Sadraey's supporting text gives C_L at minimum power = sqrt(3*C_Do/K) and the resulting 1.155 = sqrt(4/3) factor in Eq. 4.89.

**The source writes it as**

```
Sadraey gives the closed form; the proposal's argmin over computed sink rate is the numerical equivalent of the same condition. Sadraey also fixes the exact ratio: V_mp = V_md/3^0.25 = V_md/1.316, and (L/D) at minimum power = 0.866*(L/D)_max.
```

**Validity at 0.5–15 kg.** Valid and directly RC-relevant: Sadraey's statement that the minimum-power speed is the best-climb speed for a PROPELLER aircraft applies to essentially every 0.5-15 kg electric model. The V_mp = V_md/1.316 identity is a free consistency assertion the app should enforce between its two speeds - if the computed argmin and argmax disagree with it by much, the polar fit is bad, not the physics.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[i-min-sink]] | EXACT | 🟢 |  |
| [[v-min-sink]] | EXACT | 🟢 |  |
| [[w-min]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

