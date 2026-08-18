---
canon: lift-balance-speed
kind: formula
status: draft
output: flight-speed
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
---

# Speed from the steady lift balance

**Canonical form**

```
V = sqrt(2 * m * g / (rho * S_ref * C_L))
```

**Produces** [[flight-speed]]  ·  **from** [[weight]] · [[air-density]] · [[wing-reference-area]] · [[lift-coefficient]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey §4.3.2 Eq. 4.30 rearranged; Scholz 05_PreliminarySizing §5.1 writes it directly as V_S,L = sqrt(2*m_ML*g/(rho*S_W*C_L,max,L)). RC: Lennon, Basics of R/C Model Aircraft Design, Ch. 3 "Understanding Aerodynamic Formulas"; RC-Network Wiki "Flächenbelastung" (v proportional to sqrt(W/S)).

**The source writes it as**

```
Lennon writes the model-unit form V = sqrt(Lift*3519/(sigma*C_L*S)) with V in mph, S in square inches, Lift in ounces, sigma the density ratio (1.00 SL, 0.8616 at 5000 ft); the 3519 absorbs unit conversion. Same relation.
```

**Validity at 0.5–15 kg.** Exact at any scale - this is the steady lift balance, no empiricism. All the RC risk is in the C_L input, not in this equation.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[speed-polar-v]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

