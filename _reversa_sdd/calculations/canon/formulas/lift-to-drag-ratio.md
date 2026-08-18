---
canon: lift-to-drag-ratio
entry: formula
kind: law
shape: law
status: draft
output: lift-to-drag-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
---

# Lift-to-drag ratio

**Canonical form**

```
E = C_L / C_D = L / D
```

**Produces** [[lift-to-drag-ratio]]  ·  **from** [[lift-coefficient]] · [[drag-coefficient]] · [[lift-force]] · [[drag-force]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2: L/D = C_L/C_D. Scholz 05_PreliminarySizing §5.7: E = C_L/C_D. RC: RC-Network Wiki "Gleitzahl", E = A/W (Auftrieb/Widerstand).

**The source writes it as**

```
RC-Network adds the operationally useful identity E = horizontal distance / altitude lost in still air, and its reciprocal tan(glide angle) = 1/E. Scholz uses the symbol E throughout, matching the app's choice.
```

**Validity at 0.5–15 kg.** Exact - it is a ratio of two coefficients over the same q*S, so the reference area cancels and there is no scale dependence in the definition itself. RC-Network notes E is not a constant but a function of airspeed, which the app already respects by reporting it per point.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[speed-polar-ld]] | EXACT | 🟢 |  |
| [[ld-ratio-force]] | EQUIVALENT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

