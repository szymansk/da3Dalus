---
canon: dynamic-pressure
entry: formula
kind: law
shape: law
status: draft
output: dynamic-pressure
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
---

# Dynamic pressure

**Canonical form**

```
q = 0.5 * rho * V^2
```

**Produces** [[dynamic-pressure]]  ·  **from** [[air-density]] · [[flight-speed]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 "Aerodynamic Forces and Moments": q_inf = 0.5*rho_inf*V_inf^2, introduced as the quantity that scales all force coefficients. Also Scholz 05_PreliminarySizing §5.6.2 (Eq. 5.30 context).

**Validity at 0.5–15 kg.** Exact. Incompressible form; valid for M < ~0.3, which every 0.5-15 kg RC/UAV airframe satisfies with a wide margin (except propeller tips, which are outside this chain). No qualification needed.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[q_dynamic_pressure]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

