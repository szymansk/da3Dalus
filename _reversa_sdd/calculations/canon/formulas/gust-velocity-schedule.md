---
canon: gust-velocity-schedule
kind: formula
shape: law
status: draft
output: gust-velocity
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
---

# Design gust velocity scheduled against airspeed

**Canonical form**

```
U(V) = U_C for V <= V_C;  U(V) = U_C + (V - V_C)/(V_D - V_C) * (U_D - U_C) for V > V_C
```

**Produces** [[gust-velocity]]  ·  **from** [[flight-speed]] · [[cruise-speed]] · [[dive-speed]]

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> 14 CFR 23.333(c) (FAR Part 23, Flight envelope - Gust envelope): positive and negative vertical gusts of 50 ft/s at V_C and 25 ft/s at V_D, at sea level, with gust load factors varying LINEARLY with speed between V_C and V_D. Commuter category additionally requires 66 ft/s at V_B up to 20,000 ft. CS-25.341 uses an altitude-dependent reference gust U_ref instead.

**The source writes it as**

```
The regulation schedules the gust against the design speeds V_C and V_D and specifies linear variation of the LOAD FACTOR between them; the proposal schedules the gust VELOCITY linearly between the same two anchors. These coincide only if the other terms in delta_n are treated as fixed - a minor but real difference in what is being interpolated.
```

**Validity at 0.5–15 kg.** The single most important RC qualification in the whole set. 50 ft/s = 15.2 m/s is a design gust for aircraft cruising above 100 m/s, where it is a small perturbation (delta_alpha ~ 8 deg). For an RC model cruising at 15-25 m/s the same gust is comparable to the flight speed itself: the small-angle linearisation delta_alpha = U/V that the entire Pratt formulation rests on gives delta_alpha of 30-45 deg, far beyond stall. The physical outcome is not a large delta_n but a stalled wing - C_L,max, not the gust formula, caps the load. Applying the FAR gust velocities unscaled at 0.5-15 kg produces load factors that cannot physically occur. Either scale U_de to the model's speed regime or cap delta_n at the C_L,max-limited value, and declare which (ADR 0020).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_u_gust_at_v]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

