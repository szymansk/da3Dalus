---
canon: minimum-drag-speed-closed-form
kind: formula
status: draft
output: minimum-drag-speed
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - flag/conflict
---

# Minimum-drag speed from the parabolic polar

**Canonical form**

```
V_md = sqrt( 2*(W/S) / (rho * sqrt(C_D0 / k)) )
```

**Produces** [[minimum-drag-speed]]  ·  **from** [[wing-loading]] · [[air-density]] · [[zero-lift-drag-coefficient]] · [[induced-drag-factor]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.5, Eq. 4.80: V_ROCmax = V_Dmin = sqrt( (2*W/(rho*S)) / sqrt(C_Do/K) ). Cited by Sadraey to his own Aircraft Performance reference [5].

**The source writes it as**

```
Identical to the proposal once W/S is factored (Sadraey writes 2W/(rho*S) grouped, the proposal writes 2*(W/S)/rho). Sadraey introduces it as the speed for maximum rate of climb of a JET; the same quantity is the minimum-drag speed for any aircraft.
```

**Validity at 0.5–15 kg.** Valid at RC scale as an algebraic consequence of the parabolic polar, with the same caveat as max-lift-to-drag-parabolic: at Re 5e4-3e5 the polar is offset-parabolic, so C_D0 and k must be fitted over the C_L range of interest, not anchored at C_L = 0 (see zero-lift-drag-from-sweep). Do not let this closed form and the argmax-of-polar route both be authoritative - ADR 0022.

## ⚠️ Conflict

V_md is produced by three mutually independent laws in this application -- see also minimum-drag-speed-from-polar and minimum-drag-speed-heuristic. This one assumes a parabolic polar and depends on C_D0 and k; the second measures argmax(C_L/C_D) on the real computed polar; the third is a flat 1.4*V_S with no polar in it. They coincide only by accident. This producer additionally inherits the C_D0 ambiguity (see zero-lift-drag-from-sweep).

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_md]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

